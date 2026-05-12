# Add `--version` flag to `scripts/gen-skills-table.sh`

## Source

Rough intent supplied directly by the user via `/spec-workflow`, captured 2026-05-12. Verbatim:

> Add a --version flag to scripts/gen-skills-table.sh that prints a semver and exits 0; default version 0.1.0; --help should mention --version.

## Problem

`scripts/gen-skills-table.sh` currently has no introspection surface. There is no `--help`, no `--version`, no way for an operator or another script to interrogate the tool. As the script grows (new flags, alternative output paths) it becomes harder to remember the current capabilities or to detect which copy is checked out in a downstream project that pulled an old template version.

## Goal

The script accepts `--version` and `--help`, both exit 0 cleanly without performing the regeneration. `--version` prints a semver. `--help` prints a short usage block that lists `--version` alongside the script's normal behaviour, so a user discovering the flag from `--help` doesn't have to read the source.

## Success criteria

- [ ] SC1: `./scripts/gen-skills-table.sh --version` prints `gen-skills-table.sh 0.1.0` (a single line, trailing newline) and exits 0.
- [ ] SC2: `./scripts/gen-skills-table.sh --help` prints a usage block that includes the line `--version` (and a short description of what it does) and exits 0.
- [ ] SC3: Invoking the script with no arguments still regenerates `_base/README.md` as it does today — running it twice with no arguments is still idempotent (second run prints `no changes`).
- [ ] SC4: The `VERSION` constant lives at the top of the script as a `readonly` shell variable so future bumps are a one-line change.

## Non-goals

- A `-v` short alias. Not requested; not added.
- A `-h` short alias for `--help`. Not requested; not added.
- Behaviour for unknown options (e.g. `--foo`). Out of scope. The script continues to fall through to its normal flow on anything that is not `--version` or `--help`.
- Bumping the version above `0.1.0`. The first version is fixed by the intent.
- Any change to the output format of the regenerated skills table.

## Constraints

- Bash; the existing shebang `#!/usr/bin/env bash` and `set -euo pipefail` must remain.
- No new external dependencies. Argument parsing in plain bash (a `case` over `$1` is enough — there are only two recognised flags).
- `--version` and `--help` must short-circuit **before** any IO or file existence checks, so they work even if `_base/README.md` is missing or the markers are absent.
- Idempotence of the no-argument path must be preserved (covered by SC3).

## Open questions

None. The intent is precise; the defaults below are picked to match common Unix CLI conventions.

### Decided defaults (called out so reviewers don't flag them as gaps)

- **Output format for `--version`:** `gen-skills-table.sh 0.1.0` (tool name + space + semver). Matches GNU coreutils and curl's conventions; reads better in CI logs than a bare `0.1.0`.
- **Output format for `--help`:** a `Usage:` line, a one-paragraph description, and a flag list. Sent to stdout (not stderr) because the user explicitly asked for it; exit 0 is correct in that case.
- **Argument parsing position:** immediately after `set -euo pipefail` and before the `REPO_ROOT` resolution, so the script can answer `--version` / `--help` without making any other assumptions about the filesystem.
