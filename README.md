# Agents Template

This is the base **agents template** — a portable operating contract (`AGENTS.md`) and reusable skills/playbooks for Claude Code and OpenAI Codex, designed to be seeded into new projects and updated in place via a `template` git remote.

> **This `README.md` extends [`_base/README.md`](./_base/README.md).** The base file is the authoritative documentation (skills, playbooks, sync workflow, adoption patterns). Downstream projects seeded from this template should keep `_base/README.md` exactly as inherited (so future upstream improvements merge cleanly) and write their own `README.md` that links to it.

**Canonical URL:** `git@github.com:toderian/project_template.git`

## Quick links

- [Base contract → `_base/README.md`](./_base/README.md) — full template documentation
- [Operating contract → `AGENTS.md`](./AGENTS.md)
- [Artifact registry → `artifacts/README.md`](./artifacts/README.md)
- [Skills → `playbooks/skills/`](./playbooks/skills/)
- [Seed a new project → "Option 3" in `_base/README.md`](./_base/README.md#option-3-seed-a-new-project-from-this-template)
- [Pull template updates → "Staying in sync" in `_base/README.md`](./_base/README.md#staying-in-sync-with-the-template)

## Convention for downstream projects

Projects seeded from this template follow a strict two-file split:

| File | Owned by | On `git fetch template && git merge` |
|------|----------|---------------------------------------|
| `README.md` | **Downstream project** (write your own; describes your project) | Not touched — never conflicts |
| `_base/README.md` | **Upstream template** (do not edit downstream) | Updated cleanly with upstream changes |

A minimal downstream `README.md`:

```markdown
# MyApp

What MyApp does, how to run it, etc.

## Agent contract

This project extends the agents template — see [`_base/README.md`](./_base/README.md)
([upstream](https://github.com/toderian/project_template)).
```

If you need to add project-specific agent rules, do it in your own `README.md` or in a project `AGENTS.md`, **not** by editing `_base/README.md`. That file belongs to the template and gets updates with time.

The same rule applies to skills, plugins, and any other artifacts: list things **created in the base** (this template) in `_base/README.md`; list things **created in your project** in your own `README.md`. The two files never overlap, so there are no merge conflicts when the template pushes updates.

## Project-specific additions

> **This section is the downstream-project slot.** Each project seeded from this template uses this part of `README.md` to describe what *it* adds on top of the base — its own skills, plugins, conventions, scripts, etc. Keep or adapt the local credentials convention below as needed, then add project-owned items in the subsections that follow.

### Local credentials

Credentials for agent/tool use may live under `.creds/` at the repository root. The folder is
gitignored and must never be committed. Agents should read credential values only when a task requires
them, and should not print or copy secret contents into tracked files, docs, logs, prompts, final
answers, or task artifacts.

### Artifacts

Large, external, generated, encrypted, or reproducible artifacts are listed in
[`artifacts/README.md`](./artifacts/README.md). Check that registry before walking the repo for
artifact files; it records the artifact slug, backend, path or pattern, fetch command, verification
command, encryption status, key path, and update notes.

Git LFS is the default documented backend. Run `git lfs install` once, fetch only needed artifacts
with `git lfs pull --include="<path-or-pattern>"`, and use `git lfs ls-files --name-only` to confirm
that every LFS-tracked path is represented in the registry. Before committing a new LFS artifact, run
`git lfs track "<path-or-pattern>"`, keep the `.gitattributes` rule narrow and per-artifact, place it
outside the managed agents-template block, and update `artifacts/README.md` in the same change.

Encrypted artifacts should use `age` by default. Commit only encrypted files such as `*.age`, keep
private keys under `.creds/lfs/<artifact-slug>.agekey`, and write decrypted local outputs under
ignored paths such as `.local/artifacts/<artifact-slug>/`.

### Saved prompts

Reusable or historically useful prompts may live under `.prompts/` and be committed with the
repository. Review any prompt before committing it for credentials, private data, copied sensitive
context, or other material that should not be preserved in Git. Prompts that should remain local-only
belong under `.no-commit/.prompts/`.

### Python tooling environments

Repo-level Python tooling dependencies should use `uv` under `tools/python/`. When such tooling exists,
commit `tools/python/pyproject.toml`, `tools/python/uv.lock`, and `tools/python/.python-version`; keep
`tools/python/.venv/` local-only. Run managed commands from that folder, for example
`cd tools/python && uv sync` or `cd tools/python && uv run <command>`.

### Project skills

_None for the base template itself._

Downstream projects, list any skills your project adds on top of the base template here (the base-template catalog is in [`_base/README.md`](./_base/README.md#available-skills) and updates from upstream). Example:

| Skill | Description |
|-------|-------------|
| `<your-skill>` | `<one-line description>` |

### Project plugins / tooling

_None for the base template itself._

Downstream projects, list project-specific plugins, scripts, or tooling here. The base-template plugin catalog is in [`_base/README.md`](./_base/README.md#third-party-plugins-own-installers).
