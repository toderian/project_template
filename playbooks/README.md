# Playbooks

This directory stores agent-neutral workflow instructions shared across Codex and Claude.

Design rule:

- `playbooks/` stores reusable workflow logic
- `skills/` stores Codex skill wrappers
- `.claude/skills/` stores Claude Code skill wrappers
- both point to playbooks as the single source of truth

When changing a workflow, update the relevant playbook first and keep the agent-specific wrappers thin.
