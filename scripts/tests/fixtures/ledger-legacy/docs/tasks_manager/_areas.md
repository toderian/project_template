# Areas

Registry of task areas and ID prefixes. Each task's `Area` field references an **Area** slug below, and
the matching **Prefix** determines the task ID sequence.

Rules:

- `T` is reserved for the `global` area and default/cross-area work.
- Prefixes must be unique, uppercase alphanumeric, and start with a letter.
- Pages should live under `../areas/<area>.md`; durable architecture summaries live in
  `../resources/<area>/summary.md`.

See `references/todo-convention.md` and `references/inbox-convention.md` (task-ledger skill).

| Area | Prefix | Description | Page |
|------|--------|-------------|------|
| tst | TST | Fixture area for task-ledger tests. | ../areas/tst.md |
