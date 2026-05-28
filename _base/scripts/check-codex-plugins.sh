#!/usr/bin/env bash
#
# Validate bundled Codex plugin manifests and referenced local assets.
#
# Output format:
#   SEVERITY<TAB>CHECK_ID<TAB>PATH<TAB>[details]
#
# Exits 0 when all bundled plugin manifests are valid.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PLUGINS_DIR="${REPO_ROOT}/_base/plugins"

python3 - "${PLUGINS_DIR}" "${REPO_ROOT}" <<'PY'
import json
import sys
from pathlib import Path

plugins_dir = Path(sys.argv[1])
repo_root = Path(sys.argv[2])
findings = []

def rel(path: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)

def emit(severity: str, check_id: str, path: Path, details: str) -> None:
    findings.append((severity, check_id, rel(path), details))

if not plugins_dir.is_dir():
    emit("BLOCKER", "missing-plugins-dir", plugins_dir, "_base/plugins directory is missing")
else:
    for plugin_dir in sorted(p for p in plugins_dir.iterdir() if p.is_dir()):
        manifest_path = plugin_dir / ".codex-plugin" / "plugin.json"
        if not manifest_path.exists():
            continue

        try:
            manifest = json.loads(manifest_path.read_text())
        except json.JSONDecodeError as exc:
            emit("BLOCKER", "invalid-plugin-json", manifest_path, str(exc))
            continue

        name = manifest.get("name")
        if not isinstance(name, str) or not name:
            emit("BLOCKER", "missing-plugin-name", manifest_path, "manifest has no string name")
        elif name != plugin_dir.name:
            emit("DRIFT", "plugin-name-mismatch", manifest_path, f"folder={plugin_dir.name} manifest={name}")

        for key in ("version", "description"):
            if not isinstance(manifest.get(key), str) or not manifest.get(key):
                emit("DRIFT", f"missing-plugin-{key}", manifest_path, f"manifest has no string {key}")

        for key, kind in (("skills", "dir"), ("apps", "file"), ("mcp", "file")):
            value = manifest.get(key)
            if value is None:
                continue
            if not isinstance(value, str):
                emit("BLOCKER", f"bad-plugin-{key}", manifest_path, f"{key} must be a string path")
                continue
            target = (plugin_dir / value).resolve(strict=False)
            if kind == "dir" and not target.is_dir():
                emit("BLOCKER", f"missing-plugin-{key}", manifest_path, f"{key} path does not exist: {value}")
            if kind == "file" and not target.is_file():
                emit("BLOCKER", f"missing-plugin-{key}", manifest_path, f"{key} path does not exist: {value}")

        skills_value = manifest.get("skills")
        if isinstance(skills_value, str):
            skills_dir = plugin_dir / skills_value
            if skills_dir.is_dir():
                for skill_dir in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
                    skill_file = skill_dir / "SKILL.md"
                    if not skill_file.is_file():
                        emit("BLOCKER", "missing-plugin-skill-md", skill_file, "plugin skill directory has no SKILL.md")

        apps_value = manifest.get("apps")
        if isinstance(apps_value, str):
            app_path = plugin_dir / apps_value
            if app_path.is_file():
                try:
                    json.loads(app_path.read_text())
                except json.JSONDecodeError as exc:
                    emit("BLOCKER", "invalid-plugin-app-json", app_path, str(exc))

        for optional_json in (".mcp.json",):
            path = plugin_dir / optional_json
            if path.exists():
                try:
                    json.loads(path.read_text())
                except json.JSONDecodeError as exc:
                    emit("BLOCKER", "invalid-plugin-json", path, str(exc))

        interface = manifest.get("interface") or {}
        if not isinstance(interface, dict):
            emit("BLOCKER", "bad-plugin-interface", manifest_path, "interface must be an object when present")
            continue

        for key in ("composerIcon", "logo"):
            value = interface.get(key)
            if isinstance(value, str) and value.startswith("./"):
                asset = plugin_dir / value
                if not asset.is_file():
                    emit("BLOCKER", "missing-plugin-asset", manifest_path, f"{key} does not exist: {value}")

for severity, check_id, path, details in sorted(findings):
    print(f"{severity}\t{check_id}\t{path}\t{details}")

blockers = sum(1 for severity, *_ in findings if severity == "BLOCKER")
drift = sum(1 for severity, *_ in findings if severity == "DRIFT")

if blockers or drift:
    print(f"{len(findings)} findings  ({blockers} BLOCKER, {drift} DRIFT)")
    sys.exit(1)

print("OK  Codex plugin manifests valid")
PY
