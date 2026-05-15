---
name: align
description: Check a proposed feature or change against the project's PROJECT.md (vision, goals, scope, constraints) and report ALIGNED, NEEDS_CLARIFICATION, or OUT_OF_SCOPE. Use when the user wants Codex to validate alignment before starting non-trivial work or before planning. Requires PROJECT.md at the repo root.
---

# Align

Use this skill to check feature alignment against the project's PROJECT.md before non-trivial work.

Read and follow:

- `playbooks/skills/productivity/align.md`
- `playbooks/conventions/plan-critique.md` (for the broader pipeline context — `/align` sits in front of planning and plan critique)

Prerequisite: `PROJECT.md` at the repo root with at least Vision, Goals, and Out of scope filled in. If missing, copy from `_base/PROJECT.md.template`. Do not invent goals or scope on the user's behalf.

Keep this skill thin. The playbook is the shared workflow and should be updated first when the process changes.
