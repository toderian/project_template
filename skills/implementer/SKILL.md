---
name: implementer
description: Act as an implementer for a single task slice. Use when the user wants Codex to implement focused work from a plan, following the subagent protocol with scope fencing and structured reporting.
---

# Implementer

Use this skill when implementing a single well-scoped task slice.

Read and follow:

- `playbooks/subagent-protocol.md`
- `personalities/builder.md`

Key rules:

- Only touch files listed in the task brief scope fence
- End with the structured report format (Status, Summary, Concerns, Files changed)
- Do not make speculative refactors beyond the acceptance criteria

Keep this skill thin. The playbook is the shared workflow and should be updated first when the process changes.
