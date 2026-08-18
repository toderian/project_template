| Field    | Value                |
|----------|----------------------|
| Task ID  | TST-002              |
| Type     | C                    |
| Area     | tst                  |
| Status   | open                 |
| Priority | low                  |
| Created  | 2026-07-15T09:00:00  |
| Updated  | 2026-08-10T09:00:00  |
| Source   | add-task             |

## Oversized execution log fixture task

### Brief

Fixture task whose `## Execution log` section body is exactly 250 lines long, to exercise the
`at ledger check` "execution log exceeds 200 lines" warning and the `at ledger rotate-log TST-002`
rotation path.

### Phases

#### Phase 1: Only phase

- [ ] Nothing to do; this is fixture data

### Acceptance criteria

- [ ] `at ledger check` warns that the execution log exceeds 200 lines
- [ ] `at ledger rotate-log TST-002` moves the log body to docs/tasks_manager/_logs/TST-002.md

### Related tests

- `scripts/tests/test_sync_todo_ledgers.py` - exercises this fixture via subprocess

### Follow-ups

- None

---

## Execution log

### 2026-08-02T09:00:00 - Entry 1

**Actions taken:**
- Simulated action 1 for the oversized-log fixture.

### 2026-08-03T09:00:00 - Entry 2

**Actions taken:**
- Simulated action 2 for the oversized-log fixture.

### 2026-08-04T09:00:00 - Entry 3

**Actions taken:**
- Simulated action 3 for the oversized-log fixture.

### 2026-08-05T09:00:00 - Entry 4

**Actions taken:**
- Simulated action 4 for the oversized-log fixture.

### 2026-08-06T09:00:00 - Entry 5

**Actions taken:**
- Simulated action 5 for the oversized-log fixture.

### 2026-08-07T09:00:00 - Entry 6

**Actions taken:**
- Simulated action 6 for the oversized-log fixture.

### 2026-08-08T09:00:00 - Entry 7

**Actions taken:**
- Simulated action 7 for the oversized-log fixture.

### 2026-08-09T09:00:00 - Entry 8

**Actions taken:**
- Simulated action 8 for the oversized-log fixture.

### 2026-08-10T09:00:00 - Entry 9

**Actions taken:**
- Simulated action 9 for the oversized-log fixture.

### 2026-08-11T09:00:00 - Entry 10

**Actions taken:**
- Simulated action 10 for the oversized-log fixture.

### 2026-08-12T09:00:00 - Entry 11

**Actions taken:**
- Simulated action 11 for the oversized-log fixture.

### 2026-08-13T09:00:00 - Entry 12

**Actions taken:**
- Simulated action 12 for the oversized-log fixture.

### 2026-08-14T09:00:00 - Entry 13

**Actions taken:**
- Simulated action 13 for the oversized-log fixture.

### 2026-08-15T09:00:00 - Entry 14

**Actions taken:**
- Simulated action 14 for the oversized-log fixture.

### 2026-08-16T09:00:00 - Entry 15

**Actions taken:**
- Simulated action 15 for the oversized-log fixture.

### 2026-08-17T09:00:00 - Entry 16

**Actions taken:**
- Simulated action 16 for the oversized-log fixture.

### 2026-08-18T09:00:00 - Entry 17

**Actions taken:**
- Simulated action 17 for the oversized-log fixture.

### 2026-08-19T09:00:00 - Entry 18

**Actions taken:**
- Simulated action 18 for the oversized-log fixture.

### 2026-08-20T09:00:00 - Entry 19

**Actions taken:**
- Simulated action 19 for the oversized-log fixture.

### 2026-08-21T09:00:00 - Entry 20

**Actions taken:**
- Simulated action 20 for the oversized-log fixture.

### 2026-08-22T09:00:00 - Entry 21

**Actions taken:**
- Simulated action 21 for the oversized-log fixture.

### 2026-08-23T09:00:00 - Entry 22

**Actions taken:**
- Simulated action 22 for the oversized-log fixture.

### 2026-08-24T09:00:00 - Entry 23

**Actions taken:**
- Simulated action 23 for the oversized-log fixture.

### 2026-08-25T09:00:00 - Entry 24

**Actions taken:**
- Simulated action 24 for the oversized-log fixture.

### 2026-08-26T09:00:00 - Entry 25

**Actions taken:**
- Simulated action 25 for the oversized-log fixture.

### 2026-08-27T09:00:00 - Entry 26

**Actions taken:**
- Simulated action 26 for the oversized-log fixture.

### 2026-08-28T09:00:00 - Entry 27

**Actions taken:**
- Simulated action 27 for the oversized-log fixture.

### 2026-08-01T09:00:00 - Entry 28

**Actions taken:**
- Simulated action 28 for the oversized-log fixture.

### 2026-08-02T09:00:00 - Entry 29

**Actions taken:**
- Simulated action 29 for the oversized-log fixture.

### 2026-08-03T09:00:00 - Entry 30

**Actions taken:**
- Simulated action 30 for the oversized-log fixture.

### 2026-08-04T09:00:00 - Entry 31

**Actions taken:**
- Simulated action 31 for the oversized-log fixture.

### 2026-08-05T09:00:00 - Entry 32

**Actions taken:**
- Simulated action 32 for the oversized-log fixture.

### 2026-08-06T09:00:00 - Entry 33

**Actions taken:**
- Simulated action 33 for the oversized-log fixture.

### 2026-08-07T09:00:00 - Entry 34

**Actions taken:**
- Simulated action 34 for the oversized-log fixture.

### 2026-08-08T09:00:00 - Entry 35

**Actions taken:**
- Simulated action 35 for the oversized-log fixture.

### 2026-08-09T09:00:00 - Entry 36

**Actions taken:**
- Simulated action 36 for the oversized-log fixture.

### 2026-08-10T09:00:00 - Entry 37

**Actions taken:**
- Simulated action 37 for the oversized-log fixture.

### 2026-08-11T09:00:00 - Entry 38

**Actions taken:**
- Simulated action 38 for the oversized-log fixture.

### 2026-08-12T09:00:00 - Entry 39

**Actions taken:**
- Simulated action 39 for the oversized-log fixture.

### 2026-08-13T09:00:00 - Entry 40

**Actions taken:**
- Simulated action 40 for the oversized-log fixture.

### 2026-08-14T09:00:00 - Entry 41

**Actions taken:**
- Simulated action 41 for the oversized-log fixture.

### 2026-08-15T09:00:00 - Entry 42

**Actions taken:**
- Simulated action 42 for the oversized-log fixture.

### 2026-08-16T09:00:00 - Entry 43

**Actions taken:**
- Simulated action 43 for the oversized-log fixture.

### 2026-08-17T09:00:00 - Entry 44

**Actions taken:**
- Simulated action 44 for the oversized-log fixture.

### 2026-08-18T09:00:00 - Entry 45

**Actions taken:**
- Simulated action 45 for the oversized-log fixture.

### 2026-08-19T09:00:00 - Entry 46

**Actions taken:**
- Simulated action 46 for the oversized-log fixture.

### 2026-08-20T09:00:00 - Entry 47

**Actions taken:**
- Simulated action 47 for the oversized-log fixture.

### 2026-08-21T09:00:00 - Entry 48

**Actions taken:**
- Simulated action 48 for the oversized-log fixture.

### 2026-08-22T09:00:00 - Entry 49

**Actions taken:**
- Simulated action 49 for the oversized-log fixture.

### 2026-08-23T09:00:00 - Entry 50

**Actions taken:**
- Simulated action 50 for the oversized-log fixture.


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
