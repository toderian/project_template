#!/bin/bash
#
# Blocks obviously dangerous shell commands that aren't git-related.
# Companion to block-dangerous-git.sh. Both run as PreToolUse hooks on Bash.
# Patterns are intentionally narrow — false positives waste user attention more
# than they protect anything. Each pattern is anchored to a command-statement
# boundary (start of line, or after ; && || | $( ) so substrings inside quoted
# arguments (e.g., a commit message body) won't trigger.

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command')

# Boundary that must precede a dangerous keyword: start of string, or any of
# the shell statement separators / pipeline operators.
CB='(^|[;&|]|\$\()[[:space:]]*'

DANGEROUS_PATTERNS=(
  # Filesystem destruction
  "${CB}rm[[:blank:]]+-[a-zA-Z]*r[a-zA-Z]*f?[[:blank:]]+/[[:blank:]]*\$"
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

exit 0
