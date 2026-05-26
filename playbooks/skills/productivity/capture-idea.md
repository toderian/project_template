# Capture Idea

## Purpose

Record an idea into the inbox the instant the user has it, with near-zero friction. The user gets an
idea — a feature, a bug they noticed, something to look into — and it gets written down immediately as
an `I-NNN` inbox file. No phases, no acceptance criteria, no commitment; triage (`triage-inbox`) turns
the good ones into real tasks later.

The single most important quality of this skill is **speed of capture**. An idea that takes a
conversation to record is an idea lost. Don't interrogate the user — capture what they said, make a
reasonable area guess, and confirm in one line.

Follow `playbooks/conventions/inbox-convention.md` for the format and ID rules.

Prerequisite: `docs/tasks_manager/` must already be initialized. If it is missing, run `/init` first.

## Process

1. **Read the idea from context.** Usually it's whatever the user just said ("capture: add a dark mode
   toggle", "idea — the login feels slow"). Don't ask clarifying questions unless the idea is genuinely
   unintelligible.

2. **Check for a duplicate (the fast path stays fast).** Before creating anything, scan for an existing
   match so the same idea isn't recorded twice and so you can flag when it already exists:
   - **Inbox** (`docs/tasks_manager/_inbox/`) — other un-triaged ideas.
   - **Active tasks** (`docs/tasks_manager/_todos/`, status open/in_progress) — already on the backlog.
   - **Knowledge-base docs** — `docs/resources/CONTEXT.md`, area summaries under
     `docs/resources/<area>/summary.md`, dependency graphs under
     `docs/resources/<area>/dependency-graph.md`, feature contracts under
     `docs/resources/<area>/contracts/*.md`, and component contexts under
     `docs/resources/<area>/components/*/CONTEXT.md` (plus `CONTEXT_DOCS_DIR` only if configured).
     These describe what already *exists*, so a match here means the idea may already be built.

   Compare by meaning, not exact words — scan titles/headings first, then read the bodies of plausible
   hits. If nothing plausibly matches, say nothing and continue to step 3 — don't interrupt capture with
   a "no duplicates found" message.

   When there **is** a plausible match, stop and show it, then let the user decide:
   - **Same thing** → don't create a new file. If the match is an inbox idea, append the new detail to
     its body and bump `Captured`'s companion note (e.g. add an "updated" line). If the match is a task,
     append the detail to the task and tell the user it's already tracked by its task ID
     (for example `AUTH-001` or `T-001`). If it's already described in the knowledge base, tell the
     user it appears to already exist and cite the relevant doc.
   - **Different thing** → proceed to create a new idea (steps 3–5).

3. **Reserve the Inbox ID.** Run `scripts/reserve-work-item.sh inbox <short-desc>` and use the path it
   prints. The helper creates the placeholder atomically so parallel agents cannot claim the same
   `I-NNN`.

4. **Best-guess the area.** Glance at `docs/tasks_manager/_areas.md` and pick the slug that fits. If nothing fits,
   use `global` - do **not** stop to define a new area here; that's triage's job. A wrong guess is cheap.

5. **Fill the reserved file** using the inbox format: a tiny header
   (`Inbox ID`, `Captured` = now in ISO 8601, `Area`, `Status: new`) and one or two sentences of the
   idea in the user's own framing.

6. **Confirm in one line.** e.g. "Captured as I-007 (area: ui)." Then stop. If the user immediately
   adds detail, append it; otherwise you're done.

## Capturing several at once

If the user dumps multiple ideas in one message, create one file per idea with consecutive IDs. Keep
each atomic — one idea per file — so triage can promote or drop them independently.

## Quality bar

- The file passes the `block-bad-todo-name.sh` naming check (`I-NNN_<lowercase-hyphenated>.md`).
- A quick duplicate scan ran; the user was interrupted only on a genuine, plausible match.
- Capture took no unnecessary questions.
- The idea text is enough to remember the intent at triage time — not a spec.
- `Status` is `new`; the file is in `docs/tasks_manager/_inbox/` (not archived).
