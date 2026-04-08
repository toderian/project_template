---
name: implementer
description: Act as an implementer for a single task slice. Use when implementing focused work from a plan, following the subagent protocol with scope fencing and structured reporting.
disable-model-invocation: true
---

Read and follow:

- `playbooks/subagent-protocol.md`
- `playbooks/personalities/builder.md`

Key rules:

- Only touch files listed in the task brief scope fence
- End with the structured report format (Status, Summary, Concerns, Files changed)
- Do not make speculative refactors beyond the acceptance criteria

Keep this skill thin. The playbook is the shared workflow and should be updated first when the process changes.
