#!/usr/bin/env python3
"""Stand-in for `claude` / `codex` used by test_task_run.py.

Recognises both argv shapes the driver produces (claude: `-p --output-format json ... <prompt>`;
codex: `exec ... -o FILE -` with the prompt on stdin). Behaviour comes from the env the driver sets
(AT_TASK_ROLE, AT_TASK_STAGE, AT_TASK_PHASE) plus FAKE_SCENARIO:
  pass       every dispatch succeeds
  fail-once  the first spec review of every phase FAILs with one finding, the re-review passes
  no-status  the implementer never emits a status block
Implementers write src/phase<N>.txt (cwd is the repo). Calls are appended to FAKE_CALLS.
"""
import json, os, sys, pathlib
role = os.environ.get("AT_TASK_ROLE", "?"); stage = os.environ.get("AT_TASK_STAGE", ""); phase = os.environ.get("AT_TASK_PHASE", "0")
scenario = os.environ.get("FAKE_SCENARIO", "pass")
argv = sys.argv[1:]
codex = argv[:1] == ["exec"]
prompt = sys.stdin.read() if codex else argv[-1]
calls = pathlib.Path(os.environ["FAKE_CALLS"]); calls.parent.mkdir(parents=True, exist_ok=True)
with calls.open("a") as fh:
    fh.write(f"{role}|{stage}|{phase}|{'codex' if codex else 'claude'}|resume={'--resume' in argv}|ro={'read-only' in argv or '--disallowedTools' in argv}\n")
seen = calls.read_text().count(f"reviewer|spec|{phase}|")
if role == "implementer":
    if scenario == "no-status":
        reply = "I did the work."
    else:
        p = pathlib.Path("src"); p.mkdir(exist_ok=True)
        with (p / f"phase{phase}.txt").open("a") as fh:
            fh.write(f"work for phase {phase}, round {calls.read_text().count(f'implementer||{phase}|')}\n")
        reply = "Done.\n\n## Status: DONE\n## Summary: wrote src/phase.txt"
elif role == "reviewer" and stage == "spec" and scenario == "fail-once" and seen == 1:
    reply = "## Status: DONE_WITH_CONCERNS\n## Verdict: FAIL\n## Findings: 1 (C:1 I:0 M:0)\n1. [C] src/phase.txt:1 — missing newline\n## Report: r.md"
else:
    reply = "## Status: DONE\n## Verdict: PASS\n## Findings: 0 (C:0 I:0 M:0)\n## Report: r.md"
if codex:
    out = argv[argv.index("-o") + 1]; pathlib.Path(out).write_text(reply)
else:
    print(json.dumps({"type": "result", "result": reply, "session_id": f"sess-{role}-{phase}"}))
