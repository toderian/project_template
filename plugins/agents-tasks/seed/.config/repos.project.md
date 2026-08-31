# Repository Registry

The committed registry of repos this project works with. Agents read it before deciding where work
happens and how far it may go. Keep repo slugs stable — tasks and cross-repo docs use them as durable
names. Local checkout paths are machine-specific and belong in the ignored `.local/repos.map`, never
here.

Replace the example rows below with this project's real repos, then commit the file.

Allowed values:

- `Repo`: lowercase slug matching `^[a-z][a-z0-9-]*$`
- `Required`: `yes` or `no`
- branch fields: branch name, `N/A`, or `unknown`
- `Work mode`: `default-branch`, `task-branch`, `same-branch`, `read-only`, or `ask`
- `Autonomy max`: optional permission ceiling, one of `L0`, `L1`, `L2`, or `L3`; omit the column to
  keep the default `L1`
- `Areas`: comma-separated area slugs or `N/A`

Work mode meaning:

- `default-branch`: work and commit directly on `Default branch`; ask if currently elsewhere.
- `same-branch`: stay on the current branch; do not create or switch branches.
- `task-branch`: use an explicitly named task branch; ask before creating or switching if none is
  specified.
- `read-only`: inspect only; do not edit or commit.
- `ask`: ask before edits or branch changes.

Most repos should use `default-branch` or `same-branch`, not per-task branching. Work mode decides
*where* work happens; the autonomy ceiling decides *how far* it may go (see the `agents-core:git-discipline`
skill); the stricter rule wins. Validate this file with `at repos-check` (add `--local` to also check
`.local/repos.map`).

| Repo | Required | Role | Default branch | Integration branch | Work mode | Autonomy max | Areas | Notes |
|------|----------|------|----------------|--------------------|-----------|--------------|-------|-------|
| this-project | yes | Primary repo | master | master | default-branch | L1 | global | Rename to this repo's slug |
| example-service | no | Example related repo | unknown | unknown | ask | L1 | N/A | Replace or remove this example row |
