---
name: migration-safety
description: Generate safe, reversible database schema migrations and review proposed ones for production hazards (table-rewrite locks, NOT-NULL-without-backfill, missing CONCURRENTLY, irreversible DROPs). Default focus PostgreSQL with Liquibase or Flyway; safety rules generalize to MySQL and SQLite. Use when the user mentions migration, schema change, alter table, add/drop column, add index, backfill, Liquibase, Flyway, or zero-downtime DDL.
disable-model-invocation: true
---

Use this skill to write and review database migrations safely.

Read and follow:

- `playbooks/skills/migration-safety.md`

Keep this skill thin. The playbook is the shared workflow and should be updated first when the process changes.
