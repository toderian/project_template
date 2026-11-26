#!/usr/bin/env python3
"""Tests for plugins/agents-core/lib/sup_guard.py (the supervisor command guard)."""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIB = os.path.join(ROOT, "plugins", "agents-core", "lib")
HOOK = os.path.join(ROOT, "plugins", "agents-core", "hooks", "sup-guard.sh")
sys.path.insert(0, LIB)
import sup_guard as g  # noqa: E402

TABLES = {"main": g.DEFAULT_MAIN, "programs": []}

ALLOWED = [
    "at sup status", "at sup status --json", "at sup board", "at sup queue --json",
    "at sup ready RM-1", "at sup answer Q1 yes go ahead", "at sup answer Q12 'use the second one?' --profile rm",
    "at sup start-worker RM-1", "at sup stop-worker RM-1", "at sup land RM-1 --dry-run",
    "at sup grant RM-1 lab", "at sup deny RM-1 lab 'not now'", "at sup done alpha", "at sup packs --profile rm",
    "at sup measure --json --since 2026-11-01", "at sup watch status", "at sup instructions", "at sup queue --all",
    "at lease take lab --ttl 30", "at lease take lab --ttl=30 --for RM-1 --reason waiting --restore",
    "at lease release lab", "at lease list --json", "at run-guard status --all",
    "claude agents --json", "claude agents --json --all",
    "git status --short --porcelain", "git log --oneline -n 5 main", "git log --format=%H",
    "git branch --show-current", "git branch --list", "git worktree list --porcelain",
    "git rev-parse --short --abbrev-ref HEAD", "git diff --stat a b",
    "gh pr view 12 --json state", "gh pr view feature/x", "gh pr list --state open --limit 5",
    "gh pr checks 12",
]
DENIED = [
    "at sup status; rm -rf x", "at sup status && x", "at sup status | x", "at sup status > f",
    "$(x)", "`x`", "FOO=1 at sup status", "PATH=. at sup status", "/usr/bin/git status",
    "./at sup status", 'sh -c "at sup status"', 'bash -lc "at sup status"',
    "at lease run x -- sh -c y", "at lease clear x --restored", "at sup push p",
    "git -c core.pager=x status", "git -c alias.x=!y x", "git -C /tmp status",
    "git --git-dir=x status", "git --no-pager log", "git diff --ext-diff", "git diff --stat --output=f",
    "git log --output=f", "git log -O x", "git log --upload-pack=x", "git grep -Ox y",
    "git push", "git commit -m x", "git log a b", "git diff --stat a b c",
    "gh api /x", "gh alias set a b", "gh pr view 1 --web", "gh pr list --web", "gh pr checks",
    "claude -p x", "claude --bg x", "claude agents", "claude agents --all",
    "at sup status\nrm x", "at sup status\rx", "at sup status 'unterminated", "", "   ",
    'at sup answer RM-1 "text with $(x)"', "at sup answer rm-1 x", "at sup answer RM-1",
    "at lease take lab", "at lease take lab --ttl x", "at sup status --json --json",
    "at sup status --bogus", "at sup status --", "at sup status extra", "at sup ready -x",
    "at sup inbox RM-1", "at sup answer RM-1 yes", "at sup stop-worker RM-1 --stuck", "at sup op deploy now",
    "at sup measure alpha", "at sup worktree RM-1", "at sup status --hub /tmp", "at sup land RM-1 --into x",
    "at sup init --hub /tmp", "at sup tick", "at sup chat", "at sup watch once", "at sup watch start",
    "at sup ask 'q'", "at sup need lab --minutes 5", "at sup release lab", "at sup status --profile Bad",
    "git log [-]-output=x", "at sup answer T-1 [-]-owner yes", "git log *", "git log ?", "git log ~",
    "git log a#b", "git log ^a", "git log !a", 'at sup answer RM-1 "double quoted"',
    "at sup  status", "git log " + "a" * 9000, "gh pr view https://x/pull/1", "git log /etc/passwd",
    "git log HEAD:.env", "git log ~x", "git log .hidden", "git log --format=%G?", "git log --format=%H%GG",
    "at sup instruct x", "at sup answer Q1 x --owner", "at sup start-pack alpha", "at sup cap 3",
    "at sup pack alpha RM-1", "at sup watch stop", "at sup close-pack alpha",
]


class DecideTable(unittest.TestCase):
    def test_allowed(self):
        for cmd in ALLOWED:
            with self.subTest(cmd=cmd):
                self.assertTrue(g.decide(cmd, None, TABLES)[0], cmd)

    def test_denied(self):
        for cmd in DENIED:
            with self.subTest(cmd=cmd):
                self.assertFalse(g.decide(cmd, None, TABLES)[0], cmd)

    def test_non_bash_and_non_string(self):
        self.assertFalse(g.decide(None, None, TABLES)[0])
        self.assertFalse(g.decide("at sup status\x00", None, TABLES)[0])


class ChatToken(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = {k: os.environ.get(k) for k in ("AGENTS_SUP_DIR", "AGENTS_SUP_CHAT_TOKEN")}
        os.environ["AGENTS_SUP_DIR"] = self.tmp.name
        os.environ.pop("AGENTS_SUP_CHAT_TOKEN", None)
        self.addCleanup(self.restore)

    def restore(self):
        for k, v in self.env.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)

    def token(self, tok="a1b2c3d4e5f60718", sid="chat1", expires=None, mode=0o600, dmode=0o700):
        d = os.path.join(self.tmp.name, "_tokens")
        os.makedirs(d, exist_ok=True)
        os.chmod(d, dmode)
        path = os.path.join(d, tok)
        with open(path, "w") as f:
            json.dump({"session_id": sid, "expires": time.time() + 60 if expires is None else expires}, f)
        os.chmod(path, mode)
        os.environ["AGENTS_SUP_CHAT_TOKEN"] = tok

    def test_chat_commands(self):
        cmds = ["at sup instruct x", "at sup answer Q1 x --owner", "at sup start-pack alpha",
                "at sup pause-pack alpha", "at sup close-pack alpha", "at sup order alpha RM-1", "at sup cap 3",
                "at sup pack alpha RM-1 RM-2 --parallel", "at sup watch start --no-tick", "at sup watch stop"]
        for cmd in cmds:  # no token set
            self.assertEqual(g.decide(cmd, None, TABLES, "chat1"), (False, "chat only"), cmd)
        os.environ["AGENTS_SUP_CHAT_TOKEN"] = "a1b2c3d4e5f60718"  # token set, file missing
        self.assertFalse(g.check_chat_token("chat1"))
        self.token()
        for cmd in cmds:
            self.assertTrue(g.decide(cmd, None, TABLES, "chat1")[0], cmd)
        # a table rule without the chat flag cannot open a chat-only command
        free = {"main": [{"argv": ["at", "sup", "cap"], "flags": {}, "args": ["int"], "required": []}]}
        self.assertTrue(g.decide("at sup cap 3", None, free, "chat1")[0])
        os.environ["AGENTS_SUP_CHAT_TOKEN"] = "../a1b2c3d4e5f60718"
        self.assertFalse(g.decide(cmds[0], None, TABLES, "chat1")[0])
        for cmd in ("at sup push p", "at lease clear x", "at lease run x y"):  # never, even with token
            self.token()
            self.assertFalse(g.decide(cmd, None, TABLES, "chat1")[0], cmd)

    def test_token_checks(self):
        self.token()
        self.assertTrue(g.check_chat_token("chat1"))
        self.assertFalse(g.check_chat_token("other"))  # another session
        self.assertFalse(g.check_chat_token(None))
        self.token(expires=time.time() - 1)
        self.assertFalse(g.check_chat_token("chat1"))  # expired
        self.token(mode=0o644)
        self.assertFalse(g.check_chat_token("chat1"))
        self.token(dmode=0o755)
        self.assertFalse(g.check_chat_token("chat1"))
        self.token()
        os.symlink(os.path.join(self.tmp.name, "_tokens", "a1b2c3d4e5f60718"),
                   os.path.join(self.tmp.name, "_tokens", "b1b2c3d4e5f60718"))
        os.environ["AGENTS_SUP_CHAT_TOKEN"] = "b1b2c3d4e5f60718"
        self.assertFalse(g.check_chat_token("chat1"))  # symlink refused


class LauncherEnv(unittest.TestCase):
    def test_path_keeps_the_tools_and_drops_hub_directories(self):
        import shutil, tempfile
        with tempfile.TemporaryDirectory() as t:
            hub, other = os.path.join(t, "hub"), os.path.join(t, "bin")
            for d in (hub + "/bin", other):
                os.makedirs(d)
            for d in (hub + "/bin", other):
                open(d + "/at", "w").close(); os.chmod(d + "/at", 0o755)
            base = {"PATH": ":".join([hub + "/bin", other, "relative", "/usr/bin"])}
            path = g.launcher_env(base, deny_under=[hub])["PATH"].split(":")
            self.assertEqual(path[0], other); self.assertNotIn(hub + "/bin", path); self.assertEqual(path[-2:], ["/usr/bin", "/bin"])
            self.assertTrue(all(os.path.isabs(p) for p in path))
            self.assertIn(hub + "/bin", g.launcher_env(base)["PATH"])
        if shutil.which("claude"):
            self.assertIn(os.path.dirname(shutil.which("claude")), g.launcher_env(os.environ)["PATH"].split(":"))

    def test_launcher_env(self):
        env = g.launcher_env({"HOME": "/h", "GIT_DIR": "x", "GH_REPO": "y", "GH_HOST": "z",
                              "GIT_EXTERNAL_DIFF": "e", "PYTHONPATH": "p", "PATH": "/evil"})
        for k in ("GIT_DIR", "GH_REPO", "GH_HOST", "GIT_EXTERNAL_DIFF", "PYTHONPATH"):
            self.assertNotIn(k, env)
        self.assertEqual((env["HOME"], env["GIT_CONFIG_NOSYSTEM"], env["GIT_CONFIG_COUNT"]), ("/h", "1", "4"))
        pairs = {env[f"GIT_CONFIG_KEY_{i}"]: env[f"GIT_CONFIG_VALUE_{i}"] for i in range(4)}
        self.assertEqual(pairs, {"core.fsmonitor": "false", "log.showSignature": "false",
                                 "gpg.program": "/bin/false", "core.hooksPath": "/dev/null"})
        self.assertNotIn("evil", env["PATH"])


class AgentTypes(unittest.TestCase):
    def test_agent_tables(self):
        prog = "/repo/scripts/lab-run.sh"
        tables = {"main": g.DEFAULT_MAIN, "programs": [prog],
                  "lab-operator": [{"argv": [prog], "flags": {}, "args": ["name?"], "required": []}]}
        self.assertFalse(g.decide("at sup status", "other", tables)[0])  # no table
        self.assertFalse(g.decide("at sup status", "lab-operator", tables)[0])
        self.assertTrue(g.decide(prog + " job-1", "lab-operator", tables)[0])
        self.assertFalse(g.decide("/repo/scripts/other.sh", "lab-operator", tables)[0])
        self.assertFalse(g.decide(prog, "other", tables)[0])
        for reserved in ("main", "programs", "tools"):
            self.assertFalse(g.decide("at sup status", reserved, tables)[0], reserved)


class EndToEnd(unittest.TestCase):
    def run_hook(self, stdin, **env):
        with tempfile.TemporaryDirectory() as d:
            e = {**os.environ, "AGENTS_SUP_DIR": d, **env}
            e.pop("AGENTS_SUP_CHAT_TOKEN", None)
            p = subprocess.run(["/bin/bash", HOOK], input=stdin, capture_output=True, text=True, env=e)
            log = os.path.join(d, "_guard.log")
            text = ""
            if os.path.exists(log):
                with open(log) as f:
                    text = f.read()
            return p, text

    def call(self, cmd, **extra):
        return json.dumps({"session_id": "s1", "tool_name": "Bash", "tool_input": {"command": cmd}, **extra})

    def test_allow(self):
        p, log = self.run_hook(self.call("at sup status"))
        self.assertEqual((p.returncode, p.stdout, p.stderr), (0, "", ""))
        self.assertIn("\ts1\tmain\tallow\t", log)

    def test_deny(self):
        p, log = self.run_hook(self.call("at sup status; rm x"))
        self.assertEqual(p.returncode, 2)
        self.assertEqual(len(p.stderr.strip().splitlines()), 1)
        self.assertIn("\tdeny\t", log)

    def test_non_bash_allowed(self):
        p, _ = self.run_hook(json.dumps({"tool_name": "Agent", "tool_input": {}}))
        self.assertEqual(p.returncode, 0)

    def test_malformed_input_denied(self):
        for stdin in ("not json", "", "[]", "{}", json.dumps({"tool_name": "Bash"}),
                      json.dumps({"tool_name": "Bash", "tool_input": {"command": 5}}),
                      self.call("at sup status", agent_type="")):
            p, _ = self.run_hook(stdin)
            self.assertEqual(p.returncode, 2, stdin)

    def test_agent_type_without_table(self):
        p, _ = self.run_hook(self.call("at sup status", agent_type="lab-operator"))
        self.assertEqual(p.returncode, 2)

    def test_tables_file(self):
        with tempfile.TemporaryDirectory() as d:
            ok = os.path.join(d, "t.json")
            with open(ok, "w") as f:
                json.dump({"programs": ["/x/run.sh"],
                           "lab-operator": [{"argv": ["/x/run.sh"], "args": ["name"]}]}, f)
            os.chmod(ok, 0o600)
            p, _ = self.run_hook(self.call("/x/run.sh job", agent_type="lab-operator"),
                                 AGENTS_SUP_GUARD_TABLES=ok)
            self.assertEqual(p.returncode, 0)
            p, _ = self.run_hook(self.call("at sup status"), AGENTS_SUP_GUARD_TABLES=ok)
            self.assertEqual(p.returncode, 0)
            bad = os.path.join(d, "bad.json")
            with open(bad, "w") as f:
                f.write("{nope")
            for path in (bad, os.path.join(d, "missing.json")):
                p, _ = self.run_hook(self.call("at sup status"), AGENTS_SUP_GUARD_TABLES=path)
                self.assertEqual(p.returncode, 2)

    def test_tool_allowlist(self):
        for tool in ("Read", "Agent", "AskUserQuestion"):
            p, _ = self.run_hook(json.dumps({"tool_name": tool, "tool_input": {}}))
            self.assertEqual(p.returncode, 0, tool)
        for tool in ("Write", "Edit", "WebFetch", "mcp__x__y", "Skill"):
            for agent in ({}, {"agent_type": "lab-operator"}):
                p, _ = self.run_hook(json.dumps({"tool_name": tool, "tool_input": {}, **agent}))
                self.assertEqual(p.returncode, 2, tool)

    def test_reserved_agent_types(self):
        for agent in ("main", "programs", "tools"):
            p, _ = self.run_hook(self.call("at sup status", agent_type=agent))
            self.assertEqual(p.returncode, 2, agent)

    def test_wrapper_fails_closed(self):
        p, _ = self.run_hook("{}", PATH="/nonexistent")  # python3 not found: rc 127 becomes 2
        self.assertEqual(p.returncode, 2)

    def test_deny_with_stderr_closed(self):
        with tempfile.TemporaryDirectory() as d:
            e = {**os.environ, "AGENTS_SUP_DIR": d}
            p = subprocess.run(["bash", HOOK], input=self.call("rm -rf x"), text=True, env=e,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               preexec_fn=lambda: os.close(2))
            self.assertEqual(p.returncode, 2)

    def test_tables_file_validation(self):
        with tempfile.TemporaryDirectory() as d:
            def table(name, obj, mode=0o600):
                path = os.path.join(d, name)
                with open(path, "w") as f:
                    json.dump(obj, f)
                os.chmod(path, mode)
                return path
            cases = {
                "writable": table("w.json", {}, 0o666),
                "relprog": table("r.json", {"programs": ["run.sh"]}),
                "interp": table("i.json", {"lab": [{"argv": ["bash"], "args": ["any+"]}]}),
                "interp2": table("i2.json", {"programs": ["/usr/bin/python3"],
                                             "lab": [{"argv": ["/usr/bin/python3"]}]}),
                "badclass": table("c.json", {"lab": [{"argv": ["x"], "args": ["bogus"]}]}),
            }
            for name, path in cases.items():
                p, _ = self.run_hook(self.call("at sup status"), AGENTS_SUP_GUARD_TABLES=path)
                self.assertEqual(p.returncode, 2, name)
            tools = table("t.json", {"tools": ["Bash"]})
            p, _ = self.run_hook(json.dumps({"tool_name": "Read", "tool_input": {}}), AGENTS_SUP_GUARD_TABLES=tools)
            self.assertEqual(p.returncode, 2)

    def test_log_sanitized_and_private(self):
        with tempfile.TemporaryDirectory() as d:
            e = {**os.environ, "AGENTS_SUP_DIR": d}
            stdin = json.dumps({"session_id": "s\tx\ny", "tool_name": "Bash",
                                "tool_input": {"command": "at sup status\tq\x1b[2J"}})
            subprocess.run(["bash", HOOK], input=stdin, text=True, env=e, capture_output=True)
            path = os.path.join(d, "_guard.log")
            with open(path) as f:
                lines = f.read().splitlines()
            self.assertEqual((len(lines), len(lines[0].split("\t"))), (1, 6))
            self.assertNotIn("\x1b", lines[0])
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)

    def test_log_failure_keeps_decision(self):
        p, _ = self.run_hook(self.call("at sup status"), AGENTS_SUP_DIR="/proc/nope/x")
        self.assertEqual(p.returncode, 0)


if __name__ == "__main__":
    unittest.main()
