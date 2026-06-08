#!/bin/bash

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

if echo "$FILE_PATH" | grep -qE '(^|/)\.creds(/|$)'; then
  echo "BLOCKED: refused to write to sensitive path '$FILE_PATH' (matched: (^|/)\\.creds(/|$)). Protected: .env, .creds/, .git/, credentials, secrets, private keys, .pem/.key, .ssh/, .aws/. If this is intentional, ask the user to override." >&2
  exit 2
fi

# Example/sample/template scaffolds are committed, non-secret docs by convention
# (e.g. .env.example, project.env.template). Never block these — a real secret
# file never carries one of these suffixes.
case "$FILE_PATH" in
  *.example|*.sample|*.template) exit 0 ;;
esac

SENSITIVE_PATTERNS=(
  '\.env$'
  '\.env\..+'
  '\.git/'
  'credentials'
  'secrets'
  'private.*key'
  '\.pem$'
  '\.key$'
  '\.ssh/'
  '\.aws/'
)

for pattern in "${SENSITIVE_PATTERNS[@]}"; do
  if echo "$FILE_PATH" | grep -qE "$pattern"; then
    echo "BLOCKED: refused to write to sensitive path '$FILE_PATH' (matched: $pattern). Protected: .env, .creds/, .git/, credentials, secrets, private keys, .pem/.key, .ssh/, .aws/. If this is intentional, ask the user to override." >&2
    exit 2
  fi
done

exit 0
