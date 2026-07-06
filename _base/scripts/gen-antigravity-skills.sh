#!/usr/bin/env bash
#
# DEPRECATED shim (removed next release). Antigravity wrapper generation now
# lives in _base/scripts/sync-skill-selection.py, which writes all three
# wrapper trees (skills/, .claude/skills/, .agents/skills/) plus
# .claude-plugin/plugin.json and the README skills-table in one pass. Note the
# wider write surface: the old script wrote only .agents/skills/, whereas
# --sync here rewrites every generated surface. This forwards --check/--sync.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "gen-antigravity-skills.sh is deprecated; forwarding to sync-skill-selection.py, which now rewrites all wrapper trees + plugin.json + README (removed next release)." >&2
mode="--sync"; [[ "${1:-}" == "--check" ]] && mode="--check"
exec "${SCRIPT_DIR}/sync-skill-selection.py" "$mode"
