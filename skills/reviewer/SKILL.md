---
name: reviewer
description: Two-stage review of implementation work. Use when the user wants Codex to review completed task output for spec compliance and code quality.
---

# Reviewer

Use this skill when reviewing implementation work.

Read and follow:

- `playbooks/subagent-protocol.md`
- `personalities/reviewer.md`
- `personalities/critic.md`

Key rules:

- Stage 1: verify spec compliance against acceptance criteria before anything else
- Stage 2: review code quality only after spec compliance passes
- Verify independently — do not trust the implementer's self-report
- End with the structured report format (Status, Spec compliance, Quality issues, Summary)

Keep this skill thin. The playbook is the shared workflow and should be updated first when the process changes.
