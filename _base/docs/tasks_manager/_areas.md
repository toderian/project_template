# Areas

Registry of task areas and ID prefixes. Each task's `Area` field references an **Area** slug below, and
the matching **Prefix** determines the task ID sequence.

Areas are defined with the user, not from a fixed list. When an idea or task fits no existing area,
propose an area slug, uppercase prefix, one-line description, and page path; confirm with the user; add
a row here; then use it.

Rules:

- `T` is reserved for the `global` area and default/cross-area work.
- Prefixes must be unique, uppercase alphanumeric, and start with a letter.
- Pages should live under `../areas/<area>.md`.

See `playbooks/conventions/todo-convention.md` and `playbooks/conventions/inbox-convention.md`.

| Area | Prefix | Description | Page |
|------|--------|-------------|------|
| global | T | Default, cross-area, and uncategorized work. | ../areas/global.md |
