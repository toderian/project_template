---
name: doubt-driven-development
description: Subject a non-trivial implementation decision to a fresh-context adversarial review before it stands, by dispatching a reviewer that gets the artifact and its contract but not your reasoning. Use when the user wants Codex to "doubt" or stress-test a decision, when correctness matters more than speed, when working in unfamiliar code, or when a decision branches logic, crosses a module boundary, asserts an unverifiable property, or is hard to reverse.
---

Use this skill to run a fresh-context adversarial review of an implementation decision before it stands.

Read and follow:

- `playbooks/skills/engineering/doubt-driven-development.md`

It reuses `playbooks/skills/productivity/subagent-protocol.md` (dispatch + status vocabulary), the
`plan-critic` subagent with `playbooks/conventions/plan-critique.md` (plan-shaped decisions), and
`playbooks/personalities/critic.md` (code-level decisions).

Keep this skill thin. The playbook is the shared workflow and should be updated first when the process changes.
