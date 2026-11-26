#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 scripts/build.py --check
# Inside the release test (test-release.sh releases a throwaway copy of this tree) the suite has
# already run once on the same files, in the run that started the test. A release changes only the
# version keys, which build.py --check covers, so the nested releases stop here: one suite pass
# per release, not three.
if [[ -n "${AT_RELEASE_TEST:-}" ]]; then
  echo "run-all: ok (release test: build check only)"
  exit 0
fi
# The steps below do not share state (each works in its own temporary directory), so they run side
# by side: the suite takes as long as its slowest step, not the sum. Output is printed per step, in
# this order, when all have ended. AT_TEST_SERIAL=1 runs them one after another.
# test_task_run.py is the slowest file and is listed per test class; the check below fails the suite
# when a class is added there and not here.
RUN_CLASSES="$(grep -oE '^class [A-Za-z0-9_]+' scripts/tests/test_task_run.py | cut -d' ' -f2 | sort | tr '\n' ' ')"
if [[ "$RUN_CLASSES" != "FixWave Lanes Marks TaskRun " ]]; then
  echo "run-all: test_task_run.py classes are '$RUN_CLASSES': update STEPS in run-all.sh" >&2
  exit 1
fi
STEPS=(
  "python3 scripts/tests/test_codex_compat.py"
  "for p in plugins/*/; do claude plugin validate \"\$p\" >/dev/null || exit 1; done; claude plugin validate . >/dev/null"
  "bash plugins/agents-core/hooks/tests/test-hooks.sh"
  "python3 scripts/tests/test_sync_todo_ledgers.py"
  "python3 scripts/tests/test_task_brief.py"
  "python3 scripts/tests/test_task_run.py TaskRun"
  "python3 scripts/tests/test_task_run.py Marks"
  "python3 scripts/tests/test_task_run.py Lanes"
  "python3 scripts/tests/test_task_run.py FixWave"
  "python3 scripts/tests/test_run_watch.py"
  "python3 scripts/tests/test_lease.py"
  "python3 scripts/tests/test_sup_state.py"
  "python3 scripts/tests/test_sup_event.py"
  "python3 scripts/tests/test_sup_land.py"
  "python3 scripts/tests/test_sup_guard.py"
  "python3 scripts/tests/test_sup_ask.py"
  "python3 scripts/tests/test_sup_digest.py"
  "python3 scripts/tests/test_sup_tick.py"
  "python3 scripts/tests/test_sup_watch.py"
  "python3 scripts/tests/test_sup_workers.py"
  "python3 scripts/tests/test_sup_flow.py"
  "python3 scripts/tests/test_task_size.py"
  "python3 scripts/tests/test_task_report.py"
  "python3 scripts/tests/test_design_tree.py"
  "python3 scripts/tests/test_explore.py"
  "bash scripts/tests/test-at.sh"
  "bash scripts/tests/test-codex-live.sh"
)
STEP_LOGS="$(mktemp -d)"
trap 'rm -rf "$STEP_LOGS"' EXIT
STEP_PIDS=()
for i in "${!STEPS[@]}"; do
  if [[ -n "${AT_TEST_SERIAL:-}" ]]; then
    bash -c "${STEPS[$i]}"
  else
    bash -c "${STEPS[$i]}" >"$STEP_LOGS/$i.log" 2>&1 &
    STEP_PIDS[$i]=$!
  fi
done
FAILED_STEPS=0
for i in "${!STEP_PIDS[@]}"; do
  rc=0; wait "${STEP_PIDS[$i]}" || rc=$?
  cat "$STEP_LOGS/$i.log"
  if [[ "$rc" != 0 ]]; then
    echo "run-all: FAILED (exit $rc): ${STEPS[$i]}" >&2
    FAILED_STEPS=$((FAILED_STEPS + 1))
  fi
done
[[ "$FAILED_STEPS" == 0 ]]
# The full release test cuts releases of a copy of this tree and checks the rollback paths. It runs
# when a file it covers differs from HEAD, and at every real release (release.sh sets
# AT_RELEASE_TEST_FULL=1); otherwise only the dry-run half runs.
RELEASE_FILES=(scripts/release.sh scripts/build.py scripts/tests/test-release.sh scripts/tests/run-all.sh)
if [[ -z "${AT_RELEASE_TEST_FULL:-}" ]] && git diff --quiet HEAD -- "${RELEASE_FILES[@]}"; then
  export AT_RELEASE_TEST_FULL=0
fi
bash scripts/tests/test-release.sh
echo "run-all: ok"
