# Describe Component

## Purpose

Produce (or refresh) a `CONTEXT.md` for a single **system component** — a service, module, package, or
directory — that captures its *structure and boundaries*: what it's responsible for, how you call it,
what it depends on, what data it owns, the non-obvious rules, and how it's tested.

This is the **architectural** counterpart to the root `CONTEXT.md`, which is a *domain glossary*
(vocabulary, relationships). Keep the two distinct:

- **Root `CONTEXT.md`** (maintained by `grill-with-docs`) — what the words *mean* across the project.
- **Component `CONTEXT.md`** (this skill) — what *this part of the system* does and how it fits.

A component doc should **link** to domain terms in the root file, not redefine them. Duplicated
definitions drift; a cross-reference doesn't.

Use this when onboarding to or handing off a component, before refactoring something whose boundaries
are fuzzy, after building a new subsystem, or any time an agent keeps re-deriving the same "what does
this module even do" understanding. It's a one-click-deep orientation doc that saves that rediscovery.

## When NOT to use it

- For trivial components (a single small file) — a doc costs more than it saves.
- For domain vocabulary — that belongs in the root `CONTEXT.md` via `grill-with-docs`.
- For step-by-step how-tos or runbooks — this describes structure, not procedures.

## Process

### 1. Fix the component's scope

Confirm the path/boundary with the user (e.g. `src/auth/`, `services/billing/`, a package). A component
is a unit with a coherent responsibility and a callable surface — not "all the files I touched." If the
boundary is unclear, propose one and confirm before exploring.

### 2. Explore the code (don't guess)

Read the component before writing a word about it. For a larger component, dispatch an `Explore` agent;
for a small one, grep/read directly. Gather:

- **Entry points** — `main`/`index`/`__init__`, the public exports, route registrations, CLI commands.
- **Public interface** — the functions, classes, endpoints, or events other code is meant to call.
  Distinguish the intended surface from internal helpers.
- **Outbound dependencies** — what this component imports/calls (other components, libraries, services,
  env/config it reads).
- **Inbound dependencies** — who imports or calls *into* this component (grep for its module path /
  public symbols across the repo). This is what makes a change risky, so it's worth the search.
- **Data owned** — models, tables, schemas, caches, files, or in-memory state this component is the
  source of truth for. Note what it owns vs. merely reads.
- **Tests** — the test files that cover it, and roughly what they assert.

### 3. Surface the invariants and gotchas

These are the highest-value, least-recoverable parts — the things the code doesn't say out loud:
ordering requirements, concurrency assumptions, "never call X before Y," idempotency, migration
hazards, performance cliffs, security-sensitive paths. Read for them, and **ask the user** for the
tribal knowledge that isn't in the code. If you genuinely find none, say so rather than inventing them.

### 4. Reconcile with the domain glossary

If the component traffics in domain terms, link them to the root `CONTEXT.md` instead of redefining
them. If you hit a domain word that *should* be in the glossary but isn't, note it and suggest running
`grill-with-docs` — don't silently define it in the component doc.

### 5. Determine where to store it (per-repo rule)

Where the doc lives is a **per-repo rule, not a per-run question** — so the same repo always stores its
component docs the same way. The rule is the `CONTEXT_DOCS_DIR` setting in the repo's `project.env`:

- **Unset → co-located (the default):** write `<component-path>/CONTEXT.md`, next to the code. Best
  when you own the repo — most discoverable, easiest to keep current, and on Claude it doubles as
  per-directory context.
- **Set to a directory → write there instead.** Use this when component docs should be gathered in one
  place (`CONTEXT_DOCS_DIR=docs/context`) or — the important case — when the repo you're describing is
  template-inherited, vendored, or otherwise not yours to commit to. Pointing `CONTEXT_DOCS_DIR` at
  *your own* repo keeps the doc under your control instead of polluting someone else's tree.

Read `CONTEXT_DOCS_DIR` from `project.env` at the repo root and follow it silently — don't re-ask each
run. Only when the rule is **unset** may you confirm the co-located default and offer to record a
different choice into `project.env` (so it sticks for next time). Honor it thereafter.

**When the doc is stored away from the component** (any `CONTEXT_DOCS_DIR`), encode its origin so it
stays traceable: name the file to identify the source (e.g. `<source-repo>__<component>-CONTEXT.md`, or
nest under `$CONTEXT_DOCS_DIR/<source-repo>/<component>/CONTEXT.md`), and make sure the header records
the full source (`> Architectural context for {repo}:{path}`). Co-located docs don't need this — their
location says it. When stored externally, link domain terms to the domain glossary with a
repo-qualified reference. The glossary lives wherever `grill-with-docs` put it under the same rule: at
`$CONTEXT_DOCS_DIR/<source-repo>/CONTEXT.md` when the dir is set (co-located with these component docs),
or the source repo's root `CONTEXT.md` when it isn't.

### 6. Draft, confirm, write

Draft the sections (format below), show the user, fold in corrections, then write the file to the
location chosen in step 5.

## Format

```md
# {Component Name} — Component Context

> Architectural context for `{repo}:{path}` (include the repo when this doc lives outside that repo).
> Domain terms link to the root `CONTEXT.md`; this file owns structure, not vocabulary.

## Responsibility
{1–3 sentences: what this component is accountable for, and — just as useful — what it is deliberately
NOT responsible for.}

## Public interface
{The surface other code calls: key functions/classes/endpoints/events, with a one-line purpose each.
This is the contract; internal helpers don't belong here.}

## Key files / entry points
- `{path/to/file}` — {what it is / why you'd open it}

## Dependencies (in / out)
**Depends on:** {components, services, libraries, config this needs}
**Depended on by:** {who calls into this — the blast radius of a change}

## Data owned
{Models, tables, schemas, state this component is the source of truth for. Note owned vs. read-only.}

## Invariants & gotchas
- {Non-obvious constraint, ordering rule, concurrency assumption, hazard.}

## Tests
- `{path/to/test}` — {what it covers}

## Related domain terms
{Terms this component uses, linking to the root `CONTEXT.md` entries — e.g. **Order**, **Invoice**.
Do not redefine them here.}
```

Drop a section if it's genuinely empty (e.g. a stateless component has no "Data owned") rather than
padding it — but say nothing only when there's truly nothing.

## Keeping it current

A component doc describes structure, which evolves more slowly than domain vocabulary — but it does
evolve. When a refactor moves the boundary, changes the public interface, or adds a dependency, update
the doc in the same change. It's downstream-owned; treat a stale component CONTEXT.md as a bug.

## Quality bar

- Every claim is grounded in code you actually read, not inferred from names.
- The **public interface** and **Depended on by** sections are accurate — these are what make the doc
  worth trusting before a change.
- Invariants capture real, non-obvious constraints (or the doc honestly states there are none).
- Domain terms link to the root `CONTEXT.md`; nothing is redefined.
- A newcomer could read it in two minutes and know where to start and what not to break.
