Reviewer: agents-core:reviewer (workers, guard, digest), 2026-11-27. Findings verbatim; the evidence section is shortened.

## Status: DONE
## Verdict: PASS
## Findings: 3 (C:0 I:2 M:1)
1. [I] plugins/agents-core/lib/sup_workers.py:861 — a hub-root file entry adds the whole hub as a worker directory. Repro: profile `local: [".env"]`, `.env` in the hub and ignored, `start-worker RM-1`. All four argv forms end in `--add-dir <hub>`. The worker runs `--permission-mode auto`, so it gets the landing checkout, including the hub's `CLAUDE.md`/`.claude` that `land` gates with `--allow-claude-files`. Should: refuse or skip a file entry whose parent is the hub root, or a directory with tracked files.
2. [I] plugins/agents-core/lib/sup_workers.py:681 and plugins/agents-core/lib/sup_digest.py:275 — `accept-tip` refuses only a live worker, not a task that still holds the repo (`_held`). Repro: pack `a` with `--branch sib=feat/x`, RM-1 row `stopped` or `done`, unlanded, 2 commits on `feat/x`; `accept-tip a sib` returns 0. Then `land_ranges` gives old == new, so the hub landing commit gets no `sib feat/x old..new` line, and the done check reports nothing. The digest prompts this: while RM-1 runs it prints `a/sib: RM-1 2 commit(s) above the landed tip on feat/x (at sup accept-tip a sib)`. Should: refuse while `_held` names an unlanded task for the slug, and drop the hint on rows that have a holder.
3. [M] plugins/agents-core/lib/sup_workers.py:850-853 (used at 215, 223) — a wake silently drops every `--add-dir`. Three cases, links still in the worktree each time: `profile.json` is unreadable; one invalid entry (`../x`) was added after the start; the profile has no `hub` key, the worker was started with `--hub`, and the wake runs from another cwd. Resume argv is `['--bg','--resume',sid,'go']`, nothing logged. Should: log it, or fail the wake.

## Evidence (shortened)
- Probes: scratchpad `post-workers/probe1.py`, `probe2.py`, `probe3.py`, on the fixture of `scripts/tests/test_sup_workers.py`.
- Held: argv forms (entries cannot be read as flags, prompt precedes `--add-dir`), link cases, accept-tip states and callers (worker, supervisor, guard: refused), profile lock, a broken pack does not stop healthy packs, `_waits` wording, 1.17.0 pack and profile shapes.
- Not verified: `--add-dir` with a real `--bg` session; a hub entry that is a symlink leaving the hub.
