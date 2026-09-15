# Runtime: inline (no subagents)

Use this reference when no subagent tool exists in the session, or the user asked for inline
execution. You play every role yourself, sequentially, and you say so: every review written this
way is labelled **not independent** in the execution log and in `state.md`.

The run directory and `state.md` are still written exactly as in `references/run-state.md`, so a
later session with subagents can resume the run and apply real reviews from the first uncommitted
phase on.

## Per phase (replaces step 5.4–5.8)

1. Write the brief (`at task brief`, plus orchestrator notes) as usual. It is your own contract for
   the phase: implement only what it says.
2. Implement the phase within the scope fence. Run the phase checks and related tests; read the
   output. Write `phase-N/report.md` in the implementer report shape (status block, files changed,
   checks with real output).
3. Package `diff.patch` from `BASE`.
4. Review your own diff **in a separate pass, after a context break**: close the source files, reopen
   the brief and the diff, and go criterion by criterion. Write `review-spec.md` and
   `review-quality.md` in the reviewer reply shape, and `review-security.md` when the phase touched a
   security surface. Head each file with `Independence: none — main-thread self-review`.
5. Fix what you found, re-run the checks, and record the findings you left open as `Ruling:` lines.
   The three-round cap still applies: it bounds how long you keep polishing one phase.
6. Continue with step 5.9 (verify, record, commit, close the row). Add `(inline, self-reviewed)` to
   the `reviews:` line of the commit message.

## Architecture and final review (steps 4 and 7)

- Step 4: read the plan against the affected code and write `architecture-review.md` with the
  `## Architecture verdict:` block, labelled not independent. A `REVISE` you issue yourself still
  updates the plan before code edits.
- Step 7: do not pretend two reviewers ran. Write one whole-task self-review to
  `final-review-1.md`, then **stop and ask the user** whether to accept it as the final review or to
  rerun step 7 in an environment with subagents. Record the answer in the execution log.

## What inline does not change

- The orchestrator-owned commit rules and the pathspec staging.
- The per-phase execution-log entry and its pointer to `phase-N/`.
- `at ledger check` and `at task run-state check` after each phase.
- The rule that a phase with an unruled open finding is never committed.
