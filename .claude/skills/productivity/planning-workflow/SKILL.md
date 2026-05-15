---
name: planning-workflow
description: Seven-step pre-implementation planning workflow. Use when the user wants to plan a non-trivial change before writing code — multi-file features, multiple plausible approaches, or work that needs scope bounded. Pairs with the plan-critic subagent for adversarial review against the five-axis rubric.
disable-model-invocation: true
---

Use this skill to plan non-trivial changes before implementation.

Read and follow:

- `playbooks/skills/productivity/planning-workflow.md`
- `playbooks/conventions/plan-critique.md`

When adversarial critique is needed, dispatch the plan-critic subagent (`.claude/agents/plan-critic.md`) or apply the rubric on the main thread under `playbooks/personalities/critic.md`.

Keep this skill thin. The playbook is the shared workflow and should be updated first when the process changes.
