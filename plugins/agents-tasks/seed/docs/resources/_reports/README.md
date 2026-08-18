# Reports

This directory stores rerunnable agent-generated reports, audits, inventories, and migration
proposals. Each workflow should write under its own subdirectory:

```text
docs/resources/_reports/<workflow>/<YYYY-MM-DDTHHMMSS+ZZZZ>_<report-slug>.md
```

Reports are snapshots of what the agent observed at a point in time. Do not overwrite an older report;
create a new timestamped file and include a delta from the previous report when the workflow supports
it.

Stable project docs, task files, inbox ideas, plans, and specs do not belong here.
Reusable operational procedures belong in `docs/resources/<area>/runbooks/`; reports may be linked as
evidence, but raw output should not be pasted into runbooks.
