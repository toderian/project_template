---
name: writing-for-agents
description: "How to write any document an agent consumes: skills, AGENTS.md/CLAUDE.md, and docs reached by a pointer. Covers context pointers, context vs cognitive load, progressive disclosure, completion criteria, leading words, and pruning. Use when creating or editing a skill, editing AGENTS.md or CLAUDE.md, or writing a doc an agent will be pointed at."
metadata:
  source: "github.com/mattpocock/skills@885e2ca skills/productivity/writing-for-agents/SKILL.md (adapted)"
  pack: dev-tooling
---

# Writing for Agents

Reference for writing any document an agent consumes: a skill, an `AGENTS.md` / `CLAUDE.md`, a doc
reached by a pointer. The packaging differs; the writing does not. The same levers make each one
predictable, since the agent takes the same _process_ every run rather than producing the same output.

When the document is a skill, read [references/skill-mechanics.md](references/skill-mechanics.md) for
frontmatter, the invocation choice, router skills, and this marketplace's constraints.

## Context pointers

A **context pointer** is a reference held in the agent's context that names some out-of-context
material and encodes the condition for reaching it. A skill's `description` is one; a line in
`AGENTS.md` naming a doc is the same object. The pointer's _wording_, not its target, decides when
the agent reaches the material, and how reliably. A must-have target behind a weakly worded pointer
is a variance bug: sharpen the wording first, and inline the material only if sharpening fails.

A pointer does two jobs: state what the material is, and list the **branches** that should trigger
reaching it (a branch is a distinct case the document handles, so different runs take different paths
through it). Every word of an always-loaded pointer costs on every turn, so it earns harder pruning
than the body:

- **Front-load the leading word** — the pointer is where it does its triggering work.
- **One trigger per branch.** Synonyms that rename a single branch are one branch written twice.
- **Cut identity the body already carries.**

Agents under-trigger more often than they over-trigger, so name the concrete contexts the document
should fire in, including ones the user may never phrase explicitly.

## The two loads

Every document and pointer you add spends one of two budgets:

- **Context load** — the cost of always-loaded material on the agent's window: an `AGENTS.md` line, a
  skill description, anything sitting in context every turn, spending tokens and attention whether or
  not it fires.
- **Cognitive load** — the cost on the human: which documents exist and when to reach for each. The
  human is the index. Not a cost to minimise; it is the price of human agency. Spend it where human
  judgement matters, remove it where it does not.

Material reached only through a pointer escapes context load at the price of the pointer's own line;
material with no pointer at all rides entirely on cognitive load.

## Information hierarchy

A document is built from two content types: **steps** (the ordered actions the agent performs) and
**reference** (definitions, rules, facts consulted on demand). The two mix freely: all steps (a
recipe), all reference (a review's rules, this skill), or both. The core decision is where each piece
sits on the **information hierarchy**, a ladder ranked by how immediately the agent needs it:

1. **In-file step** — the primary tier: what the agent does, in order.
2. **In-file reference** — consulted on demand. Often a legitimately flat peer-set (every rule of a
   review on one rung), which is a fine arrangement, not a smell.
3. **Disclosed reference** — pushed into a separate file behind a context pointer, loaded only when
   the pointer fires. Spans a sibling `references/` file through fully external material any document
   can point at.

Push too little down and the top bloats; push too much and you hide material the agent needs. That
tension is the whole decision.

**Progressive disclosure** is the move down the ladder so the top stays legible — not primarily a
token optimisation, it is how the hierarchy is protected. Branching is the cleanest test: inline what
every branch needs, push behind a pointer what only some branches reach. In a document with steps,
in-file reference that should have been disclosed buries them and turns attending to them into a
coin-flip.

**Co-location** is the within-file companion: the ladder decides how far down a piece sits,
co-location decides what sits beside it. Keep a concept's definition, rules and caveats under one
heading rather than scattered, so reading one part brings its neighbours with it. (Distinct from
duplication: that repeats one meaning in two places; scattering fragments one meaning across many.)

**Sprawl** is the failure mode: a document simply too long, even when every line is live and unique.
Attention thins across the excess. The cure is the ladder — disclose reference behind pointers, and
split by branch or sequence so each path carries only what it needs.

## Steps and completion criteria

Every step ends on a **completion criterion**, the condition that tells the agent the work is done.
Two properties make it a lever:

- **Clarity** — can the agent tell done from not-done? A vague bound ("understanding reached")
  invites **premature completion**: ending the step before it is genuinely done, attention slipping
  to _being done_. The visible steps still ahead supply the pull; the criterion's clarity is the
  resistance. Sharpen the bound first (local and cheap); only if it is irreducibly fuzzy _and_ you
  observe the rush, hide the later steps by splitting the sequence — and that only works across a
  real context boundary (a hand-off or a subagent dispatch), since an inline call leaves the later
  steps in context.
- **Demand** — how much it requires. "Every modified model accounted for" forces thorough work where
  "produce a change list" does not. Demand drives the digging the agent does within the work, and it
  is not step-bound: "every rule applied" binds a body of flat reference just as "every step done"
  binds a sequence.

The strongest criteria are both checkable and exhaustive.

## When to split

Splitting one document into two spends one of the two loads, so split only when the cut earns it:

- **By sequence** — split a run of steps where the later ones tempt the agent to rush the one in
  front of it. Keeping them out of view drives more legwork on the current task. The reverse holds
  too: merging sequences invites premature completion.
- **By invocation** — skill-specific; see [references/skill-mechanics.md](references/skill-mechanics.md).

## Leading words

A **leading word** is a compact concept already living in the model's pretraining that the agent
thinks with while running the document (_lesson_, _fog of war_, _tracer bullets_). Repeated as a
token, never as a sentence, it accumulates a distributed definition and anchors a whole region of
behaviour in the fewest tokens, by recruiting priors the model already holds. Coining your own works
if you define it clearly, but a made-up word recruits no priors: you pay in definition tokens what a
pretrained word gives free. Reach for an existing word first.

It anchors twice. In the body, _execution_: the agent reaches for the same behaviour every time the
word appears. In a pointer, _invocation_: when the same word lives in your prompts, your docs and
your codebase, the agent links that shared language to the material and reaches it more reliably.

Hunt for refactors into leading words — a triad spelled out at three sites, a pointer spending a
sentence to gesture at one idea:

- "fast, deterministic, low-overhead" → _tight_ (a _tight_ loop).
- "a loop you believe in" → _red_, turning a fuzzy gate into a binary observable state.

**Negation** is the failure mode beside this lever: steering by prohibition drags the forbidden
behaviour into context and makes it _more_ available, not less. _Don't think of an elephant_, and the
elephant is all there is. Prompt the **positive**: state the target behaviour so the banned one is
never spoken. A prohibition earns its place only as a hard guardrail you cannot phrase positively;
even then, pair it with the positive target.

## Pruning

- Keep each meaning in a **single source of truth**, so changing the behaviour is a one-place edit.
  **Duplication** costs maintenance and tokens, and inflates a meaning's prominence past its real
  rank. (The accidental inverse of a leading word, which repeats a token on purpose, never the
  meaning.)
- The **environment** is a source of truth too (`package.json` scripts, config files, the directory
  layout, `--help` output), and a document that restates it is a **cache**: a copy of a lookup,
  earning its load only when the lookup is expensive. Cache what the agent cannot find by looking —
  the unwritten convention, the reason behind a choice, the gotcha no config confesses.
- Check every line for **relevance**: does it still bear on what the document does? A line loses
  relevance by never bearing on the task, or by going stale. Without a pruning discipline the default
  fate is **sediment**: stale layers that settle because adding feels safe and removing feels risky.
- Hunt **no-ops** sentence by sentence: an instruction the model already obeys by default pays load
  to say nothing. The test — does it change behaviour versus the default? — is model-relative, and is
  settled by running the document, not by debate. When a sentence fails, delete the whole sentence
  rather than trim words from it. The test also grades leading words: a word too weak to beat the
  default (_be thorough_ when the agent is already thorough-ish) is a no-op, and the fix is a stronger
  word (_relentless_), not a different technique.
- Explain the **why** behind a non-obvious instruction. Reasoning produces robust behaviour where a
  terse rule produces brittle behaviour; all-caps MUSTs and rigid step ladders are a yellow flag that
  the reasoning is missing.
