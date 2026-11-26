#!/usr/bin/env python3
"""Tests for plugins/agents-core/lib/sup_tick.py: init, tick, chat, board, and the agent templates."""
import argparse, json, os, re, stat, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "plugins/agents-core/lib"))
import sup_state as st
import sup_tick as tk

ASSETS = ROOT / "plugins/agents-tasks/skills/supervise/assets"
FAKE = """#!/usr/bin/env python3
import json, os, sys, time
with open(os.environ["FAKE_LOG"], "a") as f:
    f.write(json.dumps({"argv": sys.argv[1:], "env": {k: v for k, v in os.environ.items() if k.startswith("AGENTS_")},
                        "cwd": os.getcwd()}) + "\\n")
time.sleep(float(os.environ.get("FAKE_SLEEP", "0")))
print(os.environ.get("FAKE_OUT", ""))
sys.exit(int(os.environ.get("FAKE_RC", "0")))
"""


def frontmatter(path):
    m = re.match(r"---\n(.*?)\n---\n", path.read_text(), re.S)
    out, key = {}, None
    for line in m.group(1).splitlines():
        if line.startswith("  - "):
            out[key].append(line[4:].strip())
        else:
            key, _, val = line.partition(":")
            out[key] = val.strip() or []
    return out


class Sup(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        t = Path(self.tmp.name); self.hub = t / "hub"; self.hub.mkdir(); self.log = t / "claude.log"
        fake = t / "claude"; fake.write_text(FAKE); fake.chmod(0o755)
        self.old = dict(os.environ); self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self.old)))
        os.environ.update(AGENTS_SUP_DIR=str(t / "sup"), AGENTS_LEASE_DIR=str(t / "lease"), AGENTS_CLAUDE_BIN=str(fake),
                          FAKE_LOG=str(self.log), AGENTS_SUP_TICK_TIMEOUT="20")
        for k in ("AGENTS_SUPERVISOR", "FAKE_OUT", "FAKE_RC", "FAKE_SLEEP", "CLAUDE_CODE_SESSION_ID", "AGENTS_SUP_CHAT_TOKEN",
                  "AGENTS_SUP_GUARD_TABLES"):
            os.environ.pop(k, None)
        spec = t / "p.json"
        spec.write_text(json.dumps({"repos": ["/r"], "resources": [{"name": "lab", "minutes": 60, "auto": False},
                                                                   {"name": "full-suite", "minutes": 30, "auto": True}],
                                    "cap": 2, "land": "manual", "operators": ["/hub/scripts/scan.sh"]}))
        self.spec = str(spec)

    def run_cmd(self, *argv):
        p = argparse.ArgumentParser(); sub = p.add_subparsers(); tk.register(sub)
        a = p.parse_args(list(argv)); return a.func(a)

    def init(self, *extra):
        return self.run_cmd("init", "--profile", "rm", "--hub", str(self.hub), "--from", self.spec, *extra)

    def calls(self):
        return [json.loads(x) for x in self.log.read_text().splitlines()] if self.log.exists() else []

    def result(self, text, rc=0):
        os.environ["FAKE_OUT"] = json.dumps({"result": text, "total_cost_usd": 0.02, "session_id": "s"})
        os.environ["FAKE_RC"] = str(rc)

    def test_init_writes_every_file_copies_config_and_refuses_a_second_run(self):
        self.assertEqual(self.init(), 0)
        d = self.hub / ".claude"
        for f in ("agents/rm-supervisor.md", "agents/rm-adviser.md", "agents/rm-operator.md", "supervisor/rm.json",
                  "supervisor/rm.settings.json", "supervisor/rm.tables.json"):
            self.assertTrue((d / f).is_file(), f)
        hook = json.loads((d / "supervisor/rm.settings.json").read_text())["hooks"]["PreToolUse"][0]
        self.assertEqual(hook["matcher"], "*"); self.assertTrue(Path(hook["hooks"][0]["command"]).is_absolute())
        self.assertTrue(hook["hooks"][0]["command"].endswith("hooks/sup-guard.sh"))
        tables = json.loads((d / "supervisor/rm.tables.json").read_text())
        self.assertEqual(tables["programs"], ["/hub/scripts/scan.sh"]); self.assertNotIn("main", tables)
        self.assertEqual(tables["rm-adviser"], [])
        self.assertEqual(stat.S_IMODE((d / "supervisor/rm.tables.json").stat().st_mode), 0o600)
        self.assertIn("/hub/scripts/scan.sh", (d / "agents/rm-operator.md").read_text())
        self.assertNotIn("{{", (d / "agents/rm-supervisor.md").read_text())
        cfg = st.config("rm"); self.assertEqual((cfg["cap"], cfg["land"], cfg["auto"]), (2, "manual", ["full-suite"]))
        self.assertEqual(cfg["hub"], str(self.hub.resolve()))
        self.assertEqual(self.init(), 3); self.assertEqual(self.init("--force"), 0)

    def test_the_tables_init_wrote_load_in_the_guard_and_decide_per_table(self):
        import sup_guard as g
        self.init(); os.environ["AGENTS_SUP_GUARD_TABLES"] = str(self.hub / ".claude/supervisor/rm.tables.json")
        t = g.load_tables(); script = "/hub/scripts/scan.sh"
        self.assertIs(t["main"], g.DEFAULT_MAIN)
        allowed = lambda cmd, agent: g.decide(cmd, agent, t)[0]  # noqa: E731
        self.assertTrue(allowed("at sup status", None)); self.assertFalse(allowed("at sup tick", None))
        self.assertFalse(allowed("at sup init", None)); self.assertFalse(allowed("at sup watch once", None))
        self.assertFalse(allowed("at sup ask 'why'", None)); self.assertFalse(allowed(script, None))
        self.assertTrue(allowed(f"{script} lab 5", "rm-operator")); self.assertTrue(allowed("at lease list", "rm-operator"))
        self.assertFalse(allowed("/hub/scripts/other.sh", "rm-operator")); self.assertFalse(allowed("at sup status", "rm-operator"))
        self.assertFalse(allowed("at lease list", "rm-adviser")); self.assertFalse(allowed("at lease list", "rm-nobody"))

    def test_init_and_chat_only_commands_are_refused_inside_a_claude_session_without_a_token(self):
        os.environ["CLAUDE_CODE_SESSION_ID"] = "worker-1"
        self.assertEqual(self.init(), 3); self.assertFalse((self.hub / ".claude").exists())

    def test_tick_skips_no_judgement_events_without_a_session(self):
        self.init(); st.emit("rm", "started", "RM-1"); st.emit("rm", "landed", "RM-1")
        self.assertEqual(self.run_cmd("tick", "--profile", "rm"), 0)
        self.assertEqual(st.cursor("rm"), 2); self.assertEqual(self.calls(), [])

    def test_tick_runs_a_session_and_advances_only_on_tick_done(self):
        self.init(); st.emit("rm", "need", "RM-1", resource="lab", minutes=30); st.emit("rm", "started", "RM-2")
        self.result("handled it\nTICK done: 1 handled, 0 left for the owner")
        self.assertEqual(self.run_cmd("tick", "--profile", "rm"), 0)
        self.assertEqual(st.cursor("rm"), 2)
        c = self.calls()[0]; argv = c["argv"]
        self.assertEqual(argv[argv.index("--agent") + 1], "rm-supervisor")
        self.assertEqual(argv[argv.index("--settings") + 1], str(self.hub / ".claude/supervisor/rm.settings.json"))
        self.assertIn("bypassPermissions", argv); self.assertEqual(Path(c["cwd"]).resolve(), self.hub.resolve())
        unhandled = argv[-1].split("Unhandled events:")[1]
        self.assertIn("resource=lab", unhandled); self.assertNotIn("started", unhandled); self.assertIn("TICK done:", argv[-1])
        self.assertIn("rm", c["env"]["AGENTS_SUPERVISOR"]); self.assertTrue(c["env"]["AGENTS_SUP_GUARD_TABLES"].endswith("rm.tables.json"))
        row = json.loads((st.profile_dir("rm") / "ticks.jsonl").read_text().splitlines()[-1])
        self.assertEqual((row["ok"], row["cost"], row["events"]), (True, 0.02, 1))

    def test_tick_leaves_the_cursor_on_a_missing_marker_a_failure_and_a_timeout(self):
        self.init(); st.emit("rm", "dead", "RM-1")
        self.result("I did things")
        self.assertEqual(self.run_cmd("tick", "--profile", "rm"), 3); self.assertEqual(st.cursor("rm"), 0)
        self.result("TICK done: 1 handled, 0 left for the owner", rc=1)
        self.assertEqual(self.run_cmd("tick", "--profile", "rm"), 3); self.assertEqual(st.cursor("rm"), 0)
        self.result("TICK done: 1 handled, 0 left for the owner")
        os.environ.update(FAKE_SLEEP="5", AGENTS_SUP_TICK_TIMEOUT="0.5")
        self.assertEqual(self.run_cmd("tick", "--profile", "rm"), 3); self.assertEqual(st.cursor("rm"), 0)
        self.assertFalse((st.profile_dir("rm") / "tick.pid").exists())
        rows = [json.loads(x) for x in (st.profile_dir("rm") / "ticks.jsonl").read_text().splitlines()]
        self.assertEqual([r["ok"] for r in rows], [False, False, False])

    def test_a_second_tick_is_refused_while_one_is_alive(self):
        self.init(); st.emit("rm", "dead", "RM-1")
        (st.profile_dir("rm") / "tick.pid").write_text(f"{os.getpid()}\n")
        self.assertEqual(self.run_cmd("tick", "--profile", "rm"), 3); self.assertEqual(self.calls(), [])
        (st.profile_dir("rm") / "tick.pid").write_text("999999999\n"); self.result("TICK done: 1 handled, 0 left for the owner")
        self.assertEqual(self.run_cmd("tick", "--profile", "rm"), 0)

    def test_chat_print_command_shows_token_and_argv_and_the_token_file_is_private(self):
        self.init()
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(self.run_cmd("chat", "--profile", "rm", "--print-command"), 0)
        out = json.loads(buf.getvalue()); tok = out["env"]["AGENTS_SUP_CHAT_TOKEN"]
        self.assertEqual(out["env"]["AGENTS_SUPERVISOR"], "rm"); self.assertTrue(out["env"]["AGENTS_SUP_GUARD_TABLES"].endswith("rm.tables.json"))
        a = out["argv"]; self.assertEqual(a[a.index("--agent") + 1], "rm-supervisor"); self.assertIn("--settings", a)
        f = st.root() / "_tokens" / tok
        self.assertEqual(stat.S_IMODE(f.stat().st_mode), 0o600)
        rec = json.loads(f.read_text()); self.assertGreater(rec["expires"], 0)
        self.assertEqual(a[a.index("--session-id") + 1], rec["session_id"]); self.assertEqual(stat.S_IMODE(f.parent.stat().st_mode), 0o700)
        import sup_guard
        os.environ["AGENTS_SUP_CHAT_TOKEN"] = tok
        self.assertTrue(sup_guard.check_chat_token(rec["session_id"])); self.assertFalse(sup_guard.check_chat_token("other"))
        self.assertEqual(self.calls(), [])

    def test_board_writes_digest_and_the_whole_queue(self):
        self.init(); st.queue_add("rm", "RM-1", "Use A or B?", ["A", "B"], "A")
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(self.run_cmd("board", "--profile", "rm"), 0)
        text = Path(buf.getvalue().strip()).read_text(); self.assertIn("Use A or B?", text); self.assertIn("recommendation: A", text)

    def test_templates_parse_and_the_supervisor_cannot_edit(self):
        want = {"supervisor": {"Bash", "Agent", "AskUserQuestion", "Read", "Glob", "Grep"}, "adviser": {"Read", "Glob", "Grep"},
                "operator": {"Bash", "Read"}}
        for role, tools in want.items():
            fm = frontmatter(ASSETS / f"{role}.md")
            self.assertEqual(set(fm["tools"]), tools, role); self.assertEqual(fm["name"], "{{profile}}-" + role)
        self.assertLess(len((ASSETS / "supervisor.md").read_text().splitlines()), 80)
        self.assertTrue(set(json.loads((ASSETS / "profile.json").read_text())) >= {"repos", "resources", "cap", "land", "operators"})


if __name__ == "__main__":
    unittest.main()
