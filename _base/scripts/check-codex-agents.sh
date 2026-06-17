#!/usr/bin/env bash
#
# Validate committed project-scoped Codex agent mirrors.

set -euo pipefail

readonly VERSION="0.1.0"

usage() {
  cat <<'EOF'
Usage: check-codex-agents.sh [OPTION]

Validate that only intended .codex/agents/*.toml mirrors are tracked and local
Codex config/state remains ignored.

Options:
  --version    Print version and exit.
  --help       Show this message and exit.
EOF
}

case "${1:-}" in
  --version) printf 'check-codex-agents.sh %s\n' "$VERSION"; exit 0 ;;
  --help|-h) usage; exit 0 ;;
  "")        ;;
  *)         printf 'unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
esac

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

python3 - "${REPO_ROOT}" <<'PY'
from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(sys.argv[1])
EXPECTED = {
    ".codex/agents/implementer.toml",
    ".codex/agents/plan-critic.toml",
    ".codex/agents/researcher.toml",
    ".codex/agents/reviewer.toml",
    ".codex/agents/security-auditor.toml",
    ".codex/agents/spec-validator.toml",
}
ALLOWED_RE = re.compile(r"^\.codex/agents/[A-Za-z0-9_.-]+\.toml$")
REQUIRED_FIELDS = ("name", "description", "developer_instructions")

findings: list[tuple[str, str, str, str]] = []


def emit(severity: str, check_id: str, path: str, details: str) -> None:
    findings.append((severity, check_id, path, details))


def git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


tracked_result = git(["ls-files", ".codex"])
if tracked_result.returncode != 0:
    print(tracked_result.stderr, file=sys.stderr)
    raise SystemExit(tracked_result.returncode)

tracked = set(filter(None, tracked_result.stdout.splitlines()))

for path in sorted(tracked):
    if not ALLOWED_RE.fullmatch(path):
        emit("BLOCKER", "tracked-codex-local-state", path, "only .codex/agents/*.toml may be tracked")

for path in sorted(EXPECTED - tracked):
    emit("BLOCKER", "missing-codex-agent", path, "expected project-scoped Codex agent mirror")

for path in sorted(tracked & EXPECTED):
    full_path = ROOT / path
    text = full_path.read_text(encoding="utf-8")
    for field in REQUIRED_FIELDS:
        if not re.search(rf"(?m)^{field}\s*=", text):
            emit("BLOCKER", "missing-codex-agent-field", path, f"missing required field: {field}")
    if "playbooks/" not in text:
        emit("DRIFT", "codex-agent-not-thin", path, "mirror should point at shared playbooks/personality rules")

config_ignored = git(["check-ignore", "--no-index", "--quiet", ".codex/config.toml"])
if config_ignored.returncode != 0:
    emit("BLOCKER", "codex-config-not-ignored", ".codex/config.toml", "local Codex config must remain ignored")

reviewer_ignored = git(["check-ignore", "--no-index", "--quiet", ".codex/agents/reviewer.toml"])
if reviewer_ignored.returncode == 0:
    emit("BLOCKER", "codex-agent-ignored", ".codex/agents/reviewer.toml", "agent mirrors must be trackable")

for severity, check_id, path, details in sorted(findings):
    print(f"{severity}\t{check_id}\t{path}\t{details}")

blockers = sum(1 for severity, *_ in findings if severity == "BLOCKER")
drift = sum(1 for severity, *_ in findings if severity == "DRIFT")

if blockers or drift:
    print(f"{len(findings)} findings  ({blockers} BLOCKER, {drift} DRIFT)")
    raise SystemExit(1)

print("OK  Codex agent mirrors valid")
PY
