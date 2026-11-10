#!/usr/bin/env bash
#
# Compare the add-on pins in plugins/agents-core/lib/addons.py with the newest
# version of each package on npm.
#
#   scripts/check-addon-pins.sh
#
# Prints one line per add-on and exits 1 when a pin is behind, 0 otherwise.
# Skipped (exit 0) when npm is not installed or the registry does not answer.
# A newer version is a prompt to review the upstream changelog, then edit the
# pin by hand; nothing here changes a file.

set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v npm >/dev/null 2>&1; then
  echo "check-addon-pins: SKIP (npm is not installed)"
  exit 0
fi

STALE=0
while read -r name package pinned; do
  if ! latest="$(npm view "$package" version 2>/dev/null)" || [[ -z "$latest" ]]; then
    echo "check-addon-pins: SKIP $name (npm did not answer for $package)"
    continue
  fi
  if [[ "$latest" == "$pinned" ]]; then
    echo "check-addon-pins: OK $name $package@$pinned"
  else
    echo "check-addon-pins: STALE $name pins $package@$pinned, npm has $latest"
    STALE=1
  fi
done < <(python3 -c '
import sys
sys.path.insert(0, "plugins/agents-core/lib")
import addons
for name, addon in addons.ADDONS.items():
    print(name, addon["package"], addon["version"])
')
exit "$STALE"
