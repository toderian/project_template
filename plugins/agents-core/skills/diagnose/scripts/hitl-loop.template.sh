#!/usr/bin/env bash
# Human-in-the-loop reproduction loop, for the last-resort case where a person
# must click something the agent cannot. Copy this file, edit the steps at the
# bottom, and run it: the agent runs the script, the user answers in their
# terminal, and the captured values come back on stdout for the agent to parse.
#
#   step "<instruction>"        show an instruction, wait for Enter
#   capture VAR "<question>"    ask a question, read the answer into VAR
#
# `capture` echoes what the user types, and the agent reads that terminal
# output, so capture *observations* only. Anything secret — signing in, pasting
# a token — belongs in a `step`, where nothing is echoed back.

set -euo pipefail

step() {
  printf '\n>>> %s\n' "$1"
  read -r -p "    [Enter when done] " _
}

capture() {
  local var="$1" question="$2" answer
  printf '\n>>> %s\n' "$question"
  read -r -p "    > " answer
  printf -v "$var" '%s' "$answer"
}

# --- edit below: one step or capture per action -------------------------

step "Open the app at http://localhost:3000 and sign in."

capture ERRORED "Click 'Export'. Did it fail? (y/n)"

capture ERROR_MSG "Paste the error message, redacting anything secret (or 'none'):"

# --- edit above ---------------------------------------------------------

printf '\n--- Captured ---\n'
printf 'ERRORED=%s\n' "$ERRORED"
printf 'ERROR_MSG=%s\n' "$ERROR_MSG"
