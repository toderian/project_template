reviewer (quality), phase 4. Verdict: FAIL, findings 1/4/5. Passed: test_run_watch 13 OK, run-all ok, test-hooks 5 of 5 runs 319/0 (the flaky failure did not reproduce); 26 mutants, 21 killed; no spin, child reaped, log capped, claim race leaves one watcher.
1. [critical] lib/run_watch.py:285,379,402 + lib/at.py:1478: restart count and budget live only in watcher memory; a new `arm --watch` resets both. Case: a resumed session re-arms with --watch (what execute-plan step 3 tells it to do) then dies: 6 restarts at cap 1, 6.00 USD of caps.
2. [important] run_watch.py:368,393: a watcher killed mid-resume and restarted starts a second `claude --resume` of the same session while the first still runs: the child pid is recorded nowhere.
3. [important] run_watch.py:362 + at.py:1487: a marker with no targets reads as "finished": `arm` rewrites the marker non-atomically; an empty marker, or an unreadable state.md, gave "Run finished: " and watcher exit 0.
4. [important] scripts/tests/test_run_watch.py:181-184: the "never signals a non-watcher pid" test cannot fail (the killed process stays a zombie, so _pid_alive stays true).
5. [important] size flag unjustified (342 against ~300). Deletable: split_watch_flags + VALUE_FLAGS (parse_known_args does it), the macOS `ps` branch of _cmdline, _target_paths, ID_RE: about 25 lines.
6. [minor] run_watch.py:198,368: str.isdigit() accepts `²`; int() raises: watcher rc 1; `status` and `disarm` traceback.
7. [minor] run_watch.py:403: budget rounding: 0.05/20 passes 0.00; 0.2/3 passes 0.07 three times.
8. [minor] test_run_watch.py:68-72: live() leaves an orphan `sleep 30` holding stdout.
9. [minor] run_watch.py:353: a resume outlives the watcher after --until, unlogged.
10. [minor] untested (mutants survived): cwd work tree must hold a guarded file, pause doubling, 64 KB log cap, `allow bypass` in every task vs any; two `arm --watch` racing: the loser prints "the watcher did not start" rc 1 though one runs.
## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 1/4/5
