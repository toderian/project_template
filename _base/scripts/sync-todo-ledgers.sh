#!/usr/bin/env bash
#
# Thin shim: the task-ledger generator is now sync_todo_ledgers.py.
# This path is kept because ~20 docs and other scripts reference it.
# See sync_todo_ledgers.py for behavior, flags, and --check semantics.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/require.sh
source "${SCRIPT_DIR}/lib/require.sh"
require_cmd python3 "used to regenerate task ledgers"

exec python3 "${SCRIPT_DIR}/sync_todo_ledgers.py" "$@"
