Reviewer: agents-core:reviewer, re-review of the post-release fix wave, 2026-11-27. Findings as reported, evidence shortened.

## Status: DONE
## Verdict: PASS
## Findings: 6 (C:0 I:4 M:2)

All 11 review findings are fixed as decided; no probe lost, overwrote or committed a hub file outside `docs/`.

1. [I] `sup.py:56` via `sup_digest.py:496` — `errors="surrogateescape"`: `at sup task` on a task file with a non-UTF-8 byte ends in a `UnicodeEncodeError` traceback. Fixed: the text is escaped before it is returned.
2. [I] `sup_workers.py:693` — the accept-tip refusal named a way out that does not exist; an abandoned started task blocked accept-tip for ever. Fixed: a closed pack accepts, and the message names `close-pack`.
3. [I] `sup.py:199` — a file a writer drops under `docs/` during the ledger sync is staged, and deleted when the commit fails. Narrowed: only `docs/areas` and `docs/tasks_manager` are staged.
4. [I] `sup_workers.py:874` — `local: [".claude/settings.local.json"]` added `<hub>/.claude` as a worker directory. Fixed: nothing under `.claude/` or `.git/` is added.
5. [M] `sup.py:289` — wrong reason when `merge-tree` fails on a current git (unrelated histories). Fixed: wording.
6. [M] `sup.py:258` — the assume-unchanged check also refuses a cleanup-only rerun. Ruled: left (see state.md).

Not checked by the reviewer: a real git older than 2.38, an fsmonitor daemon, a real submodule, a real `claude --bg --add-dir` session.
