---
name: wayfinder
description: "Plan an effort too big for one session as a map of decision tickets held in a single task file, and resolve them one at a time until the way to the destination is clear."
disable-model-invocation: true
metadata:
  source: "github.com/mattpocock/skills@885e2ca skills/engineering/wayfinder/SKILL.md (adapted to the task ledger)"
  pack: task-management
paths: ["docs/tasks_manager/**"]
---

# Wayfinder

A loose idea has arrived, too big for one agent session, and wrapped in fog: the way from here to the
**destination** is not visible yet. Wayfinding is about finding that way, not charging at the
destination. This skill charts the way as a **map** — one task file — then works its **decision
tickets** one at a time until the route is clear.

The destination varies per effort, and naming it is the first act of charting: it shapes every ticket.
It might be a spec to hand off, a decision to lock before planning starts, or a change made in place
like a data-structure migration.

## Plan, don't do

Wayfinder is **planning**. Each ticket resolves a decision, and the map is done when the way is clear,
with nothing left to decide before someone goes and does the thing. The pull to just do the work is
usually the signal you have reached the edge of the map and it is time to hand off. An effort can
override this in its **Notes**, carrying execution into the map itself; absent that, produce decisions,
not deliverables.

## Refer by name

Every ticket has a title. In everything the human reads — narration, Decisions so far — refer to it by
name, never by a bare id: "T-042.3 Storage engine", not "#3". A wall of ids is illegible; names read at
a glance. The id rides inside the name, it does not stand in for it.

## The map

**The map is one ordinary task file** under `docs/tasks_manager/_todos/`, reserved with
`at reserve task <PREFIX> R <slug>` (type `R`, research/spike), `Source: wayfinder`,
`Spec refs: self`. So the map appears in `_active.md`, can be placed on `_roadmap.md`, rolls up on its
area page, and closes through `agents-tasks:complete-task` like any other task. Follow the `agents-tasks:task-ledger` skill
(references/todo-convention.md) for the file format; the full map layout is in
[references/map-template.md](references/map-template.md).

The map is an **index**, not a store. **Decisions so far** lists one line per resolved ticket and
points at the ticket that holds the detail; a decision lives in exactly one place.

**Tickets are dotted sub-ids of the map** — `T-042.1`, `T-042.2` — held in a `## Tickets` section of
the same file. They are not ledger tasks: no `at reserve`, no new IDs in `_active.md`, nothing for a
reader to wonder about. One map, one ID, one file to read.

Three layout rules keep `at ledger check` correct, because it scans the whole file (details and the
ready-to-fill template in [references/map-template.md](references/map-template.md)):

- The tickets index is a table whose first column is `Ticket`. No other line in the file starts with
  `|`, because every such line is read as task metadata.
- Ticket bodies are `### <id> — <title>`. Only the map's own three phases use `#### `, because every
  `#### ` heading counts as a phase.
- Ticket bodies carry no checkboxes.

A ticket's state is one of `open`, `claimed`, `resolved`, `out-of-scope`, written in both the index row
and the ticket's own `Type: … · State: …` line. A ticket is **unblocked** when every ticket it lists
under `Blocked by` is `resolved`; the **frontier** is the open, unblocked, unclaimed tickets — the edge
of the known. A session **claims** a ticket by writing its own name into `Claimed by` and setting
`claimed`, **first**, before any work, and commits that edit — the index row is the lock, so a
concurrent session sees it and skips.

## Ticket types

Every ticket is either **HITL** (worked _with_ a human who speaks for themselves) or **AFK** (driven by
the agent alone). A HITL ticket only resolves through that live exchange; the agent never stands in for
the human's side of it — a grilling that answers its own questions has broken this.

- **grilling** (HITL, the default): conversation. Invoke `agents-core:grilling` and `agents-extras:domain-modeling`.
- **research** (AFK): a fact a decision waits on, from docs, third-party APIs, or the knowledge base.
  Invoke the `agents-core:research` skill; findings land under `docs/resources/_reports/research/` and the ticket
  links them.
- **prototype** (HITL): raise the fidelity of the discussion with a cheap, rough, concrete artifact to
  react to. Invoke `agents-core:prototype` and link what it produced.
- **task** (HITL or AFK): manual work that must happen before a _decision_ can be made — signing up for
  a service so its API can be judged, provisioning access, moving data so its shape can be seen.
  Nothing to decide, but the discussion is blocked until it is done. The agent drives it alone where it
  can; otherwise it hands the human a precise checklist. When the blocker is another person's
  knowledge, `agents-extras:to-questionnaire` is the artifact. The answer records what was done and any facts later
  tickets depend on (where credentials live, new URLs, row counts).

## Fog of war

The map is _deliberately_ incomplete: don't chart what you can't yet see. Beyond the live tickets lies
the **fog of war** — decisions you can tell are coming but cannot yet pin down, because they hang on
questions still open. Resolving a ticket clears the fog ahead of it, graduating whatever is now
specifiable into fresh tickets, until the way to the destination is clear and no tickets remain.

**Not yet specified** is where that dim view is written down: the suspected question, the area to
revisit. Everything there is in scope, just not sharp enough to ticket.

**Fog or ticket?** The test is whether you can state the question precisely now, _not_ whether you can
answer it now. Ticket when the question is already sharp, even if it is blocked. Leave it in the fog
when you cannot yet phrase it that sharply — and leave it coarse: one patch may graduate into several
tickets, or none.

## Out of scope

Fog only ever gathers _toward_ the destination. Work beyond the destination is **out of scope**: it is
not fog, and it gets its own section. Scope, not sharpness, lands it there. Out-of-scope work never
graduates; it returns only if the destination is redrawn, and then as a fresh effort.

When a ticket turns out to sit past the destination, set it `out-of-scope` and leave one line in the
**Out of scope** section: the gist plus why, naming the ticket. It stays out of **Decisions so far**,
which records the route actually walked.

## Chart the map

The user invokes with a loose idea.

1. **Name the destination.** Invoke `agents-core:grilling` and `agents-extras:domain-modeling` to pin down what this map is
   finding its way to. The destination fixes the scope, so it settles first.
2. **Map the frontier.** Grill again, **breadth-first**: fan out across the whole space rather than
   deep on any one thread, surfacing the open decisions and the first steps takeable now. **If this
   surfaces no fog** — the way is already clear, the journey small enough for one session — say so and
   stop: use `agents-tasks:add-task` or `agents-core:planning-workflow` instead of a map.
3. **Create the map.** `at reserve task <PREFIX> R <slug>`, then fill
   [references/map-template.md](references/map-template.md): Destination and Notes written, Decisions
   so far empty, the fog sketched into Not yet specified.
4. **Create the tickets you can specify now**, then wire `Blocked by` in a **second pass** once they
   all have ids. Wiring sorts them into the frontier and the blocked; everything you cannot yet specify
   stays in the fog.
5. **Fire the research tickets.** For each `research` ticket, invoke `agents-core:research` so they resolve in
   parallel while the conversation continues.
6. Log the charting session, run `at ledger sync && at ledger check`, and **stop**. Charting is one
   session's work; it hand-resolves nothing.

## Work the map

The user invokes with a map (task ID or path). A ticket is **optional**: without one, you pick the next
decision, not the user.

1. **Load the map**: Destination, Notes, Decisions so far, the tickets index. Zoom into a ticket body,
   a resolved ticket, or a linked artifact only when you need it.
2. **Choose the ticket.** The user's, if they named one; otherwise the first frontier ticket in order.
   **Claim it** — `claimed` plus `Claimed by` in the index row and the ticket body — and commit that
   before any work.
3. **Resolve it** with its type's skills (above), plus whatever the Notes name.
4. **Record the resolution**: write the **Answer** into the ticket body, set `resolved` in both places,
   and append the one-line gist to **Decisions so far**. Long material links out — a research report, a
   plan, an ADR, a prototype — never pasted into the map.
5. **Advance the map.** Graduate any fog the answer made specifiable into new tickets (create, then
   wire), clearing each graduated patch from Not yet specified. Rule newly out-of-scope tickets
   `out-of-scope`. If the decision invalidates other tickets, update or remove them.
6. Append an execution-log entry, run `at ledger sync && at ledger check`, and stop. **One ticket per
   session**, research tickets excepted — they are AFK and can run alongside.

## Hand off

When the frontier is empty, the map has done its job: produce the destination artifact —
`docs/_plans/<slug>.md` via `agents-core:planning-workflow`, a spec via `agents-core:task-spec-workflow`, implementation tasks
via `agents-tasks:prd-to-todos` with real `Blocked by` edges, ADRs via `agents-extras:domain-modeling` — link it from the map, then
close the map with `agents-tasks:complete-task`. The harvest names the artifacts the map produced.

## Quality bar

- The map is a valid task file: `at ledger check` passes, phases read `0/3` … `3/3`, and the task's own
  `Status` is untouched by ticket states.
- Every ticket names a question, not a chunk of work to build.
- Decisions so far has exactly one line per resolved ticket, and the detail lives only in the ticket.
- The map stays under 400 lines (`at ledger check` warns past it) because answers link out; rotate the
  execution log with `at ledger rotate-log <TASK-ID>` when it grows.
- Nothing is silently assumed: every branch is a resolved ticket, a fog line, or an out-of-scope line.
