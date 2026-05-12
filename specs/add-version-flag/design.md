# Add `--version` flag to `scripts/gen-skills-table.sh` — Design

## Approach summary

Insert a small argument-handling block at the top of `scripts/gen-skills-table.sh`, immediately after `set -euo pipefail` and before `REPO_ROOT` is resolved. The block defines a `readonly VERSION="0.1.0"` constant, a `usage()` function, and a `case` statement over `${1:-}` that handles `--version` and `--help` by printing and exiting 0; anything else (including no argument) falls through to the existing flow unchanged.

## Architecture decisions

- **Decision:** Argument parsing as a small inline block; no getopts, no shift loop.
  - **Why:** Only two recognised flags, both mutually exclusive with normal execution, both terminal. A getopts-style loop with shifting is over-engineering and would change the no-argument path. The whole change is ~15 lines.
  - **Alternatives considered:** `getopts` builtin (rejected — overkill, only supports short options); a manual `while [[ $# -gt 0 ]]` loop with `shift` (rejected — implies future flags that aren't on the roadmap).
  - **Risks:** A future flag that needs to compose with `--version` or `--help` would need a refactor. Tolerable; the script is small and the refactor is local.

- **Decision:** Short-circuit before any filesystem checks.
  - **Why:** SC2 + the constraint "must work even if `_base/README.md` is missing or markers are absent" require it. If we let the existing markers-check at line 33 run first, `--help` would fail with a confusing IO error when the user is just asking for help.
  - **Alternatives considered:** Move only `--version` ahead and leave `--help` after (rejected — inconsistent and surprising).
  - **Risks:** None — pure ordering change.

- **Decision:** `VERSION` as a `readonly` constant at the top, not inlined.
  - **Why:** SC4 explicitly asks for a one-line bump path. A `readonly` declaration is the standard bash idiom and is immutable for the rest of the script.
  - **Alternatives considered:** Inline the string in two places (rejected — duplicates the source of truth); read from a `VERSION` file (rejected — adds a file and another check).
  - **Risks:** None.

## Components touched

- `scripts/gen-skills-table.sh` — the only file modified. Insert lines after the existing line 18 (`set -euo pipefail`) and before line 20 (`REPO_ROOT="$(cd ...)"`).

No other files change. No documentation in `_base/README.md` needs updating — the script's `--help` is now self-documenting.

## Data / API / interface changes

CLI surface gains two flags:

```
gen-skills-table.sh           — (unchanged) regenerate the skills table in _base/README.md
gen-skills-table.sh --version — print "gen-skills-table.sh 0.1.0" and exit 0
gen-skills-table.sh --help    — print usage block (mentioning --version) and exit 0
```

No other interface changes. The regeneration behaviour, exit codes for the regeneration path, and the file layout are unaffected.

## Testing strategy

Inline shell assertions (no test framework). The task brief asks the implementer to run each of the following after the edit and capture the output:

- **SC1:** `./scripts/gen-skills-table.sh --version` → stdout is exactly `gen-skills-table.sh 0.1.0` (one line, trailing newline); exit code 0.
- **SC2:** `./scripts/gen-skills-table.sh --help` → stdout contains the substring `--version` and the script exits 0.
- **SC3:** `./scripts/gen-skills-table.sh` (no args, twice) — first run says either `updated …` or `no changes …`; second run says `no changes …`. Idempotent.
- **SC4:** `grep -n '^readonly VERSION=' scripts/gen-skills-table.sh` returns exactly one line, at the top of the script.

No CI hook is added — the script is run on-demand by humans; these are post-edit sanity checks.

## Rollout & reversibility

- **Rollout:** single commit that touches one file. The change is additive — no existing path changes behaviour unless `--version` or `--help` is passed.
- **Reversibility:** revert the commit; the script returns to its current behaviour. Zero state on disk to clean up. No migration concerns.
