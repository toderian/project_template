---
name: migration-safety
description: Generate safe, reversible database schema migrations and review proposed ones for production hazards (table-rewrite locks, NOT-NULL-without-backfill, missing CONCURRENTLY, irreversible DROPs). Default focus PostgreSQL with Liquibase or Flyway; safety rules generalize to MySQL and SQLite. Use when the user mentions migration, schema change, alter table, add/drop column, add index, backfill, Liquibase, Flyway, or zero-downtime DDL.
---

Read and follow:

- `playbooks/skills/engineering/migration-safety.md`

This Antigravity wrapper is generated from `.claude-plugin/plugin.json`.
Keep Antigravity support experimental and isolated; update the shared playbook first.
