# Task-Native Specs and System Map

## Why + Scope

Agents need a reliable way to distinguish implemented system reality from planned specs, while still
using specs as first-class implementation and review inputs. This change updates the upstream template
so task files can carry executable specs, durable resource docs can carry system and contract specs,
and agent workflows must resolve spec status before code edits.

In scope:

- task-local Specification and Design guidance
- optional task `Spec refs` metadata
- spec lifecycle statuses for durable specs
- a seeded `docs/resources/system-map.md`
- `task-spec-workflow` and `map-system` skills
- updates to execute/review/refresh/closeout guidance

Out of scope:

- hard validator failures for missing spec sections in v1
- migrating existing downstream task files automatically
- replacing `spec-workflow`, PRDs, or cross-repo feature contracts

## Existing Solutions

- `spec-workflow` creates heavyweight `specs/<slug>/` artifacts for large parallelized work.
- `todo-convention` already gives tasks phases, acceptance criteria, tests, and execution logs.
- `cross-repo-feature` already uses contract status values, but does not define lifecycle semantics
  across all specs.
- `define-area` and `refresh-context` already maintain area summaries, dependency graphs, contracts,
  component contexts, and drift checks.

## Minimal Path

1. Extend existing conventions and base rules so agents must resolve spec sources and status before
   implementation.
2. Add the system-map seed doc and wire it into knowledge-base, define-area, and refresh-context.
3. Add two thin-wrapper skills backed by shared playbooks: `task-spec-workflow` and `map-system`.
4. Refresh generated skill surfaces and documentation.
5. Run validation and review.

## Risks and Unknowns

- Over-enforcement could make small tasks too ceremonial, so v1 keeps spec sections optional and
  enforces use through playbooks/review instead of script-hard-blocking.
- Agents may treat accepted specs as current behavior, so lifecycle statuses must explicitly separate
  planned intent from implemented evidence.
- `system-map.md` could become a dumping ground, so it must remain an index that links to detailed
  area docs.

## Critique History

- Initial user review rejected downstream inbox capture and clarified this must update the upstream
  template.
- User requested explicit distinction between implemented/existing specs and planned specs.
- Decision: mandatory playbook/review gate, no brittle section validator in v1.

## Phases

### Phase 1: Spec lifecycle conventions and seeded system map

- [x] Update base rules and task/knowledge conventions.
- [x] Add seeded `system-map.md`.
- [x] Update existing area/context/closeout/review workflows.

### Phase 2: New skills and generated skill surfaces

- [ ] Add `task-spec-workflow` playbook and wrappers.
- [ ] Add `map-system` playbook and wrappers.
- [ ] Register skills and regenerate README/Antigravity surfaces.

### Phase 3: Meta docs, validation, and review

- [ ] Update changelog and research snapshot.
- [ ] Run required validation checks.
- [ ] Review the implementation against this plan.

## Acceptance Criteria

- [ ] Agents have a mandatory rule to resolve spec sources and lifecycle status before implementation.
- [ ] Planned specs cannot be confused with implemented system evidence.
- [ ] Task-manager specs, durable system docs, and heavyweight `spec-workflow` have clear boundaries.
- [ ] `task-spec-workflow` and `map-system` are available through all active skill surfaces.
- [ ] Template validation scripts pass.

## Checks

- `_base/scripts/check-skills-sync.sh`
- `_base/scripts/gen-skills-table.sh --check`
- `_base/scripts/gen-antigravity-skills.sh --check`
- `_base/scripts/check-antigravity-skills.sh`
- `_base/scripts/check-template-update.sh`

## Execution Log

### 2026-06-18T00:00:00 - Plan normalization

**Actions taken:**
- Normalized the approved chat plan into this durable plan.

**Decisions made:**
- Use mandatory workflow/review enforcement without hard section validation in v1.

**Test results:**
- Not run yet.

**Outcome:** Ready for phased implementation.

### 2026-06-18T12:12:40+0300 - Phase 1: Spec lifecycle conventions and seeded system map

**Actions taken:**
- Added spec lifecycle semantics and `Spec refs` guidance to the base task contract.
- Added seeded `docs/resources/system-map.md` and status-aware resource documentation.
- Updated execute/review/closeout/refresh/area workflows to resolve specs and distinguish planned
  intent from implemented evidence.

**Decisions made:**
- Kept v1 enforcement in playbooks and review briefs rather than adding hard task-ledger validation.
- Kept `system-map.md` as an index to area docs, contracts, component contexts, and evidence.

**Test results:**
```text
_base/scripts/check-template-update.sh - passed
```

**Outcome:** Phase 1 complete.
