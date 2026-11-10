#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 scripts/build.py --check
python3 scripts/tests/test_codex_compat.py
for p in plugins/*/; do claude plugin validate "$p" >/dev/null; done
claude plugin validate . >/dev/null
bash plugins/agents-core/hooks/tests/test-hooks.sh
python3 scripts/tests/test_sync_todo_ledgers.py
python3 scripts/tests/test_task_brief.py
python3 scripts/tests/test_task_run.py
python3 scripts/tests/test_task_size.py
bash scripts/tests/test-at.sh
bash scripts/tests/test-codex-live.sh
# release.sh runs this suite inside its throwaway copy; do not recurse into it
if [[ -n "${AT_RELEASE_TEST:-}" ]]; then
  echo "SKIP: test-release (already inside the release test)"
else
  # The full release test cuts two releases of a copy of this tree, each with its own suite run:
  # most of this script's time. It runs when a file it covers differs from HEAD, and at every real
  # release (release.sh sets AT_RELEASE_TEST_FULL=1); otherwise only the dry-run half runs.
  RELEASE_FILES=(scripts/release.sh scripts/build.py scripts/tests/test-release.sh scripts/tests/run-all.sh)
  if [[ -z "${AT_RELEASE_TEST_FULL:-}" ]] && git diff --quiet HEAD -- "${RELEASE_FILES[@]}"; then
    export AT_RELEASE_TEST_FULL=0
  fi
  bash scripts/tests/test-release.sh
fi
echo "run-all: ok"
