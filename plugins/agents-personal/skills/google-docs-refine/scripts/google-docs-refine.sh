#!/usr/bin/env bash
set -euo pipefail

CACHE_ROOT="${GOOGLE_DOCS_REFINE_CACHE:-$HOME/.cache/google-docs-refine-suite}"
NPM_PREFIX="$CACHE_ROOT/npm"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLAYWRIGHT_VERSION="${PLAYWRIGHT_VERSION:-1.60.0}"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  node "$SCRIPT_DIR/google-docs-refine.mjs" --help
  exit 0
fi

if [[ ! -d "$NPM_PREFIX/node_modules/playwright" ]]; then
  mkdir -p "$NPM_PREFIX"
  npm install --silent --prefix "$NPM_PREFIX" "playwright@$PLAYWRIGHT_VERSION" >/dev/null
fi

export NODE_PATH="$NPM_PREFIX/node_modules${NODE_PATH:+:$NODE_PATH}"
node "$SCRIPT_DIR/google-docs-refine.mjs" "$@"
