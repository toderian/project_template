# agents-template

A plugin marketplace of operating skills, safety hooks and subagent roles for coding
agents — usable from **Claude Code** and **OpenAI Codex** — plus `at`, a small CLI that
seeds a downstream repository with the handful of files it owns itself.

Nothing here is merged into your project. You install plugins from this marketplace and
run `at init` once; updates arrive through the plugin manager, not through a git remote.

## Install

Claude Code, in a session (or the same two commands as `claude plugin marketplace add …`
and `claude plugin install …` from a shell):

```
/plugin marketplace add toderian/project_template
/plugin install agents-core@agents-template
```

Codex:

```bash
codex plugin marketplace add toderian/project_template
codex plugin add agents-core@agents-template
```

From a clone (both harnesses at once):

```bash
git clone git@github.com:toderian/project_template.git
cd project_template
plugins/agents-core/bin/at bootstrap --local . --claude --codex
```

`at bootstrap` adds both marketplaces, installs the plugins and writes the `~/.local/bin/at`
resolver — after it, plain `at` works everywhere, provided `~/.local/bin` is on your `PATH`
(inside Claude Code the plugin puts `at` on the tool `PATH` by itself). Drop `--local .` to
install from GitHub, add `--tasks` / `--extras` / `--personal` for the other plugins, and
`--clean-global-skills` to list stale global skill symlinks from the pre-1.0 layout.

## Use it in a repo

```bash
cd /path/to/your/repo
at init --with-tasks          # write the seed: AGENTS.md, CLAUDE.md, .claude/settings.json, …
at doctor                     # check the repo against the contract
at doctor --all               # check both runtimes when both CLIs are installed
```

`at init` never overwrites a file you own; re-running it is safe. Flags: `--with-tasks`,
`--with-artifacts`, `--with-workbooks`, `--with-repos`, `--all`. Install `jq` before using the
bundled safety hooks. In Codex, open `/hooks` after installation or an update and review/trust the
hook definitions; changed hooks are skipped until their new hash is trusted.

## Keep it up to date

Plugins install per machine, so one update covers every repo that uses them:

```bash
at update --check             # what is installed, and what version
at update                     # refresh the marketplace and update the installed plugins
at update --claude            # update only the Claude installation
at update --codex             # update only the Codex installation
```

Restart the CLI afterwards — a running session keeps the old plugins. Then, in each repo,
`at doctor` reports whether the downstream-owned `AGENTS.md` routing table has fallen behind the
plugin seed, and the `agents-core:setup-project` skill adopts the difference (see its
`references/adopting-updates.md`).

Coming from the pre-1.0 template (a repo with vendored `_base` and `playbooks` trees
and a `template` git remote)? Use `at migrate` — it is a dry run by default. Flags:
`--yes`, `--commit`, `--keep-tasks`, `--no-tasks`, `--allow-untracked` (run it with untracked
files in the tree — build output, a huge attachments dir, a WIP file you are not ready to
commit — without stashing or committing them first; `--commit` never sweeps them in). See
[`docs/migration.md`](docs/migration.md).

## Plugins

| Plugin | What's inside | Enable it when |
|---|---|---|
| `agents-core` | 21 skills (plan execution, TDD, diagnose, spec + planning workflows, grilling, codebase design, research, handoff, subagent protocol, security review, git discipline, project setup), 5 safety hooks, 6 subagent roles, the `at` CLI | Always — it is the contract |
| `agents-tasks` | 23 skills: the `docs/tasks_manager/` task ledger and its tooling, wayfinder decision maps, knowledge base, workbooks, artifact registry, cross-repo workflows | The repo tracks work as task files, or wants durable notes/registries |
| `agents-extras` | 19 skills: architecture review, domain modeling, GitHub triage and PRDs, UI/frontend review, migration safety, pre-commit setup, skill and agent-doc authoring | You want the wider review/GitHub/UI toolkit |
| `agents-personal` | 8 skills: writing, editing, Obsidian, teaching, niche migrations | Personal repos; not useful in most codebases |

Skills are invoked by their full id (`/agents-core:tdd` in Claude, `$agents-core:tdd` in Codex) or
picked up by the model from their descriptions. Use `/skills` in Codex to browse and mention an
installed skill. The invocation forms follow the
[official Codex skills documentation](https://developers.openai.com/codex/skills); Codex hook trust
is described in the [official hooks documentation](https://developers.openai.com/codex/hooks).

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
scripts/install-pre-commit.sh     installs the pre-commit gate
scripts/tests/run-all.sh          the whole test suite
docs/specs/, docs/plans/, docs/meta/, docs/migration.md
```

## Developing

```bash
python3 scripts/build.py          # regenerate derived files (marketplaces, codex twins)
python3 scripts/build.py --check  # fail if anything is out of date
bash scripts/tests/run-all.sh     # build check + plugin validation + hook/ledger/CLI tests
scripts/install-pre-commit.sh     # once: gate every commit on that suite
```

Sources of truth and the rules for changing them are in [`AGENTS.md`](AGENTS.md).
The pre-commit hook runs `run-all.sh`; CI runs every part of it that does not need the CLI.

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
