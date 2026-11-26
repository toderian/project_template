#!/usr/bin/env bash
# E5: dead session. A task marked `Execution: unattended` with `Watch: on`, two phases. The session does
# phase 1, starts a background job and ends its turn on `Run: WAITING` (so `-p` stays alive and `.status`
# records its permission mode); the scenario then arms the watchdog with the session's pid and kills that
# session with `kill -9`. Passes when the watchdog restarted it exactly once (with the divided budget),
# phase 2 is committed, the notify log holds one "restarted" and one "finished" line, and the watcher
# has exited.
# The restart goes through a `claude` wrapper first on the watcher's PATH: it adds the cheapest model, this
# tree's plugins and the harness allowlist, and logs its argv. The scenario signals only the session it
# started, by the pid in its own marker, after checking that pid is the child of its own timeout process.
# Spec: docs/specs/2026-11-26-unattended-run-hardening-plan.md, "End-to-end tests".
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

TASK_ID=LIV-005
TASK_REL=docs/tasks_manager/_todos/${TASK_ID}-F_e5.md
STATE_REL=docs/tasks_manager/_runs/${TASK_ID}/state.md
REPO=$(make_repo main) || exit 1
cat > "${REPO}/${TASK_REL}" <<'EOF'
| Field | Value |
|---|---|
| Task ID | LIV-005 |
| Execution | unattended |

## E5 fixture task

### Unattended run

Checked: 2026-11-26, READY
Authorised: edit a.txt and commit
Watch: on
Watch budget: 1 USD, at most 2 restarts
EOF
write_state "${REPO}" "${STATE_REL}" \
  "1|pending|append the line one to a.txt and commit it with the message phase 1" \
  "2|pending|append the line two to a.txt, move ${TASK_REL} to docs/tasks_manager/_todos_archived/ with git mv, and commit both with the message phase 2"
( cd "${REPO}" && git add -A && git commit -qm "chore: E5 task and state" ) || fail "commit task"

LOG="${SCRATCH}/notify.log"
printf '#!/bin/sh\n{ echo "$1"; cat; } >> "%s"\n' "${LOG}" > "${SCRATCH}/notify.sh"; chmod +x "${SCRATCH}/notify.sh"
export AGENTS_NOTIFY_CMD="${SCRATCH}/notify.sh"

REAL_CLAUDE=$(command -v claude)
ALLOW=("--allowedTools=Bash(git:*)" "--allowedTools=Bash(echo:*)" "--allowedTools=Bash(grep:*)"
       "--allowedTools=Bash(cat:*)" "--allowedTools=Bash(sed:*)" "--allowedTools=Bash(printf:*)")
PLUGINS=()
for p in "${LIVE_ROOT}"/plugins/*/; do PLUGINS+=(--plugin-dir "${p%/}"); done
mkdir -p "${SCRATCH}/bin"
{
  echo '#!/usr/bin/env bash'
  echo "echo \"\$\$ \$*\" >> '${SCRATCH}/resume.argv'"
  printf 'exec timeout -k 10 %q %q --model %q' "${LIVE_TIMEOUT}" "${REAL_CLAUDE}" "${LIVE_MODEL}"
  printf ' %q' "${PLUGINS[@]}" "${ALLOW[@]}"
  echo ' "$@"'
} > "${SCRATCH}/bin/claude"
chmod +x "${SCRATCH}/bin/claude"

SID=$(new_uuid)
WATCHER=""
e5_exit() {  # a failed run must not leave the watcher or a restarted session behind
  local rc=$? pid
  [[ ${rc} -eq 0 || ! -f "${AGENTS_RUN_GUARD_DIR}/${SID}.watch.log" ]] || cp "${AGENTS_RUN_GUARD_DIR}/${SID}.watch.log" "${SCRATCH}/"
  "${AT}" run-guard disarm --session "${SID}" >/dev/null 2>&1 || true
  for pid in $(awk '{print $1}' "${SCRATCH}/resume.argv" 2>/dev/null); do kill -TERM "${pid}" 2>/dev/null || true; done
  (exit "${rc}"); live_cleanup
}
trap e5_exit EXIT

( cd "${REPO}" && "${AT}" run-guard arm --session "${SID}" "${TASK_ID}" >/dev/null ) || fail "arm"
OUT="${SCRATCH}/main.jsonl"; LIVE_LAST_SID="${SID}"; LIVE_LAST_OUT="${OUT}"
( cd "${REPO}" && exec timeout -k 10 "${LIVE_TIMEOUT}" claude -p --model "${LIVE_MODEL}" \
    --max-budget-usd "${LIVE_BUDGET_USD}" --session-id "${SID}" --permission-mode acceptEdits \
    "${ALLOW[@]}" "--allowedTools=Bash(sleep:*)" "${PLUGINS[@]}" --output-format stream-json --verbose \
    -- "Read ${STATE_REL}. Do phase 1: do its Work, then set its Status cell to committed in state.md and commit that. Phase 2 must wait for a background job: start the command sleep 90 as a background job (run_in_background) and end your turn with this line on its own: Run: WAITING sleep 90. When the job has ended, do phase 2 the same way." \
    </dev/null > "${OUT}" 2> "${OUT}.err" ) &
LIVE_CHILD=$!

CPID=""
for _ in $(seq 50); do
  CPID=$(pgrep -P "${LIVE_CHILD}" | head -1 || true)
  [[ -n "${CPID}" ]] && break; sleep 0.2
done
[[ -n "${CPID}" ]] || fail "no claude process under the timeout wrapper ${LIVE_CHILD}"
( cd "${REPO}" && CLAUDE_PID="${CPID}" PATH="${SCRATCH}/bin:${PATH}" "${AT}" run-guard arm --session "${SID}" --watch \
    --interval 2 --pause 1 --max-resumes 2 --budget-usd 1 --idle 30 "${TASK_ID}" >/dev/null ) || fail "arm --watch"
WATCHER=$(cat "${AGENTS_RUN_GUARD_DIR}/${SID}.watch")

for _ in $(seq "${LIVE_TIMEOUT}"); do
  grep -qx 'kind=WAITING' "${AGENTS_RUN_GUARD_DIR}/${SID}.status" 2>/dev/null && break
  kill -0 "${LIVE_CHILD}" 2>/dev/null || break
  sleep 1
done
grep -qx 'kind=WAITING' "${AGENTS_RUN_GUARD_DIR}/${SID}.status" 2>/dev/null || fail "the session never stopped on Run: WAITING"
[[ "$(row_status "${REPO}/${STATE_REL}" 1)" == committed ]] || fail "row 1 is not committed before the kill"
[[ "$(row_status "${REPO}/${STATE_REL}" 2)" == pending ]] || fail "the first session already did phase 2"

PID=$(awk -F'\t' '$1 == "meta" && $2 == "pid" { print $3; exit }' "${AGENTS_RUN_GUARD_DIR}/${SID}")
[[ "${PID}" == "${CPID}" && "$(ps -o ppid= -p "${PID}" | tr -d ' ')" == "${LIVE_CHILD}" ]] \
  || fail "the marker pid '${PID}' is not the session this scenario started"
kill -9 "${PID}"
wait "${LIVE_CHILD}" 2>/dev/null || true
LIVE_CHILD=""
echo "E5: killed session pid ${PID}; watcher pid ${WATCHER}"

for _ in $(seq "$((LIVE_TIMEOUT + 60))"); do  # the restart runs under the wrapper's timeout
  kill -0 "${WATCHER}" 2>/dev/null || break
  sleep 1
done
kill -0 "${WATCHER}" 2>/dev/null && fail "the watcher ${WATCHER} has not exited"
[[ ! -e "${AGENTS_RUN_GUARD_DIR}/${SID}.watch" ]] || fail "the watcher left its .watch file"
sleep 2  # a notification still on its way
[[ "$(wc -l < "${SCRATCH}/resume.argv")" -eq 1 ]] || fail "expected exactly one restart: $(cat "${SCRATCH}/resume.argv")"
grep -q -- "--resume ${SID} -p --permission-mode acceptEdits --max-budget-usd 0.50 -- " "${SCRATCH}/resume.argv" \
  || fail "the restart argv is not the expected one: $(cat "${SCRATCH}/resume.argv")"
[[ "$(row_status "${REPO}/${STATE_REL}" 2)" == committed* ]] || fail "row 2 is not committed after the restart"  # the model may add the sha
( cd "${REPO}" && git log --format=%s -S"two" -- a.txt | grep -q . ) || fail "no commit adds the phase 2 line to a.txt"
[[ ! -e "${REPO}/${TASK_REL}" ]] || fail "the task file was not archived"
[[ "$(grep -c '^Run restarted' "${LOG}" 2>/dev/null)" == 1 ]] || fail "expected one 'Run restarted' line: $(cat "${LOG}" 2>/dev/null)"
[[ "$(grep -c '^Run finished' "${LOG}" 2>/dev/null)" == 1 ]] || fail "expected one 'Run finished' line: $(cat "${LOG}" 2>/dev/null)"
echo "E5: ok ($(grep -E '^Run (restarted|finished)' "${LOG}" | tr '\n' ';'))"
echo "E5 watcher log:"; sed 's/^/  /' "${AGENTS_RUN_GUARD_DIR}/${SID}.watch.log"
