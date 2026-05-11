---
name: spec-workflow
description: Heavyweight spec-driven development loop (plan → build → review → fix) for a single engineering item, with four artifacts under specs/<slug>/ (spec.md, design.md, tasks.md, review.md) and parallel implementer dispatch via the subagent-protocol. Use when the user asks to "spec it out", run a spec-driven workflow, plan + build + review a non-trivial feature, parallelize implementer subagents against a written design, or mentions "spec workflow" / "spec-driven". Do NOT use for one-file edits, typos, trivial bug fixes, exploratory spikes, or anything the default single-agent operating loop can handle in one pass — this skill is intentionally heavy.
disable-model-invocation: true
---

Read and follow:

- `playbooks/skills/spec-workflow.md`

Keep this skill thin. The playbook is the shared workflow and should be updated first when the process changes.
