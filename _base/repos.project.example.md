# Repository Registry

Copy this scaffold to `.config/repos.project.md` and then let the downstream project own that file.
Keep repo slugs stable because tasks and cross-repo docs use them as durable names.

Allowed values:

- `Repo`: lowercase slug matching `^[a-z][a-z0-9-]*$`
- `Required`: `yes` or `no`
- branch fields: branch name, `N/A`, or `unknown`
- `Work mode`: `default-branch`, `task-branch`, `same-branch`, `read-only`, or `ask`
- `Areas`: comma-separated area slugs or `N/A`

| Repo | Required | Role | Default branch | Integration branch | Work mode | Areas | Notes |
|------|----------|------|----------------|--------------------|-----------|-------|-------|
| project-template | yes | Agent template | main | main | default-branch | global | Work directly on main |
| naeural-core | no | Example product repo | unknown | unknown | ask | N/A | Replace or remove this example row |
