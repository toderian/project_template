# Open findings, phase 3, round 1

Both reviews failed (spec 0/3/3, quality 1/6/7). Read review-spec.md and review-quality.md here for
the reproductions. Most findings come from one cause: the report is a function of HEAD and of the
user's git configuration instead of a function of the run. Fix the cause.

## Decided design (settled)

A. The report is a function of the run's ledger, not of HEAD.
   - "Commits" lists the commits recorded in the phase rows of state.md, in row order, each as
     `<sha as recorded> <subject>` (subject from `git show -s --format=%s`). No `git log` range by
     default. This is the same file tomorrow, after unrelated commits, and after the report itself
     is committed together with other files.
   - `--since <rev>` adds a second section "Commits since <rev as given>" = `rev..HEAD`, first-parent
     order, excluding commits that touch only `_reports/`. The section header says it depends on
     HEAD; that is what the caller asked for.
   - The file name date is the commit date of `base_rev`. For an archived task whose run directory
     is gone, `base_rev` comes from a `Base: <rev>` line in the task file's `## Completion summary`
     (complete-task copies it there, see finding 3); if that line is absent the date comes from
     `--since`; with neither: exit 2 with a message naming both ways. No `git log --follow` guess.
   - Every git call: `-c` overrides and flags so user config cannot change output
     (`--no-show-signature`, fixed `--abbrev=<n>` or the recorded sha as-is, `-c
     i18n.logOutputEncoding=UTF-8`, `-c core.quotePath=false`), decoded as UTF-8 with
     `errors="replace"`; GIT_CONFIG_GLOBAL is not relied on.
B. "Needs you" holds what is open NOW: rows whose status is `parked` or `blocked`, each with the
   ledger lines that explain it (`Note: parked ...` lines and `Phase N: ...` lines naming that
   phase), and `Note: parked: <question>` lines only while the task has a row that is not
   `committed`. For a task with every row committed, or an archived one, those lines go under
   "Parked during the run" (history), not "Needs you".
C. Writing: resolve the target and refuse when any component of `docs/tasks_manager/_reports/<name>`
   is a symlink or the final path is not a regular file or absent; write to a temp file in the same
   directory and `os.replace`; build every report first, write only if all built. Every failure
   that is the input's or the filesystem's fault is exit 2 with one line, never a traceback.

## Findings (each with a test that fails without the fix)

1. [critical] quality 1: symlinked report file or parent: design C.
2. [important] spec 1, 2 + quality 11: commit list unbounded, rerun differs: design A.
3. [important] spec 3 + quality 8: file renamed after closeout: design A; and
   `agents-tasks:complete-task` copies a `Base: <base_rev>` line into the completion summary.
4. [important] quality 2, 3 + spec 4: git output depends on user config and locale: design A.
5. [important] quality 4 + quality 9: tracebacks and partial writes: design C.
6. [important] quality 5: parked note listed forever: design B.
7. [important] quality 6: blocked row without its reason: design B.
8. [important] quality 7 + spec 5: tests. Cover at least: symlink refusal (file and directory),
   row order, a blocked row with its reason, id dedupe, a state parse error (exit 2), a task with
   neither state nor archive (exit 2), a positive `--since`, `_todos` preferred when a task is in
   both places, driver-form `Note: parked phase N:`, committer date different from author date,
   `at ledger check` passing with `_reports/` present, a rerun after an unrelated commit and after
   the report was committed together with state.md, and hostile git config
   (log.showSignature, core.abbrev, i18n.logOutputEncoding=latin1 with a non-ASCII subject).
   Tests isolate the user's git config and remove their temp repos.
9. [minor] quality 10: an archived task whose run directory still exists also reads its completion
   summary; a task in both `_todos` and `_todos_archived` is reported from `_todos` with a line
   saying both exist.
10. [minor] quality 12: both skills say "`Note: parked` lines (both `Note: parked: <question>` and
    the driver's `Note: parked phase N: ...`)".
11. [minor] quality 13: unattended-run step 6 says the report covers tracked tasks (an id), and
    what to do for a plan-only run (list the same lines by hand from state.md); run-state.md's new
    section names `docs/tasks_manager/_reports/`.

Ruled, do not fix: spec 6 (with `code_repo` set, commits in the other checkout): design A lists the
recorded row commits as text, so they appear without their subject when the object is not in this
repository; say so in one line of the report instead of failing.

Shape: the module is 164 lines against ~200. Design A removes the log-range code and the
`--follow` fallback; stay within ~200 code lines.
