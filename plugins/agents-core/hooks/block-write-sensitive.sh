#!/bin/bash

command -v jq >/dev/null || { echo "hook requires jq; install jq" >&2; exit 2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/paths.sh
source "${SCRIPT_DIR}/lib/paths.sh"

INPUT=$(cat)

# Segment-anchored: a sensitive word only blocks when it is (or starts) a
# whole path segment — "docs/secrets-rotation.md" is fine, "secrets/x" or
# "config/credentials/prod.json" is not.
SEGMENT_PATTERN='(^|/)(\.creds|\.env(\..*)?|secrets?|credentials?)(/|$)'

# Whole-basename patterns for well-known private-key file shapes.
BASENAME_PATTERN='^(id_rsa|id_ed25519|.*\.pem|.*\.key|.*\.p12|.*\.agekey)$'

OTHER_SENSITIVE_PATTERNS=(
  '\.git/'
  '\.ssh/'
  '\.aws/'
)

PROTECTED_SUMMARY="Protected: .env, .creds/, .git/, credentials, secrets, private keys, .pem/.key, .ssh/, .aws/. If this is intentional, ask the user to override."

# Example/sample/template scaffolds are committed, non-secret docs by
# convention (e.g. .env.example, project.env.template). Never block these —
# a real secret file never carries one of these suffixes.
is_allowlisted() {
  case "$1" in
    *.example|*.sample|*.template) return 0 ;;
    *) return 1 ;;
  esac
}

while IFS= read -r FILE_PATH; do
  [ -z "${FILE_PATH}" ] && continue

  if is_allowlisted "${FILE_PATH}"; then
    continue
  fi

  if echo "${FILE_PATH}" | grep -qE "${SEGMENT_PATTERN}"; then
    echo "BLOCKED: refused to write to sensitive path '${FILE_PATH}' (matched: ${SEGMENT_PATTERN}). ${PROTECTED_SUMMARY}" >&2
    exit 2
  fi

  BASENAME=$(basename "${FILE_PATH}")
  if echo "${BASENAME}" | grep -qE "${BASENAME_PATTERN}"; then
    echo "BLOCKED: refused to write to sensitive path '${FILE_PATH}' (matched basename: ${BASENAME_PATTERN}). ${PROTECTED_SUMMARY}" >&2
    exit 2
  fi

  for pattern in "${OTHER_SENSITIVE_PATTERNS[@]}"; do
    if echo "${FILE_PATH}" | grep -qE "${pattern}"; then
      echo "BLOCKED: refused to write to sensitive path '${FILE_PATH}' (matched: ${pattern}). ${PROTECTED_SUMMARY}" >&2
      exit 2
    fi
  done
done < <(hook_target_paths "${INPUT}")

exit 0
