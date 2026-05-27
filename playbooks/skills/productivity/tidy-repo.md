# Tidy Repo

## Purpose

Bring a messy downstream repo — one inherited from this template but since grown unruly — back into the
template's structure **without losing anything and without surprising the user**. The typical mess is
three piles: ad-hoc todos and `TODO:` notes scattered around, loose docs in the wrong places, and
orphan files nobody remembers. This skill inventories all three, proposes a destination for each, and
only moves things once the user approves.

The guiding principle is **non-destructive and reversible**. A repo with real history is not a
greenfield; a wrong move erodes trust faster than the mess ever cost. So the default is *propose, then
apply* — never sweep silently, and **never delete**. Orphan files are only ever *flagged* for the user
to rule on.

This skill orchestrates primitives that already exist rather than reinventing them:

- `/init` — ensures the canonical `docs/tasks_manager/`, `docs/areas/`, `docs/resources/`, and
  `docs/archive/` layout is present.
- the **inbox** (`playbooks/conventions/inbox-convention.md`) — the frictionless holding pen for
  anything that can't be classified confidently. Loose work becomes `I-NNN` ideas, not forced into
  full area-prefixed tasks.
- `/triage-inbox` — the deliberate pass that later promotes the worthwhile swept-in ideas into typed
  tasks. Tidy-repo deliberately stops *before* triage; sorting quality is triage's job, not the
  sweep's.
- `_base/scripts/sync-todo-ledgers.sh` — reconciles the ledgers after any file moves.

Read `playbooks/conventions/todo-convention.md` and `playbooks/conventions/inbox-convention.md` for the
target shapes.

## The three piles → where each lands

| Pile | What it looks like | Destination | Why |
|------|--------------------|-------------|-----|
| **Loose work** | ad-hoc `TODO.md`, `NOTES.md`, inline `TODO:`/`FIXME:` clusters, half-finished task files not matching `<PREFIX>-NNN` | `docs/tasks_manager/_inbox/` as `I-NNN` ideas | The inbox is the cheap, reversible capture layer. Re-triaging later beats importing low-quality work as first-class backlog. |
| **Loose docs** | design notes, stray READMEs, architecture scribbles, `*.md` outside `docs/` that explain *how the system works* | `docs/resources/` | That's the home `/init` seeds for durable project documentation. |
| **Orphans** | stale scripts, dead configs, abandoned scratch files, `*.bak`, commented-out experiments | **flagged list only** — never moved, never deleted | Only the user knows if these are truly dead. Surface them; let them decide. |

When a file is ambiguous (could be a doc or a note), prefer the inbox — it's the lower-commitment
destination and triage will sort it.

## Process

### Phase 0 — Ensure structure

Confirm `docs/tasks_manager/`, `docs/areas/`, `docs/resources/`, and `docs/archive/` exist. If not, run `/init` (or its playbook
`playbooks/skills/misc/init.md`) first. A tidy needs somewhere to tidy *into*. Never overwrite existing
ledgers, areas registry, or tasks.

### Phase 1 — Audit (read-only, always first)

Walk the repo and build an inventory. **Touch nothing in this phase** — it is pure observation, so the
user sees the full picture before any change is proposed.

Sources to sweep for the three piles:

- **Loose work** — `find` for `TODO.md`, `TODOS.md`, `NOTES.md`, `BACKLOG.md`, `ideas*.md`, scratch
  task files; grep the tree for `TODO:`/`FIXME:`/`XXX:`/`HACK:` comment clusters (group by file, don't
  list every line). Also any `docs/tasks_manager/_todos/*.md` that fail the naming convention.
- **Loose docs** — `*.md` and doc-like files living outside `docs/` (repo root, `notes/`, `wiki/`,
  scattered `design/` dirs), excluding `README.md`/`CHANGELOG.md`/`LICENSE`/`AGENTS.md`/`CLAUDE.md` at
  the root, which belong where they are.
- **Orphans** — files that match neither: `*.bak`, `*.old`, `*~`, `*.tmp`, scratch scripts, configs
  for tools no longer in the repo, anything in a `tmp/`/`scratch/`/`old/` directory.

Respect `.gitignore` and skip `.git/`, `node_modules/`, build output, and the like — you're tidying
tracked project content, not generated artifacts.

### Phase 2 — Migration report (propose, don't apply)

Write a migration report to `docs/resources/_tidy-report.md` (and summarize it in chat). The report is
the deliverable of a tidy run — a reviewable plan, not a fait accompli. Structure:

```markdown
# Tidy report — <date>

## Summary
N loose-work items -> inbox · M loose docs -> resources · K orphans flagged

## Loose work → inbox (proposed I-NNN)
| Source | Proposed | Area guess | Note |
|--------|----------|-----------|------|
| TODO.md:12 "wire up retry" | I-008_wire-up-retry.md | net | from root TODO.md |

## Loose docs -> docs/resources/ (proposed move)
| Source | Proposed destination |
|--------|---------------------|
| notes/auth-design.md | docs/resources/auth-design.md |

## Orphans — FLAGGED for your decision (no action taken)
| File | Why flagged | Suggested |
|------|-------------|-----------|
| deploy.old.sh | superseded by deploy.sh? | you decide: keep / delete / archive |
```

Compute proposed `I-NNN` ids from the real inbox counter (highest `I-NNN` across `_inbox/` +
`_inbox_archived/`, +1), assigning sequentially so the report's ids are the ones that will actually be
used. Best-guess `Area` from `docs/tasks_manager/_areas.md`; `global` is fine.

Then **stop and present the report.** Ask the user to approve as-is, edit, or skip categories. Do not
proceed to Phase 3 without an explicit go.

### Phase 3 — Apply (only after approval)

For the approved items:

- **Loose work → inbox.** Create each `docs/tasks_manager/_inbox/I-NNN_<short-desc>.md` per the inbox
  convention (one idea per file, `Captured` = now, `Status: new`, best-guess `Area`, one or two
  sentences from the source). Where the source was a file dedicated to TODOs (e.g. a root `TODO.md`),
  leave a one-line stub pointing at the inbox, or remove it if the user okayed that — your call follows
  their approval, not your own. For inline `TODO:` code comments, **capture the idea but leave the
  comment in place** unless the user says to strip it; rewriting source is beyond a tidy's remit.
- **Loose docs -> resources.** `git mv` each into `docs/resources/` (use `git mv` to preserve history).
  Fix obvious inbound links if cheap; otherwise note broken links in the report.
- **Orphans.** Do nothing. They stay flagged in the report. If the user explicitly rules on some,
  carry out only what they directed (and prefer moving to an `_archive/` over deleting).

After moves, run `_base/scripts/sync-todo-ledgers.sh` so the ledgers reflect reality.

### Phase 4 — Report and hand off to triage

Summarize what moved where, and how many orphans await the user's decision. End by pointing at the
natural next step: **`/triage-inbox`** to promote the freshly-swept ideas into typed area-prefixed
tasks. The sweep deliberately leaves them as raw `I-NNN` — tidy gets the mess into the right buckets; triage
decides what's worth doing.

## Quality bar

- Nothing was deleted; orphans were only flagged. The user explicitly approved every move that happened.
- Every swept idea is a well-formed `I-NNN` inbox file (passes `block-bad-todo-name.sh`) with a traceable
  note of where it came from.
- Loose docs moved with `git mv` (history preserved); the migration report records any links left dangling.
- The report (`docs/resources/_tidy-report.md`) is self-contained — a reader can see what was found,
  what moved, and what still needs a human decision.
- Ledgers are in sync (`_base/scripts/sync-todo-ledgers.sh` run after moves).
- A Codex agent (no hooks) following this playbook produces correctly-named `I-NNN` files and the same
  report — the rules here don't depend on the Claude-only hooks.
