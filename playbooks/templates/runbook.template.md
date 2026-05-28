# <Scenario Name> - Runbook

| Field | Value |
|-------|-------|
| Area | <area> |
| Status | draft |
| Local bindings | .local/runbooks/<scenario-slug>.local.md |
| Last reviewed | YYYY-MM-DD |

## Purpose

What this helps the agent do.

## When to use

Concrete triggers for this scenario.

## Prerequisites

- Required access, tools, repo state, or safety approvals.

## Placeholders

| Placeholder | Meaning | Safe to commit? |
|-------------|---------|-----------------|
| `<HOST>` | SSH target or service host. | No |
| `<USER>` | Login user or account name. | No |
| `<SERVICE>` | Service name used by the procedure. | Only if explicitly approved |
| `<REMOTE_PATH>` | Remote working path. | No |
| `<CONFIG_PROFILE>` | Named configuration profile. | Only if explicitly approved |

## Procedure

1. Run commands or instructions using placeholders only.
2. Keep environment-specific values in the local bindings file.

## Expected results

What success looks like.

## Failure signals

What bad output means and what to inspect next.

## Safety and cleanup

Destructive risks, secrets handling, cleanup commands.
