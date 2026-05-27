# Codex Plugins

Place repo-provided Codex plugins in this directory.

Bundled plugins:

- `superpowers`: planning, TDD, debugging, review, and branch-finishing workflows.
- `github`: PR, issue, CI, review-comment, and publishing workflows.

Each plugin should use the standard plugin layout:

```text
plugins/
└── example-plugin/
    ├── .codex-plugin/
    │   └── plugin.json
    ├── skills/
    ├── hooks/
    ├── assets/
    ├── .mcp.json
    └── .app.json
```

Only `.codex-plugin/plugin.json` is required. Optional folders and files depend on what
the plugin provides.

Normal setup should use the one-command installer from the repo root:

```bash
./scripts/setup-agents.sh
```

Use `./scripts/setup-agents.sh --codex-only` for a Codex-only refresh.

To install only the local Codex plugins, run:

```bash
./plugins/install-codex-plugins.sh
```

The installer symlinks each plugin into `~/plugins/<plugin-name>` by default and
adds it to `~/.agents/plugins/marketplace.json` so Codex can discover it as a
local marketplace plugin.
