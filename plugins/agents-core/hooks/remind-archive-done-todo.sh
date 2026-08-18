#!/bin/bash

command -v jq >/dev/null || { echo "hook requires jq; install jq" >&2; exit 2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/paths.sh
source "${SCRIPT_DIR}/lib/paths.sh"

INPUT=$(cat)

# check_path <file_path>
# Returns 0 (silent) or 2 (reminder emitted on stderr).
check_path() {
  local FILE_PATH="$1"

  # Match the active dir of each layer; pick the layer's terminal statuses, archive
  # dir, and convention reference. Archived dirs are intentionally not matched.
  local LAYER ARCHIVE TERMINAL_RE CONVENTION
  case "${FILE_PATH}" in
    */docs/tasks_manager/_todos/*|docs/tasks_manager/_todos/*)
      LAYER="_todos"; ARCHIVE="_todos_archived"
      TERMINAL_RE='^(done|cancelled)$'
      CONVENTION="playbooks/conventions/todo-convention.md" ;;
    */docs/tasks_manager/_inbox/*|docs/tasks_manager/_inbox/*)
      LAYER="_inbox"; ARCHIVE="_inbox_archived"
      TERMINAL_RE='^(promoted|dropped)$'
      CONVENTION="playbooks/conventions/inbox-convention.md" ;;
    *) return 0 ;;
  esac

  if [ ! -f "${FILE_PATH}" ]; then
    return 0
  fi

  local STATUS
  STATUS=$(grep -iE '^\|[[:space:]]*Status[[:space:]]*\|' "${FILE_PATH}" \
    | head -1 \
    | awk -F'|' '{gsub(/^[[:space:]]+|[[:space:]]+$/, "", $3); print tolower($3)}')

  if echo "${STATUS}" | grep -qE "${TERMINAL_RE}"; then
    local BASENAME DIR ARCHIVE_DIR
    BASENAME=$(basename "${FILE_PATH}")
    DIR=$(dirname "${FILE_PATH}")
    ARCHIVE_DIR="${DIR%/"${LAYER}"}/${ARCHIVE}"

    if [ "${LAYER}" = "_todos" ]; then
      local missing=""
      if ! grep -qE '^##[[:space:]]+Completion harvest[[:space:]]*$' "${FILE_PATH}"; then
        missing="${missing} completion-harvest-section"
      fi
      if ! grep -qiE '^\|[[:space:]]*Resource updates[[:space:]]*\|[[:space:]]*(None|N/A|docs/resources/[^|]+)[[:space:]]*\|' "${FILE_PATH}"; then
        missing="${missing} resource-updates"
      fi
      if ! grep -qiE '^\|[[:space:]]*Area updates[[:space:]]*\|[[:space:]]*(None|N/A|docs/areas/[^|]+)[[:space:]]*\|' "${FILE_PATH}"; then
        missing="${missing} area-updates"
      fi
      if ! grep -qiE '^\|[[:space:]]*Follow-ups[[:space:]]*\|[[:space:]]*(None|N/A|I-[0-9]{3,}[^|]*)[[:space:]]*\|' "${FILE_PATH}"; then
        missing="${missing} follow-ups"
      fi
      if ! grep -qiE '^\|[[:space:]]*Notable decisions/deviations[[:space:]]*\|[[:space:]]*(None|N/A|[^|]*[[:alnum:]][^|]*)[[:space:]]*\|' "${FILE_PATH}"; then
        missing="${missing} notable-decisions"
      fi
      if ! grep -qE '^##[[:space:]]+Completion summary[[:space:]]*$' "${FILE_PATH}"; then
        missing="${missing} completion-summary"
      fi

      if [ -n "${missing}" ]; then
        echo "BLOCKED: '${BASENAME}' has Status: ${STATUS} but is missing required completion archive fields:${missing}" >&2
        echo "Before archiving, complete '## Completion harvest' with docs/resources updates or None, docs/areas updates or None, follow-ups or None, notable decisions/deviations or None, plus '## Completion summary'." >&2
        echo "See playbooks/conventions/todo-convention.md." >&2
        return 2
      fi
    fi

    echo "REMINDER: '${BASENAME}' has Status: ${STATUS} but is still in ${DIR}." >&2
    echo "Per ${CONVENTION}, move it to the archive now:" >&2
    echo "  mkdir -p ${ARCHIVE_DIR} && mv ${FILE_PATH} ${ARCHIVE_DIR}/${BASENAME}" >&2
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
