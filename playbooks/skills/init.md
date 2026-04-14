# Init

## Purpose

Initialize the project's todo tracking structure. Creates `docs/_todos/` and `docs/_todos_archived/` directories with the standard convention.

## Process

### 1. Check existing structure

Look for `docs/_todos/` and `docs/_todos_archived/`. If they already exist, report what's there and skip creation.

### 2. Create directories

```
docs/
├── _todos/
│   └── .gitkeep
└── _todos_archived/
    └── .gitkeep
```

Create both directories with `.gitkeep` files so they're tracked by git even when empty.

### 3. Confirm

Report what was created. Remind the user that:

- Any skill can produce todos following `playbooks/skills/todo-convention.md`
- `/write-a-prd` can generate todos at the end of the PRD workflow
- `/prd-to-todos` can extract todos from an existing PRD
- Completed todos should be moved to `_todos_archived/`
