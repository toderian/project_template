reviewer Stage: quality, phase 1, round 0. Verdict: PASS, findings 0/5/4. test-hooks 274/0, test-at 333/0.
1. [important] hooks/run-guard.sh:92: send-back text regression: `OPEN=$(run_guard_open ...)` strips the trailing newline, the last open row and "Continue at the first open row" are glued. No test reads the stderr body.
2. [important] run-guard.sh:45 + lib/at.py:1421: `cut -c1-300` cuts bytes; a multibyte character cut in half makes `at run-guard status` die with UnicodeDecodeError, and any later Python reader too.
3. [important] at.py:1438-1439: prune calls old.stat() without the old is_file() guard: a dangling symlink or a concurrent unlink makes `arm` traceback before the marker is written (run starts unguarded). It also rmtree's every directory older than 14 days, not only *.sent.
4. [important] hooks/lib/run-open.sh:20,36 + run-guard.sh:59: a sticky false `kind=DONE` on an unfinished run for: a state target whose state.md vanished; a marker with CRLF; a marker with no trailing newline (read drops the last line).
5. [important, older code] run-guard.sh:79-87: with the guard dir read-only or the disk full, .count is never written, the five-sent-back cap never fires: the session is trapped. write_status fails silently too.
6. [minor] run-guard.sh:73: `case *BLOCKED*` matches the whole line.
7. [minor] run-guard.sh:34: the lib is sourced before the no-marker check; a missing lib prints an error on every stop of every session.
8. [minor] at.py:1380-1388: _run_guard_clear leaves `<session>.status.<pid>` temp files.
9. [minor] tests assert too little: 300 cap and flattening of text, missing lib, path with spaces, arm without CLAUDE_PID, send-back body; `remind: missing jq` passes even if the hook never runs.
## Status: DONE
## Verdict: PASS
## Findings: 0/5/4
