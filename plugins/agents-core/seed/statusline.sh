#!/usr/bin/env bash
# Portable statusLine command, seeded by `at init`.
#
# Line 1 comes from the user's own GSD statusline when their machine has one
# installed (so a personal setup keeps working across repos); otherwise it is a
# self-contained "model │ dir (branch)" line needing nothing beyond python3, so
# a clone on a machine without GSD still gets a sane status line.
#
# Line 2 is always this script's own: context %, session cost, and the 5-hour
# rate-limit window with its reset countdown. Segments whose data is absent are
# skipped (rate_limits only exists for Claude.ai Pro/Max after the first API
# response), and the line is omitted entirely when nothing is available.
#
# Customize freely — `at init` never overwrites this file once it exists.
set -euo pipefail

INPUT="$(cat)"

GSD_SCRIPT="${HOME:-}/.claude/hooks/gsd-statusline.js"
USE_GSD=0
if [[ -n "${HOME:-}" && -f "$GSD_SCRIPT" ]] && command -v node >/dev/null 2>&1; then
  USE_GSD=1
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


def window(key: str, label: str) -> None:
    """Append '<label> <used>% (<countdown>)' for a rate-limit window, if present.

    `rate_limits` only exists for Claude.ai Pro/Max plans, and each window can
    be independently absent, so every field is checked before use.
    """
    info = (data.get("rate_limits") or {}).get(key) or {}
    used = info.get("used_percentage")
    resets_at = info.get("resets_at")
    if not isinstance(used, (int, float)):
        return
    piece = f"{label} {int(used)}%"
    if isinstance(resets_at, (int, float)):
        remaining = int(resets_at) - int(time.time())
        if remaining > 0:
            days, rem = divmod(remaining, 86400)
            hours, rem = divmod(rem, 3600)
            minutes = rem // 60
            if days:
                piece += f" ({days}d{hours:02d}h)"
            else:
                piece += f" ({hours}h{minutes:02d}m)"
    parts.append(piece)


window("five_hour", "5h")
window("seven_day", "7d")

# Context usage as percent plus absolute tokens. `total_input_tokens` is the
# same input-only count `used_percentage` is computed from, and is 0 before the
# first API response. GSD's line 1 already has a percent bar, but not the token
# count, so this segment is shown in both modes.
def fmt_tokens(n: float) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}".rstrip("0").rstrip(".") + "M"
    return f"{n / 1000:.0f}k" if n >= 1000 else str(int(n))


ctx = data.get("context_window") or {}
ctx_pct = ctx.get("used_percentage")
ctx_used = ctx.get("total_input_tokens")
ctx_size = ctx.get("context_window_size")
if isinstance(ctx_pct, (int, float)):
    piece = f"ctx {int(ctx_pct)}%"
    if isinstance(ctx_used, (int, float)) and isinstance(ctx_size, (int, float)) and ctx_size > 0:
        piece += f" ({fmt_tokens(ctx_used)}/{fmt_tokens(ctx_size)})"
    parts.insert(0, piece)

# GSD already rendered line 1; only this script's metrics line is wanted then.
if os.environ.get("AT_STATUSLINE_SKIP_LINE1") != "1":
    print(line1)
if parts:
    print("\033[2m" + " │ ".join(parts) + "\033[0m")
PY
)

if [[ "$USE_GSD" == "1" ]]; then
  # GSD's own line, verbatim; ensure it ends with a newline so our metrics
  # line lands on its own row even if GSD omits the trailing newline.
  GSD_OUT="$(printf '%s' "$INPUT" | node "$GSD_SCRIPT" 2>/dev/null || true)"
  [[ -n "$GSD_OUT" ]] && printf '%s\n' "$GSD_OUT"
  printf '%s' "$INPUT" | AT_STATUSLINE_SKIP_LINE1=1 python3 -c "$FALLBACK_PY"
else
  printf '%s' "$INPUT" | python3 -c "$FALLBACK_PY"
fi
