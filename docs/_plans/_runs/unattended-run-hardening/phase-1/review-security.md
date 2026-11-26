security-auditor, phase 1, round 0. Verdict: PASS, findings 0/1/4.
1. [I] hooks/run-guard.sh:45 + lib/at.py:1421: Unicode line separators (U+2028, U+2029, U+0085) survive the `text` sanitiser (tr strips only \000-\037) and Python splitlines() splits on them: `at run-guard status` shows forged `kind=DONE`, `mode=bypassPermissions`. The guard itself is not disarmed (grep -qx splits on \n only). Fix: restrict text to printable ASCII (`LC_ALL=C tr -cd '\040-\176'`), split on \n only in at.py and the watchdog.
2. [M] at.py:1441-1442 (design limit for phase 4): meta pid and cwd come from the session's environment; the session can also write the marker and .status. A watchdog must not take the restart permission mode from .status `mode`, and must verify the pid belongs to a claude process.
3. [M] at.py:1435, run-guard.sh:52,82: guard dir created with the default umask; GAVE_UP stores 300 chars of the raw last message. mkdir 0700, umask 077 in the hook.
4. [M] hooks/lib/run-open.sh:12-13,28,38: the status cell of state.md is echoed into model context with no length or character limit. Keep [A-Za-z0-9_-], cap ~30 chars.
5. [M] at.py:1438: old.stat() raises on a dangling symlink in the guard dir, arm crashes. lstat() in try/except.
Passes: session_id sanitised, no eval, kind is a literal, transcript and mode come from the payload.
## Status: DONE
## Verdict: PASS
## Findings: 0/1/4
