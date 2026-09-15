| Field         | Value                                         |
|---------------|-----------------------------------------------|
| Task ID       | TST-003                                       |
| Type          | F                                             |
| Area          | tst                                           |
| Repos         | demo-service                                  |
| Autonomy      | L1                                            |
| Created       | 2026-09-15T09:00:00                           |
| Updated       | 2026-09-15T09:00:00                           |
| Last executed | N/A                                           |
| Status        | open                                          |
| Priority      | medium                                        |
| Owner         | N/A                                           |
| Blocked by    | N/A                                           |
| Spec refs     | self, docs/resources/demo/contracts/widget.md |
| Source        | add-task                                      |
| Source ref    | N/A                                           |

## Brief-source fixture task

### Brief

Fixture task with every optional section populated so `at task brief` and `at task run-state` can be
exercised against a realistic file. The brief for one phase must carry this text, that phase only,
the acceptance criteria, related tests, specification, design, and spec refs.

### Specification

Widgets must be validated before they are persisted. Malformed widgets are rejected with a typed error.

### Design

Add `WidgetValidator` behind the repository boundary; route existing writes through it.

### Phases

#### Phase 1: Current-state review

- [ ] Map current widget write paths
- [ ] List existing tests

#### Phase 2: Implementation

- [ ] Add `WidgetValidator`
- [ ] Route writes through it

#### Phase 3: Hardening

- [ ] Add malformed-widget tests

### Acceptance criteria

- [ ] Existing valid widgets continue to persist
- [ ] Malformed widgets are rejected with `WidgetError`

### Related tests

- `tests/test_widgets.py` - validator behavior

### Follow-ups

- None

---

## Execution log

Append-only record of actions taken, decisions made, test results, and outcome.

### 2026-09-15T09:00:00 - Fixture created

**Actions taken:**
- Wrote the fixture task file.

**Outcome:** SECRET-LOG-MARKER must never appear in a brief.

---

## Completion harvest

| Item | Result |
|------|--------|
| Resource updates | None |
| Area updates | None |
| Follow-ups | None |
| Notable decisions/deviations | None |

## Completion summary

Placeholder.
