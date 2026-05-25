# Capture Idea

## Purpose

Record an idea into the inbox the instant the user has it, with near-zero friction. The user gets an
idea — a feature, a bug they noticed, something to look into — and it gets written down immediately as
an `I-NNN` inbox file. No phases, no acceptance criteria, no commitment; triage (`triage-inbox`) turns
the good ones into real todos later.

The single most important quality of this skill is **speed of capture**. An idea that takes a
conversation to record is an idea lost. Don't interrogate the user — capture what they said, make a
reasonable area guess, and confirm in one line.

Follow `playbooks/conventions/inbox-convention.md` for the format and ID rules.

## Process

1. **Read the idea from context.** Usually it's whatever the user just said ("capture: add a dark mode
   toggle", "idea — the login feels slow"). Don't ask clarifying questions unless the idea is genuinely
   unintelligible.

2. **Compute the next Inbox ID.** Scan `docs/_inbox/` and `docs/_inbox_archived/` for the highest
   `I-NNN` and add 1 (zero-padded, 3 digits). Create `docs/_inbox/` (with `.gitkeep`) if missing.

3. **Best-guess the area.** Glance at `docs/_areas.md` and pick the slug that fits. If nothing fits,
   use `—` — do **not** stop to define a new area here; that's triage's job. A wrong guess is cheap.

4. **Write the file** `docs/_inbox/I-NNN_<short-desc>.md` using the inbox format: a tiny header
   (`Inbox ID`, `Captured` = now in ISO 8601, `Area`, `Status: new`) and one or two sentences of the
   idea in the user's own framing.

5. **Confirm in one line.** e.g. "Captured as I-007 (area: ui)." Then stop. If the user immediately
   adds detail, append it; otherwise you're done.

## Capturing several at once

If the user dumps multiple ideas in one message, create one file per idea with consecutive IDs. Keep
each atomic — one idea per file — so triage can promote or drop them independently.

## Quality bar

- The file passes the `block-bad-todo-name.sh` naming check (`I-NNN_<lowercase-hyphenated>.md`).
- Capture took no unnecessary questions.
- The idea text is enough to remember the intent at triage time — not a spec.
- `Status` is `new`; the file is in `docs/_inbox/` (not archived).
