#!/bin/bash

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# Determine which layer (if any) this path belongs to, and pick the matching rule.
LAYER=""
case "$FILE_PATH" in
  */docs/_todos/*|docs/_todos/*|*/docs/_todos_archived/*|docs/_todos_archived/*) LAYER="todo" ;;
  */docs/_inbox/*|docs/_inbox/*|*/docs/_inbox_archived/*|docs/_inbox_archived/*) LAYER="inbox" ;;
  *) exit 0 ;;
esac

BASENAME=$(basename "$FILE_PATH")

if [ "$BASENAME" = ".gitkeep" ]; then
  exit 0
fi

if [ "$LAYER" = "todo" ]; then
  # T-<NNN>-<TYPE>_<short-description>.md   (TYPE in F/D/C/R, NNN >= 3 digits)
  if ! echo "$BASENAME" | grep -qE '^T-[0-9]{3,}-[FDCR]_[a-z0-9]([a-z0-9-]*[a-z0-9])?\.md$'; then
    echo "BLOCKED: todo filename '$BASENAME' does not match the required convention." >&2
    echo "Expected: T-<NNN>-<TYPE>_<short-description>.md" >&2
    echo "Example:  T-042-F_dark-mode-toggle.md" >&2
    echo "Rules: T- + zero-padded id, type F|D|C|R, underscore, lowercase hyphenated description, .md." >&2
    echo "See playbooks/conventions/todo-convention.md." >&2
    exit 2
  fi
else
  # I-<NNN>_<short-description>.md
  if ! echo "$BASENAME" | grep -qE '^I-[0-9]{3,}_[a-z0-9]([a-z0-9-]*[a-z0-9])?\.md$'; then
    echo "BLOCKED: inbox filename '$BASENAME' does not match the required convention." >&2
    echo "Expected: I-<NNN>_<short-description>.md" >&2
    echo "Example:  I-007_dark-mode-toggle.md" >&2
    echo "Rules: I- + zero-padded id, underscore, lowercase hyphenated description, .md." >&2
    echo "See playbooks/conventions/inbox-convention.md." >&2
    exit 2
  fi
fi

DESCRIPTION="${BASENAME#*_}"
DESCRIPTION="${DESCRIPTION%.md}"
if [ "${#DESCRIPTION}" -ge 50 ]; then
  echo "BLOCKED: description '$DESCRIPTION' is ${#DESCRIPTION} chars; must be under 50." >&2
  echo "See playbooks/conventions/todo-convention.md (or inbox-convention.md)." >&2
  exit 2
fi

exit 0
