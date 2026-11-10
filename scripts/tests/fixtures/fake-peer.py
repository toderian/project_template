#!/usr/bin/env python3
"""Stand-in for `claude` / `codex` in the `at peer` tests (test-at.sh copies it under both names).

Recognises the two read-only argv shapes `at peer run` produces (codex: `exec ... -s read-only
-o FILE -`, brief on stdin; claude: `-p <brief> --output-format json ...`). Each call appends
`<cli>|depth=<AT_PEER_DEPTH>|<argv>` to FAKE_PEER_CALLS. FAKE_PEER picks the behaviour:
  ok         a review with a FAIL verdict, one critical finding listed twice and one minor
  critic     a plan-critic reply (`## Plan verdict: REVISE`)
  no-status  no status block until the reminder arrives (second call)
  empty      an empty reply
  error      exit 1 with a login error on stderr
  hang       sleep 5 s (use with --timeout 1)
"""
import json, os, pathlib, sys, time
argv = sys.argv[1:]
codex = argv[:1] == ["exec"]
prompt = sys.stdin.read() if codex else argv[argv.index("-p") + 1]
with pathlib.Path(os.environ["FAKE_PEER_CALLS"]).open("a") as fh:
    fh.write(f"{'codex' if codex else 'claude'}|depth={os.environ.get('AT_PEER_DEPTH', '')}|{' '.join(a.splitlines()[0] if a else a for a in argv)}\n")
scenario = os.environ.get("FAKE_PEER", "ok")
if scenario == "hang":
    time.sleep(5)
if scenario == "error":
    sys.stderr.write("error: not logged in\nrun the login command first\n"); sys.exit(1)
finding = "1. [C] src/a.py:3 — unchecked input reaches the shell"
if scenario == "empty":
    reply = ""
elif scenario == "no-status" and "missing the report block" not in prompt:
    reply = "Looks wrong to me."
elif scenario == "critic":
    reply = "## Status: DONE_WITH_CONCERNS\n## Plan verdict: REVISE\n## Findings\n1. [I] plan.md:9 — phase 2 has no check"
else:
    reply = (f"{finding}\n\n## Status: DONE_WITH_CONCERNS\n## Verdict: FAIL\n## Findings\n{finding}\n"
             "2. [M] src/a.py:9 — name shadows a builtin")
if codex:
    pathlib.Path(argv[argv.index("-o") + 1]).write_text(reply)
else:
    print(json.dumps({"type": "result", "result": reply, "session_id": "s-1", "total_cost_usd": 0.01}))
