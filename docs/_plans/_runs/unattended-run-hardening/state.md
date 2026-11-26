---
task: unattended-run-hardening
task_file: docs/specs/2026-11-26-unattended-run-hardening-plan.md
runtime: claude
mode: large
mode_reason: 8 phases; hook and subprocess surfaces
base_rev: da43501
branch: master
work_mode: default-branch
autonomy: L1
current_phase: 3
updated: 2026-11-26T00:00:00
---
# Run ledger — unattended-run-hardening

| Phase | Status | Attempt | Spec | Quality | Security | Open | Commit | Agent |
|---|---|---|---|---|---|---|---|---|
| 0 | committed | 2 | PASS | PASS | n/a | 0 | 0063376 | — |
| 1 | committed | 2 | PASS | PASS | PASS | 0 | 721558a | — |
| 2 | reviewing | 2 | PASS | PASS | PASS | 0 | — | — |
| 3 | implementing | 1 | — | — | — | 0 | — | — |
| 4 | pending | 0 | — | — | — | 0 | — | — |
| 5 | committed | 4 | PASS | PASS | PASS | 0 | 52e97e9 | — |
| 6 | fixing | 2 | FAIL | FAIL | FAIL | 14 | — | — |
| 7 | pending | 0 | — | — | — | 0 | — | — |

Phase 0: BASE 54e23a5
Phase 5: BASE 54e23a5 (lane B)
Note: plan without the task ledger; run directory written by hand per references/run-state.md
Note: order per the revised plan: phase 0; lane A = phases 1, 2, 3, 4 serial; lane B = phases 5, 6 in a worktree; merge B after phase 4; phase 7 last
Note: this session runs the installed plugin (1.14.0), whose hooks lack run-guard.sh; the guard is armed but no hook reads it here
Note: architecture review: plan-critic REVISE (6 blocking), peer codex REVISE (4); plan revised and reconciled, no rerun
Decision: watchdog budget per resume or total — total, divided by the resume cap — why: the smaller spend of the two readings of D3 — cost if wrong: a resume runs out of budget early and the owner raises it
Decision: may the watchdog resume a session recorded in bypassPermissions — no, unless arm was given --allow-bypass, recorded per task — why: an unattended restart in bypass mode is the largest risk the review named — cost if wrong: a night run in bypass mode is not restarted until the owner adds the flag
Decision: where the live suite runs — by hand per phase and before release, not in run-all.sh — why: pre-commit runs run-all.sh and the suite spends tokens — cost if wrong: a regression is seen at release instead of at commit
Decision: report filename date — commit date of base_rev, keeping D2's pattern — why: a rerun after midnight must name the same file — cost if wrong: the date shows the run's start, not the morning it is read
Note: lane B: worktree ../project_template-lane-b, branch lane-b/driver, phases 5 then 6; phase 5 started alongside phase 0 without its E7 scenario, which is added once the phase 0 harness is merged into the lane
Interface: Runner.runnable(state, pending) -> list[int]; phase_deps(task, n) -> list[int] in lib/task_run.py (phase 5, for phase 6)
Phase 5: fix round 1/3 (12 open: spec 0/2/2, quality 1/4/3, security 0/4/3, merged in phase-5/findings-1.md)
Phase 0: fix round 1/3 (9 open: spec 0/2/4, quality 1/5/4, merged in phase-0/findings-1.md); security n/a (test harness and a document, reviewed for session safety under quality)
Note: Phase 5 fix 1: code net +76 (plugins/agents-core/lib/task_run.py), now +185/-26 against a Shape of ~150
Phase 5: fix round 2/3 (round 1 closed 10 of 12; 6 open: 3 important, 3 minor, in phase-5/findings-2.md)
Phase 0: re-review PASS 0/0/3; minors A, B fixed by the orchestrator and E1 rerun green on the real CLI
Ruling: facts file wording (stream vs transcript, "fires at the interval" on one firing) — accepted as-is — cost if wrong: a reader overestimates the scheduler evidence; fact 5 is already "partly"
Interface: hooks.json has a SessionStart matcher for startup only; phase 1 adds resume and compact (facts 2)
Interface: the session process id is CLAUDE_PID in the Bash tool environment, not $PPID (fact 3); the Stop payload carries permission_mode (fact 8)
Interface: scheduler wakeups never fire under claude -p, and -p stays alive only while a background job runs (facts 5, 9): the watchdog's headless resume cannot rely on the heartbeat
Interface: live scenarios are scripts/tests/live/eN-<name>.sh sourcing live/lib.sh (fresh_repo, run_claude, stop_hook_codes, row_status, marker_inactive, fail); run with bash scripts/tests/test-unattended-live.sh EN
Phase 1: BASE 0063376
Note: Phase 5 fix 2: code net +20 (plugins/agents-core/lib/task_run.py), now +212/-33; rounds 1 and 2 both grew it, so a round 3 would be the structural round
Interface: the marker and .status are writable by the session itself: the phase 4 watchdog must not take the resume permission mode or the authorisation from them alone; verify the pid is a claude process; parse .status on \n only (phase 1 security review)
Phase 5: fix round 3/3, structural (rounds 1 and 2 both grew task_run.py; open: policy source forgeable by the implementer in two new ways, fence regex; phase-5/findings-3.md)
Decision: where the driver takes "continue at the review cap" from — only the --at-review-cap flag, never a file — why: every file the driver could read is writable by the implementers it dispatches, and two rounds of pinning each left a bypass — cost if wrong: the owner or the starting agent must pass the flag; a task file line alone no longer enables it
Phase 1: fix round 1/3 (spec 0/2/4 FAIL, quality 0/5/4 PASS, security 0/1/4 PASS; 12 merged in phase-1/findings-1.md)
Note: Phase 5 fix 3: code net -19 (plugins/agents-core/lib/task_run.py), now +196/-36; the structural round shrank the file
Phase 5: at the cap after round 3: spec+quality PASS 0/2/4, security FAIL 0/1/1 with its three open items closed. Orchestrator fixed: implementer-commit check (HEAD against the phase base after every implementer dispatch, aborts the run), findings header anchored to end of line, `waits` documented, test debris removed; 38 tests OK, run-all ok. Committed on lane-b/driver as 52e97e9
Ruling: security 1 (driver never checked HEAD against the phase base) — fixed at the cap by the orchestrator with a test, not re-reviewed per phase; the final review covers it — cost if wrong: a defect in a 6-line check reaches the final review
Ruling: chain test does not prove the flag reaches a second task — accepted, the flag lives in the shared args object — cost if wrong: a later refactor that copies args per task loses the flag unnoticed
Ruling: peer.py skips the count check on a reply with two Findings headers — accepted as-is — cost if wrong: one malformed peer reply is stamped without its count being compared
Ruling: Open stays 0 on a row committed by continue; --retry-blocked can relabel a self-parked row as waits — accepted, both visible in the Decision: and Note: lines — cost if wrong: the Open column understates, or one row reruns without --retry-blocked after its dependency commits
Ruling: task_run.py +206/-37 against a Shape of ~150 — accepted: the review-driven additions (set-aside path, fail-closed gate, preflight, implementer-commit check) are each one single-purpose function and the structural round removed the policy reader — cost if wrong: a denser driver file
Interface: at task run exit codes: 0 all committed, 1 blocked or aborted, 2 bad arguments, id or After: graph, 4 finished with parked rows or a skipped chain task; flag --at-review-cap park|continue (phase 5)
Interface: Runner.must_not_have_committed(n, base), Runner.set_aside(state, n), Runner.runnable(state, pending), phase_deps(task, n), after_problems(task) in lib/task_run.py (phase 5, for phase 6)
Phase 6: BASE e46cb2c (lane B, after merging master 0063376 into the lane)
Phase 1: re-review 1 PASS 0/2/2, findings 1-12 closed. Orchestrator fixed N1-N4 and both test flakes: a missing state file lets the stop through as GAVE_UP; test-at pipe helpers use here-strings; the count file is read digits-only; marker 600 and guard dir 700; the hook reads stdin before its early exits. Live E1 then failed once: a redirect error on the missing count file printed "No such file" to stderr and the harness treated the hook as missing; fixed with a test. test-hooks 296/0, test-at 348/0, run-all ok, live E1 E2 PASS
Ruling: N1-N4 and the flake fixes were made by the orchestrator after a PASS verdict and not re-reviewed per phase; the final review covers them — cost if wrong: a defect in about 15 changed lines reaches the final review
Interface: any text a hook prints to stderr before its send-back can make the harness ignore the send-back ("No such file or directory" reads as a missing hook script): hooks keep stderr clean (phase 1, for phases 2-4)
Interface: .status kind=GAVE_UP also means "only missing state files are left"; kind=DONE is the only sticky inactive state (phase 1, for phases 2-4)
Phase 2: BASE 721558a
Phase 2: reviews spec FAIL 0/1/3, quality FAIL 1/4/4, security PASS 0/1/3; fix round 1/3 (10 open)
Decision: the notify command is read from AGENTS_NOTIFY_CMD or `git config agents.notifyCommand` in the working directory of `at notify`, which the hook sets from the Stop payload's `.cwd`; the plan said "in the marker's cwd", but the marker is writable by the session, which could then choose the command (phase 2 security review) — cost if wrong: a session whose harness cwd is outside the repo that holds the setting sends nothing; set it with `git config --global` or the environment
Ruling: security 2 (a session can suppress its own notification by pre-creating the dedupe key) — accepted: it can also delete its marker or disarm — cost if wrong: a misbehaving session hides one BLOCKED message; the morning report still lists it
Ruling: security 4 (no rate cap on notifications) — accepted: one message per let-through stop, each needs a new decision text — cost if wrong: a looping session sends the owner one message per turn
Note: Phase 2 fix 1: code net +16 (plugins/agents-core/lib/at.py, plugins/agents-core/hooks/run-guard.sh)
Phase 6: reviews spec FAIL 0/2/3, quality FAIL 2/4/4, security FAIL 1/2/3; fix round 1/3 (14 open), on the strongest model with a decided design
Decision: a wave in the scripted driver is a transaction: merges by recorded SHA, tick and bookkeeping only after the wave review passes, a failed wave review or stray files reset the integration branch to the wave base and park the lanes; a rerun that finds an unfinished wave stops and prints the recovery command, it resets nothing by itself — cost if wrong: after a kill mid-wave the owner runs one `git reset --hard <sha>` by hand before the rerun
Decision: the driver commits a phase only when the tree equals the tree that was reviewed (git write-tree at packaging and before the commit), in serial and lane mode — cost if wrong: a check command that legitimately rewrites tracked files after review parks the phase
Ruling: security 5 (driver git calls honour hooks in the shared .git) — accepted: the repository's pre-commit gate must run on driver commits — cost if wrong: an implementer that can write .git/hooks adds files to a driver commit; the final review diff still shows them
Phase 3: BASE 721558a (lane C, worktree ../project_template-lane-c, branch lane-c/report)
Decision: Phase 3 runs in a third worktree while Phase 2 is still in review (the plan said After: 2 because both edit unattended-run/SKILL.md): the owner asked in chat for parallel threads; the fences are disjoint regions (step 2 against step 6) and the orchestrator merges — cost if wrong: one hand-resolved merge conflict in SKILL.md, at.py or run-state.md
Phase 2: re-review 1 FAIL 0/1/3 (findings 1, 2, 4-10 closed). Orchestrator closed the rest: the notify command is split with shlex and run without a shell, title as the last argument (the `"$@"` suffix from findings-1 broke snippets and switched dedupe off); both hooks read stdin with a builtin (no `cat` on a stripped PATH); the send no longer needs a valid payload cwd; the guard dir is made absolute before the cd. test-hooks 319/0, test-at 374/0, run-all ok, live E1 E3 PASS
Decision: the owner's notify command is a program with optional arguments run without a shell (title appended as the last argument, body on stdin); shell snippets go in a script — replaces the round-1 design `sh -c '<cmd> "$@"'` — cost if wrong: an owner who wants a one-line curl must write a two-line script
Ruling: re-review N1-N4 fixed by the orchestrator after the round and not re-reviewed per phase; the final review covers them — cost if wrong: a defect in about 12 changed lines reaches the final review
Interface: `at notify <title> [--event KEY --session ID]` (body on stdin, always exit 0 unless usage error 2); command from AGENTS_NOTIFY_CMD or `git config agents.notifyCommand` in the caller's cwd; dedupe by exclusive create of `<session>.sent/<KEY>`, key removed when the send fails; AGENTS_NOTIFY_TIMEOUT 0.1-10 s for tests (phase 2, for phase 4)
