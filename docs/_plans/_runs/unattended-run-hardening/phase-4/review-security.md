security-auditor, phase 4. Verdict: FAIL, findings 0/3/4. Reproduced with a fake `claude` and a scratch guard directory unless marked. Passes: no shell, fixed prompt, `claude` resolved by shutil.which at restart time, `.watch` O_EXCL|O_NOFOLLOW, log O_NOFOLLOW and capped, guard dir 0700, log lines and titles ASCII-stripped, the cap holds within one watcher, a forged pid only prevents restarts.
1. [important] lib/at.py:1477 + lib/run_watch.py:285: caps and the restart count do not survive a re-arm: `arm --watch` kills the live watcher and starts one with the caller's flags and resumes=0. Case: owner arms `--max-resumes 1 --budget-usd 1`; each resumed session runs `at run-guard arm --watch --max-resumes 1 --budget-usd 1000`: 7 restarts, six with budget 1000, never "gave-up". Needs only `at`.
2. [important] run_watch.py:260-264: the bypass double key is held by the session: `.status` mode + the task-file line + `--allow-bypass` supplied through finding 1.
3. [important] run_watch.py:333: the session can silence the watcher's alerts: `at notify "all fine" --event gave-up --session s1` (same for restarted-n, idle, refused-*) pre-creates the dedupe key; the watcher's log still says `notify gave-up`.
4. [minor] run_watch.py:269-270: the cwd check accepts a marker `state` path that does not exist.
5. [minor] run_watch.py:34,407: a session id may start with `-` (argv `--resume --dangerously-skip-permissions -p ...`; the installed CLI rejects it today).
6. [minor] run_watch.py:193: is_watcher matches argv members anywhere: `disarm --session 600` kills a watcher whose argv holds `--interval 600`.
7. [minor] at.py:1480 + run_watch.py:260 (code read): any `arm` deletes `.status`; a missing mode becomes `default`, so a `plan` session that re-arms and dies before its next stop restarts in `default`.
## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 0/3/4
