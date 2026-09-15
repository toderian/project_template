---
name: subagent-protocol
description: "Multi-agent coordination protocol with status vocabulary, dispatch format, and two-stage review. Use when the user wants to dispatch subagents, coordinate multi-agent work, or review implementation output."
metadata:
  source: playbooks/skills/productivity/subagent-protocol.md
  pack: core
---

# Subagent Protocol

## Purpose

Define how agents dispatch, communicate with, and review subagent work. This is the authoritative reference for multi-agent coordination in any project using this template.

For writing good task briefs, see `agents-extras:github-triage` skill references/AGENT-BRIEF.md.

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

Specialized subagents may add a domain verdict line such as `## Verdict: PASS | FAIL` or
`## Plan verdict: PROCEED | REVISE | BLOCKED`, but the top-level `## Status:` line must still use the
shared vocabulary above so parent workflows can route escalation consistently.

## Report format

Every subagent must end with a structured report block:

```
## Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
## Summary: one-line description of what was accomplished or why progress stopped
## Concerns: (if DONE_WITH_CONCERNS) specific items the parent should evaluate
## Blocking on: (if NEEDS_CONTEXT or BLOCKED) what is needed to continue
## Files changed: list of files created or modified
```

## Artifacts as files, verdicts in chat

Anything longer than a verdict goes to a file and comes back as a path. The parent's context is the
scarce resource: it should hold the brief paths, the report paths, and the status blocks — never a
report body, a diff, or a test log.

- The dispatch prompt names the brief file to read and the report file to write. Implementers write
  the file and reply in at most 15 lines ending with the status block. Reviewers are read-only, so
  their reply *is* the report (status block first, evidence after, at most 40 lines) and the parent
  saves it to the file it named.
- The parent passes paths forward (brief, diff package, prior report), not contents. A reviewer reads
  the diff file; it does not receive the implementer's report pasted into its prompt.
- A run that spans phases records its state in a file the parent rewrites (see `agents-core:execute-plan`,
  references/run-state.md); a fresh session resumes from that file, not from chat history.

## Dispatch briefing format

When dispatching a subagent, the parent must construct a self-contained prompt with:

1. **Task description**: what to build or review, in concrete terms
2. **Acceptance criteria**: testable conditions that define done
3. **Scope fence**: files and directories the subagent may touch, and those it must not
4. **Personality**: which role card to follow (e.g. the `builder` personality (subagent-protocol skill, references/personalities/builder.md))
5. **Context files**: explicit list of files to read — not "read everything"
6. **Model hint**: suggested model class (see model selection below)

Do not assume the subagent inherits any context from the parent session. The briefing prompt is the sole data channel.

## Research dispatch

A question that needs facts from docs, APIs, source code, or the web goes to a background
`researcher` so the main thread keeps moving (inline: the researcher personality,
references/personalities/researcher.md). The brief names the question, the primary sources to prefer
(official docs, source, specs — not write-ups of them), and the report path:
`docs/resources/_reports/research/<YYYY-MM-DDTHHMMSS+ZZZZ>_<slug>.md` when `docs/resources/` exists,
otherwise the repo's own convention. The researcher cites every claim and says when a claim has no
primary source. Its reply is the short answer plus the path; durable conclusions graduate into
`docs/resources/` through `agents-tasks:distill-knowledge`.

## Escalation rules

- **DONE**: proceed to review
- **DONE_WITH_CONCERNS**: parent evaluates concerns — either accept or re-dispatch with clarification
- **NEEDS_CONTEXT**: parent answers the question and re-dispatches with additional context
- **BLOCKED**: parent must triage — provide more context, break the task down further, try a more capable model, or escalate to the human

Never re-dispatch with an identical prompt. If a subagent failed, change something before retrying.

Never ignore an escalation or force the same approach without changes.

## Fix loop

When a review returns `FAIL` or blocking findings, the parent runs at most **three** fix rounds per
slice, then adjudicates. Each round hands the implementer the numbered open-findings list verbatim
(never a paraphrase, never the whole review) and is followed by a re-review scoped to those findings
and the fix diff only.

| Round | Who | Prompt |
|---|---|---|
| 1–2 | the same implementer, resumed where the runtime allows; otherwise a fresh dispatch with the findings file | "Address findings 1..n; do not touch anything else." |
| 3 | a fresh implementer on the strongest model class | "A prior implementer attempted this slice twice; you own it now. Findings: …" |

At the cap the parent decides each open finding itself and records the decision as one line the
next reader can audit:

```
Ruling: <finding> — <decision: fixed by parent | accepted as-is | parked> — cost if wrong: <one clause>
```

Stop with `BLOCKED` only when every path forward is a guess; a defect the parent can fix in a few
lines is fixed by the parent and recorded as a ruling.

## Two-stage review

Review implementation in two stages, in order:

1. **Spec compliance**: does the diff satisfy the acceptance criteria from the task brief?
2. **Code quality**: maintainability, clarity, regressions, security

There is no point reviewing code quality if the implementation does not match the specification. If spec compliance fails, send back to the implementer before requesting a quality review.

The brief's `Stage: spec | quality | both` line selects what a `reviewer` runs. When the parent owns
the merge of verdicts, the two stages may run as two parallel read-only reviewers on the same diff;
a spec `FAIL` still sends the slice back before quality findings are acted on.

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
| Fix round 3 after two failed rounds | Strongest (Opus-class) | Fresh perspective on a slice that resisted two attempts |

When the plan is specific enough (exact file paths, code snippets, acceptance criteria), cheaper models can execute reliably.

## Recursive mitigation

Subagents should NOT load the full skill framework or read the root `AGENTS.md` operating contract. Their task brief is self-contained. This prevents:

- wasted tokens scanning irrelevant skills
- confused agents that lose focus on their narrow assignment
- context pollution from loading the full operating contract

The parent is responsible for including everything the subagent needs in the dispatch prompt.
