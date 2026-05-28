# Global Runbooks

Use this directory for committed, sanitized runbooks that are not owned by a narrower area.

Runbooks live at:

```text
docs/resources/<area>/runbooks/<scenario-slug>.md
```

Keep real hostnames, account names, private paths, customer names, and reusable local values in:

```text
.local/runbooks/<scenario-slug>.local.md
```

Use placeholders such as `<HOST>`, `<USER>`, `<SERVICE>`, `<REMOTE_PATH>`, and
`<CONFIG_PROFILE>` in committed runbooks. See `playbooks/conventions/runbook-convention.md` and
`playbooks/templates/runbook.template.md`.
