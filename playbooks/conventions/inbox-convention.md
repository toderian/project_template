# Inbox Convention

## Purpose

The inbox is the **frictionless capture layer** that sits before the todo layer. When you have an idea —
a feature, a bug you noticed, a thing to look into — it goes into the inbox *immediately*, with near-zero
ceremony. No phases, no acceptance criteria, no commitment. Triage later turns the good ones into full
todos.

The whole point is speed of capture: an idea half-written is an idea kept. Don't make the user answer
questions to record a thought.

Lifecycle: `Inbox idea (I-NNN) → triage → Todo (T-NNN, typed)` — see
`playbooks/conventions/todo-convention.md` for the todo layer.

## Directory structure

```
docs/
├── _inbox/              # Raw ideas, one file per idea
└── _inbox_archived/     # Promoted or dropped ideas
```

Create them (with `.gitkeep`) if missing.

## File naming

```
I-<NNN>_<short-description>.md
```

- `I-<NNN>` — the **Inbox ID**: zero-padded 3-digit handle (e.g. `I-007`). This is a *separate* counter
  from the todo `T-NNN` sequence — see ID counters below.
- `<short-description>` — lowercase, hyphenated, under 50 characters.

```
I-007_dark-mode-toggle.md
```

The capture datetime is not in the filename — it lives in the `Captured` field.

## ID counters

```
next I = (highest I-NNN found across docs/_inbox/ AND docs/_inbox_archived/) + 1
```

Scan both directories so archived ideas still reserve their numbers. Inbox IDs and todo IDs are
independent: promoting `I-007` to a todo assigns a *fresh* `T-NNN`, and the todo records `Source ref:
I-007` to keep the trail.

## File format

Deliberately minimal — a tiny header plus the raw idea:

```markdown
| Field    | Value               |
|----------|---------------------|
| Inbox ID | I-007               |
| Captured | 2026-05-25T14:30:00 |
| Area     | ui                  |
| Status   | new                 |

## Dark mode toggle in settings

One or two sentences capturing the idea while it's fresh. Enough to remember what you meant at triage
time — not a spec.
```

Field notes:

- **Captured** — ISO 8601 datetime the idea was recorded.
- **Area** — best-guess slug from `docs/_areas.md`, or `—` if unclear. A guess is fine; triage confirms it.
- **Status** — `new` | `promoted` | `dropped`.

## Capturing (the fast path)

When the user shares an idea to capture:

1. Compute the next `I-NNN`.
2. Write `docs/_inbox/I-NNN_<short-desc>.md` with `Captured` = now and `Status: new`.
3. Best-guess the `Area` from `docs/_areas.md`; use `—` rather than interrogating the user.
4. Capture the idea text in one or two sentences. Confirm briefly; don't quiz.

The `capture-idea` skill automates this.

## Triaging (idea → todo)

Periodically review `docs/_inbox/` (the `triage-inbox` skill drives this). For each `new` idea, decide:

- **Promote** — it's worth doing. Create a full todo per `todo-convention.md`: assign the next `T-NNN`,
  set `Type` (`F`/`D`/`C`/`R`), confirm/assign `Area` (defining a new one with the user if needed), set
  `Source: inbox` and `Source ref: I-NNN`, split into phases, add acceptance criteria, and add the row to
  `docs/_active.md`. Then set the inbox file's `Status: promoted`.
- **Drop** — not worth doing. Set `Status: dropped` and note why in the body.

Either way, move the inbox file to `docs/_inbox_archived/` once it's `promoted` or `dropped`, so the
inbox only ever shows live ideas.

## Why archive instead of delete

Promoted/dropped ideas move to `_inbox_archived/` rather than being deleted, so the origin of a todo
(and the reasoning behind dropped ideas) stays traceable. The promoted todo's `Source ref: I-NNN` points
straight back.
