# Connectors And MCP

## Purpose

Connectors and MCP servers let an agent read or write live systems: GitHub, Google Drive, Slack,
Linear, databases, internal APIs, cloud consoles, and similar tools. Treat them as external-state
permissions, not as ordinary file reads.

This convention defines least-privilege connector behavior by autonomy level. It complements
`playbooks/conventions/autonomy-levels.md`; the strictest safety, runtime, work-mode, branch, repo,
task, connector, or user rule wins.

## Core Rules

- Prefer connectors for private workspace data. Do not use web search or model memory to infer private
  issue, PR, document, calendar, Slack, or account state when an authorized connector exists.
- Request or use only the connector scopes needed for the task.
- Do not print, summarize, commit, or copy secret values. Local credentials belong under `.creds/`
  and must remain uncommitted.
- Treat live writes as separate from live reads. Reading a PR is not permission to comment on it;
  reading a document is not permission to edit it.
- Keep source-of-truth boundaries explicit. Durable project knowledge goes in `docs/resources/`;
  volatile connector state stays in the external system unless the user asks to record a sanitized
  summary.
- Record connector actions in task execution logs, plan logs, PR bodies, or reports when they affect
  project state.

## Autonomy Matrix

| Level | Connector Reads | Connector Writes |
|-------|-----------------|------------------|
| L0 | Allowed when needed for inspection and authorized by the connector. | Not allowed. Report recommended actions instead. |
| L1 | Allowed when needed to implement or verify local work. | Local repo writes only. External writes require asking. |
| L2 | Allowed for the approved branch/CI workflow. | Narrow writes needed to update the approved branch or CI evidence; no broad issue/doc/chat writes. |
| L3 | Allowed for draft PR validation. | Narrow draft PR creation/update and status validation. Stop before ready-for-review, merge, deploy, release, or broad notification writes. |

Broad connector writes include creating or editing issues outside the named task, editing shared docs,
posting to team chat, changing labels/project boards at scale, modifying cloud resources, updating
production data, or writing to any system not named in the task. No autonomy level grants these by
default.

## Secrets

- Read `.creds/` only when credentialed access is required for the task.
- Prefer explicit credential filenames from the user. If discovery is necessary, list filenames only;
  do not print contents.
- Never write credential values into tracked docs, task files, logs, prompts, PR bodies, comments,
  reports, or final answers.
- If a connector returns secrets, tokens, private keys, cookies, or credential-like values, redact
  them immediately and record only that sensitive data was present.

## MCP Server Selection

Before using an MCP server or connector, identify:

- data owner and workspace/account
- read versus write action
- target object, such as repo, PR, issue, doc, sheet, channel, database, or API endpoint
- required autonomy level
- where the action will be logged

If more than one connector could perform the action, choose the narrowest one. For example, use a
GitHub PR connector for PR metadata instead of a broad browser session, and use a Sheets connector for
a named spreadsheet instead of exporting an entire Drive folder.

## Stop Points

Stop and ask before:

- enabling a new connector or expanding scopes
- writing to a connector target not named by the user/task
- changing production, billing, permissions, secrets, or deployment state
- posting broad notifications
- syncing external data into committed docs beyond a sanitized summary
- continuing after a connector response exposes sensitive data unexpectedly

## Logging Template

Use this compact log entry for connector actions:

```md
Connector action:
- Connector: <name>
- Target: <repo/pr/doc/etc>
- Mode: read | write
- Autonomy: <effective level>
- Result: <sanitized result>
- Follow-up: <none or human decision needed>
```
