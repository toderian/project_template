# Architecture as the single source of truth: research snapshot

Researched on: 2026-09-04. Scope: how `agents-template` (this repo) should keep one architectural
source of truth — an architecture document plus ADRs — that agents must read before acting, and from
which tasks are derived when the architecture changes. Every non-local claim below links to a page
that was fetched during this research; where only secondary sources or no source exist, it says so.

## Question

How should a coding-agent operating contract keep a single architectural source of truth (architecture
doc + ADRs) that agents read before planning, and derive implementation tasks from it when the
architecture changes ("architecture first, tasks follow")?

## Short answer

1. Every spec-driven toolkit (Spec Kit, Kiro, OpenSpec) separates a **canonical, always-current** layer
   (constitution / steering / `specs/`) from a **proposal** layer (`specs/NNN-feature/`,
   `.kiro/specs/<feature>/`, `changes/<name>/`) and derives a `tasks.md` from the proposal with
   per-task back-references; completion merges the proposal back (OpenSpec archive) or appends the
   remaining gap (Spec Kit converge).
2. The "read before planning" gate is not an instruction to read docs; it is a **planning step that
   loads the canonical doc and fails on unjustified violation** (Spec Kit `/speckit.plan` Constitution
   Check) — and a read-only analyzer that maps requirements to tasks and flags orphans.
3. ADR practice converges on: one file per decision, immutable once accepted, `superseded by` links,
   a sequential-number log, and (MADR/AWS) an explicit **confirmation** hook used during review.
4. Agent-context docs (Claude Code, Codex, Cursor, Kiro steering) all say: keep the always-loaded file
   tiny and point at docs; the only controlled study found repository overviews in context files do
   **not** help agents while instructions **are** followed — so put the "read `architecture.md` and
   the ADR index before planning" **instruction** in `AGENTS.md`, never the architecture itself.
5. For this repo: (a) let `Spec refs` accept `ADR-NNNN` and make the pre-implementation gate resolve
   ADRs, (b) seed a one-page `docs/resources/architecture.md` (Architecture-Haiku shape) plus
   `docs/adr/README.md`, (c) add a `propose-change` flow that writes a delta against the canonical docs
   and then runs the existing task-creation ritual, (d) add stdlib-only `at` checks for unresolved
   `Spec refs`, dangling `superseded by`, and orphan ADRs, (e) ratchet spec status on completion.

## Findings per source

### 1. Spec-driven development toolkits

**GitHub Spec Kit** — https://github.com/github/spec-kit and
https://github.com/github/spec-kit/blob/main/spec-driven.md

- Layout: `.specify/memory/constitution.md` ("immutable architectural principles governing all
  implementations"), then per feature `specs/[branch-name]/{spec.md, plan.md, research.md,
  data-model.md, contracts/, quickstart.md, tasks.md}`; `tasks.md` is "Executable task list derived
  from the plan".
- Commands and order: `/speckit.constitution` → `/speckit.specify` → (`/speckit.clarify`) →
  `/speckit.plan` → `/speckit.tasks` → (`/speckit.analyze`, `/speckit.checklist`) →
  `/speckit.implement` → `/speckit.converge` ("Assess the codebase against spec/plan/tasks and
  append remaining work").
- The planning gate: the plan command's first step is "Read FEATURE_SPEC and
  `/memory/constitution.md`", fills a Constitution Check section, "ERROR if violations unjustified",
  and re-runs the check post-design
  (https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/plan.md).
- Task derivation: plan.md and spec.md are mandatory inputs; every task is `- [ ] T001 [P] [US1]
  description + file path`; tasks are grouped per user story so each story is independently
  testable; a dependency graph is required
  (https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/tasks.md).
- Drift check: `/speckit.analyze` loads spec/plan/tasks/constitution, runs six passes (duplication,
  ambiguity, underspecification, constitution alignment, coverage gaps, inconsistency), maps "each task
  to one or more requirements or stories", emits a coverage table, grades CRITICAL for "Constitution
  violations, missing core artifacts, zero-coverage blocking requirements", and "Do **not** modify any
  files" (https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/analyze.md).
- Completion merge: `/speckit.converge` builds an "intent inventory" from spec/plan/tasks, classifies
  gaps as missing / partial / contradicts / unrequested, appends a new phase to `tasks.md` with each
  item tracing to `FR-003`, `SC-002`, or `Constitution II`, and never rewrites the spec
  (https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/converge.md).
- Governance: the constitution template carries Version / Ratified / Last Amended, "Amendments require
  documentation, approval, migration plan", "Constitution supersedes all other practices", "All
  PRs/reviews must verify compliance"
  (https://raw.githubusercontent.com/github/spec-kit/main/templates/constitution-template.md).
- Anti-hallucination mechanics are structural, not rhetorical: templates "Force explicit
  `[NEEDS CLARIFICATION]` markers for ambiguities rather than assumed details" and act as "unit tests
  for the specification" (spec-driven.md).

**Kiro** — https://kiro.dev/docs/specs/, https://kiro.dev/docs/specs/feature-specs/,
https://kiro.dev/docs/specs/best-practices/, https://kiro.dev/docs/steering/,
https://kiro.dev/blog/introducing-kiro/

- Layout: `.kiro/specs/<feature>/{requirements.md, design.md, tasks.md}`; requirements in EARS
  ("WHEN [condition/event] THE SYSTEM SHALL [expected behavior]"); tasks carry "references back to
  requirement numbers"; three phases with approval gates, requirements-first or design-first.
- Change propagation: on a requirements-first spec, "Refine" on design "will update both the design
  documentation and the associated task list"; on tasks, "Sync Files ... will create new tasks that map
  to the new requirements"; "Kiro will automatically mark completed tasks" after scanning the codebase.
  Launch post: "Kiro's specs stay synced with your evolving codebase. Developers can author code and
  ask Kiro to update specs or manually update specs to refresh tasks."
- Drift/quality gate: "Analyze Requirements" before design catches "logical inconsistencies,
  ambiguities, conflicting constraints, and gaps".
- Steering = always-loaded canonical context: `.kiro/steering/{product.md, tech.md, structure.md}`
  "are included in every interaction by default"; frontmatter `inclusion: always | fileMatch
  (fileMatchPattern) | manual (#name) | auto (description)`; live file references
  `#[[file:api/openapi.yaml]]`; "One domain per file".

**OpenSpec** — https://github.com/Fission-AI/OpenSpec,
https://github.com/Fission-AI/OpenSpec/blob/main/docs/getting-started.md

- Layout: `openspec/specs/` "describe how your system currently behaves. Organized by domain";
  `openspec/changes/<name>/{proposal.md, design.md, tasks.md, specs/}` are "Proposed modifications".
- Delta spec syntax: `## ADDED Requirements` / `## MODIFIED Requirements` / `## REMOVED Requirements`,
  then `### Requirement: <name>` and `#### Scenario:` with WHEN/THEN bullets and SHALL/MUST language.
- Completion merge: on `/opsx:archive` "ADDED requirements are appended to the main spec; MODIFIED
  requirements replace the existing version; REMOVED requirements are deleted", and the change folder
  moves to `openspec/changes/archive/<date>-<name>/`.
- Drift check: `openspec validate` validates spec formatting (structure). Secondary sources
  (https://codemyspec.com/blog/openspec-explained) add that `--strict` checks "required sections
  present, valid format, cross-artifact dependencies" and "does not check behavioral correctness" — not
  confirmed on a primary page.
- Agent instructions are generated/refreshed by `openspec init` / `openspec update`; the README's
  cross-repo "Stores" model is "a platform team owns the specs; product teams reference them read-only".

**BMAD-METHOD** — https://github.com/bmad-code-org/BMAD-METHOD

- PRD + Architecture Document are the planning artifacts; a scrum-master role derives story files that
  "carry product and technical decisions forward instead of re-explaining them in every chat". The
  README fetched does not document the file layout or a merge-back step in enough detail to compare;
  treat as secondary for mechanics.

**Tessl** — https://docs.tessl.io/

- The current docs describe a registry/governance/evals platform for skills; the fetched overview
  contains no spec-file or spec-to-code workflow. No primary source found for "Tessl spec-driven
  mechanics" as of this snapshot.

**AWS "spec-driven" guidance**

- No AWS Prescriptive Guidance page on spec-driven development was found (search:
  "AWS prescriptive guidance spec-driven development AI coding agents 2026" returned only agentic-AI
  pattern guides and third-party blogs). AWS's primary spec-driven artifact is Kiro (above). AWS does
  publish primary ADR guidance (section 2).

### 2. ADR practice and the living architecture document

- **Nygard (2011)** — https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions —
  Title / Context / Decision / Status / Consequences; status "proposed, accepted, deprecated,
  superseded"; `doc/arch/adr-NNN.md`, numbers never reused; "If a decision is reversed, we will keep
  the old one around, but mark it as superseded."
- **adr.github.io** — https://adr.github.io/ — the ADR collection is the project's "decision log"
  (architectural knowledge management); lists MADR, adr-tools, log4brains; notes AWS Prescriptive
  Guidance and Azure WAF endorse ADRs.
- **MADR** — https://adr.github.io/madr/ and
  https://raw.githubusercontent.com/adr/madr/develop/template/adr-template.md — `docs/decisions/
  NNNN-title-with-dashes.md`; frontmatter status `{proposed | rejected | accepted | deprecated | … |
  superseded by ADR-0123}`; bare / minimal / full templates; a **Confirmation** section: "Describe how
  the implementation / compliance of the ADR can/will be confirmed. Is there any automated or manual
  fitness function?" — "although we classify this element as optional, it is included in many ADRs".
- **AWS ADR process** —
  https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html
  — "When the team accepts an ADR, it becomes immutable"; new insight → new ADR that supersedes the
  old; states Proposed → Accepted / Rejected → Superseded; "The team uses the ADRs as a reference
  during code and architectural reviews"; a reviewer who finds a violation "shares a link to the ADR".
- **adr-tools** — https://github.com/npryce/adr-tools — `adr init` (default `doc/adr`), `adr new`,
  `adr new -s 9` "flagged as superceding ADR [number], and changes the status of ADR [number]",
  `adr list`, `adr generate toc|graph`. This is the reference mechanic for an `at adr new [-s]`.
- **log4brains** — https://github.com/thomvaill/log4brains — docs-as-code ADR log published as a
  static site; supports global `docs/adr/` plus package-local ADRs; timeline built from git history.
- **arc42 §9** — https://docs.arc42.org/section-9/ — "Important, expensive, large scale or risky
  architecture decisions including rationales"; recommends Nygard-format ADRs; "decide whether an
  architectural decision should be documented here in this central section or whether you better
  document it locally (e.g. within the white box template of one building block)". Overview of the 12
  sections: https://arc42.org/overview.
- **C4 model** — https://c4model.com/ — System Context / Container / Component / Code abstractions;
  notation- and tooling-independent, which is what makes diagrams-as-code possible.
- **Architecture Haiku** — https://keeling.dev/essays/architecture-haiku/ — one page containing
  solution summary, technical constraints, prioritised quality attributes, high-level functional
  requirements, design decisions with rationale/trade-offs, patterns, and only diagrams that add
  meaning; "Placing extreme constraints on the architecture description forces architects to focus on
  the design's most important aspects"; updated by "scribbling notes" as construction teaches.
- **Docs as code** — https://www.writethedocs.org/guide/docs-as-code/ — plain text, VCS, code review,
  automated tests/CI; "block merging of new features if they don't include documentation".

### 3. Agent-facing context files

- **agents.md** — https://agents.md/ — "a README for agents"; plain Markdown; nested files: "Agents
  automatically read the nearest file in the directory tree, so the closest one takes precedence".
- **Claude Code memory** — https://code.claude.com/docs/en/memory — "target under 200 lines per
  CLAUDE.md file. Longer files consume more context and reduce adherence"; `@path` imports "still load
  and enter the context window at launch"; subdirectory CLAUDE.md files "are included when Claude reads
  files in those subdirectories"; `.claude/rules/*.md` with `paths:` frontmatter load on match; the
  `/doctor` trim "cuts content Claude can derive from the codebase, such as directory layouts,
  dependency lists, and architecture overviews, and keeps pitfalls, rationale, and conventions"; CLAUDE.md
  is "context, not enforced configuration" — use a hook to block.
- **Claude Code best practices** — https://code.claude.com/docs/en/best-practices — include
  "Architectural decisions specific to your project", exclude "Anything Claude can figure out by
  reading code" and "File-by-file descriptions of the codebase"; "Explore first, then plan, then
  code"; "Point to sources"; hooks "are deterministic and guarantee the action happens" whereas
  CLAUDE.md "instructions ... are advisory".
- **Codex AGENTS.md** — https://learn.chatgpt.com/docs/agent-configuration/agents-md — discovery
  `~/.codex/AGENTS.override.md` → `~/.codex/AGENTS.md` → repo root down to cwd; concatenated
  root-down; "stops adding files once the combined size reaches the limit defined by
  `project_doc_max_bytes` (32 KiB by default)".
- **Cursor rules** — https://cursor.com/docs/context/rules — Always / Auto Attached (globs) / Agent
  Requested (description) / Manual; "Keep rules under 500 lines"; "Reference files instead of copying
  their contents—this keeps rules short and prevents them from becoming stale".
- **Kiro steering** — see section 1: `inclusion: always | fileMatch | manual | auto`.
- **Evidence** — "Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding
  Agents?" https://arxiv.org/abs/2602.11988 (CTXbench 138 instances / SWE-bench Lite 300; Claude Code,
  Codex, Qwen Code): "providing context files does not generally improve task success rates, while
  increasing inference cost by over 20% on average"; "Instructions in the context files are well
  followed by coding agents"; "Repository overviews, although popular and recommended by model
  providers, are not helpful"; recommendation: human-written files "for non-standard practices" only.

### 4. Traceability, drift detection, hallucination evidence

- **Requirements traceability** — https://en.wikipedia.org/wiki/Requirements_traceability — "the
  ability to describe and follow the life of a requirement in both a forwards and backwards
  direction"; a traceability matrix is a table whose empty cells show gaps; requirements with
  incomplete trace chains signal missing implementation or verification. ISO/IEC/IEEE 29148 mandates
  an RTM per vendor summaries (https://www.reqview.com/blog/requirements-traceability-matrix/) — the
  standard text itself was not fetched (paywalled).
- **Tool-level drift checks** (primary, section 1): Spec Kit `analyze` (coverage table, orphan
  requirements, constitution CRITICAL) and `converge` (missing/partial/contradicts/unrequested);
  OpenSpec `validate` (structure); Kiro "Analyze Requirements" and "Sync Files".
- **Hallucination reduction from curated docs** — no primary source found that shows a curated
  architecture document reduces hallucination in coding agents. The only controlled study fetched
  (arXiv 2602.11988) points the other way for *overviews* and only supports *instructions*. The
  hallucination-detection papers surfaced by search (arXiv 2607.00895, "Beyond Document Grounding")
  concern span-level detection, not prevention via project docs, and were not read in full. Treat
  "docs reduce hallucination" as an unproven hypothesis; the toolkits' actual mechanisms are
  structural gates (`[NEEDS CLARIFICATION]`, constitution check, read-only analyze, approval gates).

## Comparison table

| Toolkit | Canonical doc (always current) | Change mechanism | Task derivation | Completion merge | Drift check |
|---|---|---|---|---|---|
| Spec Kit | `.specify/memory/constitution.md` (versioned, ratified, amended) | `specs/NNN-feature/{spec,plan}.md`; plan runs Constitution Check, "ERROR if violations unjustified" | `/speckit.tasks` from plan+spec → `T001 [P] [US1] … path`, per-story phases, dependency graph | `/speckit.converge` appends a gap phase tracing to `FR-nnn`/`Constitution N`; spec never rewritten | `/speckit.analyze`: 6 passes, coverage table, read-only |
| Kiro | `.kiro/steering/{product,tech,structure}.md` (`inclusion: always`) | `.kiro/specs/<feature>/{requirements,design}.md` with approval gates | `tasks.md` with "references back to requirement numbers"; "Refine"/"Sync Files" regenerate tasks | "Sync Files" marks completed tasks from code; specs stay in repo | "Analyze Requirements"; Sync Files |
| OpenSpec | `openspec/specs/<domain>/` = "how your system currently behaves" | `openspec/changes/<name>/` with delta specs `## ADDED/MODIFIED/REMOVED Requirements` | `changes/<name>/tasks.md` checklist written at `/opsx:propose` | `/opsx:archive`: ADDED appended, MODIFIED replaced, REMOVED deleted; folder → `changes/archive/` | `openspec validate` (structure only) |
| ADR practice (Nygard/MADR/AWS) | Decision log `docs/adr|decisions/NNNN-*.md`, immutable once accepted | New ADR supersedes old; `adr new -s N` flips old status | Not in scope; AWS: ADRs consulted in reviews | Status ratchet proposed → accepted → superseded | MADR "Confirmation" fitness function; AWS review links violating change to the ADR |
| agents-template today | `docs/resources/system-map.md` (index) + `<area>/summary.md` + `CONTEXT.md`; `docs/adr/NNNN-slug.md` (1–3 sentences) | None formalised; `prd-to-plan`/`prd-to-todos` start from a PRD, not from an architecture delta | `add-task` / `prd-to-todos` with `Spec refs` (paths, PRDs, `self`) | `complete-task` step 3 reconciles linked specs by hand | `at ledger check` (task structure), `at doctor` (AGENTS.md drift); nothing on `Spec refs` resolution or ADRs |

## Gaps in agents-template vs. those toolkits

Local evidence (absolute paths):

- ADRs are defined but unreachable from the task loop. `Spec refs` lists PRDs, plans, system map,
  summaries, dependency graphs, contexts, contracts — never ADRs
  (`/home/vi/work/vitalii/repos/project_template/plugins/agents-tasks/skills/task-ledger/references/todo-convention.md`
  lines 247–252 and 434; `/home/vi/work/vitalii/repos/project_template/plugins/agents-tasks/skills/add-task/SKILL.md`
  lines 78–79; `/home/vi/work/vitalii/repos/project_template/plugins/agents-core/skills/execute-plan/SKILL.md`
  line 70; `/home/vi/work/vitalii/repos/project_template/plugins/agents-tasks/skills/complete-task/SKILL.md`
  lines 45–48). The repo-wide grep for ADR shows only knowledge-base, domain-modeling, grill-with-docs,
  and passing mentions.
- No seeded architecture document. `at init --with-tasks` seeds `docs/resources/{README.md,
  CONTEXT.md, global/summary.md, _inbox, _reports}` and no `system-map.md`, `architecture.md`, or
  `docs/adr/` (`/home/vi/work/vitalii/repos/project_template/plugins/agents-tasks/seed/docs/resources/`;
  `_copy_tree` in `/home/vi/work/vitalii/repos/project_template/plugins/agents-core/lib/at.py` line 434).
  `system-map.md` is explicitly "an index, not a dumping ground for every architecture fact"
  (`knowledge-base/SKILL.md` lines 44–47), so constraints, quality priorities, and cross-cutting
  decisions — the Haiku content — have no home.
- Two status vocabularies with no link shape. ADR status is `proposed | accepted | deprecated |
  superseded by ADR-NNNN` (`knowledge-base/references/adr-convention.md` line 38); spec status is
  `draft | accepted | partially-implemented | implemented | superseded` (`knowledge-base/SKILL.md`
  lines 94–109). Summaries are told to "link to ... ADRs" (line 244) but no reference syntax is defined,
  so nothing can be validated.
- No "architecture before planning" gate. The pre-implementation gate resolves task-local spec, `Spec
  refs`, tests, and "relevant durable docs" (`todo-convention.md` lines 464–481); `planning-workflow`
  and `execute-plan` do not name an architecture doc; the seed `AGENTS.md` routes ADRs to
  `knowledge-base` only under "Durable notes"
  (`/home/vi/work/vitalii/repos/project_template/plugins/agents-core/seed/AGENTS.md` line 70).
- No "architecture change → tasks" flow. `prd-to-todos` and `prd-to-plan` take a PRD; `align` checks
  `PROJECT.md`; `complete-task` reconciles by prose. There is no delta/proposal artifact and no archive
  step that merges it into `summary.md`/`system-map.md`.
- No traceability check. `_repo_doctor_findings` (`at.py` lines 533–600) checks CLAUDE.md, AGENTS.md
  size/slots/routing drift, legacy dirs, settings, and ledgers; `Spec refs` are never parsed
  (`grep -n "Spec refs" at.py` is empty).

## Recommended changes, ranked by value/effort

Ordering: highest value per unit of effort first. Effort assumes bash + python3 stdlib + jq only.

1. **Accept `ADR-NNNN` in `Spec refs` and resolve ADRs in the gate** (value: high; effort: low).
   - Files: `todo-convention.md` §Spec lifecycle list item 2 and the `Spec refs` field definition;
     `add-task/SKILL.md` step 4; `prd-to-todos/SKILL.md` step 5; `execute-plan/SKILL.md` line 70;
     `task-spec-workflow/SKILL.md` line 33; `complete-task/SKILL.md` step 3.
   - Define the reference form once in `adr-convention.md`: `ADR-NNNN` resolves to
     `docs/adr/NNNN-*.md`; state that ADR status is a *decision* lifecycle and spec status is an
     *implementation* lifecycle, and how they combine (an `accepted` ADR is planning intent; evidence
     lives in the summary/contract that implements it). Sources: Nygard status set; MADR
     `superseded by ADR-0123`; Spec Kit tasks tracing to `Constitution II`.
2. **Seed a one-page `docs/resources/architecture.md` and `docs/adr/README.md`** (value: high;
   effort: low-medium).
   - Files: new `plugins/agents-tasks/seed/docs/resources/architecture.md` (Haiku shape: status
     header `> Status: draft`, solution summary, constraints, quality-attribute priorities, key
     decisions each linking `ADR-NNNN`, patterns, pointers to `system-map.md` and area summaries,
     ≤ 1 page); new `plugins/agents-tasks/seed/docs/adr/README.md` (index table `ADR | Title |
     Status | Supersedes/Superseded by`, status vocabulary, link to convention); update
     `seed/docs/resources/README.md`, `knowledge-base/SKILL.md` discovery order (insert after
     `CONTEXT.md`, before `system-map.md`) and the tree in `todo-convention.md` lines 19–53;
     `adr-convention.md` "create lazily" rule becomes "seeded index, lazy first ADR".
   - Sources: Keeling's one-page constraint; arc42 §9 "central vs local"; Kiro's always-loaded
     `structure.md`; Spec Kit constitution metadata (Version/Ratified/Last Amended) for the header.
   - Alternative: fold the Haiku sections into `system-map.md`. Rejected for now because `map-system`
     already defines `system-map.md` as a status-aware index; mixing rationale into it re-creates the
     dumping-ground problem the skill warns about.
3. **Make "read architecture before planning" a gate, not advice** (value: high; effort: low).
   - Files: `todo-convention.md` pre-implementation gate step 2 (add: read `architecture.md` and the
     ADR index; list every ADR that constrains the task in the execution log; if the planned change
     contradicts an `accepted` ADR, stop and propose a superseding ADR before code);
     `agents-core/skills/planning-workflow/SKILL.md` (same rule at plan time);
     `agents-core/seed/AGENTS.md` — one line under Principles ("Architecture first — before planning
     read `docs/resources/architecture.md` and `docs/adr/README.md` when they exist; a change that
     contradicts an accepted ADR needs a superseding ADR first") and a routing row "Change the
     architecture" → `agents-tasks:propose-change` (item 4). Keep the seed under 200 lines
     (`MAX_AGENTS_MD_LINES` in `at.py`; Claude Code docs) and remember Codex's 32 KiB budget.
   - Sources: Spec Kit plan Constitution Check ("ERROR if violations unjustified"); AWS "ADRs as a
     reference during code and architectural reviews"; arXiv 2602.11988 (instructions are followed,
     overviews are not — so ship the instruction, not the overview); Claude Code docs (CLAUDE.md is
     advisory; hooks are deterministic). Optional hardening later: a `PreToolUse` hook on writes
     under `docs/tasks_manager/_todos/` that warns when the execution log has no "Architecture
     resolved" entry — only if the advisory rule proves insufficient.
4. **Add an `agents-tasks:propose-change` skill (architecture change → delta → tasks)** (value:
   high; effort: medium).
   - Files: new `plugins/agents-tasks/skills/propose-change/SKILL.md` + `assets/change-proposal.
     template.md`; touch `prd-to-todos/SKILL.md` (accept a proposal as source, `Source:
     propose-change`), `complete-task/SKILL.md` (archive step), `knowledge-base/SKILL.md` (where
     proposals live), `agents-tasks/.claude-plugin/plugin.json` if skills are enumerated, then
     `python3 scripts/build.py`.
   - Mechanics (OpenSpec-shaped, kept in Markdown): `docs/resources/_changes/<YYYY-MM-DD>-<slug>/
     proposal.md` with `## ADDED / MODIFIED / REMOVED` sections, each naming the canonical target
     (`architecture.md`, `<area>/summary.md`, `contracts/<slug>.md`) and status `draft`; any
     decision passing the offer test becomes `docs/adr/NNNN-slug.md` in `proposed`; user approval
     flips ADR to `accepted` and proposal to `accepted`; tasks are then created through the existing
     `add-task` ritual with `Spec refs: docs/resources/_changes/…/proposal.md, ADR-NNNN` and
     `Blocked by` edges; on the last task's `complete-task`, the deltas are applied to the canonical
     docs (append / replace / delete, exactly OpenSpec's archive rule), the proposal moves to
     `docs/archive/changes/`, and canonical status ratchets (item 6).
   - Sources: OpenSpec layout and archive rule; Spec Kit `tasks` format and `converge` gap phase;
     Kiro "Sync Files"; AWS immutable-after-acceptance.
   - Lower-effort alternative: skip the new skill and add a "source is an architecture delta" mode to
     `prd-to-todos`. Loses the archive/merge step, which is the part this repo is missing most.
5. **Traceability checks in `at`** (value: medium-high; effort: medium).
   - File: `plugins/agents-core/lib/at.py` (`_ledger_findings` / `_repo_doctor_findings`) plus
     `scripts/tests/` coverage. Checks: (a) every `Spec refs` entry that is a path or `ADR-NNNN`
     resolves (ERROR); (b) `superseded by ADR-NNNN` points to an existing ADR (ERROR); (c) ADR status
     is in the allowed set (ERROR); (d) an `accepted` ADR referenced by no task, summary,
     `architecture.md`, or proposal is reported as orphan (WARN); (e) `architecture.md` /
     `summary.md` with `Status:` outside the spec set (ERROR). Bidirectional, like an RTM, but
     WARN-only where a human judgment is needed.
   - Sources: Spec Kit `analyze` coverage table and "orphaned items"; Wikipedia RTM empty-cell rule;
     docs-as-code CI gating. Guard against the false-positive cost the arXiv paper attributes to
     unneeded ceremony: do not fail CI on (d).
6. **Status ratchet on completion** (value: medium; effort: low).
   - Files: `complete-task/SKILL.md` step 3 and `todo-convention.md` §Completion. Rules: a completed
     task may move a linked durable spec `accepted → partially-implemented | implemented` only with
     evidence recorded in the harvest; it never moves anything backwards and never flips an ADR
     (ADRs change only by supersession, which requires the user); `draft → accepted` is a human act.
   - Sources: AWS immutable ADRs; MADR Confirmation ("automated or manual fitness function") — add an
     optional `## Confirmation` section to `adr.template.md` so a task can cite it as evidence.
7. **`at adr new <slug> [-s NNNN]`** (value: medium; effort: low-medium).
   - File: `at.py` (mirror `at reserve task`: atomic next number from `docs/adr/`, template copy,
     optional supersede that rewrites the old ADR's status line and appends the new row to
     `docs/adr/README.md`). Source: adr-tools `adr new -s`.

Not recommended: copying the architecture doc into `AGENTS.md`/`CLAUDE.md` (Claude Code `/doctor`
trims exactly that; arXiv 2602.11988), an EARS/SHALL requirement grammar (heavier than the repo's
1–3-sentence ADR style and unnecessary until tasks are generated by tooling rather than by an agent
following a skill), or a second numbering scheme for proposals (the date-slug folder is enough).

## Open questions

- Should `architecture.md` and `system-map.md` be one file? Recommendation above keeps them separate;
  a downstream with a single repo may prefer one. Decide before seeding.
- Who accepts an ADR in a solo-maintainer repo? AWS assumes a team review; the offer test plus an
  explicit user "accept" in chat is probably enough, but the skill must say so.
- Is the 1–3-sentence ADR body sufficient once tasks derive from ADRs? MADR's Confirmation section is
  the minimal addition that makes an ADR verifiable; anything more re-imports the boilerplate the
  current convention deliberately dropped.
- Where do change proposals live long-term: `docs/resources/_changes/` (proposed here, mirrors
  `_inbox/_digests/_reports`), `docs/_plans/` (already used by `prd-to-plan`), or inside the task file
  (`### Specification`)? Reusing `docs/_plans/` reduces surface but conflates plan and delta.
- Will the advisory "read architecture" instruction hold in Codex, where the 32 KiB
  `project_doc_max_bytes` cap concatenates root and nested `AGENTS.md`? Measure downstream sizes
  before adding rows.
- Whether a curated architecture doc reduces hallucinated structure remains unmeasured. The repo's
  own signal would be: count of "invented structure" corrections in task logs before/after the gate.

## Sources

Local (read in full):

- `/home/vi/work/vitalii/repos/project_template/plugins/agents-tasks/skills/knowledge-base/SKILL.md`
- `/home/vi/work/vitalii/repos/project_template/plugins/agents-tasks/skills/knowledge-base/references/adr-convention.md`
- `/home/vi/work/vitalii/repos/project_template/plugins/agents-tasks/skills/knowledge-base/assets/adr.template.md`
- `/home/vi/work/vitalii/repos/project_template/plugins/agents-tasks/skills/task-ledger/references/todo-convention.md`
- `/home/vi/work/vitalii/repos/project_template/plugins/agents-tasks/skills/complete-task/SKILL.md`
- `/home/vi/work/vitalii/repos/project_template/plugins/agents-tasks/skills/add-task/SKILL.md`
- `/home/vi/work/vitalii/repos/project_template/plugins/agents-tasks/skills/prd-to-todos/SKILL.md`
- `/home/vi/work/vitalii/repos/project_template/plugins/agents-tasks/skills/prd-to-plan/SKILL.md`
- `/home/vi/work/vitalii/repos/project_template/plugins/agents-tasks/skills/align/SKILL.md`
- `/home/vi/work/vitalii/repos/project_template/plugins/agents-core/seed/AGENTS.md`
- `/home/vi/work/vitalii/repos/project_template/plugins/agents-tasks/seed/docs/resources/` (README.md, CONTEXT.md, global/summary.md)
- `/home/vi/work/vitalii/repos/project_template/plugins/agents-core/lib/at.py` (lines 394–445 seeding, 533–600 doctor)
- `/home/vi/work/vitalii/repos/project_template/plugins/agents-core/skills/execute-plan/SKILL.md`, `task-spec-workflow/SKILL.md` (grep hits only)

Primary (fetched):

- https://github.com/github/spec-kit — Spec Kit README: commands, layout
- https://github.com/github/spec-kit/blob/main/spec-driven.md — SDD methodology, constitution, "specifications as source of truth"
- https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/plan.md — Constitution Check gate
- https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/tasks.md — task format and derivation
- https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/analyze.md — read-only cross-artifact analysis
- https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/converge.md — gap detection and append-only tasks
- https://raw.githubusercontent.com/github/spec-kit/main/templates/constitution-template.md — governance/amendment fields
- https://kiro.dev/docs/specs/ , https://kiro.dev/docs/specs/feature-specs/ , https://kiro.dev/docs/specs/best-practices/ — spec files, EARS, Refine/Sync Files
- https://kiro.dev/docs/steering/ — inclusion modes, foundation files
- https://kiro.dev/blog/introducing-kiro/ — specs synced with codebase
- https://github.com/Fission-AI/OpenSpec , https://github.com/Fission-AI/OpenSpec/blob/main/docs/getting-started.md — specs vs changes, delta syntax, archive merge rule
- https://github.com/bmad-code-org/BMAD-METHOD — PRD + architecture → stories (mechanics thin)
- https://docs.tessl.io/ — no spec-driven mechanics found
- https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions — Nygard ADR
- https://adr.github.io/ — ADR overview, decision log
- https://adr.github.io/madr/ , https://raw.githubusercontent.com/adr/madr/develop/template/adr-template.md — MADR statuses, Confirmation
- https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html — AWS ADR lifecycle and review use
- https://github.com/npryce/adr-tools — `adr new -s`
- https://github.com/thomvaill/log4brains — docs-as-code ADR log
- https://docs.arc42.org/section-9/ , https://arc42.org/overview — arc42 decisions section
- https://c4model.com/ — C4 abstractions
- https://keeling.dev/essays/architecture-haiku/ — one-page architecture description
- https://www.writethedocs.org/guide/docs-as-code/ — docs as code
- https://agents.md/ — AGENTS.md spec
- https://code.claude.com/docs/en/memory , https://code.claude.com/docs/en/best-practices — CLAUDE.md size, imports, rules, /doctor trims, hooks vs advice
- https://learn.chatgpt.com/docs/agent-configuration/agents-md — Codex discovery and 32 KiB cap
- https://cursor.com/docs/context/rules — rule types, size, reference-not-copy
- https://arxiv.org/abs/2602.11988 , https://arxiv.org/html/2602.11988 — context-file evaluation
- https://en.wikipedia.org/wiki/Requirements_traceability — RTM, bidirectional traceability

Secondary (search results only, not relied on for mechanics):

- https://codemyspec.com/blog/openspec-explained — `openspec validate --strict` description
- https://www.reqview.com/blog/requirements-traceability-matrix/ — ISO/IEC/IEEE 29148 RTM mention
- https://dev.to/krlz/spec-driven-development-in-2026-what-it-is-the-tooling-and-how-teams-actually-use-it-2fk2 — landscape overview
