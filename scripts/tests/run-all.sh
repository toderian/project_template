#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 scripts/build.py --check
for p in plugins/*/; do claude plugin validate "$p" >/dev/null; done
claude plugin validate . >/dev/null
# appended by later tasks:
# bash plugins/agents-core/hooks/tests/test-hooks.sh
# python3 scripts/tests/test_sync_todo_ledgers.py
# bash scripts/tests/test-at.sh
echo "run-all: ok"
