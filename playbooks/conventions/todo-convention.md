# Todo Convention

## Purpose

Shared format for committed task files used across all skills. Raw thoughts still start in the inbox;
tasks are the point where work becomes planned, typed, sequenced, and ready for agents to execute.

## Where this fits

Lifecycle:

```text
Inbox idea (I-NNN) -> triage or direct creation -> Task (<PREFIX>-NNN, typed) -> done/cancelled -> archive
```

Use `capture-idea` for vague ideas and follow-ups. Use `add-task`, `triage-inbox`, `prd-to-todos`, or
another task-producing skill when the work is clear enough to become a full task immediately.

## Directory structure

```text
docs/
├── _plans/                 # Durable implementation plans that outlive a session
├── tasks_manager/
│   ├── _areas.md            # Area registry: Area | Prefix | Description | Page
│   ├── _roadmap.md          # Global Now / Next / Later execution plan
│   ├── _active.md           # Generated ledger of open + in_progress tasks
│   ├── _done.md             # Generated ledger of completed/cancelled tasks
│   ├── _inbox/              # Raw ideas (see inbox-convention.md)
│   ├── _inbox_archived/     # Promoted or dropped ideas
│   ├── _todos/              # Active task files
│   └── _todos_archived/     # Completed or cancelled task files
├── areas/
│   ├── _overview.md         # Generated area/task overview
│   └── <slug>.md            # Human area notes plus generated status blocks
├── resources/               # Durable reference material, runbooks, decisions, component docs
└── archive/                 # Frozen docs/resources that are no longer current
```

The task manager remains the source of truth for work. `docs/resources/` replaces the older
`docs/reference/` folder. Do not add a Projects layer; the global roadmap and area pages are enough.

If these directories do not exist, run `/init` to seed them from `_base/docs/`.

## File naming

```text
<PREFIX>-<NNN>-<TYPE>_<short-description>.md
```

- `<PREFIX>-<NNN>` is the stable Task ID, for example `AUTH-001` or `T-042`.
- `<PREFIX>` comes from `docs/tasks_manager/_areas.md`. `T` is reserved for default, global, or
  cross-area work.
- `<NNN>` is a zero-padded, per-prefix counter. Roll naturally to 4 digits after 999.
- `<TYPE>` is one of `F` feature, `D` debug/bug, `C` chore/refactor, or `R` research/spike.
- `<short-description>` is lowercase, hyphenated, and under 50 characters.

Examples:

```text
AUTH-001-F_login-session.md
DBM-001-C_clean-migrations.md
T-001-R_evaluate-ci.md
```

The creation datetime is not in the filename; it lives in `Created`.

## ID counters

Task counters are monotonic per prefix and never reused. To assign the next ID:

```bash
scripts/reserve-work-item.sh task <PREFIX> <TYPE> <short-description>
```

The helper atomically creates the empty placeholder file and prints its path, so parallel agents cannot
claim the same ID. Fill the placeholder immediately with the full task template. If an agent is
interrupted after reservation, `scripts/sync-todo-ledgers.sh --check` catches the malformed placeholder.

Under the hood, the helper scans both active and archived task directories so archived tasks still
reserve their numbers. Inbox IDs use the separate `I-NNN` counter from
`playbooks/conventions/inbox-convention.md`; promoting `I-007` assigns a fresh task ID and records
`Source ref: I-007`.

## Area registry

`docs/tasks_manager/_areas.md` is the registry for task prefixes and area pages.

```markdown
| Area | Prefix | Description | Page |
|------|--------|-------------|------|
| global | T | Default, cross-area, and uncategorized work. | ../areas/global.md |
| auth | AUTH | Authentication and session management. | ../areas/auth.md |
```

Rules:

- `Area` is a short lowercase slug.
- `Prefix` is uppercase alphanumeric, starts with a letter, and is unique.
- `T` is reserved for the `global` area and for work that genuinely crosses areas.
- `Page` points at `docs/areas/<slug>.md`.
- Areas are defined with the user when possible. If no existing area fits a clear task, propose a slug,
  prefix, description, and page, then add it after confirmation.

`scripts/sync-todo-ledgers.sh` uses this registry to create missing area pages, regenerate
`docs/areas/_overview.md`, and refresh generated Now / Next / Later blocks in each area page. Human
area notes outside generated markers are preserved.

## File format

Every task starts with a metadata table, then a short title, a brief, phases, acceptance criteria,
related tests, follow-ups, execution log, completion harvest, and completion summary.

````markdown
| Field         | Value                              |
|---------------|------------------------------------|
| Task ID       | AUTH-001                           |
| Type          | F                                  |
| Area          | auth                               |
| Created       | 2026-04-14T10:30:00                |
| Updated       | 2026-04-14T10:30:00                |
| Last executed | N/A                                |
| Status        | open                               |
| Priority      | high                               |
| Owner         | N/A                                |
| Blocked by    | N/A                                |
| Source        | add-task                           |
| Source ref    | N/A                                |

## Login session hardening

### Brief

Harden session handling so users stay signed in reliably without weakening token storage. The current
implementation has several scattered checks, so this task consolidates the behavior behind one
testable boundary. The first pass should preserve public behavior, then add the stricter validation.

### Phases

#### Phase 1: Current-state review

- [ ] Map current session creation and validation paths
- [ ] Identify existing tests and missing coverage

#### Phase 2: Implementation

- [ ] Add the validation boundary
- [ ] Route existing session checks through it

### Acceptance criteria

- [ ] Existing valid sessions continue to work
- [ ] Expired sessions are rejected consistently
- [ ] Related tests cover valid, expired, and malformed sessions

### Related tests

- `tests/auth/test_sessions.py` - session validation behavior

### Follow-ups

- None

---

## Execution log

Append-only record of actions taken, decisions made, test results, and outcome.

### 2026-04-15T09:00:00 - Pre-implementation review gate

**Researcher current-state review:**
- Current session validation is split across middleware and token helpers.
- Existing coverage is limited to happy-path login.

**Plan-critic freshness/applicability review:**
- Verdict: PROCEED.
- Risk accepted: malformed-token coverage needs to be added before implementation is marked done.

**Outcome:** Gate passed. Scope unchanged.

### 2026-04-15T14:30:00 - Phase 2: Implementation

**Actions taken:**
- Implemented SessionValidator.
- Routed middleware validation through the new boundary.

**Decisions made:**
- Kept token parsing in the existing helper to avoid a wider refactor.

**Test results:**
```text
tests/auth/test_sessions.py - 8 passed, 0 failed
```

**Outcome:** Phase 2 complete. Committed as `feat: harden session validation` (a1b2c3d).

---

## Completion harvest

| Item | Result |
|------|--------|
| Resource updates | docs/resources/auth/session-validation.md |
| Area updates | docs/areas/auth.md |
| Follow-ups | I-012 |
| Notable decisions/deviations | Kept token parsing in the existing helper. |

## Completion summary

Completed session validation hardening over 2 phases. Final validation: 8 tests passed. One follow-up
was captured for session expiry telemetry.
````

### Field definitions

| Field | Description |
|-------|-------------|
| Task ID | Stable `<PREFIX>-NNN` handle, assigned at creation, never changed or reused |
| Type | `F` feature, `D` debug/bug, `C` chore/refactor, `R` research/spike |
| Area | Area slug from `docs/tasks_manager/_areas.md` |
| Created | ISO 8601 datetime when the file was created |
| Updated | ISO 8601 datetime of the last metadata or content update |
| Last executed | ISO 8601 datetime when implementation/research last happened, or `N/A` |
| Status | `open`, `in_progress`, `done`, or `cancelled` |
| Priority | `high`, `medium`, or `low`; roadmap order decides execution sequence |
| Owner | Agent/user working the task, or `N/A` |
| Blocked by | Task ID or filename this depends on, or `N/A` |
| Source | Skill or process that created the task, for example `add-task`, `inbox`, `prd-to-todos`, `manual` |
| Source ref | Origin reference, for example `I-007`, issue number, file path, or `N/A` |

## Task body requirements

- **Title:** the first `##` after metadata is the short human-readable title.
- **Brief:** 2-4 sentences explaining the user outcome and relevant constraints.
- **Phases:** one or more logical, committable phases with checklists.
- **Acceptance criteria:** verifiable criteria for marking the whole task done.
- **Related tests:** list known tests, or write `N/A - <reason>` when tests do not apply.
- **Follow-ups:** use `None` if no follow-ups exist. Prefer `I-NNN` inbox captures for new ideas.
- **Execution log:** append-only. Each entry records actions taken, decisions made, test results, and outcome.
- **Completion harvest:** required before archiving; each row must name updates or explicitly say `None`.
- **Completion summary:** required when archived, with the outcome and final validation state.

## Pre-implementation review gate

Before starting implementation of any existing task, run two reviews and record both in the execution
log before code edits:

1. **Researcher current-state review** - inspect relevant code, docs, tests, ledgers, and area pages.
   Record what already exists, likely conflicts, and current test coverage.
2. **Plan-critic freshness/applicability review** - challenge whether the task is still valid, sequenced
   correctly, duplicated, stale, or overlapping later work. Use `playbooks/conventions/plan-critique.md`.

Claude Code may dispatch `researcher` and `plan-critic` subagents. Codex must run equivalent
main-thread passes using `playbooks/personalities/researcher.md` and the plan critique convention.

If the reviews find stale assumptions, duplicate work, ordering issues, or overlapping later tasks,
reconcile before implementation. Agents may update roadmap ordering, task notes, area status, and
cross-links. Agents must ask before merging tasks, cancelling tasks, or materially changing scope.

This gate applies to starting existing tasks. It does not apply to quick inbox capture.

## Creating tasks

Any skill that produces actionable work can create tasks. Prefer `/add-task` for direct creation from a
clear user request, and `/capture-idea` for vague ideas.

Creation steps:

1. Read this convention.
2. Pick or confirm an area from `docs/tasks_manager/_areas.md`.
3. Reserve the task filename with `scripts/reserve-work-item.sh task <PREFIX> <TYPE> <desc>`. Use `T`
   only for global/cross-area/default work.
4. Pick a type (`F`, `D`, `C`, or `R`) and priority (`high`, `medium`, or `low`).
5. Fill the reserved file in `docs/tasks_manager/_todos/` named `<PREFIX>-NNN-<TYPE>_<desc>.md`.
6. Fill the full template: brief, phases, acceptance criteria, related tests, follow-ups, execution log,
   completion harvest, and completion summary placeholders.
7. Set `Source` and `Source ref`.
8. Run `scripts/sync-todo-ledgers.sh`.
9. Optionally place the task on `docs/tasks_manager/_roadmap.md` if the user wants it scheduled.

Keep tasks atomic: one clear deliverable per file.

## Roadmap

`docs/tasks_manager/_roadmap.md` is the global execution plan: Now, Next, and Later. Placement and order
are deliberate human decisions, not derived from status or priority. Priority stays `high`, `medium`, or
`low`; roadmap order decides the actual execution sequence.

The roadmap is placement-only. It stores task IDs like `AUTH-001` and raw inbox ideas like `I-007` in
the intended horizon and order; task files remain authoritative for status, phases, priority, and other
detail. Ambiguous or missing references reported by `scripts/sync-todo-ledgers.sh --check` must be
fixed by a human or agent; do not guess which task was meant.

## Ledgers and area sync

Task files remain the source of truth. `scripts/sync-todo-ledgers.sh` derives:

- `docs/tasks_manager/_active.md` - every `open` and `in_progress` task.
- `docs/tasks_manager/_done.md` - every `done` and `cancelled` archived task.
- `docs/areas/_overview.md` - generated overview from `_areas.md`, task metadata, and recognizable
  roadmap IDs.
- Generated Now / Next / Later status blocks in each `docs/areas/<slug>.md`.

The sync tooling edits only generated marker blocks inside area pages. Human-authored context outside
those markers is preserved. Missing area pages are created from the standard template.

Use `scripts/sync-todo-ledgers.sh` to regenerate. Use `scripts/sync-todo-ledgers.sh --check` in CI or
agent handoff validation; it is read-only and fails on duplicate IDs, malformed metadata,
status-directory mismatch, unregistered areas/prefixes, bad roadmap references, stale generated files,
and archived tasks without an explicit completion harvest and summary.

## Completion and archive

Status transitions:

```text
open -> in_progress -> done -> archive
open -> cancelled -> archive
in_progress -> cancelled -> archive
```

Prefer `/complete-task` for this workflow. Before changing a task to `done` or `cancelled`:

1. Verify acceptance criteria and related tests.
2. Append a final execution log entry.
3. Complete the harvest table:
   - Resource updates in `docs/resources/`, or `None`
   - Area updates in `docs/areas/`, or `None`
   - Follow-ups, usually `I-NNN` inbox items, or `None`
   - Notable decisions/deviations, or `None`
4. Write the completion summary.
5. Change `Status`.
6. Move the file to `docs/tasks_manager/_todos_archived/`.
7. Run `scripts/sync-todo-ledgers.sh`.
8. Run `scripts/sync-todo-ledgers.sh --check`.

Claude hooks may block or remind when a terminal task is missing a completion harvest or remains in the
active `_todos/` directory. Codex has no hooks, so Codex agents must run the same validation manually.

## Listing tasks

For a quick overview, read `docs/tasks_manager/_roadmap.md`, `docs/tasks_manager/_active.md`,
`docs/areas/_overview.md`, and `docs/tasks_manager/_done.md`. If they look stale, rebuild with
`scripts/sync-todo-ledgers.sh`, then report:

- Counts by status and area.
- Breakdown by priority.
- Items at the top of Now / Next / Later.
- Oldest open tasks.
- Recently executed tasks.
- Blocked tasks and dependencies.
