# Agents Template

This is the base **agents template** — a portable operating contract (`AGENTS.md`) and reusable skills/playbooks for Claude Code and OpenAI Codex, designed to be seeded into new projects and updated in place via a `template` git remote.

> **This `README.md` extends [`README_BASE.md`](./README_BASE.md).** The base file is the authoritative documentation (skills, playbooks, sync workflow, adoption patterns). Downstream projects seeded from this template should keep `README_BASE.md` exactly as inherited (so future upstream improvements merge cleanly) and write their own `README.md` that links to it.

**Canonical URL:** `git@github.com:toderian/project_template.git`

## Quick links

- [Base contract → `README_BASE.md`](./README_BASE.md) — full template documentation
- [Operating contract → `AGENTS.md`](./AGENTS.md)
- [Skills → `playbooks/skills/`](./playbooks/skills/)
- [Seed a new project → "Option 3" in `README_BASE.md`](./README_BASE.md#option-3-seed-a-new-project-from-this-template)
- [Pull template updates → "Staying in sync" in `README_BASE.md`](./README_BASE.md#staying-in-sync-with-the-template)

## Convention for downstream projects

Projects seeded from this template follow a strict two-file split:

| File | Owned by | On `git fetch template && git merge` |
|------|----------|---------------------------------------|
| `README.md` | **Downstream project** (write your own; describes your project) | Not touched — never conflicts |
| `README_BASE.md` | **Upstream template** (do not edit downstream) | Updated cleanly with upstream changes |

A minimal downstream `README.md`:

```markdown
# MyApp

What MyApp does, how to run it, etc.

## Agent contract

This project extends the agents template — see [`README_BASE.md`](./README_BASE.md)
([upstream](https://github.com/toderian/project_template)).
```

If you need to add project-specific agent rules, do it in your own `README.md` or in a project `AGENTS.md`, **not** by editing `README_BASE.md`. That file belongs to the template and gets updates with time.
