| Field    | Value                |
|----------|----------------------|
| Task ID  | TST-001              |
| Type     | F                    |
| Area     | tst                  |
| Status   | open                 |
| Priority | medium               |
| Created  | 2026-08-10T09:00:00  |
| Updated  | 2026-08-10T09:00:00  |
| Source   | add-task             |

## Minimal metadata fixture task

### Brief

Fixture task whose metadata table only carries the now-required fields (Task ID, Type, Area, Status,
Priority, Created, Updated, Source) to confirm `at ledger check` no longer flags the newly-optional
fields (Last executed, Owner, Blocked by, Source ref) as missing.

### Phases

#### Phase 1: Only phase

- [ ] Nothing to do; this is fixture data

### Acceptance criteria

- [ ] `at ledger check` reports zero errors for this fixture

### Related tests

- `scripts/tests/test_sync_todo_ledgers.py` - exercises this fixture via subprocess

### Follow-ups

- None

---

## Execution log

Append-only record of actions taken, decisions made, test results, and outcome.

### 2026-08-10T09:00:00 - Fixture created

**Actions taken:**
- Wrote the fixture task file with the minimal metadata table.

**Outcome:** Fixture ready for use by `test_sync_todo_ledgers.py`.
