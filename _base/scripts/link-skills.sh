#!/usr/bin/env bash
#
# Symlink every active skill (per .claude-plugin/plugin.json) into Claude
# Code's global skills directory at ~/.claude/skills/. After running this,
# the skills are available in Claude Code sessions opened from any
# directory — not just from within this repo.
#
# Source:      .claude/skills/<bucket>/<name>/
# Destination: ~/.claude/skills/<name>/                (flat, like Codex)
#
# This is the Claude-side counterpart to skills/install-codex-skills.sh.
# Without it, Claude only loads `.claude/skills/` from within this repo.
#
# Re-running is idempotent. Existing symlinks are refreshed; existing
# non-symlink entries are left alone (and printed so the user can clean
# them up manually).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
MANIFEST="${REPO_ROOT}/.claude-plugin/plugin.json"
SOURCE_TREE="${REPO_ROOT}/.claude/skills"
DEST="${HOME}/.claude/skills"

resolve_path() {
  python3 - "$1" <<'PY'
from pathlib import Path
import sys

print(Path(sys.argv[1]).expanduser().resolve(strict=False))
PY
}

if [[ ! -f "${MANIFEST}" ]]; then
  echo "error: ${MANIFEST} not found" >&2
  exit 1
fi

# Safety: refuse to run if DEST is itself a symlink pointing back into this
# repo (a previous run with a different layout could leave this state, and
# re-running would create symlinks under symlinks). Force the user to clear
# it first.
if [[ -L "${DEST}" ]]; then
  resolved="$(resolve_path "${DEST}")"
  case "${resolved}" in
    "${REPO_ROOT}"|"${REPO_ROOT}"/*)
      cat >&2 <<EOF
error: ${DEST} is a symlink into this repo (${resolved}).
Remove it ("rm ${DEST}") and re-run; the script will recreate it as a
real directory containing per-skill symlinks.
EOF
      exit 1
      ;;
  esac
fi

mkdir -p "${DEST}"

installed=0
refreshed=0
skipped=0
missing=0
pruned=0

path_is_under() {
  local child="$1" parent="$2"
  [[ "$child" == "$parent" || "$child" == "$parent/"* ]]
}

declare -A ACTIVE_NAMES

while IFS=$'\t' read -r name bucket; do
  ACTIVE_NAMES["$name"]=1
  src="${SOURCE_TREE}/${bucket}/${name}"
  target="${DEST}/${name}"

  if [[ ! -d "${src}" ]]; then
    echo "missing source for ${name}: ${src}" >&2
    missing=$((missing+1))
    continue
  fi

  if [[ -L "${target}" ]]; then
    # Existing symlink — refresh in case the source moved (e.g. bucket change)
    current="$(resolve_path "${target}" || true)"
    desired="$(resolve_path "${src}")"
    if [[ "${current}" == "${desired}" ]]; then
      skipped=$((skipped+1))
      continue
    fi
    ln -sfn "${src}" "${target}"
    echo "refreshed ${name} -> ${src}"
    refreshed=$((refreshed+1))
    continue
  fi

  if [[ -e "${target}" ]]; then
    echo "skipping ${name}: ${target} exists and is not a symlink" >&2
    skipped=$((skipped+1))
    continue
  fi

  ln -s "${src}" "${target}"
  echo "linked ${name} -> ${src}"
  installed=$((installed+1))
done < <(python3 - "${MANIFEST}" <<'PY'
import json, sys
with open(sys.argv[1]) as f:
    data = json.load(f)
for p in data["skills"]:
    parts = p.strip("./").split("/")
    if len(parts) != 3 or parts[0] != "skills":
        sys.exit(f"manifest entry malformed: {p}")
    # The plugin.json paths point at the Codex tree (./skills/<bucket>/<name>),
    # but for Claude we mirror the bucket+name from the same identifiers under
    # the .claude/skills/ tree.
    print(f"{parts[2]}\t{parts[1]}")
PY
)

source_resolved="$(resolve_path "${SOURCE_TREE}")"
while IFS= read -r -d '' entry; do
  name="$(basename "${entry}")"
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
  echo "pruned inactive ${name} -> ${resolved}"
  pruned=$((pruned+1))
done < <(find "${DEST}" -mindepth 1 -maxdepth 1 -print0 2>/dev/null)

echo
echo "Linked ${installed}, refreshed ${refreshed}, skipped ${skipped}, pruned ${pruned}, missing ${missing}."

if (( missing > 0 )); then
  exit 1
fi
