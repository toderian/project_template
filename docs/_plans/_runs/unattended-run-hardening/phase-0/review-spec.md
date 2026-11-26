reviewer Stage: spec, phase 0, round 0. Verdict: FAIL, findings 0/2/4. E1 not rerun by the reviewer.
1. [important] scripts/tests/live/e1-guard-holds.sh:44-51: negative 1 uses a fresh repo with no armed marker anywhere, not "a second session in the same repo that never armed the guard"; a guard that ignored session_id would still pass. Keep another session id armed on the same repo's open state, then run the unarmed session there.
2. [important] docs/meta/2026-11-26-run-guard-facts.md:19-20, 58-61: fact 4 claims plugin hooks run on `--resume -p`, but the quoted evidence is a --settings Stop hook, not a plugin hook. Quote a plugin hook_response from a resumed session, or mark that half not observed.
3. [minor] facts:95: the bypass-mode refusal has no quoted evidence and came from the outer session's classifier, not the CLI. Mark not observed.
4. [minor] facts:29-30, 66-70, 98: "pty heartbeat works" overstated: the cron fired once, then the turn stalled on a permission prompt.
5. [minor] facts:46: "same session_id" on resume is not quoted for resume.
6. [minor] live/lib.sh:79-81, 85-87: transcript_of has no caller; stop_hook_codes counts every Stop hook, so negatives 1-3 do not prove the codes came from run-guard.sh.
## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 0/2/4
