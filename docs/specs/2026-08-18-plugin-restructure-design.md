# Design: agents-template as plugins + thin seed

- Date: 2026-08-18
- Status: approved in conversation (approach B), spec pending user review
- Audit that motivated this: `https://claude.ai/code/artifact/66bacd4d-1af5-43e6-992c-3aeab095480d`

## 1. Goal

Turn `project_template` from a git-merged monolith (`_base/` + `playbooks/` + three
generated skill trees + vendored third-party plugins) into:

1. a **plugin marketplace** whose plugins both Claude Code and Codex install and update
   natively (versioned, pinned, namespaced), and
2. a **thin seed** of downstream-owned files (~8) that a small CLI writes into a project
   once and never merges again.

Non-goals: changing the task-ledger data format on disk beyond making fields optional;
supporting Antigravity/Gemini/Copilot with dedicated machinery (they get `.agents/skills`
compatibility for free); keeping the `template` git remote.

## 2. Decisions already made (with the user)

| # | Decision |
|---|---|
| 1 | Approach **B** (plugin + thin seed). Not A (tidy in place), not C (external only). |
| 2 | Task ledger: **keep and slim**. Same on-disk format, fewer required fields, logs offloaded, roadmap horizons optional. |
| 3 | **Drop** dedicated Antigravity/Gemini support and its scripts. |
| 4 | Third-party plugins (superpowers, github) come from their **marketplaces, pinned**; nothing vendored. |
| 5 | Ledger path stays **`docs/tasks_manager/`**. |
| 6 | Dormant/personal skills → a second plugin `agents-personal` in the same marketplace (default; user may relocate later). |

## 3. Facts the design depends on (verified 2026-08-18)

- Claude Code loads `CLAUDE.md`, not `AGENTS.md`; `@AGENTS.md` inside `CLAUDE.md` is the documented interop. Keep always-loaded files < 200 lines.
- Claude Code skills: `.claude/skills/`, `~/.claude/skills/`, plugin `skills/`. `disable-model-invocation: true` hides a skill from the model. Skill frontmatter supports `paths:` (load when matching files are touched).
- Codex reads `AGENTS.md` (root-down, 32 KiB cap) and skills from `$REPO_ROOT/.agents/skills`, `~/.agents/skills`, plugin `skills/`.
- Claude plugin: `.claude-plugin/plugin.json`; defaults `skills/`, `agents/`, `hooks/hooks.json`, `bin/` (added to Bash `PATH`); env `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}`, `${CLAUDE_PROJECT_DIR}`. Marketplace: `.claude-plugin/marketplace.json` with `plugins[].source` relative to the marketplace repo; pin by `version`/`ref`/`sha`; a committed project `.claude/settings.json` (`extraKnownMarketplaces` + `enabledPlugins`) auto-installs after folder trust. `claude plugin validate <path>`, `claude plugin details <name>` exist.
- Codex plugin: `.codex-plugin/plugin.json` (`name`, `version`, `description` required; `skills`, `hooks`, `mcpServers`, `interface`); no agents component. Marketplace `.agents/plugins/marketplace.json` at repo root; `codex plugin marketplace add owner/repo[@ref] | <path>`; `codex plugin add <plugin>@<marketplace>`. Plugin hooks get `PLUGIN_ROOT`/`PLUGIN_DATA` and require one-time user trust.
- Codex hooks: same event names, same stdin JSON (`tool_name: Bash|apply_patch|Edit|Write`, `tool_input.command`), same exit-2 / `permissionDecision` contract; `.codex/hooks.json`, `~/.codex/hooks.json`, or plugin `hooks/hooks.json`. Enabled by default (user has `[features] hooks = true`).
- The user's Codex CLI is 0.147.0; Claude Code 2.1.234. The existing local Codex marketplace (`~/.agents/plugins/marketplace.json`) resolves to non-existent paths and is "not installed" — it will be replaced.

## 4. Upstream repository layout (target)

```
project_template/                       # = the marketplace repo
├── .claude-plugin/marketplace.json     # name: agents-template; 4 plugins, relative sources
├── .agents/plugins/marketplace.json    # Codex view of the same 4 plugins
├── plugins/
│   ├── agents-core/                    # ALWAYS enabled downstream
│   │   ├── .claude-plugin/plugin.json  # name agents-core, version 1.0.0
│   │   ├── .codex-plugin/plugin.json
│   │   ├── skills/<name>/SKILL.md (+ references/, scripts/, assets/)
│   │   ├── agents/*.md                 # implementer, reviewer, researcher, plan-critic,
│   │   │                               # security-auditor, spec-validator  (source of truth)
│   │   ├── hooks/hooks.json            # Claude (uses ${CLAUDE_PLUGIN_ROOT})
│   │   ├── hooks/hooks.codex.json      # GENERATED for Codex (uses ${PLUGIN_ROOT})
│   │   ├── hooks/*.sh, hooks/tests/test-hooks.sh
│   │   ├── codex/agents/*.toml         # GENERATED from agents/*.md; copied to seed
│   │   ├── seed/                       # files `at init` writes into a downstream (see §6)
│   │   └── bin/at                      # the CLI (on Bash PATH in Claude; symlinked for humans)
│   ├── agents-tasks/                   # opt-in: ledger, knowledge base, workbooks, artifacts, cross-repo
│   │   ├── .claude-plugin/ .codex-plugin/
│   │   ├── skills/... (task-ledger holds scripts/ + references/ conventions)
│   │   ├── seed/                       # docs/tasks_manager skeleton, artifacts/README.md, workbooks/README.md
│   │   └── bin/at-ledger, bin/at-repos # thin wrappers over the task-ledger scripts
│   ├── agents-extras/                  # opt-in: architecture, github, ui, database, dev-tooling
│   └── agents-personal/                # opt-in: writing, obsidian, education, typescript
├── scripts/                            # template DEV tooling only (not shipped)
│   ├── build.py                        # generates codex hooks/agents, marketplace files, skill index; --check mode
│   ├── release.sh                      # bump versions, tag
│   └── tests/                          # hook tests runner, ledger tests, init/migrate integration test
├── docs/
│   ├── specs/, plans/                  # this spec + implementation plan
│   ├── meta/UPDATE_PLAN.md, RESEARCH_SNAPSHOT.md
│   └── migration.md                    # how a legacy `_base/` downstream migrates
├── AGENTS.md, CLAUDE.md                # contributor rules for THIS repo (short)
├── README.md, CHANGELOG.md, LICENSE, .gitignore, .gitattributes (binary rules only)
└── (deleted: _base/, playbooks/, skills/, .claude/skills, .agents/skills, .agents/*.json,
             .claude-plugin/plugin.json at root, .codex/, .claude/hooks, .claude/agents,
             .claude/settings.json hooks block, artifacts/, docs/_plans/.gitkeep)
```

Design choices explained:

- **Marketplace root with `plugins/<name>/`** (codex-warp shape) rather than plugin-at-root (superpowers shape) because we ship four plugins with per-repo enablement; per-repo pack selection becomes "which plugins are enabled" instead of a home-grown `skills.enabled.json`.
- **Skills follow the Agent Skills spec**: one `SKILL.md` per skill (≤ 500 lines), playbook body inlined, conventions moved into `references/`, templates into `assets/`. No wrapper → playbook hop; no `disable-model-invocation` on workflow skills (only on side-effect-heavy ones: `complete-task`, `squash-workspace-commits`, `tidy-repo`).
- **One `hooks/hooks.json` for Claude and a generated Codex twin.** The five scripts stay bash+jq, read `tool_input.command` / `tool_input.file_path`; the sensitive-write hook gains an `apply_patch` branch (parses `*** Add File:` / `*** Update File:` lines) so it also fires in Codex.
- **Agents**: Claude `.md` is the source; `codex/agents/*.toml` generated by `scripts/build.py` and shipped in the seed (Codex plugins cannot carry agents).
- **`bin/at`**: single CLI, bash + python3 only. Subcommands: `bootstrap`, `init`, `migrate`, `doctor`, `version`, `ledger …`, `reserve …`, `repos-check`. On the Bash PATH inside Claude automatically; `at bootstrap` writes `~/.local/bin/at` as a resolver script that finds the newest installed `agents-core` (Claude cache first, then Codex marketplace checkout) so humans and Codex sessions can call it too.

## 5. Skill inventory (what goes where)

| Plugin | Skills (name → source today) | Notes |
|---|---|---|
| **agents-core** | `execute-plan`, `tdd` (+refs tests/mocking/deep-modules/interface-design/refactoring), `diagnose`, `spec-workflow`, `task-spec-workflow`, `planning-workflow` (+ref plan-critique), `prototype` (+refs UI/LOGIC), `performance-optimization`, `handoff` (+assets AGENT_* templates), `subagent-protocol` (+refs personalities/*, agent-loop-recipes, prompt-orchestration), `security-review-owasp` (+ref languages.md), `simplicity-review`, `git-discipline` (NEW: contract §9 branch/commit/push + autonomy-levels + squash-workspace-commits), `setup-project` (renamed from `init`; wraps `at init`) | 15 skills |
| **agents-tasks** | `task-ledger` (NEW hub: quickstart + `references/{todo-convention,inbox-convention,task-system-quickstart}.md` + `scripts/{sync_todo_ledgers.py,mdtables.py,reserve_work_item.sh,check_repos_config.sh}`; `paths: docs/tasks_manager/**`), `add-task`, `capture-idea`, `triage-inbox`, `complete-task`, `roadmap`, `audit-todos`, `align`, `tidy-repo`, `prd-to-todos`, `prd-to-plan` (+ref vertical-slicing), `knowledge-base` (NEW hub: kb quickstart + refs runbook/adr/generated-artifacts + assets templates), `define-area`, `describe-component`, `distill-knowledge`, `map-system`, `refresh-context`, `ubiquitous-language`, `workbook` (convention as skill), `artifacts-registry` (registry convention + LFS/age steps, from root AGENTS.md/artifacts README), `cross-repo-feature`, `cross-repo-pr-review` (+ `.local/pr-review/<repo>-<pr>/` convention), `connectors-and-mcp` (small skill; today's convention) | 24 skills |
| **agents-extras** | `design-an-interface`, `doubt-driven-development`, `grill-me`, `grill-with-docs` (+refs), `improve-codebase-architecture` (+ref), `request-refactor-plan`, `zoom-out`, `github-triage` (+refs), `prd-to-issues`, `qa`, `triage-issue`, `write-a-prd`, `frontend-design`, `ui-design-review`, `migration-safety`, `setup-pre-commit`, `write-a-skill` | 17 skills |
| **agents-personal** | `academic-humanizer`, `deslop`, `edit-article`, `sciwrite`, `obsidian-vault`, `scaffold-exercises`, `migrate-to-shoehorn` | 7 skills |
| dropped | `git-guardrails-claude-code` (obsolete: hooks ship in plugin), `_base/workbooks/prompt-orchestration-long-task` (0 downstream refs), `playbooks/meta/template-plans/*` (git history), `test-taxonomy.md` → folded into `tdd/references/`, `agent_roles` flat wrappers (implementer/reviewer are agents, not skills) | |

Skill frontmatter: `name`, `description` (rewritten to be harness-neutral, ≤ 1,024 chars, "Use when…" phrasing), optional `paths`, `disable-model-invocation` only where noted, `metadata: {pack: <old pack>, source: playbooks/skills/…}` for provenance.

## 6. Seed (downstream-owned files) — written by `at init`

| File | Content | Overwrite policy |
|---|---|---|
| `AGENTS.md` | ≤ 200 lines: (1) operating loop + condensed principles, (2) autonomy default L1 → `git-discipline`, (3) what hooks/permissions enforce, (4) routing table task → skill, (5) repo conventions (`.creds/`, `.no-commit/`, `.prompts/`, `.local/`, `tools/python` uv, commit format), (6) **Project** section with fill-in slots (summary, commands, domain rules, repos/areas, people). HTML comments guide the human. | never overwrite; `at doctor` warns if slots still contain placeholders |
| `CLAUDE.md` | exactly `@AGENTS.md` (Claude-only additions may follow it) | create if missing |
| `.claude/settings.json` | `extraKnownMarketplaces.agents-template` (github `toderian/project_template`), `enabledPlugins` (`agents-core@agents-template: true`, `agents-tasks@…` if `--with-tasks`), `permissions.deny` (`Read(./.creds/**)`, `Edit(./.creds/**)`, `Write(./.creds/**)`, `Bash(git push --force*)`, `Bash(git push -f*)`), no hooks block (hooks come from the plugin) | merge keys; never drop user keys |
| `.codex/agents/*.toml` | generated role mirrors | overwrite (generated) |
| `.gitignore` | `# BEGIN agents-template … # END agents-template` block (`.creds/`, `.no-commit/`, `.local/`, `.inbox/`, `.venv/`, `__pycache__/`, `.claude/settings.local.json*`, `.codex/*` except agents, worktrees/tmp) | managed block replaced in place; rest untouched |
| `.gitattributes` | `# BEGIN agents-template` block with binary rules (`*.pdf *.docx *.xlsx *.pptx *.png *.jpg *.zip binary`) | managed block; **no merge drivers** |
| `docs/tasks_manager/` (`--with-tasks`) | `_inbox/ _todos/ _todos_archived/ _inbox_archived/ _logs/ _areas.md _roadmap.md` (+ generated `_active.md _done.md`) | create if missing |
| `docs/areas/`, `docs/resources/` skeleton (`--with-tasks`) | as today's `_base/docs/` minus digests/system-map extras | create if missing |
| `artifacts/README.md` (`--with-artifacts`), `workbooks/README.md` (`--with-workbooks`) | today's content, trimmed | create if missing |
| `.config/repos.project.md` (`--with-repos`) | today's example, as used by edge_node (Required/Role/Default branch/Integration branch/Work mode/Areas/Notes) | create if missing |

Not seeded any more: `README.md` (project writes its own), `_base/**`, `playbooks/**`, `skills/**`, `.claude/skills/**`, `.agents/skills/**`, `.claude/hooks/**`, `.claude/agents/**`, `.claude-plugin/`, `CONTEXT.md`, `PROJECT.md`, `project.env`.

## 7. `at` CLI behaviour

- `at bootstrap` (per machine, idempotent): `claude plugin marketplace add toderian/project_template` (or a local path with `--local <dir>`); `codex plugin marketplace add toderian/project_template`; `codex plugin add agents-core@agents-template` (+ tasks/extras/personal on flags); writes `~/.local/bin/at` resolver; optionally (`--clean-global-skills`) removes `~/.claude/skills/*` and `~/.codex/skills/*` symlinks that resolve into a template `.claude/skills|skills` tree, listing them first; prints the superpowers/github marketplace commands (does not vendor them).
- `at init [--with-tasks --with-artifacts --with-workbooks --with-repos]`: writes the seed (§6) into the cwd repo; never clobbers owned files; idempotent.
- `at migrate [--keep-tasks|--no-tasks] [--dry-run]`: for a legacy downstream. Preconditions: clean tree, on default branch. Steps: create `backup/pre-plugin-migration-<date>` branch; `git remote remove template`; delete `_base/`, `playbooks/`, `skills/` (only if it's the template tree — refuses if non-template files are present, e.g. edge_node's zombie `.py` are moved back/deleted explicitly), `.claude/skills/`, `.agents/skills/`, `.agents/skill-library.json`, `.agents/skills.enabled.json`, `.claude-plugin/`, `.claude/hooks/`, `.claude/agents/` (only files identical to a known template version), `CONTEXT.md` if it is the template stub, template-boilerplate blocks in `AGENTS.md`/`README.md` (only exact known blocks); strip the `# BEGIN agents-template merge rules` block from `.gitattributes` and `git config --unset merge.template-keep-*`; rewrite `.claude/settings.json` (drop hooks pointing at `.claude/hooks`, add marketplace/enabledPlugins/deny); then `at init` with flags inferred (tasks if `docs/tasks_manager/_todos` exists, etc.); then `at doctor`; prints a summary and (with `--commit`) commits.
- `at doctor`: CLAUDE.md imports AGENTS.md; AGENTS.md ≤ 200 lines and no `TODO-FILL` placeholders; no `_base/`, `playbooks/`, template `skills/` left; plugins enabled in `.claude/settings.json`; if `docs/tasks_manager` present → `at ledger check`; warns on task files > 400 lines without an `_logs/` pointer; exit 1 on errors, 0 with warnings.
- `at ledger sync|check|rotate-log`, `at reserve <todo|inbox> …`, `at repos-check`: thin wrappers over `plugins/agents-tasks/skills/task-ledger/scripts/*`. Resolution order for the agents-tasks root: `$AT_TASKS_ROOT` if set; `<core-root>/../agents-tasks` (dev checkout and Codex marketplace layout `plugins/<name>/`); newest `<core-root>/../../agents-tasks/*/` (Claude cache layout `<marketplace>/<plugin>/<version>/`); else a clear error naming the flag to install `agents-tasks`.

## 8. Task ledger slimming (agents-tasks)

- Required fields: `Task ID`, `Type`, `Area`, `Status`, `Priority`, `Created`, `Updated`, `Source`. Optional (validated only when present): `Repos`, `Autonomy`, `Last executed`, `Target date`, `Deadline`, `Owner`, `Blocked by`, `Spec refs`, `Source ref`. Existing files (redmesh 154, edge_node 23) remain valid unchanged.
- Completion harvest + completion summary: still recommended in `complete-task`; the archive check downgrades a missing harvest from error to warning.
- Execution-log offloading: convention + tooling. `at ledger check` warns when a task file exceeds 400 lines or its `## Execution log` exceeds 200 lines; `at ledger rotate-log <ID>` moves the log body to `docs/tasks_manager/_logs/<ID>.md` and leaves a pointer line. `execute-plan`/`complete-task` mention it.
- Roadmap horizons optional: area pages' generated block lists active tasks by status when a horizon is empty instead of "_No tasks._".
- Hooks keep matching `docs/tasks_manager/**` (decision 5).
- `todo-convention.md` shrinks accordingly (target ≤ 350 lines) and moves to `task-ledger/references/`.

## 9. Downstream AGENTS.md routing table (seed) — the contract in ≤ 200 lines

Rows point at skills by name; e.g. "Implement a tracked task → `execute-plan`, `task-ledger`", "Security-sensitive change → `security-review-owasp`", "Branch/commit/push question → `git-discipline`", "Multi-repo work → `cross-repo-feature` / `.config/repos.project.md`", "Durable notes → `knowledge-base`", "Repeatable workflow → `workbook`", "Large/generated artifacts → `artifacts-registry`", "Delegating to subagents → `subagent-protocol`". Everything the old `_base/AGENTS.md` said beyond tier 0 lives in those skills' bodies or references.

## 10. Rollout

Phase 0 — quick fixes in every downstream (safe under any approach): add `CLAUDE.md` (`@AGENTS.md`); nothing else (the rest is superseded by migration).

Phase 1 — upstream restructure (this repo), tag `v1.0.0`; verify with `claude plugin validate`, `claude plugin details`, hook tests, ledger tests, `at init`/`at migrate` integration test on scratch copies of a light and a heavy downstream; install from the local checkout into both harnesses and confirm skills/hooks/agents appear.

Phase 2 — migrate ratio1 hubs: redmesh → edge_node → infra with `at migrate` (tasks on), fill their `AGENTS.md` project sections from existing README/`.config`, run `at doctor` + `at ledger check`, commit on master (their convention). edge_node also: delete zombie `skills/*.py`, delete the six leaked template-dev plans from `docs/_plans`.

Phase 3 — light consumers: bootstrap_work, models_playground, project_technical_writing, project_fl_godfather (`at migrate --no-tasks`); learning_project_vi, ubuntu-setup (`git remote remove template` + `at init`); `at bootstrap --clean-global-skills` to repoint global skills.

Phase 4 — later: agent `memory:`/`effort`/`isolation`, `.claude/rules` path-scoping experiments, research snapshot refresh.

## 11. Testing

- `plugins/agents-core/hooks/tests/test-hooks.sh` (existing 43 cases + new apply_patch cases + sensitive-path fixes) — must pass.
- `scripts/tests/test_sync_todo_ledgers.py` — new pytest-free unittest: fixture ledger with (a) legacy full-field task, (b) minimal-field task, (c) empty roadmap horizons, (d) oversized log → expected outputs/warnings.
- `scripts/tests/test-init-migrate.sh` — creates a scratch git repo from a tarball copy of `models_playground` and `project_r1_redmesh` (read-only source), runs `at migrate --commit`, asserts tree shape, `at doctor` exit 0, `at ledger check` exit 0.
- `claude plugin validate plugins/agents-core` etc. and `claude plugin validate .` (marketplace) — exit 0.
- `scripts/build.py --check` — generated files up to date.
- Manual: `claude plugin marketplace add <local checkout>`, install, `/context` shows the seed AGENTS.md via CLAUDE.md, `/agents-core:tdd` invocable, hooks block `git push --force`; Codex: `codex plugin marketplace add <local checkout>`, `codex plugin add agents-core@agents-template`, `$tdd` visible, hook trust prompt appears once.

## 12. Risks and mitigations

- **Skill listing budget in Claude (1% of context)** — 16 core skills ≈ 1–1.5k tokens; tasks +24. Mitigate: keep descriptions tight; `disable-model-invocation` on side-effect skills; agents-tasks only where used.
- **Codex plugin enablement is user-level, not per-repo** — acceptable; per-repo selection is a Claude feature. Document.
- **Path references in existing task files/commit bodies to `_base/scripts/...`** — history only; the two AGENTS.md rules in redmesh that cite them are rewritten during migration.
- **`at migrate` is destructive** — dry-run default output, backup branch, refuses on dirty tree, deletes only recognised template content.
- **Codex `apply_patch` payload for sensitive-write hook** — new code path, covered by tests.
- **Version pinning drift between `plugin.json` and `marketplace.json`** — `scripts/build.py --check` + `claude plugin validate` in `scripts/tests`.
