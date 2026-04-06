---
name: git-guardrails-claude-code
description: Set up Claude Code hooks to block dangerous git commands (push, reset --hard, clean, branch -D, etc.) before they execute. Use when the user wants Codex to help prevent destructive git operations or add git safety hooks. Note: the hook mechanism is Claude Code specific.
---

# Git Guardrails for Claude Code

Use this skill to set up git safety guardrails via Claude Code hooks.

Read and follow:

- `playbooks/git-guardrails-claude-code.md`

The hook script is bundled at `.claude/skills/git-guardrails-claude-code/scripts/block-dangerous-git.sh`.

Keep this skill thin. The playbook is the shared workflow and should be updated first when the process changes.
