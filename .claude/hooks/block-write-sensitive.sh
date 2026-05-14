#!/bin/bash

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

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
    echo "BLOCKED: refused to write to sensitive path '$FILE_PATH' (matched: $pattern). Protected: .env, .git/, credentials, secrets, private keys, .pem/.key, .ssh/, .aws/. If this is intentional, ask the user to override." >&2
    exit 2
  fi
done

exit 0
