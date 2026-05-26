# Init

## Purpose

Initialize the project's `docs/` layout: the **task manager** (`docs/tasks_manager/` - inbox capture
layer, committed tasks, areas registry, ledgers, and roadmap), **areas** (`docs/areas/` - generated
area status plus human notes), **plans** (`docs/_plans/` - durable implementation plans),
**resources** (`docs/resources/` - project documentation), and **archive** (`docs/archive/` - frozen
docs/resources). Seeded from the `_base/docs/` template.

## Process

### 1. Check existing structure

Look for the `docs/` layout below. If `docs/tasks_manager/` already exists, report what's there and
skip creating those; only fill in what's missing. Never overwrite existing ledgers, roadmap, area
pages, or the areas registry.

### 2. Seed the structure from the template

The canonical template lives in `_base/docs/`. Copy it into the working repo rather than
hand-authoring the files — this keeps every project's structure identical and lets the template evolve
upstream. Copy without clobbering anything already present:

```bash
scripts/seed-docs.sh
```

Resulting layout:

```
docs/
├── _plans/              # durable implementation plans
├── tasks_manager/        # seeded from _base/docs/tasks_manager/
│   ├── _areas.md         #   area registry: Area | Prefix | Description | Page
│   ├── _roadmap.md       #   Now/Next/Later plan of execution
│   ├── _active.md        #   open + in_progress ledger
│   ├── _done.md          #   completed/cancelled ledger
│   ├── _inbox/           #   raw captured ideas (I-NNN)
│   ├── _inbox_archived/
│   ├── _todos/           #   active tasks (<PREFIX>-NNN)
│   └── _todos_archived/
├── areas/
│   └── _overview.md      #   generated from areas + tasks + roadmap
├── resources/            # project docs (architecture, CONTEXT.md, runbooks)
└── archive/              # frozen docs/resources
```

The `.gitkeep` files come along with the copy so the empty dirs stay tracked by git. After seeding,
run `scripts/sync-todo-ledgers.sh` to confirm the ledgers are valid.

If `_base/docs/` is unavailable (e.g. a repo that vendored only part of the template), fall back to
creating the dirs with `.gitkeep` and seeding `_areas.md`/`_active.md`/`_done.md`/`_roadmap.md`,
`docs/_plans/`, and `docs/areas/_overview.md` by hand - see `playbooks/conventions/todo-convention.md` and
`playbooks/conventions/inbox-convention.md` for the exact shapes.

### 3. Confirm

Report what was created. Remind the user that:

- `/capture-idea` records an idea into `docs/tasks_manager/_inbox/` instantly (`I-NNN`)
- `/add-task` creates a full task directly when the work is already clear
- `/triage-inbox` promotes inbox ideas into typed, area-prefixed tasks
- `/roadmap` maintains `docs/tasks_manager/_roadmap.md` — the Now/Next/Later plan of execution
- Any skill can produce tasks following `playbooks/conventions/todo-convention.md` (`/write-a-prd`,
  `/prd-to-todos`, planning)
- Durable implementation plans live in `docs/_plans/`
- Tasks are typed `F`/`D`/`C`/`R` and classified by `Area` + `Prefix` (see
  `docs/tasks_manager/_areas.md`)
- Completed tasks move to `_todos_archived/` and get a row in `docs/tasks_manager/_done.md`;
  `/complete-task` performs the closeout, and `scripts/sync-todo-ledgers.sh --check` validates the result
