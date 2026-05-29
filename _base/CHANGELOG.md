# Changelog (base)

BASE_VERSION: 2026.05.29.5

> This is `_base/CHANGELOG.md`: the changelog for **base-template** changes only.
> Downstream projects may keep their own `CHANGELOG.md` for changes they make on top of the template; the two files never overlap.

All template-relevant changes are recorded here so downstream projects can see what's coming in before running `git merge template/master`.

Format: reverse chronological. `BASE_VERSION` is the machine-readable base-template version currently
present in the checkout; bump it for every base-template change intended for downstream repos. Use
`YYYY.MM.DD.N`, where `N` starts at `0` for the first base change of that date. Each changelog entry
lists the date, a short description, and (where relevant) a **Downstream impact** line explaining what
a project pulling this in should expect — particularly merge conflicts, new conventions to follow, or
behavior changes.

This file is **upstream-owned**: do not edit it in a downstream project. It updates cleanly via `git fetch template && git merge`.

For exhaustive history, use `git log` against the `template` remote.

## Unreleased

### Allow post-completion squash of downstream task commits

`execute-plan` now keeps per-phase commits during execution and review, but explicitly allows
downstream repos to squash a completed task's own phase/review commits into one final task commit after
validation and review pass.

**Downstream impact:** behavior clarification. Agents should still create phase commits while working
so each step is reviewable and recoverable. After the task is done, they may squash only the commits
belonging to that task, preserve the phase/review/check summary in the final commit message, rerun
final checks, and avoid rewriting pushed/shared history without explicit user approval.

### Require branch policy check before execute-plan work

`execute-plan` now explicitly resolves repo scope and branch/work mode before implementation starts.

- The playbook reads and validates `.config/repos.project.md` when present.
- If task `Repos` metadata points at multiple repos, the agent must validate `.local/repos.map` before
  editing other checkouts.
- `default-branch` and `same-branch` modes forbid creating per-task branches.
- `task-branch` mode requires an explicitly named branch; the agent must ask before creating or
  switching when none is named.
- Template-inherited downstream repos default to same/default-branch execution when no repo registry
  exists.

**Downstream impact:** behavior clarification plus example update. Existing repos that use
`.config/repos.project.md` should review `Work mode` values: use `default-branch` or `same-branch` for
template-inherited downstream repos that should keep all execute-plan commits on the same
`main`/`master` branch. Use `task-branch` only for product repos that intentionally require per-task
branches.

### Clarify downstream format migration consent

Agents updating downstream repos from the template must now explicitly ask whether to migrate
downstream-owned files when a base update introduces or changes formats, seeded docs, task metadata,
project-slot files, or local setup conventions.

**Downstream impact:** documentation-only behavior clarification. Template merges still update
`_base/**` directly, but downstream-owned format migrations should be presented as a separate
user-approved follow-up step instead of being applied silently during the merge.

### Add template merge rules for downstream repos

Downstream projects can now install Git merge drivers and a managed `.gitattributes` block that encode
the template ownership split.

- New root `.gitattributes` managed block maps `_base/**` to `template-keep-upstream`.
- Downstream-owned files such as `AGENTS.md`, `README.md`, `PROJECT.md`, `CONTEXT.md`,
  `CHANGELOG.md`, `LICENSE`, `.config/repos.project.md`, root `docs/**`, and root `workbooks/**` map
  to `template-keep-local`.
- New `_base/scripts/setup-template-merge-rules.sh` configures the required local Git merge drivers and
  creates or refreshes the managed `.gitattributes` block.
- New `_base/scripts/template-merge-driver.sh` applies keep-local or keep-upstream only when Git's
  merge environment identifies refs under the `template` remote; ordinary project branch merges fall
  back to normal three-way file merging.
- `_base/scripts/check-template-update.sh` now validates these merge rules before running the rest of
  the post-merge checks.
- `_base/SETUP_INSTRUCTIONS.md`, `_base/README.md`, and `_base/AGENTS.md` now tell agents to install
  or verify merge rules before template pulls.

**Downstream impact:** after merging this update, run
`./_base/scripts/setup-template-merge-rules.sh`, commit `.gitattributes` if it changed, then run
`./_base/scripts/check-template-update.sh`. If a downstream project already has a root
`.gitattributes`, keep its project-specific rules outside the managed agents-template block. Future
template pulls should keep `_base/**` from upstream automatically and keep downstream-owned slot files
local only for template-remote merges; mixed paths such as `playbooks/`, `skills/`, and
`.claude/settings.json` still require human merge judgment.

### Add workbook and durable attachment conventions

The template now distinguishes reusable workbook bundles, raw knowledge staging, and long-lived
committed source documents.

- New `playbooks/conventions/workbook-convention.md` defines root `workbooks/` as the canonical home
  for workbook bundles.
- `_base/workbooks/README.md` seeds a root workbook index. `_base/scripts/seed-docs.sh` now copies it
  to `workbooks/README.md` without overwriting downstream files.
- Each workbook lives in its own folder, may be nested into collections, keeps scripts/support files
  local, and declares workbook reuse through README `Depends on` paths.
- `docs/tasks_manager/_inbox/` remains the raw idea/work-item inbox.
- `docs/resources/_inbox/` remains the raw knowledge-file staging area for `/distill-knowledge`;
  non-Markdown files there stay ignored by default unless a downstream project intentionally changes
  that policy.
- Long-lived committed `.docx`, PDFs, spreadsheets, diagrams, and similar source documents now have a
  durable home under `docs/resources/<area>/attachments/` with nearby Markdown metadata or an
  attachment index documenting purpose, provenance, area or owner, and update guidance.

**Downstream impact:** run `_base/scripts/seed-docs.sh` to create `workbooks/README.md` in existing
repos. Add or move workbook bundles under root `workbooks/`, declare reuse in each workbook README
`Depends on` section, keep raw uploads awaiting distillation in `docs/resources/_inbox/`, and move
long-lived committed binaries to `docs/resources/<area>/attachments/` with Markdown metadata. Keep the
existing fetch-only `template` remote before future updates:
`git remote add template git@github.com:toderian/project_template.git` and
`git remote set-url --push template DISABLE`. No new remote mechanism is introduced.

### Expand roadmap horizons

The task roadmap convention now uses five placement horizons: `Urgent`, `Now`, `Next`, `Later`, and
`Someday`.

- `docs/tasks_manager/_roadmap.md` is still placement-only; task `Priority` remains `high`, `medium`,
  or `low` metadata.
- Raw `I-NNN` inbox IDs may appear only in `Someday`; task IDs may appear in any horizon.
- `_base/scripts/sync-todo-ledgers.sh` now recognizes all five horizons and generates matching area
  page and overview columns.
- Horizon soft thresholds are documented review guidance only, not script or CI validation rules.

**Downstream impact:** after merging this update, run `_base/scripts/sync-todo-ledgers.sh` to refresh
generated area pages and `docs/areas/_overview.md`. Move any raw inbox references from `Later` to
`Someday`, or promote them to tasks before placing them elsewhere.

### Move repo registry to `.config/repos.project.md`

The committed downstream repo registry now lives under `.config/` and uses a Markdown extension.

- `_base/repos.project.example` was renamed to `_base/repos.project.example.md`.
- `_base/scripts/check-repos-config.sh` now validates `.config/repos.project.md` only.
- Root-level `repos.project` and `repos.project.md` are no longer supported registry paths.
- `.local/repos.map` stays unchanged as the gitignored machine-local checkout map.

**Downstream impact:** projects with a committed root `repos.project` or `repos.project.md` must
migrate with `mkdir -p .config && git mv <legacy-file> .config/repos.project.md`, then run
`_base/scripts/check-repos-config.sh`. Fresh multi-repo projects should copy
`_base/repos.project.example.md` to `.config/repos.project.md` and keep `.local/repos.map` local.

### Add operational runbook storage convention

Repeated agent-assisted operational procedures now have a sanitized committed home plus ignored local
bindings.

- New `playbooks/conventions/runbook-convention.md` defines committed runbooks under
  `docs/resources/<area>/runbooks/<scenario-slug>.md`.
- New `playbooks/templates/runbook.template.md` and `playbooks/templates/runbook.local.template.md`
  provide starter shapes for committed procedures and local bindings.
- `_base/docs/resources/global/runbooks/` is seeded for cross-cutting runbooks.
- Knowledge-base docs now tell agents to search runbooks before asking repeated SSH, setup, service,
  or debugging questions, while keeping real hostnames, account names, paths, and reusable local values
  in `.local/runbooks/`.
- The template `.gitignore` also ignores `.no-commit/`, `.temp/`, `.tmp/`, `temp/`, and `tmp/` for
  local scratch or intentionally uncommitted material.

**Downstream impact:** run `_base/scripts/seed-docs.sh` to seed
`docs/resources/global/runbooks/` in existing repos. Use committed placeholders in runbooks and keep
real values in ignored `.local/runbooks/<scenario-slug>.local.md` files. Move scratch files that must
not be committed under `.no-commit/`, `.temp/`, `.tmp/`, `temp/`, or `tmp/`.

### Add one-command template update check

Downstream repos now have a single read-only verification command after pulling or merging template
updates.

- New `_base/scripts/check-template-update.sh` prints `BASE_VERSION`, syntax-checks template shell
  scripts, validates skills, bundled Codex plugin manifests, repo registry/task `Repos` metadata,
  optional local checkout maps, task ledgers, and git whitespace.
- The script validates `.local/repos.map` automatically when present, or requires it with `--local`.
- Setup docs and README now point downstream users at this command as the standard post-merge check.

**Downstream impact:** after `git merge template/master`, run
`./_base/scripts/check-template-update.sh`. Run `./_base/scripts/setup-agents.sh` separately when you
want to refresh local agent runtime installs.

### Add optional repo registry and local checkout map convention

Projects can now opt into stable repo slugs without committing machine-local paths.

- New `_base/repos.project.example` provides the scaffold for downstream-owned `repos.project`.
- New `_base/repos.map.example` documents the gitignored `.local/repos.map` checkout map format.
- New `_base/scripts/check-repos-config.sh` validates the optional registry, task `Repos` metadata, and
  local checkout paths in `--local` mode.
- Task-producing playbooks can fill optional `Repos` metadata when inferable from `repos.project`.
- Cross-repo docs now use `<repo-slug>:<repo-relative-path>` references and keep absolute local paths
  out of committed docs.

**Downstream impact:** no required action for single-repo projects. Multi-repo projects can copy
`_base/repos.project.example` to `repos.project`, commit it, copy `_base/repos.map.example` to
`.local/repos.map`, and run `_base/scripts/check-repos-config.sh --local`.

### Add timestamped report artifact convention

Rerunnable agent reports now have a stable home and unique filenames.

- New `playbooks/conventions/generated-artifacts.md` distinguishes stable project artifacts from
  rerunnable reports, audits, inventories, and snapshots.
- `/init` seeds `docs/resources/_reports/` for report snapshots.
- `/tidy-repo` now writes each migration report under
  `docs/resources/_reports/tidy-repo/<timestamp>_tidy-report.md` and includes a delta from the previous
  tidy report when one exists.
- Saved `/audit-todos` reports use the same `_reports/<workflow>/` convention.

**Downstream impact:** future tidy reports no longer overwrite the old single-report location. Run
`/init` or `_base/scripts/seed-docs.sh` to seed `docs/resources/_reports/` in existing repos.

### Move template plugins under `_base/plugins`

Template-owned bundled plugins no longer live in the root `plugins/` directory.

- Moved bundled Codex plugin packages and plugin installers under `_base/plugins/`.
- `_base/scripts/setup-agents.sh` now calls plugin installers from `_base/plugins/`.
- `_base/scripts/check-codex-plugins.sh` validates `_base/plugins/`.
- Codex marketplace entries are refreshed to point at `./_base/plugins/<name>` instead of the old
  root `./plugins/<name>` paths.
- Root `plugins/` is left for downstream project-owned plugin/tooling content.

**Downstream impact:** after pulling template updates, run `./_base/scripts/setup-agents.sh` so Codex
plugin symlinks and marketplace entries refresh to `_base/plugins`. Use
`./_base/plugins/install-codex-plugins.sh`, `./_base/plugins/install-claude-plugins.sh`, or
`./_base/plugins/bootstrap-third-party.sh` only for manual/debugging setup.

### Move template scripts under `_base/scripts`

Template-owned operational scripts no longer live in the root `scripts/` directory.

- Moved agent setup, Claude skill linking, docs seeding, work-item reservation, and task-ledger sync
  scripts under `_base/scripts/`.
- Updated playbooks, setup docs, generated seed docs, and agent instructions to use the new paths.
- Root `scripts/` is left for downstream project-owned scripts.

**Downstream impact:** after pulling template updates, use `./_base/scripts/setup-agents.sh` for the
agent refresh and `_base/scripts/sync-todo-ledgers.sh` / `_base/scripts/reserve-work-item.sh` for task
system operations. Existing downstream-owned files under `scripts/` are no longer in the template's
namespace.

### Clarify Codex skill invocation

Codex setup was working but users could still reasonably try `/tidy-repo` and hit an "Unrecognized
command" error because Codex skills are model-visible skills, not TUI slash commands.

- `_base/scripts/setup-agents.sh` now prints a Codex invocation note after setup.
- `_base/README.md`, `_base/SETUP_INSTRUCTIONS.md`, and `_base/AGENTS.md` now explain that Codex users
  should use natural language or `$skill-name` (for example `$tidy-repo`) instead of `/skill-name`.

**Downstream impact:** after running `./_base/scripts/setup-agents.sh` and restarting Codex, invoke template
skills with prompts like `tidy this repo` or `$tidy-repo`, not `/tidy-repo`.

### Add one-command agent setup

Setup after pulling template updates now has a single default command:

- New `_base/scripts/setup-agents.sh` validates the skill catalog, installs or refreshes Codex skills,
  installs or refreshes Codex plugins, links Claude Code skills globally, and installs or refreshes
  Claude Code plugins. It defaults to both runtimes, supports `--codex-only` and `--claude-only`, and
  checks selected agent CLIs before changing runtime install state.
- `_base/README.md`, `_base/SETUP_INSTRUCTIONS.md`, and plugin docs now point users at the one-command
  setup path first, with lower-level installers kept as manual/debugging escape hatches.

**Downstream impact:** after pulling template updates, run `./_base/scripts/setup-agents.sh` and restart
Codex and Claude Code instead of remembering separate skill/plugin installer commands.

### Add active-task audit workflow

The task system now has a report-only active-task health check:

- New `/audit-todos` audits `docs/tasks_manager/_todos/` against current code, tests, docs, roadmap,
  generated ledgers, area pages, archived task evidence, and `docs/resources/`.
- The audit classifies tasks as `keep`, `needs-update`, `appears-done`, `cancel-or-close`,
  `split-follow-up`, or `needs-user-decision`.
- Recommendations must be evidence-based; age alone is never enough to close or cancel work.
- The audit does not mutate files by default. Closeout, cancellation, follow-up capture, task creation,
  and sequencing cleanup stay delegated to `/complete-task`, `/capture-idea`, `/add-task`, and
  `/roadmap`.

**Downstream impact:** re-run skill installers to pick up `/audit-todos`. Use it periodically before
large backlog or roadmap cleanup sessions.

### Add raw knowledge inbox and distillation workflow

The docs-primary knowledge base now has a raw-source ingestion lane:

- `docs/resources/_inbox/` is the raw drop zone for documents, exports, notes, transcripts, and other
  source material waiting to be processed.
- `docs/resources/_digests/<area-or-bucket>/` stores curated Markdown digests segregated by area, with
  `global/`, `_cross-area/`, and `_uncategorized/` seeded as default buckets.
- New `/distill-knowledge` extracts the important source-backed facts into a digest, then promotes only
  stable facts into canonical knowledge files such as `CONTEXT.md`, area summaries, dependency graphs,
  contracts, or component contexts.
- Non-Markdown raw inbox files are ignored by default so large, binary, proprietary, or sensitive
  sources are not committed by accident.

**Downstream impact:** run `/init` or `_base/scripts/seed-docs.sh` to seed the raw knowledge inbox and digest
folders. Re-run skill installers to pick up `/distill-knowledge`.

### Define branch and checkpoint-commit policy

The base agent contract now distinguishes two repo modes:

- downstream template-maintenance repos should work directly on the default branch (`main` or
  `master`) and avoid ad hoc feature/subbranches;
- working/product repos should use the explicit task branch named by the user, task file, issue, or
  project convention at task start.

Agents should commit each coherent, reviewable set of modifications, stage only related files, run
relevant checks where possible, and still avoid pushing unless explicitly asked.

**Downstream impact:** downstream projects pulling this in get a clearer default branch policy for
agents. Product repos that want task branches should name the branch at task start or encode the branch
convention in project-specific `AGENTS.md`.

### Add generic cross-repo area and feature-contract workflows

The docs-primary knowledge base now has a generic cross-repo workflow family:

- `/define-area` creates or refreshes durable area knowledge under `docs/resources/<area>/`, including
  participant repos, dependency graphs, install modes, runtime dependencies, and known docs.
- `/cross-repo-feature` writes concrete feature contracts under
  `docs/resources/<area>/contracts/<feature-slug>.md`, covering repo responsibilities, boundaries,
  compatibility, rollout order, and verification.
- `/refresh-context` now treats area summaries, dependency graphs, feature contracts, and component
  contexts as one refreshable area knowledge set.
- `/init` seeds `docs/resources/global/summary.md`; generated task-status pages remain under
  `docs/areas/`.
- The seeded `docs/resources/CONTEXT.md` glossary now uses placeholders only, so downstream projects do
  not inherit example domain language.

**Downstream impact:** re-run skill installers to pick up `/define-area` and `/cross-repo-feature`.
Run `/init` or `_base/scripts/seed-docs.sh` to seed the generic global area summary without overwriting
existing docs.

### Make docs/ the primary knowledge-base home and add `/refresh-context`

Knowledge-base docs now default to the seeded `docs/` layout instead of scattered glossary/component
files:

- `docs/resources/CONTEXT.md` is the primary domain glossary. The top-level `CONTEXT.md` template is
  now a small pointer/fallback.
- Area architecture summaries live at `docs/resources/<area>/summary.md`; generated task status stays in
  `docs/areas/<area>.md`.
- Component contexts live under `docs/resources/<area>/components/<component-slug>/CONTEXT.md`, with
  exact source paths recorded in their headers.
- `CONTEXT_DOCS_DIR` is now documented as an external-storage escape hatch for repos that should not
  receive local docs, not as the normal template layout.
- New `/refresh-context` checks code, task logs, completion harvests, and recent changes for drift,
  then updates stale glossary, area, and component docs only when evidence supports the change.
- `/init` and `_base/scripts/seed-docs.sh` now seed the docs-primary glossary, a global area summary, and a
  top-level pointer when one is missing.

**Downstream impact:** run `/init` or `_base/scripts/seed-docs.sh` to pick up the new seeded docs without
overwriting existing project files. Move future glossary edits to `docs/resources/CONTEXT.md` and
future component context to the docs-primary component path. Re-run skill installers to pick up
`/refresh-context` and refreshed descriptions.

### Tighten runtime setup docs and guardrail references

Follow-up consistency fixes from a Claude/Codex parity review:

- `_base/README.md` now reflects that Claude Code can use `_base/plugins/install-claude-plugins.sh`, lists the
  full Claude agent set in the repo tree, and points Codex implementer/reviewer behavioral skills at
  their bucketed source paths.
- `_base/SETUP_INSTRUCTIONS.md` now describes the bucketed Codex skill source layout, flat install
  destination, idempotent installer summary, and `_base/README.md` as the skills catalog.
- `/triage-inbox` trigger text now says `triage inbox` instead of generic `triage`, reducing overlap
  with issue triage skills.
- Git guardrails docs and wrappers now point at the real bucketed hook script path.
- Claude subagent prompts now keep domain verdicts (`PASS`/`FAIL`, `PROCEED`/`REVISE`/`BLOCKED`) as
  separate verdict lines while using the shared `DONE` / `DONE_WITH_CONCERNS` / `BLOCKED` status
  vocabulary for parent routing.
- Codex subagent guidance now accounts for environments that expose multi-agent tools while preserving
  sequential behavioral-skill fallbacks when they do not.
- The pre-implementation review gate is now explicitly bounded: routine tasks can log concise
  codebase-first current-state and plan-freshness notes, while full researcher/plan-critique workflows
  are reserved for larger, stale, high-risk, or externally current work.
- `_base/plugins/install-claude-plugins.sh` now distinguishes GitHub marketplace repos from local Claude
  marketplace aliases, fixing Superpowers installation to use `superpowers@superpowers-marketplace`.
- New `_base/scripts/check-codex-plugins.sh` validates bundled Codex plugin manifests, plugin skill
  files, app JSON, optional MCP JSON, and declared interface assets. `_base/plugins/install-codex-plugins.sh`
  runs it before changing local install state.
- `_base/scripts/gen-skills-table.sh --check` now supports read-only table validation, and
  `_base/scripts/check-skills-sync.sh` uses that mode instead of regenerating and restoring files.

**Downstream impact:** documentation and setup-validation changes only. Re-run skill installers if you
want the refreshed `/triage-inbox` description in global Claude/Codex skill directories. Re-run
`./_base/plugins/install-claude-plugins.sh` if you installed the older Superpowers marketplace entry.

### Add task-system quickstart and triage discovery gate

Documentation-only update to make the task system's golden path and triage expectations explicit:

- New `playbooks/conventions/task-system-quickstart.md` explains the `/init` -> `/capture-idea` ->
  `/triage-inbox` discovery gate -> `/roadmap` -> pre-implementation gate -> implement/execute ->
  `/complete-task` -> `_base/scripts/sync-todo-ledgers.sh --check` flow.
- `/triage-inbox` now requires a discovery gate before promotion decisions: inspect inbox ideas, active
  and archived tasks, roadmap, area pages, resources, context docs, and likely code/tests; classify
  duplicates, already tracked work, already implemented work, stale ideas, related work, and genuinely
  new work before creating tasks.
- `inbox-convention.md`, `todo-convention.md`, `/add-task`, `/prd-to-todos`, `/roadmap`,
  `_base/README.md`, and `_base/AGENTS.md` now point agents toward the same source-of-truth split: task
  files own detail/status, roadmap owns placement, raw inbox IDs only park in `Later`, and ledgers/area
  pages are generated.
- `_base/scripts/sync-todo-ledgers.sh --check` now enforces the same roadmap rule by rejecting raw inbox IDs
  in `Now` or `Next`, validates inbox status/archive placement, and validates area registry pages
  against `docs/areas/<area>.md`.

**Downstream impact:** no migration, commands, metadata fields, or file formats changed. Agents should
follow the new `/triage-inbox` discovery gate before promoting captured ideas into tasks. Projects with
raw `I-NNN` inbox IDs in roadmap `Now` or `Next` should either move them to `Later` or promote them
with `/triage-inbox`. Projects with terminal inbox files still in `_inbox/`, live `new` inbox files in
`_inbox_archived/`, or area pages outside `docs/areas/<area>.md` should reconcile those before relying
on strict validation.

### Harden idea-to-task validation and completion flow

The task system keeps the permissive sync path for recovery, but now has strict read-only validation
for CI and agent handoff:

- `_base/scripts/sync-todo-ledgers.sh --check` fails on duplicate IDs, malformed metadata, status/archive
  mismatches, unregistered areas or prefixes, bad roadmap references, stale generated ledgers/area
  blocks, and archived tasks without explicit completion harvest/summary.
- `_base/scripts/reserve-work-item.sh` atomically reserves inbox and task IDs before agents fill the file.
- New `/complete-task` workflow closes out acceptance checks, final execution logs, harvest, summary,
  archive move, sync, and strict validation.
- Roadmap docs are now placement-only; task files remain authoritative for status and phase detail.
- Durable implementation plans now live under `docs/_plans/`.
- `_base/scripts/seed-docs.sh` replaces GNU-specific no-clobber copy snippets for setup/init docs seeding.

**Downstream impact:** projects using the task manager should run `/init` or `_base/scripts/seed-docs.sh` to
pick up `docs/_plans/`, re-run skill installers for `/complete-task`, and use
`_base/scripts/sync-todo-ledgers.sh --check` in CI or before handing tasks to another agent.

### Add Areas / Resources / Archive task system and `/add-task`

The task system now supports area-specific task ID prefixes without adding a Projects layer:

- `docs/tasks_manager/_areas.md` now uses `Area | Prefix | Description | Page`; `T` is reserved for
  global/default/cross-area tasks.
- Task filenames are now `<PREFIX>-NNN-<TYPE>_<desc>.md` with per-prefix counters. Inbox IDs remain
  `I-NNN`, and tasks stay flat under `docs/tasks_manager/_todos/`.
- The legacy reference seed folder is replaced by `_base/docs/resources/`, and the seed layout now includes
  `_base/docs/areas/` and `_base/docs/archive/`.
- `_base/scripts/sync-todo-ledgers.sh` now regenerates `_active.md`, `_done.md`, `docs/areas/_overview.md`,
  and marker-delimited generated status blocks in `docs/areas/<slug>.md`; it also reports missing or
  ambiguous roadmap references instead of guessing.
- New `/add-task` productivity skill creates a full task directly with area/prefix/ID assignment,
  priority, phases, acceptance criteria, related tests, completion harvest placeholders, sync, and
  optional roadmap placement.
- Starting an existing task now has a pre-implementation review gate: record a researcher current-state
  review and a plan-critic freshness/applicability review in the task execution log before code edits.
- Completion harvest is required before archive: resource updates or `None`, area updates or `None`,
  follow-ups or `None`, and notable decisions/deviations or `None`. Claude hooks validate the archive
  fields and area-prefixed filenames.

**Downstream impact:** downstream projects using the task system should migrate existing task filenames
from `T-NNN-...` only where area-specific prefixes are desired; `T` remains valid for global/default
work. Rename any legacy project reference folder to `docs/resources/` if present, run `/init` to seed `docs/areas/` and
`docs/archive/`, then run `_base/scripts/sync-todo-ledgers.sh`. Re-run skill installers to pick up
`/add-task`.

### Tighten downstream setup checks and refresh Codex plugin symlinks

Fixed a few template-hygiene issues that affected newly seeded projects and repeat installs:

- **`_base/SETUP_INSTRUCTIONS.md`** now lists `jq` as a Claude Code hook prerequisite, because the
  shipped hooks parse tool input JSON with `jq`.
- The downstream `AGENTS.md` check now verifies the `_base/AGENTS.md` auto-load directive and fails if
  the `_None for the base template itself._` placeholder remains under Project-specific overrides.
  The previous `grep -A3 ... | tail -1` check could pass on a blank line.
- **`_base/plugins/install-codex-plugins.sh`** now refreshes existing plugin symlinks when they point at stale
  locations, while still preserving non-symlink targets. This mirrors the Codex skill installer.

**Downstream impact:** re-running `./_base/plugins/install-codex-plugins.sh` now repairs stale local plugin
symlinks. Fresh setup agents should have `jq` available for Claude Code hook support. The active
manifest and `project.env` behavior are unchanged.

### Route the domain glossary through `CONTEXT_DOCS_DIR` + document the knob

`describe-component` already let you redirect component `CONTEXT.md` docs out of a repo you don't own
(via `CONTEXT_DOCS_DIR` in `project.env`). `grill-with-docs` did not. Now both honor the same escape
hatch, while the normal template layout remains docs-primary.

- **`grill-with-docs`** reads `CONTEXT_DOCS_DIR` only when set; otherwise it uses the docs-primary
  glossary at `docs/resources/CONTEXT.md`. When set, it writes the glossary at
  `$CONTEXT_DOCS_DIR/<source-repo>/CONTEXT.md` (and `CONTEXT-MAP.md`), namespaced by source repo, with
  origin recorded in the header. `describe-component` links domain terms to wherever the glossary
  actually lives.
- **`_base/project.env.example`** now documents `CONTEXT_DOCS_DIR` (previously referenced by skills but
  defined nowhere) under a new "Context docs" section.
- **`block-write-sensitive.sh`** now exempts `*.example` / `*.sample` / `*.template` scaffolds, fixing a
  false positive where `project.env.example` (and similar committed, secret-free templates) were blocked.
  Real `.env` / credentials / key files are unaffected.
- **Downstream impact**: use `docs/resources/CONTEXT.md` for normal glossary edits. Set
  `CONTEXT_DOCS_DIR` in `project.env` only for external storage. The hook change is a strict relaxation
  for template files only.

### Add `/tidy-repo` — systematize a messy inherited repo

New `productivity` skill (playbook + Codex/Claude wrappers) for repos that have drifted: scattered
todos, stray docs, and orphan files. It audits the repo read-only, writes a migration report to
`docs/resources/_reports/tidy-repo/`, and only applies moves after you approve them.

- **Non-destructive by design**: loose work → `docs/tasks_manager/_inbox/` as `I-NNN` ideas (re-triage
  later with `/triage-inbox`), loose docs → `docs/resources/` (via `git mv`), orphan files **flagged
  only — never moved, never deleted**.
- Orchestrates existing primitives (`/init`, the inbox, `/triage-inbox`, `sync-todo-ledgers.sh`) rather
  than adding new machinery.
- **Downstream impact**: additive only — a new skill installed by `link-skills.sh` / the manifest. No
  changes to existing conventions or hooks. Run `/tidy-repo` in a messy project to use it.

### Restructure docs/ — task manager under docs/tasks_manager/, templates in _base/docs/

Separated the task-tracking machinery from project documentation, and made the structure a seeded
template rather than live files in the framework repo:

- **`docs/tasks_manager/`** now holds the whole task system (`_areas.md`, `_roadmap.md`, `_active.md`,
  `_done.md`, `_inbox/`, `_inbox_archived/`, `_todos/`, `_todos_archived/`). Previously these sat
  directly under `docs/`.
- **`docs/resources/`** is the home for project documentation (architecture, component
  `CONTEXT.md` files, runbooks) — kept separate from queued work.
- **`_base/docs/`** is the canonical template. `/init` now seeds the working repo by copying
  `_base/docs/tasks_manager/` and `_base/docs/resources/` (like `PROJECT.md.template`), instead of
  hand-authoring the files. The framework repo no longer carries a live `docs/tasks_manager/`.
- Updated to the new paths: both todo hooks (`block-bad-todo-name`, `remind-archive-done-todo`),
  `_base/scripts/sync-todo-ledgers.sh`, the todo/inbox conventions, and the `capture-idea` / `triage-inbox`
  / `roadmap` / `prd-to-todos` skills.

**Downstream impact:** repos that already have a flat `docs/_todos/` (etc.) must migrate by moving the
files under `docs/tasks_manager/`: `mkdir -p docs/tasks_manager && git mv docs/_* docs/tasks_manager/`.
The hooks and sync script only recognize the new `docs/tasks_manager/…` paths. Run `/init` in a fresh
repo to get the new layout. No skills added/removed; manifest unchanged.

### Add describe-component, roadmap, and duplicate-aware capture

Built on the inbox/todo system:

- **`describe-component`** (engineering) — generates a structural `CONTEXT.md` for a system component
  (responsibility, public interface, key files, in/out dependencies, data owned, invariants, tests,
  links to domain terms). Distinct from the docs-primary domain glossary at
  `docs/resources/CONTEXT.md` (`grill-with-docs`). Component docs now live under
  `docs/resources/<area>/components/<component-slug>/CONTEXT.md`, with `CONTEXT_DOCS_DIR` reserved for
  external storage when the source repo should not receive docs.
- **`roadmap`** (productivity) + **`docs/tasks_manager/_roadmap.md`** — a Now/Next/Later plan of execution across all
  todos/ideas. Horizon placement is human intent (not derived from status, not rebuilt by the ledger
  script). Each todo renders as a collapsible `<details>` block (summary = plan, expanded = phases).
- **Duplicate-aware capture** — `capture-idea` now scans inbox + active todos + knowledge-base docs
  before recording, and offers to expand an existing item instead of creating a near-duplicate. The fast
  path is preserved: it only interrupts on a plausible match.

**Downstream impact:** `/init` now also scaffolds `docs/tasks_manager/_roadmap.md`. Two skills added to the plugin
manifest (`describe-component`, `roadmap`) — re-run the install scripts to pick them up. Optional
`CONTEXT_DOCS_DIR` setting in `project.env` remains for external storage.

### Add inbox capture layer + typed/indexed todos + ledgers

Todos gained a capture layer and stable identity. Ideas now flow `inbox → triage → todo`:

- **Inbox** (`docs/_inbox/`, archived to `docs/_inbox_archived/`) — frictionless idea capture, one
  `I-NNN_<desc>.md` file per idea, via the new `/capture-idea` skill. The new `/triage-inbox` skill
  promotes worthwhile ideas into full todos or drops them.
- **Typed, indexed todos** — todo filenames changed from `<datetime>_<desc>.md` to
  `T-NNN-<TYPE>_<desc>.md`, where `T-NNN` is a stable handle and `TYPE` is `F` feature / `D` debug /
  `C` chore / `R` research. Three metadata fields added: `Task ID`, `Type`, `Area`.
- **Areas registry** (`docs/_areas.md`) — todos/ideas are classified by an `Area` slug, defined
  collaboratively rather than from a fixed list.
- **Two ledgers** — `docs/_active.md` (open + in_progress) and `docs/_done.md` (completed, newest at
  the top), each row linking to its source file. New tool-agnostic `_base/scripts/sync-todo-ledgers.sh`
  rebuilds both from the todo files (works for Codex, which has no hooks).
- **Hooks** — `block-bad-todo-name.sh` now validates both `T-NNN-<TYPE>` and `I-NNN` names;
  `remind-archive-done-todo.sh` now nudges archiving for both the todo and inbox layers.

**Downstream impact:** the todo filename format changed — existing `<datetime>_<desc>.md` todos still
work but won't match the new hook; rename them to `T-NNN-<TYPE>_<desc>.md` to silence it, or leave
archived ones as-is. Run `/init` to create the new `docs/` files (`_inbox/`, `_inbox_archived/`,
`_areas.md`, `_active.md`, `_done.md`). New skills `capture-idea` and `triage-inbox` are added to the
plugin manifest — re-run `_base/scripts/link-skills.sh` / `skills/install-codex-skills.sh` to install them.

### Fix dual-runtime wiring for the PROJECT.md / `/align` rollout

Follow-up to the four preceding entries (block-write-sensitive hook, test-taxonomy convention, PROJECT.md template, `/align` skill). Validation against the repo's Codex/Claude dual-runtime ideology surfaced three issues:

- **`_base/SETUP_INSTRUCTIONS.md` Phase 2c was not idempotent.** The `cp _base/PROJECT.md.template PROJECT.md` line was unconditional, so if Claude's setup agent ran the phase first and then Codex's agent ran it second (or the user already seeded the file), the second run would overwrite existing content. Phases 0–2 are required to be idempotent per the file's own header. Fixed with a `[[ -f PROJECT.md ]] && echo "already exists" || cp …` guard.
- **`_base/README.md` listed `PROJECT.md` in two ownership buckets.** Once under "Downstream-owned" (alongside the required `README.md` and `AGENTS.md`) and again under "Mixed" (alongside the similarly-optional `project.env`). `PROJECT.md` is optional, so the "Mixed" entry is the correct one; the "Downstream-owned" duplicate was removed.
- **`_base/README.md` platform-support table** still showed only `implementer` and `reviewer` as agent definitions, missing the four new Claude-only subagents (`plan-critic`, `spec-validator`, `security-auditor`, `researcher`) added in a prior entry. Refreshed both columns to reflect all six subagents and to call out that the four new ones have no Codex equivalent — they run on the main thread under the cited personality + skill/convention.

`playbooks/conventions/test-taxonomy.md` was also rephrased to mirror the inclusive "consumer on Claude, main-thread on Codex" wording already used by `playbooks/conventions/plan-critique.md`. No behavior change; clarity only.

**Downstream impact:** documentation-only fixes. No skills, agents, hooks, or settings affected. `_base/SETUP_INSTRUCTIONS.md` and `_base/README.md` are upstream-owned and update cleanly via `git fetch template && git merge`. Downstream projects do not need to take any action.

### Add `/align` skill for feature alignment against `PROJECT.md`

New `playbooks/skills/align.md` plus Codex and Claude wrappers. The skill compares a proposed feature or change against the active `PROJECT.md` (Vision, Goals, Out of scope, Constraints) and issues one of three verdicts:

- **ALIGNED** — proceed; cites the goal(s) the change advances
- **NEEDS_CLARIFICATION** — surfaces specific questions to the user (ambiguous goals, missing scope entry)
- **OUT_OF_SCOPE** — surfaces the conflict and presents three explicit options: (a) update `PROJECT.md` to bring the feature into scope with user approval, (b) adjust the feature to fit current scope, or (c) cancel and discuss scope first

Comparison runs on three axes: goal alignment, scope (against the explicit Out-of-scope list), and constraint violations. Each axis must be marked with cited evidence from `PROJECT.md` — soft verdicts ("mostly aligned") and silent edits to the alignment doc are explicit failure modes.

`/align` is positioned at the front of the adversarial review pipeline: `align` (project-level) → `planning-workflow` → `plan-critic` (plan-level) → implementation → `spec-validator` → `security-auditor`. Each layer catches a different class of mistake.

This is a methodology skill — no Python library, no LLM-as-judge score thresholds, no audit-log JSONL. The model does the comparison in the skill's context with the user in the loop. Autonomous-dev's score-based `alignment_gate.py` (642 lines, ≥7/10 thresholds) is intentionally **not** ported; project_template's user-driven design does not need automated gating.

The skills table in `_base/README.md` was regenerated to include `align`.

**Downstream impact:** new files only; no conflicts expected. The skill is opt-in by invocation, and requires `PROJECT.md` at the repo root (downstream projects set it up via the previous CHANGELOG entry). Downstream projects without a `PROJECT.md` can ignore the skill entirely — it simply errors with instructions when invoked. After merging, run `./_base/scripts/gen-skills-table.sh` if your downstream `_base/README.md` skills table is out of date.

### Add `PROJECT.md` template for downstream project alignment

New `_base/PROJECT.md.template` is a lightweight scaffold downstream projects copy to `PROJECT.md` at the repo root when they want feature-level alignment gating. Sections: Vision, Goals, Out of scope, Constraints, Current phase, Known limitations, How agents should use this file, plus an optional Version history. Each section has brief inline guidance and `<placeholder>` markers the user replaces.

Tone: light and flexible (~160 lines). The template deliberately does **not** prescribe directory structure, root-file-count limits, or file-placement rules — those are downstream-project decisions and would collide with each project's own conventions. The Vision / Goals / Out of scope sections are the load-bearing ones for `/align` (forthcoming); the rest are optional context.

Supporting touch-ups:

- `_base/SETUP_INSTRUCTIONS.md` — new Phase 2c step covering `cp _base/PROJECT.md.template PROJECT.md`, marked optional. Skipping is supported and clearly stated.
- `_base/README.md` — file-tree diagram, "Quick start" copy-into-a-repo artifact table, and the downstream/upstream/mixed file-ownership matrix all gain rows for `PROJECT.md.template` (upstream-owned) and `PROJECT.md` (downstream-owned, never collides on pulls).

The mechanism mirrors the existing `_base/project.env.example` → `project.env` pattern: an upstream-owned example flows in cleanly via `git fetch template && git merge`, and a downstream-owned live file is the project's own.

**Downstream impact:** new files plus three small additions to `_base/SETUP_INSTRUCTIONS.md` and `_base/README.md`. No conflicts expected. Existing projects gain the option to add a `PROJECT.md` later; nothing forces them to. The `/align` skill (next entry) is the only consumer; without it the template is just documentation. Downstream projects that already maintain a project-vision doc under another name can either rename it to `PROJECT.md` (recommended) or fork the `/align` skill locally to read their preferred path.

### Add `test-taxonomy` convention naming the five test layers

New `playbooks/conventions/test-taxonomy.md` names the five layers this template recognizes — acceptance, contract, property-based, integration, unit — with definitions, when-to-use guidance, example assertion shapes, a decision matrix by change type (utility / data model / API / auth / multi-component / bug fix / UI / refactor), and a failure-modes section. The convention is shared vocabulary, not a workflow.

Existing files gain one-paragraph references:

- `playbooks/skills/tdd.md` — points readers at the taxonomy for the layer vocabulary; the skill itself stays focused on the RGR loop and vertical slices.
- `.claude/agents/spec-validator.md` — notes that the binary pass/fail tests it writes are the acceptance layer of the taxonomy, scoping it away from unit/integration/property-based work.

Neither file is restructured. The taxonomy lives in `playbooks/conventions/` next to `todo-convention.md` and `plan-critique.md`, matching the bare-markdown convention pattern.

**Downstream impact:** new file plus two minimal additions. No conflicts expected. Downstream projects that have customized `tdd.md` will need to merge the new one-paragraph reference by hand. The convention is opt-in — any skill or agent that wants the shared vocabulary can reference it; nothing forces it.

### Add `block-write-sensitive` hook to guard Write/Edit on sensitive paths

New `.claude/hooks/block-write-sensitive.sh` is a `PreToolUse` hook on `Write|Edit|MultiEdit` that denies operations targeting sensitive paths. Patterns blocked: `.env` and `.env.*` files, anything under `.git/`, `credentials`, `secrets`, `private*key`, `*.pem`, `*.key`, `.ssh/`, `.aws/`. Closes the chokepoint that the existing Bash guards (`block-dangerous-bash.sh`, `block-dangerous-git.sh`) don't cover — the Write/Edit tools can otherwise overwrite secrets and git internals without going through a shell.

Matches the existing hook style (stdin → `jq` → exit 2 on block with stderr message, exit 0 on allow). The new matcher entry is appended to `.claude/settings.json` next to the existing Bash matcher; no existing hooks were modified.

**Downstream impact:** new files and a new `PreToolUse.matcher` entry in `.claude/settings.json`. Downstream projects that have customized `.claude/settings.json` will need to merge the new `Write|Edit|MultiEdit` matcher block by hand (the existing `Bash` block is unchanged). If a downstream project has a legitimate reason to write to one of the protected paths (e.g., generating a `.env` from a configurator script), either narrow the patterns in the script or remove it from the matcher list locally — agents that hit the block should ask the user before overriding.

### Add adversarial review and research subagents

Four new Claude Code subagents in `.claude/agents/`, ported from the [autonomous-dev](https://github.com/akaszubski/autonomous-dev) harness and adapted to this template's style and skill graph:

- **`plan-critic`** — adversarial plan review against the five-axis rubric in `playbooks/conventions/plan-critique.md`. Issues PROCEED, REVISE, or BLOCKED with composite scoring. Read-only.
- **`spec-validator`** — spec-blind behavioral validation. Reads only the acceptance criteria (not the implementation), writes binary pass/fail tests in `tests/spec_validation/`, and reports PASS or FAIL.
- **`security-auditor`** — OWASP + LLM + Agentic AI review using the existing `security-review-owasp` skill. Smart secret detection that distinguishes correctly-gitignored `.env` from secrets in source/history. Flags deletion of security-related tests as HIGH.
- **`researcher`** — codebase-first investigation with citation and tradeoff requirements. Pairs with the broadened `researcher` personality.

`_base/AGENTS.md` gains a new "Available subagents" subsection under Multi-agent rules, cataloging all six subagents (the four new ones plus the existing `implementer` and `reviewer`) with purpose and dispatch trigger.

Harness-specific bits from the source were dropped during the port: file-write verdict gates, checkpoint-tracker Python blocks, active-scanner library imports, pipeline-state JSON files, RFC 2119 MUST/SHOULD shouting, and HARD GATE / FORBIDDEN markers. The ported content references this template's existing personalities (`critic`, `reviewer`, `researcher`) and skills (`security-review-owasp`) rather than duplicating their content.

**Downstream impact:** new files only; no conflicts expected. Claude Code users gain four additional subagents discoverable via `.claude/agents/` and the updated catalog in `_base/AGENTS.md`. Codex sessions without a multi-agent runtime should run `plan-critic`, `spec-validator`, `security-auditor`, and `researcher` on the main thread under the cited personality + skill/convention.

### Add `planning-workflow` skill and `plan-critique` convention

New methodology for pre-implementation planning:

- **`planning-workflow` skill** (`playbooks/skills/planning-workflow.md` + Codex wrapper at `skills/planning-workflow/` + Claude wrapper at `.claude/skills/planning-workflow/`) — a seven-step pre-implementation workflow: problem statement, scope check (with a 1.5x halt rule), existing-solutions search, minimal-path design, adversarial critique, decomposition, and durable plan output.
- **`plan-critique` convention** (`playbooks/conventions/plan-critique.md`) — a five-axis scoring rubric (assumption audit, scope creep, existing solutions, minimalism, uncertainty) with a fixed composite-to-verdict mapping (≥3.0 / no axis below 2 → PROCEED; <3.0 or any axis at 1 → REVISE; <2.0 or two or more axes at 1 → BLOCKED), calibration anchors per axis, minimum-rounds rule scaled by complexity, and a required output template. Applicable on the main thread under the `critic` personality, and used directly by the new `plan-critic` subagent (forthcoming).

The skills table in `_base/README.md` was regenerated to include `planning-workflow`.

**Downstream impact:** new files only; no conflicts expected. The convention adds a published rubric that existing skills like `prd-to-plan` and the `critic` personality can reference for plan validation. Run `./_base/scripts/gen-skills-table.sh` after merging if your downstream `_base/README.md` skills table is out of date.

### Broaden researcher personality to a general research role

`playbooks/personalities/researcher.md` evolved from a narrow doctrine-refresher into a general research role. New content: a four-phase workflow (codebase recon → targeted search → deep read of authoritative sources → synthesis), an explicit source hierarchy (official docs → reference implementations → community sources), and explicit citation + tradeoff requirements. The original doctrine-refresh use case (refreshing `_base/AGENTS.md` and evaluation guides) is preserved as one application of the broader role.

**Downstream impact:** strict superset of the previous personality — projects relying on the old framing keep working. Any new investigation task can now reference this role for consistent methodology.

### Move `project.env.example` under `_base/`

The reference env-vars file is now at `_base/project.env.example`. The live `project.env` continues to live at the repo root (gitignored) and is the file all four installer scripts (`skills/install-codex-skills.sh`, `_base/plugins/install-codex-plugins.sh`, `_base/plugins/install-claude-plugins.sh`, `_base/plugins/bootstrap-third-party.sh`) source — no installer changes were needed. The example file's internal header comment now documents the new copy command: `cp _base/project.env.example project.env`.

**Downstream impact:** if your downstream `README.md`, scripts, CI, or local notes reference `project.env.example` at the repo root, update the path to `_base/project.env.example` after merging. Your live `project.env` at the repo root is unaffected and continues to work as-is. Future template updates to the reference env vars (new entries, removed entries, comment changes) will now arrive cleanly inside `_base/` instead of as root-level merge candidates. Downstream projects that want to ship their *own* `.env.example` for project-specific env vars can now do so at the repo root without colliding with the template's.

### Move maintenance scripts under `_base/scripts/`

Both `scripts/gen-skills-table.sh` and `scripts/check-skills-sync.sh` now live at `_base/scripts/`. They only operate on upstream-owned content (the auto-generated table in `_base/README.md` and the template's skill catalog), so colocating them with the other `_base/` upstream files makes the ownership boundary explicit and frees the root-level `scripts/` namespace for downstream-owned tooling. The internal `REPO_ROOT` resolution in each script and the auto-generated table comment now point to the new path.

**Downstream impact:** if you have any local automation (CI, git hooks, shell aliases, downstream `AGENTS.md` rules) that invokes `./scripts/gen-skills-table.sh` or `./scripts/check-skills-sync.sh`, update the path to `./_base/scripts/…` after merging. No behavior change otherwise. If your downstream project has its own `scripts/` directory, it now coexists cleanly with the template's maintenance scripts (no merge conflict).

### Add `_base/scripts/check-skills-sync.sh` validator

New maintenance script that validates skill / wrapper / table consistency: every playbook has matching Codex + Claude wrappers, frontmatter `name` matches the directory, descriptions are present, Claude wrappers carry `disable-model-invocation: true`, wrappers reference their playbook and stay thin (≤50 lines), personalities aren't exposed as slash commands, the auto-generated skills table in `_base/README.md` is up-to-date, and quoted trigger phrases (e.g. `"red-green-refactor"`) don't drift between the Codex and Claude wrapper descriptions. Line-oriented output (`SEVERITY<tab>CHECK_ID<tab>PATH<tab>[details]`) with three tiers (BLOCKER / DRIFT / STYLE); exit 1 on BLOCKER or DRIFT, designed to be called by an agent in a loop (run → fix → re-run until clean).

**Downstream impact:** none. Opt-in maintenance script. Recommended after adding or modifying any skill or wrapper, and as a CI gate for downstream projects that add their own skills. The "Adding a new skill" checklist in `_base/README.md` now includes a regenerate-table + validate step.

### Add `_base/plugins/install-claude-plugins.sh` and `_base/SETUP_INSTRUCTIONS.md`

Two related additions that close the dual-runtime setup story for downstream projects.

- **`_base/plugins/install-claude-plugins.sh`** — installs a curated set of Claude Code plugins by merging entries into `~/.claude/settings.json` (`extraKnownMarketplaces` + `enabledPlugins`). Idempotent: re-running reports `already present, left as-is` for entries that already exist; preserves unrelated keys in the user's settings. The curated default list is hard-coded at the top of the script under `PLUGINS=( … )` and is easy to edit. The list ships with two starters: `obra/superpowers-marketplace` (Claude variant of the already-vendored Codex superpowers plugin) and `thedotmack/claude-mem` (cross-session memory). No umbrella `install-all.sh` — installers stay agent-scoped (Codex installers under `skills/` + `_base/plugins/`; Claude installer under `_base/plugins/`).
- **`_base/SETUP_INSTRUCTIONS.md`** — agent-readable numbered setup steps for wiring up a fresh project. **Each agent sets up only its own runtime**: Claude Code agents run Phases 0–2 + Phase 3 (Claude) + Phases 5–6; Codex agents run Phases 0–2 + Phase 4 (Codex) + Phases 5–6. Phases 0, 1, 2, 5, 6 are idempotent, so a second agent on the other runtime can re-run the file later to set up its side without re-doing or breaking the first agent's work. Each step has an explicit check; on any failure the agent stops and hands control back to the user. Pointed at like `Follow _base/SETUP_INSTRUCTIONS.md`.

**Downstream impact:** none for existing projects; the new installer is opt-in. Newly-seeded projects benefit immediately — pointing an agent at `_base/SETUP_INSTRUCTIONS.md` is now the canonical setup path (`_base/README.md` § "Quick start" updated to reflect this). The file ownership matrix in both `_base/README.md` and `_base/AGENTS.md` now lists `_base/SETUP_INSTRUCTIONS.md` as upstream-owned.

### Add `spec-workflow` skill

New heavyweight skill that drives a plan → build → review → fix loop for a single engineering item, with four standardized artifacts under `specs/<slug>/` (`spec.md`, `design.md`, `tasks.md`, `review.md`). Reuses the existing `subagent-protocol` dispatch + status vocabulary and the existing `implementer` and `reviewer` subagent/skill definitions — no new agent definitions, no experimental flags. Runtime-agnostic: same playbook and artifacts on Claude Code (Task-tool parallel dispatch) and Codex (sequential `/implementer` invocation per task). Composes with the existing PRD chain — `write-a-prd` / `prd-to-plan` / `prd-to-issues` / `prd-to-todos` remain unchanged; spec-workflow accepts a PRD or rough intent as input. Strong "do NOT use for…" guardrails in the wrapper description keep it from auto-triggering on small tasks.

**Downstream impact:** none. New skill; opt-in by invocation. After merging, run `./_base/scripts/gen-skills-table.sh` to regenerate the skills table in this file's sibling `_base/README.md`. No conflicts expected; new files only.

## 2026-05-11

### Add skills table generator and `_base/CHANGELOG.md`

The "Available skills" table in `_base/README.md` is now auto-generated from `playbooks/skills/*.md` between `<!-- BEGIN skills-table -->` / `<!-- END skills-table -->` markers. Run `./_base/scripts/gen-skills-table.sh` after adding, renaming, or removing a skill. Descriptions are pulled from the matching Claude wrapper's `description:` frontmatter (falls back to the playbook's `## Purpose` paragraph).

This base-changelog file (`_base/CHANGELOG.md`) was added. It lives under `_base/` alongside the other upstream-owned files, so a downstream project can keep its own root-level `CHANGELOG.md` without collision.

**Downstream impact:** none. Upstream-owned file; no manual action required after `git merge`. Downstream projects may keep a separate root-level `CHANGELOG.md` for their own changes.

### Split `AGENTS.md` and `README.md` into entrypoints + `_base/` files

Established a template-remote convention. New upstream-owned `_base/` directory at the repo root, containing:

- `_base/AGENTS.md` — base operating contract (previously the entirety of `AGENTS.md`).
- `_base/README.md` — base documentation (previously the entirety of `README.md`).

The remaining root-level `AGENTS.md` and `README.md` are now **downstream-owned**:

- `AGENTS.md` is a short auto-loaded entrypoint that instructs agents to also read `_base/AGENTS.md` and applies any project-specific overrides on top.
- `README.md` is the downstream project's own README; it links to `_base/README.md`.

Simple rule for merge conflicts going forward: always accept upstream under `_base/*`; keep downstream for `AGENTS.md`, `README.md`, and any customized skills.

**Downstream impact (one-time merge, expected to be small):**

- On first pull after this change, you'll see a new `_base/` directory appear. Accept it as-is from upstream.
- Your existing `AGENTS.md` and `README.md` may conflict with the new short entrypoint versions. **Default to keeping your downstream content** — your `AGENTS.md` already contains your project rules, and your `README.md` already describes your project. Lift the "First instruction to every agent: also read `_base/AGENTS.md`" directive into the top of your `AGENTS.md` so agents continue to load the base contract.
- After this one-time merge, future template pulls will not conflict on `AGENTS.md` or `README.md`.

### `template` git remote convention

Every project seeded from this template should keep a fetch-only `template` remote pointing at `git@github.com:toderian/project_template.git`. Documented in `_base/README.md` → "Staying in sync with the template" and `_base/AGENTS.md` → "Template-remote convention".

**Downstream impact:** if your project was started by copying files (not cloning), add the remote retroactively:

```bash
git remote add template git@github.com:toderian/project_template.git
git remote set-url --push template DISABLE
git fetch template
```

## 2026-05-10

### Add OWASP and migration-safety skills; harden bash hook

- New skill `security-review-owasp` (vendored from `agamm/claude-code-owasp`): applies OWASP Top 10:2025, ASVS 5.0, LLM Top 10 2025, and Agentic AI 2026.
- New skill `migration-safety` (adapted from OmexIT): generates safe, reversible DB schema migrations and reviews proposed ones for production hazards. Default focus PostgreSQL with Liquibase/Flyway.
- `.claude/hooks/block-dangerous-bash.sh` hardened against more dangerous shell invocations.

**Downstream impact:** the two new skills are additive and opt-in. The hook change tightens an existing block — review your hook config if you've customized it.

### Dual-runtime audit fixes

Closed gaps between Claude Code and Codex wrappers across existing skills so both runtimes get equivalent behavior.

**Downstream impact:** none expected unless you've forked specific wrappers.

### Add frontend-design skill, third-party bootstrap, richer write-a-skill

- New skill `frontend-design` (imported from Anthropic's frontend-design plugin): builds distinctive, production-grade frontend interfaces.
- `_base/plugins/bootstrap-third-party.sh` installs/documents third-party tools (`get-shit-done-cc`, `context-mode`, `claude-mem`) that ship their own multi-platform installers. Toggle each with env vars (`INSTALL_GSD`, `INSTALL_CONTEXT_MODE`, `INSTALL_CLAUDE_MEM`).
- `write-a-skill` playbook expanded with more concrete guidance.

**Downstream impact:** additive. To pick up the third-party tools, run `./_base/plugins/bootstrap-third-party.sh`.

## 2026-04-27

### Bundle GitHub Codex plugin and add Codex plugin installation support

- New `_base/plugins/install-codex-plugins.sh` symlinks repo plugins into `~/plugins/` and adds local marketplace entries to `~/.agents/plugins/marketplace.json`.
- Vendored `_base/plugins/github/` plugin for Codex (PR/issue/CI workflows).

**Downstream impact:** additive. Run `./_base/plugins/install-codex-plugins.sh` if you use Codex; restart Codex after.

## 2026-04-14

### Add todo-tracking skills with phased execution convention

New `init`, `prd-to-todos`, and related skills introduce a `docs/_todos/` + `_todos_archived/` convention for durable task tracking.

**Downstream impact:** additive. The convention only applies if you invoke `/init` or the related skills.

## 2026-04-09

### Reorganize: skill playbooks moved to `playbooks/skills/`

Authoritative skill workflow logic now lives under `playbooks/skills/<name>.md`. `skills/<name>/SKILL.md` (Codex) and `.claude/skills/<name>/SKILL.md` (Claude Code) are thin wrappers that point to the playbook.

**Downstream impact:** if you forked any skill, ensure your fork follows the new layout — the playbook is the single source of truth; both wrappers should be thin and reference it. The `install-codex-skills.sh` script also moved from `scripts/` to `skills/`.

### Add `project.env.example`

Copy to `project.env` to override default install paths for the Codex installers.

**Downstream impact:** optional. Defaults still work without it.

## Earlier history

Pre-2026-04-09 changes are not catalogued here. Use `git log` for full history.
