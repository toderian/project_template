# Design tree convention

`docs/resources/<area>/design/` is the source of truth for how a product works, how it is meant to
work, and why. Tasks change it; it does not track tasks. `at design check` enforces the rules marked
(checked) and `at design sync` writes the generated blocks.

## Layout

```text
docs/resources/<area>/design/
├── README.md                    # root index: purpose, path prefixes, modules
├── _crosscutting/               # facts several modules use (roles, shared conventions)
│   └── <subject>.md
└── <module>/
    ├── README.md                # purpose (five lines or fewer) and index; no feature facts
    ├── <leaf>.md                # one feature or mechanism
    ├── <leaf>.reference.md      # optional catalogue beside its leaf
    └── <submodule>/<leaf>.md    # optional; at most three folder levels (checked)
```

A file whose name starts with `_` holds notes about the tree and is not a leaf.

## Rules

1. **A leaf states what the code does now.** "Now" is the integration branch of the product
   repositories. Present tense, no version labels, no "target" sections.
2. **A change in progress lives in its task file.** The leaf lists it under Pending changes as a task
   ID and one line. The behaviour text is written into the leaf when the change merges.
3. **Status is one value for the whole leaf** (checked): `draft` (proposed), `accepted` (approved,
   not built), `implemented` (matches the code), `superseded` (replaced; link the replacement).
   `partially-implemented` is not used here. A feature that is designed but not built gets its own
   `accepted` leaf; it is never a section inside an `implemented` one.
4. **A fact has one owner file.** Other files link to it. A fact several modules use goes in
   `_crosscutting/`.
5. **Every leaf is reachable from an index** (checked): the nearest `README.md` above it links to it
   or carries the generated index block.
6. **Size** (checked): aim for 300 lines; a leaf over 500 fails. A catalogue (schema, endpoint list,
   key inventory) goes in a sibling `<leaf>.reference.md`, which has no size limit.
7. **Cite code by path and symbol,** with a line number only where the symbol is not enough. Declare
   path prefixes for each product repository once, in the root `README.md`, using the repo slugs from
   `.config/repos.project.md`. Never write an absolute checkout path.
8. **Relative links resolve** (checked).
9. **How-to steps go in `runbooks/`.** Verification matrices, rollout logs and test evidence stay in
   the task that produced them.
10. **Never state a secret value,** including a default or fallback one found in code. Name the
    constant and the file.

## Leaf shape

Frontmatter (checked: `summary`, `status`, and `verified.date` when the status is `implemented`):

```yaml
---
summary: one line, used by the folder index
status: implemented
code_paths:
  - <prefix>/path/or/glob
verified:
  <repo-slug>: <commit the text was checked against, or "not checked">
  date: YYYY-MM-DD
  method: how the text was checked against the code, and what was not checked
---
```

Sections, in this order; omit one that would be empty:

| Section | Content |
|---|---|
| Intent and why | The problem and the reason this exists. |
| Current behaviour | What it does, as numbered statements a reader can check. |
| Interfaces | Endpoints, records, events, configuration: what it exposes and depends on. |
| How it works | Mechanism, with links to code in place of restated code. |
| Constraints | Invariants, limits, compatibility promises. |
| Decisions | The table below. |
| Pending changes | Task ID, one-line summary. Pointers only. |
| Risks and open questions | Known gaps, debt, unanswered questions, text not yet verified. |

`assets/design-leaf.template.md` is a starter.

## Decisions table

The header is exactly this (checked):

```md
| ID | Date | Decision | Why | Source | Supersedes | Status |
```

| Column | Content |
|---|---|
| ID | `D-NN`, per file, never reused |
| Date | ISO date, or `not recorded`. Never guess a date. |
| Decision | One sentence |
| Why | The reason, naming the rejected alternative where one is known |
| Source | Task ID or `ADR-NNNN`; `not recorded` when neither exists |
| Supersedes | `D-NN` or a dash |
| Status | `active` or `superseded by D-NN` |

Rows are append-only. The only edit allowed to an old row is its Status cell. A new row that
supersedes an old one names it in Supersedes, and the old row's Status names the new one (checked,
both directions). A decision that spans several leaves, or needs more than a row, is an ADR in
`docs/adr/` (`adr-convention.md`); the row points at it.

## How a task changes the tree

1. The task names the leaves or module it will change in its `Spec refs` row. A design path that
   does not exist fails the check.
2. While the task is open, each named leaf lists it under Pending changes. The check warns when a
   named leaf does not, and when Pending changes names a closed task.
3. When the change merges to the integration branch, the task rewrites the affected sections in
   place, adds a Decisions row if a decision changed, updates `verified`, and removes its Pending
   changes line.
4. The task's `Resource updates` closeout row names the leaves it changed.

A change to behaviour with no leaf change is a review finding: either the leaf was already wrong, or
it is wrong now.

## Variants of the leaf shape

- **A design that is not built** (`accepted` or `draft`). Sections: Intent and why, the decisions
  already taken, how it differs from what the code does today, and where the detail is (a task, an
  ADR or a spec). No Current behaviour section. Keep it under about 100 lines.
- **A UX leaf.** Current behaviour is a list of rules. Each rule has an identifier and these lines:
  Rule, Why, Do, Don't, Check (a yes or no question answerable from a diff or a screenshot), Holds
  (`yes`, `partly` or `target`, with a count or an example), Source. A `target` rule is one the code
  does not follow yet; it needs the owner's decision before a screen is held to it.
- **A UI token leaf** (colour, typography, spacing). One row per token: name, role, must not be used
  for, implemented in (file and selector), why, source. No value column: a token can have one value
  per theme, and the code holds them.
- **A reference file** holds a catalogue only. It has frontmatter with `summary` and no fixed
  sections.

UI and UX rules that every screen follows live in the module of the application that renders them
(`<app>/ui/`, `<app>/ux/`). A feature's own screens are described in the feature's module and cite
those rules.

## Generated blocks

`at design sync` rewrites the text between these marker pairs in a `README.md`; `at design check`
fails when a block is stale. A `README.md` without the index markers must link to every leaf it owns
by hand.

```md
<!-- BEGIN generated-design-index -->
<!-- END generated-design-index -->

<!-- BEGIN generated-design-tasks -->
<!-- END generated-design-tasks -->
```

- **Index:** one row per leaf in the folder (summary and status from frontmatter), one row per
  subfolder that has its own `README.md` (first sentence and leaf counts), and the leaves of
  subfolders that have none.
- **Tasks:** the open tasks whose `Spec refs` name this folder or a file under it.

## Relation to the other knowledge-base homes

| Content | Home |
|---|---|
| How a feature works, and why | a design leaf |
| An agreement between repositories that is not one feature's behaviour (a wire format, a version promise) | `contracts/<feature-slug>.md`, linked from the leaves that rely on it |
| A hard-to-reverse decision across modules | `docs/adr/`, with a Decisions row pointing at it |
| A procedure | `runbooks/` |
| Area responsibilities and entry points | `summary.md`, which links to `design/README.md` |

A repository that adopts a design tree converts its feature contracts into leaves and replaces each
converted contract with a short pointer to the leaves that hold its content.
