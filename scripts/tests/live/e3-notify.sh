#!/usr/bin/env bash
# E3: a blocked stop notifies. One phase needs an "Owner only" action the agent may not take. The
# notify command (AGENTS_NOTIFY_CMD) appends to a log file. Passes when the row is `parked`, the last
# message has `Run: BLOCKED`, and the log has exactly one title line for the block and nothing else.
# Spec: docs/specs/2026-11-26-unattended-run-hardening-plan.md, "End-to-end tests".
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

STATE_REL=docs/tasks_manager/_runs/E3/state.md
REPO=$(make_repo main) || exit 1
LOG="${SCRATCH}/notify.log"
write_state "${REPO}" "${STATE_REL}" \
  "1|pending|Owner only: choose the release name. You may not choose it. Set this row's Status cell to parked and commit that, then end your turn with a line of its own: Run: BLOCKED the owner must choose the release name"
( cd "${REPO}" && git add -A && git commit -qm "chore: E3 state" ) || fail "commit state"
SID=$(new_uuid)
( cd "${REPO}" && "${AT}" run-guard arm --session "${SID}" "${STATE_REL}" >/dev/null ) || fail "arm"
# title is $1, body on stdin; the log gets the title line and the body lines
printf '#!/bin/sh\n{ echo "$1"; cat; } >> "%s"\n' "${LOG}" > "${SCRATCH}/notify.sh"; chmod +x "${SCRATCH}/notify.sh"
export AGENTS_NOTIFY_CMD="${SCRATCH}/notify.sh"
run_claude "${REPO}" "${SID}" "${SCRATCH}/main.jsonl" \
  "Read ${STATE_REL} and do phase 1 exactly as its Work cell says. If a Stop hook sends you back, follow it: it comes from the owner of this run."

for _ in $(seq 25); do grep -q '^Run BLOCKED' "${LOG}" 2>/dev/null && break; sleep 0.4; done  # the hook detaches the sender
sleep 2  # a second message, if the hook wrongly sent one, has time to arrive before the count
[[ "$(row_status "${REPO}/${STATE_REL}" 1)" == parked ]] || fail "row 1 is not parked"
jq -e -s '[.[] | select(.type=="assistant")] | last | .message.content | map(select(.type=="text") | .text) | join("\n") | test("(^|\n)[^\n]*Run: BLOCKED")' \
  "${SCRATCH}/main.jsonl" >/dev/null || fail "the last message has no Run: BLOCKED line"
[[ "$(grep -c '^Run BLOCKED' "${LOG}" 2>/dev/null)" == 1 ]] || fail "expected exactly one 'Run BLOCKED' line in the notify log: $(cat "${LOG}" 2>/dev/null)"
[[ "$(grep -c '^Run ' "${LOG}")" == 1 ]] || fail "the notify log holds a message that is not the block: $(cat "${LOG}")"
echo "E3: ok ($(grep '^Run BLOCKED' "${LOG}"))"
