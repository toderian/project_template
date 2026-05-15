# Migration Safety

## Purpose

Generate safe, reversible database schema migrations and review proposed ones for production hazards. Default focus is PostgreSQL (Liquibase / Flyway / plain SQL); the safety rules generalize to MySQL and SQLite where noted.

Adapted from [OmexIT/claude-skills-pack `db-migration`](https://github.com/OmexIT/claude-skills-pack/blob/main/skills/db-migration/SKILL.md) (MIT). Project-specific conventions (naming, audit columns, money types) are written as **defaults** below — override them per-project in `docs/db/conventions.md` if your project has its own.

## When to use

Trigger this skill when the user mentions: "migration", "new table", "schema change", "add column", "alter table", "add index", "create index", "drop column", "rename column", "backfill", "Liquibase", "Flyway", "schema evolution", "changelog". Implicit triggers:

- User describes a new entity that needs persistence
- User adds a field to an existing entity (needs matching migration)
- User asks about zero-downtime migrations
- User mentions PostgreSQL `CONCURRENTLY` or `NOT VALID`
- User wants to add a foreign key to a populated table
- User asks to normalize or denormalize a table

## Before you start

Migrations have no classical TDD but have strict verification requirements.

1. **Brainstorm blast radius first** — recommended for destructive operations (DROP, rename, column type change). Explore: what depends on this column? What's the lock behavior under load? What's the rollback plan? Estimated downtime?
2. **Multi-phase changes get a written plan** — mandatory for: add column → backfill → switch reads → drop old. Each phase is a separate changeset.
3. **Write verification SQL first** — assertions about the expected post-migration state (rows exist, constraints applied, index present, RLS enabled). This replaces classical TDD for the SQL class.
4. **Generate the migration changeset.** Sequential execution only — migrations have strict ordering, never parallel.
5. **Verification before completion is mandatory.** Run the migration against a test database (Testcontainers or dedicated test DB). Run rollback. Re-run the migration. Show all output.
6. **Code review is mandatory for schema changes.** Reviewer focuses on: rollback safety, lock behavior, index strategy (`CONCURRENTLY` on populated tables), audit column discipline.

**Destructive-operation gate**: this skill must never generate `DROP TABLE`, `DROP COLUMN`, column renames, or type changes without explicit user confirmation. If the user tries to bypass the prompt, refuse.

## Mode detection

```bash
# Liquibase indicators
find src/main/resources/db/changelog -name "*.sql" 2>/dev/null | head -3
grep -l "liquibase formatted sql" src/main/resources/db/changelog/**/*.sql 2>/dev/null | head -3

# Flyway indicators
find src/main/resources/db/migration -name "V*__*.sql" 2>/dev/null | head -3
grep -rE "flyway-core|spring-boot-starter-flyway" build.gradle* pom.xml 2>/dev/null

# Plain SQL / Alembic / Knex / Prisma / Diesel — look at package manifests + migrations dirs
ls -d migrations alembic prisma/migrations db/migrate 2>/dev/null
```

Report the detected mode. If none detected, ask the user which migration tool they're using; default to Liquibase or plain SQL depending on stack.

## Default conventions (override per project)

These are sensible defaults. If the project has its own `docs/db/conventions.md`, follow that instead.

### Primary keys
```sql
id BIGINT PRIMARY KEY
```
Default to application-generated time-sortable IDs (TSID, ULID, Snowflake) over `SERIAL` / `IDENTITY` so IDs are stable across replicas and don't leak insertion volume. Use `UUID` if you specifically need globally unique IDs (note the index-locality cost).

### Audit columns (on every business table)
```sql
created_by        TEXT NOT NULL,
created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
last_modified_by  TEXT,
updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
```

### Money columns
```sql
amount_fiat   NUMERIC(20,2)   -- USD, EUR, etc.
amount_crypto NUMERIC(20,8)   -- BTC, ETH, USDT
```
Never `FLOAT`, `DOUBLE PRECISION`, or `REAL`. PostgreSQL's `MONEY` is also discouraged (locale-dependent).

### Timestamps
```sql
occurred_at TIMESTAMPTZ NOT NULL
```
Never `TIMESTAMP` (without time zone) for event times. `DATE` only for calendar dates, never for event times.

### Multi-tenancy (PostgreSQL)
If the table is tenant-scoped:
```sql
ALTER TABLE <table> ADD COLUMN tenant_id BIGINT NOT NULL;
ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;
ALTER TABLE <table> FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON <table>
  USING (tenant_id = current_setting('app.tenant_id')::BIGINT);
```
MySQL/SQLite have no equivalent — enforce tenant filtering at the application layer.

### Enums
Use `TEXT` with `CHECK` constraints, not native `ENUM`:
```sql
status TEXT NOT NULL CHECK (status IN ('PENDING','ACTIVE','SUSPENDED','CLOSED'))
```
PostgreSQL's `CREATE TYPE ... AS ENUM` is hard to evolve (can't drop a value safely).

## Mode A: Liquibase

### File naming
```
src/main/resources/db/changelog/changes/sql/<scope>-<NNN>-<description>.sql
```
Example: `ledger-001-core-tables.sql`, `payment-002-add-expires-at.sql`.

### Required header format
```sql
--liquibase formatted sql
--changeset <author>:<scope>-<NNN>-<description>

-- ... DDL here ...

--rollback DROP INDEX idx_...;
--rollback DROP TABLE ...;
```

### Add-column pattern
```sql
--liquibase formatted sql
--changeset team:order-002-add-reference

ALTER TABLE orders ADD COLUMN reference TEXT;
CREATE UNIQUE INDEX idx_orders_reference ON orders(tenant_id, reference)
  WHERE reference IS NOT NULL;

--rollback DROP INDEX idx_orders_reference;
--rollback ALTER TABLE orders DROP COLUMN reference;
```

### Backfill pattern (split into separate changeset)
```sql
--liquibase formatted sql
--changeset team:order-003-backfill-status-batch
--runInTransaction:false

DO $$
DECLARE
    batch_size INT := 10000;
    rows_updated INT;
BEGIN
    LOOP
        UPDATE orders
           SET status = 'EXPIRED'
         WHERE id IN (
            SELECT id FROM orders
             WHERE status = 'ACTIVE' AND expires_at < now()
             LIMIT batch_size
         );
        GET DIAGNOSTICS rows_updated = ROW_COUNT;
        EXIT WHEN rows_updated = 0;
        PERFORM pg_sleep(0.05);  -- throttle
    END LOOP;
END $$;

--rollback SELECT 1; -- backfill is irreversible; document in ADR
```

## Mode B: Flyway 10+

### File naming
```
src/main/resources/db/migration/V<yyyyMMddHHmmss>__<snake_case_description>.sql
```
Use the current timestamp (not sequential numbers) to avoid merge conflicts.

### Standard migration
```sql
-- Create orders table

CREATE TABLE orders (
    id                BIGINT PRIMARY KEY,
    tenant_id         BIGINT NOT NULL,
    amount            NUMERIC(20,2) NOT NULL CHECK (amount > 0),
    currency          TEXT NOT NULL,
    status            TEXT NOT NULL CHECK (status IN ('ACTIVE','CANCELLED','PAID')),
    created_by        TEXT NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_modified_by  TEXT,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_orders_tenant_status ON orders(tenant_id, status);
```

### Flyway undo (Teams edition)
Sibling file: `U<yyyyMMddHHmmss>__<snake_case_description>.sql` mirroring the up migration in reverse.

### Index on populated table — use CONCURRENTLY
```sql
-- Mark this migration transactional=false (Flyway header or spring.flyway.mixed=true)

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_created_at
  ON orders(created_at);
```

## Universal safety rules

1. **Never DROP without explicit confirmation.** If the user asks to drop a table/column, first show:
   - Row count: `SELECT COUNT(*) FROM <table>`
   - Dependencies: `SELECT * FROM pg_depend WHERE refobjid = '<table>'::regclass` (PG)
   - Referencing FKs
   Then ask: "Confirm destructive operation? [yes/no]"
2. **Never rename a column on a populated table in one step.** Two-phase:
   - Phase 1 (non-breaking): add new column, dual-write from app, backfill
   - Phase 2 (cleanup, after deploy verifies dual-write): drop old column
3. **Indexes on large tables must use `CONCURRENTLY`** (PostgreSQL). MySQL: use `ALGORITHM=INPLACE, LOCK=NONE`. SQLite: there is no online index build — scheduling-only.
4. **Foreign keys on large tables must be added `NOT VALID` then `VALIDATE CONSTRAINT`** (PostgreSQL):
   ```sql
   ALTER TABLE child ADD CONSTRAINT fk_parent FOREIGN KEY (parent_id) REFERENCES parent(id) NOT VALID;
   ALTER TABLE child VALIDATE CONSTRAINT fk_parent;  -- runs without exclusive lock
   ```
5. **`NOT NULL` on a populated column is a multi-step migration**, not a single ALTER:
   - Phase 1: add column nullable with a default; backfill in batches
   - Phase 2: switch to `SET NOT NULL` after the backfill completes
   Adding `NOT NULL` directly to an existing column on a large table is a table-rewrite-and-lock hazard.
6. **Every changeset has a rollback.** Even if it's `SELECT 1; -- irreversible, see ADR`.
7. **Backfills are throttled** (`pg_sleep(0.05)` between batches) and run in non-transactional mode.
8. **Seed data uses `ON CONFLICT DO NOTHING`** (PG) / `INSERT IGNORE` (MySQL) — seeds must be idempotent.

## Verification SQL (always generate alongside the migration)

After creating a migration, generate a verification file that asserts the expected state. Pattern:

```sql
-- verify-order-001.sql
SELECT 1 / (CASE WHEN
    (SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'orders') = 1
  THEN 1 ELSE 0 END);  -- divide-by-zero fails the assertion

SELECT 1 / (CASE WHEN
    (SELECT COUNT(*) FROM information_schema.columns
      WHERE table_name = 'orders' AND column_name = 'tenant_id') = 1
  THEN 1 ELSE 0 END);

SELECT 1 / (CASE WHEN
    (SELECT relrowsecurity FROM pg_class WHERE relname = 'orders') = TRUE
  THEN 1 ELSE 0 END);
```

(Use a real assertion helper if your project ships one; otherwise the `1/0` pattern above is portable.)

## Output contract

For each migration request, produce:

- The migration file (Liquibase / Flyway / plain SQL — match detected mode)
- A verification SQL file (`docs/migrations/verify-<description>.sql`)
- A rollback plan or undo file (`U…` for Flyway Teams; `--rollback` for Liquibase; documented for plain SQL)
- A short markdown note (`docs/migrations/<description>.md`) covering: rollback plan, blast radius, expected lock behavior, estimated downtime

## Anti-patterns (never generate)

- `SERIAL` / `BIGSERIAL` / `IDENTITY` PKs in projects that have committed to TSID/ULID/Snowflake
- Native `CREATE TYPE ... AS ENUM` — use `TEXT` + `CHECK`
- `TIMESTAMP` without time zone for event times — always `TIMESTAMPTZ`
- `DECIMAL`, `DOUBLE PRECISION`, `REAL`, `MONEY` for money — always `NUMERIC(20,2)` or `NUMERIC(20,8)`
- Renaming a column on a populated table in one step — two-phase
- `DROP TABLE ... CASCADE` without rollback script — irreversible
- Index creation without `CONCURRENTLY` on populated PG tables
- Adding `NOT NULL` to a populated column in one step — multi-phase
- Adding FK without `NOT VALID` on large tables
- Missing audit columns on business tables
- Foreign keys without an index on the FK column
- Seeds without `ON CONFLICT DO NOTHING` / `INSERT IGNORE`
- Using Liquibase XML format — always `--liquibase formatted sql`
- Mixing multiple unrelated changes in one changeset — one concern per file

## When this skill is **not** the right fit

- ORM-managed migrations (Alembic, Django migrations, ActiveRecord, Prisma, TypeORM, Diesel) — those have their own conventions. Apply the safety rules above but defer to the framework's idioms for file structure.
- NoSQL / document stores — mostly N/A (different concerns: index builds, bulk re-shape via background jobs).
- Snowflake / BigQuery / other warehouses — these have very different lock semantics and benefit from their own playbook.
