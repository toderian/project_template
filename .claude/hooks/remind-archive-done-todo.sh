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
  echo "REMINDER: '$BASENAME' has Status: $STATUS but is still in $DIR." >&2
  echo "Per $CONVENTION, move it to the archive now:" >&2
  echo "  mkdir -p $ARCHIVE_DIR && mv $FILE_PATH $ARCHIVE_DIR/$BASENAME" >&2
  exit 2
fi

exit 0
