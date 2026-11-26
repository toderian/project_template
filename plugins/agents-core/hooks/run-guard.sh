#!/bin/bash
# Stop hook: a session that armed the run guard (`at run-guard arm`, done by
# agents-core:execute-plan when it opens a run) may only end a turn while guarded work is open
# if its last message says why, on a line of its own:
#
#   Run: WAITING <the background job or subagent that will report back>
#   Run: BLOCKED <what only the owner can decide>
#
# Anything else is sent back to the next open row (exit 2 + reason on stderr). The guard is keyed
# by session id, so other sessions in the same checkout are never touched, and it removes itself
# when every guarded task is archived and every guarded state file is fully committed.
#
# Marker: ${AGENTS_RUN_GUARD_DIR:-${XDG_STATE_HOME:-~/.local/state}/agents-template/run-guard}/<session_id>
#   task<TAB><repo root><TAB><TASK-ID>    open while docs/tasks_manager/_todos/<TASK-ID>-*.md exists
#   state<TAB><path to state.md>          open while a table row is not `committed`
#
# Never traps a session: no marker, no jq, an empty final message, or five sent-backs in a row
# all let the stop through.

GUARD_DIR="${AGENTS_RUN_GUARD_DIR:-${XDG_STATE_HOME:-${HOME}/.local/state}/agents-template/run-guard}"
MAX_SENT_BACK=5

[ -d "${GUARD_DIR}" ] || { echo '{}'; exit 0; }
command -v jq >/dev/null || { echo "run-guard: jq is missing, the guard is off" >&2; echo '{}'; exit 0; }

INPUT=$(cat)
SESSION=$(printf '%s' "${INPUT}" | jq -r '.session_id // ""' | tr -cd 'A-Za-z0-9._-')
MARKER="${GUARD_DIR}/${SESSION}"
if [ -z "${SESSION}" ] || [ ! -f "${MARKER}" ]; then
  echo '{}'
  exit 0
fi
COUNT_FILE="${MARKER}.count"

# first_open_row <state.md>: prints "<phase> (<status>)" for the first row that is not committed.
first_open_row() {
  awk -F'|' '/^\|[[:space:]]*[0-9]+[a-z]?[[:space:]]*\|/ {
    p=$2; s=$3; gsub(/[[:space:]]/, "", p); gsub(/[[:space:]]/, "", s)
    if (s != "committed") { print p " (" s ")"; exit }
  }' "$1" 2>/dev/null
}

OPEN=""
while IFS=$'\t' read -r KIND A B; do
  case "${KIND}" in
    task)
      if compgen -G "${A}/docs/tasks_manager/_todos/${B}-*.md" >/dev/null; then
        ROW=""
        STATE="${A}/docs/tasks_manager/_runs/${B}/state.md"
        [ -f "${STATE}" ] && ROW=$(first_open_row "${STATE}")
        if [ -n "${ROW}" ]; then
          OPEN="${OPEN}  - ${B}: phase ${ROW} in ${STATE}"$'\n'
        elif [ -f "${STATE}" ]; then
          OPEN="${OPEN}  - ${B}: every phase is committed; final validation, final review and closeout remain"$'\n'
        else
          OPEN="${OPEN}  - ${B}: not started (no run state yet)"$'\n'
        fi
      fi ;;
    state)
      if [ -f "${A}" ]; then
        ROW=$(first_open_row "${A}")
        [ -n "${ROW}" ] && OPEN="${OPEN}  - ${A}: phase ${ROW}"$'\n'
      fi ;;
  esac
done < "${MARKER}"

if [ -z "${OPEN}" ]; then
  rm -f "${MARKER}" "${COUNT_FILE}"
  echo '{}'
  exit 0
fi

MESSAGE=$(printf '%s' "${INPUT}" | jq -r '.last_assistant_message // ""')
if [ -z "${MESSAGE}" ] || printf '%s\n' "${MESSAGE}" | grep -qE '^[[:space:]>*_`-]*Run:[*_`]*[[:space:]]*(WAITING|BLOCKED)[*_`]*[[:space:]:-]+[^[:space:]]'; then
  rm -f "${COUNT_FILE}"
  echo '{}'
  exit 0
fi

COUNT=$(( $(cat "${COUNT_FILE}" 2>/dev/null || echo 0) + 1 ))
if [ "${COUNT}" -gt "${MAX_SENT_BACK}" ]; then
  rm -f "${COUNT_FILE}"
  echo "run-guard: sent back ${MAX_SENT_BACK} times in a row; letting this stop through." >&2
  echo '{}'
  exit 0
fi
echo "${COUNT}" > "${COUNT_FILE}"

{
  echo "Run guard: this session is executing a run that is not finished, so the turn cannot end here."
  echo "Open:"
  printf '%s' "${OPEN}"
  echo "Continue at the first open row, following agents-core:execute-plan (load the skill again if"
  echo "its text is no longer in your context, and resume from state.md, not from memory)."
  echo "A summary of the phase you just finished is not a reason to stop."
  echo "End the turn only with one of these as a line of its own in your last message:"
  echo "  Run: WAITING <the background job or subagent that will report back>   (it must be running now)"
  echo "  Run: BLOCKED <what only the owner can decide>   (only when no open row can proceed without it)"
  echo "The owner can switch the guard off with: at run-guard disarm"
} >&2
exit 2
