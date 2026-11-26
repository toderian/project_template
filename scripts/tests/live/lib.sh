#!/usr/bin/env bash
# Shared helpers for scripts/tests/live/eN-*.sh. Source it; do not run it.
#
# Every claude session started here: cheapest model, --max-budget-usd, a timeout, the plugins of
# this working tree, the scratch repo as cwd, and AGENTS_RUN_GUARD_DIR inside the scratch dir.
# Assertions read files (git log, state.md, markers, the session transcript), never model prose.
#
# Safety: `set -euo pipefail`, so a setup failure ends the scenario; run_claude refuses any repo that
# is not a git repo under ${SCRATCH}/. INT/TERM stop the running session and exit 130.
# Known leftover: a passing run deletes its scratch dir but not the session transcripts the CLI
# wrote under ~/.claude/projects/ for it; remove them by hand if they matter.

set -euo pipefail

LIVE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
AT="${LIVE_ROOT}/plugins/agents-core/bin/at"
LIVE_MODEL="${LIVE_MODEL:-haiku}"
LIVE_BUDGET_USD="${LIVE_BUDGET_USD:-1}"
LIVE_TIMEOUT="${LIVE_TIMEOUT:-300}"

SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/at-live.XXXXXX")" || { echo "FAIL: mktemp -d failed" >&2; exit 1; }
[[ -n "${SCRATCH}" && -d "${SCRATCH}" ]] || { echo "FAIL: no scratch dir" >&2; exit 1; }
export AGENTS_RUN_GUARD_DIR="${SCRATCH}/guard"
# a session started here must not look like a child of the session that runs the suite
unset CLAUDE_CODE_SESSION_ID CLAUDE_CODE_CHILD_SESSION CLAUDE_PID

LIVE_CHILD=""      # pid of the running claude session (its timeout wrapper)
LIVE_LAST_SID=""   # the last session started, for the failure report
LIVE_LAST_OUT=""

live_cleanup() {
  local rc=$?
  if [[ ${rc} -eq 0 ]]; then
    rm -rf "${SCRATCH}"
  else
    echo "kept for inspection: ${SCRATCH}" >&2
  fi
}
trap live_cleanup EXIT
# timeout forwards TERM to claude and kills it after -k seconds; the group of timeout is its own
live_abort() {
  [[ -z "${LIVE_CHILD}" ]] || kill -TERM "${LIVE_CHILD}" 2>/dev/null || true
  echo "interrupted" >&2
  exit 130
}
trap live_abort INT TERM

fail() {
  echo "FAIL: $*" >&2
  echo "  scratch repo dir: ${SCRATCH}" >&2
  [[ -z "${LIVE_LAST_OUT}" ]] || echo "  stream file: ${LIVE_LAST_OUT}" >&2
  if [[ -n "${LIVE_LAST_SID}" ]]; then
    echo "  session transcript: $(transcript_of "${LIVE_LAST_SID}")" >&2
  fi
  exit 1
}
need() { command -v "$1" >/dev/null || fail "$1 is not on PATH"; }
need claude; need jq; need git; need python3; need timeout

new_uuid() { cat /proc/sys/kernel/random/uuid 2>/dev/null || python3 -c 'import uuid; print(uuid.uuid4())'; }

# make_repo <name>: a scratch git repo seeded with `at init --with-tasks`; prints its path.
make_repo() {
  local repo="${SCRATCH}/$1"
  mkdir -p "${repo}" && cd "${repo}" || return 1
  { git init -q -b main . && git config user.email live@example.invalid && git config user.name live; } || return 1
  echo "base" > a.txt
  { git add -A && git commit -qm "base"; } || return 1
  "${AT}" init --with-tasks >/dev/null 2>&1 || fail "at init --with-tasks failed in ${repo}"
  { git add -A && git commit -qm "chore: at init"; } || return 1
  echo "${repo}"
}

# write_state <repo> <state.md path rel. to repo> <row>...: a run state with one row per argument,
# each "<n>|<status>|<what to do>".
write_state() {
  local repo="$1" rel="$2"; shift 2
  mkdir -p "${repo}/$(dirname "${rel}")"
  {
    echo "# Run state"
    echo
    echo "| Phase | Status | Work |"
    echo "|---|---|---|"
    local row
    for row in "$@"; do IFS='|' read -r n s w <<<"${row}"; echo "| ${n} | ${s} | ${w} |"; done
  } > "${repo}/${rel}"
}

# run_claude <repo> <session-id> <out.jsonl> <prompt>: one headless session, resumable by its id.
# LIVE_SESSION_FLAG=--resume continues an existing session instead of starting it.
run_claude() {
  local repo="$1" sid="$2" out="$3" prompt="$4" rc=0
  local plugins=() p
  [[ -n "${repo}" && "${repo}" == "${SCRATCH}"/?* && -e "${repo}/.git" ]] \
    || fail "refusing to start a session outside the scratch dir (repo: '${repo}')"
  LIVE_LAST_SID="${sid}"; LIVE_LAST_OUT="${out}"
  for p in "${LIVE_ROOT}"/plugins/*/; do plugins+=(--plugin-dir "${p%/}"); done
  ( cd "${repo}" && exec timeout -k 10 "${LIVE_TIMEOUT}" claude -p --model "${LIVE_MODEL}" \
      --max-budget-usd "${LIVE_BUDGET_USD}" "${LIVE_SESSION_FLAG:---session-id}" "${sid}" \
      --permission-mode acceptEdits \
      "--allowedTools=Bash(git:*)" "--allowedTools=Bash(echo:*)" "--allowedTools=Bash(grep:*)" \
      "--allowedTools=Bash(cat:*)" "--allowedTools=Bash(sed:*)" "--allowedTools=Bash(printf:*)" \
      "${plugins[@]}" --output-format stream-json --verbose --include-hook-events \
      -- "${prompt}" </dev/null > "${out}" 2> "${out}.err" ) &
  LIVE_CHILD=$!
  wait "${LIVE_CHILD}" || rc=$?
  LIVE_CHILD=""
  [[ ${rc} -eq 0 ]] || fail "claude exited ${rc} for session ${sid} (output: ${out}, ${out}.err)"
}

# transcript_of <session-id>: the session transcript the CLI wrote (hook entries live there).
transcript_of() {
  find "${HOME}/.claude/projects" -maxdepth 2 -name "$1.jsonl" 2>/dev/null | head -1
}

# stop_hook_codes <session-id>: one line per Stop hook run of THIS working tree's run-guard.sh, in
# order: 2 = it sent the agent back, 0 = it let the turn end, x = it failed some other way. Read
# from the session transcript (`stop_hook_summary` entries): the stream output names no command, so
# it cannot tell the guard from another plugin's Stop hook. A sent-back names the expanded path
# "<this tree>/plugins/agents-core"/hooks/run-guard.sh, which is what proves the working tree ran.
stop_hook_codes() {
  local t; t=$(transcript_of "$1")
  [[ -n "${t}" ]] || fail "no transcript for session $1 under ~/.claude/projects"
  jq -r --arg root "${LIVE_ROOT}/plugins/agents-core\"/hooks/run-guard.sh" '
    select(.type=="system" and .subtype=="stop_hook_summary"
           and any(.hookInfos[]?; (.command // "") | contains("hooks/run-guard.sh")))
    | if (.hookErrors | length) == 0 then "0"
      elif any(.hookErrors[]; contains($root) and contains("Run guard:")) then "2"
      else "x" end' "${t}" || fail "cannot parse transcript ${t}"
}

# row_status <state.md> <phase>: the status cell of that row.
row_status() {
  awk -F'|' -v p="$2" '{a=$2; s=$3; gsub(/[[:space:]]/,"",a); gsub(/[[:space:]]/,"",s); if (a==p) print s}' "$1"
}

# marker_inactive <session-id>: no marker, or one whose status says DONE (the later lifecycle).
marker_inactive() {
  local m="${AGENTS_RUN_GUARD_DIR}/$1"
  [[ ! -f "${m}" ]] || grep -qx 'kind=DONE' "${m}.status" 2>/dev/null
}
