# Runtime: inline (no subagents)

Use this reference when no subagent tool exists in the session, or the user asked for inline
execution. The run is in **small mode** whatever its size (there is nobody to dispatch to), and you
play every role yourself, sequentially, and say so: every review written this way is labelled
**not independent** in the execution log and in `state.md`.

The run directory and `state.md` are still written exactly as in `references/run-state.md`, so a
later session with subagents can resume the run and apply real reviews from the first uncommitted
phase on.

## Per phase (replaces step 5.4–5.8)

1. Write the brief (`at task brief`, plus orchestrator notes) as usual. It is your own contract for
   the phase: implement only what it says.
2. Implement the phase within the scope fence. Run the phase checks and related tests; read the
   output. Write `phase-N/report.md` in the implementer report shape (status block, files changed,
   checks with real output).
3. Package `diff.patch` from `BASE` and `size.md` (`at task size <TASK-ID> --phase N`).
4. Review your own diff **in a separate pass, after a context break**: close the source files, reopen
   the brief, the diff and the size table, and go checklist item by checklist item, then quality
   (every flagged file needs a reason you can name). Write `review.md`
   in the reviewer reply shape (`Stage: both`), and `review-security.md` when the phase touched a
   security surface. Head each file with `Independence: none — main-thread self-review`.
5. Fix what you found, re-run the checks, and record the findings you left open as `Ruling:` lines.
   The three-round cap still applies: it bounds how long you keep polishing one phase.
6. Continue with step 5.9 (verify, record, commit, close the row). Add `(inline, self-reviewed)` to
   the `reviews:` line of the commit message.

## Architecture and final review (steps 4 and 7)

- Step 4 does not run inline (small mode); the pre-implementation note in the task file stands.
- Step 7: write one whole-task self-review to `final-review-1.md`, labelled not independent, record
  it in the execution log and continue. Say in the final report that the reviews were self-reviews
  so the user can rerun step 7 with subagents if they want an independent verdict.

## What inline does not change

- The orchestrator-owned commit rules and the pathspec staging.
- The per-phase execution-log entry and its pointer to `phase-N/`.
- `at ledger check` and `at task run-state check` after each phase.
- The rule that a phase with an unruled open finding is never committed.
