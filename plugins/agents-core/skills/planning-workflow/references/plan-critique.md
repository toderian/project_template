# Plan Critique Convention

## Purpose

A shared rubric for adversarial plan review. Used by the plan-critic subagent (`.claude/agents/plan-critic.md`) and applicable on the main thread when running the critic personality manually.

The point is to catch weak plans before any code is written. A plan that survives this rubric is genuinely strong; a plan that does not is cheaper to revise now than to rework later.

## The five axes

Every plan is scored on these five axes. Each axis gets a 1–5 score with a one-line justification grounded in evidence — a grep result, a file path, a citation — not a vibe.

1. **Assumption audit** — what does the plan assume that is not yet verified? Unstated dependencies, environmental requirements, behavioral guarantees.
2. **Scope creep** — is the plan doing more than necessary? Could a significant fraction be deferred? Is there gold-plating disguised as completeness?
3. **Existing solutions** — has the author actually checked whether this already exists? Codebase grep, web search, library survey.
4. **Minimalism** — what is the smallest change that gets the outcome? Every new file, abstraction, or dependency must justify itself.
5. **Uncertainty** — what is most likely to go wrong? Where is the plan speculative or where would failure be costly?

## Scoring scale

| Score | Label | Meaning |
|---|---|---|
| 1 | Critical gap | Blocking — plan cannot proceed as-is |
| 2 | Significant concern | Must address before implementation |
| 3 | Adequate | Minor improvements possible but not required |
| 4 | Strong | No issues found |
| 5 | Exemplary | Above expectations |

## Verdict mapping

After scoring all five axes, compute the composite (arithmetic mean) and apply:

| Composite | Axis floor | Verdict |
|---|---|---|
| ≥ 3.0 | no axis below 2 | **PROCEED** |
| < 3.0 OR any axis at 1 | — | **REVISE** |
| < 2.0 OR two or more axes at 1 | — | **BLOCKED** |

The mapping is fixed. A verdict that does not match the scores is invalid.

## Calibration anchors

Reference points to keep scores stable across reviewers and sessions.

| Axis | Score 1 (critical) | Score 3 (adequate) | Score 5 (exemplary) |
|---|---|---|---|
| Assumption audit | plan assumes an API exists but grep shows it does not | assumptions are plausible but unverified | every assumption verified with grep/web evidence cited inline |
| Scope creep | plan includes work explicitly OUT of scope | reasonable scope, one or two tangential additions | plan addresses only the stated problem, nothing more |
| Existing solutions | no search performed; plan rebuilds what exists | partial search (codebase OR web, not both) | comprehensive search with specific evidence cited |
| Minimalism | plan creates 5+ new files when 1–2 would do | reasonable but could prune 1–2 unneeded files or abstractions | irreducible — every file is load-bearing |
| Uncertainty | no contingency for known-risky parts | risks named, mitigation vague | every high-risk area has a specific mitigation |

## Required output

A critique round MUST produce:

- score per axis with a one-line evidence-based justification
- composite score (arithmetic mean across all five axes)
- one of PROCEED / REVISE / BLOCKED, following the verdict mapping
- on REVISE: the concrete changes required before re-review
- on round ≥ 2: a delta column showing change since the previous round

## Minimum rounds

A plan does not earn PROCEED in a single round unless it is genuinely trivial. Scale by complexity:

- 1 round — trivial plans (single file, single concern)
- 2 rounds — typical plans
- 3 rounds — plans touching multiple components, or any plan whose previous round contained a score of 1

If round N produces PROCEED but the previous round contained any score of 1, run one more round to confirm convergence.

## Failure modes to prevent

- issuing PROCEED while any axis sits at 1
- providing only positive feedback — a round must surface at least one gap until convergence
- accepting claims without evidence — unverified claims score 1 on Assumption Audit
- assigning Existing Solutions a score above 1 without citing a search result
- overriding the verdict mapping or softening verdicts with qualifiers ("mostly proceed", "soft block")
- inventing critiques to look thorough when an axis is genuinely strong

## Output template

```
## Verdict: PROCEED | REVISE | BLOCKED

### Scores
| Axis | Score | Delta | Evidence |
|---|---|---|---|
| Assumption audit | [1-5] | [+/-N or —] | [grep, citation, file path] |
| Scope creep | [1-5] | [+/-N or —] | [evidence] |
| Existing solutions | [1-5] | [+/-N or —] | [evidence] |
| Minimalism | [1-5] | [+/-N or —] | [evidence] |
| Uncertainty | [1-5] | [+/-N or —] | [evidence] |
| **Composite** | **[mean]** | **[+/-N]** | |

### Issues found (REVISE/BLOCKED)
- [specific issue with evidence]

### Required changes (REVISE)
1. [concrete change]

### Strengths (PROCEED)
- [what is good about this plan]

### Remaining risks accepted (PROCEED)
- [risks acknowledged as acceptable]
```
