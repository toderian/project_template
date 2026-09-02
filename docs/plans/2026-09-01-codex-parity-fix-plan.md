# Codex parity repair and Claude-safe v1.2.1 release

**Status:** executing  
**Base revision:** `4569c07`  
**Repo:** `project_template`  
**Branch / work mode:** `master` / `default-branch`  
**Autonomy:** repo default L1; the user's explicit request authorizes the local v1.2.1 release commit
and tag; no push, publish, merge, or remote write is authorized.

## Goal

Restore current Codex compatibility for skill invocation policy, plugin updates, CLI resolution,
diagnostics, instructions, and compatibility tests while preserving Claude Code behavior.

## Phases

- [x] **Phase 1 — Codex skill policy generation and authoring contract.** Generate
  `agents/openai.yaml` from `disable-model-invocation: true`, safely detect/remove obsolete
  banner-owned outputs, update the generated-file table and skill-authoring doctrine in the same
  phase, add static contract tests, and keep Claude frontmatter intact.
- [x] **Phase 2 — Dual-harness `at` lifecycle.** Add per-harness inventory, capability-aware Codex
  updates, current Codex cache resolution, strict doctor modes, and `at seed-path`.
- [x] **Phase 3 — Harness-neutral instructions.** Normalize active skill references, fix the skill
  authoring doctrine, and document Codex hook trust, `jq`, diagnostics, and updates.
- [x] **Phase 4 — Live compatibility gates.** Add hermetic current/minimum Codex smoke coverage and
  validate skill, agent, hook, and task-recording behavior without making Codex mandatory for
  Claude-only contributors.
- [ ] **Phase 5 — Review and release.** Run full validation, two independent implementation reviews,
  address findings, update the changelog, and run `scripts/release.sh 1.2.1`.

## Acceptance criteria

- All 71 skills remain explicitly invocable in both harnesses.
- The 10 skills marked `disable-model-invocation: true` are also non-implicit in current Codex.
- Claude's flag, manifests, source hook declarations, update command sequence, and explicit slash
  invocation remain valid.
- `at update` succeeds on Claude-only, Codex-only, and mixed installations without invoking an
  absent or unconfigured harness.
- Plain `at` resolves from versioned Claude and Codex plugin caches.
- Plain `at doctor` remains backward-compatible; `--claude`, `--codex`, and `--all` add strict
  runtime checks.
- Task capture produces a valid inbox item and `at ledger check` / `at repos-check` pass.
- `python3 scripts/build.py --check`, `bash scripts/tests/run-all.sh`, Claude plugin validation, and
  the supported Codex smoke checks pass.
- All four plugins share version `1.2.1`, tag `v1.2.1` exists locally, and the worktree is clean.

## Checks

- `python3 scripts/build.py --check`
- `python3 scripts/tests/test_codex_compat.py`
- `bash scripts/tests/test-at.sh`
- `bash scripts/tests/test-codex-live.sh` when Codex is available
- `bash scripts/tests/run-all.sh`
- `claude plugin validate` for each plugin and the marketplace
- scratch-repo Claude and Codex task-capture/hook smoke

## Compatibility contract

- Minimum supported Codex: `0.147.0`; pinned current validation target: `0.151.0`.
- Claude and Codex installation inventories stay independent. Plain `at update` selects only
  configured harnesses; explicit harness flags fail actionably when unavailable.
- Codex Git marketplace update: run `codex plugin marketplace upgrade agents-template`, then
  idempotently `codex plugin add` each installed agents-template plugin and verify its cache payload.
- Codex local marketplace update: skip marketplace upgrade, idempotently `codex plugin add` each
  installed plugin, and verify its cache payload.
- Legacy Codex command capability is detected at runtime rather than inferred only from the version.
- Repository doctor checks are a separate function from optional harness runtime checks, so
  `at migrate` retains the plain repository-check behavior.
- Static Codex compatibility tests are mandatory in `run-all.sh` and CI. Live CLI smoke may skip for
  ordinary contributors only; release validation sets an explicit required mode where a skip fails.
- Generated `agents/openai.yaml` files carry a build banner. Removing the source flag makes normal
  build delete only the banner-owned orphan and makes `--check` report it stale; an unbannered file
  is never overwritten or deleted.

## Execution log

- **2026-09-01 — Started.** Resolved the pasted approved plan into five independently committable
  phases. No `.config/repos.project.md` exists, so the template-maintenance policy applies: work on
  `master`, the configured default branch. Effective autonomy is L1 for edits/checks/phase commits;
  the user explicitly authorized the plan's local release commit and tag. Base tree was clean at
  `4569c07`. No push is authorized.
- **2026-09-01 — Architecture review.** Independent xhigh review returned `REVISE` with no permanent
  blocker. Revised the plan to specify the exact Git/local Codex reinstall paths, minimum/current
  versions, generated-orphan lifecycle, doctor separation, phase-local Claude validation, and a
  non-skipping release smoke mode. Implementation may proceed against this revised contract.
- **2026-09-01 — Phase 1 complete.** `scripts/build.py` now generates ten banner-owned Codex
  invocation policies from the unchanged Claude flags, detects unowned conflicts, and reports or
  removes obsolete generated policies. Added six static compatibility tests and wired them into the
  local and CI gates; updated the source/generated and skill-authoring contracts in the same phase.
  Checks: build check passed; static compatibility 6/6 passed; all Claude plugin validations passed;
  full `run-all.sh` passed (54 hook, 9 ledger, 266 CLI, 29 release tests).
- **2026-09-02 — Phase 2 complete.** `at` now resolves the newest semantic cache across Claude and
  Codex, keeps live and cached inventories separate per harness, updates Codex through supported
  marketplace/reinstall commands, verifies the inventory-recorded payload, and exposes strict
  `doctor` selectors plus `seed-path`. Plain doctor and migration remain repository-only. The phase
  reviewer approved the corrected inventory, payload, and doctor boundaries. Checks: build and
  static compatibility passed; all Claude plugin validations passed; focused CLI 272/272 passed;
  full `run-all.sh` passed (54 hook, 9 ledger, 272 CLI, 29 release tests).
- **2026-09-02 — Phase 3 complete.** Active agent-facing prose now uses full, harness-neutral skill
  ids; user docs show `/plugin:skill` for Claude and `$plugin:skill` for Codex. Removed obsolete
  bare slash commands and nonexistent Codex role skills, routed task initialization through
  `at init --with-tasks`, switched update adoption to `at seed-path`, and documented `jq`, strict
  doctor selectors, update selectors, and Codex hook review/trust. The phase reviewer caught and
  approved a correction to `tidy-repo`'s seeded-directory claim. Checks: static compatibility 8/8
  passed; all Claude plugin validations passed; full `run-all.sh` passed (54 hook, 9 ledger, 272 CLI,
  29 release tests).
- **2026-09-02 — Phase 4 complete.** Added a hermetic no-login Codex smoke that installs all four
  plugins into a fresh home and validates inventory/cache shape, 71 skills, 10 explicit-only
  policies, six role files, hook manifest and allow/block behavior, cached `at` resolution, strict
  doctor, task capture, ledger validation, and repo-registry validation. CI requires it for Codex
  0.147.0 and 0.151.0; ordinary local suites skip without Codex, while real releases require the
  gate. Both pinned versions passed locally and the phase reviewer approved the gate boundaries.
  Checks: pinned Codex 0.147.0 passed; pinned Codex 0.151.0 passed; release mechanics 32/32 passed.
