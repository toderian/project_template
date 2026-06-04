# Doubt-Driven Development

## Purpose

Subject every non-trivial decision to a fresh-context adversarial review *before it stands* — during
implementation, not just at the planning stage. The technique: materialize a reviewer that receives
the smallest reviewable artifact plus its contract, but **not** your reasoning, and let it try to
break the decision against the actual text. A confident answer is not a correct one; this skill is
how you find out which kind you have.

Use this when correctness matters more than speed, when working in unfamiliar code, or when the cost
of being wrong is high. It complements `grill-with-docs` (which interrogates a *plan* with the user)
and the `plan-critic` subagent (which scores a *plan*); doubt-driven-development operates one level
down, on individual implementation decisions as they are made.

## When it fires

Run a doubt cycle before a decision becomes final when it:

- **branches logic** — introduces a conditional, a new code path, or a state transition whose
  behavior you have not proven
- **crosses a module boundary** — changes a contract, signature, or assumption another module relies on
- **asserts an unverifiable property** — claims something is "safe", "atomic", "idempotent", or
  "backwards-compatible" without a test or proof in hand
- **carries irreversible blast radius** — data migration, deletion, schema change, or anything costly
  to undo once shipped

Do **not** run a cycle on trivial or reversible decisions. If a decision is easy to reverse, you'll
just reverse it; spending a review round on it is waste. Mirror the discipline of the ADR offer test
(`playbooks/conventions/adr-convention.md`): no real trade-off, no irreversibility → skip the doubt.

## The fresh-context reviewer

Dispatch the reviewer using the dispatch briefing format in
`playbooks/skills/productivity/subagent-protocol.md`. The single most important rule comes from that
protocol: **"the briefing prompt is the sole data channel."** That property is exactly what makes the
review adversarial — the reviewer cannot be anchored by reasoning you never sent it.

Hand the reviewer only:

1. **The smallest reviewable artifact** — the specific diff, function, query, or interface under
   doubt, not the whole change.
2. **The contract** — what this artifact must guarantee: inputs, outputs, invariants, error behavior,
   the acceptance criteria it answers to.
3. **A refute-first instruction** — ask it to find where the artifact violates the contract, default
   to "broken" when uncertain, and ground every finding in a quote from the actual text.

Deliberately withhold your justification, your "why I think this is fine", and your confidence level.
Those are precisely the anchors a fresh-context review exists to avoid.

## Review engine

Pick the engine that fits the decision:

- **Plan-shaped decisions** (an approach, a sequencing, a structural choice) — dispatch the existing
  `plan-critic` subagent (`.claude/agents/plan-critic.md`) against the five-axis rubric in
  `playbooks/conventions/plan-critique.md`. Do not restate or fork that rubric here; reference it so
  there is one definition.
- **Code-level decisions** (this function, this query, this boundary) — run the critic stance from
  `playbooks/personalities/critic.md`. Require each finding to be classified against the actual text:
  a quoted line plus the contract clause it violates. Reject vibe-level objections ("feels fragile")
  with no anchor.

Either way the reviewer reports back using the shared status vocabulary (below), so escalation routes
consistently.

## Stop rule

Iterate, but bound it:

- Stop when the latest round surfaces only trivial findings (nits, style, nothing that touches the
  contract), **or**
- Stop after **3 rounds**, whichever comes first.

Between rounds, change the artifact in response to real findings before re-dispatching. Per the
subagent protocol escalation rule, **never re-dispatch an identical prompt** — if a round changed
nothing, either the finding was unreal or you have not actually addressed it. Three rounds with
non-converging findings means the decision is genuinely hard: escalate to the human rather than
looping.

## Report

Close each cycle with the subagent-protocol report block. The top-level status must use the shared
vocabulary:

- **DONE** — the decision survived review; findings are trivial or resolved.
- **DONE_WITH_CONCERNS** — the decision stands but the reviewer flagged residual risk you are
  knowingly accepting; record why.
- **NEEDS_CONTEXT** — the reviewer could not judge the decision without information the contract
  omitted; supply it and re-run.
- **BLOCKED** — the decision is unsound as written and you cannot resolve it in three rounds;
  escalate.

If the decision was both hard-to-reverse and the result of a real trade-off, the surviving decision
is also a candidate for an ADR (`playbooks/conventions/adr-convention.md`).

---
*Adapted from [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) (MIT License).*
