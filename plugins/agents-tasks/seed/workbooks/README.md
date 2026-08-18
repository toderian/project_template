# Workbooks

This root folder is the canonical home for workbook bundles: reusable workflow packages with their
scripts, configs, sample inputs, support files, methodology notes, and documented outputs.

Each workbook lives in its own folder and contains everything needed to rerun it:

```text
workbooks/<workbook-slug>/
├── README.md
├── scripts/              # runnable entrypoints with descriptive filenames
├── configs/              # optional; safe sample/default config only
├── samples/              # optional; safe sample inputs or tiny fixtures
├── prompts/              # optional; prompt templates or prompt notes meant to be committed
├── schemas/              # optional; machine-readable input/output/state contracts
├── evals/                # optional; evaluation fixtures, graders, or expected judgments
├── traces/README.md      # optional; trace location, retention, and redaction notes
├── outputs/              # optional; documented example output or generated-output notes
└── support/              # optional; workbook-local helper modules/assets
```

Do not create empty folders just to match the shape. Workbooks may be nested into collections when
that makes ownership or navigation clearer.

Every workbook `README.md` covers: **Purpose** (what it produces), **Depends on** (repo-relative paths
to reused workbook folders, or `None`), **Contents** (each script, config, sample, and support file),
**How to run/use** (commands, prerequisites, arguments, expected inputs and outputs, success criteria,
cleanup), and **Methodology** (the human-readable method, assumptions, validation, known limitations).

Scripts must be human-runnable without replaying the agent transcript: descriptive filenames, a stated
working directory, documented arguments and config, no private local paths or secrets, and persistent
Python dependencies kept in `tools/python/` with `uv`.

Where things go instead of here:

- Raw knowledge uploads awaiting distillation → `docs/resources/_inbox/`.
- Long-lived committed source documents and binaries → `docs/resources/<area>/attachments/` with
  nearby Markdown metadata or an index (purpose, provenance, area or owner, update guidance).
- Large, external, generated, encrypted, or reproducible outputs → registered in `artifacts/README.md`.

The full convention — when a workflow earns a workbook and how to structure one — lives in the
`workbook` skill.
