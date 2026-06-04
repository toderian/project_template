---
name: migration-safety
description: Safety review and generation guidance for reversible database schema migrations. Focuses on production hazards such as table-rewrite locks, unsafe NOT NULL changes, missing concurrent indexes, irreversible drops, backfills, and zero-downtime DDL across PostgreSQL, MySQL, SQLite, Liquibase, or Flyway.
disable-model-invocation: true
---

Use this skill to write and review database migrations safely.

Read and follow:

- `playbooks/skills/engineering/migration-safety.md`

Keep this skill thin. The playbook is the shared workflow and should be updated first when the process changes.
