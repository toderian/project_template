#!/usr/bin/env bash
# E7: the scripted driver with marks. `at task run` (the real claude harness, not run_claude) on a
# three-phase `Execution: unattended` task: phase 2 cannot pass its check, phase 3 says `After: 1`.
# Passes when phase 3 is committed, phase 2 and nothing else is `parked`, and the exit code is 4.
# Spec: docs/specs/2026-11-26-unattended-run-hardening-plan.md, "End-to-end tests".
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

STATE_REL=docs/tasks_manager/_runs/T-001/state.md
DRIVER_BUDGET_USD="${DRIVER_BUDGET_USD:-0.5}"   # per dispatch; a whole scenario stays far below 10 USD
DRIVER_TIMEOUT="${DRIVER_TIMEOUT:-240}"         # per dispatch, seconds

# write_task <repo>: task T-001 with three one-file phases; phase 3 waits only for phase 1.
write_task() {
  cat > "$1/docs/tasks_manager/_todos/T-001-F_marks.md" <<'TASK'
| Field     | Value               |
|-----------|---------------------|
| Task ID   | T-001               |
| Type      | F                   |
| Area      | global              |
| Status    | open                |
| Priority  | medium              |
| Created   | 2026-11-26T09:00:00 |
| Updated   | 2026-11-26T09:00:00 |
| Execution | unattended          |
| Source    | add-task            |

## Driver marks

### Brief

Three tiny phases that each create one text file in the repository root.

### Phases

#### Phase 1: one

- [ ] Create `one.txt` containing the single line `one`.

#### Phase 2: two

- [ ] Create `two.txt` containing the single line `two`.

#### Phase 3: three

After: 1

- [ ] Create `three.txt` containing the single line `three`.

### Acceptance criteria

- [ ] The three files exist.

### Related tests

- none

### Follow-ups

- none

---

## Execution log

Append-only record.
TASK
}

REPO=$(make_repo marks) || exit 1
cd "${REPO}"
write_task "${REPO}"
"${AT}" ledger sync >/dev/null 2>&1 || fail "at ledger sync"
git add -A && git commit -qm "chore: T-001 task" || fail "commit the task"

RC=0
"${AT}" task run T-001 --harness claude --model "${LIVE_MODEL}" --strong-model "${LIVE_MODEL}" \
  --mode small --max-rounds 1 --budget-usd "${DRIVER_BUDGET_USD}" --timeout "${DRIVER_TIMEOUT}" \
  --check 'test ! -f two.txt' > "${SCRATCH}/run.out" 2> "${SCRATCH}/run.err" || RC=$?
tail -n 5 "${SCRATCH}/run.out" "${SCRATCH}/run.err" >&2 || true

[[ ${RC} -eq 4 ]] || fail "exit code ${RC}, expected 4 (run output: ${SCRATCH}/run.out, ${SCRATCH}/run.err)"
S="${REPO}/${STATE_REL}"
[[ "$(row_status "${S}" 1)" == committed ]] || fail "row 1 is $(row_status "${S}" 1), expected committed"
[[ "$(row_status "${S}" 2)" == parked ]] || fail "row 2 is $(row_status "${S}" 2), expected parked"
[[ "$(row_status "${S}" 3)" == committed ]] || fail "row 3 is $(row_status "${S}" 3), expected committed"
[[ "$(grep -c '^| [0-9]* | parked ' "${S}")" -eq 1 ]] || fail "more than one parked row"
grep -q 'T-001 phase 3' <<<"$(git log --format=%s)" || fail "no commit for phase 3"
[[ -f three.txt && ! -f two.txt ]] || fail "three.txt missing or two.txt present in the tree"
[[ -z "$(git status --porcelain)" ]] || fail "the tree is not clean: $(git status --porcelain | head -3)"
echo "E7: ok (exit 4; rows: $(for n in 1 2 3; do row_status "${S}" "${n}"; done | tr '\n' ' '))"
