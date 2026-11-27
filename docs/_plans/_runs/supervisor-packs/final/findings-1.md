# Final fix wave: findings for the implementer

Repo: /home/vi/work/repos/project_template. Lib: plugins/agents-core/lib/. Tests: scripts/tests/ (each file is run alone:
`python3 scripts/tests/test_sup_workers.py`). python3 stdlib only. Run only the test files you touch; no full suite.

NOT yours (the orchestrator edits them now, do not touch): `plugins/agents-core/lib/sup.py`, `scripts/tests/test_sup_land.py`.
Do not commit. Do not bump versions. After editing a plugin source run `python3 scripts/build.py`.

Each item needs a test that fails without the fix. Keep fixes small; no new abstractions.

A. [C] sup_workers.py `_link_local` (~line 830): a `local` entry that is an existing hub FILE (`data/cache.db`, `notes.txt`)
   raises FileExistsError from `src.mkdir`. Make the hub directory only for an entry that ends in `/` and is missing; for a
   file entry make only `src.parent` (a missing file is still skipped as today). Also catch RuntimeError (symlink loop,
   `dst.resolve()` on a self-referencing link) as a Refused naming the path.
B. [I] Trial fact (docs/meta/2026-11-26-supervisor-facts.md, last section): a worker session cannot write through a linked
   `local` path, the harness refuses a path that resolves outside its working directories. Probe result: it works when the
   session is started with `--add-dir <hub path of the entry>`. `--add-dir` takes several values, so it must come AFTER the
   prompt argument. Pass `--add-dir` for each linked `local` entry (the hub directory for a `/` entry, the parent directory
   for a file entry; only those that were linked) on every worker start AND every wake/resume (headless `-p`, `-p --resume`,
   `--bg`, `--bg --resume`; find them in sup_workers.py and sup_watch.py). No `local` entries: argv unchanged.
C. [I] sup_workers.py `next_tasks` (~347, 362): `_held` and `_pack_repos` are called outside its `try`; one unreadable task
   file (byte \xff) in a pack with branches raises Refused out of `next_tasks`, and the watcher's `_starts` then fails for
   every pack. Such a pack must be handled like a pack `_edges` refuses (its tasks late, the start refusal names the cause).
D. [I] sup_workers.py `_repos` (~247, 254): a non-UTF-8 `.local/repos.map` or `.config/repos.project.md` raises
   UnicodeDecodeError. Raise Refused naming the file. `at sup status` must print no traceback (one line in the digest).
E. [I] A pack tip can go stale for ever (an owner fixup commit above the landed tip; a worker amended a landed commit):
   `at sup done <pack>` then exits 3 for ever and `close-pack` keeps the worktree. Add an owner command
   `at sup accept-tip <pack> <slug>`: records the current head of the pack branch as the landed tip. Refuse: unknown pack or
   slug, dirty pack worktree, a live worker row of that pack whose task names the repo. Owner's chat only (like
   `start-pack`); it must NOT be in the supervisor session's allow-list of sup_guard.py (add a guard test that it is
   denied). The `done` and status lines that report "above the landed tip" / "not an ancestor" name the command. One
   sentence in plugins/agents-tasks/skills/supervise/SKILL.md where `at sup done` is described.
F. [I] sup_digest.py `_waits`: status shows a reason only for `Blocked by`. A task that waits because another task of the
   pack holds its repo (and that task is stopped or running) must show `waits for <ID> (repo <slug>)` or similar.
G. [M] sup_workers.py `_write_map` (~801): OSError (`.local` is a file, `repos.map` is a directory) → Refused naming the path.
H. Test gaps (mutations that survived; add the assertion, no code change expected):
   1. test_sup_workers.py:561 "an archived blocker outside the pack does not block": passes with
      `and not any((hub / sup.ARCHIVED).glob(...))` removed from `_blockers`. Assert `_blockers(...) == []` or exit 0 of `at sup pack`.
   2. sup_workers.py:492 "tip may not move backwards" and :461 "no recorded tip" guard: no test.
   3. sup_workers.py:67 prompt sentence "You are on task/{task} ... on purpose": no test.
I. [M] plugins/agents-tasks/skills/supervise/assets/supervisor.md:39,54: show `at sup pack <name> <TASK>... [--parallel]
   [--branch <slug>=<branch>]` and `at sup ready --pack <name>` (the guard already allows both).
J. Simplicity (behaviour-neutral):
   1. sup_workers.py `_write_map` (~794-797) rebuilds the pack worktree path; use `_pack_wt`.
   2. The repo slug pattern lives in sup_workers.py:71 `SLUG`, task_lanes.py:37 inside `ENTRY_RE`, sup_guard.py:64. Make
      `task_lanes` own `SLUG`, build `ENTRY_RE` from it, import it in sup_workers; the guard copy stays with a one-line pointer comment.
   3. sup_digest.py:196-201 `_pack_ready_lines` tests `slug in tips` three times: one `continue` at the loop top.
   4. sup_workers.py:641-642 `cmd_close_pack` calls `_clean(wt)` twice: bind once.

Report: the usual implementer report (## Test plan first, Status line, files changed, test commands and results, anything
you did not do and why).
