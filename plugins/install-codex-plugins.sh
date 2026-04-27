#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Source project.env if it exists.
if [[ -f "${REPO_ROOT}/project.env" ]]; then
  # shellcheck source=/dev/null
  source "${REPO_ROOT}/project.env"
fi

SOURCE_PLUGINS_DIR="${SCRIPT_DIR}"
AGENTS_HOME="${AGENTS_HOME:-${HOME}/.agents}"
TARGET_PLUGINS_DIR="${CODEX_PLUGINS_DIR:-${HOME}/plugins}"
MARKETPLACE_PATH="${CODEX_MARKETPLACE_PATH:-${AGENTS_HOME}/plugins/marketplace.json}"
MARKETPLACE_NAME="${CODEX_MARKETPLACE_NAME:-local-project-template}"
MARKETPLACE_DISPLAY_NAME="${CODEX_MARKETPLACE_DISPLAY_NAME:-Local Project Template}"

if [[ ! -d "${SOURCE_PLUGINS_DIR}" ]]; then
  echo "No repo plugins directory found at ${SOURCE_PLUGINS_DIR}" >&2
  exit 1
fi

plugin_dirs=()

for plugin_dir in "${SOURCE_PLUGINS_DIR}"/*; do
  [[ -d "${plugin_dir}" ]] || continue

  plugin_name="$(basename "${plugin_dir}")"
  manifest_path="${plugin_dir}/.codex-plugin/plugin.json"

  if [[ ! -f "${manifest_path}" ]]; then
    echo "Skipping ${plugin_name}: missing .codex-plugin/plugin.json"
    continue
  fi

  plugin_dirs+=("${plugin_dir}")
done

if [[ ${#plugin_dirs[@]} -eq 0 ]]; then
  echo "No installable plugins found in ${SOURCE_PLUGINS_DIR}."
  exit 0
fi

mkdir -p "${TARGET_PLUGINS_DIR}"
mkdir -p "$(dirname "${MARKETPLACE_PATH}")"

for plugin_dir in "${plugin_dirs[@]}"; do
  plugin_name="$(basename "${plugin_dir}")"
  target_path="${TARGET_PLUGINS_DIR}/${plugin_name}"

  if [[ -e "${target_path}" || -L "${target_path}" ]]; then
    echo "Skipping link for ${plugin_name}: ${target_path} already exists"
    continue
  fi

  ln -s "${plugin_dir}" "${target_path}"
  echo "Installed ${plugin_name} -> ${target_path}"
done

python3 - "${MARKETPLACE_PATH}" "${MARKETPLACE_NAME}" "${MARKETPLACE_DISPLAY_NAME}" "${plugin_dirs[@]}" <<'PY'
import json
import sys
from pathlib import Path

marketplace_path = Path(sys.argv[1])
marketplace_name = sys.argv[2]
marketplace_display_name = sys.argv[3]
plugin_dirs = [Path(path) for path in sys.argv[4:]]

if marketplace_path.exists():
    data = json.loads(marketplace_path.read_text())
else:
    data = {
        "name": marketplace_name,
        "interface": {"displayName": marketplace_display_name},
        "plugins": [],
    }

data.setdefault("name", marketplace_name)
interface = data.setdefault("interface", {})
interface.setdefault("displayName", marketplace_display_name)
plugins = data.setdefault("plugins", [])
existing_by_name = {
    entry.get("name"): entry
    for entry in plugins
    if isinstance(entry, dict) and entry.get("name")
}

for plugin_dir in plugin_dirs:
    plugin_name = plugin_dir.name
    manifest_path = plugin_dir / ".codex-plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text())
    manifest_name = manifest.get("name")

    if manifest_name and manifest_name != plugin_name:
        print(
            f"Warning: {plugin_name} manifest name is {manifest_name!r}; "
            "marketplace entry uses the folder name."
        )

    category = manifest.get("interface", {}).get("category") or "Productivity"
    entry = {
        "name": plugin_name,
        "source": {
            "source": "local",
            "path": f"./plugins/{plugin_name}",
        },
        "policy": {
            "installation": "AVAILABLE",
            "authentication": "ON_INSTALL",
        },
        "category": category,
    }

    if plugin_name in existing_by_name:
        print(f"Marketplace already has {plugin_name}; leaving existing entry unchanged")
    else:
        plugins.append(entry)
        print(f"Added marketplace entry for {plugin_name}")

marketplace_path.write_text(json.dumps(data, indent=2) + "\n")
print(f"Marketplace: {marketplace_path}")
PY

echo "Restart Codex to pick up newly installed plugins."
