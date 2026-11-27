## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 5 (C:1 I:1 M:3)
1. [C] plugins/agents-core/lib/sup.py:237-240 — `at sup land <ID>` with no `--profile` and no `AGENTS_SUPERVISOR` skips the whole pack step: a dirty pack worktree does not refuse, the hub commit has no range, tips stay old; a rerun cannot repair it (branch gone). Reproduced.
2. [I] plugins/agents-core/lib/sup_digest.py:186-193,430 — a 1.17.0 pack with a directory-name key now prints `hub: feat/x, ? commit(s) over unknown, ready for PR`; `_pack_ready_lines` needs the "has a recorded tip" filter.
3. [M] plugins/agents-core/lib/sup_digest.py:132,173,245 — `_repos` raises `sup_workers.Refused` on a relative map path; `cmd_status`/`cmd_done` do not catch it.
4. [M] scripts/tests/test_sup_digest.py:275 — the status test asserts only the `-` placeholder for the task.
5. [M] plugins/agents-core/lib/sup.py:243 — the range line is dropped when old tip == new tip; not stated.

Evidence (short): land/done/close-pack/flow criteria met on the profile path; touched tests green (35/17/29/4);
102 non-comment code lines against 120.
