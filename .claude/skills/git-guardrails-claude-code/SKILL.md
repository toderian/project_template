---
name: git-guardrails-claude-code
description: Set up Claude Code hooks to block dangerous git commands (push, reset --hard, clean, branch -D, etc.) before they execute. Use when user wants to prevent destructive git operations, add git safety hooks, or block git push/reset in Claude Code.
disable-model-invocation: true
---

Use this skill to set up git safety guardrails via Claude Code hooks.

Read and follow:

- `playbooks/git-guardrails-claude-code.md`

The hook script is bundled at `.claude/skills/git-guardrails-claude-code/scripts/block-dangerous-git.sh`.

Keep this skill thin. The playbook is the shared workflow and should be updated first when the process changes.
