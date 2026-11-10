#!/bin/bash
# SessionStart hook: say once, in one line, when this repo has fallen behind the plugin seed
# (routing rows, removed skill ids, seed plugins, permission rules, legacy tree). Both Claude Code
# and Codex add a SessionStart hook's stdout to the model's context, so the agent can offer
# agents-core:setup-project instead of the drift waiting for someone to run `at doctor`.
#
# Never blocks and never fails a session: prints nothing for a repo that is current or was never
# seeded, and exits 0 whatever happens (missing jq or python3, not a git repo, unreadable files).

INPUT=$(cat 2>/dev/null)
CWD=""
if command -v jq >/dev/null 2>&1; then
  CWD=$(printf '%s' "${INPUT}" | jq -r '.cwd // empty' 2>/dev/null)
fi
CWD=${CWD:-$PWD}

AT="$(cd "$(dirname "${BASH_SOURCE[0]}" 2>/dev/null)/.." 2>/dev/null && pwd)/bin/at"
if [ -x "${AT}" ] && command -v python3 >/dev/null 2>&1 && cd "${CWD}" 2>/dev/null; then
  "${AT}" doctor --drift 2>/dev/null
fi
exit 0
