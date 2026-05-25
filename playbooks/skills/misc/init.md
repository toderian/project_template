# Init

## Purpose

Initialize the project's idea/todo tracking structure: the inbox (capture layer), the todos (committed
work), the areas registry, and the two ledgers — all following the standard conventions.

## Process

### 1. Check existing structure

Look for the `docs/` files and directories below. If they already exist, report what's there and skip
creating those; only fill in what's missing.

### 2. Create the structure

```
docs/
├── _areas.md            # areas registry (seed with header + empty table)
├── _active.md           # open + in_progress ledger (seed with header + table header)
├── _done.md             # completed/cancelled ledger (seed with header + table header)
├── _inbox/
│   └── .gitkeep
├── _inbox_archived/
│   └── .gitkeep
├── _todos/
│   └── .gitkeep
└── _todos_archived/
    └── .gitkeep
```

Create the directories with `.gitkeep` files so they're tracked by git even when empty. Seed
`_areas.md`, `_active.md`, and `_done.md` with their headers (see
`playbooks/conventions/todo-convention.md` and `playbooks/conventions/inbox-convention.md` for the
exact shapes). After seeding, run `scripts/sync-todo-ledgers.sh` to confirm the ledgers are valid.

### 3. Confirm

Report what was created. Remind the user that:

- `/capture-idea` records an idea into `docs/_inbox/` instantly (`I-NNN`)
- `/triage-inbox` promotes inbox ideas into typed `T-NNN` todos
- Any skill can produce todos following `playbooks/conventions/todo-convention.md` (`/write-a-prd`,
  `/prd-to-todos`, planning)
- Todos are typed `F`/`D`/`C`/`R` and classified by `Area` (see `docs/_areas.md`)
- Completed todos move to `_todos_archived/` and get a row in `docs/_done.md`; `scripts/sync-todo-ledgers.sh` rebuilds both ledgers
