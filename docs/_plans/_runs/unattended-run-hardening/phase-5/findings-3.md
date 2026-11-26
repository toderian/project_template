# Phase 5, fix round 3 — the structural round

Rounds 1 and 2 each grew `plugins/agents-core/lib/task_run.py` and each left the same hole open in
a new place: the rule "may an unattended run commit a phase with open findings" was read from
files (the task file, state.md, a revision name) that the implementer the driver itself dispatches
can write. No amount of pinning closes that. This round removes the cause instead of adding a guard.
`task_run.py` must end this round with FEWER added lines than it has now (+212/-33 against 54e23a5).

Decided by the orchestrator (recorded as a Decision: in state.md):

1. [I] `continue` at the review cap comes ONLY from the command line: `--at-review-cap park|continue`,
   default `park`. The driver never reads an `At review cap:` line from any file. Delete the
   base-revision lookup, `git show`, and the cap-line parsing; `preflight` no longer reads policy.
   (re-review-2 F1, N2; security 2, 6)
2. [I] `unattended` (which only decides `parked` + exit 4 versus `blocked` + exit 1, never a commit)
   is read from the task file as loaded, by splitting the `| Execution | ... |` row's cell on commas
   and comparing values exactly. Delete the fence and comment stripping. (N1)
3. [M] The review header: `re.fullmatch` the parenthesised detail as C, I, M counts once each
   (optional spaces), and park when a reply has more than one `## Findings:` line. (security new 5)
4. [M] A dependency-parked row is recognised from its current reason, not from note order: after a
   dedupe the row parked only for a dependency still reruns once that dependency commits. (N3)
5. Tests: replace the policy-from-file tests with: the flag alone enables continue; a task file
   that says `At review cap: continue` without the flag parks; a chain with the flag applies it to
   every task; `orchestrated, unattended` is unattended; a task file with a closed code fence above
   the metadata still reads as unattended; two `## Findings:` headers park. Remove tests whose
   subject no longer exists.
6. run-state.md "Scripted driver": the flag is the only source; say why in one sentence (the task
   file is writable by the implementers the driver dispatches). Remove the base-revision text.
