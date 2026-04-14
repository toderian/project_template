# Todo Convention

## Purpose

Shared format for todo files used across all skills. Any skill that produces actionable output can create todos by following this convention.

## Directory structure

```
docs/
├── _todos/              # Active todos
└── _todos_archived/     # Completed or cancelled todos
```

If these directories don't exist, create them. Each directory should contain a `.gitkeep` file so empty directories are tracked.

## File naming

```
<ISO-datetime>_<short-description>.md
```

The datetime uses filesystem-safe format (dashes instead of colons):

```
2026-04-14T10-30-00_refactor-auth-middleware.md
```

Use the current time when creating the file. The short description should be lowercase, hyphenated, and under 50 characters.

## File format

Every todo starts with a metadata table, then phases, acceptance criteria, related tests, an execution log, and (when done) a completion summary.

````markdown
| Field         | Value                              |
|---------------|------------------------------------|
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

1. Reference this convention: `playbooks/skills/todo-convention.md`
2. Create one file per actionable item in `docs/_todos/`
3. Set `Source` to the skill name
4. Set `Source ref` to the origin (issue number, PRD title, etc.)
5. Set `Priority` based on urgency and importance
6. Set `Blocked by` if this todo depends on another
7. Split the work into phases with clear commit points
8. Define acceptance criteria and list any known related tests

Keep todos atomic — one clear deliverable per file. If a PRD produces 5 vertical slices, create 5 todo files.

## Updating todos during execution

When starting work on a todo:

1. Set `Owner` to who is working on it
2. Change Status to `in_progress`
3. Update `Last executed` and `Updated` to now

After completing each phase:

1. Check off the phase's checklist items
2. Run related tests and record results
3. Append an execution log entry with what was done, test results, and outcome
4. Commit the code changes AND the updated todo file together
5. Update `Last executed` and `Updated`

When all phases are done:

1. Verify all acceptance criteria pass — check them off
2. Append a final execution log entry
3. Write the completion summary
4. Change Status to `done`
5. Move file to `docs/_todos_archived/`

## Listing todos

To get a quick overview, scan `docs/_todos/` and report:

- Total count by status
- Breakdown by priority
- Oldest open todos (by Created date)
- Recently executed (by Last executed date)
- Phase progress (e.g. "Phase 2/4 in progress")
- Blocked todos and what they're waiting on
