#!/usr/bin/env bash
# E4: the morning report. A run (real session, real commit) of a two-phase task whose state holds one
# committed row, one parked row with its question and one Decision: line; then `at task report`.
# Passes when the report file lists the recorded phase commit, the parked question under "needs you" and the
# Decision: line, is named by the commit date of base_rev, and a second run leaves it byte-identical.
# The session only does the phase-1 work; the state lines are fixture, so the check reads files, not prose.
# Spec: docs/specs/2026-11-26-unattended-run-hardening-plan.md, "End-to-end tests".
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

TM=docs/tasks_manager
REPO=$(make_repo report) || exit 1
cd "${REPO}"
BASE=$(git rev-parse --short HEAD)
DATE=$(git show -s --format=%cs "${BASE}")
mkdir -p "${TM}/_todos" "${TM}/_runs/E4-001"
cat > "${TM}/_todos/E4-001-F_report.md" <<'T'
| Field | Value |
|---|---|
| Task ID | E4-001 |
| Status | in_progress |

## Report fixture

### Phases

#### Phase 1: Line one

#### Phase 2: Line two
T
cat > "${TM}/_runs/E4-001/state.md" <<S
---
task: E4-001
task_file: ${TM}/_todos/E4-001-F_report.md
runtime: claude
base_rev: ${BASE}
current_phase: 2
updated: 2026-01-01T00:00:00
---
# Run ledger — E4-001

| Phase | Status | Attempt | Spec | Quality | Security | Open | Commit | Agent |
|---|---|---|---|---|---|---|---|---|
| 1 | pending | 1 | — | — | n/a | 0 | — | — |
| 2 | parked | 1 | — | — | n/a | 0 | — | — |

Decision: log format — chose plain text — why: inside the authorised scope — cost if wrong: one reformat
Note: parked: should phase 2 delete the old table? recommend no
S
git add -A && git commit -qm "chore: E4 task and state" || fail "commit fixture"

SID=$(new_uuid)
run_claude "${REPO}" "${SID}" "${SCRATCH}/e4.jsonl" \
  "Append the line one to a.txt and commit it with the message 'feat: E4-001 phase 1'. Touch nothing else, then reply ok."
git log --format=%s | grep -qx 'feat: E4-001 phase 1' || fail "the session did not commit phase 1"

# the report lists the commits recorded in the rows: record the one the session made
SHA=$(git rev-parse --short HEAD)
sed -i "s/^| 1 | pending | 1 | — | — | n\/a | 0 | — | — |/| 1 | committed | 1 | PASS | PASS | n\/a | 0 | ${SHA} | — |/" "${TM}/_runs/E4-001/state.md"
grep -q "| ${SHA} |" "${TM}/_runs/E4-001/state.md" || fail "could not record the phase commit in the state"

OUT="${TM}/_reports/${DATE}-E4-001.md"
"${AT}" task report E4-001 >"${SCRATCH}/report.out" 2>&1 || fail "at task report failed: $(cat "${SCRATCH}/report.out")"
[[ -f "${OUT}" ]] || fail "no report file ${OUT} (output: $(cat "${SCRATCH}/report.out"))"
grep -q 'feat: E4-001 phase 1' "${OUT}" || fail "the report lists no phase commit"
NEEDS=$(sed -n '/^## Needs you/,/^## Task/p' "${OUT}")
grep -q 'should phase 2 delete the old table' <<<"${NEEDS}" || fail "the parked question is not under needs you"
grep -q '^- Decision: log format' "${OUT}" || fail "the Decision: line is missing"
cp "${OUT}" "${SCRATCH}/first.md"
"${AT}" task report E4-001 >/dev/null || fail "second at task report failed"
cmp -s "${OUT}" "${SCRATCH}/first.md" || fail "a second run changed the report"
echo "E4: ok (${OUT})"
