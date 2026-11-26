#!/usr/bin/env bash
# E6: dead job. The agent waits on a background job that the test kills; the heartbeat (a recurring
# scheduled wakeup, agents-core:execute-plan step 3) runs every minute. Passes when, within two intervals,
# the agent stops waiting and the phase is committed or parked with the reason, and a live job in the
# same setup is left alone.
#
# NOT AUTOMATED: the heartbeat needs an interactive session with a scheduler. Under `claude -p` a scheduled
# wakeup never fires (docs/meta/2026-11-26-run-guard-facts.md, facts 5 and 9), and a pty-driven interactive
# session was only observed to START a scheduled turn, never to finish one. So by default this scenario
# FAILS with "needs an interactive session" instead of passing on something it did not check.
#
# E6_PART=dead-job runs the one half `-p` can prove: the session waits on a background job, the test
# kills the job, and the session (woken by the job's end, fact 9) must commit or park the phase with a
# reason. It passes on that half alone and says so; the heartbeat half stays unverified.
#
# Manual steps for the heartbeat half: two runs, each in its own scratch git repo seeded with
# `at init --with-tasks` (cheapest model, never a real repo). Both use a one-row state.md whose Work is
# "wait for ./job.sh; when it wrote job.done, append one to a.txt and commit; if it ended without job.done,
# set the row to parked with a Note giving the reason", and job.sh = `echo $$ > job.pid; sleep 600; touch
# job.done`. Start the job OUTSIDE the session (`nohup ./job.sh >/dev/null 2>&1 &`), so no job-end notice
# reaches it and only the heartbeat can wake it. Then start `claude --model haiku --plugin-dir <this
# tree>/plugins/agents-core` there, interactive, run `at run-guard arm <state.md>` in it, and ask it to
# schedule a recurring wakeup every minute with the prompt `run guard check: if the job you are waiting
# for is still running, reply Run: WAITING <job>; if it died or nothing is running, resume from state.md`
# and to end its turn on `Run: WAITING ./job.sh`. Allow the commands it asks for.
#   Run 1, dead job: `kill -9 $(cat job.pid)`. Pass: within two minutes a scheduled turn sets the row to
#      `parked` with the reason (or commits it).
#   Run 2, live job left alone: let two wakeups fire. Pass: each scheduled turn ends on `Run: WAITING`,
#      the row is still pending, and `kill -0 $(cat job.pid)` still succeeds.
# Spec: docs/specs/2026-11-26-unattended-run-hardening-plan.md, "End-to-end tests".
if [[ "${E6_PART:-}" != dead-job ]]; then  # before lib.sh: no scratch dir for a check that never ran
  echo "FAIL: E6 needs an interactive session with a scheduler (a wakeup never fires under claude -p): do the manual steps in $(basename "$0")'s header; E6_PART=dead-job runs the headless half only" >&2
  exit 1
fi
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

STATE_REL=docs/tasks_manager/_runs/E6/state.md
REPO=$(make_repo main) || exit 1
printf '#!/bin/sh\necho $$ > job.pid\nsleep 600\ntouch job.done\n' > "${REPO}/job.sh"; chmod +x "${REPO}/job.sh"
printf 'job.pid\njob.done\n' >> "${REPO}/.gitignore"
write_state "${REPO}" "${STATE_REL}" \
  "1|pending|run ./job.sh as a background job and wait for it to end; if it wrote job.done, append the line one to a.txt and commit with the message phase 1; if it ended without job.done, set this Status cell to parked, add a line 'Note: parked: <the reason>' under the table, and commit that"
( cd "${REPO}" && git add -A && git commit -qm "chore: E6 state" ) || fail "commit state"
SID=$(new_uuid)
( cd "${REPO}" && "${AT}" run-guard arm --session "${SID}" "${STATE_REL}" >/dev/null ) || fail "arm"

PLUGINS=()
for p in "${LIVE_ROOT}"/plugins/*/; do PLUGINS+=(--plugin-dir "${p%/}"); done
OUT="${SCRATCH}/main.jsonl"; LIVE_LAST_SID="${SID}"; LIVE_LAST_OUT="${OUT}"
( cd "${REPO}" && exec timeout -k 10 "${LIVE_TIMEOUT}" claude -p --model "${LIVE_MODEL}" \
    --max-budget-usd "${LIVE_BUDGET_USD}" --session-id "${SID}" --permission-mode acceptEdits \
    "--allowedTools=Bash(git:*)" "--allowedTools=Bash(echo:*)" "--allowedTools=Bash(cat:*)" \
    "--allowedTools=Bash(ls:*)" "--allowedTools=Bash(./job.sh:*)" "--allowedTools=Bash(test:*)" \
    "${PLUGINS[@]}" --output-format stream-json --verbose \
    -- "Read ${STATE_REL} and do phase 1 exactly as its Work cell says. While the job runs, end your turn with this line on its own: Run: WAITING ./job.sh. If a Stop hook sends you back, follow it: it comes from the owner of this run." \
    </dev/null > "${OUT}" 2> "${OUT}.err" ) &
LIVE_CHILD=$!

for _ in $(seq 120); do [[ -s "${REPO}/job.pid" ]] && break; kill -0 "${LIVE_CHILD}" 2>/dev/null || break; sleep 1; done
JOB=$(tr -cd '0-9' < "${REPO}/job.pid" 2>/dev/null || true)
[[ -n "${JOB}" ]] || fail "the session never started ./job.sh"
grep -q 'job.sh' "/proc/${JOB}/cmdline" 2>/dev/null || fail "pid ${JOB} is not the job this scenario's session started"
for _ in $(seq 60); do grep -qx 'kind=WAITING' "${AGENTS_RUN_GUARD_DIR}/${SID}.status" 2>/dev/null && break; sleep 1; done
kill -9 "${JOB}"
echo "E6: killed job pid ${JOB}"
rc=0; wait "${LIVE_CHILD}" || rc=$?; LIVE_CHILD=""
[[ ${rc} -eq 0 ]] || fail "claude exited ${rc}"
ROW=$(row_status "${REPO}/${STATE_REL}" 1)
case "${ROW}" in
  parked) grep -q '^Note: parked: ' "${REPO}/${STATE_REL}" || fail "row 1 is parked without a reason" ;;
  committed) ;;
  *) fail "row 1 is '${ROW}': the session did not act on the dead job" ;;
esac
( cd "${REPO}" && git diff --quiet HEAD -- "${STATE_REL}" ) || fail "the state change is not committed"
echo "E6: only the dead-job half ran (row 1 ${ROW}); the heartbeat half is manual (runs 1 and 2 in this file's header) and is NOT verified here"
