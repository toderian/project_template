reviewer (spec), phase 4. Verdict: FAIL, findings 0/1/7. Every functional checklist item met (heartbeat text, tick rules, limits, one watcher/disarm/status, unattended-run step 4, tests, E5 by reading, E6 as the brief allows, scope fence, skill ids); the FAIL rests on the Shape line only. test_run_watch 13 OK, test-at 374 passed, build --check ok, 8 fake-claude probes.
1. [important] lib/run_watch.py: 342 code lines against a Shape of <= ~300, with no recorded reason (candidates to trim: the `ps` fallback at :176-180, SESSION_ENV).
2. [minor] skills/execute-plan/SKILL.md:184-185: "Claude Code's `CronCreate`" names a product tool in the skill body.
3. [minor] run_watch.py:403: `--budget-usd 0.01` with 4 restarts passes `--max-budget-usd 0.00`; parse_caps should reject a share below 0.01.
4. [minor] run_watch.py:76-84: `arm --watch --budget-usd=4 TST-001` fails ("--budget-usd=4 is neither a file nor an open task"); the `=` form works on `watch` only.
5. [minor] scripts/tests/live/e6-heartbeat.sh:76: with E6_PART=dead-job the script exits 0, so the harness prints PASS E6 although only half ran.
6. [minor] e6-heartbeat.sh:28-30: manual step 4 (nohup outside the session) contradicts steps 1-2; split into two numbered runs.
7. [minor] state.md Interface line says `--budget USD`; the code says `--budget-usd`.
8. [minor] run_watch.py:367-368: liveness is the recorded `meta pid` only: an owner resuming by hand after a crash, before the session re-arms, gets a second `claude --resume` of the same id; not stated as a limit in run-state.md.
## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 0/1/7
