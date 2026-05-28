# Generated Artifacts Convention

## Purpose

Agents create two different kinds of files:

- stable project artifacts that humans and workflows link to by ID, slug, or canonical path
- rerunnable observation artifacts such as reports, audits, inventories, and snapshots

Do not use one naming rule for both. Stable artifacts keep stable names. Rerunnable reports get a new
timestamped filename for every run so repeated use does not overwrite or obscure previous evidence.

## Stable artifacts

Do not add timestamps to filenames for stable artifacts whose identity is already carried by an ID,
slug, or canonical path. Store creation/update times in metadata or an execution log instead.

Examples:

- inbox ideas: `docs/tasks_manager/_inbox/I-NNN_<short-description>.md`
- task files: `docs/tasks_manager/_todos/<PREFIX>-NNN-<TYPE>_<short-description>.md`
- durable plans: `docs/_plans/<slug>.md`
- spec-workflow artifacts: `specs/<slug>/spec.md`, `design.md`, `tasks.md`, `review.md`
- durable knowledge docs: `docs/resources/CONTEXT.md`, `docs/resources/<area>/summary.md`,
  component contexts, dependency graphs, feature contracts, and sanitized operational runbooks under
  `docs/resources/<area>/runbooks/<scenario-slug>.md`

These files are meant to be referenced repeatedly. Timestamped names would make links brittle and make
routine updates harder to find.

## Rerunnable reports

Reports, audits, inventories, migration proposals, and other rerunnable observations must use a unique
timestamped filename. The default path shape is:

```text
docs/resources/_reports/<workflow>/<YYYY-MM-DDTHHMMSS+ZZZZ>_<report-slug>.md
```

Examples:

```text
docs/resources/_reports/tidy-repo/2026-05-28T153012+0300_tidy-report.md
docs/resources/_reports/audit-todos/2026-05-28T153012+0300_audit-todos-report.md
```

Use local time with timezone and no colon characters in the filename:

```bash
date +%Y-%m-%dT%H%M%S%z
```

If the exact path already exists because two runs started in the same second, append `-02`, `-03`, and
so on before the `.md` suffix until the path is unused, for example
`2026-05-28T153012+0300_tidy-report-02.md`. Never overwrite an older report.

## Delta section

When the workflow has prior reports in the same report directory, read the newest previous report and
include a delta section in the new report. Previous-report lookup must include collision-suffixed
variants such as `<timestamp>_<report-slug>-02.md`, not just the unsuffixed base name.

```markdown
## Delta since previous report

Previous report: docs/resources/_reports/<workflow>/<timestamp>_<report-slug>.md

- New findings: ...
- Resolved findings: ...
- Still present: ...
```

Use stable finding keys for the comparison: source file plus line/title for loose work, source path for
loose docs, file path for orphan candidates, task ID for task audits, and similar durable handles for
other report types. If no prior report exists, include:

```markdown
## Delta since previous report

No previous report found.
```

Do not replace timestamped reports with runbooks. A report records one run's observations; a runbook
records a stable procedure that can be run again with placeholders and local bindings.
