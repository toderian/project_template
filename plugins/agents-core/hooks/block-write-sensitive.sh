#!/bin/bash

command -v jq >/dev/null || { echo "hook requires jq; install jq" >&2; exit 2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/paths.sh
source "${SCRIPT_DIR}/lib/paths.sh"

INPUT=$(cat)

# Segment-anchored: a sensitive word only blocks when it is a whole path
# segment, alone or with a config-file extension — "docs/secrets-rotation.md"
# and "docs/secrets.md" are fine; "secrets/x", "secrets.yaml",
# "config/credentials/prod.json" and "credentials.json" are not. Any "*.env"
# file (prod.env) and .envrc count as .env files.
SECRET_EXT='json|ya?ml|toml|ini|txt|env|properties|xml|conf|cfg'
SEGMENT_PATTERN="(^|/)(\\.env(\\..*)?|\\.envrc|[^/]+\\.env|(secrets?|credentials?)(\\.(${SECRET_EXT}))?)(/|\$)"

# .creds/ is checked separately, before the example/sample/template
# allowlist below: unlike .env.example, a file under .creds/ is never a
# committed non-secret scaffold — block it unconditionally.
CREDS_PATTERN='(^|/)\.creds(/|$)'

# Whole-basename patterns for well-known private-key file shapes.
BASENAME_PATTERN='^(id_(rsa|dsa|ecdsa|ed25519)(_sk)?|.*\.pem|.*\.key|.*\.p12|.*\.pfx|.*\.agekey)$'

OTHER_SENSITIVE_PATTERNS=(
  '\.git/'
  '\.ssh/'
  '\.aws/'
)

PROTECTED_SUMMARY="Protected: .env and *.env, .creds/, .git/, credentials, secrets, private keys, .pem/.key, .ssh/, .aws/. If this is intentional, ask the user to override."

# Example/sample/template scaffolds are committed, non-secret docs by
# convention (e.g. .env.example, project.env.template). Never block these —
# a real secret file never carries one of these suffixes.
is_allowlisted() {
  case "$1" in
    *.example|*.sample|*.template) return 0 ;;
    *) return 1 ;;
  esac
}

# check_path <path> <path as the tool call gave it>: exits 2 on a protected path.
check_path() {
  local path="$1" shown="$2" pattern

  if echo "${path}" | grep -qE "${CREDS_PATTERN}"; then
    echo "BLOCKED: refused to write to sensitive path '${shown}' (matched: ${CREDS_PATTERN}). ${PROTECTED_SUMMARY}" >&2
    exit 2
  fi

  if is_allowlisted "${path}"; then
    return 0
  fi

  if echo "${path}" | grep -qE "${SEGMENT_PATTERN}"; then
    echo "BLOCKED: refused to write to sensitive path '${shown}' (matched: ${SEGMENT_PATTERN}). ${PROTECTED_SUMMARY}" >&2
    exit 2
  fi

  if basename "${path}" | grep -qE "${BASENAME_PATTERN}"; then
    echo "BLOCKED: refused to write to sensitive path '${shown}' (matched basename: ${BASENAME_PATTERN}). ${PROTECTED_SUMMARY}" >&2
    exit 2
  fi

  for pattern in "${OTHER_SENSITIVE_PATTERNS[@]}"; do
    if echo "${path}" | grep -qE "${pattern}"; then
      echo "BLOCKED: refused to write to sensitive path '${shown}' (matched: ${pattern}). ${PROTECTED_SUMMARY}" >&2
      exit 2
    fi
  done
}

# Relative paths resolve against the tool call's cwd, as the tool itself does.
HOOK_CWD=$(echo "${INPUT}" | jq -r '.cwd // empty')
[ -n "${HOOK_CWD}" ] && cd "${HOOK_CWD}" 2>/dev/null

while IFS= read -r FILE_PATH; do
  [ -z "${FILE_PATH}" ] && continue
  check_path "${FILE_PATH}" "${FILE_PATH}"

  # A symlink on the way (safe -> .creds) hides the real target: when resolving
  # links changes the path, the resolved path must pass too. Without GNU
  # realpath both come back empty and only the path as given is checked.
  RESOLVED=$(realpath -m -- "${FILE_PATH}" 2>/dev/null)
  LEXICAL=$(realpath -ms -- "${FILE_PATH}" 2>/dev/null)
  if [ -n "${RESOLVED}" ] && [ "${RESOLVED}" != "${LEXICAL}" ]; then
    check_path "${RESOLVED}" "${FILE_PATH} -> ${RESOLVED}"
  fi
done < <(hook_target_paths "${INPUT}")

exit 0
