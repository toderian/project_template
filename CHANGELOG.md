# Changelog

Notable changes to agents-template. All four plugins share the version of the repository.

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
