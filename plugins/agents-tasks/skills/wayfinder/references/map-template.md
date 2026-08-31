# Wayfinder map template

Fill this into the file `at reserve task <PREFIX> R <slug>` created under
`docs/tasks_manager/_todos/`. It is an ordinary task file: the metadata table, phases, acceptance
criteria and log are exactly what `agents-tasks:task-ledger` (references/todo-convention.md) requires. The only
addition is the `## Tickets` section.

Three rules keep `at ledger check` correct, because it scans the whole file:

- Every line starting with `|` is read as task metadata. The tickets index is safe because its first
  column is `Ticket`, which is not a metadata key — keep it that way, and never start a ticket line
  with `|` anywhere else.
- Every `#### ` heading counts as a phase. The three phases below are the only ones; ticket bodies use
  `### `.
- Checkbox items count toward phase progress only inside a `#### ` phase, so ticket bodies carry no
  checkboxes.

---

````markdown
| Field         | Value                    |
|---------------|--------------------------|
| Task ID       | T-042                    |
| Type          | R                        |
| Area          | global                   |
| Created       | 2026-08-19T10:30:00      |
| Updated       | 2026-08-19T10:30:00      |
| Last executed | N/A                      |
| Status        | open                     |
| Priority      | medium                   |
| Owner         | N/A                      |
| Blocked by    | N/A                      |
| Spec refs     | self                     |
| Source        | wayfinder                |
| Source ref    | N/A                      |

## <Map name: the effort, in words a human recognises>

### Brief

The loose idea that arrived, and why it needs a map rather than a plan: too big for one session, and
the way from here to the destination is not visible yet.

### Destination

What reaching the end of this map looks like: the spec, decision, or change this effort is finding its
way to. One or two lines — every session orients to it before choosing a ticket.

### Notes

Domain; skills every session should consult; standing preferences for this effort.

### Decisions so far

<!-- index only: one line per resolved ticket, then zoom into the ticket for the detail -->

- None yet.

### Not yet specified

<!-- fog: in-scope questions you cannot phrase sharply enough to ticket yet -->

- None yet.

### Out of scope

<!-- work ruled beyond the destination; never graduates -->

- None yet.

### Phases

#### Phase 1: Chart the map

- [ ] Destination named and agreed
- [ ] Frontier mapped breadth-first
- [ ] Tickets created and blocking edges wired

#### Phase 2: Work the map

- [ ] Frontier empty: every ticket resolved or ruled out of scope

#### Phase 3: Hand off

- [ ] Destination artifact produced and linked from the harvest

### Acceptance criteria

- [ ] Every ticket is resolved or out of scope, and nothing is left silently assumed
- [ ] The destination artifact exists and is linked here
- [ ] `at ledger check` passes

### Related tests

- N/A - planning map

### Follow-ups

- None

## Tickets

| Ticket | Title | Type | State | Blocked by | Claimed by |
|---|---|---|---|---|---|
| T-042.1 | Storage engine | grilling | open | T-042.2 | — |
| T-042.2 | Vendor API limits | research | open | — | — |

### T-042.1 — Storage engine

Type: grilling · State: open · Blocked by: T-042.2 · Claimed by: —

**Question.** Which storage engine do we commit to, given the write pattern and the retention rule?

### T-042.2 — Vendor API limits

Type: research · State: open · Blocked by: — · Claimed by: —

**Question.** What are the vendor's documented rate and payload limits, and what do they cost?

---

## Execution log

Append-only. One entry per charting or ticket session.

## Completion harvest

| Item | Result |
|------|--------|
| Resource updates | |
| Area updates | |
| Follow-ups | |
| Notable decisions/deviations | |

## Completion summary

<!-- filled by /complete-task when the map is handed off -->
````

## Resolved ticket shape

```markdown
### T-042.2 — Vendor API limits

Type: research · State: resolved · Blocked by: — · Claimed by: vi

**Question.** What are the vendor's documented rate and payload limits, and what do they cost?

**Answer.** 100 req/s burst, 10 MB payload, hard 30-day retention on the free tier.
Full findings: `docs/resources/_reports/research/2026-08-19T103000+0300_vendor-api-limits.md`
```

And in the map's Decisions so far:

```markdown
- T-042.2 Vendor API limits: 100 req/s, 10 MB payload, 30-day retention — free tier is enough for v1.
```
