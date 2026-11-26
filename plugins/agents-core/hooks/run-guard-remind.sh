#!/bin/bash
# SessionStart hook (matchers resume, compact): a session that armed the run guard and still has open
# targets gets told which ones, so a compaction or a resume does not lose the run. Its stdout reaches
# the model. Prints nothing otherwise and always exits 0.

GUARD_DIR="${AGENTS_RUN_GUARD_DIR:-${XDG_STATE_HOME:-${HOME}/.local/state}/agents-template/run-guard}"
IFS= read -r -d '' INPUT || true  # read first, with a builtin: an unread payload breaks the writer's pipe
command -v jq >/dev/null 2>&1 || exit 0
SESSION=$(printf '%s' "${INPUT}" | jq -r '.session_id // ""' 2>/dev/null | tr -cd 'A-Za-z0-9._-')
MARKER="${GUARD_DIR}/${SESSION}"
[ -n "${SESSION}" ] && [ -f "${MARKER}" ] || exit 0

. "$(dirname "${BASH_SOURCE[0]}")/lib/run-open.sh" 2>/dev/null || exit 0
run_guard_done "${MARKER}" && exit 0
OPEN=$(run_guard_open "${MARKER}" 2>/dev/null)
[ -n "${OPEN}" ] || exit 0
printf 'Run guard: this session is executing a run that is not finished. Open:\n%s\n' "${OPEN}"
echo "Load agents-core:execute-plan and resume from state.md (the first open row above), not from memory."
exit 0
