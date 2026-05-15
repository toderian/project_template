#!/usr/bin/env bash
#
# Symlink every active skill (per .claude-plugin/plugin.json) into Codex's
# global skills directory. The destination tree is intentionally flat —
# Codex doesn't read our bucket layout, so we collapse `skills/<bucket>/<name>`
# down to `~/.codex/skills/<name>`.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Source project.env if it exists
if [[ -f "${REPO_ROOT}/project.env" ]]; then
  # shellcheck source=/dev/null
  source "${REPO_ROOT}/project.env"
fi

SOURCE_SKILLS_DIR="${SCRIPT_DIR}"
CODEX_HOME="${CODEX_HOME:-${HOME}/.codex}"
TARGET_SKILLS_DIR="${CODEX_HOME}/skills"
MANIFEST="${REPO_ROOT}/.claude-plugin/plugin.json"

if [[ ! -d "${SOURCE_SKILLS_DIR}" ]]; then
  echo "No repo skills directory found at ${SOURCE_SKILLS_DIR}" >&2
  exit 1
fi

if [[ ! -f "${MANIFEST}" ]]; then
  echo "No skills manifest at ${MANIFEST}" >&2
  exit 1
fi

mkdir -p "${TARGET_SKILLS_DIR}"

installed=0
skipped=0
missing=0

while IFS=$'\t' read -r name bucket; do
  skill_dir="${SOURCE_SKILLS_DIR}/${bucket}/${name}"
  target_path="${TARGET_SKILLS_DIR}/${name}"

  if [[ ! -d "${skill_dir}" ]]; then
    echo "Missing source for ${name}: ${skill_dir}" >&2
    missing=$((missing+1))
    continue
  fi

  if [[ -e "${target_path}" || -L "${target_path}" ]]; then
    echo "Skipping ${name}: ${target_path} already exists"
    skipped=$((skipped+1))
    continue
  fi

  ln -s "${skill_dir}" "${target_path}"
  echo "Installed ${name} -> ${target_path}"
  installed=$((installed+1))
done < <(python3 - "${MANIFEST}" <<'PY'
import json, sys
with open(sys.argv[1]) as f:
    data = json.load(f)
for p in data["skills"]:
    parts = p.strip("./").split("/")
    if len(parts) != 3 or parts[0] != "skills":
        sys.exit(f"manifest entry malformed: {p}")
    print(f"{parts[2]}\t{parts[1]}")
PY
)

echo
echo "Installed ${installed}, skipped ${skipped}, missing ${missing}."
echo "Restart Codex to pick up newly installed skills."

if (( missing > 0 )); then
  exit 1
fi
