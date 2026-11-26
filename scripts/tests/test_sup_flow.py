#!/usr/bin/env python3
"""`at sup` end to end through lib/at.py: init, pack, a worker's question and answer, the watcher waking and landing it.

Real code throughout; only `claude` is a fake script (AGENTS_CLAUDE_BIN) and the hub is a throwaway git repo
without a task ledger. The commands run in a non-git directory, so the hub comes from the profile's config.
"""
import json, os, stat, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "plugins/agents-core/lib"
sys.path.insert(0, str(LIB))
import sup_guard
import sup_state as st

TASK_FILE = """| Field | Value |
|---|---|
| Task ID | TST-009 |

## Ready task

Resources: none

### Phases

#### Phase 1: Build

Files: `src/a.py`
- Checks: `python3 -m unittest`
- [ ] do it

### Acceptance criteria

- [ ] works

### Unattended run

Checked: 2026-11-26, READY
Authorised: restart the dev server
Owner only: push
Defaults: if X, do Y
"""
FAKE_CLAUDE = """#!/usr/bin/env python3
import json, os, sys
d, a = os.environ["FAKE_DIR"], sys.argv[1:]
with open(d + "/claude.log", "a") as f:
    f.write(json.dumps({"argv": a, "cwd": os.getcwd(), "env": {k: v for k, v in os.environ.items() if k.startswith("AGENTS_")}}) + "\\n")
if a[:1] == ["--bg"] and "--resume" not in a:
    name = a[a.index("--name") + 1]
    open(d + "/name", "w").write(name)
    print("backgrounded \\u00b7 abcd1234 \\u00b7 " + name)
elif a[:1] == ["agents"]:
    name = open(d + "/name").read() if os.path.exists(d + "/name") else ""
    print(json.dumps([{"sessionId": "abcd1234-full", "name": name, "pid": 77}]))
elif "-p" in a:
    print(json.dumps({"result": "TICK done: 1 handled, 0 left for the owner", "total_cost_usd": 0.01}))
"""
TASK, SESSION = "TST-009", "abcd1234-full"


def git(path, *a):
    return subprocess.run(["git", "-C", str(path), *a], capture_output=True, text=True, check=True).stdout.strip()


class Flow(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(); self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name).resolve()
        self.hub, self.work = self.tmp / "hub", self.tmp / "elsewhere"
        self.hub.mkdir(); self.work.mkdir()
        git(self.hub, "init", "-q", "-b", "main"); git(self.hub, "config", "user.name", "T"); git(self.hub, "config", "user.email", "t@example.invalid")
        (self.hub / "README.md").write_text("base\n")
        todo = self.hub / "docs/tasks_manager/_todos"; todo.mkdir(parents=True)
        (todo / f"{TASK}-F_x.md").write_text(TASK_FILE)
        git(self.hub, "add", "-A"); git(self.hub, "commit", "-q", "-m", "base")
        for name, body in (("claude", FAKE_CLAUDE), ("at", f'#!/bin/sh\nexec "{sys.executable}" "{LIB / "at.py"}" "$@"\n')):
            (self.tmp / name).write_text(body); (self.tmp / name).chmod(stat.S_IRWXU)
        (self.tmp / "profile.json").write_text(json.dumps({"repos": [], "resources": [], "cap": 2, "land": "auto", "operators": []}))
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(("AGENTS_", "CLAUDE_CODE_", "FAKE_"))}
        self.env.update(AGENTS_SUP_DIR=str(self.tmp / "sup"), AGENTS_LEASE_DIR=str(self.tmp / "leases"), AGENTS_CLAUDE_BIN=str(self.tmp / "claude"),
                        AGENTS_AT_BIN=str(self.tmp / "at"), FAKE_DIR=str(self.tmp))
        os.environ.update(AGENTS_SUP_DIR=self.env["AGENTS_SUP_DIR"], AGENTS_LEASE_DIR=self.env["AGENTS_LEASE_DIR"])
        self.addCleanup(lambda: [os.environ.pop(k, None) for k in ("AGENTS_SUP_DIR", "AGENTS_LEASE_DIR")])

    def at(self, *argv, env=None, ok=True):
        p = subprocess.run([sys.executable, str(LIB / "at.py"), "sup", *argv, "--profile", "p"], cwd=self.work, capture_output=True,
                           text=True, env={**self.env, **(env or {})}, timeout=60)
        if ok:
            self.assertEqual(p.returncode, 0, f"at sup {' '.join(argv)}: {p.stdout}{p.stderr}")
        return p

    def claude_calls(self):
        return [json.loads(x) for x in (self.tmp / "claude.log").read_text().splitlines()]

    def test_init_to_landed(self):
        self.at("init", "--hub", str(self.hub), "--from", str(self.tmp / "profile.json"))
        self.assertEqual(st.config("p")["hub"], str(self.hub))
        self.assertEqual(git(self.hub, "status", "--porcelain"), "")  # the generated .claude files are excluded
        self.at("pack", "a", TASK); self.at("start-pack", "a")

        self.assertEqual(self.at("watch", "once", "--no-tick").stdout.split(), ["started", TASK])
        worker = st.worker_for("p", task=TASK)
        wt = self.tmp / "hub-tst-009"
        self.assertEqual((worker["session"], worker["state"], worker["cwd"]), (SESSION, "running", str(wt)))
        first = self.claude_calls()[0]
        self.assertEqual(first["env"]["AGENTS_SUP_TASK"], TASK); self.assertEqual(first["env"]["AGENTS_SUPERVISOR"], "p")
        self.assertEqual(Path(first["cwd"]).resolve(), wt)

        worker_env = {"AGENTS_SUPERVISOR": "p", "AGENTS_SUP_TASK": TASK, "CLAUDE_CODE_SESSION_ID": SESSION}
        out = self.at("ask", "Which db?", "--option", "pg", "--option", "sqlite", "--recommend", "pg", env=worker_env).stdout
        self.assertEqual(out, "Q1\nWAITING supervisor: Q1\n")
        status = self.at("status").stdout
        self.assertIn("OPEN QUESTIONS (1)", status); self.assertIn("Q1 TST-009: Which db?", status)
        self.assertEqual(self.at("watch", "once", "--no-tick").stdout.split(), [])  # nothing to wake yet

        self.at("answer", "Q1", "sqlite")
        self.assertEqual(st.worker_for("p", task=TASK)["state"], "stopped")
        self.assertEqual(self.at("watch", "once", "--no-tick").stdout.split(), ["restarted", TASK])
        verbs = [c["argv"][0] for c in self.claude_calls() if c["argv"][0] in ("stop", "--bg")]
        self.assertEqual(verbs[-2:], ["stop", "--bg"]); self.assertIn("--resume", self.claude_calls()[-1]["argv"])
        self.assertEqual(st.worker_for("p", task=TASK)["state"], "running")
        self.assertIn("sqlite", self.at("inbox", env=worker_env).stdout)

        # the worker closes the task out on its branch; the Stop hook (sup_event) marks the row done
        (wt / "docs/tasks_manager/_todos_archived").mkdir(parents=True)
        git(wt, "mv", f"docs/tasks_manager/_todos/{TASK}-F_x.md", f"docs/tasks_manager/_todos_archived/{TASK}-F_x.md")
        (wt / "src").mkdir(); (wt / "src/a.py").write_text("x = 1\n")
        git(wt, "add", "-A"); git(wt, "commit", "-q", "-m", f"{TASK} work"); git(wt, "commit", "-q", "--allow-empty", "-m", f"{TASK} closeout")
        with st.locked("p"):
            st.set_worker("p", SESSION, state="done")
        before = int(git(self.hub, "rev-list", "--count", "main"))
        landing = self.at("watch", "once").stdout.split()  # this pass may tick: the fake `claude -p` ends with TICK done
        self.assertEqual(landing[:2], ["landed", TASK]); self.assertEqual(landing[2:], ["tick"])
        self.assertEqual(int(git(self.hub, "rev-list", "--count", "main")), before + 1)
        self.assertTrue((self.hub / "src/a.py").exists()); self.assertFalse(wt.exists())
        self.assertIn("landed", [e["kind"] for e in st.events_since("p", 0)])
        self.assertEqual(st.cursor("p"), st.events_since("p", 0)[-1]["id"])  # the tick handled everything
        tick = [c for c in self.claude_calls() if "-p" in c["argv"]][0]
        self.assertEqual(tick["argv"][tick["argv"].index("--agent") + 1], "p-supervisor")
        self.assertEqual(Path(tick["cwd"]).resolve(), self.hub)

        self.assertEqual(self.at("done", "a").stdout.strip(), "done: a")
        self.assertEqual(json.loads(self.at("measure", "--json").stdout)["tasks_landed"], 1)

    def test_every_chat_only_command_is_refused_in_a_claude_session_without_a_token(self):
        self.at("init", "--hub", str(self.hub), "--from", str(self.tmp / "profile.json"))
        args = {"instruct": ["x"], "pack": ["b", TASK], "start-pack": ["b"], "pause-pack": ["b"], "close-pack": ["b"],
                "order": ["b", TASK], "cap": ["2"], "watch start": [], "watch stop": [], "init": ["--force"]}
        self.assertEqual(sorted(args), sorted(sup_guard.CHAT_COMMANDS))
        session = {"CLAUDE_CODE_SESSION_ID": "worker-1"}
        for cmd, rest in args.items():
            p = self.at(*cmd.split(), *rest, env=session, ok=False)
            self.assertEqual((cmd, p.returncode), (cmd, 3), p.stderr); self.assertIn("only the owner's chat", p.stderr)
        self.at("ask", "Q?", env={**session, "AGENTS_SUP_TASK": TASK})  # the worker side stays open
        p = self.at("answer", "Q1", "x", "--owner", env=session, ok=False); self.assertEqual(p.returncode, 3)
        self.assertEqual(self.at("answer", "Q1", "x", env=session).returncode, 0)

    def test_every_guard_rule_for_at_sup_names_a_command_that_exists(self):
        import argparse, sup
        top = argparse.ArgumentParser(); sup.add_parser(top.add_subparsers())
        sup_parser = next(a for a in top._actions if isinstance(a, argparse._SubParsersAction)).choices["sup"]
        cmds = next(a for a in sup_parser._actions if isinstance(a, argparse._SubParsersAction)).choices
        for rule in sup_guard.DEFAULT_MAIN:
            if rule["argv"][:2] == ["at", "sup"]:
                self.assertIn(rule["argv"][2], cmds, rule)
                for flag in rule["flags"]:
                    self.assertIn(flag, cmds[rule["argv"][2]]._option_string_actions if rule["argv"][2] != "watch" else
                                  next(a for a in cmds["watch"]._actions if isinstance(a, argparse._SubParsersAction)).choices[
                                      rule["argv"][3]]._option_string_actions, rule)
        for gone in ("init", "tick", "chat", "ask", "need", "release"):
            self.assertFalse([r for r in sup_guard.DEFAULT_MAIN if r["argv"][:3] == ["at", "sup", gone]], gone)
        self.assertFalse([r for r in sup_guard.DEFAULT_MAIN if r["argv"][:4] == ["at", "sup", "watch", "once"]])


if __name__ == "__main__":
    unittest.main()
