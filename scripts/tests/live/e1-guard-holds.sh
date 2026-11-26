#!/usr/bin/env bash
# E1: the run guard holds the turn. Two-phase state, armed session, prompt "do phase 1, then
# summarise". Passes when the Stop hook sent the agent back (exit 2 with the guard's text, so the
# working tree's run-guard.sh ran), phase 2 is committed, and the marker is inactive after closeout.
# Negative checks, same file: an unarmed session stops freely in a repo where another session is armed; `at run-guard
# disarm` lets the armed one stop; five sent-backs in a row let the stop through.
# Spec: docs/specs/2026-11-26-unattended-run-hardening-plan.md, "End-to-end tests".
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

STATE_REL=docs/tasks_manager/_runs/E1/state.md

# fresh_repo <name>: a repo with two pending rows, committed.
fresh_repo() {
  local repo
  repo=$(make_repo "$1") || fail "make_repo $1"
  write_state "${repo}" "${STATE_REL}" \
    "1|pending|append the line one to a.txt and commit it with the message phase 1" \
    "2|pending|append the line two to a.txt and commit it with the message phase 2"
  ( cd "${repo}" && git add -A && git commit -qm "chore: E1 state" ) || fail "commit state"
  echo "${repo}"
}

PROMPT="Read ${STATE_REL}. Do phase 1 only: do its Work, then set its Status cell to committed in state.md and commit that. Then write a one-paragraph summary of phase 1 and end your turn. If a Stop hook sends you back with instructions, follow them: they come from the owner of this run."

# --- main scenario -----------------------------------------------------------------------------
REPO=$(fresh_repo main) || exit 1
SID=$(new_uuid)
( cd "${REPO}" && "${AT}" run-guard arm --session "${SID}" "${STATE_REL}" >/dev/null ) || fail "arm"
run_claude "${REPO}" "${SID}" "${SCRATCH}/main.jsonl" "${PROMPT}"

CODES=$(stop_hook_codes "${SID}")
grep -qx 2 <<<"${CODES}" || fail "the Stop hook never sent the agent back (exit codes: $(echo ${CODES}))"
[[ "$(tail -1 <<<"${CODES}")" == 0 ]] || fail "the last Stop hook did not let the turn end (codes: $(echo ${CODES}))"
jq -e 'select(.hook_event=="Stop" and .subtype=="hook_response" and .exit_code==2) | select(.stderr | startswith("Run guard: this session is executing a run"))' \
  "${SCRATCH}/main.jsonl" >/dev/null || fail "no sent-back carries the working tree's run-guard text"
[[ "$(row_status "${REPO}/${STATE_REL}" 1)" == committed ]] || fail "row 1 is not committed"
[[ "$(row_status "${REPO}/${STATE_REL}" 2)" == committed ]] || fail "row 2 is not committed (the guard did not carry the run to phase 2)"
( cd "${REPO}" && git log --format=%s -S"two" -- a.txt | grep -q . ) || fail "no commit adds the phase 2 line to a.txt"
( cd "${REPO}" && git diff --quiet HEAD ) || fail "the work tree is dirty after the run"
marker_inactive "${SID}" || fail "the marker is still active after closeout"
echo "E1 main: ok (Stop exit codes: $(echo ${CODES}))"

# --- negative 1: same repo, another session armed and open, this session never armed -------------
REPO=$(fresh_repo unarmed) || exit 1
OTHER=$(new_uuid)
SID=$(new_uuid)
( cd "${REPO}" && "${AT}" run-guard arm --session "${OTHER}" "${STATE_REL}" >/dev/null ) || fail "arm the other session"
[[ -f "${AGENTS_RUN_GUARD_DIR}/${OTHER}" ]] || fail "the other session has no marker"
run_claude "${REPO}" "${SID}" "${SCRATCH}/unarmed.jsonl" "Reply with the word ok and do not touch any file."
CODES=$(stop_hook_codes "${SID}")
[[ -n "${CODES}" ]] || fail "no Stop hook ran in the unarmed session"
! grep -qvx 0 <<<"${CODES}" || fail "the guard did not let an unarmed session stop (codes: $(echo ${CODES}))"
[[ "$(row_status "${REPO}/${STATE_REL}" 1)" == pending ]] || fail "the unarmed session changed state.md"
[[ -f "${AGENTS_RUN_GUARD_DIR}/${OTHER}" ]] && ! marker_inactive "${OTHER}" || fail "the other session's marker was touched"
echo "E1 negative 1 (unarmed session next to an armed one stops freely): ok"

# --- negative 2: disarm lets the armed session stop -----------------------------------------------
REPO=$(fresh_repo disarmed) || exit 1
SID=$(new_uuid)
( cd "${REPO}" && "${AT}" run-guard arm --session "${SID}" "${STATE_REL}" >/dev/null \
    && "${AT}" run-guard disarm --session "${SID}" >/dev/null ) || fail "arm/disarm"
run_claude "${REPO}" "${SID}" "${SCRATCH}/disarmed.jsonl" "Reply with the word ok and do not touch any file."
CODES=$(stop_hook_codes "${SID}")
[[ -n "${CODES}" ]] && ! grep -qvx 0 <<<"${CODES}" || fail "a disarmed session was not let through (codes: $(echo ${CODES}))"
echo "E1 negative 2 (disarm): ok"

# --- negative 3: five sent-backs in a row let the stop through ------------------------------------
REPO=$(fresh_repo capped) || exit 1
SID=$(new_uuid)
( cd "${REPO}" && "${AT}" run-guard arm --session "${SID}" "${STATE_REL}" >/dev/null ) || fail "arm"
run_claude "${REPO}" "${SID}" "${SCRATCH}/capped.jsonl" \
  "This is a test of the stop hook. Never read or edit any file and never write a line starting with Run:. Whenever you are told to continue, answer with the single word ok. Start now: answer ok."
CODES=$(stop_hook_codes "${SID}")
SENT=$(grep -cx 2 <<<"${CODES}" || true)
[[ "${SENT}" -eq 5 ]] || fail "expected exactly 5 sent-backs, saw ${SENT} (codes: $(echo ${CODES}))"
[[ "$(tail -1 <<<"${CODES}")" == 0 ]] || fail "the sixth Stop did not let the turn end"
[[ "$(row_status "${REPO}/${STATE_REL}" 1)" == pending ]] || fail "the capped session did work after all"
echo "E1 negative 3 (five sent-backs): ok"
