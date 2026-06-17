# Workbooks

This root folder is the canonical home for workbook bundles.

Each workbook lives in its own folder and contains everything needed for that workbook. Human-runnable
workbooks default to this organization:

```text
workbooks/<workbook-slug>/
├── README.md
├── scripts/              # runnable entrypoints with descriptive filenames
├── configs/              # optional; safe sample/default config only
├── samples/              # optional; safe sample inputs or tiny fixtures
├── outputs/              # optional; documented example output or generated-output notes
└── support/              # optional; workbook-local helper modules/assets
```

Do not create empty folders just to match the shape. Workbooks may be nested into collections when
that makes ownership or navigation clearer.

Every workbook `README.md` should include:

## Purpose

What the workbook is for and what outcome it produces.

## Depends on

List repo-relative paths to other workbook folders this workbook reuses, or `None`.

## Contents

List important scripts, configs, samples, outputs, and support files and what each one is for.

## How to run/use

Document commands, prerequisites, arguments or config files, expected inputs, expected outputs, success
criteria, and cleanup notes.

## Methodology

Document the human-readable method, assumptions, validation approach, and known limitations.

Scripts should be human-runnable without replaying the agent transcript: use descriptive filenames,
state the working directory, document arguments and config, avoid private local paths and secrets, and
keep persistent Python tooling dependencies in `tools/python/` with `uv`.

Raw knowledge uploads awaiting distillation belong in `docs/resources/_inbox/`, not here. Long-lived
committed source documents and binaries belong under `docs/resources/<area>/attachments/` with nearby
Markdown metadata or an index documenting purpose, provenance, area or owner, and update guidance.
Large, external, generated, encrypted, or reproducible artifacts produced by a workbook should be
registered in `artifacts/README.md`.

See `playbooks/conventions/workbook-convention.md` for the full convention.
