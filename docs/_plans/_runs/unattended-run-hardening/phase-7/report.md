implementer, phase 7 (text only). Status: DONE.
- unattended-run/SKILL.md: step 3 bullet with the four always-asked questions (review cap, lane cap, refusal, shared resource), each with a recommended default through `agents-core:ask`; step 4 template lines `At review cap:`, `Lanes:`, `On refusal:`, `On shared resource:`; note that `at task run` gets `--at-review-cap` and `--lanes`.
- README.md: unattended-run block (status file, compaction reminder, `arm --watch` and caps, `at task report`, driver marks, `--lanes N`, live suite), pointing at run-state.md.
- seed/AGENTS.md: one bullet (turn-end `Run:` lines, report path, a watched run may be restarted).
- CHANGELOG.md Unreleased/Added: eight entries. No version touched.
- run-state.md, Scripted driver: recovery after a rejected wave commit.
Concern: `--retry-blocked` only helps after the lane worktree and branch are removed; written that way, not re-checked in code.
Checks: build ok, run-all ok; SKILL.md 167 and 371 lines.
