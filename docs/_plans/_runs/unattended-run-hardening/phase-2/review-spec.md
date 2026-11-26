reviewer (spec), phase 2. Verdict: FAIL, findings 0/1/3. test-hooks 311/0, test-at 358/0. Checklist: command source partly (finding 1); at notify, hook kinds, skill step 2, body and README, Shape (68 code lines), E3 scenario: met.
1. [important] lib/at.py:1510 with README.md:94: the command runs as `sh -c <cmd> agents-notify <title>`, so `$1` exists only inside the shell string; README's example `agents.notifyCommand 'my-sender'` starts my-sender with no arguments (reproduced: empty title). No test catches it: all use an inline `{ echo "$1"; cat; }`. Fix: append `"$@"` to the command, or change the examples.
2. [minor] at.py:1493-1499: the `.sent/<key>` file is created before the command is looked up or run: no command set, or a failed or timed-out send, burns the key for that arm.
3. [minor] test-at.sh:436-455, test-hooks.sh:891-931: no test fails if the 10 s timeout is removed, none covers GAVE_UP notifying or env-over-git precedence.
4. [minor] live/e3-notify.sh:22: the wait loop ends at the first `Run BLOCKED` line; a late second send could land after the count.
## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 0/1/3
