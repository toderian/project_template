# Grill With Docs

## Purpose

Extended grilling session that stress-tests a plan against the project's existing domain model and
recorded decisions. Sharpens terminology and updates documentation (`docs/resources/CONTEXT.md`, ADRs)
inline as decisions crystallise.

Use this instead of plain `grill-me` when the project already has — or is starting to grow — a domain glossary and an ADR log. If the project has neither yet, plain `grill-me` is fine; this skill is what graduates a project from "we have a plan" to "we have a plan _and_ the language to keep talking about it precisely."

## The interview

Interview the user relentlessly about every aspect of the plan until you reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask the questions one at a time, waiting for feedback on each question before continuing.

If a question can be answered by exploring the codebase, explore the codebase instead.

## Domain awareness

During codebase exploration, also look for existing documentation:

### Where the glossary lives

In template-inherited repos, the primary glossary lives at `docs/resources/CONTEXT.md`. A root
`CONTEXT.md` is only a pointer for quick discovery and legacy tooling. If you find an older substantive
root glossary, treat it as fallback evidence and prefer moving future edits to `docs/resources/`.

Read `CONTEXT_DOCS_DIR` from `project.env` at the repo root and follow it silently. This setting is an
external-storage escape hatch for a repo you should not write into; it is not the normal default:

- **Unset (normal):** read and update `docs/resources/CONTEXT.md`.
- **Set to a directory:** read and update `$CONTEXT_DOCS_DIR/<source-repo>/CONTEXT.md`, namespaced by
  source repo. Record the origin in the file header (`> Domain glossary for {repo}`) because the
  location no longer identifies the source by itself.

### File structure

Most repos have a single context:

```
/
├── docs/
│   ├── resources/
│   │   └── CONTEXT.md
│   └── adr/
│       ├── 0001-event-sourced-orders.md
│       └── 0002-postgres-for-write-model.md
├── CONTEXT.md          # pointer to docs/resources/CONTEXT.md
└── src/
```

If `docs/resources/CONTEXT-MAP.md` exists, the repo has multiple contexts. The map points to where each
one lives:

```
/
├── docs/
│   ├── resources/
│   │   ├── CONTEXT-MAP.md
│   │   ├── ordering/
│   │   │   └── CONTEXT.md
│   │   └── billing/
│   │       └── CONTEXT.md
│   └── adr/                          # system-wide decisions
├── src/
│   ├── ordering/
│   │   └── docs/adr/                 # context-specific decisions
│   └── billing/
│       └── docs/adr/
└── CONTEXT.md                        # pointer
```

Create files lazily - only when you have something to write. If no primary glossary exists, create it
when the first term is resolved (use `_base/docs/resources/CONTEXT.md` as the starting structure). If
root `CONTEXT.md` is missing, create the small pointer from `_base/CONTEXT.md.template`. If no
`docs/adr/` exists, create it when the first ADR is needed.

## During the session

### Challenge against the glossary

When the user uses a term that conflicts with the existing language in `docs/resources/CONTEXT.md`,
call it out immediately. "Your glossary defines 'cancellation' as X, but you seem to mean Y - which is
it?"

### Sharpen fuzzy language

When the user uses vague or overloaded terms, propose a precise canonical term. "You're saying 'account' — do you mean the Customer or the User? Those are different things."

### Discuss concrete scenarios

When domain relationships are being discussed, stress-test them with specific scenarios. Invent scenarios that probe edge cases and force the user to be precise about the boundaries between concepts.

### Cross-reference with code

When the user states how something works, check whether the code agrees. If you find a contradiction, surface it: "Your code cancels entire Orders, but you just said partial cancellation is possible — which is right?"

### Update CONTEXT.md inline

When a term is resolved, update `docs/resources/CONTEXT.md` right there. Don't batch these up - capture
them as they happen. Use the format in [CONTEXT-FORMAT.md](grill-with-docs/CONTEXT-FORMAT.md).

`docs/resources/CONTEXT.md` should be totally devoid of implementation details. Do not treat it as a
spec, a scratch pad, or a repository for implementation decisions. It is a glossary and nothing else.

### Offer ADRs sparingly

Only offer to create an ADR when all three are true:

1. **Hard to reverse** — the cost of changing your mind later is meaningful
2. **Surprising without context** — a future reader will wonder "why did they do it this way?"
3. **The result of a real trade-off** — there were genuine alternatives and you picked one for specific reasons

If any of the three is missing, skip the ADR. Follow the format in [`playbooks/conventions/adr-convention.md`](../../conventions/adr-convention.md) (the bundled [ADR-FORMAT.md](grill-with-docs/ADR-FORMAT.md) now points there).

## Convergence

Stop grilling when:

- all the main branches of the plan have been walked
- no question generates new information or changes a prior answer
- the user says they are satisfied

Then produce a brief summary:

- **Decisions made** — concrete answers that were locked in
- **Glossary changes** — terms added to or sharpened in `docs/resources/CONTEXT.md`
- **ADRs created** — new files under `docs/adr/`
- **Open questions** — anything that was deferred or unresolved
- **Risks identified** — concerns that surfaced during grilling
