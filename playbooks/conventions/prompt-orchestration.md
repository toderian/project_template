# Prompt Orchestration Convention

## Purpose

Prompt orchestration is the repo-owned harness around long or repeatable agent work: task state,
workbook commands, prompts, evidence gathering, verification, critique, and checkpointing.

Use this convention when a downstream project needs a repeatable way to plan the next slice of a
long-running task, especially when the task already lives in `docs/tasks_manager/_todos/` and has a
related workbook. Do not make a LangChain, LangGraph, or agent-framework dependency the default for
every project. Add a runtime only when the workflow needs durable branching, retries, checkpoint/resume,
or parallel lanes that cannot be handled by a small prompt script plus task/workbook files.

## Decision Tree

Choose the smallest orchestration pattern that controls the actual failure mode.

| Pattern | Use when | Keep it out when |
| --- | --- | --- |
| Plain prompt script | The next step can be chosen from existing task state, workbook commands, and a short checklist | The script would need hidden mutable state, provider calls, or complex branching |
| Prompt chain | The work has a fixed sequence of artifacts such as intake, evidence, plan, verification, critique, checkpoint | Later steps frequently change shape based on earlier results |
| Evaluator loop | Outputs can be judged against clear criteria, tests, schemas, or review rubrics | The evaluator only gives ungrounded approval or repeats the same prompt |
| LangGraph-style workflow graph | The workflow needs durable state, checkpoint/resume, branching, retries, human interrupts, or parallel lanes | The only goal is to run a few prompts in order |
| Subagents | Independent roles materially improve quality or reduce context pressure, such as researcher, implementer, tester, reviewer | The task is tightly coupled, lacks clear ownership boundaries, or coordination cost exceeds value |

Default path:

1. Start with a plain prompt script or workbook checklist.
2. Add a prompt chain when intermediate artifacts need named gates.
3. Add an evaluator loop when quality can be checked against explicit criteria.
4. Add a graph runtime only after durable state or branching is the bottleneck.
5. Add subagents only when ownership and review boundaries are explicit.

## Task Taxonomy

Task prefixes are routing hints, not a replacement for task files or area docs.

| Prefix family | Typical meaning | Orchestration implication |
| --- | --- | --- |
| `F-*` | Feature or product slice | Start from acceptance criteria, current phase, related workbook, tests, and rollout notes |
| `D-*` | Defect, diagnosis, or debug correction | Start from reproduction, observed failure, minimal fix hypothesis, regression test, and verification |
| `C-*` | Chore, cleanup, convention, or infrastructure | Start from affected conventions, compatibility, migration risk, and template/downstream impact |
| `R-*` | Research, report, or resource distillation | Start from source inventory, provenance, synthesis target, and follow-up task criteria |
| `<AREA>-*` | Area-scoped task such as `RMM-*`, `EGM-*`, `RM-*`, or `EG-*` | Read the area summary, component docs, related contracts/runbooks, and repo registry rows for that area |
| `T-*` | Global template or cross-area task | Read template conventions, global resources, setup/check scripts, and downstream impact docs |

When a task combines families, route by the riskiest remaining work. For example, a model/eval feature
with artifact outputs should use feature acceptance criteria plus evaluation and artifact-registry
checks. A debug task with generated corrections should use reproduction and regression verification
before any polish work.

## Downstream Checklist

Before planning the next long-task slice, collect only the files needed to answer these questions:

- Task file: which phase is current, which acceptance criteria are still open, and what changed in the
  execution log?
- Area docs: which `docs/resources/<area>/summary.md`, component contexts, contracts, runbooks, or
  dependency graphs constrain the task?
- Repo registry: which `.config/repos.project.md` rows, `.local/repos.map` paths, work modes, branches,
  and autonomy ceilings apply?
- Related workbook: which `workbooks/<related-workbook>/README.md` commands, scripts, samples, outputs,
  and methodology apply?
- Artifact registry: do generated, large, encrypted, external, or reproducible outputs need
  `artifacts/README.md` entries?
- Local-only data: do credentials or private prompts belong under `.creds/`, `.no-commit/`, or another
  ignored path?
- Evals/tests: which deterministic checks, benchmark slices, regression tests, or human review gates
  prove the next slice?
- Current phase: what is the smallest reviewable next action and what stop point proves it is done?
- Blockers: what missing credential, artifact, source doc, failing baseline, or unresolved decision
  should stop the loop?

## Workbook-Backed Long-Task Loop

Use this read-only planning loop before starting an implementation slice:

```text
intake -> current-state review -> classify task -> select next phase -> gather workbook commands
       -> plan next slice -> verify plan -> critique risks -> checkpoint
```

The seeded workbook `_base/workbooks/prompt-orchestration-long-task/` contains a standard-library
helper that reads a task file and related workbook README, then prints a deterministic next-slice
brief. Downstream projects can copy it to `workbooks/prompt-orchestration-long-task/` with
`_base/scripts/seed-docs.sh` or by explicitly adopting the workbook.

Example downstream command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 workbooks/prompt-orchestration-long-task/scripts/plan_next_slice.py \
  --task docs/tasks_manager/_todos/<TASK>.md \
  --workbook workbooks/<related-workbook>/README.md
```

## LangGraph Adoption Guidance

Document LangGraph or LangChain as an optional downstream choice, not as a template default.

Adopt a graph runtime when at least one of these is true:

- the workflow must resume from checkpoints after crashes, interruptions, or human review
- the same task can branch into materially different next states
- retries and fallbacks need first-class state instead of ad hoc prompt text
- independent lanes run in parallel and later join with explicit merge rules
- trace replay, state inspection, or production observability is required

If a downstream project adopts LangGraph, add the dependency in that project with its chosen Python
tooling environment, preferably `tools/python/` with `uv` when it is repo-level tooling. Keep graph
state schemas, traces, evals, and prompts in the related workbook or application package, and document
how to migrate from the simple workbook loop.

## Non-Goals

- Do not create a new task schema.
- Do not replace `docs/tasks_manager`.
- Do not bypass `/complete-task` when a task is implemented or cancelled.
- Do not add default LangChain, LangGraph, or provider SDK dependencies to the template.
- Do not grant new autonomy permissions. Branch, commit, push, PR, connector, and secret rules remain
  governed by `AGENTS.md`, `.config/repos.project.md`, and `playbooks/conventions/autonomy-levels.md`.
