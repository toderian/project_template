# Add `--version` flag to `scripts/gen-skills-table.sh` — Tasks

## Parallel groups

The change is confined to a single file; there is no opportunity for file-disjoint parallelism. The work is one task in one group.

### Group 1

- [x] T1.1 Insert version + help handling in `scripts/gen-skills-table.sh` — scope: `scripts/gen-skills-table.sh` — verifies: SC1, SC2, SC3, SC4 — DONE (all four SCs passed; see implementer report)

  Add, immediately after `set -euo pipefail` (existing line 18) and before the `REPO_ROOT="$(cd ...)"` declaration (existing line 20):

  1. A `readonly VERSION="0.1.0"` constant.
  2. A `usage()` function that prints to stdout the following block (use a heredoc):

     ```
     Usage: gen-skills-table.sh [OPTION]

     Regenerate the "Available skills" table in _base/README.md from playbooks/skills/*.md.

     With no option, regenerate the table in place.

     Options:
       --version    Print version and exit.
       --help       Show this message and exit.
     ```

  3. A `case "${1:-}" in` block over the first argument:
     - `--version)` → `printf 'gen-skills-table.sh %s\n' "$VERSION"; exit 0`
     - `--help)` → `usage; exit 0`
     - default `)` → do nothing (fall through to the rest of the script unchanged).

  After the edit, run all four checks from `design.md` § "Testing strategy" and paste their output in the structured report's `Summary` (or `Concerns` if anything failed).

  Do **not** modify any line below the existing `REPO_ROOT` declaration. Do **not** add a `-v` or `-h` short alias. Do **not** add unknown-option handling.

## Fix iterations

_(None yet.)_
