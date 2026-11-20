# Starting or converting a design tree

Use this when an area has no `design/` tree, or has feature contracts, specs or long summaries that
should become one. Existing documents drift from the code in both directions: some describe what was
never built, some omit what was. Convert from the code, with the documents as a guide to intent.

## 1. Agree the modules

Propose a module list from the code layout and the existing documents, ten to twelve at most for a
large product, each with a one-line purpose. Get the owner's agreement before writing. File a task
for the conversion and work under it.

## 2. Map the code before writing

For each module, read the code on the integration branch and write a code map as a rerunnable report
under `docs/resources/_reports/<date>_design-tree-code-map/<module>.md`. For every section of every
existing document that belongs to the module, record one verdict:

| Verdict | Meaning |
|---|---|
| match | The code does what the section says. |
| stale | The code does something else; say what. |
| not built | Nothing in the code implements it. |
| removed | It existed and was deleted. |
| not checked | Not read; say why. |

Also list what the code does that no document mentions. One module per subagent works well; give
each the same brief and the commit to read.

## 3. Pilot one module

Write one module by hand first, the one with the most stacked versions or contradictions. Show the
owner the leaf shape before converting the rest. Record any variant the pilot needed in the
conversion task, so the remaining modules use it.

## 4. Write the remaining modules

Per module, follow "Write a leaf" in the skill. In addition:

- `match` sections become Current behaviour. `stale` sections are rewritten from the code, and the
  disagreement is noted under Risks and open questions.
- `not built` sections become a short `accepted` or `draft` leaf that points at the document holding
  the detail.
- `removed` and superseded text is dropped. Git keeps it.
- Stacked versions ("live v1, target v2") collapse to what the code does; the task that introduced
  each change becomes a Decisions row.
- Give every module `README.md` the generated index and open-task markers.

Then check a sample of specific statements (limits, defaults, constants, counts) against the code
yourself, across every module a subagent wrote, and report how many you checked.

## 5. Retire what was converted

Only after a whole module is converted:

1. Replace each fully covered document with a short pointer file: which leaves hold its content, and
   the commit where its earlier text can be read.
2. Leave a partly covered document in place and list, in the conversion task, what no leaf states
   yet.
3. Repoint `Spec refs` in open tasks from the old document to the leaf or module that replaced it.
4. Add an update note to any ADR the leaves found out of date. Do not rewrite an ADR.
5. Point the area `summary.md` and the repository `AGENTS.md` at `design/README.md` as the source
   of truth for behaviour.

## 6. Hand over the questions

Collect the entries under Risks and open questions across the tree into one list for the owner,
separating defects (propose a task for each) from decisions only the owner can make.
