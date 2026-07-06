#!/usr/bin/env bash
#
# DEPRECATED shim (removed next release). Skills-table generation now lives in
# _base/scripts/sync-skill-selection.py, which regenerates the table from
# playbook frontmatter as part of the same pass that writes the runtime
# wrappers and .claude-plugin/plugin.json. This forwards --check/--sync there.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "gen-skills-table.sh is deprecated; forwarding to sync-skill-selection.py (removed next release)." >&2
mode="--sync"; [[ "${1:-}" == "--check" ]] && mode="--check"
exec "${SCRIPT_DIR}/sync-skill-selection.py" "$mode"
