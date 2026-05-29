# Repository Registry

Copy this scaffold to `.config/repos.project.md` and then let the downstream project own that file.
Keep repo slugs stable because tasks and cross-repo docs use them as durable names.

Allowed values:

- `Repo`: lowercase slug matching `^[a-z][a-z0-9-]*$`
- `Required`: `yes` or `no`
- branch fields: branch name, `N/A`, or `unknown`
- `Work mode`: `default-branch`, `task-branch`, `same-branch`, `read-only`, or `ask`
- `Areas`: comma-separated area slugs or `N/A`

Work mode meaning:

- `default-branch`: work and commit directly on `Default branch`; ask if currently elsewhere.
- `same-branch`: stay on the current branch; do not create or switch branches.
- `task-branch`: use an explicitly named task branch; ask before creating or switching if none is
  specified.
- `read-only`: inspect only; do not edit or commit.
- `ask`: ask before edits or branch changes.

Template-inherited downstream repos should normally use `default-branch` or `same-branch`, not
per-task branching.

| Repo | Required | Role | Default branch | Integration branch | Work mode | Areas | Notes |
|------|----------|------|----------------|--------------------|-----------|-------|-------|
| project-template | yes | Agent template | master | master | default-branch | global | Work directly on default branch |
| naeural-core | no | Example product repo | unknown | unknown | ask | N/A | Replace or remove this example row |
