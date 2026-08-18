#!/usr/bin/env bash
#
# Install this repo's pre-commit gate: .git/hooks/pre-commit runs the whole test
# suite (scripts/tests/run-all.sh) before every commit.
#
#   scripts/install-pre-commit.sh [--force]
#
# Idempotent: re-running it on an already-installed hook changes nothing. It
# refuses to replace a hook it did not write unless you pass --force (the old
# file is kept as .git/hooks/pre-commit.bak).

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

FORCE=0
for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    -h|--help) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "install-pre-commit: unknown option: $arg" >&2; exit 2 ;;
  esac
done

HOOK_DIR="$(git rev-parse --git-path hooks)"
HOOK="$HOOK_DIR/pre-commit"
WANT='#!/bin/sh
# Installed by scripts/install-pre-commit.sh (agents-template).
exec "$(git rev-parse --show-toplevel)/scripts/tests/run-all.sh"'

if [[ -e "$HOOK" ]]; then
  if [[ "$(cat "$HOOK")" == "$WANT" ]]; then
    echo "pre-commit hook already installed: $HOOK"
    exit 0
  fi
  if ! grep -q "scripts/tests/run-all.sh" "$HOOK" && [[ "$FORCE" == 0 ]]; then
    echo "install-pre-commit: $HOOK exists and is not ours; re-run with --force to replace it" >&2
    exit 1
  fi
  cp "$HOOK" "$HOOK.bak"
  echo "kept the previous hook as $HOOK.bak"
fi

mkdir -p "$HOOK_DIR"
printf '%s\n' "$WANT" > "$HOOK"
chmod +x "$HOOK"
echo "installed $HOOK (runs scripts/tests/run-all.sh)"
