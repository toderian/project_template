#!/usr/bin/env bash
#
# Shared prerequisite guards for _base/scripts/*.sh (and callers outside
# _base/ that resolve their own repo root, e.g. skills/install-codex-skills.sh).
#
# This file is sourced, not executed, and declares no side effects beyond
# its two functions. Keep it dependency-free (no python3/jq calls) so it can
# run before any other prerequisite is confirmed present.
#
# Usage (source after `set -euo pipefail`, before using the guarded feature):
#   source "${SCRIPT_DIR}/lib/require.sh"     # or "${REPO_ROOT}/_base/scripts/lib/require.sh"
#   require_bash4
#   require_cmd python3 "used to parse .claude-plugin/plugin.json"

# require_bash4: die with a clear message if running under bash < 4
# (e.g. macOS's shipped /bin/bash 3.2, which lacks declare -A / mapfile).
require_bash4() {
  if (( BASH_VERSINFO[0] < 4 )); then
    echo "error: bash >= 4 is required (found ${BASH_VERSION:-unknown}); on macOS, install a" \
      "newer bash (e.g. 'brew install bash') and re-run with it" >&2
    exit 2
  fi
}

# require_cmd <name> [hint]: die with a clear message if <name> is not on PATH.
require_cmd() {
  local cmd="$1" hint="${2:-}"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "error: required command '${cmd}' not found on PATH${hint:+ (${hint})}" >&2
    exit 2
  fi
}
