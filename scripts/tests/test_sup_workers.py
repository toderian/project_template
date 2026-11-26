#!/usr/bin/env python3
"""Tests for plugins/agents-core/lib/sup_workers.py with a fake `claude` and a fake `at`."""
import argparse, io, json, os, sys, tempfile, unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "plugins/agents-core/lib"))
import sup_state as st
import sup_workers as sw

FAKE_CLAUDE = """#!/usr/bin/env python3
import json, os, sys
d = os.environ["FAKE_DIR"]
with open(d + "/claude.log", "a") as f:
    f.write(json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd(), "sup": os.environ.get("AGENTS_SUPERVISOR"),
                        "task": os.environ.get("AGENTS_SUP_TASK")}) + "\\n")
a = sys.argv[1:]
if a[0] == "--bg" and "--resume" not in a:
    name = a[a.index("--name") + 1]
    print("backgrounded \\u00b7 abcd1234 \\u00b7 " + name)
elif a[0] == "agents":
    name = open(d + "/agents.name").read().strip() if os.path.exists(d + "/agents.name") else ""
    print(json.dumps([{"sessionId": "abcd1234-full", "name": name, "pid": 77}, {"sessionId": "dead0000-x", "name": "z", "pid": None}]))
elif a[0] == "-p":
    print("{}")
sys.exit(int(os.environ.get("FAKE_RESUME_RC", "0")) if "--resume" in a else 0)
"""
FAKE_AT = """#!/usr/bin/env python3
import os, sys
a = sys.argv[1:]
if a[:2] == ["sup", "ready"]:
    if os.environ.get("FAKE_READY_RC", "0") != "0":
        print("phase 1 has no Files: fence"); sys.exit(1)
elif a[:2] == ["sup", "worktree"]:
    print("created worktree"); print(os.environ["FAKE_DIR"] + "/wt")
"""


class Workers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.old = dict(os.environ); self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self.old)))
        t = Path(self.tmp.name); (t / "wt").mkdir()
        for name, body in (("claude", FAKE_CLAUDE), ("at", FAKE_AT)):
            (t / name).write_text(body); (t / name).chmod(0o755)
        os.environ.update(AGENTS_SUP_DIR=str(t / "sup"), AGENTS_CLAUDE_BIN=str(t / "claude"), AGENTS_AT_BIN=str(t / "at"),
                          FAKE_DIR=str(t), AGENTS_SUPERVISOR="p")
        for k in ("FAKE_READY_RC", "FAKE_RESUME_RC", "CLAUDE_CODE_SESSION_ID", "AGENTS_SUP_CHAT_TOKEN"):
            os.environ.pop(k, None)
        (t / "agents.name").write_text("p-RM-1")
        self.t = t
        top = argparse.ArgumentParser(); sub = top.add_subparsers(); sw.register(sub); self.top = top

    def cli(self, *argv):
        args = self.top.parse_args(list(argv))
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = args.func(args)
        return rc, out.getvalue(), err.getvalue()

    def log(self):
        p = self.t / "claude.log"
        return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []

    def running_pack(self, tasks=("RM-1", "RM-2", "RM-3"), parallel=False, name="a"):
        self.assertEqual(self.cli("pack", name, *tasks, *(["--parallel"] if parallel else []))[0], 0)
        self.assertEqual(self.cli("start-pack", name)[0], 0)

    def test_start_worker_refusals_each_give_exit_3_and_one_reason(self):
        rc, _, err = self.cli("start-worker", "RM-1")
        self.assertEqual((rc, err.count("\n")), (3, 1)); self.assertIn("no pack", err)
        self.cli("pack", "a", "RM-1", "RM-2")
        rc, _, err = self.cli("start-worker", "RM-1"); self.assertEqual(rc, 3); self.assertIn("new, not running", err)
        self.cli("start-pack", "a")
        os.environ["FAKE_READY_RC"] = "1"
        rc, _, err = self.cli("start-worker", "RM-1"); self.assertEqual(rc, 3); self.assertIn("Files: fence", err)
        os.environ.pop("FAKE_READY_RC")
        st.set_worker("p", "s-live", task="RM-1", state="running")
        rc, _, err = self.cli("start-worker", "RM-1"); self.assertEqual(rc, 3); self.assertIn("live worker", err)
        self.cli("cap", "1")
        rc, _, err = self.cli("start-worker", "RM-2"); self.assertEqual(rc, 3); self.assertIn("cap 1", err)
        self.assertEqual(self.log(), [])

    def test_start_worker_registers_the_row_sets_the_environment_and_emits_started(self):
        self.running_pack()
        rc, out, _ = self.cli("start-worker", "RM-1")
        self.assertEqual((rc, out), (0, "started RM-1 abcd1234-full\n"))
        bg = self.log()[0]
        self.assertEqual(bg["argv"][:5], ["--bg", "--name", "p-RM-1", "--permission-mode", "auto"])
        self.assertEqual((bg["sup"], bg["task"], bg["cwd"]), ("p", "RM-1", os.path.realpath(self.t / "wt")))
        self.assertIn("WAITING supervisor", bg["argv"][-1]); self.assertIn("profile p", bg["argv"][-1])
        row = st.worker_for("p", task="RM-1")
        self.assertEqual((row["session"], row["mode"], row["state"], row["pack"]), ("abcd1234-full", "bg", "running", "a"))
        self.assertEqual([e["kind"] for e in st.events_since("p", 0)], ["started"])

    def test_headless_start_uses_claude_p_and_a_pid_session(self):
        self.running_pack()
        rc, out, _ = self.cli("start-worker", "RM-1", "--headless"); self.assertEqual(rc, 0)
        row = st.worker_for("p", task="RM-1")
        self.assertEqual(row["mode"], "headless"); self.assertRegex(row["session"], r"^headless-\d+$")
        self.assertTrue((st.profile_dir("p") / "logs").is_dir())
        for _ in range(100):
            if self.log(): break
            import time; time.sleep(0.05)
        self.assertEqual(self.log()[0]["argv"][:5], ["-p", "--permission-mode", "auto", "--output-format", "json"])

    def test_stop_worker_stops_the_short_id_and_marks_the_row(self):
        self.running_pack(); self.cli("start-worker", "RM-1")
        rc, _, _ = self.cli("stop-worker", "RM-1"); self.assertEqual(rc, 0)
        self.assertEqual(self.log()[-1]["argv"], ["stop", "abcd1234"])
        self.assertEqual(st.worker_for("p", task="RM-1")["state"], "stopped")
        self.assertEqual(self.cli("stop-worker", "RM-1")[0], 3)

    def test_wake_stops_before_it_resumes_and_reports_the_exit_code(self):
        st.set_worker("p", "abcd1234-full", task="RM-1", mode="bg", state="waiting", waiting_for="lab")
        self.assertTrue(sw.wake("p", "abcd1234-full", "go"))
        argvs = [e["argv"] for e in self.log()]
        self.assertEqual(argvs, [["stop", "abcd1234"], ["--bg", "--resume", "abcd1234-full", "go"]])
        self.assertEqual(st.worker_for("p", task="RM-1")["state"], "waiting")  # the caller (the watcher) sets `running`
        os.environ["FAKE_RESUME_RC"] = "1"
        self.assertFalse(sw.wake("p", "abcd1234-full", "go"))
        self.assertEqual(st.worker_for("p", task="RM-1")["state"], "waiting")

    def test_is_alive_checks_the_agents_pid_and_the_headless_pid(self):
        self.assertTrue(sw.is_alive({"session": "abcd1234-full", "mode": "bg"}))
        self.assertFalse(sw.is_alive({"session": "dead0000-x", "mode": "bg"}))
        self.assertFalse(sw.is_alive({"session": "nope", "mode": "bg"}))
        self.assertTrue(sw.is_alive({"session": f"headless-{os.getpid()}", "mode": "headless"}))
        self.assertFalse(sw.is_alive({"session": "headless-999999999", "mode": "headless"}))

    def test_next_tasks_serial_gives_one_in_order_and_parallel_gives_all_under_the_cap(self):
        self.running_pack(("RM-1", "RM-2", "RM-3"), name="s")
        self.assertEqual(sw.next_tasks("p"), ["RM-1"])
        st.set_worker("p", "w1", task="RM-1", state="running")
        self.assertEqual(sw.next_tasks("p"), [])
        st.set_worker("p", "w1", state="done"); st.emit("p", "landed", task="RM-1")
        self.assertEqual(sw.next_tasks("p"), ["RM-2"])
        st.set_worker("p", "w2", task="RM-2", state="stopped")
        self.assertEqual(sw.next_tasks("p"), [])
        self.cli("pause-pack", "s")
        self.assertEqual(sw.next_tasks("p"), [])
        self.running_pack(("RM-7", "RM-8", "RM-9", "RM-10"), parallel=True, name="q")
        self.cli("pause-pack", "s")
        self.assertEqual(sw.next_tasks("p"), ["RM-7", "RM-8", "RM-9"])
        st.set_worker("p", "w3", task="RM-7", state="running")
        self.assertEqual(sw.next_tasks("p"), ["RM-8", "RM-9"])
        self.cli("cap", "2")
        self.assertEqual(sw.next_tasks("p"), ["RM-8"])

    def test_pack_order_and_cap_validation_and_touch_log(self):
        self.assertEqual(self.cli("pack", "a", "RM-1", "bad")[0], 2)
        self.assertEqual(self.cli("pack", "a", "RM-1", "RM-1")[0], 2)
        self.assertEqual(self.cli("pack", "a", "RM-1", "RM-2", "RM-3")[0], 0)
        self.assertEqual(self.cli("pack", "b", "RM-3")[0], 3)
        self.assertEqual(self.cli("pack", "a", "RM-1", "RM-2")[0], 0)
        self.assertEqual(self.cli("order", "a", "RM-2", "RM-3")[0], 2)
        self.assertEqual(self.cli("order", "a", "RM-2", "RM-1")[0], 0)
        self.assertEqual(st.read_pack("p", "a")["tasks"], ["RM-2", "RM-1"])
        self.assertEqual(self.cli("order", "zz", "RM-1")[0], 3)
        self.cli("start-pack", "a")
        st.set_worker("p", "w", task="RM-1", state="running")
        self.assertEqual(self.cli("order", "a", "RM-2")[0], 0)
        self.assertEqual(st.read_pack("p", "a")["tasks"], ["RM-1", "RM-2"])
        self.assertEqual(self.cli("pack", "a", "RM-1")[0], 3)
        self.assertEqual(self.cli("close-pack", "a")[0], 3)
        for bad in (0, 9):
            self.assertEqual(self.cli("cap", str(bad))[0], 2)
        self.assertEqual(self.cli("cap", "8")[0], 0); self.assertEqual(st.config("p")["cap"], 8)
        log = (st.profile_dir("p") / "touch.log").read_text()
        for what in ("pack a", "start-pack a", "order a", "cap 8"):
            self.assertIn(what, log)
        self.assertNotIn("cap 9", log)
        out = self.cli("packs")[1]; self.assertIn("a running serial RM-1 RM-2", out)

    def test_no_profile_is_a_usage_error(self):
        os.environ.pop("AGENTS_SUPERVISOR")
        with self.assertRaises(SystemExit) as c, redirect_stderr(io.StringIO()):
            self.cli("packs")
        self.assertEqual(c.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
