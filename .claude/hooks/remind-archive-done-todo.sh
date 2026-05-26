#!/bin/bash

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# Match the active dir of each layer; pick the layer's terminal statuses, archive
# dir, and convention reference. Archived dirs are intentionally not matched.
case "$FILE_PATH" in
  */docs/tasks_manager/_todos/*|docs/tasks_manager/_todos/*)
    LAYER="_todos"; ARCHIVE="_todos_archived"
    TERMINAL_RE='^(done|cancelled)$'
    CONVENTION="playbooks/conventions/todo-convention.md" ;;
  */docs/tasks_manager/_inbox/*|docs/tasks_manager/_inbox/*)
    LAYER="_inbox"; ARCHIVE="_inbox_archived"
    TERMINAL_RE='^(promoted|dropped)$'
    CONVENTION="playbooks/conventions/inbox-convention.md" ;;
  *) exit 0 ;;
esac

if [ ! -f "$FILE_PATH" ]; then
  exit 0
fi

STATUS=$(grep -iE '^\|[[:space:]]*Status[[:space:]]*\|' "$FILE_PATH" \
  | head -1 \
  | awk -F'|' '{gsub(/^[[:space:]]+|[[:space:]]+$/, "", $3); print tolower($3)}')

if echo "$STATUS" | grep -qE "$TERMINAL_RE"; then
  BASENAME=$(basename "$FILE_PATH")
  DIR=$(dirname "$FILE_PATH")
  ARCHIVE_DIR="${DIR%/$LAYER}/$ARCHIVE"

  if [ "$LAYER" = "_todos" ]; then
    missing=""
    if ! grep -qE '^##[[:space:]]+Completion harvest[[:space:]]*$' "$FILE_PATH"; then
      missing="${missing} completion-harvest-section"
    fi
    if ! grep -qiE '^\|[[:space:]]*Resource updates[[:space:]]*\|[[:space:]]*(None|N/A|docs/resources/[^|]+)[[:space:]]*\|' "$FILE_PATH"; then
      missing="${missing} resource-updates"
    fi
    if ! grep -qiE '^\|[[:space:]]*Area updates[[:space:]]*\|[[:space:]]*(None|N/A|docs/areas/[^|]+)[[:space:]]*\|' "$FILE_PATH"; then
      missing="${missing} area-updates"
    fi
    if ! grep -qiE '^\|[[:space:]]*Follow-ups[[:space:]]*\|[[:space:]]*(None|N/A|I-[0-9]{3,}[^|]*)[[:space:]]*\|' "$FILE_PATH"; then
      missing="${missing} follow-ups"
    fi
    if ! grep -qiE '^\|[[:space:]]*Notable decisions/deviations[[:space:]]*\|[[:space:]]*(None|N/A|[^|]*[[:alnum:]][^|]*)[[:space:]]*\|' "$FILE_PATH"; then
      missing="${missing} notable-decisions"
    fi
    if ! grep -qE '^##[[:space:]]+Completion summary[[:space:]]*$' "$FILE_PATH"; then
      missing="${missing} completion-summary"
    fi

    if [ -n "$missing" ]; then
      echo "BLOCKED: '$BASENAME' has Status: $STATUS but is missing required completion archive fields:$missing" >&2
      echo "Before archiving, complete '## Completion harvest' with docs/resources updates or None, docs/areas updates or None, follow-ups or None, notable decisions/deviations or None, plus '## Completion summary'." >&2
      echo "See playbooks/conventions/todo-convention.md." >&2
      exit 2
    fi
  fi

  echo "REMINDER: '$BASENAME' has Status: $STATUS but is still in $DIR." >&2
  echo "Per $CONVENTION, move it to the archive now:" >&2
  echo "  mkdir -p $ARCHIVE_DIR && mv $FILE_PATH $ARCHIVE_DIR/$BASENAME" >&2
  exit 2
fi

exit 0
