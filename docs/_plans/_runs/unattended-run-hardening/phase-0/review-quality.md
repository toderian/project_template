reviewer Stage: quality, phase 0, round 0. Verdict: FAIL, findings 1/5/4. Reproductions used a stub claude.
1. [critical] live/lib.sh:29,67 + e1-guard-holds.sh:26,44,54,64: a setup failure starts the session in the caller's cwd (the real repo): `fail` inside `REPO=$(fresh_repo ...)` exits only the subshell, REPO is empty, `cd "" && claude -p --permission-mode acceptEdits` runs in place. Fix: `set -euo pipefail` in lib.sh, `REPO=$(...) || exit 1`, run_claude refuses any repo not under "${SCRATCH}"/ with a .git.
2. [important] lib.sh:14: mktemp failure unchecked: SCRATCH empty, guard dir becomes /guard, repos /main.
3. [important] lib.sh:67: Ctrl-C does not stop a session or the suite (timeout has its own process group; no INT/TERM trap, no -k). Use `timeout --foreground -k 10` or a trap that kills the child and exits 130.
4. [important] e1-guard-holds.sh:32,71: no retry, sample of 2; main fails when the model does phase 2 unprompted; negative 3 needs exactly six bare replies. Bounded retry in the runner (each attempt keeps its scratch dir), or treat "phase 2 done with zero exit-2" as inconclusive and rerun.
5. [important] lib.sh:85-87: stop_hook_codes takes every Stop hook_response, not only run-guard's. Filter on the hook command containing run-guard.sh.
6. [important] lib.sh:19-27,75: a failing scenario never prints the session transcript path; transcript_of has no caller.
7. [minor] facts file:36, 38-39, 48: personal home path, real session ids and a pid in a committed file. Use `~/.claude/projects/...` and `<session-id>`.
8. [minor] lib.sh:31,67: `timeout` not in `need`; `sort -uV` is GNU-only.
9. [minor] lib.sh:80: passing runs leave transcripts under ~/.claude/projects/ for deleted scratch repos.
10. [minor] lib.sh:83: comment names stop_hook_events, function is stop_hook_codes.
## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 1/5/4
