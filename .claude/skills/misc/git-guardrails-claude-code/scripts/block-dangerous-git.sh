#!/bin/bash

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command')

GIT_COMMAND_PREFIX='(^|[;&|[:space:]])["'"'"']?([^[:space:]"'"'"']*/)?git["'"'"']?([[:space:]]+(-C[[:space:]]+[^[:space:]]+|-c[[:space:]]+[^[:space:]]+|--git-dir(=|[[:space:]])[^[:space:]]+|--work-tree(=|[[:space:]])[^[:space:]]+|--[[:alnum:]-]+(=[^[:space:]]+)?))*[[:space:]]+'
CREDS_PATH_PATTERN='(^|[[:space:]"'"'"'])([^[:space:]"'"'"']*/)?\.creds([/\\]|[[:space:]"'"'"']|$)'
FORCE_ADD_PATTERN='(^|[[:space:]])(--force|-[^[:space:]]*f[^[:space:]]*)([[:space:]]|$)'
BROAD_ADD_PATTERN='(^|[[:space:]])(--[[:space:]]+)?(-A|--all|\.|\.\/|:\/)([[:space:]]|$)'

if echo "$COMMAND" | grep -qE "${GIT_COMMAND_PREFIX}add([[:space:]]|$)"; then
  if echo "$COMMAND" | grep -qE "$CREDS_PATH_PATTERN"; then
    echo "BLOCKED: refused to stage .creds/ paths. Credentials must remain uncommitted." >&2
    exit 2
  fi
  if echo "$COMMAND" | grep -qE "$FORCE_ADD_PATTERN"; then
    echo "BLOCKED: refused to run forced git add. Forced staging can bypass .gitignore and commit local-only credentials." >&2
    exit 2
  fi
  if echo "$COMMAND" | grep -qE "$BROAD_ADD_PATTERN" && git ls-files -- .creds | grep -q .; then
    echo "BLOCKED: refused broad git add while .creds/ paths are tracked. Remove tracked credentials first." >&2
    exit 2
  fi
fi

DANGEROUS_PATTERNS=(
  "git push"
  "git reset --hard"
  "git clean -fd"
  "git clean -f"
  "git branch -D"
  "git checkout \."
  "git restore \."
  "push --force"
  "reset --hard"
)

for pattern in "${DANGEROUS_PATTERNS[@]}"; do
  if echo "$COMMAND" | grep -qE "$pattern"; then
    echo "BLOCKED: '$COMMAND' matches dangerous pattern '$pattern'. The user has prevented you from doing this." >&2
    exit 2
  fi
done

if echo "$COMMAND" | grep -qE "${GIT_COMMAND_PREFIX}commit([[:space:]]|$)"; then
  if git diff --cached --name-only --diff-filter=ACMR | grep -qE '(^|/)\.creds(/|$)'; then
    echo "BLOCKED: refused to commit staged .creds/ paths. Credentials must remain uncommitted." >&2
    exit 2
  fi
fi

exit 0
