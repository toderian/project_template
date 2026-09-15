# Repo registry, local checkout map, and autonomy

Cross-repo projects use a two-layer repo convention:

- `.config/repos.project.md` is created and committed by each downstream project that opts into this
  convention. It defines stable repo slugs, whether each repo is required, branch defaults, work mode,
  optional autonomy ceiling, and related areas.
- `.local/repos.map` is a local-only, gitignored map from repo slug to absolute checkout path. It is
  machine-specific and must never be referenced from committed docs.
- `at init --with-repos` seeds `.config/repos.project.md` from the upstream example; create
  `.local/repos.map` by hand per machine.

Set this up during downstream project setup, after project-specific `README.md` and `AGENTS.md` are in
place and before creating tasks for multi-repo work. Single-repo projects can skip it until they need
repo-scope tasks or cross-repo docs.

Repo slugs must match `^[a-z][a-z0-9-]*$`. If no `.config/repos.project.md` exists, omit `Repos`
metadata from new task files; existing `Repos: N/A` rows remain valid. Cross-repo docs should
reference source paths as `<repo-slug>:<repo-relative-path>`, never as absolute local paths. The
branch/work policy in `.config/repos.project.md` is a default; explicit user instructions, task files,
or repo-specific `AGENTS.md` instructions override it.

## `.config/repos.project.md`

Markdown with one required table.

New shape:

```md
| Repo | Required | Role | Default branch | Integration branch | Work mode | Autonomy max | Areas | Notes |
|------|----------|------|----------------|--------------------|-----------|--------------|-------|-------|
| project-template | yes | Agent template | master | master | default-branch | L1 | global | Work directly on default branch |
```

Legacy shape, still valid and treated as `Autonomy max: L1`:

```md
| Repo | Required | Role | Default branch | Integration branch | Work mode | Areas | Notes |
|------|----------|------|----------------|--------------------|-----------|-------|-------|
| project-template | yes | Agent template | master | master | default-branch | global | Work directly on default branch |
```

Allowed values:

- `Required`: `yes` or `no`
- branch fields: a branch name, `N/A`, or `unknown`
- `Work mode`: `default-branch`, `task-branch`, `same-branch`, `read-only`, or `ask`
- `Autonomy max`: optional permission ceiling, one of `L0`, `L1`, `L2`, or `L3`; old registries
  without this column remain valid and default to `L1`
- `Areas`: comma-separated area slugs or `N/A`

Work mode meaning:

- `default-branch`: work and commit directly on `Default branch`; ask if the checkout is elsewhere.
- `same-branch`: stay on the current branch and do not create or switch branches.
- `task-branch`: use an explicitly named task branch; ask before creating or switching if none is
  specified.
- `read-only`: inspect only; do not edit or commit.
- `ask`: ask the user before edits or branch changes.

Template-inherited downstream repos should normally use `default-branch` or `same-branch`. Do not use
branching for those repos unless the user explicitly asks or the host/CI policy requires it.

## Autonomy levels

Autonomy levels are permission ceilings layered on top of work mode and branch rules:

- `L0`: read-only inspection and reporting.
- `L1`: local edits, checks, iteration, and local commits inside an approved workflow.
- `L2`: L1 plus push/update the approved branch and repair CI for that branch.
- `L3`: L2 plus open/update draft PRs and validate PR status.

No level authorizes merge, deploy, release, ready-for-review, force-push/history rewrite, broad
connector writes, or secret exposure. A task's optional `Autonomy` row may lower the effective
ceiling; it cannot exceed the resolved repo `Autonomy max`. Full ladder and resolution order: the
`agents-core:git-discipline` skill (references/autonomy-levels.md).

## `.local/repos.map`

Line-oriented:

```text
# Format: <repo-slug>: <absolute-path>
project-template: /home/you/repos/project_template
naeural-core: /home/you/repos/naeural_core
```

Blank lines and `#` comment lines are allowed. Entries split on the first `:`, with whitespace trimmed
around slug and path. Duplicate slugs are invalid. Paths must be absolute local paths to existing
directories. No shell expansion is performed; this is not dotenv.

## Validation

```bash
at repos-check           # committed repo config and task Repos / Autonomy metadata
at repos-check --local   # also the local checkout map
```
