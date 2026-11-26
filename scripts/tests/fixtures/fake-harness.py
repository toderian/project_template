#!/usr/bin/env python3
"""Stand-in for `claude` / `codex` used by test_task_run.py.

Recognises both argv shapes the driver produces (claude: `-p --output-format json ... <prompt>`;
codex: `exec ... -o FILE -` with the prompt on stdin). Behaviour comes from the env the driver sets
(AT_TASK_ROLE, AT_TASK_STAGE, AT_TASK_PHASE) plus FAKE_SCENARIO:
  pass       every dispatch succeeds
  fail-once  the first spec review of every phase FAILs with one finding, the re-review passes
  no-status  the implementer never emits a status block
  status-retry  the implementer emits the block only when reminded (second call)
  hang       every call sleeps 5 s (use with --timeout 1)
  grow       every quality review FAILs; each fix round appends 50 lines to src/phase<N>.py, so the
             driver's structural-round rule fires on round 3 and blocks the phase when it still grows
Lane tests: FAKE_BARRIER=<dir>:<k>:<phases, comma-separated> makes those phases' implementers drop a marker in <dir> and wait up to 10 s until k markers
exist (it exits 5 when they never do, so two phases run one after the other fail); FAKE_SHARED=<file> makes it
also write "phase <N>" to that file (two lanes then conflict).
Implementers write src/phase<N>.py (cwd is the repo). Calls are appended to FAKE_CALLS.
"""
import json, os, sys, pathlib
role = os.environ.get("AT_TASK_ROLE", "?"); stage = os.environ.get("AT_TASK_STAGE", ""); phase = os.environ.get("AT_TASK_PHASE", "0")
scenario = os.environ.get("FAKE_SCENARIO", "pass")
argv = sys.argv[1:]
codex = argv[:1] == ["exec"]
def claude_prompt(argv):
    # Parse like the real CLI: options with values consume exactly one argument each
    # (tool lists are comma-joined, so a space-separated list here would be a driver bug);
    # the single positional left over is the prompt. A missing/duplicate positional is an error.
    valued = {"--output-format", "--append-system-prompt", "--model", "--permission-mode", "--allowedTools",
              "--disallowedTools", "--max-budget-usd", "--resume", "--effort"}
    positionals, i = [], 0
    while i < len(argv):
        if argv[i] in valued:
            i += 2
        elif argv[i].startswith("-"):
            i += 1
        else:
            positionals.append(argv[i]); i += 1
    if len(positionals) != 1:
        sys.stderr.write(f"fake claude: expected one prompt positional, got {positionals!r}\n"); sys.exit(3)
    return positionals[0]
prompt = sys.stdin.read() if codex else claude_prompt(argv)
if not codex and not prompt.startswith(("Project:", "Fix round", "A prior implementer", "Two fix rounds", "Stage:", "Surface:", "Your previous reply")):
    sys.stderr.write(f"fake claude: prompt does not look like a driver prompt: {prompt[:60]!r}\n"); sys.exit(3)
calls = pathlib.Path(os.environ["FAKE_CALLS"]); calls.parent.mkdir(parents=True, exist_ok=True)
with calls.open("a") as fh:
    mode = argv[argv.index("--permission-mode") + 1] if "--permission-mode" in argv else ("yolo" if "--yolo" in argv else "-")
    allowed = argv[argv.index("--allowedTools") + 1] if "--allowedTools" in argv else "-"
    budget = argv[argv.index("--max-budget-usd") + 1] if "--max-budget-usd" in argv else "-"
    effort = argv[argv.index("--effort") + 1] if "--effort" in argv else next(
        (a.split("=", 1)[1].strip('"') for a in argv if a.startswith("model_reasoning_effort=")), "")
    fh.write(f"{role}|{stage}|{phase}|{'codex' if codex else 'claude'}|resume={'--resume' in argv}|ro={'--disallowedTools' in argv or (codex and 'Scope fence: read-only' in prompt)}|mode={mode}|allowed={allowed}|budget={budget}"
             + ("|structural" if "Do not add another guard" in prompt else "") + ("|size" if "\nSize: " in prompt else "") + (f"|effort={effort}" if effort else "") + "\n")
if scenario == "hang":
    import time; time.sleep(5)
seen = calls.read_text().count(f"reviewer|spec|{phase}|")
if role == "implementer" and phase in os.environ.get("FAKE_BARRIER", "::").split(":")[2].split(","):
    import time
    bdir, want, _ = os.environ["FAKE_BARRIER"].split(":"); pathlib.Path(bdir).mkdir(exist_ok=True)
    (pathlib.Path(bdir) / f"p{phase}").write_text("x")
    for _ in range(100):
        if len(list(pathlib.Path(bdir).iterdir())) >= int(want): break
        time.sleep(0.1)
    else:
        sys.stderr.write("fake: the other lane never started\n"); sys.exit(5)
if role == "implementer":
    if scenario == "no-status" or (scenario == "status-retry" and "missing the report block" not in prompt):
        reply = "I did the work."
    else:
        p = pathlib.Path("src"); p.mkdir(exist_ok=True)
        with (p / f"phase{phase}.py").open("a") as fh:
            fh.write(f"work for phase {phase}, round {calls.read_text().count(f'implementer||{phase}|')}\n")
            if scenario == "grow" and prompt.startswith(("Fix round", "Two fix rounds")):
                fh.write("guard\n" * 50)
        if os.environ.get("FAKE_SHARED"):
            pathlib.Path(os.environ["FAKE_SHARED"]).write_text(f"phase {phase}\n")
        reply = "Done.\n\n## Status: DONE\n## Summary: wrote src/phase.py"
elif role == "reviewer" and stage == "quality" and scenario == "grow":
    reply = "## Status: DONE_WITH_CONCERNS\n## Verdict: FAIL\n## Findings: 1 (C:1 I:0 M:0)\n1. [C] src/phase.py:1 — still racy\n## Report: r.md"
elif role == "reviewer" and stage == "spec" and scenario == "fail-once" and seen == 1:
    reply = "## Status: DONE_WITH_CONCERNS\n## Verdict: FAIL\n## Findings: 1 (C:1 I:0 M:0)\n1. [C] src/phase.py:1 — missing newline\n## Report: r.md"
else:
    reply = "## Status: DONE\n## Verdict: PASS\n## Findings: 0 (C:0 I:0 M:0)\n## Report: r.md"
if codex:
    out = argv[argv.index("-o") + 1]; pathlib.Path(out).write_text(reply)
else:
    print(json.dumps({"type": "result", "result": reply, "session_id": f"sess-{role}-{phase}"}))
