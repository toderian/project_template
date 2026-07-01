#!/usr/bin/env bash
#
# Read-only validation for the experimental Antigravity skill wrappers.

set -euo pipefail

readonly VERSION="0.1.0"

usage() {
  cat <<'EOF'
Usage: check-antigravity-skills.sh [OPTION]

Validate that generated .agents/skills/ wrappers match the active skill selection.

Options:
  --version    Print version and exit.
  --help       Show this message and exit.
EOF
}

case "${1:-}" in
  --version) printf 'check-antigravity-skills.sh %s\n' "$VERSION"; exit 0 ;;
  --help|-h) usage; exit 0 ;;
  "")        ;;
  *)         printf 'unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"${SCRIPT_DIR}/gen-antigravity-skills.sh" --check
