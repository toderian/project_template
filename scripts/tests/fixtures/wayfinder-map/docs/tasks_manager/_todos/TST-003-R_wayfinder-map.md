| Field         | Value               |
|---------------|---------------------|
| Task ID       | TST-003             |
| Type          | R                   |
| Area          | tst                 |
| Created       | 2026-08-19T09:00:00 |
| Updated       | 2026-08-19T09:00:00 |
| Last executed | N/A                 |
| Status        | open                |
| Priority      | medium              |
| Owner         | N/A                 |
| Blocked by    | N/A                 |
| Spec refs     | self                |
| Source        | wayfinder           |
| Source ref    | N/A                 |

## Wayfinder map fixture

### Brief

Fixture map produced by the `wayfinder` skill. It exists to pin the two layout rules that keep a map
readable to `at ledger check`: the tickets index must not look like task metadata, and ticket bodies
must not look like phases.

### Destination

A decision the ledger can validate without seeing ticket state leak into task state.

### Notes

Fixture data only.

### Decisions so far

- TST-003.2 Vendor limits: free tier is enough for v1.

### Not yet specified

- Whether the retention rule changes the storage choice.

### Out of scope

- None yet.

### Phases

#### Phase 1: Chart the map

- [x] Destination named and agreed
- [x] Frontier mapped breadth-first
- [x] Tickets created and blocking edges wired

#### Phase 2: Work the map

- [ ] Frontier empty: every ticket resolved or ruled out of scope

#### Phase 3: Hand off

- [ ] Destination artifact produced and linked from the harvest

### Acceptance criteria

- [ ] Every ticket is resolved or out of scope
- [ ] `at ledger check` passes

### Related tests

- `scripts/tests/test_sync_todo_ledgers.py` - wayfinder map layout

### Follow-ups

- None

## Tickets

| Ticket | Title | Type | State | Blocked by | Claimed by |
|---|---|---|---|---|---|
| TST-003.1 | Storage engine | grilling | claimed | — | vi |
| TST-003.2 | Vendor limits | research | resolved | — | vi |

### TST-003.1 — Storage engine

Type: grilling · State: claimed · Blocked by: — · Claimed by: vi

**Question.** Which storage engine do we commit to?

### TST-003.2 — Vendor limits

Type: research · State: resolved · Blocked by: — · Claimed by: vi

**Question.** What are the vendor's documented limits?

**Answer.** Free tier covers v1.

---

## Execution log

### 2026-08-19T09:00:00 - Chart the map

**Outcome:** Map charted with two tickets.

## Completion harvest

| Item | Result |
|------|--------|
| Resource updates | |
| Area updates | |
| Follow-ups | |
| Notable decisions/deviations | |

## Completion summary

<!-- filled at hand-off -->
