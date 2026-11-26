Phase 2 report (implementer reply, saved by the orchestrator).
## Test plan
Hook (test-hooks.sh): BLOCKED notifies with task id and decision, body ids + reason, exit 0, stdout `{}`; once per event, another decision is another message, DONE once, EMPTY notifies, WAITING sends nothing; never traps (no command, failing command, bad marker cwd, unwritable .sent, slow command); model text is never run. CLI (test-at.sh, 9 asserts): nothing configured, title $1 + stdin body, git config in cwd, exit 0 on failure, --event dedupe, bad key refused. Live: scripts/tests/live/e3-notify.sh.
## Design
Command: AGENTS_NOTIFY_CMD, else `git -C <marker meta cwd> config agents.notifyCommand`; run as `sh -c <cmd> agents-notify <title>`, body on stdin. The hook backgrounds `at notify` with all fds redirected (never waits, prints or alters the exit code); 10 s timeout with killpg. Dedupe: exclusive create `<session>.sent/<kind>-<cksum hash>`, key validated `[A-Za-z0-9._-]+`. Body: `tasks: <ids>` and `reason: <text>`, flattened ASCII, capped; GAVE_UP uses a fixed reason. The call sits in write_status.
## Checks
test-hooks 311/0, test-at 358/0, build ok, run-all ok. Live E1 E2 E3: PASS (E2 failed attempt 1 "no phase 3 commit", passed attempt 2; E3 passed first attempt twice).
## Concerns
E2 flaked once; a state-file-only marker has no task id in the title; cksum is a 32-bit CRC; live spend not measured.
## Status: DONE_WITH_CONCERNS
