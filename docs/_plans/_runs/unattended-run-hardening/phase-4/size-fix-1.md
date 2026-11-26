# Size, phase 4 after fix round 1 (hand-written; whole phase against d322b16)
```
1	0	README.md
58	15	plugins/agents-core/lib/at.py
472	0	plugins/agents-core/lib/run_watch.py
12	0	plugins/agents-core/skills/execute-plan/SKILL.md
33	0	plugins/agents-core/skills/execute-plan/references/run-state.md
7	0	plugins/agents-core/skills/unattended-run/SKILL.md
120	0	scripts/tests/live/e5-watchdog.sh
75	0	scripts/tests/live/e6-heartbeat.sh
1	0	scripts/tests/run-all.sh
346	0	scripts/tests/test_run_watch.py
```
run_watch.py: 350 code lines against the decided ceiling of 350 (round 0: 342). Spent on: watch loop/tick/restart 92, process identity and claim 59, marker/status/scan reading 46, caps parsing 38, record 29, authorise 27, notify and log 27, constants and prompt 32.
