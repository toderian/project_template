---
name: spec-workflow
description: Heavyweight spec-driven development loop (plan → build → review → fix) for a single engineering item, producing spec.md / design.md / tasks.md / review.md under specs/<slug>/ and dispatching parallel implementers via the subagent-protocol. Use when the user wants Codex to "spec it out", drive a spec-driven workflow, or plan + build + review a non-trivial feature with parallel subagents. Do NOT use for one-file edits, typos, trivial bug fixes, or exploratory spikes — the default single-agent operating loop is correct for those.
---

# Spec Workflow

Use this skill to run a plan → build → review → fix loop with the four standardized artifacts under `specs/<slug>/`.

Read and follow:

- `playbooks/skills/spec-workflow.md`

Keep this skill thin. The playbook is the shared workflow and should be updated first when the process changes.
