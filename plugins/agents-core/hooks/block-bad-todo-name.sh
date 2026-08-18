#!/bin/bash

command -v jq >/dev/null || { echo "hook requires jq; install jq" >&2; exit 2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/paths.sh
source "${SCRIPT_DIR}/lib/paths.sh"

INPUT=$(cat)

# check_path <file_path>
# Returns 0 (allowed) or 2 (blocked); writes the blocking reason to stderr.
check_path() {
  local FILE_PATH="$1"

  # Determine which layer (if any) this path belongs to, and pick the matching rule.
  local LAYER=""
  case "${FILE_PATH}" in
    */docs/tasks_manager/_todos/*|docs/tasks_manager/_todos/*|*/docs/tasks_manager/_todos_archived/*|docs/tasks_manager/_todos_archived/*) LAYER="todo" ;;
    */docs/tasks_manager/_inbox/*|docs/tasks_manager/_inbox/*|*/docs/tasks_manager/_inbox_archived/*|docs/tasks_manager/_inbox_archived/*) LAYER="inbox" ;;
    *) return 0 ;;
  esac

  local BASENAME
  BASENAME=$(basename "${FILE_PATH}")

  if [ "${BASENAME}" = ".gitkeep" ]; then
    return 0
  fi

  if [ "${LAYER}" = "todo" ]; then
    # <PREFIX>-<NNN>-<TYPE>_<short-description>.md
    # TYPE in F/D/C/R, NNN >= 3 digits, PREFIX uppercase alphanumeric starting with a letter.
    if ! echo "${BASENAME}" | grep -qE '^[A-Z][A-Z0-9]*-[0-9]{3,}-[FDCR]_[a-z0-9]([a-z0-9-]*[a-z0-9])?\.md$'; then
      echo "BLOCKED: task filename '${BASENAME}' does not match the required convention." >&2
      echo "Expected: <PREFIX>-<NNN>-<TYPE>_<short-description>.md" >&2
      echo "Example:  AUTH-001-F_login-session.md" >&2
      echo "Rules: uppercase area prefix, zero-padded id, type F|D|C|R, underscore, lowercase hyphenated description, .md." >&2
      echo "See the task-ledger skill: references/todo-convention.md." >&2
      return 2
    fi
    local PREFIX="${BASENAME%%-*}"
    if [ "${PREFIX}" = "I" ]; then
      echo "BLOCKED: task prefix 'I' is reserved for inbox IDs." >&2
      echo "Use an area prefix from docs/tasks_manager/_areas.md, or T for global/default work." >&2
      return 2
    fi
  else
    # I-<NNN>_<short-description>.md
    if ! echo "${BASENAME}" | grep -qE '^I-[0-9]{3,}_[a-z0-9]([a-z0-9-]*[a-z0-9])?\.md$'; then
      echo "BLOCKED: inbox filename '${BASENAME}' does not match the required convention." >&2
      echo "Expected: I-<NNN>_<short-description>.md" >&2
      echo "Example:  I-007_dark-mode-toggle.md" >&2
      echo "Rules: I- + zero-padded id, underscore, lowercase hyphenated description, .md." >&2
      echo "See the task-ledger skill: references/inbox-convention.md." >&2
      return 2
    fi
  fi

  local DESCRIPTION="${BASENAME#*_}"
  DESCRIPTION="${DESCRIPTION%.md}"
  if [ "${#DESCRIPTION}" -ge 50 ]; then
    echo "BLOCKED: description '${DESCRIPTION}' is ${#DESCRIPTION} chars; must be under 50." >&2
    echo "See the task-ledger skill: references/todo-convention.md (or inbox-convention.md)." >&2
    return 2
  fi

  return 0
}

while IFS= read -r FILE_PATH; do
  [ -z "${FILE_PATH}" ] && continue
  if ! check_path "${FILE_PATH}"; then
    exit 2
  fi
done < <(hook_target_paths "${INPUT}")

exit 0
