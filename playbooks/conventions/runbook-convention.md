# Operational Runbooks Convention

## Purpose

Repeated agent-assisted operational workflows need a reusable home that does not commit private
environment details. Use runbooks for SSH, setup, debugging, deployment inspection, service restart,
and similar procedures that an agent or human will run again.

The split is:

- committed, sanitized procedure: `docs/resources/<area>/runbooks/<scenario-slug>.md`
- local-only placeholder bindings: `.local/runbooks/<scenario-slug>.local.md`

Use `global` as the area for cross-cutting workflows that are not owned by a narrower area.

## When to create a runbook

Create or update a runbook when:

- the same setup, SSH, debugging, or inspection workflow is likely to recur
- the user has answered the same operational values more than once
- a task or incident produced a reusable procedure that future agents should find before asking
  questions

Do not turn raw transcripts, terminal dumps, or one-off investigation logs directly into runbooks.
Store those in the right knowledge lane first:

- raw notes, transcripts, or pasted logs: `docs/resources/_inbox/`
- distilled reusable facts from raw sources: `docs/resources/_digests/<area-or-bucket>/...`
- rerunnable investigation output: `docs/resources/_reports/<workflow>/...`
- durable source documents and binaries: `docs/resources/<area>/attachments/` with Markdown metadata
- reusable workbook bundles with scripts/support files: `workbooks/<workbook-slug>/`

Promote only stable, repeatable procedure steps into a runbook.

## Committed runbooks

Committed runbooks must be safe to share with the repo. They use placeholder names for environment
values:

- `<HOST>`
- `<USER>`
- `<SERVICE>`
- `<REMOTE_PATH>`
- `<CONFIG_PROFILE>`
- `<LOG_PATH>`
- `<PORT>`

If a value is not explicitly approved as safe to commit, keep it out of the runbook and put it in the
local binding file. This applies to real hostnames, account names, private paths, customer names,
internal service labels, and reusable placeholder values.

Never commit secrets, private keys, tokens, passwords, recovery codes, or equivalent credentials in
runbooks or local-binding templates.

Use this shape:

```md
# <Scenario Name> - Runbook

| Field | Value |
|-------|-------|
| Area | <area> |
| Status | draft/active/deprecated |
| Local bindings | .local/runbooks/<scenario-slug>.local.md |
| Last reviewed | YYYY-MM-DD |

## Purpose

What this helps the agent do.

## When to use

Concrete triggers.

## Prerequisites

- Required access, tools, repo state, or safety approvals.

## Placeholders

| Placeholder | Meaning | Safe to commit? |
|-------------|---------|-----------------|
| `<HOST>` | SSH target or service host. | No |
| `<USER>` | Login user or account name. | No |
| `<REMOTE_PATH>` | Remote working path. | No |

## Procedure

1. Step-by-step commands and instructions using placeholders only.

## Expected results

What success looks like.

## Failure signals

What bad output means and what to inspect next.

## Safety and cleanup

Destructive risks, secrets handling, cleanup commands.
```

See `playbooks/templates/runbook.template.md` for a copyable template.

## Local bindings

Local binding files live under `.local/runbooks/`, which is ignored by git. They map placeholders to
real values for one or more profiles:

```md
# <Scenario Name> - Local Bindings

> Local-only. Do not commit.

## Profiles

### <profile-name>

| Placeholder | Value | Notes |
|-------------|-------|-------|
| `<HOST>` | <local host value> | SSH target |
| `<USER>` | <local user value> | Login user |
| `<REMOTE_PATH>` | <local remote path> | Working path |
```

Use profile names such as `prod-a`, `devnet`, `staging`, or `customer-x` when the same runbook applies
to multiple environments. Profiles may include sensitive operational context because the file is
local-only, but do not store credentials there unless the project explicitly allows that local
practice.

See `playbooks/templates/runbook.local.template.md` for a local-only starter.

## Discovery

Before asking the user to repeat setup or debugging details, agents should check:

1. `docs/resources/<area>/runbooks/*.md` for the affected area.
2. `docs/resources/global/runbooks/*.md` for cross-cutting procedures.
3. `.local/runbooks/<scenario-slug>.local.md` for machine-local placeholder values.

If the committed runbook exists but local bindings are missing or incomplete, ask only for the missing
placeholder values and suggest recording them in `.local/runbooks/`.

## Review checklist

Before committing a runbook:

- all procedure commands use placeholders for private values
- every placeholder is defined in the placeholders table
- the `Local bindings` row points at `.local/runbooks/<scenario-slug>.local.md`
- no secrets, private keys, tokens, private hostnames, private account names, or private paths are
  present unless the user explicitly marked the non-secret value safe to commit
- raw transcripts or rerunnable output were kept in `_inbox`, `_digests`, or `_reports` instead of
  pasted into the runbook
