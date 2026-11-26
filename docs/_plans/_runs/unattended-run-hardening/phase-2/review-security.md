security-auditor, phase 2. Verdict: PASS, findings 0/1/3. No injection (model text arrives literally as $1 and stdin), no cross-session reach, no path traversal, body carries no file contents or transcript path; failure paths exit 0 with clean output.
1. [I] lib/at.py:1490: the session chooses which command runs: the marker's `meta cwd` is session-writable and feeds `git -C <cwd> config agents.notifyCommand`; a directory of plain files (HEAD, config, objects/, refs/) ran `id` from the Stop hook. Fix: take the directory from the hook payload's `.cwd`, or read only `--global` / AGENTS_NOTIFY_CMD.
2. [M] at.py:1496: pre-creating `<session>.sent/blocked-<cksum>` or making `.sent` a file drops the message (the session can also delete its marker).
3. [M] at.py:1496-1497: `.sent` as a symlink is followed: an empty 0600 file is created outside the guard dir.
4. [M] run-guard.sh:68: no rate cap: every distinct BLOCKED text sends; bounded to one message per let-through stop.
Note: a session that can write the repo's .git/config already gets command execution through git itself (core.fsmonitor); the new exposure is only finding 1.
## Status: DONE
## Verdict: PASS
## Findings: 0/1/3
