# Contributing to agents-template

Rules for working **in this repository** (the marketplace itself). The contract that ships
to downstream repos is `plugins/agents-core/seed/AGENTS.md` — a different file with a
different audience. Read `README.md` first for the layout.

## Sources of truth vs generated files

Edit only the sources. Everything else is written by `python3 scripts/build.py`.

| Source of truth | Generates |
|---|---|
| `plugins/*/.claude-plugin/plugin.json` | `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, `plugins/*/.codex-plugin/plugin.json` |
| `plugins/*/hooks/hooks.json` | `plugins/*/hooks/hooks.codex.json` |
| `plugins/agents-core/agents/*.md` | `plugins/agents-core/codex/agents/*.toml` (copied into the seed) |

Generated files carry a GENERATED banner: never hand-edit one, build and commit instead.

## Before every commit

```bash
python3 scripts/build.py          # if you touched a source above
bash scripts/tests/run-all.sh     # build --check, plugin validation, hook/ledger/CLI tests
```

Install the gate once with `scripts/install-pre-commit.sh`; after that the pre-commit hook
runs `run-all.sh` on every commit — never bypass it with `-n`, fix the cause. CI
(`.github/workflows/check.yml`) runs every part of it that does not need the Claude Code CLI.

Commit messages: `type: summary`, then `What changed:` / `Why:` / `Checks:` sections.

## Writing skills

- One `SKILL.md` per skill, ≤ 500 lines. Longer material goes to `references/`,
  templates to `assets/`, executables to `scripts/`.
- Spec-shaped: what to do, in what order, with what checks — not an essay.
- `description` is harness-neutral ("Use when …"), ≤ 1,024 characters, and never names a
  specific product UI. It is the only thing the model sees before loading the skill.
- `disable-model-invocation: true` only for side-effect-heavy skills a human should start.
- Keep `metadata.source` provenance when moving an existing skill.
- Put a skill in the plugin that matches its audience (see the table in `README.md`);
  `agents-core` stays small because it is always enabled.

## Versioning and release

All four plugins share one version. Bump them together:

```bash
scripts/release.sh <X.Y.Z>        # edits the four plugin.json, builds, tests, commits, tags v<X.Y.Z>
git push && git push --tags
```

Never edit a version by hand — `build.py --check` will fail on a marketplace that
disagrees with a manifest.

## Boundaries

- No vendored third-party code, skills or plugins. Point at their marketplaces instead.
- No new runtime dependencies: bash, `python3` (stdlib only) and `jq` for hooks.
- Downstream-owned content belongs in a `seed/` directory, never in a skill body.
