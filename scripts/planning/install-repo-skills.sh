#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SOURCE_SKILLS_DIR="${REPO_ROOT}/skills"
CODEX_HOME="${CODEX_HOME:-${HOME}/.codex}"
TARGET_SKILLS_DIR="${CODEX_HOME}/skills"

if [[ ! -d "${SOURCE_SKILLS_DIR}" ]]; then
  echo "No repo skills directory found at ${SOURCE_SKILLS_DIR}" >&2
  exit 1
fi

mkdir -p "${TARGET_SKILLS_DIR}"

for skill_dir in "${SOURCE_SKILLS_DIR}"/*; do
  [[ -d "${skill_dir}" ]] || continue

  skill_name="$(basename "${skill_dir}")"
  target_path="${TARGET_SKILLS_DIR}/${skill_name}"

  if [[ -e "${target_path}" || -L "${target_path}" ]]; then
    echo "Skipping ${skill_name}: ${target_path} already exists"
    continue
  fi

  ln -s "${skill_dir}" "${target_path}"
  echo "Installed ${skill_name} -> ${target_path}"
done

echo "Restart Codex to pick up newly installed skills."
