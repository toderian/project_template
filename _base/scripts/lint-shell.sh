#!/usr/bin/env bash
#
# Optional shellcheck lint pass over template-owned, repo-authored shell
# scripts. Vendored plugin subdirectories (e.g. _base/plugins/superpowers/)
# are intentionally excluded — that's upstream content, not maintained here.
#
# Skips cleanly (exit 0) when shellcheck isn't installed: this is optional
# local tooling, not a hard requirement for check-template-update.sh to pass.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if ! command -v shellcheck >/dev/null 2>&1; then
  printf 'SKIP  shellcheck not installed (install it to enable this check)\n'
  exit 0
fi

cd "${REPO_ROOT}" || exit 1

# -P (source search path) lets shellcheck resolve the repo's
# `# shellcheck source=...` directives, which are written relative to each
# sourcing script's own directory (_base/scripts/ or skills/).
SHELLCHECK=(shellcheck -x -P _base/scripts -P skills --severity=style)

failed=0

while IFS= read -r -d '' file; do
  "${SHELLCHECK[@]}" "${file}" || failed=1
done < <(
  {
    find _base/scripts -type f -name '*.sh' -print0
    find _base/scripts/git-hooks -type f -print0
    find .claude/hooks -type f -name '*.sh' -print0
    find skills -type f -name '*.sh' -print0
    find _base/plugins -maxdepth 1 -type f -name '*.sh' -print0
  }
)

exit "${failed}"
