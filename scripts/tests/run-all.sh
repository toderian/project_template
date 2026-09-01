#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 scripts/build.py --check
python3 scripts/tests/test_codex_compat.py
for p in plugins/*/; do claude plugin validate "$p" >/dev/null; done
claude plugin validate . >/dev/null
bash plugins/agents-core/hooks/tests/test-hooks.sh
python3 scripts/tests/test_sync_todo_ledgers.py
bash scripts/tests/test-at.sh
# release.sh runs this suite inside its throwaway copy; do not recurse into it
if [[ -n "${AT_RELEASE_TEST:-}" ]]; then
  echo "SKIP: test-release (already inside the release test)"
else
  bash scripts/tests/test-release.sh
fi
echo "run-all: ok"
