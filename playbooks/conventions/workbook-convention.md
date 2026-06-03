# Workbook Convention

## Purpose

`workbooks/` is the root-level home for workbook bundles: repeatable, project-owned working sets that
combine instructions with the scripts, data, assets, templates, examples, outputs, or support files
needed to run one workflow.

Use a workbook when a body of work needs more than a durable Markdown note but should stay packaged,
reviewable, and reusable inside the repository.

## Layout

The canonical path is:

```text
workbooks/<workbook-slug>/
```

Nested workbook collections are allowed when they make ownership or navigation clearer:

```text
workbooks/<collection>/<workbook-slug>/
```

Each workbook is a separate folder. Keep everything needed for that workbook inside the folder unless
it is intentionally shared with another workbook. Workbook-local files may include:

- `README.md`
- scripts
- data
- assets
- templates
- examples
- outputs
- support files

If a workbook reuses another workbook, declare the relationship in its `README.md` rather than copying
shared files silently.

## README Shape

Every workbook folder starts with a `README.md` using at least these sections:

```markdown
# <Workbook name>

## Purpose

What this workbook is for, who uses it, and what outcome it produces.

## Depends on

- `workbooks/<other-workbook>/`

Use `None` when the workbook is self-contained.

## Contents

- `script-or-folder` - what it does.

## How to run/use

Commands, prerequisites, expected inputs, expected outputs, and any cleanup notes.
```

Dependencies should be repo-relative paths to other workbook folders. If a dependency is external, name
the tool, service, dataset, or document explicitly and include setup notes under `How to run/use`.

## Relationship to Resources

Keep these lanes distinct:

- `docs/tasks_manager/_inbox/` is for raw ideas and work items.
- `docs/resources/_inbox/` is for raw uploaded knowledge files awaiting distillation; related files
  from one source event may be grouped in a batch folder with a `README.md` manifest.
- `docs/resources/_digests/` is for curated Markdown summaries extracted from raw sources.
- `docs/resources/<area>/sources.md` is for area source history: why a source was added, where it is
  stored, and which digests, tasks, or canonical docs depend on it.
- `docs/resources/<area>/attachments/` is for long-lived committed source documents and binaries such
  as `.docx`, PDFs, spreadsheets, diagrams, and similar durable project resources.
- `workbooks/` is for reusable working bundles that may contain scripts, data, generated outputs, or
  support assets for a concrete workflow.

Do not use `docs/resources/_inbox/` as a permanent home for authoritative binaries. If a source
document needs to be committed for long-term reference, move it under
`docs/resources/<area>/attachments/` and add nearby Markdown metadata or an index documenting purpose,
provenance, area or owner, and update guidance.

## Git Hygiene

Commit workbook files only when they are reusable and appropriate for the repository. Keep secrets,
private local paths, customer-specific values, very large generated outputs, and scratch files out of
committed workbooks unless the project has an explicit policy allowing them.
