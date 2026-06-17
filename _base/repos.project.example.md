# Repository Registry

Copy this scaffold to `.config/repos.project.md` and then let the downstream project own that file.
Keep repo slugs stable because tasks and cross-repo docs use them as durable names.

Allowed values:

- `Repo`: lowercase slug matching `^[a-z][a-z0-9-]*$`
- `Required`: `yes` or `no`
- branch fields: branch name, `N/A`, or `unknown`
- `Work mode`: `default-branch`, `task-branch`, `same-branch`, `read-only`, or `ask`
- `Autonomy max`: optional permission ceiling, one of `L0`, `L1`, `L2`, or `L3`; omit the column in
  older registries to keep the default `L1`
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

Autonomy levels are defined in `playbooks/conventions/autonomy-levels.md`. Existing 8-column
registries remain valid and default to `L1`. Do not migrate downstream-owned `.config/repos.project.md`
files automatically during a template merge; ask whether the project wants to adopt the new column.

| Repo | Required | Role | Default branch | Integration branch | Work mode | Autonomy max | Areas | Notes |
|------|----------|------|----------------|--------------------|-----------|--------------|-------|-------|
| project-template | yes | Agent template | master | master | default-branch | L1 | global | Work directly on default branch |
| naeural-core | no | Example product repo | unknown | unknown | ask | L1 | N/A | Replace or remove this example row |
