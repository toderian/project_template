#!/usr/bin/env bash
#
# Symlink every active skill (per .claude-plugin/plugin.json) into Codex's
# global skills directory. The destination tree is intentionally flat —
# Codex doesn't read our bucket layout, so we collapse `skills/<bucket>/<name>`
# down to `~/.codex/skills/<name>`.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: install-codex-skills.sh [OPTION]

Symlink every active project skill into Codex's global skills directory.

With no option, install or refresh symlinks from this repository's skills/
directory into ${CODEX_HOME:-$HOME/.codex}/skills.

Options:
  --prune-source PATH  Remove Codex skill symlinks whose resolved target is under PATH.
  --dry-run            With --prune-source, print removals without deleting symlinks.
  --help               Show this message and exit.
EOF
}

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
PRUNE_SOURCE=""
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --prune-source)
      if [[ $# -lt 2 || "$2" == --* ]]; then
        echo "--prune-source requires a PATH argument" >&2
        usage >&2
        exit 2
      fi
      PRUNE_SOURCE="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if (( DRY_RUN == 1 )) && [[ -z "${PRUNE_SOURCE}" ]]; then
  echo "--dry-run is only supported with --prune-source" >&2
  usage >&2
  exit 2
fi

resolve_path() {
  python3 - "$1" <<'PY'
from pathlib import Path
import sys

print(Path(sys.argv[1]).expanduser().resolve(strict=False))
PY
}

path_is_under() {
  local child="$1" parent="$2"
  [[ "$child" == "$parent" || "$child" == "$parent/"* ]]
}

prune_source_symlinks() {
  local source_resolved
  source_resolved="$(resolve_path "${PRUNE_SOURCE}")"

  if [[ ! -d "${TARGET_SKILLS_DIR}" ]]; then
    echo "No Codex skills directory found at ${TARGET_SKILLS_DIR}; nothing to prune."
    return 0
  fi

  local pruned=0 kept=0
  while IFS= read -r -d '' entry; do
    local name resolved
    name="$(basename "${entry}")"

    if [[ "${name}" == ".system" ]]; then
      kept=$((kept+1))
      continue
    fi

    if [[ ! -L "${entry}" ]]; then
      kept=$((kept+1))
      continue
    fi

    resolved="$(resolve_path "${entry}")"
    if ! path_is_under "${resolved}" "${source_resolved}"; then
      kept=$((kept+1))
      continue
    fi

    if (( DRY_RUN == 1 )); then
      echo "Would prune ${name} -> ${resolved}"
    else
      rm "${entry}"
      echo "Pruned ${name} -> ${resolved}"
    fi
    pruned=$((pruned+1))
  done < <(find "${TARGET_SKILLS_DIR}" -mindepth 1 -maxdepth 1 -print0 2>/dev/null)

  echo
  if (( DRY_RUN == 1 )); then
    echo "Dry run: would prune ${pruned} symlink(s) from ${TARGET_SKILLS_DIR}; kept ${kept} entries."
  else
    echo "Pruned ${pruned} symlink(s) from ${TARGET_SKILLS_DIR}; kept ${kept} entries."
  fi
  echo "Prune source: ${source_resolved}"
}

if [[ -n "${PRUNE_SOURCE}" ]]; then
  prune_source_symlinks
  exit 0
fi

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
refreshed=0
skipped=0
missing=0
pruned=0

declare -A ACTIVE_NAMES

while IFS=$'\t' read -r name bucket; do
  ACTIVE_NAMES["$name"]=1
  skill_dir="${SOURCE_SKILLS_DIR}/${bucket}/${name}"
  target_path="${TARGET_SKILLS_DIR}/${name}"

  if [[ ! -d "${skill_dir}" ]]; then
    echo "Missing source for ${name}: ${skill_dir}" >&2
    missing=$((missing+1))
    continue
  fi

  if [[ -L "${target_path}" ]]; then
    # Existing symlink — refresh in case the source moved (e.g. bucket change)
    current="$(resolve_path "${target_path}" || true)"
    desired="$(resolve_path "${skill_dir}")"
    if [[ "${current}" == "${desired}" ]]; then
      skipped=$((skipped+1))
      continue
    fi
    ln -sfn "${skill_dir}" "${target_path}"
    echo "Refreshed ${name} -> ${target_path}"
    refreshed=$((refreshed+1))
    continue
  fi

  if [[ -e "${target_path}" ]]; then
    echo "Skipping ${name}: ${target_path} exists and is not a symlink"
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

source_resolved="$(resolve_path "${SOURCE_SKILLS_DIR}")"
while IFS= read -r -d '' entry; do
  name="$(basename "${entry}")"
  if [[ "${name}" == ".system" ]]; then
    continue
  fi
  if [[ ! -L "${entry}" ]]; then
    continue
  fi
  resolved="$(resolve_path "${entry}")"
  if ! path_is_under "${resolved}" "${source_resolved}"; then
    continue
  fi
  if [[ -n "${ACTIVE_NAMES[$name]+x}" ]]; then
    continue
  fi
  rm "${entry}"
  echo "Pruned inactive ${name} -> ${resolved}"
  pruned=$((pruned+1))
done < <(find "${TARGET_SKILLS_DIR}" -mindepth 1 -maxdepth 1 -print0 2>/dev/null)

echo
echo "Installed ${installed}, refreshed ${refreshed}, skipped ${skipped}, pruned ${pruned}, missing ${missing}."
echo "Restart Codex to pick up newly installed skills."

if (( missing > 0 )); then
  exit 1
fi
