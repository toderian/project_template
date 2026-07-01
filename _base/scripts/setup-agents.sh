#!/usr/bin/env bash
#
# One-command agent refresh for this template.
#
# Use after pulling template updates, or when setting up a repo seeded from this
# template. This intentionally calls the lower-level scripts rather than
# duplicating their logic.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Source project.env if it exists so users can override CLI names or setup modes
# in the same place they override install paths for the lower-level scripts.
if [[ -f "${REPO_ROOT}/project.env" ]]; then
  # shellcheck source=/dev/null
  source "${REPO_ROOT}/project.env"
fi

CODEX_CLI="${CODEX_CLI:-codex}"
CLAUDE_CLI="${CLAUDE_CLI:-claude}"
ANTIGRAVITY_CLI="${ANTIGRAVITY_CLI:-agy}"
TARGET_CODEX=1
TARGET_CLAUDE=1
TARGET_ANTIGRAVITY=0
FORCE_SETUP=0
SKILL_PROMPT=1
SKILL_PROFILE=""
SKILL_PACKS=""
SKILL_EXTRA=""
LIST_SKILLS=0

usage() {
  cat <<'EOF'
Usage: _base/scripts/setup-agents.sh [OPTION]

Validate and refresh agent integrations after pulling template updates.

Default:
  Set up both Codex and Claude Code. Antigravity is experimental and opt-in.

Options:
  --all                Set up both Codex and Claude Code. This is the default.
  --codex-only         Set up only Codex skills/plugins.
  --claude-only        Set up only Claude Code skills/plugins.
  --antigravity-only   Generate only experimental Antigravity skill wrappers.
  --skills-profile P   Activate a named skill profile before setup
                       (minimal, recommended, full).
  --skills PACKS       Activate a comma-separated custom pack list before setup.
  --extra-skills LIST  Add comma-separated individual skills to --skills.
  --all-skills         Activate the full skill-library profile.
  --list-skills        List available skill profiles and packs, then exit.
  --no-skill-prompt    Do not prompt for optional skill packs; keep current selection.
  --force              Run selected setup even if the matching CLI is not on PATH.
  --help               Show this help.

CLI guards:
  By default, the script requires selected CLIs to be installed:
  - Codex:       command named by CODEX_CLI, default "codex"
  - Claude:      command named by CLAUDE_CLI, default "claude"
  - Antigravity: command named by ANTIGRAVITY_CLI, default "agy"

  Use --force to preinstall links/settings on a machine before the CLI exists.

Skill selection:
  Interactive setup asks which optional skill profile or packs to activate.
  Non-interactive runs keep the current .agents/skills.enabled.json selection.
  Use --skills-profile, --skills, or --all-skills for scripted re-selection.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --all)
      TARGET_CODEX=1
      TARGET_CLAUDE=1
      TARGET_ANTIGRAVITY=0
      ;;
    --codex-only)
      TARGET_CODEX=1
      TARGET_CLAUDE=0
      TARGET_ANTIGRAVITY=0
      ;;
    --claude-only)
      TARGET_CODEX=0
      TARGET_CLAUDE=1
      TARGET_ANTIGRAVITY=0
      ;;
    --antigravity-only)
      TARGET_CODEX=0
      TARGET_CLAUDE=0
      TARGET_ANTIGRAVITY=1
      ;;
    --skills-profile)
      if [[ $# -lt 2 || "$2" == --* ]]; then
        printf '%s requires an argument\n\n' "$1" >&2
        usage >&2
        exit 2
      fi
      SKILL_PROFILE="$2"
      SKILL_PROMPT=0
      shift
      ;;
    --skills)
      if [[ $# -lt 2 || "$2" == --* ]]; then
        printf '%s requires an argument\n\n' "$1" >&2
        usage >&2
        exit 2
      fi
      SKILL_PACKS="$2"
      SKILL_PROMPT=0
      shift
      ;;
    --extra-skills)
      if [[ $# -lt 2 || "$2" == --* ]]; then
        printf '%s requires an argument\n\n' "$1" >&2
        usage >&2
        exit 2
      fi
      SKILL_EXTRA="$2"
      SKILL_PROMPT=0
      shift
      ;;
    --all-skills)
      SKILL_PROFILE="full"
      SKILL_PROMPT=0
      ;;
    --list-skills)
      LIST_SKILLS=1
      ;;
    --no-skill-prompt)
      SKILL_PROMPT=0
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

sync_skill_selection() {
  local script="${REPO_ROOT}/_base/scripts/sync-skill-selection.py"

  if [[ "${LIST_SKILLS}" -eq 1 ]]; then
    "${script}" --list
    exit 0
  fi

  if [[ -n "${SKILL_PROFILE}" ]]; then
    "${script}" --profile "${SKILL_PROFILE}"
    return
  fi

  if [[ -n "${SKILL_PACKS}" || -n "${SKILL_EXTRA}" ]]; then
    local args=(--packs "${SKILL_PACKS}")
    if [[ -n "${SKILL_EXTRA}" ]]; then
      args+=(--skills "${SKILL_EXTRA}")
    fi
    "${script}" "${args[@]}"
    return
  fi

  if [[ "${SKILL_PROMPT}" -eq 1 && -t 0 && -t 1 ]]; then
    "${script}" --interactive
    return
  fi

  "${script}" --sync
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

run_step "Sync active skill selection" \
  sync_skill_selection

run_step "Validate skill catalog" \
  "${REPO_ROOT}/_base/scripts/check-skills-sync.sh"

codex_path="$(cli_path "${CODEX_CLI}")"
claude_path="$(cli_path "${CLAUDE_CLI}")"
antigravity_path="$(cli_path "${ANTIGRAVITY_CLI}")"

printf '\nDetected runtimes:\n'
printf '  Codex CLI:        %s\n' "${codex_path:-not found (${CODEX_CLI})}"
printf '  Claude Code CLI:  %s\n' "${claude_path:-not found (${CLAUDE_CLI})}"
printf '  Antigravity CLI:  %s\n' "${antigravity_path:-not found (${ANTIGRAVITY_CLI})}"

if [[ "${TARGET_CODEX}" -eq 1 ]]; then
  require_cli "Codex" "${CODEX_CLI}"
fi
if [[ "${TARGET_CLAUDE}" -eq 1 ]]; then
  require_cli "Claude Code" "${CLAUDE_CLI}"
fi
if [[ "${TARGET_ANTIGRAVITY}" -eq 1 ]]; then
  require_cli "Antigravity" "${ANTIGRAVITY_CLI}"
fi

if [[ "${TARGET_CODEX}" -eq 1 ]]; then
  run_step "Install or refresh Codex skills" \
    "${REPO_ROOT}/skills/install-codex-skills.sh"

  run_step "Install or refresh Codex plugins" \
    "${REPO_ROOT}/_base/plugins/install-codex-plugins.sh"
fi

if [[ "${TARGET_CLAUDE}" -eq 1 ]]; then
  run_step "Link Claude Code skills globally" \
    "${REPO_ROOT}/_base/scripts/link-skills.sh"

  run_step "Install or refresh Claude Code plugins" \
    "${REPO_ROOT}/_base/plugins/install-claude-plugins.sh"
fi

if [[ "${TARGET_ANTIGRAVITY}" -eq 1 ]]; then
  run_step "Generate experimental Antigravity skill wrappers" \
    "${REPO_ROOT}/_base/scripts/gen-antigravity-skills.sh"

  run_step "Validate experimental Antigravity skill wrappers" \
    "${REPO_ROOT}/_base/scripts/check-antigravity-skills.sh"
fi

cat <<'EOF'

Agent setup complete for selected runtimes.

This command is idempotent; run it again after each template update to refresh links and plugin entries.
Restart any agent CLI whose setup ran so it reloads skills and plugins.

Codex note: installed skills are model-visible skills, not TUI slash commands.
Invoke them by describing the task ("tidy this repo") or by naming the skill ("$tidy-repo").

Antigravity note: `agy` support is experimental. It only generates repo-local wrappers under
`.agents/skills/`; there is no Antigravity plugin bundle in this template.
EOF
