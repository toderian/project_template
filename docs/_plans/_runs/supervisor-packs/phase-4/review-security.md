## Status: DONE
## Verdict: PASS
## Findings: 5 (C: 0, I: 0, M: 5)
1. [M] plugins/agents-core/lib/sup.py:355,364,366,368 — a raw phase heading reaches the supervisor session and the `start-pack` refusal unsanitised (ESC, BEL, free text); older than this phase for `ready <ID>`, widened to every pack task. Fix: cut and strip control characters as `sup_state._clean` does.
2. [M] plugins/agents-core/lib/sup.py:421 (with :397) — a resource name has no length cap or shape check; `!r` escapes control characters. Fix: show only names matching `sup_state.RES`.
3. [M] plugins/agents-core/lib/task_lanes.py:36 (used at sup.py:450) — shared-file check bypassed by spelling: `src/a.py` vs `src/./a.py`. Fix: refuse `.` segments in `entry_ok`.
4. [M] plugins/agents-core/lib/sup.py:446-451 — quadratic pair check with no bound: two tasks with 3,000 entries each took 19 s.
5. [M] plugins/agents-core/lib/sup.py:461 — `ValueError` from `st.read_pack` is not caught: `at sup ready --pack ../x` prints a traceback, exit 1 (owner's shell only; the guard blocks the name).

Correctly handled (probed): traversal, absolute paths, option-like entries, control characters in `Files:`; no entry is
used as a filesystem path or pathspec; `Repos` and `Blocked by` cells; the guard rule (36 hostile strings);
prepare-pack skill text (no push, commit after the owner's yes).
