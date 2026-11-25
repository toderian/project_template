#!/bin/bash
#
# Blocks obviously dangerous shell commands that aren't git-related.
# Companion to block-dangerous-git.sh. Both run as PreToolUse hooks on Bash.
# Patterns are intentionally narrow — false positives waste user attention more
# than they protect anything. Each pattern is anchored to a command-statement
# boundary (start of line, or after ; && || | $( ) so substrings inside quoted
# arguments (e.g., a commit message body) won't trigger.

command -v jq >/dev/null || { echo "hook requires jq; install jq" >&2; exit 2; }

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command')

# Boundary that must precede a dangerous keyword: start of string, or any of
# the shell statement separators / pipeline operators. Optionally tolerate a
# wrapper (sudo, env VAR=... assignments, xargs with flags) between the
# boundary and the actual command, since those are common accidental-danger
# vectors (e.g. `sudo rm -rf /`, `env FOO=1 rm -rf /`, `... | xargs rm -rf`).
CB='(^|[;&|]|\$\()[[:space:]]*(sudo[[:space:]]+|env([[:space:]]+[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*)*[[:space:]]+|xargs([[:space:]]+-[^[:space:]]+)*[[:space:]]+)?'

DANGEROUS_PATTERNS=(
  # Filesystem destruction. The "/" target's end-anchor tolerates trailing
  # flags (e.g. `rm -rf / --no-preserve-root`) instead of requiring "/" to be
  # the last token.
  "${CB}rm[[:blank:]]+-[a-zA-Z]*r[a-zA-Z]*f?[[:blank:]]+/([[:blank:]]+--[a-zA-Z-]+)*[[:blank:]]*\$"
  "${CB}rm[[:blank:]]+-[a-zA-Z]*r[a-zA-Z]*f?[[:blank:]]+/\\*"
  "${CB}rm[[:blank:]]+-rf[[:blank:]]+~/?[[:blank:]]*\$"
  "${CB}find[[:blank:]]+/[[:blank:]].*-delete"
  "${CB}find[[:blank:]]+/[[:blank:]].*-exec[[:blank:]]+rm"

  # Block-device / disk overwrites
  "${CB}dd[[:blank:]]+.*of=/dev/(sd|nvme|hd|vd)"
  '>[[:blank:]]*/dev/sd[a-z]'
  '>[[:blank:]]*/dev/nvme'

  # Permission escalation surfaces
  "${CB}chmod[[:blank:]]+-R[[:blank:]]+0*777[[:blank:]]+/"
  "${CB}chown[[:blank:]]+-R[[:blank:]]+.*[[:blank:]]+/[[:blank:]]*\$"

  # Untrusted-code-from-network execution
  "${CB}curl[[:blank:]]+[^|]*\\|[[:blank:]]*(sudo[[:blank:]]+)?(bash|sh|zsh|fish)"
  "${CB}wget[[:blank:]]+[^|]*\\|[[:blank:]]*(sudo[[:blank:]]+)?(bash|sh|zsh|fish)"
  "${CB}(bash|sh)[[:blank:]]+<\\([[:blank:]]*(curl|wget)"
  "${CB}eval[[:blank:]]+\"?\\\$\\((curl|wget)"

  # System-level reset
  "${CB}:\\(\\)\\{[[:space:]]*:\\|:&[[:space:]]*\\};:"    # fork bomb
  "${CB}mkfs\\.[a-z0-9]+[[:blank:]]+/dev/"
  "${CB}shutdown[[:blank:]]+-h[[:blank:]]+now"
  "${CB}systemctl[[:blank:]]+(poweroff|halt)"
)

for pattern in "${DANGEROUS_PATTERNS[@]}"; do
  if echo "$COMMAND" | grep -qE "$pattern"; then
    echo "BLOCKED: '$COMMAND' matches dangerous pattern '$pattern'. The user has prevented you from doing this." >&2
    exit 2
  fi
done

# Writes into .creds/ or a .env file. block-write-sensitive.sh guards the file
# tools; this is the same guardrail for the common shell forms: an output
# redirect (`>`, `>>`, `>|`, `>&`, `&>`, `<>`), tee, the destination of
# cp/mv/install (also `-t DIR`, and a protected name copied into `.`),
# `install -d`, and sed -i. Reading stays allowed (`cat .env`, `cp .env /tmp/x`).
# It stops the accidental write, not a determined one: a path built from a
# variable, eval, `bash -c '...'`, or another write tool (curl -o, ln, rsync)
# passes.
#
# The awk program reads the command the way the shell does, so text a command
# only carries is never a write: it splits the command into simple commands and
# words, keeping quoted text inside its word, and drops heredoc bodies and
# comments. `$( )`, backticks and `<( )`/`>( )` are commands of their own, and
# stand for one opaque piece of the word they sit in; a `( )` subshell is a
# group of its own. `$(( ))`, `(( ))` and
# `[[ ]]` hold no redirects. Brace expansion (`.env{.example,}`) is expanded.
# Protected: a `.creds` path segment (a glob segment counts if it matches); a basename `.env`, `.env.<x>`, `.env*`,
# `.envrc` or `<name>.env`, except a scaffold: a `.env` name ending in `.example`,
# `.sample` or `.template` (`.env.example`, `.env.local.example`). `..` segments are
# resolved first.
#
# Known gaps, left open on purpose (rare forms; see the 2026-11 review rounds):
# a brace word with a quoted part after the braces (`.env{.example,}''`), a
# target spelled with `$'\NNN'` escapes, a `case` inside `( )` inside "$( )".
# A quoted `'.env*'` is treated as a glob and blocked.
SCAN_BLOCK=$(printf '%s\n' "$COMMAND" | tr -d '\r' | awk '
  function prot(p,   n, s, i, o, k, b, r) {
    n = split(p, s, "/"); k = 0
    for (i = 1; i <= n; i++) {
      if (s[i] == "." || (s[i] == "" && i > 1)) continue
      if (s[i] == ".." && k > 0 && o[k] != ".." && o[k] != "") { k--; continue }
      o[++k] = s[i]
    }
    for (i = 1; i <= k; i++) if (gm(o[i], ".creds")) return 1
    if (k == 0) return 0
    b = o[k]
    if (b ~ /[*?[]/ && (gm(b, ".env") || gm(b, ".envrc"))) return 1
    if (b == ".envrc") return 1
    if (substr(b, 1, 4) == ".env") {
      r = substr(b, 5)
      if (r == "") return 1
      if (r ~ /\.(example|sample|template)[*?]*$/) return 0
      return r ~ /^[.*?]/
    }
    return b ~ /.\.env$/
  }
  # gm(pattern, name): does the glob match the name? A leading dot must match
  # literally; a bracket class `[...]` matches any one character.
  function gm(p, x,   re, i, c, j) {
    if (p !~ /[*?[]/) return p == x
    if (substr(x, 1, 1) == "." && substr(p, 1, 1) != ".") return 0
    re = ""
    for (i = 1; i <= length(p); i++) {
      c = substr(p, i, 1)
      if (c == "*") re = re ".*"; else if (c == "?") re = re "."
      else if (c == "[" && (j = index(substr(p, i + 1), "]")) > 1) { re = re "."; i += j }
      else if (index("\\^$.|+(){}[]", c)) re = re "\\" c; else re = re c
    }
    return x ~ ("^" re "$")
  }
  function base(p) { sub(/\/+$/, "", p); sub(/.*\//, "", p); return p }
  # Brace expansion, one group at a time; a group needs a comma.
  function expand(w, res,   q, qn, qi, cur, s, e, pre, body, post, parts, np2, j, k) {
    k = 0; qn = 1; q[1] = w; qi = 0
    while (qi < qn) {
      cur = q[++qi]; s = index(cur, "{"); e = s ? index(substr(cur, s), "}") : 0
      if (!s || !e || !index(substr(cur, s, e), ",") || qn > 64) { res[++k] = cur; continue }
      pre = substr(cur, 1, s - 1); body = substr(cur, s + 1, e - 2); post = substr(cur, s + e)
      np2 = split(body, parts, ",")
      for (j = 1; j <= np2; j++) q[++qn] = pre parts[j] post
    }
    return k
  }
  function checkword(w, q,   r, k, i) { if (q) { if (prot(w)) blocked = 1; return }; k = expand(w, r); for (i = 1; i <= k; i++) if (prot(r[i])) blocked = 1 }
  # QB marks a word whose braces came from quoted text: bash does not expand those.
  function add(f, c) { if (QS[f] != "" && index("{,}", c)) QB[f] = 1; if (length(CW[f]) < 4096) CW[f] = CW[f] c }
  # A keyword counts only unquoted, where a command starts.
  function cmdpos(f) { return WN[f] == 0 || W[f, WN[f]] ~ /^(if|elif|while|until|then|do|else|!|\{|time)$/ }
  function endword(f,   w, kw, q) {
    if (!CH[f] && CW[f] == "") return
    w = CW[f]; q = QB[f]; kw = !CH[f] && cmdpos(f); CW[f] = ""; CH[f] = 0; QB[f] = 0
    if (RP[f] == 1 || (RP[f] == 4 && w !~ /^([0-9]+-?|-)$/)) { checkword(w, q); RP[f] = 0; return }
    if (RP[f]) { RP[f] = 0; return }
    if (DBL[f] && w == "]]") DBL[f] = 0
    else if (kw && w == "[[") DBL[f] = 1
    else if (kw && w == "case") INC[f]++
    else if (kw && w == "esac" && INC[f] > 0) INC[f]--
    W[f, ++WN[f]] = w; WQ[f, WN[f]] = q
  }
  function evalcmd(f,   A, na, i, j, k, r, w, a, cmd, td, ops, no, dd, dflag, ip, sg, pos, t, d, ns) {
    na = 0
    for (i = 1; i <= WN[f]; i++) {
      if (WQ[f, i]) { A[++na] = W[f, i]; continue }
      k = expand(W[f, i], r); for (j = 1; j <= k; j++) A[++na] = r[j]
    }
    WN[f] = 0; RP[f] = 0
    i = 1
    while (i <= na) {
      w = A[i]
      if (w ~ /^[A-Za-z_][A-Za-z0-9_]*\+?=/ || w ~ /^(!|\{|\}|then|do|else|elif|if|while|until|nohup)$/) { i++; continue }
      if (w == "function") { i += 2; continue }
      if (w ~ /^(sudo|doas|env|xargs|timeout|nice|ionice|stdbuf|command|builtin|time|exec)$/) {
        i++
        while (i <= na && (A[i] ~ /^-/ || (w == "env" && A[i] ~ /=/))) {
          if ((w ~ /^(sudo|doas)$/ && A[i] ~ /^-[ugCDhprRT]$/) || (w == "env" && A[i] ~ /^-[uSC]$/) \
              || (w == "xargs" && A[i] ~ /^-[IdLnPsaE]$/) || (w == "timeout" && A[i] ~ /^-[sk]$/) \
              || (w ~ /^(nice|ionice|stdbuf)$/ && A[i] ~ /^-[nctioe]$/) || (w == "exec" && A[i] == "-a")) i++
          i++
        }
        if (w == "timeout") i++
        continue
      }
      break
    }
    if (i > na) return
    cmd = A[i++]; if (cmd ~ /^\//) sub(/.*\//, "", cmd)
    if (cmd == "tee") {
      for (dd = 0; i <= na; i++) {
        a = A[i]
        if (!dd && a == "--") { dd = 1; continue }
        if (!dd && a ~ /^-./) continue
        if (prot(a)) blocked = 1
      }
      return
    }
    if (cmd == "cp" || cmd == "mv" || cmd == "install") {
      td = ""; no = 0; dd = 0; dflag = 0
      for (; i <= na; i++) {
        a = A[i]
        if (dd || a !~ /^-./) { ops[++no] = a; continue }
        if (a == "--") { dd = 1; continue }
        if (a ~ /^--target-directory=/) { td = substr(a, 20); continue }
        if (a == "--target-directory") { td = A[++i]; continue }
        if (a ~ /^--/) continue
        if (cmd == "install" && a ~ /^-[^-]*d/) dflag = 1
        # Short flags left to right: -t takes DIR; -S (and install -m -o -g) take a value.
        for (pos = 2; pos <= length(a); pos++) {
          t = substr(a, pos, 1)
          if (t == "t") { t = substr(a, pos + 1); td = (t != "") ? t : A[++i]; break }
          if (t == "S" || (cmd == "install" && index("mog", t))) { if (pos == length(a)) i++; break }
        }
      }
      if (dflag) { for (k = 1; k <= no; k++) if (prot(ops[k])) blocked = 1; return }
      if (td != "") { d = td; ns = no }
      else { if (no < 2) return; d = ops[no]; ns = no - 1 }
      if (prot(d)) blocked = 1
      if (d ~ /^\.\/?$/) for (k = 1; k <= ns; k++) if (prot(base(ops[k]))) blocked = 1
      return
    }
    if (cmd == "sed") {
      ip = 0; sg = 0; no = 0; dd = 0
      for (; i <= na; i++) {
        a = A[i]
        if (dd || a !~ /^-./) { if (!sg) sg = 1; else ops[++no] = a; continue }
        if (a == "--") { dd = 1; continue }
        if (a ~ /^--in-place/) { ip = 1; continue }
        if (a ~ /^--(expression|file)$/) { sg = 1; i++; continue }
        if (a ~ /^--(expression|file)=/) { sg = 1; continue }
        if (a ~ /^--/) continue
        if (a ~ /^-[^-iI]*[iI]/) { ip = 1; continue }
        if (a ~ /[ef]$/) { sg = 1; i++ }
      }
      if (ip) for (k = 1; k <= no; k++) if (prot(ops[k])) blocked = 1
    }
  }
  function openf(k) { fd++; FK[fd] = k; CW[fd] = ""; CH[fd] = 0; QB[fd] = 0; WN[fd] = 0; RP[fd] = 0; QS[fd] = ""; INC[fd] = 0; DBL[fd] = 0 }
  function closef() {
    endword(fd); evalcmd(fd)
    if (fd > 1) { fd--; add(fd, "\001"); CH[fd] = 1 }
  }
  function arith(j, f,   dep) {
    dep = 2
    for (; j <= n; j++) { if (ch[j] == "(") dep++; else if (ch[j] == ")" && --dep == 0) break }
    add(f, "\001"); CH[f] = 1
    return j
  }
  function heredoc(j,   dash, q2, tag, c2) {
    dash = 0; if (ch[j] == "-") { dash = 1; j++ }
    while (ch[j] == " " || ch[j] == "\t") j++
    if (ch[j] == "\\") j++
    q2 = ""; tag = ""
    for (; j <= n; j++) {
      c2 = ch[j]
      if (q2 != "") { if (c2 == q2) q2 = ""; else tag = tag c2; continue }
      if (c2 == "\047" || c2 == "\"") { q2 = c2; continue }
      if (index(" \t;&|<>()", c2)) break
      tag = tag c2
    }
    if (tag != "") { ptag[++np] = tag; pdash[np] = dash }
    return j - 1
  }
  function skipdocs(   line, t) {
    while (pt <= np && ln < m) {
      line = L[++ln]; if (pdash[pt]) sub(/^\t+/, "", line)
      t = ptag[pt]
      if (line == t) { pt++; continue }
      if (fd > 1 && substr(line, 1, length(t) + 1) == t ")") { L[ln] = substr(line, length(t) + 1); pt++; ln--; break }
    }
    if (pt > np) { np = 0; pt = 1 }
  }
  { L[++m] = $0 }
  END {
    fd = 1; FK[1] = "T"; np = 0; pt = 1
    for (ln = 1; ln <= m && !blocked; ln++) {
      n = split(L[ln], ch, ""); cont = 0
      for (i = 1; i <= n && !blocked; i++) {
        c = ch[i]; f = fd; qs = QS[f]
        if (qs == "S") { if (c == "\047") QS[f] = ""; else add(f, c); continue }
        if (c == "\\") {
          if (i == n) { cont = 1; break }
          c = ch[++i]
          if (qs == "D" && !index("$`\"\\", c)) add(f, "\\")
          add(f, c); CH[f] = 1; continue
        }
        if (qs == "A") { if (c == "\047") QS[f] = ""; else add(f, c); continue }
        if (qs == "D") {
          if (c == "\"") QS[f] = ""
          else if (c == "$" && ch[i + 1] == "(" && ch[i + 2] == "(") i = arith(i + 3, f)
          else if (c == "$" && ch[i + 1] == "(") { i++; openf("C") }
          else if (c == "`") openf("B")
          else add(f, c)
          continue
        }
        if (c == " " || c == "\t") { endword(f); continue }
        if (c == "#" && CW[f] == "" && !CH[f]) break
        if (c == "\047" || c == "\"") {
          isd = (CW[f] ~ /\$$/); if (isd) CW[f] = substr(CW[f], 1, length(CW[f]) - 1)
          QS[f] = (c == "\"") ? "D" : (isd ? "A" : "S"); CH[f] = 1; continue
        }
        if (c == "`") { if (FK[f] == "B") closef(); else openf("B"); continue }
        if (c == "$" && ch[i + 1] == "(" && ch[i + 2] == "(") { i = arith(i + 3, f); continue }
        if (c == "(" && ch[i + 1] == "(" && !CH[f] && (CW[f] == "for" || (CW[f] == "" && (WN[f] == 0 || W[f, WN[f]] == "for")))) { endword(f); i = arith(i + 2, f); continue }
        if (c == "$" && ch[i + 1] == "(") { i++; openf("C"); continue }
        if ((c == "<" || c == ">") && ch[i + 1] == "(" && !DBL[f]) { i++; openf("P"); continue }
        if (c == "$" && ch[i + 1] == "[") { for (i += 2; i <= n && ch[i] != "]"; i++); add(f, "\001"); CH[f] = 1; continue }
        if (c == ")") {
          endword(f)
          if (FK[f] == "G") { evalcmd(f); fd-- }
          else if ((FK[f] == "C" || FK[f] == "P") && !INC[f]) closef()
          else evalcmd(f)
          continue
        }
        if (c == "(") { endword(f); evalcmd(f); openf("G"); continue }
        if (c == ";" || c == "|" || (c == "&" && ch[i + 1] != ">")) { endword(f); evalcmd(f); continue }
        if (DBL[f] && (c == "<" || c == ">")) { endword(f); continue }
        if (c == "&") { endword(f); i++; if (ch[i + 1] == ">") i++; RP[f] = 1; continue }
        if (c == ">") {
          if (CW[f] ~ /^[0-9]+$/ && !CH[f]) CW[f] = ""; else endword(f)
          if (ch[i + 1] == ">" || ch[i + 1] == "|") { i++; RP[f] = 1 }
          else if (ch[i + 1] == "&") { i++; RP[f] = 4 }
          else RP[f] = 1
          continue
        }
        if (c == "<") {
          if (CW[f] ~ /^[0-9]+$/ && !CH[f]) CW[f] = ""; else endword(f)
          if (ch[i + 1] == "<" && ch[i + 2] == "<") { i += 2; RP[f] = 2; continue }
          if (ch[i + 1] == "<") { i = heredoc(i + 2); continue }
          if (ch[i + 1] == ">") { i++; RP[f] = 1; continue }
          if (ch[i + 1] == "&") i++
          RP[f] = 2; continue
        }
        add(f, c)
      }
      if (cont || blocked) continue
      if (QS[fd] != "") { add(fd, "\n"); continue }
      endword(fd); evalcmd(fd)
      if (np >= pt) skipdocs()
    }
    while (fd >= 1 && !blocked) { endword(fd); evalcmd(fd); fd-- }
    if (blocked) print "BLOCK"
  }')

if [[ "$SCAN_BLOCK" == BLOCK ]]; then
  echo "BLOCKED: '$COMMAND' writes to a sensitive path (.creds/ or a .env file). If this is intentional, ask the user to do it." >&2
  exit 2
fi

exit 0
