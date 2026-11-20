---
name: design-doc
description: "Write, refresh, split or convert design leaves under docs/resources/<area>/design/: the source of truth for how a feature works and why, with its decisions and the tasks that made them. Use when the user says \"design doc\", \"document how this feature works\", \"update the design\", \"add a design leaf\", \"start a design tree\", wants existing specs or contracts converted into a design tree, or when a task changed behaviour that a leaf describes."
argument-hint: "Which feature, leaf or module?"
metadata:
  pack: docs-knowledge
---

# Design Doc

## Purpose

Keep `docs/resources/<area>/design/` true: each leaf states what the code does now, why, and which
task or decision made it so. A leaf that is wrong is worse than a missing one, because agents plan
from it.

The format (layout, frontmatter, sections, Decisions table, leaf variants, generated blocks) is owned
by `agents-tasks:knowledge-base`: `references/design-convention.md`, with the starter
`assets/design-leaf.template.md`. Read the convention before writing; this skill is the procedure
only.

## Pick the job

| Situation | Go to |
|---|---|
| A feature has no leaf | Write a leaf |
| A task changed behaviour a leaf describes | Refresh a leaf |
| A leaf is over 500 lines or covers two features | Split a leaf |
| The area has no design tree, or has specs and contracts to convert | [references/converting.md](references/converting.md) |

Do not write a leaf for a single small function or for a procedure (that is a runbook).

## Write a leaf

1. **Place it.** Read `design/README.md` and the module `README.md`. Pick the module that owns the
   code. A fact several modules need goes in `_crosscutting/`. Search the tree for the subject first:
   a fact has one owner file, so extend the owner or link to it.
2. **Read the code before writing.** Entry points, the public surface, what it stores, its limits and
   defaults, its error answers, its tests. For a feature that spans repositories, read each side on
   its integration branch and note the commit.
3. **Write Current behaviour as numbered statements a reader can check.** Each one names a value, a
   condition or an answer. "Validates the input" is not checkable; "refuses a name over 120
   characters with `invalid_name`" is.
4. **Recover the decisions.** Search task files, ADRs and commit messages for why each non-obvious
   rule exists. Write one row per decision. Where no source records the date or the reason, write
   `not recorded`; never infer one.
5. **Fill `verified` honestly:** the commit per repository, the date, and the method, including what
   you did not check. Put each unchecked statement under Risks and open questions.
6. **Record what you found wrong.** Behaviour that contradicts an earlier document, an ADR or a
   test goes under Risks and open questions with the path. Do not fix code here; propose a task.
7. Omit a section that would be empty.

A feature that is approved but not built gets the short `accepted` variant and no Current behaviour
section. Never describe unbuilt behaviour in an `implemented` leaf.

## Refresh a leaf

Run this when a task that names the leaf in `Spec refs` merges, or when the leaf is found stale.

1. Diff the code since the commit in `verified` for the paths in `code_paths`.
2. Rewrite the affected statements in place, in the present tense. Delete what is no longer true; do
   not keep it as history. Git holds the earlier text.
3. If a decision changed, append a Decisions row with the task ID as Source. If it replaces an
   earlier row, name that row in Supersedes and set the old row's Status to `superseded by D-NN`.
   Edit nothing else in an old row.
4. Remove the task's line from Pending changes. Update `verified`.
5. Name the leaf in the task's `Resource updates` closeout row.

When a task starts and names a leaf, add its ID and one line to Pending changes; that is the only
edit an unmerged change makes to a leaf.

## Split a leaf

1. Find the seam: two features, or a feature and a catalogue. A catalogue moves to
   `<leaf>.reference.md`.
2. Each statement and each Decisions row moves to exactly one file. A moved decision keeps its text
   and date and gets a new ID in the new file; note the old ID in its Why cell.
3. Replace moved text with a link. Fix every link that pointed at a moved heading: search the tree,
   the open task files and `AGENTS.md` for the old path.

## Finish

```bash
at design sync      # rewrites the generated index and open-task blocks
at design check     # fails on a broken link, a bad Decisions table, an unindexed or oversized leaf
```

Fix every error. Report each warning or fix it. Then report: the leaves written or changed, what was
verified against code and at which commit, what was not, and the defects or open questions found.

## Quality bar

- Every statement in Current behaviour was read in code at the commit in `verified`, or is listed as
  unchecked.
- No version labels, no "target" sections, no unbuilt behaviour in an `implemented` leaf.
- No fact is stated in two files.
- No date, reason or task ID is guessed.
- No secret value appears, including a default one from code.
- `at design check` passes.
