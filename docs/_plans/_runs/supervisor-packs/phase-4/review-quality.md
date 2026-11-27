Stage: quality, phase 4 (code lane).

## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 8 (C:1 I:4 M:3)
1. [C] plugins/agents-core/lib/sup.py:452,461 — `pack_problems` raises: a non-UTF-8 `.local/repos.map` or registry gives a traceback (`UnicodeDecodeError`, a `ValueError`); `at sup ready --pack Bad_Name` gives a traceback from `st.read_pack`.
2. [I] sup.py:437 — a `Repos` slug is checked only when the map has a line for it; the registry is discarded. A registry slug with no map line passes although it is a sibling repo.
3. [I] sup.py:334 — `_slugs` is a second parser of the `Repos` cell and disagrees with `sw._task_repos`: `Repos: \`sib\`; x` makes the shared-file rule treat two tasks as serialised while phase 1 does not serialise them; prose in the cell flags false slugs.
4. [I] scripts/tests/test_sup_workers.py:86 — no test covers `start-pack` running the pack check (a mutant back to `_edges` passes everything); the setUp patch switches off all task rules in that file.
5. [I] sup.py net 107 against 80 with no reason. Mergeable: `_slugs` with `sw._task_repos`; `_brief` with the import code in `sw._task_meta`; three parses per task (`task_lines`, `readiness`, `_edges`); profile.json read copied from sup_tick.py:449; `e.partition(":")` three times while `ENTRY_RE` has a slug group; `Resources:` split twice.
6. [M] sup.py:426 — when `_edges` refuses, the shared-file rule runs without edges and prints a false "can run together" line.
7. [M] sup.py:417 — a corrupt profile.json is reported as "not a resource of the profile"; name the file.
8. [M] sup.py:390 — a pack task archived by hand (file in the archive, no `landed` event) makes `start-pack` on a paused pack refuse with `no task file`; `_blockers` counts the same file as done.
