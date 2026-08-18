| Field         | Value                              |
|---------------|------------------------------------|
| Task ID       | TST-001                            |
| Type          | F                                  |
| Area          | tst                                |
| Repos         | N/A                                |
| Autonomy      | L1                                 |
| Created       | 2026-08-01T09:00:00                |
| Updated       | 2026-08-02T10:15:00                |
| Last executed | 2026-08-02T10:00:00                |
| Status        | open                               |
| Priority      | high                               |
| Target date   | 2026-09-01                         |
| Deadline      | N/A                                |
| Owner         | fixture-owner                      |
| Blocked by    | N/A                                |
| Spec refs     | self                               |
| Source        | add-task                           |
| Source ref    | N/A                                |

## Full metadata fixture task

### Brief

Fixture task exercising every recognized metadata row so `sync_todo_ledgers.py --check` still
format-checks optional fields when they are present, even though they are no longer required.

### Specification

Planned behavior: none, this is fixture data for `test_sync_todo_ledgers.py`.

### Phases

#### Phase 1: Setup

- [x] Create fixture directory structure
- [x] Register the `tst` area and `TST` prefix

#### Phase 2: Verification

- [ ] Confirm `--check` reports zero errors

### Acceptance criteria

- [ ] `at ledger check` reports zero errors for this fixture

### Related tests

- `scripts/tests/test_sync_todo_ledgers.py` - exercises this fixture via subprocess

### Follow-ups

- None

---

## Execution log

Append-only record of actions taken, decisions made, test results, and outcome.

### 2026-08-01T09:00:00 - Fixture created

**Actions taken:**
- Wrote the fixture task file with the full metadata table.

**Outcome:** Fixture ready for use by `test_sync_todo_ledgers.py`.

---

## Completion harvest

| Item | Result |
|------|--------|
| Resource updates | None |
| Area updates | None |
| Follow-ups | None |
| Notable decisions/deviations | None |

## Completion summary

Not applicable; this task stays `open` as fixture data.
