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
- `scripts/` for human-runnable entrypoints
- `configs/` for checked-in safe default or sample configuration
- `samples/` or `examples/` for safe sample inputs and small fixtures
- `data/`, `assets/`, or `templates/` when the workflow needs committed inputs
- `outputs/` for documented example outputs or a README describing generated outputs
- `support/` for workbook-local helper code or reusable support files

If a workbook reuses another workbook, declare the relationship in its `README.md` rather than copying
shared files silently.

## Default Organization

New workbooks that capture an executable workflow should default to this shape:

```text
workbooks/<workbook-slug>/
├── README.md
├── scripts/
│   └── <verb>-<object>.<ext>
├── configs/              # optional; safe sample/default config only
├── samples/              # optional; safe sample inputs or tiny fixtures
├── outputs/              # optional; documented example output or generated-output notes
└── support/              # optional; workbook-local helper modules/assets
```

Do not create empty folders just to match the shape. If the workflow has no runnable entrypoint,
explain why in the `README.md`; otherwise put entrypoints under `scripts/` rather than burying them in
the README as long inline snippets.

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

- `scripts/<entrypoint>` - what it runs.
- `configs/<file>` - what settings it controls, when present.
- `samples/<file>` - what safe input it demonstrates, when present.
- `outputs/` - what the workflow writes or where generated outputs should be stored, when present.

## How to run/use

Commands, prerequisites, expected inputs, expected outputs, and any cleanup notes.

## Methodology

The human-readable method, assumptions, validation approach, and known limitations.
```

Dependencies should be repo-relative paths to other workbook folders. If a dependency is external, name
the tool, service, dataset, or document explicitly and include setup notes under `How to run/use`.

## Script Expectations

Workbook scripts should be useful to a human without replaying the original agent transcript:

- Use descriptive filenames, usually verb-object names such as `prepare-dataset.py`,
  `run-evaluation.sh`, or `summarize-results.ts`.
- Document the command from the repo root or the exact working directory required to run it.
- Document every required argument, environment variable, config file, and input path.
- State expected outputs, output paths, success criteria, and cleanup commands.
- Keep private local paths, customer-specific values, credentials, tokens, and secrets out of scripts,
  configs, samples, output examples, and README prose.
- Use small, safe sample inputs when an example makes the workflow easier to verify.
- Put persistent repo-level Python tooling dependencies in `tools/python/` with `uv`; do not hide
  dependency setup inside untracked virtual environments or ad hoc `pip install` steps.
- Capture the methodology and validation approach in the workbook `README.md`, not only in code
  comments.

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

If a workbook produces large, external, generated, encrypted, or reproducible artifacts that should not
live directly in Git, register them in `artifacts/README.md` and keep only the runnable workflow,
metadata, safe samples, and output documentation in the workbook.
