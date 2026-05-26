#!/usr/bin/env bash
#
# Install a curated set of Claude Code plugins by editing the user's
# ~/.claude/settings.json. Idempotent — re-running this is safe; already-listed
# marketplaces and plugins are left alone.
#
# Curated default list lives in the PLUGINS array below. Edit it to add or
# remove entries; one line per plugin in the form:
#
#   "<marketplace-repo>|<plugin-name>|<marketplace-key>"
#
# where <marketplace-repo> is a GitHub "owner/repo" the user trusts and
# <plugin-name> is the plugin entry inside that marketplace. <marketplace-key>
# is the local Claude marketplace alias used in enabledPlugins. It is optional;
# when omitted, the repo basename is used.
#
# How the install works:
#
#   1. ensure ~/.claude/settings.json exists (create empty {} if not)
#   2. for each plugin in PLUGINS:
#        - add "<marketplace-key>" under .extraKnownMarketplaces with a "github" source
#        - add "<plugin-name>@<marketplace-key>" under .enabledPlugins set to true
#   3. report what changed; ask the user to restart Claude Code
#
# NOTHING is downloaded by this script — Claude Code resolves marketplaces on
# next start. If you'd rather drive the install interactively, run inside
# Claude:
#
#   /plugin marketplace add <repo>
#   /plugin install <plugin-name>@<marketplace-key>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Source project.env if it exists.
if [[ -f "${REPO_ROOT}/project.env" ]]; then
  # shellcheck source=/dev/null
  source "${REPO_ROOT}/project.env"
fi

CLAUDE_HOME="${CLAUDE_HOME:-${HOME}/.claude}"
SETTINGS_PATH="${CLAUDE_SETTINGS_PATH:-${CLAUDE_HOME}/settings.json}"

# Curated default plugin list. Format:
#   "<owner/repo>|<plugin-name>|<marketplace-key>"
#
# The third field is optional. Keep it explicit for entries whose official
# marketplace alias differs from the GitHub repo.
# Edit this list to fit the project. Comment lines out with a leading '#'.
PLUGINS=(
  # Broad workflow plugin (TDD, debugging, planning, dispatching parallel agents).
  # Codex equivalent is vendored under plugins/superpowers/; this is the Claude variant.
  "obra/superpowers-marketplace|superpowers|superpowers-marketplace"

  # Cross-session memory for Claude. Ships .claude-plugin/ + .codex-plugin/;
  # bootstrap-third-party.sh prints the install hint, this installer makes it hands-off.
  "thedotmack/claude-mem|claude-mem|claude-mem"
)

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to merge ~/.claude/settings.json safely" >&2
  exit 1
fi

mkdir -p "${CLAUDE_HOME}"
if [[ ! -f "${SETTINGS_PATH}" ]]; then
  printf '{}\n' > "${SETTINGS_PATH}"
fi

# Build a flat list of repo / plugin-name / marketplace-key triples to pass as
# positional args to the python merger. Lines whose first character is '#' or
# that are empty are skipped (so users can leave commented examples in PLUGINS).
plugin_args=()
for entry in "${PLUGINS[@]}"; do
  trimmed="${entry#"${entry%%[![:space:]]*}"}"
  [[ -z "${trimmed}" ]] && continue
  [[ "${trimmed:0:1}" == "#" ]] && continue

  if [[ "${entry}" != *"|"* ]]; then
    echo "Skipping malformed entry (no '|' delimiter): ${entry}" >&2
    continue
  fi
  IFS='|' read -r repo plugin_name marketplace_key extra <<<"${entry}"
  if [[ -n "${extra:-}" ]]; then
    echo "Skipping malformed entry (too many '|' delimiters): ${entry}" >&2
    continue
  fi
  if [[ -z "${repo}" || -z "${plugin_name}" ]]; then
    echo "Skipping malformed entry (empty required field): ${entry}" >&2
    continue
  fi
  if [[ -z "${marketplace_key:-}" ]]; then
    marketplace_key="${repo##*/}"
  fi
  if [[ -z "${marketplace_key}" ]]; then
    echo "Skipping malformed entry (empty marketplace key): ${entry}" >&2
    continue
  fi

  plugin_args+=("${repo}" "${plugin_name}" "${marketplace_key}")
done

if [[ ${#plugin_args[@]} -eq 0 ]]; then
  echo "No plugins to install (PLUGINS array is empty after filtering)."
  exit 0
fi

python3 - "${SETTINGS_PATH}" "${plugin_args[@]}" <<'PY'
import json, sys
from pathlib import Path

settings_path = Path(sys.argv[1])
data = json.loads(settings_path.read_text() or "{}")

marketplaces = data.setdefault("extraKnownMarketplaces", {})
enabled = data.setdefault("enabledPlugins", {})

added_marketplaces = []
added_plugins = []
skipped_marketplaces = []
skipped_plugins = []

# sys.argv[2:] is a flat list of (repo, plugin_name, marketplace_key) triples.
args = sys.argv[2:]
if len(args) % 3 != 0:
    sys.exit(f"internal error: expected triples of plugin args, got {len(args)}")

for repo, plugin_name, marketplace_key in zip(args[0::3], args[1::3], args[2::3]):
    plugin_key = f"{plugin_name}@{marketplace_key}"

    if marketplace_key in marketplaces:
        skipped_marketplaces.append(marketplace_key)
    else:
        marketplaces[marketplace_key] = {
            "source": {"source": "github", "repo": repo}
        }
        added_marketplaces.append(marketplace_key)

    if plugin_key in enabled:
        skipped_plugins.append(plugin_key)
    else:
        enabled[plugin_key] = True
        added_plugins.append(plugin_key)

settings_path.write_text(json.dumps(data, indent=2) + "\n")

def report(label, added, skipped):
    for item in added:
        print(f"  + {label}: {item}")
    for item in skipped:
        print(f"  = {label}: {item} (already present, left as-is)")

print(f"Updated {settings_path}")
report("marketplace", added_marketplaces, skipped_marketplaces)
report("plugin    ", added_plugins, skipped_plugins)
PY

echo
echo "Restart Claude Code to fetch and enable the plugins."
