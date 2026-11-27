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
if "--resume" in a:
    print("woke session " + a[a.index("--resume") + 1][:8] + " with its saved options")
elif a[:1] == ["--bg"]:
    name = a[a.index("--name") + 1]
    open(d + "/name", "w").write(name); open(d + "/sid", "w").write(a[a.index("--session-id") + 1])
    print("backgrounded \\u00b7 " + a[a.index("--session-id") + 1][:8] + " \\u00b7 " + name)
elif a[:1] == ["agents"]:
    sid = open(d + "/sid").read() if os.path.exists(d + "/sid") else ""
    print(json.dumps([{"sessionId": sid, "name": "x", "pid": 77}] if sid else []))
elif "-p" in a:
    print(json.dumps({"result": "TICK done: 1 handled, 0 left for the owner", "total_cost_usd": 0.01}))
"""
TASK = "TST-009"


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
        SESSION = worker["session"]
        self.assertEqual((worker["state"], worker["cwd"]), ("running", str(wt)))
        first = self.claude_calls()[0]
        self.assertEqual(first["argv"][first["argv"].index("--session-id") + 1], SESSION)
        self.assertEqual(first["env"]["AGENTS_SUP_TASK"], TASK); self.assertEqual(first["env"]["AGENTS_SUPERVISOR"], "p")
        self.assertEqual(Path(first["cwd"]).resolve(), wt)

        worker_env = {"AGENTS_SUPERVISOR": "p", "AGENTS_SUP_TASK": TASK, "CLAUDE_CODE_SESSION_ID": SESSION}
        out = self.at("ask", "Which db?", "--option", "pg", "--option", "sqlite", "--recommend", "pg", env=worker_env).stdout
        self.assertTrue(out.startswith("Q1\n") and out.endswith("WAITING supervisor: Q1\n"), out)
        status = self.at("status").stdout
        self.assertIn("OPEN QUESTIONS (1)", status); self.assertIn("Q1 TST-009 BLOCKING: Which db?", status)
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
        done = wt / f"docs/tasks_manager/_todos_archived/{TASK}-F_x.md"; done.write_text(done.read_text().replace("- [ ]", "- [x]"))
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
        self.assertEqual(Path(tick["cwd"]).resolve(), (st.profile_dir("p") / "conf").resolve())  # never the hub

        self.assertEqual(self.at("done", "a").stdout.strip(), "done: a")
        self.assertEqual(json.loads(self.at("measure", "--json").stdout)["tasks_landed"], 1)

    def close_out(self, task, wt):
        (wt / "docs/tasks_manager/_todos_archived").mkdir(parents=True, exist_ok=True)
        git(wt, "mv", f"docs/tasks_manager/_todos/{task}-F_x.md", f"docs/tasks_manager/_todos_archived/{task}-F_x.md")
        f = wt / f"docs/tasks_manager/_todos_archived/{task}-F_x.md"; f.write_text(f.read_text().replace("- [ ]", "- [x]")); git(wt, "add", "-A")
        git(wt, "commit", "-q", "-m", f"{task} closeout")

    def test_a_pack_with_a_sibling_repo_runs_two_tasks_in_order_and_done_names_the_branch(self):
        T1, T2 = "TST-009", "TST-010"
        sib = self.tmp / "sib"; sib.mkdir()
        git(sib, "init", "-q", "-b", "dev"); git(sib, "config", "user.name", "T"); git(sib, "config", "user.email", "t@example.invalid")
        git(sib, "commit", "-q", "--allow-empty", "-m", "sib base")
        (self.hub / ".config").mkdir(); (self.hub / ".local").mkdir(); (self.hub / ".gitignore").write_text(".local/\n")
        (self.hub / ".config/repos.project.md").write_text("| Repo | Required | Role | Default branch | Integration branch | Work mode |\n|---|---|---|---|---|---|\n"
                                                           "| hub | yes | x | main | main | d |\n| sib | no | x | dev | dev | d |\n")
        (self.hub / ".local/repos.map").write_text(f"hub: {self.hub}\nsib: {sib}\n")
        todo = self.hub / "docs/tasks_manager/_todos"
        for t in (T1, T2):
            (todo / f"{t}-F_x.md").write_text(TASK_FILE.replace(TASK, t).replace("| Task ID |", "| Repos | `sib` |\n| Task ID |"))
        git(self.hub, "add", "-A"); git(self.hub, "commit", "-q", "-m", "tasks and registry")
        self.at("init", "--hub", str(self.hub), "--from", str(self.tmp / "profile.json"))
        self.at("pack", "a", T1, T2, "--branch", "sib=feat/x"); self.at("start-pack", "a")
        pw, tip0 = self.tmp / "sib-a", git(sib, "rev-parse", "dev")
        self.assertEqual(st.read_pack("p", "a")["tips"], {"sib": tip0})
        tips, hub_commits = [tip0], int(git(self.hub, "rev-list", "--count", "main"))
        for n, t in enumerate((T1, T2), 1):
            self.assertEqual(self.at("watch", "once", "--no-tick").stdout.split(), ["started", t])
            wt = self.tmp / f"hub-{t.lower()}"
            self.assertIn(f"sib: {pw}", (wt / ".local/repos.map").read_text())
            self.assertEqual(git(pw, "rev-list", "--count", f"{tip0}..HEAD"), str(n - 1))  # the second task starts on the first one's commit
            (pw / f"p{n}.py").write_text("x\n"); git(pw, "add", "-A"); git(pw, "commit", "-q", "-m", f"{t} phase 1")
            self.close_out(t, wt)
            with st.locked("p"):
                st.set_worker("p", st.worker_for("p", task=t)["session"], state="done")
            if n == 2:  # a dirty pack worktree refuses the landing; an ignored file under .local is kept
                (wt / ".local/notes.txt").write_text("n\n"); (pw / "half.py").write_text("x")
                p = self.at("land", t, ok=False); self.assertEqual(p.returncode, 3); self.assertIn("uncommitted changes", p.stderr)
                (pw / "half.py").unlink()
            self.assertEqual(self.at("watch", "once", "--no-tick").stdout.split(), ["landed", t])
            tips.append(git(pw, "rev-parse", "HEAD"))
            self.assertIn(f"sib feat/x {tips[-2]}..{tips[-1]}", git(self.hub, "log", "-1", "--format=%B"))
            self.assertEqual(st.read_pack("p", "a")["tips"], {"sib": tips[-1]})
        self.assertEqual(int(git(self.hub, "rev-list", "--count", "main")), hub_commits + 2)
        self.assertEqual((self.tmp / "sup/_host/kept" / T2 / ".local/notes.txt").read_text(), "n\n")
        self.assertFalse((self.tmp / "sup/_host/kept" / T2 / ".local/repos.map").exists())
        done = self.at("done", "a").stdout
        self.assertIn("sib: feat/x, 2 commit(s) over dev, ready for PR", done); self.assertTrue(done.endswith("done: a\n"))
        (pw / "late.py").write_text("x"); git(pw, "add", "-A"); git(pw, "commit", "-q", "-m", "late")
        late = self.at("done", "a", ok=False); self.assertEqual(late.returncode, 3); self.assertIn("1 commit(s) above the landed tip", late.stdout); self.assertIn("at sup accept-tip a sib", late.stdout)

    def test_every_chat_only_command_is_refused_in_a_claude_session_without_a_token(self):
        self.at("init", "--hub", str(self.hub), "--from", str(self.tmp / "profile.json"))
        args = {"instruct": ["x"], "pack": ["b", TASK], "start-pack": ["b"], "pause-pack": ["b"], "close-pack": ["b"],
                "order": ["b", TASK], "cap": ["2"], "accept-tip": ["b", "sib"], "watch start": [], "watch stop": [], "init": ["--force"]}
        self.assertEqual(sorted(args), sorted(sup_guard.CHAT_COMMANDS))
        session = {"CLAUDE_CODE_SESSION_ID": "worker-0001"}
        for cmd, rest in args.items():
            p = self.at(*cmd.split(), *rest, env=session, ok=False)
            self.assertEqual((cmd, p.returncode), (cmd, 3), p.stderr); self.assertIn("only the owner's chat", p.stderr)
        st.set_worker("p", "worker-0001", task=TASK, state="running", mode="bg")  # a worker that `start-worker` registered
        self.at("ask", "Q?", env={**session, "AGENTS_SUP_TASK": TASK})  # the worker side stays open
        p = self.at("answer", "Q1", "x", "--owner", env=session, ok=False); self.assertEqual(p.returncode, 3)
        p = self.at("answer", "Q1", "x", env=session, ok=False); self.assertEqual(p.returncode, 3)  # a registered worker may not answer
        self.assertEqual(self.at("answer", "Q1", "x").returncode, 0)  # the supervisor's tick (no worker row) may

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
