| Field         | Value                              |
|---------------|------------------------------------|
| Task ID       | TST-003                            |
| Type          | D                                  |
| Area          | tst                                |
| Created       | 2026-06-01T09:00:00                |
| Updated       | 2026-06-02T11:00:00                |
| Status        | cancelled                          |
| Priority      | low                                |
| Owner         | N/A                                |
| Blocked by    | N/A                                |
| Source        | add-task                           |
| Source ref    | N/A                                |

## Archived fixture task without a harvest section

### Brief

Fixture archived task that was cancelled and archived without ever filling in a Completion harvest
section. `at ledger check` must report this as a warning, not an error, per the slimmed validation in
this task.

### Phases

#### Phase 1: Only phase

- [ ] Never finished

### Acceptance criteria

- [ ] N/A - task was cancelled

### Related tests

- N/A - fixture data

### Follow-ups

- None

---

## Execution log

### 2026-06-02T11:00:00 - Cancelled

**Actions taken:**
- Cancelled the fixture task without filling in the completion harvest.

**Outcome:** Cancelled, harvest intentionally omitted for this fixture.
