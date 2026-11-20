# A `design/` tree as the source of truth: research snapshot

Date: 2026-11-20. Status: research, nothing implemented. Follows
`2026-09-04-architecture-source-of-truth-research.md`, whose recommendations were mostly not built.

## Question

How should a downstream hub repo (RedMesh, Edge Node, Infra) keep one source of truth for how the
product works, what features it has, how each is intended to work and why, split into modules and
submodules, including UI and UX rules, so that every task points at the design file it changes?

## Short answer

1. Add `docs/resources/<area>/design/`: a tree of small Markdown leaves with a generated index in each
   folder. It replaces the flat `contracts/` files and absorbs component contexts.
2. A leaf body states only what the code does now. A change in progress stays in its task file. The
   leaf shows pending changes as a generated table of task IDs, never as behaviour text.
3. Status is one value per leaf, never per section. A leaf for a feature that is designed but not
   built is `draft` or `accepted` as a whole.
4. Each leaf has an append-only Decisions table whose rows name the task or ADR that made them.
5. No new task field is needed. `Spec refs` and the `Resource updates` harvest row already link tasks
   and docs in both directions; what is missing is a check that they resolve and were honoured.
6. UI docs hold roles, rules and rationale. Colour and font values stay in the frontend code, and a
   script checks that token names match.
7. Pilot on RedMesh `engagements` before writing the convention.

## What exists today

### Template

- `agents-tasks:knowledge-base` defines `summary.md`, `contracts/<feature>.md`,
  `components/<slug>/CONTEXT.md`, `system-map.md`, `docs/adr/` and a five-value spec status.
- Task files have an optional `Spec refs` row. `agents-tasks:complete-task` reconciles linked specs at
  closeout, and `plugins/agents-core/hooks/remind-archive-done-todo.sh` refuses to archive a task
  with no `Resource updates` row. The row may say `None`, and nothing checks the paths.
- `at.py` never parses `Spec refs`. No architecture doc or ADR index is seeded.
- Eighteen files in `plugins/` and `scripts/` reference `contracts/`, component contexts or
  `system-map.md`; `knowledge-base` (12 mentions) and `refresh-context` (10) lead.

### RedMesh hub

- 26 contract files, about 17,000 lines; nine are near or over 1,000 lines and
  `data-at-rest-schema.md` is 2,486. A plain file read in Claude Code returns 2,000 lines, so that
  file is truncated unless the agent pages it.
- 5 ADRs, a 1,650-line glossary, a 263-line `summary.md`, no `system-map.md`.
- `Spec refs` appears in 68 of 165 open and 167 of 221 archived tasks; 97 tasks name a contract.
  `Resource updates` appears in 220 of 221 archived tasks; 83 name a contract.
- **Truth layering is the main defect.** `contracts/engagements.md` stacks Target v3, v4, v2 and a
  340-line v1 body, with the rule "a later target wins". No file has a "current behaviour" heading.
- **Docs already contradict each other.** `multi-tenant-workspaces.md:6-9` says RM-107 is not merged;
  `engagements.md:4-6` says it merged on 2026-09-29. ADR 0002 describes an engagement that carries
  Rules of Engagement; `engagements.md:62-65` (Target v4) removed them.
- **Decisions are scattered.** An estimated 150 to 250 dated decisions sit in contract prose, numbered
  "Owner decisions" lists, change logs and task files. The count is a regex estimate, not a tally.
- Roles are tabulated in four different contracts.
- Sections with no obvious home in a design leaf recur in five to seven files each: verification
  matrix, rollout order, compatibility, participant responsibilities.
- About 5,000 lines (`data-at-rest-*`, `continuous-monitoring`, `cssp-deployment-bundle`) describe
  features that are designed but not built.

### Edge Node hub

Eight area summaries of 39 to 91 lines in one shape, a 143-line glossary, and four contracts, all
under `deeploy` (2,785 lines). No ADRs, no recorded intent or decisions, and no design for storage,
container apps or node operations.

### Infra hub

Only `agents-core` is enabled, and the layout predates the task ledger. Durable architecture knowledge
is three files, led by `docs/r1infra/mainnet-edge-node-comms-explained.md` (497 lines); the rest are
incident logs, assessments and tasks.

### Navigator frontend (`/home/vi/work/ratio1/repos/RedMesh-Navigator`)

- Next.js 14, Tailwind 3.4, hand-written components; no Storybook and no design documentation.
- Tokens live in `app/globals.css` and `tailwind.config.ts`, with a third palette copy in
  `lib/pdf/layout/theme.ts`. Five themes are selected per deployment.
- The semantic variables (`--accent`, `--success`, `--surface`) are defined but unused in components.
  The vocabulary in use is the Tailwind slate scale, stock status hues and two brand colours, plus
  about 85 hard-coded hex literals.
- UX rules exist only inside contracts, mostly `multi-tenant-navigator-experience.md:1072-1166`
  (for example "status never by colour alone" at `:1164`).

## Prior art

| Source | What it contributes |
|---|---|
| OpenSpec | Specs state how the system behaves now; a change is a separate folder merged in at archive. Its delta blocks replace whole requirements and have lost content (PR #843). |
| GitHub Spec Kit | Specs are per change, not current truth. Evolving an existing spec is its best-known gap (issue #1191). |
| Kiro | Specs are edited in place; no split between truth and pending. |
| Python PEP 1 | A final proposal is history; behaviour is documented in the reference. `Replaces` and `Superseded-By` are set on both sides. |
| Kubernetes KEP | Keeps the decision status and the rollout stage as two separate fields. |
| C4 | Context and container levels suffice for most teams; the code level is not recommended. |
| arc42 | Hierarchical building blocks; cross-cutting concepts are documented once, centrally. |
| MADR, Nygard, AWS | One decision per ADR, immutable once accepted, superseded by a new one. Putting every decision in an ADR is a known anti-pattern. |
| Anthropic docs | Keep on-demand files under 500 lines, references one level deep, and a contents list in files over 100 lines. |
| arXiv 2602.11988 | Instructions in context files are followed; repository overviews do not improve task success. |
| DTCG tokens, DESIGN.md, Carbon, GOV.UK | Token values are generated reference; roles, usage rules and rationale are hand-written. |

Our task file already plays the role of the OpenSpec change or the PEP, so a second proposal artifact
is not needed. This reverses item 4 of the September research (`propose-change`).

## Recommended design

### Tree

```
docs/resources/<area>/design/
  README.md                    # product level: goals, constraints, generated index
  _crosscutting/<concept>.md   # one concept per file: roles, trust boundary, audit, purge
  <module>/
    README.md                  # purpose in five lines, generated index, pointers
    <feature>.md               # leaf
    <feature>.reference.md     # optional: schema or API catalogue
    <submodule>/README.md + leaves
```

- Depth is at most three levels; most modules stay at two.
- Every leaf is linked from its direct parent README.
- A fact has one owner file. Other files link to it.
- A README holds no feature facts. Its index table is generated from leaf frontmatter into a marker
  block, as `at ledger sync` does for area pages.
- Normative non-Markdown files (`.sql`, fixtures) sit beside the leaf that owns them.
- How-to content stays in `runbooks/`. Verification matrices and rollout logs stay in tasks.

### Leaf

Frontmatter: `summary` (one line), `status`, `code_paths` (globs), `verified` (repo, commit, date).

| Section | Content |
|---|---|
| Intent and why | The problem and the reason this feature exists. |
| Current behaviour | What it does now, with one or two key scenarios. |
| Interfaces | APIs, schemas, events, environment, CLI: what it exposes and depends on. |
| How it works | Mechanism, with links to code paths in place of restated code. |
| Constraints | Invariants, limits and compatibility promises. |
| Decisions | The table below. |
| Pending changes | Generated: task ID, one-line summary, state. Pointers only. |
| Risks and open questions | Known debt and unanswered questions. |

Empty sections are omitted. Evidence is cited inline next to the claim it supports.

Size: aim for 300 lines and split at 500. No source measures an optimum; 500 is Anthropic's published
figure for on-demand agent files.

### Status

One value per leaf, reusing the existing vocabulary: `draft`, `accepted`, `implemented`, `superseded`.
`partially-implemented` is dropped for design leaves because it is the status that permits layered
sections. A leaf is `implemented` when its body matches the code; a change to it lives in a task until
the change lands.

### Decisions

| Field | Content |
|---|---|
| ID | `D-NN`, per file, never reused |
| Date | ISO date |
| Decision | One sentence |
| Why | Names the alternative that was rejected |
| Task | Ledger ID or `ADR-NNNN` |
| Supersedes | `D-NN` or a dash |
| Status | `active` or `superseded by D-NN` |

Rows are append-only; only the Status cell of an old row may change. A decision becomes an ADR when it
passes the existing three-part test, spans more than one design file, or does not fit a row.

### Enforcement

Hard gates, in `at ledger check`, run by pre-commit and CI:

- Every `Spec refs` and `Resource updates` path resolves.
- The Decisions table parses; each task and supersedes target exists; superseding is marked on both
  rows.
- Generated indexes match the files (`--check`).
- A leaf over the size limit fails.

Warnings: a design path in `Spec refs` that the task's commits did not touch; a leaf whose `verified`
date is older than a threshold.

Reviewer only: whether the text matches the code, whether `None` in `Resource updates` is honest, and
whether a decision was made but not recorded. `agents-tasks:verify-task` does this and cites
`path:line` evidence for each changed claim.

One line goes in the seed `AGENTS.md`: a behaviour change updates the design leaf and adds a Decisions
row. No new hook.

### UI and UX module

```
design/navigator/ui/  colors.md  typography.md  layout.md  components.md
design/navigator/ux/  principles.md  patterns.md  accessibility.md
```

- Token row: name, role, must not be used for, implemented in (file and selector), why, task ID.
- No value column. Navigator has five themes, so one value would be wrong for four of them. A
  generated block stamped with the frontend commit can list values if readers want them.
- Principle entry: statement, rationale, a do and a don't example, a yes/no check a reviewer can
  answer from a diff or screenshot, task ID.
- Pattern entry: when to use, when not to use, numbered rules, components used, known gaps.
- Drift check: a stdlib script given the frontend checkout path compares token names in the doc with
  `app/globals.css` and `tailwind.config.ts`, and records the commit it checked.
- A feature's own screens stay in that feature's module and cite these rules.

### Skills and tooling

- `agents-tasks:knowledge-base` gains `references/design-convention.md` and owns the format.
- New skill `agents-tasks:design-doc`: create, refresh or split a leaf. It absorbs
  `agents-tasks:describe-component`, whose leaf shape already covers interfaces and invariants.
- `at design sync` and `at design check` generate and verify indexes and pending tables.
- `agents-tasks:cross-repo-feature`, `agents-tasks:refresh-context`, `agents-tasks:map-system` and
  `agents-tasks:define-area` are repointed from `contracts/` to `design/`.

## Open decisions for the owner

1. **What "current" means.** One researcher recommends folding a change into the leaf at deploy.
   This document recommends at merge to the integration branch, because agents read the doc beside
   the code, and RedMesh has no single deployed state. Deployment state would then live in one place
   per environment, not in feature leaves.
2. **Whether `contracts/` is removed or kept** for true cross-repo agreements in repos that have few
   features.
3. **The RedMesh module boundaries.** The analysis proposes ten modules: tenancy, identity, jobs,
   model-testing, findings, compliance, storage, integrations, deployment, navigator.

## Rollout

1. Pilot: convert RedMesh `engagements` by hand. It has four stacked versions, an ADR that no longer
   matches, and many task links.
2. Write the convention, skill and checks from what the pilot shows.
3. RedMesh: nine contracts move nearly as they are, eight need restructuring, six need splitting
   (`multi-tenant-workspaces.md` into at least six modules).
4. Edge Node: start with `deeploy/design/`, then stubs from each area summary.
5. Infra: enable `agents-tasks`, then build `network/design/` from the three durable files.

## Risks

- Collapsing stacked versions into "current behaviour" needs a check against code for every leaf,
  because the docs already disagree about what is live. No product code was read for this research.
- Recovering 150 to 250 decisions with task IDs is slow manual work.
- A gate that only checks "the file changed" invites trivial edits; the reviewer step is what
  prevents that.
- Agents reading index files is supported by one vendor evaluation only. Test the pilot tree on a few
  real planning tasks before mandating the shape.

## Not verified

- Any measured optimum for file size or tree depth.
- False-positive rates for path-based doc gates.
- Whether Codex reads large files the same way as Claude Code.
- Agreement between the RedMesh contracts and the product code.
- Only part of the 17,000 contract lines was read in full; the rest by headings and excerpts.

## Sources

- https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/docs/concepts.md
- https://github.com/Fission-AI/OpenSpec/pull/843
- https://raw.githubusercontent.com/github/spec-kit/main/spec-driven.md
- https://github.com/github/spec-kit/issues/1191
- https://kiro.dev/docs/specs/
- https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html
- https://peps.python.org/pep-0001/
- https://raw.githubusercontent.com/kubernetes/enhancements/master/keps/NNNN-kep-template/kep.yaml
- https://c4model.com/diagrams
- https://docs.arc42.org/section-5/ and https://docs.arc42.org/section-8/
- https://diataxis.fr/start-here/
- https://adr.github.io/madr/
- https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
- https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html
- https://www.infoq.com/articles/architectural-decision-record-purpose
- https://ozimmer.ch/practices/2020/04/27/ArchitectureDecisionMaking.html
- https://code.claude.com/docs/en/memory
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- https://arxiv.org/abs/2602.11988
- https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals
- https://www.designtokens.org/tr/2025.10/format/
- https://raw.githubusercontent.com/google-labs-code/design.md/main/docs/spec.md
- https://carbondesignsystem.com/elements/color/tokens/
- https://design-system.service.gov.uk/community/contribution-criteria
