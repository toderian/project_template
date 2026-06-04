---
name: doubt-driven-development
description: Adversarial review for a non-trivial implementation decision before it stands. Use when the user asks to "doubt" or stress-test a decision, when correctness matters more than speed, or when the choice crosses module boundaries, asserts something hard to verify, or is hard to reverse.
---

Use this skill to run a fresh-context adversarial review of an implementation decision before it stands.

Read and follow:

- `playbooks/skills/engineering/doubt-driven-development.md`

It reuses `playbooks/skills/productivity/subagent-protocol.md` (dispatch + status vocabulary), the
`plan-critic` subagent with `playbooks/conventions/plan-critique.md` (plan-shaped decisions), and
`playbooks/personalities/critic.md` (code-level decisions).

Keep this skill thin. The playbook is the shared workflow and should be updated first when the process changes.
