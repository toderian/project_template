# Open findings, phase 2, round 1

Decided design (do not re-open): `at notify` resolves the command from `AGENTS_NOTIFY_CMD`, else
`git config agents.notifyCommand` read in ITS OWN working directory. The hook starts it with the
working directory taken from the Stop payload's `.cwd` (harness-supplied), never from the marker's
`meta cwd` (session-writable). Remove the marker-cwd lookup. The command is run as
`sh -c '<cmd> "$@"' agents-notify <title>`, so a plain program name receives the title as `$1` and a
snippet using `$1` still works.

1. [critical] (quality 1, spec 2) at.py `cmd_notify`: resolve the command first (none configured:
   return without creating a key); create `.sent/<key>` exclusively; if the command fails or times
   out, remove the key so the same event can be sent later. `at run-guard status` must not say
   "notified" for a message that never left. Tests for: failing command then working command sends;
   no command then command sends.
2. [important] (security 1) the session chooses which command runs through the marker `meta cwd`:
   apply the decided design. Test: a marker whose cwd names a directory with its own
   `agents.notifyCommand` does not run that command.
3. [important] (spec 1) a plain program name gets no title: apply the decided design. Test with a
   script file as the command, and one with a `$1` snippet. README and the skill's example stay valid.
4. [important] (quality 2) test-at.sh bad-key test cannot fail: make it fail when the key check is
   removed (assert no file is created outside `.sent` and nothing is sent).
5. [important] (quality 3) GAVE_UP: tests that it notifies and that the body and title never carry
   the model's message.
6. [important] (quality 4) the 10 s timeout: make it testable without a 10 s test (an environment
   override for tests, e.g. `AGENTS_NOTIFY_TIMEOUT`, validated as a small number) and test that a
   hanging command and its child are gone and the caller exits 0.
7. [important] (quality 5) `.sent` cannot be created for a reason other than "already exists"
   (read-only guard dir, `.sent` is a file): send anyway, undeduped, and say so in a comment; an
   `.sent` that is a symlink is not followed (security 3). Tests for read-only dir and symlink.
8. [minor] (quality 6, spec 4) tests wait with a helper that polls for the expected line count up to
   a bound, positive and negative asserts both; e3-notify.sh waits a short settle time after the first
   line before counting.
9. [minor] (quality 7, 8, 9) drop the redundant `is_dir` checks; test the title cap; header comment
   lists `<session>.sent/` and says write_status also notifies; README mentions EMPTY (an empty last
   message); `--event` without `--session` is an error (exit 2); do not block forever on stdin (read
   only when stdin is not a TTY is not enough: the hook always pipes a body, so document that a
   caller must close stdin, and make the hook-side call do so).
10. [minor] (outside the diff, same files) run-guard.sh write_status prints "Permission denied" to
    stderr when the guard dir is read-only: the redirect fails before `2>/dev/null` applies; group
    it so nothing is printed. "remind: missing jq is silent" flakes with exit 141: run-guard-remind.sh
    must read stdin before its early exits, like run-guard.sh does (it is outside this phase's
    fence; you may edit that one line there).

Ruled, do not fix: security 2 (a session can suppress its own notification by pre-creating the key;
it can also delete its marker) and security 4 (no rate cap; bounded to one message per let-through stop).
