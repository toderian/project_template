# Subagent Protocol

## Purpose

Define how agents dispatch, communicate with, and review subagent work. This is the authoritative reference for multi-agent coordination in any project using this template.

For writing good task briefs, see `playbooks/skills/github-triage/AGENT-BRIEF.md`.

## When to dispatch subagents

Stay single-agent unless at least one of these is true:

- the task splits cleanly into independent subproblems
- specialized roles (implementer, reviewer) materially improve reliability
- the context would otherwise grow too large for one session
- parallel execution justifies the coordination cost

If the work is tightly coupled, stay single-agent and emulate roles sequentially.

## Status vocabulary

Every subagent must end its work with one of these statuses:

- **DONE**: task completed, all acceptance criteria met
- **DONE_WITH_CONCERNS**: task completed but the subagent has flagged doubts — parent evaluates concerns before proceeding
- **NEEDS_CONTEXT**: subagent lacks information to continue — parent provides context and re-dispatches
- **BLOCKED**: task cannot be completed as specified — parent must triage

## Report format

Every subagent must end with a structured report block:

```
## Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
## Summary: one-line description of what was accomplished or why progress stopped
## Concerns: (if DONE_WITH_CONCERNS) specific items the parent should evaluate
## Blocking on: (if NEEDS_CONTEXT or BLOCKED) what is needed to continue
## Files changed: list of files created or modified
```

## Dispatch briefing format

When dispatching a subagent, the parent must construct a self-contained prompt with:

1. **Task description**: what to build or review, in concrete terms
2. **Acceptance criteria**: testable conditions that define done
3. **Scope fence**: files and directories the subagent may touch, and those it must not
4. **Personality**: which role card to follow (e.g. `playbooks/personalities/builder.md`)
5. **Context files**: explicit list of files to read — not "read everything"
6. **Model hint**: suggested model class (see model selection below)

Do not assume the subagent inherits any context from the parent session. The briefing prompt is the sole data channel.

## Escalation rules

- **DONE**: proceed to review
- **DONE_WITH_CONCERNS**: parent evaluates concerns — either accept or re-dispatch with clarification
- **NEEDS_CONTEXT**: parent answers the question and re-dispatches with additional context
- **BLOCKED**: parent must triage — provide more context, break the task down further, try a more capable model, or escalate to the human

Never re-dispatch with an identical prompt. If a subagent failed, change something before retrying.

Never ignore an escalation or force the same approach without changes.

## Two-stage review

Review implementation in two stages, in order:

1. **Spec compliance**: does the diff satisfy the acceptance criteria from the task brief?
2. **Code quality**: maintainability, clarity, regressions, security

There is no point reviewing code quality if the implementation does not match the specification. If spec compliance fails, send back to the implementer before requesting a quality review.

### Skepticism directive for reviewers

The implementer's self-report may be incomplete or optimistic. Verify independently:

- read the actual diff, not the summary
- check each acceptance criterion against the code
- look for untested edge cases and silent regressions
- do not trust "all tests pass" without checking what the tests actually verify

## Model selection

Guidance for choosing subagent model class. Availability varies by platform.

| Task type | Model class | Rationale |
|-----------|-------------|-----------|
| Exploration, search, file lookup | Fastest (Haiku-class) | Low complexity, high volume |
| Mechanical implementation with detailed plan | Fast (Haiku/Sonnet-class) | Plan provides all decisions |
| Multi-file integration | Default (Sonnet-class) | Needs cross-file reasoning |
| Architecture, complex review | Strongest (Opus-class) | Judgment-heavy, high stakes |

When the plan is specific enough (exact file paths, code snippets, acceptance criteria), cheaper models can execute reliably.

## Recursive mitigation

Subagents should NOT load the full skill framework or read AGENTS.md. Their task brief is self-contained. This prevents:

- wasted tokens scanning irrelevant skills
- confused agents that lose focus on their narrow assignment
- context pollution from loading the full operating contract

The parent is responsible for including everything the subagent needs in the dispatch prompt.
