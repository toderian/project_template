---
name: grilling
description: "Grill the user relentlessly about a plan, decision, or idea until every branch of the design tree is resolved. Use when the user wants to stress-test their thinking, says \"grill me\", or another skill needs decisions only the user can make."
metadata:
  source: "github.com/mattpocock/skills@885e2ca skills/productivity/grilling/SKILL.md (adapted)"
  pack: core
---

# Grilling

Interview the user relentlessly until you reach a shared understanding. Map the topic as a
**design tree**: every decision branches into the decisions that hang off it.

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already
settled: the questions you can ask _now_ without guessing at answers you have not heard yet. Ask
the whole frontier in one round, numbered, each with your recommended answer, then wait for the
user's answers before the next round.

Format each question like this:

```
❓ **Q1** - **<question title>**: <question body; may run several paragraphs and offer choices>

➡️ <your recommended answer>
```

Each round of answers reshapes the tree: settled decisions push the frontier outward and unblock
the questions that depended on them. Recompute the frontier and ask the next round. A question whose
answer depends on another question still open in this round belongs to a _later_ round.

Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the
environment (code, tests, docs, tools, the web), dispatch a sub-agent or look it up yourself
(a `researcher` dispatch per `agents-core:subagent-protocol` §"Research dispatch"); never ask the
user for anything you could find. Do not block on it: a running lookup is an unsettled
prerequisite, so only the questions downstream of it wait; ask the rest of the frontier now. The
_decisions_ are the user's: put each one to them and wait.

When the topic has a domain vocabulary or ADR trail, load `agents-extras:domain-modeling` alongside
this skill so questions use the glossary's terms and settled decisions are not re-asked.

The session is done when the frontier is empty: every branch of the design tree visited, nothing
left silently assumed. Close with a short summary — **Decisions made**, **Open questions**
(deferred on purpose), **Risks identified** — and do not act on any of it until the user confirms
you have reached a shared understanding.
