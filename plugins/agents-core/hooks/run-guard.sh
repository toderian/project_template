#!/bin/bash
# Stop hook: a session that armed the run guard (`at run-guard arm`, done by
# agents-core:execute-plan when it opens a run) may only end a turn while guarded work is open
# if its last message says why, on a line of its own:
#
#   Run: WAITING <the background job or subagent that will report back>
#   Run: BLOCKED <what only the owner can decide>
#
# Anything else is sent back to the next open row (exit 2 + reason on stderr). The guard is keyed
# by session id, so other sessions in the same checkout are never touched. When every guarded task
# is archived and every guarded state file is fully committed it marks the run DONE (below) and
# passes every later stop.
#
# Marker: ${AGENTS_RUN_GUARD_DIR:-${XDG_STATE_HOME:-~/.local/state}/agents-template/run-guard}/<session_id>
#   task<TAB><repo root><TAB><TASK-ID>    open while docs/tasks_manager/_todos/<TASK-ID>-*.md exists
#   state<TAB><path to state.md>          open while a table row is not `committed`
#   meta<TAB>key<TAB>value                pid, cwd, armed: written by `at run-guard arm`
# <session_id>.status: key=value lines written at every stop this hook lets through: last_stop,
#   kind (WAITING | BLOCKED | GAVE_UP | EMPTY | DONE), text (one line, capped), transcript, mode.
#   kind=DONE makes the marker inactive until a new `at run-guard arm`.
# <session_id>.sent/<key>: one empty file per owner notification already sent (write_status also
#   notifies, through `at notify`; see notify_owner).
#
# Never traps a session: no marker, no jq, an empty final message, five sent-backs in a row, or
# nothing open but a state file that no longer exists all let the stop through.

umask 077  # the guard dir and its files hold message text: private
GUARD_DIR="${AGENTS_RUN_GUARD_DIR:-${XDG_STATE_HOME:-${HOME}/.local/state}/agents-template/run-guard}"
MAX_SENT_BACK=5

IFS= read -r -d '' INPUT || true  # read first, with a builtin: an unread payload breaks the writer's pipe
[ -d "${GUARD_DIR}" ] || { echo '{}'; exit 0; }
command -v jq >/dev/null || { echo "run-guard: jq is missing, the guard is off" >&2; echo '{}'; exit 0; }

SESSION=$(printf '%s' "${INPUT}" | jq -r '.session_id // ""' | tr -cd 'A-Za-z0-9._-')
MARKER="${GUARD_DIR}/${SESSION}"
if [ -z "${SESSION}" ] || [ ! -f "${MARKER}" ]; then
  echo '{}'
  exit 0
fi
# sourced only for a session that armed the guard; a missing lib lets the stop through quietly
. "$(dirname "${BASH_SOURCE[0]}")/lib/run-open.sh" 2>/dev/null || { echo '{}'; exit 0; }
if run_guard_done "${MARKER}"; then
  echo '{}'
  exit 0
fi
COUNT_FILE="${MARKER}.count"

# write_status <kind> <text>: the one place .status is written (temp file + mv, so a reader never
# sees half a file). text is printable ASCII on one line of at most 300 characters (so no cut splits a
# character and no Unicode line separator survives) and is never evaluated.
ascii() { LC_ALL=C tr '\r\t' '  ' | LC_ALL=C tr -cd '\040-\176'; }  # drops newlines
write_status() {
  local text tmp="${MARKER}.status.$$"
  text=$(printf '%s' "$2" | tr '\n' ' ' | ascii | cut -c1-300)
  { {
    echo "last_stop=$(date +%Y-%m-%dT%H:%M:%S%z)"
    echo "kind=$1"
    echo "text=${text}"
    echo "transcript=$(printf '%s' "${INPUT}" | jq -r '.transcript_path // ""' | ascii)"
    echo "mode=$(printf '%s' "${INPUT}" | jq -r '.permission_mode // ""' | ascii)"
  } > "${tmp}"; } 2>/dev/null && mv -f "${tmp}" "${MARKER}.status" 2>/dev/null || rm -f "${tmp}"
  notify_owner "$1" "${text}"
}

# notify_owner <kind> <text>: tells the owner about a stop that needs them or a run that ended, through
# `at notify` (the owner's own command). Detached with every fd redirected, so the hook never waits,
# prints, or changes its exit code; any failure (no python3, no `at`, no command) is silent.
# The event key is a hash (once per distinct decision; DONE once per arm), never raw text.
notify_owner() {
  local at ids title key cwd
  case "$1" in BLOCKED|GAVE_UP|EMPTY|DONE) ;; *) return 0 ;; esac
  at="$(cd "$(dirname "${BASH_SOURCE[0]}")/../bin" 2>/dev/null && pwd)/at"
  cwd=$(printf '%s' "${INPUT}" | jq -r '.cwd // ""')  # the harness's cwd, never the marker's (session-writable)
  [ -x "${at}" ] || return 0
  [ "$1" = GAVE_UP ] && set -- GAVE_UP "the guard let a stop through (details: at run-guard status)"  # never relay the message
  ids=$(awk -F'\t' '$1 == "task" { sub(/\r$/, "", $3); printf "%s ", $3 }' "${MARKER}" 2>/dev/null | ascii | cut -c1-100)
  title="Run $1: ${ids}${2}"
  [ "$1" = DONE ] && title="Run finished: ${ids}"
  key=$(printf '%s' "$1 $2" | cksum | cut -d' ' -f1)
  ( export AGENTS_RUN_GUARD_DIR="$(cd "${GUARD_DIR}" 2>/dev/null && pwd)"  # absolute before the cd
    cd "${cwd}" 2>/dev/null  # where `git config agents.notifyCommand` is read; AGENTS_NOTIFY_CMD needs no cwd
    printf 'tasks: %s\nreason: %s\n' "${ids}" "$2" | "${at}" notify "$(printf '%s' "${title}" | cut -c1-200)" \
      --event "$(printf '%s' "$1" | tr A-Z a-z)-${key}" --session "${SESSION}" >/dev/null 2>&1 & ) >/dev/null 2>&1
  return 0
}

OPEN=$(run_guard_open "${MARKER}")

if [ -z "${OPEN}" ]; then
  rm -f "${COUNT_FILE}"
  write_status DONE "nothing is open"
  echo '{}'
  exit 0
fi
if ! printf '%s\n' "${OPEN}" | grep -qv 'the state file is missing'; then
  # only vanished state files are left (a run directory removed at closeout): not DONE, but never a trap
  rm -f "${COUNT_FILE}"
  write_status GAVE_UP "the state file is missing"
  echo "run-guard: the state file is missing; letting this stop through." >&2
  echo '{}'
  exit 0
fi

MESSAGE=$(printf '%s' "${INPUT}" | jq -r '.last_assistant_message // ""')
DECLARED=$(printf '%s\n' "${MESSAGE}" | grep -E '^[[:space:]>*_`-]*Run:[*_`]*[[:space:]]*(WAITING|BLOCKED)[*_`]*[[:space:]:-]+[^[:space:]]' | head -1)
if [ -z "${MESSAGE}" ]; then
  rm -f "${COUNT_FILE}"
  write_status EMPTY "the last message was empty"
  echo '{}'
  exit 0
elif [ -n "${DECLARED}" ]; then
  rm -f "${COUNT_FILE}"
  # the kind is the keyword right after `Run:`, not any word of the line
  write_status "$(printf '%s' "${DECLARED}" | sed -E 's/^[^R]*Run:[*_`]*[[:space:]]*(WAITING|BLOCKED).*/\1/')" \
    "$(printf '%s' "${DECLARED}" | sed -E 's/^[^R]*Run:[*_`]*[[:space:]]*(WAITING|BLOCKED)[*_`]*[[:space:]:-]+//')"
  echo '{}'
  exit 0
fi

COUNT=$(cat "${COUNT_FILE}" 2>/dev/null | tr -cd '0-9' | cut -c1-3)  # digits only: the file is never evaluated
COUNT=$(( 10#${COUNT:-0} + 1 ))
if [ "${COUNT}" -gt "${MAX_SENT_BACK}" ]; then
  rm -f "${COUNT_FILE}"
  write_status GAVE_UP "$(printf '%s' "${MESSAGE}" | tr '\n' ' ')"
  echo "run-guard: sent back ${MAX_SENT_BACK} times in a row; letting this stop through." >&2
  echo '{}'
  exit 0
fi
if ! echo "${COUNT}" > "${COUNT_FILE}" 2>/dev/null; then  # no count, no cap: never trap the session
  write_status GAVE_UP "the sent-back count cannot be written"
  echo "run-guard: cannot write ${COUNT_FILE}; letting this stop through." >&2
  echo '{}'
  exit 0
fi

{
  echo "Run guard: this session is executing a run that is not finished, so the turn cannot end here."
  echo "Open:"
  printf '%s\n' "${OPEN}"
  echo "Continue at the first open row, following agents-core:execute-plan (load the skill again if"
  echo "its text is no longer in your context, and resume from state.md, not from memory)."
  echo "A summary of the phase you just finished is not a reason to stop."
  echo "End the turn only with one of these as a line of its own in your last message:"
  echo "  Run: WAITING <the background job or subagent that will report back>   (it must be running now)"
  echo "  Run: BLOCKED <what only the owner can decide>   (only when no open row can proceed without it)"
  echo "The owner can switch the guard off with: at run-guard disarm"
} >&2
exit 2
