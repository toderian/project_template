Fix round 1 (implementer reply, saved by the orchestrator). All 9 findings reported fixed; E1 passes on the real CLI (42 s); run-all ok.
1 set -euo pipefail, mktemp and REPO failures end the run, run_claude refuses a repo outside ${SCRATCH}/ or without .git; proved with a stub claude (no stub call on TMPDIR=/nonexistent, failing git init, empty repo, real repo).
2 background `timeout -k 10` with a TERM/INT trap, exit 130, runner passes 130 through without retry; need timeout; sort -un.
3 stop_hook_codes <session-id> reads the transcript and counts only stop_hook_summary entries whose command is hooks/run-guard.sh of this tree.
4 fail prints scratch dir, stream file and transcript path.
5 runner retries, default 2 attempts (LIVE_ATTEMPTS), own scratch dir each, reports a pass after retry. Retry path not triggered.
6 negative 1 arms another session on the same repo's open state, then runs a never-armed session there. Not mutation-checked against a guard that ignores the session id.
7 probe session resumed with --resume -p: same session id, run-guard.sh Stop hook_success quoted.
8 bypass refusal and completed pty heartbeat turn marked not observed.
9 home path, ids and pids replaced with placeholders.
Not checked: retry path, real CLI under Ctrl-C (stub only), mutation of negative 1.
