# Todo Convention

## Purpose

Shared format for todo files used across all skills. Any skill that produces actionable output can create todos by following this convention.

## Where this fits

Todos are the *committed-work* layer. Raw ideas start one layer earlier, in the **inbox**
(`playbooks/conventions/inbox-convention.md`): an idea is captured as `I-NNN`, then **triaged** into a
todo here. Lifecycle: `Inbox idea (I-NNN) → triage → Todo (T-NNN, typed) → done (ledger + archive)`.

## Directory structure

```
docs/tasks_manager/
├── _areas.md            # Registry of feature/areas (slug + description)
├── _roadmap.md          # Plan of execution: Now / Next / Later (see /roadmap)
├── _active.md           # Ledger of open + in_progress todos (the backlog view)
├── _done.md             # Ledger of completed/cancelled todos, newest-first
├── _inbox/              # Raw ideas (see inbox-convention.md)
├── _inbox_archived/     # Promoted or dropped ideas
├── _todos/              # Active todos
└── _todos_archived/     # Completed or cancelled todos (full files)
```

The task manager lives under `docs/tasks_manager/` (project documentation lives beside it in
`docs/reference/`). If these directories don't exist, run `/init` to seed them from `_base/docs/`, or
create them by hand — each directory should contain a `.gitkeep` file so empty directories are tracked.

## File naming

```
T-<NNN>-<TYPE>_<short-description>.md
```

- `T-<NNN>` — the **Task ID**: a stable, zero-padded 3-digit handle (e.g. `T-042`). This is how the
  todo is referenced everywhere ("work on T-042"), so it never changes once assigned.
- `<TYPE>` — one of `F` (feature), `D` (debug/bug), `C` (chore/refactor), `R` (research/spike).
- `<short-description>` — lowercase, hyphenated, under 50 characters.

```
T-042-F_dark-mode-toggle.md
T-051-D_fix-slow-login.md
```

The creation datetime is **not** in the filename — it lives in the `Created` metadata field. The Task
ID is the sort key and the stable reference.

## ID counters

Task IDs are monotonic and never reused. To assign the next one:

```
next T = (highest T-NNN found across docs/tasks_manager/_todos/ AND docs/tasks_manager/_todos_archived/) + 1
```

Scan both directories so archived todos still reserve their numbers (no gaps, no collisions). Inbox
ideas use a **separate** `I-NNN` counter (see inbox-convention.md) — promoting an idea to a todo
assigns a fresh `T-NNN`; the two sequences are independent. Zero-pad to 3 digits; roll to 4 digits
naturally if you ever pass `T-999`.

## File format

Every todo starts with a metadata table, then phases, acceptance criteria, related tests, an execution log, and (when done) a completion summary.

````markdown
| Field         | Value                              |
|---------------|------------------------------------|
| Task ID       | T-042                              |
| Type          | F                                  |
| Area          | auth                               |
| Created       | 2026-04-14T10:30:00                |
| Updated       | 2026-04-14T10:30:00                |
| Last executed | —                                  |
| Status        | open                               |
| Priority      | high                               |
| Owner         | —                                  |
| Blocked by    | —                                  |
| Source        | write-a-prd                        |
| Source ref    | #42                                |

## Refactor auth middleware

Description of what needs to be done.

### Phases

Each phase is a logical, committable unit of work. Complete phases sequentially — commit after each one.

#### Phase 1: Extract session interface

- [ ] Define SessionStore interface
- [ ] Move existing implementation behind the interface

#### Phase 2: Implement new token storage

- [ ] Add encrypted token store
- [ ] Wire up to SessionStore interface

#### Phase 3: Migration and cleanup

- [ ] Add migration script for existing sessions
- [ ] Remove deprecated storage code

### Acceptance criteria

Overall criteria for the entire todo to be considered done:

- [ ] All session tokens are stored encrypted at rest
- [ ] Existing sessions migrate transparently
- [ ] No breaking changes to public API

### Related tests

Tests that verify this todo's behavior. Updated as phases are completed.

- `tests/auth/test_session_store.py` — session interface contract
- `tests/auth/test_token_encryption.py` — encryption round-trip
- (list test files/descriptions as they are created or identified)

---

## Execution log

Append-only record of work performed. Each entry captures what was done, test results, and outcome. Keep entries concise — link to the commit for full details.

### 2026-04-15T09:00:00 — Phase 1: Extract session interface

**What was done:**
- Extracted SessionStore interface from monolithic auth module
- Moved FileSessionStore behind the new interface

**Test results:**
```
tests/auth/test_session_store.py — 4 passed, 0 failed
```

**Outcome:** Phase 1 complete. Committed as `feat: extract session store interface` (a1b2c3d).

### 2026-04-15T14:30:00 — Phase 2: Implement new token storage

**What was done:**
- Implemented EncryptedTokenStore
- Integrated with SessionStore interface

**Test results:**
```
tests/auth/test_session_store.py — 4 passed, 0 failed
tests/auth/test_token_encryption.py — 6 passed, 0 failed
```

**Outcome:** Phase 2 complete. Committed as `feat: add encrypted token storage` (d4e5f6a).

---

## Completion summary

Refactored auth middleware to use encrypted token storage behind a clean SessionStore interface. All 3 phases completed over 2 sessions. Final test state: 10 passed, 0 failed across 2 test files. No breaking changes to public API.
````

### Field definitions

| Field | Description |
|-------|-------------|
| Task ID | Stable `T-NNN` handle, assigned at creation, never changed or reused (see ID counters) |
| Type | `F` feature, `D` debug/bug, `C` chore/refactor, `R` research/spike |
| Area | Feature/area slug from `docs/tasks_manager/_areas.md`, or `—` if none yet (see areas registry) |
| Created | ISO 8601 datetime when the file was created |
| Updated | ISO 8601 datetime of the last modification |
| Last executed | ISO 8601 datetime when work last happened on this todo, or `—` if never started |
| Status | `open`, `in_progress`, `done`, `cancelled` |
| Priority | `high`, `medium`, `low` — determines work order |
| Owner | Who is working on this (agent name, user name, or `—` if unassigned) |
| Blocked by | Filename of another todo this depends on, or `—` if none |
| Source | Which skill or process created this todo (e.g. `write-a-prd`, `triage-issue`, `manual`) |
| Source ref | Optional reference to the origin (issue number, PRD link, etc.) |

## Phases

Every todo should be split into phases — logical, committable steps that build on each other.

Rules for phases:

- Each phase produces a working, committable state (no half-done code)
- Phases are sequential — complete and commit one before starting the next
- Each phase has its own checklist of concrete items
- Keep phases small enough to reason about, large enough to be meaningful
- A simple todo might have 1-2 phases; a complex one might have 5+

When creating a todo, think: "Where are the natural commit points?"

### When a phase fails

If a phase produces broken code or failing tests:

1. **Revert** to the last committed state (end of previous phase)
2. **Log the failure** in the execution log with outcome `Phase N failed. <what went wrong>. Reverted to <commit>.`
3. **Reassess** — decide whether to retry the phase with a different approach, split it into smaller phases, or escalate to the user
4. Do not proceed to the next phase with broken code

## Acceptance criteria

Overall criteria that define when the entire todo is done. These are separate from per-phase checklists — a todo is done when all phases are complete AND all acceptance criteria pass.

Write criteria that are:

- Verifiable (can be checked by running code, reading output, or inspecting state)
- Behavioral (describe what the system does, not how it's built)
- Complete (cover the full scope, not just the happy path)

## Related tests

List test files and descriptions relevant to this todo. This section evolves as work progresses:

- When creating the todo: list existing tests that might be affected
- During execution: add new tests as they are written
- When done: the final list serves as a test coverage record

Format: `path/to/test_file.py` — brief description of what it covers

## Execution log

Append-only section at the bottom of the todo. **Never edit previous entries** — only append new ones.

Each entry records:

1. **Datetime and phase** — which phase was worked on
2. **What was done** — concise summary of changes (1-3 bullet points, not a full diff)
3. **Test results** — pass/fail counts from running tests
4. **Outcome** — result and commit hash

Keep entries brief. The commit itself is the detailed record — the log is for quick scanning. Include the short commit hash so readers can `git show` for full details.

Possible outcomes:

- `Phase N complete. Committed as '<message>' (<short-hash>).`
- `Phase N partially complete. Blocked on <reason>.`
- `Phase N failed. <what went wrong>. Reverted to <commit>.`

## Completion summary

When all phases are done and the todo is moved to `_todos_archived/`, add a `## Completion summary` section after the execution log. This is a one-paragraph recap:

- What was accomplished (1-2 sentences)
- Total phases completed and time span (e.g. "3 phases over 2 sessions")
- Final test state (e.g. "12 passed, 0 failed across 3 test files")
- Any notable decisions or deviations from the original plan

This summary lets someone scanning the archive understand the outcome without reading the full execution log.

## Status transitions

```
open → in_progress → done → (archive)
open → cancelled → (archive)
in_progress → cancelled → (archive)
```

When status changes to `done` or `cancelled`, move the file from `_todos/` to `_todos_archived/`.

Always update the `Updated` field when changing any metadata.
Always update `Last executed` when actual work is performed on the todo.

## Creating todos from other skills

Any skill that produces actionable output can create todos. To integrate:

1. Reference this convention: `playbooks/conventions/todo-convention.md`
2. Assign the next `Task ID` (see ID counters) and pick a `Type` (`F`/`D`/`C`/`R`)
3. Pick an `Area` from `docs/tasks_manager/_areas.md` (define a new one with the user if none fit — see Areas)
4. Create one file per actionable item in `docs/tasks_manager/_todos/` named `T-NNN-<TYPE>_<desc>.md`
5. Set `Source` to the skill name
6. Set `Source ref` to the origin (issue number, PRD title, etc.)
7. Set `Priority` based on urgency and importance
8. Set `Blocked by` if this todo depends on another
9. Split the work into phases with clear commit points
10. Define acceptance criteria and list any known related tests
11. Add a row for the new todo to `docs/tasks_manager/_active.md` (or run `scripts/sync-todo-ledgers.sh`)

Keep todos atomic — one clear deliverable per file. If a PRD produces 5 vertical slices, create 5 todo files.

## Areas

`docs/tasks_manager/_areas.md` is the registry of feature/areas. Each todo's `Area` field references a slug from it.
Areas are **defined with the user**, not from a fixed list: when an idea or todo fits no existing area,
propose a new slug + one-line description, confirm with the user, append it to `docs/tasks_manager/_areas.md`, then
use it. Leave `Area` as `—` only when the work genuinely spans everything or is not yet classifiable.

## Ledgers

Two generated index files give an at-a-glance view; the todo files themselves remain the source of truth.

- `docs/tasks_manager/_active.md` — every `open` + `in_progress` todo (the backlog). Sorted in_progress first, then
  by priority, then Task ID. Each row links to its file under `_todos/`.
- `docs/tasks_manager/_done.md` — every completed/cancelled todo, **newest row inserted at the top** so it reads
  newest-first by completion date. Each row links to its file under `_todos_archived/`, and records the
  commit hash.

Both carry a **File** column whose cell is a relative markdown link (e.g.
`[T-042-F_dark-mode-toggle.md](_todos/T-042-F_dark-mode-toggle.md)`) so editors can Ctrl/Cmd-click to
the source. Keep them current as part of each status change (steps below). They are fully derivable
from the todo files, so `scripts/sync-todo-ledgers.sh` can rebuild them at any time — run it if you
suspect drift or after bulk edits. This works for Codex too, which has no hooks to catch mistakes.

## Roadmap

`docs/tasks_manager/_roadmap.md` is the **plan of execution**: which todos/ideas happen Now, Next, and Later, in the
order intended. Unlike the ledgers, it is *not* derived from status — the horizon placement is a
deliberate human decision and is **not** rebuilt by `scripts/sync-todo-ledgers.sh`. Maintain it with the
`/roadmap` skill, which renders each todo as a collapsible block (summary = the plan, expanded =
phases). Promote inbox ideas with `/triage-inbox` before scheduling a `T-NNN` into `Now`.

## Updating todos during execution

When starting work on a todo:

1. Set `Owner` to who is working on it
2. Change Status to `in_progress`
3. Update `Last executed` and `Updated` to now
4. Update the todo's row in `docs/tasks_manager/_active.md` (status → in_progress)

After completing each phase:

1. Check off the phase's checklist items
2. Run related tests and record results
3. Append an execution log entry with what was done, test results, and outcome
4. Commit the code changes AND the updated todo file together
5. Update `Last executed` and `Updated`
6. Update the phase progress in the todo's `docs/tasks_manager/_active.md` row

When all phases are done:

1. Verify all acceptance criteria pass — check them off
2. Append a final execution log entry
3. Write the completion summary
4. Change Status to `done`
5. Insert a row at the **top** of `docs/tasks_manager/_done.md` (Task ID, Type, Title, Area, completion datetime,
   commit hash, link to the archived file), and remove the todo's row from `docs/tasks_manager/_active.md`
6. Move file to `docs/tasks_manager/_todos_archived/`

`cancelled` todos follow the same final steps (record them in `_done.md` with a cancelled note instead
of a commit). If the ledgers ever look out of sync, run `scripts/sync-todo-ledgers.sh` to rebuild them.

## Listing todos

For a quick overview, read `docs/tasks_manager/_active.md` (open + in_progress) and `docs/tasks_manager/_done.md` (history) — they
are maintained for exactly this. If they look stale, rebuild with `scripts/sync-todo-ledgers.sh`, then
report:

- Total count by status
- Breakdown by priority
- Oldest open todos (by Created date)
- Recently executed (by Last executed date)
- Phase progress (e.g. "Phase 2/4 in progress")
- Blocked todos and what they're waiting on
