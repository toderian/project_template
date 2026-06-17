# Loop Engineering Digest

| Field | Value |
|-------|-------|
| Digest date | 2026-06-17 |
| Source | Addy Osmani, "Loop Engineering", published 2026-06-07, https://addyosmani.com/blog/loop-engineering/ |
| Supporting source | OpenAI Codex Manual, fetched 2026-06-17 through `openai-docs`, `/codex/subagents.md` and `/codex/concepts/subagents.md` |
| Area | global |
| Copyright note | This digest is paraphrased. It avoids long excerpts and records only operational takeaways relevant to this template. |

## Core Takeaways

Loop engineering shifts the engineer's leverage point from repeatedly prompting an agent to designing a
repeatable system around the agent. In the article's framing, a useful loop discovers work, assigns or
performs it, checks the result, records state, and decides the next action without requiring the human
to hand-prompt every step.

The article names six recurring building blocks:

- scheduled or trigger-based automations
- isolated workspaces, often Git worktrees
- skills that preserve project knowledge and operating rules
- plugins and connectors that let the loop touch external tools
- subagents or equivalent reviewer separation
- durable memory outside the active conversation

The safety message is more important for this template than the novelty of the term. Faster loops
increase the cost of weak verification, weak source-of-truth boundaries, and weak human review. A loop
that can act across tools, repos, branches, tickets, or private connectors needs explicit stop points
and auditable permissions.

## Template Consequences

- Treat autonomy as a permission ceiling layered on top of existing repo work rules. It should never
  replace branch policy, task scope, runtime sandboxing, or explicit user instructions.
- Keep L1 as the default. Local edits, tests, iteration, and local commits are already the template's
  normal execute-plan loop.
- Require explicit opt-in for L2/L3 behavior because push, CI repair, and draft PR creation change
  external state.
- Keep maker/checker separation as a recommended loop shape, but do not assume subagents may be used
  unless the active runtime and user authorization permit them.
- Prefer isolated worktrees for parallel loops, but still require ownership boundaries and review
  capacity. Worktree isolation prevents file collisions; it does not remove integration risk.
- Keep state in durable files: task execution logs, plan files, resource digests, ledgers, and PR
  notes. Do not rely on a single conversation as the only loop memory.
- Connector/MCP access must be least-privilege by autonomy level. Read-only inspection and private
  data reads are different permissions from writing to issue trackers, docs, Slack, GitHub, or
  production APIs.

## Source Notes

Addy Osmani's article is the conceptual source for the loop-engineering framing and the six-part loop
anatomy. The Codex manual is the source for current Codex custom-agent file placement and the rule
that Codex only spawns subagents when explicitly asked. The local template adoption narrows both into a
conservative operating contract: default local execution, explicit escalation for publish behavior, and
clear boundaries around live connector writes.

## Open Questions

- Which downstream repos should ever opt into L2 or L3 by default, if any?
- Should CI repair loops require a separate branch allowlist in addition to repo `Work mode`?
- Should future template checks enforce autonomy metadata in task files, or keep it optional and
  validation-only when present?
