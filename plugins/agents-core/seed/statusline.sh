#!/usr/bin/env bash
# Portable statusLine command, seeded by `at init`.
#
# Prefers the user's own GSD statusline (if their machine has one installed) so
# personal setups keep working across repos; falls back to a plain
# "model | directory" line that needs nothing beyond python3, so a clone on a
# machine without GSD (or a teammate without it) still gets a sane status line.
#
# Customize freely — `at init` never overwrites this file once it exists.
set -euo pipefail

INPUT="$(cat)"

GSD_SCRIPT="${HOME:-}/.claude/hooks/gsd-statusline.js"
if [[ -n "${HOME:-}" && -f "$GSD_SCRIPT" ]] && command -v node >/dev/null 2>&1; then
  printf '%s' "$INPUT" | node "$GSD_SCRIPT"
  exit 0
fi

# `python3 -` would read this script FROM stdin, consuming the piped JSON
# before the program itself could read it — pass the code via -c instead so
# stdin stays connected to $INPUT.
FALLBACK_PY=$(cat <<'PY'
import json
import os
import subprocess
import sys
import time

try:
    data = json.load(sys.stdin)
except (json.JSONDecodeError, ValueError):
    data = {}

model = ((data.get("model") or {}).get("display_name")) or "Claude"
cwd = ((data.get("workspace") or {}).get("current_dir")) or os.getcwd()
label = os.path.basename(cwd.rstrip("/")) or cwd

branch = ""
try:
    out = subprocess.run(["git", "-C", cwd, "branch", "--show-current"],
                          capture_output=True, text=True, timeout=1)
    branch = out.stdout.strip()
except Exception:
    pass

line1 = f"{model} │ {label}" + (f" ({branch})" if branch else "")

parts = []
ctx_pct = (data.get("context_window") or {}).get("used_percentage")
if isinstance(ctx_pct, (int, float)):
    parts.append(f"ctx {int(ctx_pct)}%")

cost = (data.get("cost") or {}).get("total_cost_usd")
if isinstance(cost, (int, float)):
    parts.append(f"${cost:.2f}")

five_hour = (data.get("rate_limits") or {}).get("five_hour") or {}
used_pct = five_hour.get("used_percentage")
resets_at = five_hour.get("resets_at")
if isinstance(used_pct, (int, float)):
    piece = f"5h {int(used_pct)}%"
    if isinstance(resets_at, (int, float)):
        remaining = int(resets_at) - int(time.time())
        if remaining > 0:
            hours, rem = divmod(remaining, 3600)
            minutes = rem // 60
            piece += f" (resets {hours}h{minutes:02d}m)"
    parts.append(piece)

print(line1)
if parts:
    print(" │ ".join(parts))
PY
)
printf '%s' "$INPUT" | python3 -c "$FALLBACK_PY"
