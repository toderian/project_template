# agents-template

A plugin marketplace of operating skills, safety hooks and subagent roles for coding
agents — usable from **Claude Code** and **OpenAI Codex** — plus `at`, a small CLI that
seeds a downstream repository with the handful of files it owns itself.

Nothing here is merged into your project. You install plugins from this marketplace and
run `at init` once; updates arrive through the plugin manager, not through a git remote.

## Install

Claude Code:

```
/plugin marketplace add toderian/project_template
/plugin install agents-core@agents-template
```

Codex:

```bash
codex plugin marketplace add toderian/project_template
codex plugin add agents-core@agents-template
```

Or do both harnesses at once, from any shell:

```bash
at bootstrap --tasks          # adds both marketplaces, installs plugins, writes ~/.local/bin/at
```

`at bootstrap` also accepts `--local <checkout>` (install from a clone instead of GitHub),
`--claude` / `--codex` (one harness only), `--extras`, `--personal`, and
`--clean-global-skills` (list stale global skill symlinks from the pre-1.0 layout).

## Use it in a repo

```bash
cd /path/to/your/repo
at init --with-tasks          # write the seed: AGENTS.md, CLAUDE.md, .claude/settings.json, …
at doctor                     # check the repo against the contract
```

`at init` never overwrites a file you own; re-running it is safe. Flags: `--with-tasks`,
`--with-artifacts`, `--with-workbooks`, `--with-repos`, `--all`.

Coming from the pre-1.0 template (a repo with vendored `_base` and `playbooks` trees
and a `template` git remote)? Use `at migrate` — it is a dry run by default. See [`docs/migration.md`](docs/migration.md).

## Plugins

| Plugin | What's inside | Enable it when |
|---|---|---|
| `agents-core` | 16 skills (plan execution, TDD, diagnose, spec + planning workflows, handoff, subagent protocol, security review, git discipline, project setup), 5 safety hooks, 6 subagent roles, the `at` CLI | Always — it is the contract |
| `agents-tasks` | 22 skills: the `docs/tasks_manager/` task ledger and its tooling, knowledge base, workbooks, artifact registry, cross-repo workflows | The repo tracks work as task files, or wants durable notes/registries |
| `agents-extras` | 17 skills: architecture review, GitHub triage and PRDs, UI/frontend review, migration safety, pre-commit setup, skill authoring | You want the wider review/GitHub/UI toolkit |
| `agents-personal` | 8 skills: writing, editing, Obsidian, teaching, niche migrations | Personal repos; not useful in most codebases |

Skills are invoked by name (`/agents-core:tdd` in Claude, `$tdd` in Codex) or picked up by
the model from their descriptions.

## Layout

```
.claude-plugin/marketplace.json   generated — Claude view of the four plugins
.agents/plugins/marketplace.json  generated — Codex view of the same four
plugins/<name>/                   the plugins themselves
  .claude-plugin/plugin.json      source of truth for name/version/description
  .codex-plugin/plugin.json       generated
  skills/, agents/, hooks/, seed/, bin/, lib/
scripts/build.py                  regenerates every derived file (--check verifies)
scripts/release.sh                version bump + build + tests + tag
scripts/tests/run-all.sh          the whole test suite
docs/specs/, docs/plans/, docs/meta/, docs/migration.md
```

## Developing

```bash
python3 scripts/build.py          # regenerate derived files (marketplaces, codex twins)
python3 scripts/build.py --check  # fail if anything is out of date
bash scripts/tests/run-all.sh     # build check + plugin validation + hook/ledger/CLI tests
```

Sources of truth and the rules for changing them are in [`AGENTS.md`](AGENTS.md).
The pre-commit hook runs `run-all.sh`; CI runs the same suite minus `claude plugin validate`.

Release:

```bash
scripts/release.sh 1.1.0 --dry-run   # show the plan
scripts/release.sh 1.1.0             # bump all four plugins, build, test, commit, tag
git push && git push --tags
```

`claude plugin tag plugins/agents-core` can additionally publish a per-plugin tag.

## More

- Design: [`docs/specs/2026-08-18-plugin-restructure-design.md`](docs/specs/2026-08-18-plugin-restructure-design.md)
- Migration from the pre-1.0 template: [`docs/migration.md`](docs/migration.md)
- Changes: [`CHANGELOG.md`](CHANGELOG.md)
- Refresh process for this repo's doctrine: [`docs/meta/UPDATE_PLAN.md`](docs/meta/UPDATE_PLAN.md), [`docs/meta/RESEARCH_SNAPSHOT.md`](docs/meta/RESEARCH_SNAPSHOT.md)

Licensed under Apache-2.0 ([`LICENSE`](LICENSE)).
