# Todo Convention

## Purpose

Shared format for committed task files used across all skills. Raw thoughts still start in the inbox;
tasks are the point where work becomes planned, typed, sequenced, and ready for agents to execute.

A task file is the smallest document that lets an agent do the work and a reader see it was done: a
short metadata table, a brief, one or more phases, and acceptance criteria. Everything else is
optional and added when it is first needed.

## Where this fits

Lifecycle:

```text
Inbox idea (I-NNN) -> triage or direct creation -> Task (<PREFIX>-NNN, typed) -> done/cancelled -> archive
```

Use `agents-tasks:capture-idea` for vague ideas and follow-ups. Use `agents-tasks:add-task`, `agents-tasks:triage-inbox`, `agents-tasks:prd-to-todos`, or
another task-producing skill when the work is clear enough to become a full task immediately.

## Directory structure

```text
docs/
├── _plans/                 # Durable implementation plans that outlive a session
├── tasks_manager/
│   ├── _areas.md            # Area registry: Area | Prefix | Description | Page
│   ├── _roadmap.md          # Global Urgent / Now / Next / Later / Someday execution plan
│   ├── _active.md           # Generated ledger of open + in_progress tasks
│   ├── _done.md             # Generated ledger of completed/cancelled tasks
│   ├── _inbox/              # Raw ideas (see inbox-convention.md)
│   ├── _inbox_archived/     # Promoted or dropped ideas
│   ├── _todos/              # Active task files
│   ├── _todos_archived/     # Completed or cancelled task files
│   ├── _logs/               # Rotated execution logs (`at ledger rotate-log`)
│   └── _runs/<TASK-ID>/     # execute-plan run state: state.md + phase-N/ artifacts; removed at completion
├── areas/
│   ├── _overview.md         # Generated area/task overview
│   └── <slug>.md            # Generated area task-status page plus context pointer
├── resources/               # Durable reference material, glossary, runbooks, attachments, component docs
│   ├── CONTEXT.md           # Primary domain glossary
│   ├── _inbox/              # Raw knowledge files waiting for agents-tasks:distill-knowledge
│   ├── _digests/            # Curated Markdown summaries of raw sources
│   ├── _reports/            # Timestamped rerunnable reports and audits
│   └── <area>/
│       ├── summary.md       # Durable area architecture summary
│       ├── sources.md       # Area source history and provenance ledger
│       ├── dependency-graph.md
│       ├── attachments/     # Durable source documents and binaries with Markdown metadata
│       ├── contracts/<feature-slug>.md
│       ├── runbooks/<scenario-slug>.md
│       └── components/<component-slug>/CONTEXT.md
└── archive/                 # Frozen docs/resources that are no longer current

workbooks/
└── <workbook-slug>/          # Reusable workbook bundle with README and local support files
```

The task manager remains the source of truth for work. `docs/resources/` replaces the older
reference folder. `docs/resources/CONTEXT.md` is the primary domain glossary; root
`CONTEXT.md` is only a pointer or legacy fallback. Do not add repo slugs to task IDs, filenames,
prefixes, or areas; use the optional `Repos` metadata row for repo scope.

If these directories do not exist, run `at init --with-tasks` to seed them.

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
at reserve task <PREFIX> <TYPE> <short-description>
```

The helper atomically creates the empty placeholder file and prints its path, so parallel agents cannot
claim the same ID. Fill the placeholder immediately with the task template. If an agent is
interrupted after reservation, `at ledger check` catches the malformed placeholder.

Under the hood, the helper scans both active and archived task directories so archived tasks still
reserve their numbers. Inbox IDs use the separate `I-NNN` counter from
[inbox-convention.md](inbox-convention.md); promoting `I-007` assigns a fresh task ID and records
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
- `Page` points at `docs/areas/<slug>.md`; durable architecture notes for the area live in
  `docs/resources/<slug>/summary.md`, and repeatable operational procedures live in
  `docs/resources/<slug>/runbooks/`.
- Areas are defined with the user when possible. If no existing area fits a clear task, propose a slug,
  prefix, description, and page, then add it after confirmation.

`at ledger sync` uses this registry to create missing area pages, regenerate
`docs/areas/_overview.md`, and refresh generated Urgent / Now / Next / Later / Someday blocks in each area page. Do not
add durable architecture notes to area pages; write them under `docs/resources/<area>/`.

## Repo registry and autonomy

Multi-repo projects declare their repos in `.config/repos.project.md` and map them to local checkouts
in `.local/repos.map`; tasks then carry an optional `Repos` row, and an optional `Autonomy` row may
lower the permission ceiling. Shapes, allowed values, work modes and `at repos-check` are in
[repos-and-autonomy.md](repos-and-autonomy.md). Single-repo projects skip all of it.

## Spec lifecycle

Durable specs under `docs/resources/` carry a status (`draft`, `accepted`, `partially-implemented`,
`implemented`, `superseded`); task-local `### Specification` / `### Design` sections are planned
intent until closeout reconciles them. The status table and the resolution order agents follow before
implementation are in [spec-lifecycle.md](spec-lifecycle.md).

## File format

The **core** shape every task has. Nothing below it is a placeholder: sections appear when they carry
content.

````markdown
| Field    | Value               |
|----------|---------------------|
| Task ID  | AUTH-001            |
| Type     | F                   |
| Area     | auth                |
| Created  | 2026-04-14T10:30:00 |
| Updated  | 2026-04-14T10:30:00 |
| Status   | open                |
| Priority | high                |
| Source   | add-task            |

## Login session hardening

### Brief

Harden session handling so users stay signed in reliably without weakening token storage. The current
checks are scattered across middleware and token helpers; this task consolidates them behind one
testable boundary while preserving public behavior.

### Phases

#### Phase 1: Validation boundary

- [ ] Add `SessionValidator` and route the existing middleware checks through it
- [ ] Cover valid, expired, and malformed sessions in `tests/auth/test_sessions.py`

### Acceptance criteria

- [ ] Existing valid sessions continue to work
- [ ] Expired sessions are rejected consistently
- [ ] Related tests cover valid, expired, and malformed sessions
````

One phase is the normal case. Split into more only when each phase is separately committable and
reviewable; a phase that only reads code ("current-state review") is not a phase, it is the
pre-implementation note below.

A phase may carry one optional `Shape:` line directly under its heading, before the checklist —
`Shape: ExposedPortRow.tsx net shrinks; ≤ ~150 new code lines.` It states the size the phase is
expected to have; `at task size` prints it above the phase's size table and the spec reviewer checks
it like a checklist item.

### Optional metadata rows

Add a row when it carries a real value; omit it otherwise (never fill `N/A` to satisfy a template).

| Row | When | Value |
|-----|------|-------|
| `Last executed` | after the first execution | ISO 8601 datetime |
| `Owner` | someone specific owns it | agent or user |
| `Blocked by` | a dependency exists | task ID or filename |
| `Source ref` | the task came from somewhere | `I-007`, issue number, PRD path |
| `Spec refs` | task-local spec/design sections exist (`self`) or the task depends on durable specs | comma-separated references |
| `Repos` | `.config/repos.project.md` exists and scope is inferable | repo slugs |
| `Autonomy` | the task must be stricter than the repo default | `L0`–`L3`, never above the repo max |
| `Target date` / `Deadline` | the user gave explicit scheduling intent | `YYYY-MM-DD` |
| `Execution` | the task must run through the full orchestrated pipeline regardless of size | `orchestrated` |

`Status` is `open`, `in_progress`, `done`, or `cancelled`. `Priority` is `high`, `medium`, or `low`;
roadmap order decides the execution sequence. `Source` names the skill or process that created the
task (`add-task`, `inbox`, `prd-to-todos`, `manual`).

### Optional sections

In this order when present, between the core sections and the execution log:

- `### Specification` (after Brief) — planned behavior, non-goals, constraints, open questions. Add
  it when acceptance criteria alone would lose intent.
- `### Design` (after Specification) — approach, touched components, interface/data changes, test
  strategy, rollout. Add it when the approach needs agreement before code edits.
- `### Related tests` (after Acceptance criteria) — known tests, or `N/A - <reason>` when tests do
  not apply. Add it once tests are known.
- `### Repo scope` — cross-repo tasks when the `Repos` row alone does not explain the split; use
  `<repo-slug>:<repo-relative-path>` references.
- `### Follow-ups` — `I-NNN` captures for work deliberately left out. Add it when the first one exists.
- `## Tickets` — decision tickets, only in `agents-tasks:wayfinder` maps (its `references/map-template.md`
  has the two validator constraints: ticket tables start with a `Ticket` column, ticket bodies use
  `###` headings without checkboxes).

### Execution log

Appended by the first execution, append-only after that, under `## Execution log` after a `---` rule:

```markdown
---

## Execution log

### 2026-04-15T14:30:00 - Phase 1: Validation boundary

- Implemented SessionValidator; routed middleware validation through it.
- Kept token parsing in the existing helper to avoid a wider refactor.
- tests/auth/test_sessions.py: 8 passed. Committed as a1b2c3d.
```

Each entry records actions, decisions, test results with real output, commit SHAs when work is
committed, and outcome. Keep entries short; `at ledger check` warns past 200 lines and
`at ledger rotate-log` moves old entries to `_logs/`.

### Completion harvest and summary

Written by `agents-tasks:complete-task` when the task closes, never at creation:

```markdown
## Completion harvest

| Item | Result |
|------|--------|
| Resource updates | docs/resources/auth/session-validation.md |
| Area updates | None |
| Follow-ups | I-012 |
| Notable decisions/deviations | Kept token parsing in the existing helper. |

## Completion summary

Completed session validation hardening in 1 phase. Final validation: 8 tests passed. One follow-up
captured for session expiry telemetry.
```

Each harvest row names updates or says `None`. The summary states the outcome and final validation
state, and carries any `Ruling:` lines from the task's `_runs/` state.

## Before implementing an existing task

Read the task, then write a ≤ 3-line current-state note as the first execution-log entry: what already
exists in code, docs and tests; whether the task is still valid, correctly sequenced and not
duplicated; which spec sources apply and whether they are planned intent or evidence
([spec-lifecycle.md](spec-lifecycle.md)). That note is the whole gate for a trivial task (≤ 2 phases,
one concern, no dependence on external facts).

For a larger, stale, high-risk task, or one that depends on current third-party facts, replace the
note with two bounded reviews recorded as concise bullets: a **current-state review** (`researcher`
subagent or the researcher personality) and a **plan freshness review** (`plan-critic` subagent, or
the relevant axes of the `agents-core:planning-workflow` critique rubric on the main thread).

If either finds stale assumptions, duplicate work, ordering issues, or overlap with later tasks,
reconcile before implementation: agents may update roadmap ordering, task notes, area status and
cross-links, and must ask before merging, cancelling, or materially rescoping tasks. This gate applies
to starting existing tasks, not to inbox capture.

## Creating tasks

Any skill that produces actionable work can create tasks. Prefer `agents-tasks:add-task` for direct creation from a
clear user request, and `agents-tasks:capture-idea` for vague ideas.

1. Pick or confirm an area from `docs/tasks_manager/_areas.md`.
2. Reserve the filename with `at reserve task <PREFIX> <TYPE> <desc>` (`T` only for global or
   cross-area work).
3. Fill the core shape: metadata, title, brief, phases, acceptance criteria. Add optional rows and
   sections only when they carry a value now.
4. Run `at ledger sync`, then `at repos-check` when the task carries `Repos` or `Autonomy`.
5. Place the task on `docs/tasks_manager/_roadmap.md` only if the user wants it scheduled.

Keep tasks atomic: one clear deliverable per file.

## Roadmap

`docs/tasks_manager/_roadmap.md` is the global execution plan: Urgent, Now, Next, Later, and Someday.
Placement and order are deliberate human decisions, not derived from status or priority. Optional
milestone headings inside those horizons carry goal-level dates. Priority stays `high`, `medium`, or
`low`; roadmap order decides the actual execution sequence.

This is the canonical definition of the horizons and their soft item thresholds. Thresholds are review
pressure only, not validation failures:

- **Urgent** — interrupting work that displaces the current plan; soft threshold 0-2 items.
- **Now** — active or immediate-pickup work; soft threshold 1-3 items.
- **Next** — the committed near-term queue; soft threshold 5-10 items.
- **Later** — valid committed tasks that are intentionally unscheduled; no threshold.
- **Someday** — weak-commitment parking lot; no threshold.

The roadmap is placement-only. It stores task IDs like `AUTH-001` in the intended horizon and order;
task IDs may appear in any horizon. Raw inbox ideas like `I-007` may appear only in `Someday` as
parking-lot signals, and must be promoted through `agents-tasks:triage-inbox` before moving into `Urgent`, `Now`,
`Next`, or `Later`. It may group work with
`### Milestone: <name> (target: YYYY-MM-DD)` or
`### Milestone: <name> (deadline: YYYY-MM-DD)` headings inside an existing horizon, but it must not add
a separate top-level `## Milestones` section. Task files remain authoritative for status, phases,
priority, optional task-specific dates, and other detail.
Ambiguous or missing references reported by
`at ledger check` must be fixed by a human or agent; do not guess which task was
meant.

## Ledgers and area sync

Task files remain the source of truth. `at ledger sync` derives:

- `docs/tasks_manager/_active.md` - every `open` and `in_progress` task.
- `docs/tasks_manager/_done.md` - every `done` and `cancelled` archived task.
- `docs/areas/_overview.md` - generated overview from `_areas.md`, task metadata, and recognizable
  roadmap IDs.
- Generated Urgent / Now / Next / Later / Someday status blocks in each `docs/areas/<slug>.md`.

The sync tooling edits only generated marker blocks inside area pages and creates missing area pages
from the standard template. Existing content outside those markers is preserved for compatibility, but
new durable context belongs under `docs/resources/<area>/`.

Use `at ledger sync` to regenerate. Use `at ledger check` in CI or
agent handoff validation; it is read-only and fails on duplicate IDs, malformed metadata,
status-directory mismatch, unregistered areas/prefixes, bad roadmap references, stale generated files,
and archived tasks without an explicit completion harvest and summary.

## Active-task audits

Use `agents-tasks:audit-todos` for periodic active-task health checks. It audits files under
`docs/tasks_manager/_todos/` against current code, tests, docs, roadmap placement, generated ledgers,
area pages, archived task evidence, and `docs/resources/`.

The audit is evidence-based and report-only by default. It may recommend `keep`, `needs-update`,
`appears-done`, `cancel-or-close`, `split-follow-up`, or `needs-user-decision`, but it does not edit,
archive, capture follow-ups, or reorder roadmap entries unless the user explicitly starts a follow-up
workflow. Age alone is not enough to close or cancel work; each meaningful recommendation must cite
current repo evidence.

## Run state

`agents-core:execute-plan` keeps its per-task working state in `docs/tasks_manager/_runs/<TASK-ID>/`:
`state.md` (the resume map: one row per phase, commit SHAs, review verdicts, `Ruling:` lines) and one
`phase-N/` directory per phase (brief, implementer report, review reports). The directory is created by
`at task run-state init <TASK-ID>` and `at task brief <TASK-ID> --phase N`, committed with the phase
commits so a fresh session or machine can resume, and removed when the task is completed. Format and
resume procedure: the `agents-core:execute-plan` skill (references/run-state.md). `at ledger check`
warns when a run directory has no task or its task is already archived.

## Completion and archive

Status transitions:

```text
open -> in_progress -> done -> archive
open -> cancelled -> archive
in_progress -> cancelled -> archive
```

Prefer `agents-tasks:complete-task` for this workflow. Before changing a task to `done` or `cancelled`:

1. Verify acceptance criteria and related tests (`agents-tasks:verify-task` for anything with more
   than one phase or an execute-plan run).
2. Reconcile linked specs ([spec-lifecycle.md](spec-lifecycle.md) §"At completion").
3. Append a final execution log entry.
4. Write the completion harvest table and the completion summary (format above), copying any
   `Ruling:` lines from `docs/tasks_manager/_runs/<TASK-ID>/state.md` into the summary, then remove
   the run directory (`git rm -r docs/tasks_manager/_runs/<TASK-ID>`) when one exists.
5. Change `Status`.
6. Move the file to `docs/tasks_manager/_todos_archived/`.
7. Run `at ledger sync`, then `at ledger check`.

Plugin hooks remind when a terminal task is missing its harvest or remains in the active `_todos/`
directory. Run the same validation manually as the authoritative completion check.

## Listing tasks

For a quick overview, read `docs/tasks_manager/_roadmap.md`, `docs/tasks_manager/_active.md`,
`docs/areas/_overview.md`, and `docs/tasks_manager/_done.md`. If they look stale, rebuild with
`at ledger sync`, then report:

- Counts by status and area.
- Breakdown by priority.
- Items at the top of Urgent / Now / Next / Later / Someday.
- Oldest open tasks.
- Recently executed tasks.
- Blocked tasks and dependencies.
