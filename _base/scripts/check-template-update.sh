#!/usr/bin/env bash
#
# One-command read-only verification after pulling or merging template updates.
#
# This intentionally checks downstream repo state without refreshing global agent
# installs or writing generated docs. Run setup-agents.sh separately when you
# want to update local agent integrations.

set -uo pipefail

REQUIRE_LOCAL=0

usage() {
  cat <<'EOF'
Usage: _base/scripts/check-template-update.sh [--local]

Run the standard read-only checks after pulling or merging template updates.

Checks:
  - reports BASE_VERSION from _base/CHANGELOG.md
  - validates template merge rules and local Git merge drivers
  - syntax-checks template shell scripts
  - validates skill/wrapper/table consistency
  - validates generated Antigravity skill wrappers
  - validates bundled Codex plugin manifests
  - validates committed Codex agent mirrors and local Codex ignore rules
  - validates optional .config/repos.project.md and task Repos / Autonomy metadata
  - validates .local/repos.map when present, or always with --local
  - validates task ledgers in --check mode
  - runs git diff --check

Options:
  --local   Require and validate .local/repos.map.
  --help    Show this message.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --local) REQUIRE_LOCAL=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

FAILURES=0

run_check() {
  local label="$1"
  shift

  printf '\n==> %s\n' "${label}"
  if "$@"; then
    printf 'OK  %s\n' "${label}"
  else
    printf 'FAIL  %s\n' "${label}" >&2
    FAILURES=$((FAILURES + 1))
  fi
}

print_base_version() {
  local changelog="${REPO_ROOT}/_base/CHANGELOG.md"

  printf '\n==> Base version\n'
  if [[ ! -f "${changelog}" ]]; then
    printf 'FAIL  missing _base/CHANGELOG.md\n' >&2
    FAILURES=$((FAILURES + 1))
    return
  fi

  local version
  version="$(grep -m1 '^BASE_VERSION:' "${changelog}" || true)"
  if [[ -z "${version}" ]]; then
    printf 'FAIL  BASE_VERSION missing from _base/CHANGELOG.md\n' >&2
    FAILURES=$((FAILURES + 1))
    return
  fi

  printf '%s\n' "${version}"
}

check_shell_syntax() {
  local failed=0
  local root file
  local roots=(
    "${REPO_ROOT}/_base/scripts"
    "${REPO_ROOT}/_base/plugins"
    "${REPO_ROOT}/skills"
  )

  for root in "${roots[@]}"; do
    [[ -d "${root}" ]] || continue
    while IFS= read -r -d '' file; do
      if ! bash -n "${file}"; then
        failed=1
      fi
    done < <(find "${root}" -type f -name '*.sh' -print0)
  done

  return "${failed}"
}

print_base_version

run_check "Template merge rules" \
  "${REPO_ROOT}/_base/scripts/setup-template-merge-rules.sh" --check

run_check "Template shell syntax" \
  check_shell_syntax

run_check "Skill catalog" \
  "${REPO_ROOT}/_base/scripts/check-skills-sync.sh"

run_check "Antigravity skill wrappers" \
  "${REPO_ROOT}/_base/scripts/check-antigravity-skills.sh"

run_check "Codex plugin manifests" \
  "${REPO_ROOT}/_base/scripts/check-codex-plugins.sh"

run_check "Codex agent mirrors" \
  "${REPO_ROOT}/_base/scripts/check-codex-agents.sh"

run_check "Repo registry and task Repos / Autonomy metadata" \
  "${REPO_ROOT}/_base/scripts/check-repos-config.sh"

if [[ "${REQUIRE_LOCAL}" -eq 1 || -f "${REPO_ROOT}/.local/repos.map" ]]; then
  run_check "Local repo checkout map" \
    "${REPO_ROOT}/_base/scripts/check-repos-config.sh" --local
else
  printf '\n==> Local repo checkout map\n'
  printf 'SKIP  .local/repos.map is absent; use --local to require it.\n'
fi

run_check "Task ledgers" \
  "${REPO_ROOT}/_base/scripts/sync-todo-ledgers.sh" --check

run_check "Git whitespace checks" \
  git -C "${REPO_ROOT}" diff --check

if [[ "${FAILURES}" -gt 0 ]]; then
  printf '\nTemplate update checks failed: %d\n' "${FAILURES}" >&2
  printf 'Ask an agent to fix the reported failures, then rerun this command until it passes.\n' >&2
  exit 1
fi

cat <<'EOF'

Template update checks passed.

This command is read-only. Run ./_base/scripts/setup-agents.sh separately when you want to refresh
local Codex/Claude skill and plugin installs after a template update.
EOF
