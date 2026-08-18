#!/bin/bash
# Shared helper for write-side hooks (PreToolUse/PostToolUse) that need to
# know which file(s) a tool call touches.
#
# Claude sends the target path directly as tool_input.file_path (Write,
# Edit, MultiEdit). Codex's apply_patch instead carries a unified patch
# script in tool_input.command, whose "*** Add File: <path>",
# "*** Update File: <path>", "*** Delete File: <path>" and
# "*** Move to: <path>" lines each name a path the patch touches.
#
# Usage: hook_target_paths "$INPUT"
#   where INPUT is the JSON payload already captured from stdin via
#   INPUT=$(cat), following this repo's existing hook convention.
# Prints one path per line; prints nothing if no path can be determined.
# Requires jq (callers already fail closed on a missing jq before sourcing
# this file).
hook_target_paths() {
  local payload="$1"
  local file_path
  file_path=$(echo "$payload" | jq -r '.tool_input.file_path // empty')

  if [ -n "$file_path" ]; then
    printf '%s\n' "$file_path"
    return 0
  fi

  local tool_name
  tool_name=$(echo "$payload" | jq -r '.tool_name // empty')
  if [ "$tool_name" = "apply_patch" ]; then
    echo "$payload" | jq -r '.tool_input.command // empty' \
      | grep -E '^\*\*\* (Add File|Update File|Delete File|Move to): ' \
      | sed -E 's/^\*\*\* (Add File|Update File|Delete File|Move to): //'
  fi
}
