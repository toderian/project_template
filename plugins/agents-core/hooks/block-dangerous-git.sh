#!/bin/bash

command -v jq >/dev/null || { echo "hook requires jq; install jq" >&2; exit 2; }

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command')

GIT_COMMAND_PREFIX='(^|[;&|[:space:]])["'"'"']?([^[:space:]"'"'"']*/)?git["'"'"']?([[:space:]]+(-C[[:space:]]+[^[:space:]]+|-c[[:space:]]+[^[:space:]]+|--git-dir(=|[[:space:]])[^[:space:]]+|--work-tree(=|[[:space:]])[^[:space:]]+|--[[:alnum:]-]+(=[^[:space:]]+)?))*[[:space:]]+'
CREDS_PATH_PATTERN='(^|[[:space:]"'"'"'])([^[:space:]"'"'"']*/)?\.creds([/\\]|[[:space:]"'"'"']|$)'
VENV_PATH_PATTERN='(^|[[:space:]"'"'"'])([^[:space:]"'"'"']*/)?\.venv([/\\]|[[:space:]"'"'"']|$)'
FORCE_ADD_PATTERN='(^|[[:space:]])(--force|-[^[:space:]]*f[^[:space:]]*)([[:space:]]|$)'
BROAD_ADD_PATTERN='(^|[[:space:]])(--[[:space:]]+)?(-A|--all|\.|\.\/|:\/)([[:space:]]|$)'
LOCAL_ONLY_STAGED_PATTERN='(^|/)(\.creds|\.venv)(/|$)'

if echo "$COMMAND" | grep -qE "${GIT_COMMAND_PREFIX}add([[:space:]]|$)"; then
  if echo "$COMMAND" | grep -qE "$CREDS_PATH_PATTERN"; then
    echo "BLOCKED: refused to stage .creds/ paths. Credentials must remain uncommitted." >&2
    exit 2
  fi
  if echo "$COMMAND" | grep -qE "$VENV_PATH_PATTERN"; then
    echo "BLOCKED: refused to stage .venv/ paths. Virtual environments must remain uncommitted." >&2
    exit 2
  fi
  if echo "$COMMAND" | grep -qE "$FORCE_ADD_PATTERN"; then
    echo "BLOCKED: refused to run forced git add. Forced staging can bypass .gitignore and commit local-only files." >&2
    exit 2
  fi
  if echo "$COMMAND" | grep -qE "$BROAD_ADD_PATTERN" && git ls-files | grep -qE "$LOCAL_ONLY_STAGED_PATTERN"; then
    echo "BLOCKED: refused broad git add while local-only .creds/ or .venv/ paths are tracked. Remove tracked local-only paths first." >&2
    exit 2
  fi
fi

# Reuse the boundary-anchored GIT_COMMAND_PREFIX (defined above, already used
# for the add/commit guards) instead of bare substrings, so quoted text (e.g.
# a commit message mentioning "git push") and dotfile arguments (e.g.
# `git checkout .gitignore`) don't false-positive on these patterns.
DANGEROUS_PATTERNS=(
  "${GIT_COMMAND_PREFIX}push([[:space:]]|$)"
  "${GIT_COMMAND_PREFIX}reset[[:space:]]+[^;&|]*--hard([[:space:]]|$)"
  "${GIT_COMMAND_PREFIX}clean[[:space:]]+-[a-zA-Z]*f[a-zA-Z]*([[:space:]]|$)"
  "${GIT_COMMAND_PREFIX}branch[[:space:]]+[^;&|]*-D([[:space:]]|$)"
  "${GIT_COMMAND_PREFIX}checkout([[:space:]]+--)?[[:space:]]+\.([[:space:]]|$)"
  "${GIT_COMMAND_PREFIX}restore([[:space:]]+--)?[[:space:]]+\.([[:space:]]|$)"
)

# Strip quoted spans before matching DANGEROUS_PATTERNS so free text inside
# quotes (e.g. a commit message like "Reminder to git push before EOD") can't
# false-positive. Tradeoff: a dangerous command hidden inside quotes (e.g.
# passed to `bash -c "..."`) is not caught — acceptable for an accident
# guardrail; this hook is not a security boundary. Only this matching uses the
# stripped text; the add/commit guards above/below inspect the full command.
STRIPPED_COMMAND=$(printf '%s' "$COMMAND" | sed -e 's/"[^"]*"//g' -e "s/'[^']*'//g")

for pattern in "${DANGEROUS_PATTERNS[@]}"; do
  if echo "$STRIPPED_COMMAND" | grep -qE "$pattern"; then
    echo "BLOCKED: '$COMMAND' matches dangerous pattern '$pattern'. The user has prevented you from doing this." >&2
    exit 2
  fi
done

if echo "$COMMAND" | grep -qE "${GIT_COMMAND_PREFIX}commit([[:space:]]|$)"; then
  if git diff --cached --name-only --diff-filter=ACMR | grep -qE "$LOCAL_ONLY_STAGED_PATTERN"; then
    echo "BLOCKED: refused to commit staged .creds/ or .venv/ paths. Local-only files must remain uncommitted." >&2
    exit 2
  fi
fi

exit 0
