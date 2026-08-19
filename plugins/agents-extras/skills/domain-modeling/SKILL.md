---
name: domain-modeling
description: "Build and sharpen the project's domain model: challenge terms against the glossary, stress-test with edge-case scenarios, and update docs/resources/CONTEXT.md and ADRs inline. Use when discussing codebase terminology, writing or editing a CONTEXT.md, or recording an ADR."
metadata:
  source:
    - "github.com/mattpocock/skills@885e2ca skills/engineering/domain-modeling/SKILL.md (adapted)"
    - playbooks/skills/engineering/grill-with-docs.md
  pack: architecture
---

# Domain Modeling

Actively build and sharpen the project's domain model as you design: challenge terms, invent
edge-case scenarios, and write the glossary and the decisions down the moment they crystallise.
Merely *reading* `docs/resources/CONTEXT.md` for vocabulary is not this skill — that is a habit any
skill can have. This skill is for when you are *changing* the model, not just consuming it.

## Where the docs live

Before changing anything, find what already exists:

### The glossary

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
when the first term is resolved (use the standard `docs/resources/CONTEXT.md` structure — see the
`knowledge-base` skill). If root `CONTEXT.md` is missing, create the small pointer from the standard
CONTEXT.md pointer template. If no
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
them as they happen. Use the format in [CONTEXT-FORMAT.md](references/CONTEXT-FORMAT.md).

`docs/resources/CONTEXT.md` should be totally devoid of implementation details. Do not treat it as a
spec, a scratch pad, or a repository for implementation decisions. It is a glossary and nothing else.

### Offer ADRs sparingly

Only offer to create an ADR when all three are true:

1. **Hard to reverse** — the cost of changing your mind later is meaningful
2. **Surprising without context** — a future reader will wonder "why did they do it this way?"
3. **The result of a real trade-off** — there were genuine alternatives and you picked one for specific reasons

If any of the three is missing, skip the ADR. Follow the format in the `knowledge-base` skill (references/adr-convention.md) — see also the bundled [ADR-FORMAT.md](references/ADR-FORMAT.md).
