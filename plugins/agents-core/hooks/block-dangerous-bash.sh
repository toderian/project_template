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
# tools; this is the same guardrail for the common shell forms: a redirect
# (`>`, `>>`, `>|`), tee, the destination of cp/mv/install (also `-t DIR`), and
# sed -i. Reading stays allowed (`cat .env`, `cp .env /tmp/x`). It stops the
# accidental write, not a determined one: a path built from a variable, or a
# command run through eval or `bash -c '...'`, passes.
TOKEN="[^[:space:];&|<>()]"
NAME="[^[:space:];&|<>()/]"
END="([[:space:];&|)<>]|\$)"
# A directory prefix may include a command substitution: "$(pwd)/.env".
PREFIX="((${TOKEN}|\\\$\\([^()]*\\))*/)?"
CREDS_BASE="\\.creds"
# The same .env files as block-write-sensitive.sh: .env, .env.<x>, .envrc, <name>.env.
ENV_BASE="(\\.env(\\.${NAME}*)?|\\.envrc|${NAME}+\\.env)"
CREDS_TARGET="${PREFIX}${CREDS_BASE}(/${TOKEN}*)?"
ENV_TARGET="${PREFIX}${ENV_BASE}"

# A write command starts a statement: after a separator, `(`, `{`, `$(` or a
# `case` pattern's `)`, behind any keywords and wrappers (if, elif, while,
# until, then, do, else, !, time, VAR=value, env, command, nohup, exec, sudo,
# doas, xargs), each with its options.
WRAP="(([A-Za-z_][A-Za-z0-9_]*=${TOKEN}*|if|elif|while|until|then|do|else|!|time|command|nohup|exec|env|sudo|doas|xargs)([[:blank:]]+-${TOKEN}*([[:blank:]]+[^-[:space:];&|<>()]${TOKEN}*)?)*[[:blank:]]+)*"
WB="(^|[;&|({)]|\\\$\\()[[:blank:]]*${WRAP}"

# write_patterns <target regex> <basename regex>: one pattern per line. The
# cp/mv/install destination is the last word, which may be followed by options
# (`-f`, `-m 600`), its own redirect or a here-string. Copying a protected name
# into `.` writes it there too (`cp ../main/.env .`).
AFTER="([[:blank:]]+-${TOKEN}*([[:blank:]]+[0-9]+)?)*[[:blank:]]*([;&|)<]|\$|[0-9&]*>)"
write_patterns() {
  printf '%s\n' \
    ">[>|]?[[:blank:]]*$1${END}" \
    "${WB}tee[[:blank:]]+([^;&|<>()]*[[:blank:]])?$1${END}" \
    "${WB}(cp|mv|install)[[:blank:]]+[^;&|<>()]*[[:blank:]]$1${AFTER}" \
    "${WB}(cp|mv|install)[[:blank:]]+([^;&|<>()]*[[:blank:]])?${PREFIX}$2/?[[:blank:]]+([^;&|<>()]*[[:blank:]])?\\./?${AFTER}" \
    "${WB}sed[[:blank:]]+([^;&|<>()]*[[:blank:]])?(-[A-Za-z]*i|--in-place)[^;&|<>()]*[[:blank:]]$1${END}"
}

# Read the command the way the shell does, so text it only carries is not a
# write: a quoted commit message, a heredoc body, a comment. The scanner keeps a
# stack of contexts: code (unquoted, or inside `$( )` or backticks), '...',
# $'...', "...". A backtick substitution reads as `$( )`.
# - Text inside quotes becomes plain word characters: whitespace, newlines,
#   quotes and shell operators turn into `_`. A quoted target stays a target
#   (`> 'my app.env'` reads `> my_app.env`); a message keeps no operator.
#   `$( )` inside "..." is code again, so `x="$(echo k > .env)"` is a write.
# - A heredoc body is dropped; the line that opens it keeps its redirect. Every
#   opener form counts (`<<EOF`, `<<-EOF`, `<<'EOF'`, `<<"EOF"`, `<<\EOF`, a
#   quoted tag with spaces, any unquoted word as tag, several on one line, one inside `"$( ... )"`), and
#   `EOF)` closes one inside `$( )`. `<<<`, and `<<` in quotes or arithmetic,
#   open nothing. Only `<<-` lets the closing tag carry leading tabs.
# - `#` at the start of a word starts a comment; a backslash-newline joins lines.
# A command over 100 KB is checked as written (some awks slow down
# quadratically on very long input): a heredoc body there is checked as code,
# and a quoted target with a space in it passes.
if (( ${#COMMAND} > 100000 )); then
  SCAN=$COMMAND
else
SCAN=$(printf '%s\n' "$COMMAND" | tr -d '\r' | awk '
  function sp(c) { return index(" \t<>|;&()\"\047`", c) ? "_" : c }
  function wordstart(s, i) { return i == 1 || index(" \t;&|(", substr(s, i - 1, 1)) > 0 }
  BEGIN { d = 1; st[1] = "U" }
  {
    s = $0
    if (skipping) {
      line = s; if (strip[ti]) sub(/^\t+/, "", line)
      tl = length(tags[ti])
      if (line == tags[ti] || (st[d] == "C" && substr(line, 1, tl + 1) == tags[ti] ")")) {
        rest = substr(line, tl + 1)
        if (++ti > nt) { skipping = 0; nt = 0 }
        if (skipping || rest == "") next
        s = rest
      } else next
    }
    n = length(s); cont = 0
    for (i = 1; i <= n; i++) {
      c = substr(s, i, 1); t = st[d]
      if (t == "S") { if (c == "\047") d--; else printf "%s", sp(c); continue }
      if (c == "\\") {
        if (i == n) { cont = 1; break }
        i++; printf "%s", sp(substr(s, i, 1)); continue
      }
      if (t == "A") { if (c == "\047") d--; else printf "%s", sp(c); continue }
      if (t == "D") {
        if (c == "\"") d--
        else if (substr(s, i, 2) == "$(" && substr(s, i + 2, 1) != "(") { st[++d] = "C"; printf "$("; i++ }
        else if (c == "`") { st[++d] = "B"; printf "$(" }
        else printf "%s", sp(c)
        continue
      }
      if (c == "#" && arith == 0 && wordstart(s, i)) break
      if (c == "\047") { st[++d] = (i > 1 && substr(s, i - 1, 1) == "$") ? "A" : "S"; continue }
      if (c == "\"") { st[++d] = "D"; continue }
      if (c == "`") { if (t == "B") { d--; printf ")" } else { st[++d] = "B"; printf "$(" }; continue }
      if (substr(s, i, 3) == "$((") { arith++; printf "$(("; i += 2; continue }
      if (substr(s, i, 2) == "((" && (wordstart(s, i) || substr(s, i - 3, 3) == "for")) { arith++; printf "(("; i++; continue }
      if (arith > 0 && substr(s, i, 2) == "))") { arith--; printf "))"; i++; continue }
      if (arith == 0 && substr(s, i, 2) == "$(") { st[++d] = "C"; printf "$("; i++; continue }
      if (t == "C" && c == "(") { st[++d] = "C"; printf "("; continue }
      if (t == "C" && c == ")") { d--; printf ")"; continue }
      if (substr(s, i, 3) == "<<<") { printf "<<<"; i += 2; continue }
      if (arith == 0 && substr(s, i, 2) == "<<") {
        j = i + 2; dash = 0; if (substr(s, j, 1) == "-") { dash = 1; j++ }
        while (substr(s, j, 1) == " " || substr(s, j, 1) == "\t") j++
        qc = substr(s, j, 1); tag = ""
        if (qc == "\047" || qc == "\"") {
          k = index(substr(s, j + 1), qc); if (k > 1) { tag = substr(s, j + 1, k - 1); j += k + 1 }
        } else {
          if (qc == "\\") j++
          while (j <= n && !index(" \t;&|<>()\"\047", substr(s, j, 1))) { tag = tag substr(s, j, 1); j++ }
        }
        if (tag != "") {
          tags[++nt] = tag; strip[nt] = dash; shown = tag; gsub(/[ \t]/, "_", shown)
          printf "<<%s", shown; i = j - 1; continue
        }
      }
      printf "%s", c
    }
    if (cont) next
    if (nt > 0 && !skipping) { skipping = 1; ti = 1 }
    arith = 0
    printf "%s", (st[d] == "U" || st[d] == "C" || st[d] == "B" ? "\n" : "_")
  }
  END { printf "\n" }')
fi

# `cp -t DIR SRC...`: move DIR to the end, where the destination rule looks.
SCAN=$(printf '%s\n' "$SCAN" | sed -E "s/(^|[[:blank:]])(-t[[:blank:]]*|--target-directory[=[:blank:]][[:blank:]]*)(${TOKEN}+)([^;&|<>()]*)/\\1\\4 \\3/g")

# .env.example, .env.sample and .env.template are committed scaffolds: drop
# those words before the .env check. Nothing under .creds/ is a scaffold, so
# that check reads the command as scanned.
SCAFFOLD_FREE=$(printf '%s\n' "$SCAN" | sed -E "s/${TOKEN}*\\.(example|sample|template)${END}/\\2/g")

check_writes() {
  local text="$1" target="$2" pattern
  while IFS= read -r pattern; do
    if printf '%s\n' "$text" | grep -qE -- "$pattern"; then
      echo "BLOCKED: '$COMMAND' writes to a sensitive path (.creds/ or a .env file). If this is intentional, ask the user to do it." >&2
      exit 2
    fi
  done < <(write_patterns "$target" "$3")
}
check_writes "$SCAN" "$CREDS_TARGET" "$CREDS_BASE"
check_writes "$SCAFFOLD_FREE" "$ENV_TARGET" "$ENV_BASE"

exit 0
