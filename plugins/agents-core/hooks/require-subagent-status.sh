#!/bin/bash
# SubagentStop hook: a role subagent (implementer, reviewer, ...) may only finish with the
# report contract from agents-core:subagent-protocol — a `## Status:` line carrying one of the
# shared statuses. Without it the orchestrator cannot route, so the subagent is sent back once
# (exit 2 + reason on stderr; both Claude Code and Codex deliver that as its next instruction).
#
# Never loops: when the harness reports the subagent was already continued by a stop hook
# (`stop_hook_active`), or when it cannot show the final message at all, the stop is allowed.

command -v jq >/dev/null || { echo "hook requires jq; install jq" >&2; exit 2; }

INPUT=$(cat)

ACTIVE=$(printf '%s' "${INPUT}" | jq -r '.stop_hook_active // false')
MESSAGE=$(printf '%s' "${INPUT}" | jq -r '.last_assistant_message // ""')

if [ "${ACTIVE}" = "true" ] || [ -z "${MESSAGE}" ]; then
  echo '{}'
  exit 0
fi

if printf '%s\n' "${MESSAGE}" | grep -qE '^[[:space:]]*(#+[[:space:]]*)?Status:[[:space:]]*(DONE|DONE_WITH_CONCERNS|NEEDS_CONTEXT|BLOCKED)\b'; then
  echo '{}'
  exit 0
fi

AGENT=$(printf '%s' "${INPUT}" | jq -r '.agent_type // "subagent"')
echo "Your reply is missing the report block your brief requires (${AGENT})." >&2
echo "Finish with the structured block, last, exactly in this shape:" >&2
echo '  ## Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED' >&2
echo '  ## Summary: <one line>' >&2
echo "plus the role-specific lines from your brief (Verdict, Findings, Report path). Keep the reply short; the full report goes to the report path." >&2
exit 2
