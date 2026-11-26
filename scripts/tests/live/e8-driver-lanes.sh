#!/usr/bin/env bash
# E8: the scripted driver with lanes. `at task run --lanes 2` (the real claude harness, not
# run_claude) on an `Execution: unattended` task with two independent phases, each with its own
# `Files:` fence. Passes when both phase commits reach the integration branch as two lane merges with
# one wave review, and no lane worktree or branch is left. Variant: the two phases also both replace the same line of shared.txt, which
# their fences do not name; passes when one lane is parked (its worktree kept), the other is
# committed, no merge is half done and the tree is clean.
# Spec: docs/specs/2026-11-26-unattended-run-hardening-plan.md, "End-to-end tests".
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

STATE_REL=docs/tasks_manager/_runs/T-001/state.md
DRIVER_BUDGET_USD="${DRIVER_BUDGET_USD:-0.5}"   # per dispatch; a whole scenario stays far below 10 USD
DRIVER_TIMEOUT="${DRIVER_TIMEOUT:-240}"         # per dispatch, seconds

# write_task <repo> <phase 1 text> <phase 2 text>: task T-001, two phases with no `After:` between them.
write_task() {
  cat > "$1/docs/tasks_manager/_todos/T-001-F_lanes.md" <<TASK
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

## Driver lanes

### Brief

Two tiny phases that can run side by side.

### Phases

#### Phase 1: first

After: none
Files: one.txt

- [ ] $2

#### Phase 2: second

After: none
Files: two.txt

- [ ] $3

### Acceptance criteria

- [ ] Both phases are done.

### Related tests

- none

### Follow-ups

- none

---

## Execution log

Append-only record.
TASK
}

# lanes_repo <name> <phase 1 text> <phase 2 text>: a committed repo with the task and a shared.txt.
lanes_repo() {
  local repo
  repo=$(make_repo "$1") || fail "make_repo $1"
  ( cd "${repo}" && echo base > shared.txt && write_task "${repo}" "$2" "$3" \
    && "${AT}" ledger sync >/dev/null 2>&1 && git add -A && git commit -qm "chore: T-001 task" ) || fail "prepare $1"
  echo "${repo}"
}

# drive <repo> <label>: `at task run --lanes 2`; sets RC.
drive() {
  RC=0
  ( cd "$1" && "${AT}" task run T-001 --lanes 2 --harness claude --model "${LIVE_MODEL}" --strong-model "${LIVE_MODEL}" \
      --mode small --max-rounds 1 --no-final-review --budget-usd "${DRIVER_BUDGET_USD}" --timeout "${DRIVER_TIMEOUT}" \
      > "${SCRATCH}/$2.out" 2> "${SCRATCH}/$2.err" ) || RC=$?
  tail -n 4 "${SCRATCH}/$2.out" "${SCRATCH}/$2.err" >&2 || true
}

# --- main: two independent files -----------------------------------------------------------------
REPO=$(lanes_repo main "Create \`one.txt\` containing the single line \`one\`." "Create \`two.txt\` containing the single line \`two\`.") || exit 1
drive "${REPO}" main
cd "${REPO}"
[[ ${RC} -eq 0 ]] || fail "exit code ${RC}, expected 0 (output: ${SCRATCH}/main.out, ${SCRATCH}/main.err)"
grep -q 'T-001 phase 1' <<<"$(git log --format=%s)" || fail "no commit for phase 1 on the integration branch"
grep -q 'T-001 phase 2' <<<"$(git log --format=%s)" || fail "no commit for phase 2 on the integration branch"
[[ -f one.txt && -f two.txt ]] || fail "one.txt or two.txt is missing"
MERGES=$(git log --merges --format=%s)
[[ "$(grep -c 'lane' <<<"${MERGES}")" -eq 2 ]] || fail "expected two lane merges, got: ${MERGES:-none} (did the phases run serially?)"
[[ -f docs/tasks_manager/_runs/T-001/wave-1/review.md ]] || fail "no wave-1 review: the phases did not run as one wave"
[[ "$(git worktree list | wc -l)" -eq 1 ]] || fail "a lane worktree is left: $(git worktree list)"
[[ -z "$(git branch --list 'at-lane/*')" ]] || fail "a lane branch is left"
[[ -z "$(git status --porcelain)" ]] || fail "the tree is not clean"
echo "E8 main: ok"

# --- variant: both phases replace the same line --------------------------------------------------
REPO=$(lanes_repo clash "Create \`one.txt\` containing the single line \`one\`, and replace the single line of \`shared.txt\` with \`alpha\`. \`shared.txt\` is a shared index that every phase updates, so the Files: line names only this phase's own file." "Create \`two.txt\` containing the single line \`two\`, and replace the single line of \`shared.txt\` with \`beta\`. \`shared.txt\` is a shared index that every phase updates, so the Files: line names only this phase's own file.") || exit 1
drive "${REPO}" clash
cd "${REPO}"
S="${REPO}/${STATE_REL}"
[[ ${RC} -eq 4 ]] || fail "variant: exit code ${RC}, expected 4 (output: ${SCRATCH}/clash.out, ${SCRATCH}/clash.err)"
[[ "$(row_status "${S}" 1)" == committed && "$(row_status "${S}" 2)" == parked ]] \
  || fail "variant: rows are $(row_status "${S}" 1)/$(row_status "${S}" 2), expected committed/parked"
[[ "$(cat shared.txt)" == alpha ]] || fail "variant: shared.txt is not alpha on the integration branch"
[[ ! -e .git/MERGE_HEAD ]] || fail "variant: a merge is left half done"
[[ -z "$(git status --porcelain)" ]] || fail "variant: the tree is not clean: $(git status --porcelain | head -3)"
[[ "$(git worktree list | wc -l)" -eq 2 ]] || fail "variant: the parked lane's worktree was not kept"
echo "E8 variant: ok"
