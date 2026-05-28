# Init

## Purpose

Initialize the project's `docs/` layout: the **task manager** (`docs/tasks_manager/` - inbox capture
layer, committed tasks, areas registry, ledgers, and roadmap), **areas** (`docs/areas/` - generated
area task-status pages), **plans** (`docs/_plans/` - durable implementation plans), **resources**
(`docs/resources/` - project documentation, the primary domain glossary, durable area contexts,
feature contracts, component contexts, sanitized operational runbooks, and timestamped reports), and
**archive** (`docs/archive/` - frozen docs/resources). Seeded from the `_base/docs/` template.

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
_base/scripts/seed-docs.sh
```

Resulting layout:

```
docs/
├── _plans/              # durable implementation plans
├── tasks_manager/        # seeded from _base/docs/tasks_manager/
│   ├── _areas.md         #   area registry: Area | Prefix | Description | Page
│   ├── _roadmap.md       #   Urgent/Now/Next/Later/Someday plan of execution
│   ├── _active.md        #   open + in_progress ledger
│   ├── _done.md          #   completed/cancelled ledger
│   ├── _inbox/           #   raw captured ideas (I-NNN)
│   ├── _inbox_archived/
│   ├── _todos/           #   active tasks (<PREFIX>-NNN)
│   └── _todos_archived/
├── areas/
│   ├── _overview.md      #   generated from areas + tasks + roadmap
│   └── global.md         #   generated global-area task status
├── resources/            # project docs (architecture, glossary, component contexts, runbooks)
│   ├── _inbox/           #   raw knowledge drops waiting for /distill-knowledge
│   ├── _digests/         #   curated Markdown summaries of raw sources, segregated by area
│   ├── _reports/         #   timestamped reports, audits, inventories, and migration proposals
│   ├── CONTEXT.md        #   primary domain glossary
│   └── global/
│       ├── summary.md    #   durable global-area architecture notes
│       └── runbooks/     #   sanitized cross-cutting operational procedures
└── archive/              # frozen docs/resources
```

The root `CONTEXT.md`, if missing, is created as a pointer to `docs/resources/CONTEXT.md`. The
`.gitkeep` files come along with the copy so the empty dirs stay tracked by git. After seeding, run
`_base/scripts/sync-todo-ledgers.sh` to confirm the ledgers are valid.

Stable repo slugs are normally set up earlier in `_base/SETUP_INSTRUCTIONS.md` Phase 2c, before docs
and tasks are created. If `/init` is the first moment a multi-repo need is discovered, create
`.config/`, copy `_base/repos.project.example.md` to `.config/repos.project.md`, edit it for the
downstream project, and commit it.
For local checkout paths, copy `_base/repos.map.example` to `.local/repos.map` and edit it locally;
`.local/` is gitignored and should not be committed.

If `_base/docs/` is unavailable (e.g. a repo that vendored only part of the template), fall back to
creating the dirs with `.gitkeep` and seeding `_areas.md`/`_active.md`/`_done.md`/`_roadmap.md`,
`docs/_plans/`, `docs/areas/_overview.md`, `docs/resources/CONTEXT.md`,
`docs/resources/_inbox/`, `docs/resources/_digests/`, `docs/resources/_reports/`,
`docs/resources/global/summary.md`, `docs/resources/global/runbooks/`, and a root pointer by hand -
see `playbooks/conventions/todo-convention.md`,
`playbooks/conventions/inbox-convention.md`, and
`playbooks/conventions/knowledge-base-quickstart.md` for the exact shapes.

### 3. Confirm

Report what was created. Remind the user that:

- `/capture-idea` records an idea into `docs/tasks_manager/_inbox/` instantly (`I-NNN`)
- `/add-task` creates a full task directly when the work is already clear
- `/triage-inbox` promotes inbox ideas into typed, area-prefixed tasks
- `/roadmap` maintains `docs/tasks_manager/_roadmap.md` — the Urgent/Now/Next/Later/Someday plan of execution
- Any skill can produce tasks following `playbooks/conventions/todo-convention.md` (`/write-a-prd`,
  `/prd-to-todos`, planning)
- Durable implementation plans live in `docs/_plans/`
- The primary domain glossary lives in `docs/resources/CONTEXT.md`; root `CONTEXT.md` is only a pointer
- Raw docs, notes, and exports can be dropped into `docs/resources/_inbox/`; `/distill-knowledge`
  writes curated Markdown digests under `docs/resources/_digests/` and promotes stable facts into the
  knowledge base
- Rerunnable reports and audits go under `docs/resources/_reports/<workflow>/` with timestamped
  filenames
- Reusable operational procedures go under `docs/resources/<area>/runbooks/` with committed
  placeholders; real values live in ignored `.local/runbooks/` binding files
- Durable area knowledge lives in `docs/resources/<area>/`; use `/define-area` to index real
  architecture before adding cross-repo feature contracts
- Cross-repo feature contracts live in `docs/resources/<area>/contracts/<feature-slug>.md`
- Optional repo scope lives in committed `.config/repos.project.md`; local checkout paths live in ignored
  `.local/repos.map`
- Tasks are typed `F`/`D`/`C`/`R` and classified by `Area` + `Prefix` (see
  `docs/tasks_manager/_areas.md`)
- Completed tasks move to `_todos_archived/` and get a row in `docs/tasks_manager/_done.md`;
  `/complete-task` performs the closeout, and `_base/scripts/sync-todo-ledgers.sh --check` validates the result
