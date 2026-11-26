#!/usr/bin/env bash
# E2: a compaction does not lose the run. Three-phase state, armed session. Turn 1 does phase 1 and
# ends on a `Run: BLOCKED` line (a stop the guard allows); the session is then compacted
# (`--resume <id> -p /compact`, fact 7) and resumed with a bare "Continue." that names no task and no
# phase: headless needs one prompt to continue at all, so the follow-up carries no instruction, and
# the only place the run survives is the reminder hook's output. (The --resume of that last turn
# fires the resume reminder too; the transcript check below proves the compact one fired.)
# Passes when the transcript holds the SessionStart:compact output of run-guard-remind.sh and phases
# 2 and 3 are committed, with no prompt that says what to do.
# Spec: docs/specs/2026-11-26-unattended-run-hardening-plan.md, "End-to-end tests", E2.
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

STATE_REL=docs/tasks_manager/_runs/E2/state.md

REPO=$(make_repo main) || fail "make_repo"
write_state "${REPO}" "${STATE_REL}" \
  "1|pending|append the line one to a.txt and commit it with the message phase 1" \
  "2|pending|append the line two to a.txt and commit it with the message phase 2" \
  "3|pending|append the line three to a.txt and commit it with the message phase 3"
( cd "${REPO}" && git add -A && git commit -qm "chore: E2 state" ) || fail "commit state"
SID=$(new_uuid)
( cd "${REPO}" && "${AT}" run-guard arm --session "${SID}" "${STATE_REL}" >/dev/null ) || fail "arm"

run_claude "${REPO}" "${SID}" "${SCRATCH}/t1.jsonl" \
  "Read ${STATE_REL}. This run has three phases, and you will carry all of them out. Do phase 1 now: do its Work, then set its Status cell to committed in state.md and commit that. Then end your last message with the line 'Run: BLOCKED the owner compacts this session now' and nothing after it."
[[ "$(row_status "${REPO}/${STATE_REL}" 1)" == committed ]] || fail "turn 1 did not commit phase 1"
[[ "$(row_status "${REPO}/${STATE_REL}" 2)" == pending ]] || fail "turn 1 went past phase 1 (nothing left to lose in the compaction)"

export LIVE_SESSION_FLAG=--resume
run_claude "${REPO}" "${SID}" "${SCRATCH}/t2.jsonl" "/compact"
run_claude "${REPO}" "${SID}" "${SCRATCH}/t3.jsonl" "Continue."

T=$(transcript_of "${SID}")
[[ -n "${T}" ]] || fail "no transcript"
jq -e 'select(.attachment.hookName? == "SessionStart:compact") | .attachment | tostring | select(contains("Run guard: this session is executing a run") and contains("agents-core:execute-plan"))' \
  "${T}" >/dev/null || fail "the compaction did not bring the run-guard reminder into the transcript"
for n in 2 3; do
  [[ "$(row_status "${REPO}/${STATE_REL}" ${n})" == committed ]] || fail "row ${n} is not committed after the compaction"
done
( cd "${REPO}" && git log --format=%s | grep -qx 'phase 3' ) || fail "no phase 3 commit"
( cd "${REPO}" && git diff --quiet HEAD ) || fail "the work tree is dirty after the run"
echo "E2: ok (Stop exit codes: $(echo $(stop_hook_codes "${SID}")))"
