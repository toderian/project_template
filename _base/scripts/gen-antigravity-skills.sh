#!/usr/bin/env bash
#
# Generate experimental Antigravity skill wrappers from the shared skill
# manifest. Antigravity support is intentionally thin and removable: the only
# repo-local runtime surface this script writes is .agents/skills/.

set -euo pipefail

readonly VERSION="0.1.0"

usage() {
  cat <<'EOF'
Usage: gen-antigravity-skills.sh [OPTION]

Generate .agents/skills/ wrappers from .claude-plugin/plugin.json.

With no option, regenerate wrappers in place. The generated wrappers point to
the existing shared playbooks and do not change the manifest schema.

Options:
  --check      Validate that .agents/skills/ is current without writing files.
  --version    Print version and exit.
  --help       Show this message and exit.
EOF
}

CHECK_MODE=0
case "${1:-}" in
  --version) printf 'gen-antigravity-skills.sh %s\n' "$VERSION"; exit 0 ;;
  --help)    usage; exit 0 ;;
  --check)   CHECK_MODE=1 ;;
  "")        ;;
  *)         printf 'unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
esac

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

python3 - "$REPO_ROOT" "$CHECK_MODE" <<'PY'
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

repo_root = Path(sys.argv[1])
check_mode = sys.argv[2] == "1"

manifest_path = repo_root / ".claude-plugin" / "plugin.json"
claude_skills_dir = repo_root / ".claude" / "skills"
playbooks_dir = repo_root / "playbooks" / "skills"
target_dir = repo_root / ".agents" / "skills"

agent_only_refs = {
    "implementer": [
        "playbooks/skills/productivity/subagent-protocol.md",
        "playbooks/personalities/builder.md",
    ],
    "reviewer": [
        "playbooks/skills/productivity/subagent-protocol.md",
        "playbooks/personalities/reviewer.md",
        "playbooks/personalities/critic.md",
    ],
}


def frontmatter_field(path: Path, field: str) -> str:
    if not path.exists():
        raise SystemExit(f"missing source wrapper: {path.relative_to(repo_root)}")

    in_frontmatter = False
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if line == "---":
            if in_frontmatter:
                break
            in_frontmatter = True
            continue
        if not in_frontmatter:
            continue
        prefix = f"{field}:"
        if line.startswith(prefix):
            value = line[len(prefix):].strip()
            if len(value) >= 2 and value[0] == value[-1] == '"':
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    value = value[1:-1]
            elif len(value) >= 2 and value[0] == value[-1] == "'":
                value = value[1:-1].replace("''", "'")
            return value
    raise SystemExit(f"missing frontmatter field {field!r}: {path.relative_to(repo_root)}")


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def skill_tuples() -> list[tuple[str, str]]:
    if not manifest_path.exists():
        raise SystemExit(f"missing manifest: {manifest_path.relative_to(repo_root)}")

    data = json.loads(manifest_path.read_text())
    tuples: list[tuple[str, str]] = []
    for entry in data.get("skills", []):
        parts = entry.strip("./").split("/")
        if len(parts) != 3 or parts[0] != "skills":
            raise SystemExit(f"manifest entry malformed: {entry}")
        bucket, name = parts[1], parts[2]
        tuples.append((bucket, name))
    return sorted(tuples)


def references_for(bucket: str, name: str) -> list[str]:
    if name in agent_only_refs:
        return agent_only_refs[name]

    playbook = playbooks_dir / bucket / f"{name}.md"
    playbook_dir = playbooks_dir / bucket / name
    if playbook.exists():
        return [f"playbooks/skills/{bucket}/{name}.md"]
    if playbook_dir.is_dir():
        return [f"playbooks/skills/{bucket}/{name}/"]
    raise SystemExit(f"missing playbook for {bucket}/{name}")


def wrapper_content(bucket: str, name: str) -> str:
    source_wrapper = claude_skills_dir / bucket / name / "SKILL.md"
    description = frontmatter_field(source_wrapper, "description")
    refs = references_for(bucket, name)
    ref_lines = "\n".join(f"- `{ref}`" for ref in refs)
    return f"""---
name: {name}
description: {yaml_string(description)}
---

Read and follow:

{ref_lines}

This Antigravity wrapper is generated from `.claude-plugin/plugin.json`.
Keep Antigravity support experimental and isolated; update the shared playbook first.
"""


expected: dict[Path, str] = {}
for bucket, name in skill_tuples():
    rel = Path(bucket) / name / "SKILL.md"
    expected[rel] = wrapper_content(bucket, name)

findings: list[str] = []

for rel, content in expected.items():
    path = target_dir / rel
    if not path.exists():
        findings.append(f"missing .agents/skills/{rel}")
    elif path.read_text() != content:
        findings.append(f"drift .agents/skills/{rel}")

if target_dir.exists():
    for path in sorted(p for p in target_dir.rglob("*") if p.is_file()):
        rel = path.relative_to(target_dir)
        if rel not in expected:
            findings.append(f"unexpected .agents/skills/{rel}")

try:
    tracked = subprocess.check_output(
        ["git", "-C", str(repo_root), "ls-files", ".agents"],
        text=True,
    ).splitlines()
except subprocess.CalledProcessError as exc:
    raise SystemExit(exc.returncode) from exc

for tracked_path in tracked:
    if not tracked_path.startswith(".agents/skills/"):
        findings.append(f"tracked file outside .agents/skills: {tracked_path}")

if check_mode:
    if findings:
        print("Antigravity skill wrappers are out of sync:")
        for finding in findings:
            print(f"- {finding}")
        raise SystemExit(1)
    print(f"OK  Antigravity wrappers current ({len(expected)} skills)")
    raise SystemExit(0)

target_dir.mkdir(parents=True, exist_ok=True)
for rel, content in expected.items():
    path = target_dir / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text() != content:
        path.write_text(content)

if target_dir.exists():
    for path in sorted(p for p in target_dir.rglob("*") if p.is_file()):
        rel = path.relative_to(target_dir)
        if rel not in expected:
            path.unlink()
    for path in sorted((p for p in target_dir.rglob("*") if p.is_dir()), reverse=True):
        try:
            path.rmdir()
        except OSError:
            pass

print(f"generated .agents/skills wrappers for {len(expected)} skills")
PY
