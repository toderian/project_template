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
# tools; this is the same guardrail for the common shell forms: a redirect,
# tee, the destination of cp/mv/install, and sed -i. Reading stays allowed
# (`cat .env`, `cp .env /tmp/x`). It stops the accidental write, not a
# determined one.
Q="[\"']?"
TOKEN="[^[:space:];&|<>\"']"
NAME="[^[:space:];&|<>\"'/]"
END="${Q}([[:space:];&|)]|\$)"
CREDS_TARGET="(${TOKEN}*/)?\\.creds(/${TOKEN}*)?"
# The same .env files as block-write-sensitive.sh: .env, .env.<x>, .envrc, <name>.env.
ENV_TARGET="(${TOKEN}*/)?(\\.env(\\.${NAME}*)?|\\.envrc|${NAME}+\\.env)"

# write_patterns <target regex>: one pattern per line. `>|` is the clobber
# redirect; a cp/mv/install destination may be followed by its own redirect.
write_patterns() {
  printf '%s\n' \
    ">[>|]?[[:blank:]]*${Q}$1${END}" \
    "${CB}tee[[:blank:]]+([^;&|]*[[:blank:]])?${Q}$1${END}" \
    "${CB}(cp|mv|install)[[:blank:]]+[^;&|]*[[:blank:]]${Q}$1${Q}[[:blank:]]*([;&|)]|\$|[0-9&]*>)" \
    "${CB}sed[[:blank:]]+([^;&|]*[[:blank:]])?-i[^;&|]*[[:blank:]]${Q}$1${END}"
}

# Text a command only carries is not a write: a commit message or echo string
# that mentions `> .env`, or a heredoc body.
# 1. Drop heredoc bodies. The line that opens a heredoc stays, with its own
#    redirect. `<<` inside quotes or `$((...))` does not open one.
# 2. Over the whole command (a quoted message may span lines): unquote a quoted
#    word with no whitespace or shell operator in it (`cp x ".env"` is still a
#    write), then blank every other quoted string.
SQ="'"
NL=$'\001'
SCAN=$(printf '%s\n' "$COMMAND" | awk '
  skip { line = $0; sub(/^\t+/, "", line); if (line == tag) skip = 0; next }
  { print
    if (match($0, /<<-?[ \t]*["\047]?[A-Za-z_][A-Za-z0-9_]*/) && substr($0, RSTART + 2, 1) != "<" \
        && (RSTART == 1 || substr($0, RSTART - 1, 1) != "<")) {
      before = substr($0, 1, RSTART - 1)
      dq = gsub(/"/, "&", before); sq = gsub(/\047/, "&", before)
      if (dq % 2 == 0 && sq % 2 == 0 && before !~ /\$\(\([^)]*$/) {
        tag = substr($0, RSTART, RLENGTH); sub(/^<<-?[ \t]*["\047]?/, "", tag); skip = 1
      }
    } }' \
  | tr '\n' "$NL" \
  | sed -E -e "s/\"([^\"[:space:]${NL}<>|;&]*)\"/\\1/g" -e "s/${SQ}([^${SQ}[:space:]${NL}<>|;&]*)${SQ}/\\1/g" \
           -e "s/\"[^\"]*\"/\"\"/g" -e "s/${SQ}[^${SQ}]*${SQ}/${SQ}${SQ}/g" \
  | tr "$NL" '\n')

# .env.example, .env.sample and .env.template are committed scaffolds: drop
# those words before the .env check. Nothing under .creds/ is a scaffold, so
# that check reads the command as scanned.
SCAFFOLD_FREE=$(printf '%s\n' "$SCAN" | sed -E "s/${TOKEN}*\\.(example|sample|template)(${Q}([[:space:];&|)]|\$))/\\2/g")

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
