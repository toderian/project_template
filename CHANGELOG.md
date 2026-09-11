# Changelog

Notable changes to agents-template. All four plugins share the version of the repository.

## Unreleased

### Added

- The [caveman](https://github.com/JuliusBrussee/caveman) skill ships as a companion, installed
  from its own marketplace rather than vendored. `at bootstrap` and `at update` install or refresh
  it on the machine for each harness they touch (Claude as the `caveman@caveman` plugin, Codex as a
  global skill through `npx skills add`), and the seed `.claude/settings.json` enables it, so a
  downstream repo picks it up on its next `at init` and Claude Code installs it at the next session
  start. `at doctor` now checks every plugin the seed enables and warns when `node`, which the
  caveman hooks need, is missing. The seed routing table gains a row for it, so existing repos see
  the drift and adopt it through `agents-core:setup-project`. `at init` writes a local
  `.caveman.json` with a null `defaultMode` (inherits the user config, default `full`), which the
  seed `.gitignore` block ignores and `at migrate --commit` never stages, so switching it to `off`
  is a per-checkout edit that cannot be committed and a machine-wide opt-out is still honoured. Terse mode
  is session-wide in Claude and per-session (`$caveman`) in Codex. The companion is optional: a
  missing `npx` or a failed install is reported and never fails `at bootstrap` or `at update`, and
  `at doctor --codex` reports whether the Codex skill landed.

### Fixed

- `at` finds the installed `agents-tasks` seed through the cache next to its own plugin root, so
  `at init --with-tasks` works when the harness cache is not under `$HOME` (`CLAUDE_CONFIG_DIR`,
  `CODEX_HOME`).

## 1.2.1 — 2026-09-02

### Fixed

- Codex now receives generated `agents/openai.yaml` policy files for the ten skills whose Claude
  source frontmatter disables model invocation. Those skills remain explicitly invocable, but are
  no longer selected implicitly by either harness.
- Generated Codex roles preserve full `agents-core:<skill>` ids when translating references from
  Claude plugin-root paths, so role delegation can resolve the intended skill.
- `at` discovers installed plugins and the optional `agents-tasks` seed independently across Claude
  and Codex caches. Mixed installations, semantic version ordering, live-versus-stale cache display,
  and current Codex local/Git marketplace update flows are handled explicitly.
- `at doctor` keeps its repository-only default and adds strict `--claude`, `--codex`, and `--all`
  checks; `at seed-path` exposes the installed seed used to adopt routing updates.

### Changed

- Agent-facing documentation consistently uses full `plugin:skill` ids and documents the distinct
  Claude `/plugin:skill` and Codex `$plugin:skill` invocation forms, Codex hook trust, and `jq`.
- CI and releases run a hermetic Codex compatibility smoke covering plugin installation, all 71
  skills, ten invocation policies, six roles, hooks, updates, task capture, and ledger validation.
  CI tests the minimum supported Codex `0.147.0` and current Codex `0.152.1`; ordinary local checks
  still skip the live smoke when Codex is absent.
- Claude manifests, source hook declarations, slash invocation, and update behavior remain intact;
  the generated Codex additions are derived from the same existing sources.

## 1.2.0 — 2026-08-20

### Added

- `at update` — refresh the marketplace and update every plugin installed from it on this machine,
  with `--check` for a read-only report of what is installed and at which version. Plugins install
  per machine, and `at bootstrap` only ever *installed* them, so an existing machine had no update
  path short of running the harness commands by hand.
- `at doctor` reports routing-table drift: `AGENTS.md` is downstream-owned, so `at init` never
  touches it and skills added upstream stayed unrouted silently. Doctor now names the exact seed rows
  a repo is missing, and points at `/setup-project`.
- `setup-project` gains an adoption mode and `references/adopting-updates.md`: the steps for bringing
  a template update into a repo that already has a contract. Written as desired-state checks rather
  than a per-release changelog, so it works from any starting version and is safe to re-run.

## 1.1.0 — 2026-08-19

### Added

- `grilling` (agents-core): the reusable interview primitive — design tree, frontier, one round of
  numbered questions with recommended answers at a time. `grill-me` moves to agents-core and becomes
  a router over it; `write-a-prd`, `github-triage`, `planning-workflow`, `spec-workflow` and
  `task-spec-workflow` now invoke it instead of restating the technique.
- `domain-modeling` (agents-extras): the glossary/ADR half of `grill-with-docs`, now model-invoked so
  any skill can reach it. `grill-with-docs` becomes a router over `grilling` + `domain-modeling`.
- `wayfinder` (agents-tasks): charts an effort too big for one session as a map — one task file
  holding decision tickets as dotted sub-ids (`T-042.1`) — and resolves them one per session.
- `research` and `wait-what` (agents-core), `to-questionnaire` (agents-extras).
- `writing-for-agents` (agents-extras): how to write anything an agent reads — context pointers, the
  two loads, progressive disclosure, completion criteria, leading words, pruning. `write-a-skill`
  drops the prose advice it duplicated and keeps the marketplace mechanics.
- `codebase-design` (agents-core, + references/deepening.md): one home for the module / interface /
  adapter / depth / seam / leverage / locality vocabulary, the deep-vs-shallow model, the deletion
  test, the dependency categories and the replace-don't-layer testing rule. Six skills used these
  words; three defined "deep module" differently. `tdd/references/deep-modules.md` and
  `interface-design.md` are absorbed into it.

### Fixed

- **`diagnose` referenced a minimised repro that no phase produced.** Phase 2 is now
  "Reproduce + minimise" and produces it. Phase 1 gained a real completion criterion (one command,
  already run, red-capable / deterministic / fast / agent-runnable) in place of "a loop you believe
  in", plus a `## Redact` section and a bundled `scripts/hitl-loop.template.sh`.
- **`github-triage` poisoned its own dedup store.** An enhancement closed as `wontfix` because it is
  *already implemented* is no longer written to `.out-of-scope/`, which is read back as the record of
  prior *rejections*. Triage also gained a redundancy check and an AI disclaimer on posted comments.

### Changed

- `todo-convention.md` documents the optional `## Tickets` section used by wayfinder maps, and the
  two layout rules that keep ticket state from leaking into task state.
- `vertical-slicing.md` gains the wide-refactor exception (expand → migrate → contract), reaching
  `prd-to-plan`, `prd-to-issues` and `prd-to-todos` from one file.
- `ubiquitous-language` now writes into `docs/resources/CONTEXT.md` using `domain-modeling`'s format
  instead of maintaining a competing root `UBIQUITOUS_LANGUAGE.md`; it keeps its distinct
  retrospective/batch trigger. Downstream repos with an existing `UBIQUITOUS_LANGUAGE.md` should fold
  it into the glossary.
- `tdd` confirms the seams tests are written at and names the tautological-test anti-pattern;
  `handoff` redacts secrets and personal data; `improve-codebase-architecture` scopes its search by
  git-log hot spots and screens with the deletion test.
- Skills adapted from `mattpocock/skills` now name that provenance in `metadata.source`.

### Known follow-ups

- `prototype` predates upstream's redesign (logic prototypes as one shareable HTML file; a prototype
  kept on a throwaway branch rather than deleted).
- `github-triage` does not treat external PRs as a request surface.
- No lint enforces the `AGENTS.md` skill rules (name/description/line limits, README skill counts);
  today they hold, but only by hand.

## 1.0.1 — 2026-08-19

Fixes found by actually migrating nine real downstream repositories with `at migrate`,
plus the rollout itself.

### Fixed

- `at migrate --allow-untracked` could delete untracked files that lived *inside* a tree
  it removes (a wholly-untracked ancestor directory, e.g. `?? .claude/`, hid a removal
  target such as `.claude/hooks/` from the leak guard). Containment is now checked in
  both directions.
- `at migrate --commit` used `git add -A` internally in one path, which could sweep
  untracked content into the migration commit; it now stages only the exact paths it
  touched (`git add -u` plus explicit adds), force-added so a downstream's own
  `.gitignore` can't cause a silent partial commit, and rolls back cleanly if the leak
  guard trips.
- `at migrate` on a repo whose untracked path collides with a file the plugin itself
  manages (e.g. a hand-edited untracked `.codex/agents/*.toml`) now **adopts** it
  (backs the old content up to `.no-commit/pre-migration/`, then proceeds) instead of
  silently overwriting it or refusing after the tree was already rewritten.
- `at bootstrap --clean-global-skills` only flagged a global skill symlink as stale if
  its target repo *still had* `_base/`/`playbooks/`. Once a repo is migrated those
  directories are gone, so the symlink is genuinely dangling but was invisible to the
  old check — it now flags any symlink whose target no longer exists, in addition to
  the pre-migration case.
- `scripts/release.sh` rolled its version bump back with `git checkout -- .`, which
  restores the worktree but not the index; a commit failure after `git add -A` could
  leave the bump staged. Rollback now restores both.

### Rollout

Migrated to the plugin layout: `project_r1_redmesh`, `project_r1_edge_node`,
`project_r1_infra`, `bootstrap_work`, `models_playground`, `project_fl_godfather`,
`project_technical_writing` (its downstream-authored `google-docs-refine` skill was
adopted into `agents-personal` first, then dropped from the downstream copy).
`learning_project_vi` was found not to be a consumer of this template (its `template`
remote points elsewhere). `ubuntu-setup` has real in-progress uncommitted work and was
left untouched pending the owner's own commit/stash. Every migration created a
`backup/pre-plugin-migration-<timestamp>` branch before changing anything.

## 1.0.0 — 2026-08-18

The repository stops being a git-merged monolith and becomes a **plugin marketplace plus a
thin seed**. Design: [`docs/specs/2026-08-18-plugin-restructure-design.md`](docs/specs/2026-08-18-plugin-restructure-design.md).
Upgrading an existing downstream: [`docs/migration.md`](docs/migration.md).

### Added

- **Marketplace `agents-template`** with four plugins under `plugins/`: `agents-core`
  (16 skills, 5 hooks, 6 subagent roles, the `at` CLI), `agents-tasks` (22), `agents-extras`
  (17), `agents-personal` (8). Installable natively by Claude Code
  (`.claude-plugin/marketplace.json`) and Codex (`.agents/plugins/marketplace.json`).
- **`at` CLI** (`agents-core`, bash + python3 stdlib): `bootstrap`, `init`, `migrate`,
  `doctor`, `version`, `ledger sync|check|rotate-log`, `reserve`, `repos-check`.
- **Seed** (`plugins/*/seed/`): the ~8 files a downstream owns — `AGENTS.md` (≤ 200-line
  contract with a routing table), `CLAUDE.md`, `.claude/settings.json`, managed `.gitignore`
  and `.gitattributes` blocks, Codex agent mirrors, and optional `docs/tasks_manager/`,
  artifacts, workbooks and repo-registry skeletons. Written once by `at init`, never merged.
- **Codex parity**: generated `.codex-plugin/plugin.json`, `hooks/hooks.codex.json` and
  `codex/agents/*.toml`; the sensitive-write hook now also understands `apply_patch`.
- **Tooling**: `scripts/build.py` (regenerates every derived file, `--check` in CI),
  `scripts/release.sh`, `scripts/install-pre-commit.sh`, `scripts/tests/run-all.sh` (hook,
  ledger, CLI and release tests), `.github/workflows/check.yml`.

### Changed

- Playbooks became **skills** that follow the Agent Skills spec: one `SKILL.md` (≤ 500
  lines) with `references/`, `assets/` and `scripts/` beside it; no wrapper-to-playbook hop;
  harness-neutral descriptions.
- Task ledger slimmed: fewer required fields, optional roadmap horizons, execution logs
  offloadable to `docs/tasks_manager/_logs/` via `at ledger rotate-log`.
- Third-party plugins (superpowers, github) are no longer vendored — install them from
  their own marketplaces.

### Removed

- The vendored template trees and their machinery: `_base/`, `playbooks/`, the three
  generated skill trees (`skills/`, `.claude/skills/`, `.agents/skills/`), the root plugin
  manifest, `.claude/hooks/`, `.claude/agents/`, `.codex/`, `.agents/skill-library.json`,
  `.agents/skills.enabled.json`, `scripts/convert_playbook.py`, and the `.gitattributes`
  merge-driver block. Updates now arrive through the plugin manager, not a `template` remote.
- Dedicated Antigravity/Gemini support (those harnesses read `.agents/skills` anyway).

### Verified

- End-to-end on Claude Code 2.1.234 and Codex CLI 0.147.0: `at bootstrap --local . --claude
  --codex --tasks --extras` installed all three plugins on the first try in both harnesses;
  `at init --all` + `at doctor` passed in a scratch repo; Claude Code's `block-dangerous-git.sh`
  hook blocked `git push --force` and both harnesses' agents saw `AGENTS.md` and the
  `agents-core` skills (`agents-core:tdd`, `$tdd`/`agents-core:execute-plan`). Details and
  token-cost numbers in `docs/meta/RESEARCH_SNAPSHOT.md` "Verification 2026-08-18".

Earlier history: `_base/CHANGELOG.md` before commit `a90cf0d` in git history.
