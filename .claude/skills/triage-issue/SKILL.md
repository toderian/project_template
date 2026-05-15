---
name: triage-issue
description: Triage a bug or issue through a two-role state machine (category + state) and produce a `ready-for-agent` GitHub issue with a TDD-based fix plan, by exploring the codebase to find the root cause. Use when the user wants to "triage" a bug, investigate an issue, file an issue, plan a fix, or move an issue toward `ready-for-agent`.
disable-model-invocation: true
---

Use this skill to investigate bugs and file TDD fix plans as GitHub issues.

Read and follow:

- `playbooks/skills/triage-issue.md`

Keep this skill thin. The playbook is the shared workflow and should be updated first when the process changes.
