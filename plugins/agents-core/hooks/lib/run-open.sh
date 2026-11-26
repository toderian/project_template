#!/bin/bash
# Shared by run-guard.sh and run-guard-remind.sh: what is still open in a run-guard marker.
# Marker lines: `task<TAB><repo root><TAB><TASK-ID>`, `state<TAB><path to state.md>`, and
# `meta<TAB>key<TAB>value` (ignored here). Source this file; it defines functions only.

# run_guard_done <marker>: true when the hook already marked the run DONE (an inactive marker).
run_guard_done() { grep -qx 'kind=DONE' "$1.status" 2>/dev/null; }

# first_open_row <state.md>: prints "<phase> (<status>)" for the first row that is not committed.
first_open_row() {
  awk -F'|' '/^\|[[:space:]]*[0-9]+[a-z]?[[:space:]]*\|/ {
    p=$2; s=$3; gsub(/[[:space:]]/, "", p); gsub(/[[:space:]]/, "", s)
    # the cell reaches the model context: keep it to a short plain token
    if (s != "committed") { gsub(/[^A-Za-z0-9_-]/, "", s); gsub(/[^0-9a-z]/, "", p); print substr(p, 1, 10) " (" substr(s, 1, 30) ")"; exit }
  }' "$1" 2>/dev/null
}

# run_guard_open <marker>: one "  - <target>: <what is open>" line per open target; nothing when finished.
run_guard_open() {
  local KIND A B ROW STATE
  while IFS=$'\t' read -r KIND A B || [ -n "${KIND}" ]; do  # `|| [ -n ]`: a last line without a newline
    A=${A%$'\r'}; B=${B%$'\r'}  # a CRLF marker
    case "${KIND}" in
      task)
        if compgen -G "${A}/docs/tasks_manager/_todos/${B}-*.md" >/dev/null; then
          ROW=""
          STATE="${A}/docs/tasks_manager/_runs/${B}/state.md"
          [ -f "${STATE}" ] && ROW=$(first_open_row "${STATE}")
          if [ -n "${ROW}" ]; then
            echo "  - ${B}: phase ${ROW} in ${STATE}"
          elif [ -f "${STATE}" ]; then
            echo "  - ${B}: every phase is committed; final validation, final review and closeout remain"
          else
            echo "  - ${B}: not started (no run state yet)"
          fi
        fi ;;
      state)
        if [ -f "${A}" ]; then
          ROW=$(first_open_row "${A}")
          [ -n "${ROW}" ] && echo "  - ${A}: phase ${ROW}"
        else
          echo "  - ${A}: the state file is missing; find it or disarm with: at run-guard disarm"
        fi ;;
    esac
  done < "$1"
}
