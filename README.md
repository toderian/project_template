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

`at bootstrap` and `at update` also install the [caveman](https://github.com/JuliusBrussee/caveman)
companion from its own marketplace: the `caveman@caveman` plugin in Claude Code (its hooks need
`node`), and the `caveman` skill in Codex through `npx skills add`. The seed settings enable it per
repo, so `at init` and a session restart are all a downstream repo needs. Invoke it as
`/caveman:caveman` in Claude or `$caveman` in Codex. In Claude it is on for every session; in Codex
it is per session, since the skill has no hook there. `at init` also writes a local `.caveman.json`,
ignored by the seed `.gitignore` block, with `defaultMode` left null so it inherits your user-level
caveman config (default `full`): set it to `"off"` to turn terse mode off for that checkout only,
with no risk of committing the change. `CAVEMAN_DEFAULT_MODE=off` in the shell outranks it. The companion
tracks caveman's default branch and is refreshed by `at update`; it is optional, so a missing `npx`
or a failed install is reported but never fails `at bootstrap` or `at update`.

### Optional add-ons

Tools only some repos need are off until a repo switches them on with `at addon enable <name>`.
Each is an MCP server from its own upstream, pinned to a version and started with `npx`; nothing is
copied into the repo.

| Add-on | What it adds | Upstream |
|---|---|---|
| `browser` | The agent opens the running app in a local headless Chrome: screenshots, console, accessibility checks. Usage statistics are switched off | [ChromeDevTools/chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp) |
| `shadcn` | Component search and install for React + Tailwind repos that have `components.json` | [shadcn-ui/ui](https://github.com/shadcn-ui/ui) |

`enable` writes the server to `.mcp.json` and enables `agents-extras` (which holds
`agents-extras:frontend-design` and `agents-extras:ui-design-review`) in `.claude/settings.json`.
Commit both, so everyone working in the repo gets the same tools; Claude Code asks each person once
to approve the server. For Codex the server goes into the checkout's git-ignored
`.codex/config.toml`, which Codex loads in a trusted project, so each Codex user runs the same
`at addon enable` once. Codex asks before each tool call of the server; a non-interactive
`codex exec` run cannot answer, so there the tools fail unless the server sets
`default_tools_approval_mode = "approve"`. To set it, replace the managed block in
`.codex/config.toml` with your own `[mcp_servers.<name>]` table; `at` keeps a definition it did not
write. `at addon status` and `at doctor` say what is enabled and what is missing
(Node's `npx`, `components.json`, the Codex step); `at addon disable <name>` removes what `enable`
wrote.

## Use it in a repo

```bash
cd /path/to/your/repo
at init --with-tasks          # write the seed: AGENTS.md, CLAUDE.md, .claude/settings.json, …
at doctor                     # check the repo against the contract
at doctor --all               # check both runtimes when both CLIs are installed
at task brief AUTH-001 --phase 2      # one phase of a task as a self-contained implementer brief
at task run-state init AUTH-001       # open the resume map for agents-core:execute-plan
at task run AUTH-001 --check "make test"   # drive the whole execute-plan loop from a shell
at task report AUTH-001               # morning report of a run: commits, decisions, parked questions (docs/tasks_manager/_reports/)
at run-guard status                   # what this session must finish before its turn may end (disarm: at run-guard disarm)
at run-guard arm --watch --budget-usd 4 AUTH-001   # plus a watchdog that restarts the session if its process dies
at lease run full-suite -- make test  # one holder per shared resource on this host (take|release|list|clear; exit 3 = refused)
at notify "title" < body.txt         # run your notify command (git config agents.notifyCommand "<cmd>", or AGENTS_NOTIFY_CMD); the run guard uses it
at peer enable codex          # opt in, this checkout only: large reviews also ask the other agent CLI
at addon enable browser       # opt in, this repo: UI skills plus a browser the agent can look through
```

Notifications: when an unattended run stops for you (`BLOCKED`), gives up, ends on an empty last
message (`EMPTY`), or finishes, the run guard runs your own command (`git config agents.notifyCommand
'my-sender --flag'`, read in the session's working directory, or `AGENTS_NOTIFY_CMD`). It is a program with
optional arguments, run without a shell: the title is appended as its last argument and the body comes on
stdin. Put pipes, redirects or `curl` calls in a script and name the script.
The body holds task ids and a one-line reason, no file contents. That text leaves
this machine through whatever command you configured. Nothing is sent when none is set.

Unattended runs (`agents-core:unattended-run`, then `agents-core:execute-plan` or `at task run`), in
short; `plugins/agents-core/skills/execute-plan/references/run-state.md` has the detail:

- The run guard writes a status file per session (`<session id>.status`: the kind of the last
  let-through stop, `at run-guard status` shows it) and, after a compaction or a resume, reminds the
  session of its open tasks and first open row.
- `at run-guard arm --watch` adds a watchdog that restarts a dead session with `claude --resume`,
  only for a task marked `Watch: on`, within recorded caps (`--max-resumes`, `--budget-usd`; bypass
  mode only with `--allow-bypass`). Those caps and the restarts used live in one record per run;
  `--until` and `--idle` (when to report a silent run) belong to one watcher and are not recorded.
- `at task report <TASK-ID>` writes the morning report to `docs/tasks_manager/_reports/`: phases,
  commits, `Decision:` / `Ruling:` lines, and what needs you first.
- `at task run` honours `After:` lines: a phase that fails is set aside and only its dependants are
  parked; the rest run. `--at-review-cap park|continue` says what happens at the review cap (default
  `park`; `continue` only in an unattended task and never with a critical finding), and exit code 4 means the run finished with parked rows. `--lanes N` (1-3) runs phases whose
  `Files:` fences do not overlap in parallel worktrees, merged wave by wave.
- Live check against the real CLI, by hand (it spends tokens, so it is not in `run-all.sh`, the
  pre-commit hook or CI): `bash scripts/tests/test-unattended-live.sh [E1 ...]`.

`at init` never overwrites a file you own; re-running it is safe. Flags: `--with-tasks`,
`--with-artifacts`, `--with-workbooks`, `--with-repos`, `--all`. Install `jq` before using the
bundled safety hooks. In Codex, open `/hooks` after installation or an update and review/trust the
hook definitions; changed hooks are skipped until their new hash is trusted.

The seed `.claude/settings.json` sets `"autoCompactWindow": 300000`, so Claude Code compacts the
conversation near 300k tokens instead of filling the model's whole window. To change it in one
checkout without touching the committed file, put a number in `.claude/settings.local.json` (for
example `{"autoCompactWindow": 1000000}`); `"auto"` there does not override the project value.
`CLAUDE_CODE_AUTO_COMPACT_WINDOW=<tokens>` in the shell and `/autocompact` in a session also win.
`at init` adds the key only when the repo has none.

## Keep it up to date

Agents close verified tasks through `agents-tasks:complete-task` as part of authorized execution,
then continue an already-authorized task chain. A separate closure request is unnecessary; failed
checks, missing evidence, and explicit human acceptance gates still block completion.

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
| `agents-core` | 21 skills (plan execution in order or in parallel lanes, unattended runs, structured questions to the user, TDD, diagnose, spec + planning workflows, grilling, codebase design, handoff, subagent protocol, security review, git discipline, project setup), 9 hooks (5 safety guards, a subagent report-contract check, a run guard that keeps a session from ending a turn mid-run, a reminder of the open run after a compaction or resume, a seed-drift notice at session start), 6 subagent roles, the `at` CLI | Always — it is the contract |
| `agents-tasks` | 26 skills: the `docs/tasks_manager/` task ledger and its tooling, task simplification and verification, wayfinder decision maps, knowledge base, design trees (`at design`), exploratory testing against them (`at explore`), workbooks, artifact registry, cross-repo workflows | The repo tracks work as task files, or wants durable notes/registries |
| `agents-extras` | 19 skills: architecture review, domain modeling, GitHub triage and PRDs, UI/frontend review, migration safety, pre-commit setup, skill and agent-doc authoring, repository memory sync | You want the wider review/GitHub/UI toolkit |
| `agents-personal` | 8 skills: writing, editing, Obsidian, teaching, niche migrations | Personal repos; not useful in most codebases |

Skills are invoked by their full id (`/agents-core:tdd` in Claude, `$agents-core:tdd` in Codex) or
picked up by the model from their descriptions. Use `/skills` in Codex to browse and mention an
installed skill. The invocation forms follow the
[official Codex skills documentation](https://developers.openai.com/codex/skills); Codex hook trust
is described in the [official hooks documentation](https://developers.openai.com/codex/hooks).

## Share repository memory between agents

With `agents-extras` installed, run `/agents-extras:sync` in Claude Code or `$agents-extras:sync` in
Codex. Add `preview` for a read-only merge proposal. Either invocation reads both agents' saved
memories for the current repository, reconciles them into `.no-commit/agent-memory/MEMORY.md`, and
adds project instruction pointers so both agents read that shared context. Conflicts are surfaced
for resolution; native stores stay intact. Global preferences and other repositories are excluded.

This is an explicit, machine-local sync. Rerun it after new learnings; an already-running peer must
read the shared index or restart. Codex's generated native memory files are not overwritten. The
skill reports missing sources and unresolved conflicts rather than claiming complete synchronization.

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
scripts/check-addon-pins.sh       compares the add-on pins with npm
scripts/tests/run-all.sh          the whole test suite
docs/specs/, docs/meta/, docs/migration.md
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
