# Simplicity audit: does agents-template make agents do the simplest plan that works?

Audited on: 2026-09-15, against v1.4.4. Two inputs: a primary-source survey of vendor guidance on
agent instructions, skills, plans and multi-agent work, and a full read of every `SKILL.md`, agent
card, hook and the seed `AGENTS.md`. Outcome: release 1.5.0 (the "What 1.5.0 changed" section).

## Verdict

The principles were right and the process skills contradicted them. The seed contract said "one
agent running the passes in sequence beats orchestration" and "smallest surgical change"; the skills
agents actually run made the simplest tracked task go through six subagent dispatches, three review
gates, a 17-field task form and a template with three empty placeholder sections.

## Sources and the rules taken from them

| Rule | Source |
|---|---|
| Add complexity only when it demonstrably improves outcomes; simplest solution first | [Building effective agents](https://www.anthropic.com/research/building-effective-agents) |
| Smallest set of high-signal tokens; subagents return a distilled summary (~1–2k tokens) | [Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) |
| "Claude is already very smart. Only add context Claude doesn't already have"; one default plus one escape hatch; SKILL.md < 500 lines, references one level deep | [Agent Skills best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) |
| CLAUDE.md under ~200 lines; "Would removing this cause Claude to make mistakes? If not, cut it"; hooks for what must happen every time; "if you could describe the diff in one sentence, skip the plan"; chasing every reviewer finding leads to over-engineering | [Memory](https://code.claude.com/docs/en/memory), [Best practices](https://code.claude.com/docs/en/best-practices) |
| Subagents for verbose output, tool restriction, self-contained work; main conversation when planning, implementation and testing share context | [Sub-agents](https://code.claude.com/docs/en/sub-agents) |
| Multi-agent ≈ 15× the tokens of a chat; coding has few truly parallel parts | [Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) |
| Maximise a single agent first; split for complex branching or tool overload, not by default | [A practical guide to building agents](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf) |
| Contradictory or vague instructions hurt more than length; skip plans for the easiest ~25 % of tasks; never end with only a plan | [GPT-5 prompting guide](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide), [Codex prompting guide](https://github.com/openai/openai-cookbook/blob/main/examples/gpt-5/codex_prompting_guide.ipynb) |
| AGENTS.md is a README for agents; Codex caps project docs at 32 KiB | [agents.md](https://agents.md/), [Codex AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md) |

## Scorecard (16 testable criteria)

| # | Criterion | v1.4.4 | v1.5.0 |
|---|---|---|---|
| 1 | Seed AGENTS.md ≤ 200 lines | 153 | 138 |
| 2 | AGENTS.md holds facts and rules; procedures live in skills | yes | yes |
| 3 | Every line survives "would removing it cause mistakes?" | anti-patterns duplicated principles; 5-line caveman bullet | fixed |
| 4 | At most one emphasised rule per file | yes | yes |
| 5 | SKILL.md ≤ 500 lines, references one level deep | yes (max 369) | yes (max 348) |
| 6 | Skills state outcomes and checks, not narration | mostly | mostly |
| 7 | One default path + one escape hatch per skill | execute-plan, add-task, complete-task had no escape hatch | small/large rung; core template; trivial-task note |
| 8 | Exact-command steps only for fragile ops | yes | yes |
| 9 | Each skill justified by an observed gap | 5 aliases/duplicates | removed |
| 10 | Every-time behaviour is a hook; lint in CI | hook wording claimed a block it cannot make | reworded |
| 11 | Plans skipped for one-sentence diffs; never single-step, never plan-only | planning-workflow only | seed loop + execute-plan rung |
| 12 | Single agent by default; subagents for isolation, parallelism, fresh-eyes review | 6 dispatches minimum per task | 1 reviewer per phase in small mode |
| 13 | Every delegation carries objective, format, tools, boundaries; ≤ ~2k tokens back | yes | yes |
| 14 | No two skill descriptions overlap in trigger | planning cluster of 6, grill cluster of 4 | 2 planning entry points, 1 grilling |
| 15 | No contradictory rules across seed, skills, downstream | AGENTS.md:32 vs execute-plan | consistent |
| 16 | Reviewer prompts scoped to correctness and stated requirements; one gate per stage | critique demanded 2 rounds and "at least one gap" | score decides |

## The five findings (v1.4.4, file:line)

1. **execute-plan had no small-task path.** `execute-plan/SKILL.md:42-56, 194-206, 236-245, 306-311`
   mandated plan-critic + fresh implementer + two phase reviewers + two final reviewers, ≥ 5 artifact
   files per phase, and a branch/autonomy resolution "mandatory even when the task looks single-repo".
   Real run CALC-001 (two five-line functions): 15 dispatches, $2.68.
2. **The task file was a 17-field / 12-section form** (`todo-convention.md:267-282, 437-464`) and
   `add-task:89-91` wrote three empty placeholder sections at creation. The validator already
   required only 8 fields; the prose demanded the rest.
3. **Gates fired on trivial work.** `todo-convention.md:466-494` three reviews before any existing
   task; `plan-critique.md:63-76` two rounds minimum and "a round must surface at least one gap";
   `remind-archive-done-todo.sh:67-69` printed BLOCKED from a PostToolUse hook that cannot block.
4. **Six planning skills emitted the same artifact** (planning-workflow, task-spec-workflow,
   spec-workflow, prd-to-plan, add-task, roadmap), kept apart by "lightweight/heavyweight cousin"
   prose; grill-me and grill-with-docs were pure aliases; research wrapped the researcher agent.
5. **Reference cycles.** 9 A↔B cycles and a 9-hop chain; wayfinder named 11 skills, task-ledger 10.

Corrected during planning: the audit first called both todo hooks "hard blocks". Only the filename
hook blocks (PreToolUse); the archive reminder is PostToolUse and only prints. An exit-0 hook's
stderr never reaches the model, so "warn only" would have meant "silent". Both hooks stayed.

## What 1.5.0 changed

- Task template reduced to a required core (8 metadata rows, brief, phases, criteria); optional rows
  and sections added when first needed; log, harvest and summary written when they happen; the
  pre-implementation gate is a ≤ 3-line note for a trivial task. Repo registry and spec lifecycle
  moved to their own references.
- Five skills removed with successors documented; `at doctor` warns on a downstream table that still
  routes to one.
- Seed AGENTS.md: 153 → 138 lines; trivial-diff exemption; merged planning rows; two new rows.
- execute-plan picks a rung: small (implement yourself, one `Stage: both` reviewer per phase, one
  final reviewer for two phases) by default; large (the unchanged pipeline) on any trigger; program
  (wayfinder) above that. `at task run --mode`.
- plan-critique: the score decides, no minimum rounds.
- Skill references: hand off once, never describe a peer; the worst offenders trimmed by hand.
- New: `agents-tasks:simplify-task` and `agents-tasks:verify-task` (prior art: GSD verifier and
  plan-checker, superpowers verification-before-completion, Spec Kit analyze/clarify, OpenSpec verify;
  none reduces a plan to its minimum, none separates a met criterion from one changed mid-task).

## Measurement: small mode on a real task

CALC-002 (two phases: `divide` with a zero guard, `power`) driven by `at task run --harness claude
--model sonnet` after the change:

| Metric | v1.4.x CALC-001 (large) | v1.5.0 CALC-002 (small) |
|---|---|---|
| Dispatches | 15 | 5 (2 implementer, 2 phase reviewers, 1 final reviewer) |
| Claude spend | $2.68 | $0.91 |
| Fix rounds | 1 wasted (mis-scoped spec review) + 3 blocked | 0 |
| Outcome | both phases committed, final PASS ×2 | both phases committed, final PASS, acceptance criteria ticked, 11 tests green |

The single `Stage: both` reviewer returned the per-item checklist verdicts first, as the prompt asks,
so the spec scoping problem that cost CALC-001 a fix round did not recur.

Compare CALC-001 under v1.4.x: 15 dispatches, $2.68, one wasted fix round from a mis-scoped spec
review.

## Exercise: the two new skills on the same workspace

- `verify-task` on CALC-002 (run by hand as the orchestrator, with a real `spec-validator` and a
  real `Stage: both` reviewer): all four criteria MET with three evidence locations each, tests
  rerun (11, rc=0), drift `unchanged` for every criterion, spec-validator PASS 4/4, reviewer PASS
  with three minor findings (tracked `__pycache__` churn, the zero-division message not pinned by a
  test, a generated area page in the diff). Verdict PASS, recommendation accept. Two skill defects
  found and fixed on the spot: the first drift recipe reported checkbox ticks as changes (now a
  per-commit form that drops tick pairs), and the scope check needed the generated ledger pages
  named as expected noise.
- `simplify-task` on a deliberately padded CALC-003 (four phases, five criteria, TBD spec and
  design, placeholder log/harvest/summary): 4 → 1 phases, 5 → 3 criteria; cut the current-state
  phase, a duplicate criterion and every placeholder section; merged the tests phase into the
  implementation phase; deferred configurable rounding to Follow-ups with its trigger. The
  approval stop was simulated (scratch workspace). `at ledger check` clean afterwards.

## Not changed, deliberately

- `block-bad-todo-name.sh` stays a block: cheap, deterministic, and `at ledger check` would fail the
  commit anyway.
- The codebase-design cluster keeps its hub-and-spoke references; `spec-workflow` stays for
  multi-session `specs/<slug>/` work; `doubt-driven-development` stays unrouted.
- The repo still does not run its own task manager on itself; the next change to this repo should.
- `at task run` still stages the phase with `git add -A` (the skill says explicit pathspecs); it
  relies on the workspace's `.gitignore`, which is how CALC-002's commits picked up `__pycache__`.
  Found by `verify-task`'s scope check; a driver-side fix is a follow-up.
