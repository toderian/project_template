# <Project Name> - Domain Language

> **This is a downstream-owned file.** Seeded by `/init` at `docs/resources/CONTEXT.md`; fill in the
> project's domain language as it crystallises. `grill-with-docs` reads and updates this file inline.

> Some templates also describe themselves; this one shows the structure. Replace the placeholders with
> real terms; delete the explanatory blockquotes once you have filled in your first few entries.

One or two sentences describing what this context is and why it exists. If the project has a single
bounded context, keep the primary glossary here. If it has multiple bounded contexts, see
"Multi-context repos" below.

---

## Language

> The vocabulary unique to this project. Define what each term IS, not what it does. Be opinionated
> about the canonical name; list aliases under `_Avoid_` so the team and the agent stop using them.

**<Canonical Term>**:
One-sentence definition of what this concept is in the project domain.
_Avoid_: <ambiguous synonym>, <legacy name>.

**<Related Term>**:
One-sentence definition of a related concept, especially where teams often blur the boundary.
_Avoid_: <overloaded word>.

**<Actor or Owner Term>**:
One-sentence definition of the person, system, team, or role that owns or triggers the concept.
_Avoid_: <imprecise role name>.

(Add more terms below as they crystallise. `grill-with-docs` writes here when domain words come up
during planning.)

---

## Relationships

> How the terms connect, with cardinality where it is not obvious. Useful for ruling out
> misunderstandings ("wait, does one thing produce one related thing or many?").

- A **<Canonical Term>** produces one or more **<Related Terms>**
- A **<Related Term>** belongs to exactly one **<Actor or Owner Term>**
- A **<Actor or Owner Term>** may own many **<Canonical Terms>**

---

## Example dialogue

> A short, realistic conversation between two team members, or a dev and a domain expert, that
> demonstrates how the terms interact. This catches subtle boundary errors that flat definitions miss.

> **Dev:** "When a **<Actor or Owner Term>** creates a **<Canonical Term>**, do we create the
> **<Related Term>** immediately?"
>
> **Domain expert:** "No; the **<Related Term>** is only created once the **<Canonical Term>** reaches
> the agreed lifecycle state."

---

## Flagged ambiguities

> Words the team used to mean multiple things, with the resolution. Keeps the team from re-litigating
> the same overloaded term every quarter.

- "<overloaded word>" was used to mean both **<Canonical Term>** and **<Related Term>**; resolved:
  these are distinct concepts.

---

## Multi-context repos

Most projects have a single context: one primary glossary at `docs/resources/CONTEXT.md`.

If the project has multiple bounded contexts, create `docs/resources/CONTEXT-MAP.md` that lists the
contexts and how they relate. Put per-context glossaries under `docs/resources/<context>/CONTEXT.md`.
Keep root `CONTEXT.md` as a pointer, not the primary map or glossary.

See `playbooks/skills/engineering/grill-with-docs/CONTEXT-FORMAT.md` for the exact layout.

---

## How agents should use this file

- The `grill-with-docs` skill reads this file before stress-testing a plan, and writes back to it inline
  when new terms are resolved.
- The `diagnose`, `zoom-out`, and `refresh-context` skills consult it to use the project's canonical
  vocabulary when describing code.
- Updates to this file are appropriate any time a domain term is sharpened, an ambiguity is resolved,
  or a new bounded concept emerges. Implementation details, library names, framework choices, and
  component boundaries do **not** belong here.
- This file is **downstream-owned**: each project maintains its own. The template seed at
  `_base/docs/resources/CONTEXT.md` is upstream-owned and updated cleanly via
  `git fetch template && git merge`.
