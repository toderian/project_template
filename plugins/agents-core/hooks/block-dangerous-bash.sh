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
CREDS_TARGET="(${TOKEN}*/)?\\.creds(/${TOKEN}*)?"
# The same .env files as block-write-sensitive.sh: .env, .env.<x>, .envrc, <name>.env.
ENV_TARGET="(${TOKEN}*/)?(\\.env(\\.${NAME}*)?|\\.envrc|${NAME}+\\.env)"

# A write command starts a statement: after a separator, `(`, `{` or `$(`,
# behind any keywords and wrappers (then, do, else, !, time, VAR=value, env,
# command, nohup, exec, sudo, doas, xargs), each with its options.
WRAP="(([A-Za-z_][A-Za-z0-9_]*=${TOKEN}*|then|do|else|!|time|command|nohup|exec|env|sudo|doas|xargs)([[:blank:]]+-${TOKEN}*([[:blank:]]+[^-[:space:];&|<>()]${TOKEN}*)?)*[[:blank:]]+)*"
WB="(^|[;&|({]|\\\$\\()[[:blank:]]*${WRAP}"

# write_patterns <target regex>: one pattern per line. The cp/mv/install
# destination is the last word, which may be followed by its own redirect.
write_patterns() {
  printf '%s\n' \
    ">[>|]?[[:blank:]]*$1${END}" \
    "${WB}tee[[:blank:]]+([^;&|<>()]*[[:blank:]])?$1${END}" \
    "${WB}(cp|mv|install)[[:blank:]]+[^;&|<>()]*[[:blank:]]$1[[:blank:]]*([;&|)]|\$|[0-9&]*>)" \
    "${WB}sed[[:blank:]]+([^;&|<>()]*[[:blank:]])?(-i|--in-place)[^;&|<>()]*[[:blank:]]$1${END}"
}

# Read the command the way the shell does, so text it only carries is not a
# write: a quoted commit message, a heredoc body, a comment.
# - A quoted string becomes one plain word: the quotes go, and whitespace,
#   newlines, quotes and shell operators inside it become `_`. A quoted target
#   stays a target (`> 'my app.env'` reads `> my_app.env`); a message keeps no
#   operator. A backslash escape reads the same way.
# - A heredoc body is dropped; the line that opens it keeps its redirect. Every
#   opener form counts (`<<EOF`, `<<-EOF`, `<<'EOF'`, `<<"EOF"`, `<<\EOF`, a tag
#   with `-` or `.`, several on one line), and so does one inside `"$( ... )"`,
#   the usual commit-message form. `<<` in other quoted text, `<<<` and `<<`
#   inside `$(( ))` open nothing.
# - `#` at the start of a word starts a comment; a backslash-newline joins lines.
SCAN=$(printf '%s\n' "$COMMAND" | tr -d '\r' | awk '
  function sp(c) { return index(" \t<>|;&()\"\047", c) ? "_" : c }
  function wordstart(s, i) { return i == 1 || index(" \t;&|(", substr(s, i - 1, 1)) > 0 }
  skipping {
    line = $0; sub(/^\t+/, "", line)
    if (line == tags[ti] && ++ti > nt) { skipping = 0; nt = 0 }
    next
  }
  {
    s = $0; n = length(s); cont = 0
    for (i = 1; i <= n; i++) {
      c = substr(s, i, 1)
      if (q == "\047") { if (c == q) q = ""; else printf "%s", sp(c); continue }
      if (c == "\\") {
        if (i == n) { cont = 1; break }
        i++; printf "%s", sp(substr(s, i, 1)); continue
      }
      if (q == "\"" && dsub == 0) {
        if (c == q) q = ""
        else if (c == "$" && substr(s, i + 1, 1) == "(" && substr(s, i + 2, 1) != "(") { dsub = 1; i++; printf "__" }
        else printf "%s", sp(c)
        continue
      }
      if (q == "\"") {
        if (c == "\"") { q = ""; dsub = 0; continue }
        if (c == ")") { dsub--; printf "_"; continue }
        if (c == "(") { dsub++; printf "_"; continue }
      } else {
        if (c == "#" && arith == 0 && wordstart(s, i)) break
        if (c == "\"" || c == "\047") { q = c; continue }
        if (substr(s, i, 3) == "$((") { arith++; printf "$(("; i += 2; continue }
        if (arith > 0 && substr(s, i, 2) == "))") { arith--; printf "))"; i++; continue }
      }
      if (substr(s, i, 3) == "<<<") { printf "%s", (q == "" ? "<<<" : "___"); i += 2; continue }
      if (arith == 0 && substr(s, i, 2) == "<<") {
        j = i + 2; if (substr(s, j, 1) == "-") j++
        while (substr(s, j, 1) == " " || substr(s, j, 1) == "\t") j++
        qc = substr(s, j, 1); if (qc == "\047" || qc == "\"" || qc == "\\") j++
        tag = ""; while (substr(s, j, 1) ~ /[A-Za-z0-9_.-]/) { tag = tag substr(s, j, 1); j++ }
        if (tag != "") {
          if ((qc == "\047" || qc == "\"") && substr(s, j, 1) == qc) j++
          tags[++nt] = tag; printf "%s", (q == "" ? "<<" : "__") tag; i = j - 1; continue
        }
      }
      printf "%s", (q == "" ? c : sp(c))
    }
    if (cont) next
    if (nt > 0) { skipping = 1; ti = 1 }
    printf "%s", (q == "" ? "\n" : "_")
  }
  END { printf "\n" }')

# `cp -t DIR SRC...`: move DIR to the end, where the destination rule looks.
SCAN=$(printf '%s\n' "$SCAN" | sed -E "s/(-t[[:blank:]]*|--target-directory[=[:blank:]][[:blank:]]*)(${TOKEN}+)([^;&|<>()]*)/\\3 \\2/g")

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
  done < <(write_patterns "$target")
}
check_writes "$SCAN" "$CREDS_TARGET"
check_writes "$SCAFFOLD_FREE" "$ENV_TARGET"

exit 0
