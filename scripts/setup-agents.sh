#!/usr/bin/env bash
#
# One-command agent refresh for this template.
#
# Use after pulling template updates, or when setting up a repo seeded from this
# template. This intentionally calls the lower-level scripts rather than
# duplicating their logic.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Source project.env if it exists so users can override CLI names or setup modes
# in the same place they override install paths for the lower-level scripts.
if [[ -f "${REPO_ROOT}/project.env" ]]; then
  # shellcheck source=/dev/null
  source "${REPO_ROOT}/project.env"
fi

CODEX_CLI="${CODEX_CLI:-codex}"
CLAUDE_CLI="${CLAUDE_CLI:-claude}"
TARGET_CODEX=1
TARGET_CLAUDE=1
FORCE_SETUP=0

usage() {
  cat <<'EOF'
Usage: scripts/setup-agents.sh [OPTION]

Validate and refresh agent integrations after pulling template updates.

Default:
  Set up both Codex and Claude Code.

Options:
  --all          Set up both Codex and Claude Code. This is the default.
  --codex-only   Set up only Codex skills/plugins.
  --claude-only  Set up only Claude Code skills/plugins.
  --force        Run selected setup even if the matching CLI is not on PATH.
  --help         Show this help.

CLI guards:
  By default, the script requires selected CLIs to be installed:
  - Codex:  command named by CODEX_CLI, default "codex"
  - Claude: command named by CLAUDE_CLI, default "claude"

  Use --force to preinstall links/settings on a machine before the CLI exists.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --all)
      TARGET_CODEX=1
      TARGET_CLAUDE=1
      ;;
    --codex-only)
      TARGET_CODEX=1
      TARGET_CLAUDE=0
      ;;
    --claude-only)
      TARGET_CODEX=0
      TARGET_CLAUDE=1
      ;;
    --force)
      FORCE_SETUP=1
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

run_step() {
  local label="$1"
  shift

  printf '\n==> %s\n' "${label}"
  "$@"
}

cli_path() {
  command -v "$1" 2>/dev/null || true
}

require_cli() {
  local name="$1" cli="$2"

  if [[ -n "$(cli_path "${cli}")" ]]; then
    return 0
  fi
  if [[ "${FORCE_SETUP}" -eq 1 ]]; then
    printf 'Warning: %s CLI not found on PATH as %q; continuing because --force was set.\n' \
      "${name}" "${cli}" >&2
    return 0
  fi

  printf 'error: %s CLI not found on PATH as %q.\n' "${name}" "${cli}" >&2
  printf '       Install it, choose a narrower target, or rerun with --force.\n' >&2
  return 1
}

run_step "Validate skill catalog" \
  "${REPO_ROOT}/_base/scripts/check-skills-sync.sh"

codex_path="$(cli_path "${CODEX_CLI}")"
claude_path="$(cli_path "${CLAUDE_CLI}")"

printf '\nDetected runtimes:\n'
printf '  Codex CLI:      %s\n' "${codex_path:-not found (${CODEX_CLI})}"
printf '  Claude Code CLI: %s\n' "${claude_path:-not found (${CLAUDE_CLI})}"

if [[ "${TARGET_CODEX}" -eq 1 ]]; then
  require_cli "Codex" "${CODEX_CLI}"
fi
if [[ "${TARGET_CLAUDE}" -eq 1 ]]; then
  require_cli "Claude Code" "${CLAUDE_CLI}"
fi

if [[ "${TARGET_CODEX}" -eq 1 ]]; then
  run_step "Install or refresh Codex skills" \
    "${REPO_ROOT}/skills/install-codex-skills.sh"

  run_step "Install or refresh Codex plugins" \
    "${REPO_ROOT}/plugins/install-codex-plugins.sh"
fi

if [[ "${TARGET_CLAUDE}" -eq 1 ]]; then
  run_step "Link Claude Code skills globally" \
    "${REPO_ROOT}/scripts/link-skills.sh"

  run_step "Install or refresh Claude Code plugins" \
    "${REPO_ROOT}/plugins/install-claude-plugins.sh"
fi

cat <<'EOF'

Agent setup complete.

This command is idempotent; run it again after each template update to refresh links and plugin entries.
Restart any agent CLI whose setup ran so it reloads skills and plugins.

Codex note: installed skills are model-visible skills, not TUI slash commands.
Invoke them by describing the task ("tidy this repo") or by naming the skill ("$tidy-repo").
EOF
