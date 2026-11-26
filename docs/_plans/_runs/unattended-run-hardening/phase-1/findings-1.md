# Phase 1, open findings for fix round 1

Sources: review-spec.md, review-quality.md, review-security.md in this directory (line numbers and
reproductions). Each fix needs a test that fails without it. Keep the code inside the phase's
Shape (about 90 net new code lines; it is at about 76).

Hook (plugins/agents-core/hooks/run-guard.sh, lib/run-open.sh):
1. [I] `kind` comes from the matched keyword of the `Run:` line, not from a substring of the whole
   line: `Run: WAITING implementer for the BLOCKED row 3` is WAITING. (spec 1, quality 6)
2. [I] The send-back text has the open rows and the instruction on separate lines again; a test
   reads the stderr body. (quality 1)
3. [I] `text` in .status is printable ASCII only, one line, at most 300 characters, so no cut can
   split a character and no Unicode line separator survives (`LC_ALL=C tr -cd '\040-\176'`).
   (quality 2, security 1)
4. [I] No false DONE: a marker with CRLF line ends or without a trailing newline is read fully; a
   `state` target whose file is missing counts as open and is named as missing in the send-back
   text. DONE is written only when every target was found and is finished. (quality 4)
5. [I] Never trap: when the count file cannot be written (read-only guard dir, full disk) the
   stop is let through. (quality 5)
6. [M] The status cell echoed from state.md into the model's context is limited to
   `[A-Za-z0-9_-]`, at most 30 characters. (security 4)
7. [M] The lib is sourced only after the marker check; a missing lib lets the stop through
   quietly. Guard dir and files are created private (umask 077 in the hook). (quality 7, security 3)

CLI (plugins/agents-core/lib/at.py, run-guard block only):
8. [I] Prune and clear never crash `arm`: lstat in try/except; prune removes only this tool's own
   names (marker, `.status`, `.status.*` temp files, `.count`, `.watch`, `.sent/`), never an
   unrelated directory. Guard dir created with mode 0700. (quality 3, 8; security 3, 5)
9. [I] `.status` is read with `errors="replace"` and split on `\n` only. (quality 2, security 1)
10. [M] `at run-guard status` shows what exists beside `.status`: the sent-back count, the events
    already notified (`.sent/`), a watcher (`.watch`). (spec 4)

Tests:
11. [I] Add: 14-day prune of every side file; re-arm removes `.count`; text cap and flattening;
    missing lib; path with spaces; arm without CLAUDE_PID; `remind: missing jq` must fail if the
    hook did not run. (spec 2, 3; quality 9)

Live scenario (scripts/tests/live/e2-compaction.sh):
12. [M] Turn 1's prompt must not announce being sent back; the commit check must not depend on a
    commit above "phase 3" in git log; say in the header that the follow-up prompt names no task
    and that headless needs one prompt to continue. (spec 5, 6)
