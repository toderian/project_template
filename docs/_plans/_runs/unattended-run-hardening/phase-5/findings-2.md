# Phase 5, open findings for fix round 2

Sources: re-review-1.md and re-review-1-security.md in this directory. Rounds 1 and 2 both touch
plugins/agents-core/lib/task_run.py: this round must not add net code lines to it beyond what the
items below strictly need; prefer tightening the two existing functions (`run_policy`,
`may_commit_open`) over new ones. Every fix needs a test that fails without it.

1. [I] Policy source. `unattended` and `At review cap` are read from the task file at the run's
   base revision (`base_rev` in state.md; for a run that is just opening, the HEAD at that moment),
   never from a later HEAD, so neither a rerun nor an implementer's commit changes them. In a chain
   every task's policy is read in `preflight`, before the first dispatch. The owner's way to change
   the cap rule for a run in progress is a command-line flag `--at-review-cap park|continue`
   (overrides the file; document it in run-state.md). (re-review A, security original 3)
2. [I] The Execution row is comma-separated: `orchestrated, unattended`, `unattended, parallel`
   and `unattended` alone are unattended; `not unattended` and `unattended is forbidden here` are
   not. Parse the cell into values and compare each exactly. Ignore `~~~` fences, HTML comments and
   an unclosed fence the same way as backtick fences. (re-review B, security residual 5)
3. [I] `may_commit_open` accepts a review only when its verdict is FAIL with at least one parsed
   finding, the header is the strict form `N (C:x I:y M:z)` (optional spaces after the colons and
   commas are read, not ignored) with x+y+z == N == parsed count, and no critical anywhere.
   Everything else parks: zero parsed findings, the `a/b/c` form, a header without a count.
   State in run-state.md that a reviewer reply without a counted header (the security auditor's
   today) therefore always parks. (security original 1, re-review C)
4. [M] The DispatchError note records the role and points at driver.log; no harness stderr goes
   into state.md. (security new 8)
5. [M] A rerun that changes nothing adds no duplicate `Note:` and makes no new run-state commit.
   (re-review D)
6. [M] run-state.md: a dispatch failure or timeout exits 4 in an unattended run, 1 otherwise.
   (re-review E)
