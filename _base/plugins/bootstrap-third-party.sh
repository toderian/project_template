#!/usr/bin/env bash
#
# Bootstrap third-party plugins/skills that ship their own multi-platform
# installers. Each section is independent and idempotent — re-running this
# script is safe.
#
# What this installs (and where it lives upstream):
#   - get-shit-done-cc  — https://github.com/gsd-build/get-shit-done
#   - context-mode      — https://github.com/mksglu/context-mode
#   - claude-mem        — https://github.com/thedotmack/claude-mem
#
# Each ships first-class support for both Claude Code and Codex; we delegate
# to their own installers rather than vendoring under playbooks/.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [[ -f "${REPO_ROOT}/project.env" ]]; then
  # shellcheck source=/dev/null
  source "${REPO_ROOT}/project.env"
fi

INSTALL_GSD="${INSTALL_GSD:-1}"
INSTALL_CONTEXT_MODE="${INSTALL_CONTEXT_MODE:-1}"
INSTALL_CLAUDE_MEM="${INSTALL_CLAUDE_MEM:-1}"

log() { printf '\n=== %s ===\n' "$*"; }
warn() { printf 'WARN: %s\n' "$*" >&2; }

require() {
  command -v "$1" >/dev/null 2>&1 || {
    warn "missing dependency: $1 — skipping section"
    return 1
  }
}

# --- get-shit-done-cc ------------------------------------------------------
# Spec-driven dev workflow with native installers for Claude and Codex.
if [[ "${INSTALL_GSD}" == "1" ]]; then
  log "get-shit-done-cc"
  if require npx; then
    npx -y get-shit-done-cc@latest --claude --global || warn "claude install failed"
    npx -y get-shit-done-cc@latest --codex --global || warn "codex install failed"
  fi
fi

# --- context-mode ----------------------------------------------------------
# MCP server + hooks that sandbox tool output. Install via Claude marketplace
# and via the upstream Codex instructions. The Claude install path is gated
# behind the `claude` CLI and the user's chosen plugin manager.
if [[ "${INSTALL_CONTEXT_MODE}" == "1" ]]; then
  log "context-mode"
  cat <<'NOTE'
context-mode is an MCP server + hook bundle. It is not a markdown skill,
so it cannot be vendored under playbooks/. Install it from inside each
runtime instead:

  Claude Code:
    /plugin marketplace add mksglu/context-mode
    /plugin install context-mode@context-mode

  Codex CLI:
    See https://github.com/mksglu/context-mode for the Codex MCP wiring.
    Codex hook coverage is partial (no PreCompact/SessionStart), so
    enforcement is reduced compared to Claude Code.
NOTE
fi

# --- claude-mem ------------------------------------------------------------
# Cross-session memory with auto-compression. Ships .claude-plugin/ AND
# .codex-plugin/ side by side. Heavy runtime deps (Bun + uv + Node + Chroma).
if [[ "${INSTALL_CLAUDE_MEM}" == "1" ]]; then
  log "claude-mem"
  cat <<'NOTE'
claude-mem is a marketplace plugin with an MCP server. Install from inside
each runtime:

  Claude Code:
    /plugin marketplace add thedotmack/claude-mem
    /plugin install claude-mem

  Codex CLI:
    The same repo ships a .codex-plugin/ manifest. See
    https://github.com/thedotmack/claude-mem for Codex install steps.

Runtime requirements: Bun, uv (Python), Node 18+, Chroma.
NOTE
fi

log "Done. Restart Claude Code and Codex to pick up new skills/plugins."
