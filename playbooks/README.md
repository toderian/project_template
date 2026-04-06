# Playbooks

This directory stores agent-neutral workflow instructions shared across Codex and Claude.

Design rule:

- `planning/` stores state
- `playbooks/` stores reusable workflow logic
- `skills/` stores Codex adapters
- `.claude/skills/` stores Claude adapters
- `.claude/agents/` stores Claude-specific subagents

When changing a planning workflow, update the relevant playbook first and keep the agent-specific wrappers thin.
