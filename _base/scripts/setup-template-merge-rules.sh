#!/usr/bin/env bash
#
# Configure Git merge drivers and the root .gitattributes block used when a
# downstream project pulls updates from the agents template remote.

set -euo pipefail

MODE="write"

usage() {
  cat <<'EOF'
Usage: _base/scripts/setup-template-merge-rules.sh [--check]

Install or verify the template merge rules for this repository.

What it manages:
  - local Git merge drivers:
      template-keep-local     keep downstream-owned files during template merges
      template-keep-upstream  accept template remote files during template merges
  - a marked block in the root .gitattributes file

Options:
  --check   Verify only; do not write Git config or .gitattributes.
  --help    Show this message.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check)
      MODE="check"
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      printf 'unknown option: %s\n\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ATTRIBUTES_FILE="${REPO_ROOT}/.gitattributes"

read -r -d '' MANAGED_BLOCK <<'EOF' || true
# BEGIN agents-template merge rules
# Managed by _base/scripts/setup-template-merge-rules.sh.
# Keep project-specific attributes outside this block.

# Avoid conflicts when downstream projects add their own attributes.
.gitattributes merge=union

# Downstream-owned files and seeded project workspaces keep the local version
# during template-remote merges. Ordinary project branch merges use normal
# three-way file merging.
AGENTS.md merge=template-keep-local
README.md merge=template-keep-local
CHANGELOG.md merge=template-keep-local
LICENSE merge=template-keep-local
PROJECT.md merge=template-keep-local
CONTEXT.md merge=template-keep-local
.config/repos.project.md merge=template-keep-local
docs/** merge=template-keep-local
workbooks/** merge=template-keep-local

# Upstream-owned base files accept the template remote's version during
# template-remote merges. Ordinary project branch merges use normal three-way
# file merging.
_base/** merge=template-keep-upstream
# END agents-template merge rules
EOF

check_driver() {
  local key="$1" expected="$2"
  local actual

  actual="$(git -C "${REPO_ROOT}" config --local --get "${key}" || true)"
  [[ "${actual}" == "${expected}" ]]
}

driver_command() {
  local mode="$1"
  local driver_script quoted_script

  driver_script="${REPO_ROOT}/_base/scripts/template-merge-driver.sh"
  printf -v quoted_script '%q' "${driver_script}"
  printf '%s %s %%O %%A %%B' "${quoted_script}" "${mode}"
}

check_attributes_block() {
  MANAGED_BLOCK="${MANAGED_BLOCK}" ATTRIBUTES_FILE="${ATTRIBUTES_FILE}" python3 - <<'PY'
import os
from pathlib import Path

path = Path(os.environ["ATTRIBUTES_FILE"])
expected = os.environ["MANAGED_BLOCK"].strip()

if not path.exists():
    raise SystemExit(1)

text = path.read_text().strip()
if expected not in text:
    raise SystemExit(1)
PY
}

write_attributes_block() {
  MANAGED_BLOCK="${MANAGED_BLOCK}" ATTRIBUTES_FILE="${ATTRIBUTES_FILE}" python3 - <<'PY'
import os
from pathlib import Path

path = Path(os.environ["ATTRIBUTES_FILE"])
block = os.environ["MANAGED_BLOCK"].strip() + "\n"
begin = "# BEGIN agents-template merge rules"
end = "# END agents-template merge rules"

text = path.read_text() if path.exists() else ""

if begin in text and end in text:
    prefix, rest = text.split(begin, 1)
    _, suffix = rest.split(end, 1)
    new_text = prefix.rstrip() + ("\n\n" if prefix.strip() else "") + block
    suffix = suffix.lstrip("\n")
    if suffix:
        new_text += "\n" + suffix
elif text.strip():
    new_text = block + "\n" + text.lstrip("\n")
else:
    new_text = block

path.write_text(new_text)
PY
}

if [[ "${MODE}" == "check" ]]; then
  failures=0

  if ! check_driver "merge.template-keep-local.driver" "$(driver_command keep-local)"; then
    printf 'FAIL  missing local Git merge driver: template-keep-local\n' >&2
    failures=$((failures + 1))
  fi

  if ! check_driver "merge.template-keep-upstream.driver" "$(driver_command keep-upstream)"; then
    printf 'FAIL  missing local Git merge driver: template-keep-upstream\n' >&2
    failures=$((failures + 1))
  fi

  if ! check_attributes_block; then
    printf 'FAIL  root .gitattributes is missing the agents-template merge rules block\n' >&2
    failures=$((failures + 1))
  fi

  if [[ "${failures}" -gt 0 ]]; then
    printf '\nRun ./_base/scripts/setup-template-merge-rules.sh, then commit .gitattributes if it changed.\n' >&2
    exit 1
  fi

  printf 'OK  template merge rules are installed\n'
  exit 0
fi

git -C "${REPO_ROOT}" rev-parse --git-dir >/dev/null

git -C "${REPO_ROOT}" config --local merge.template-keep-local.name \
  "Keep downstream-owned files when merging template updates"
git -C "${REPO_ROOT}" config --local merge.template-keep-local.driver "$(driver_command keep-local)"

git -C "${REPO_ROOT}" config --local merge.template-keep-upstream.name \
  "Accept template remote files for upstream-owned template content"
git -C "${REPO_ROOT}" config --local merge.template-keep-upstream.driver "$(driver_command keep-upstream)"

write_attributes_block

cat <<'EOF'
Template merge rules installed.

Local Git config now knows:
  template-keep-local
  template-keep-upstream

The root .gitattributes file contains the managed agents-template block. Commit
.gitattributes in downstream repos so future template pulls use these rules.
EOF
