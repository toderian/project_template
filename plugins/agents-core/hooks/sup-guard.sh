#!/bin/bash
# PreToolUse guard for supervisor sessions (matcher "*"). Not registered in hooks.json: a
# supervisor's --settings file names it. Logic lives in lib/sup_guard.py. Fails closed: the
# harness treats any exit code but 2 as non-blocking, so anything but a clean 0 becomes 2.
python3 -I "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../lib/sup_guard.py"
rc=$?
[ "$rc" -eq 0 ] && exit 0
exit 2
