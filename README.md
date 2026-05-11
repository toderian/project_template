# Agents Template

This is the base **agents template** — a portable operating contract (`AGENTS.md`) and reusable skills/playbooks for Claude Code and OpenAI Codex, designed to be seeded into new projects and updated in place via a `template` git remote.

> **This `README.md` extends [`_base/README.md`](./_base/README.md).** The base file is the authoritative documentation (skills, playbooks, sync workflow, adoption patterns). Downstream projects seeded from this template should keep `_base/README.md` exactly as inherited (so future upstream improvements merge cleanly) and write their own `README.md` that links to it.

**Canonical URL:** `git@github.com:toderian/project_template.git`

## Quick links

- [Base contract → `_base/README.md`](./_base/README.md) — full template documentation
- [Operating contract → `AGENTS.md`](./AGENTS.md)
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

> **This section is the downstream-project slot.** Each project seeded from this template uses this part of `README.md` to describe what *it* adds on top of the base — its own skills, plugins, conventions, scripts, etc. The base template itself has nothing to list here, so this section is intentionally empty.

### Project skills

_None for the base template itself._

Downstream projects, list any skills your project adds on top of the base template here (the base-template catalog is in [`_base/README.md`](./_base/README.md#available-skills) and updates from upstream). Example:

| Skill | Description |
|-------|-------------|
| `<your-skill>` | `<one-line description>` |

### Project plugins / tooling

_None for the base template itself._

Downstream projects, list project-specific plugins, scripts, or tooling here. The base-template plugin catalog is in [`_base/README.md`](./_base/README.md#third-party-plugins-own-installers).
