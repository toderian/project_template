#!/usr/bin/env python3
"""Tests for plugins/agents-core/lib/sup_workers.py with a fake `claude` and a fake `at`."""
import argparse, io, json, os, subprocess, sys, tempfile, time, unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "plugins/agents-core/lib"))
import sup_state as st
import sup_workers as sw

FAKE_CLAUDE = """#!/usr/bin/env python3
import json, os, sys
d = os.environ["FAKE_DIR"]
a = sys.argv[1:]
with open(d + "/claude.log", "a") as f:
    f.write(json.dumps({"argv": a, "cwd": os.getcwd(), "sup": os.environ.get("AGENTS_SUPERVISOR"), "task": os.environ.get("AGENTS_SUP_TASK"),
                        "path": os.environ.get("PATH"), "gitcfg": sorted(k for k in os.environ if k.startswith("GIT_CONFIG"))}) + "\\n")
def has(n): return os.path.exists(d + "/" + n)
def lines(n): return open(d + "/" + n).read().split() if has(n) else []
if "--resume" in a:
    sid = a[a.index("--resume") + 1]
    if has("resume.copy"): print("started a copy as e8ad3784")
    else:
        print("woke session " + sid[:8] + " with its saved options")
        open(d + "/stopped", "w").write(" ".join(x for x in lines("stopped") if x != sid[:8]))
    sys.exit(int(os.environ.get("FAKE_RESUME_RC", "0")))
if a[0] == "--bg":
    if has("bg.fail"):
        sys.stderr.write("Workspace not trusted\\n"); sys.exit(1)
    sid = a[a.index("--session-id") + 1]
    open(d + "/sessions", "a").write(sid + "\\n")
    print("backgrounded \\u00b7 " + sid[:8] + " \\u00b7 " + a[a.index("--name") + 1])
elif a[0] == "agents":
    if has("agents.fail"): sys.exit(1)
    left = int(open(d + "/agents.skip").read()) if has("agents.skip") else 0
    if left > 0:
        open(d + "/agents.skip", "w").write(str(left - 1)); print("[]"); sys.exit(0)
    print(json.dumps([{"sessionId": s, "name": "x", "pid": None if s[:8] in lines("stopped") or s in lines("dead") else 77} for s in lines("sessions")]))
elif a[0] == "stop":
    if has("stop.fail"): sys.exit(1)
    open(d + "/stopped", "a").write(a[1] + " ")
elif a[0] == "-p":
    print("{}")
"""
FAKE_AT = """#!/usr/bin/env python3
import os, sys
a = sys.argv[1:]
open(os.environ["FAKE_DIR"] + "/at.log", "a").write(" ".join(a) + "\\n")
if a[:2] == ["sup", "ready"]:
    if os.environ.get("FAKE_READY_RC", "0") != "0":
        print("phase 1 has no Files: fence"); sys.exit(1)
elif a[:2] == ["sup", "worktree"]:
    print("created worktree"); print(os.environ["FAKE_DIR"] + "/wt")
"""
SID = "abcd1234-0000-4000-8000-00000000000%d"


def git(path, *a):
    return subprocess.run(["git", "-C", str(path), *a], capture_output=True, text=True, check=True).stdout.strip()


class Workers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.old = dict(os.environ); self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self.old)))
        t = Path(self.tmp.name).resolve(); (t / "wt").mkdir()
        for name, body in (("claude", FAKE_CLAUDE), ("at", FAKE_AT)):
            (t / name).write_text(body); (t / name).chmod(0o755)
        os.environ.update(AGENTS_SUP_DIR=str(t / "sup"), AGENTS_CLAUDE_BIN=str(t / "claude"), AGENTS_AT_BIN=str(t / "at"),
                          FAKE_DIR=str(t))
        for k in ("FAKE_READY_RC", "FAKE_RESUME_RC", "CLAUDE_CODE_SESSION_ID", "AGENTS_SUP_CHAT_TOKEN", "AGENTS_SUP_TASK",
                  "AGENTS_SUP_ORIG_PATH"):
            os.environ.pop(k, None)
        self.t = t
        self.hub = t / "hub"; self.hub.mkdir()
        git(self.hub, "init", "-q", "-b", "main"); git(self.hub, "config", "user.name", "T"); git(self.hub, "config", "user.email", "t@x.invalid")
        git(self.hub, "commit", "-q", "--allow-empty", "-m", "base")
        st.set_config("p", hub=str(self.hub))
        sw.POLL_DELAY = 0
        self.addCleanup(lambda: setattr(sw, "POLL_DELAY", 0.5))
        top = argparse.ArgumentParser(); sub = top.add_subparsers(); sw.register(sub); self.top = top

    def cli(self, *argv, profile=True):
        args = self.top.parse_args(list(argv) + (["--profile", "p"] if profile else []))
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = args.func(args)
        return rc, out.getvalue(), err.getvalue()

    def log(self):
        p = self.t / "claude.log"
        return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []

    def at_log(self):
        p = self.t / "at.log"
        return p.read_text().splitlines() if p.exists() else []

    def running_pack(self, tasks=("RM-1", "RM-2", "RM-3"), parallel=False, name="a"):
        self.assertEqual(self.cli("pack", name, *tasks, *(["--parallel"] if parallel else []))[0], 0)
        self.assertEqual(self.cli("start-pack", name)[0], 0)

    def add_session(self, sid):
        with open(self.t / "sessions", "a") as f:
            f.write(sid + "\n")

    def live_row(self, n=1, task="RM-1", **kw):
        st.set_worker("p", SID % n, **{"task": task, "mode": "bg", "cwd": str(self.t / "wt"), "state": "running", **kw})
        self.add_session(SID % n)

    def test_start_worker_refusals_each_give_exit_3_and_one_reason(self):
        rc, _, err = self.cli("start-worker", "RM-1")
        self.assertEqual((rc, err.count("\n")), (3, 1)); self.assertIn("no pack", err)
        self.cli("pack", "a", "RM-1", "RM-2")
        rc, _, err = self.cli("start-worker", "RM-1"); self.assertEqual(rc, 3); self.assertIn("new, not running", err)
        self.cli("start-pack", "a")
        os.environ["FAKE_READY_RC"] = "1"
        rc, _, err = self.cli("start-worker", "RM-1"); self.assertEqual(rc, 3); self.assertIn("Files: fence", err)
        self.assertEqual(st.workers("p"), [])  # a refused start leaves no row
        os.environ.pop("FAKE_READY_RC")
        st.set_worker("p", SID % 9, task="RM-1", state="running")
        rc, _, err = self.cli("start-worker", "RM-1"); self.assertEqual(rc, 3); self.assertIn("live worker", err)
        self.cli("cap", "1")
        rc, _, err = self.cli("start-worker", "RM-2"); self.assertEqual(rc, 3); self.assertIn("cap 1", err)
        self.assertEqual(self.log(), [])

    def test_start_worker_registers_the_row_sets_the_environment_and_emits_started(self):
        self.running_pack()
        os.environ.update(GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="core.hooksPath", GIT_CONFIG_VALUE_0="/dev/null",
                          AGENTS_SUP_ORIG_PATH="/usr/bin:/bin", PATH="/restricted")
        rc, out, _ = self.cli("start-worker", "RM-1")
        row = st.worker_for("p", task="RM-1")
        self.assertEqual((rc, out), (0, f"started RM-1 {row['session']}\n"))
        self.assertRegex(row["session"], r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[0-9a-f]{4}-[0-9a-f]{12}$")
        bg = self.log()[0]
        self.assertEqual(bg["argv"][:7], ["--bg", "--session-id", row["session"], "--name", "p-RM-1", "--permission-mode", "auto"])
        self.assertEqual((bg["sup"], bg["task"], bg["cwd"]), ("p", "RM-1", os.path.realpath(self.t / "wt")))
        self.assertEqual((bg["gitcfg"], bg["path"]), ([], "/usr/bin:/bin"))  # finding security-10
        for text in ("WAITING supervisor", "profile p", "at sup inbox --ack", "at sup release", "--minutes"):
            self.assertIn(text, bg["argv"][-1])
        self.assertEqual((row["mode"], row["state"], row["pack"]), ("bg", "running", "a"))
        ev = st.events_since("p", 0)
        self.assertEqual([(e["kind"], e["session"]) for e in ev], [("started", row["session"])])

    def test_a_failed_start_leaves_no_row_and_the_retry_reuses_the_worktree(self):
        self.running_pack()
        git(self.hub, "worktree", "add", "-q", "-b", "task/RM-1", str(self.t / "hub-rm-1"))
        (self.t / "bg.fail").write_text("")
        rc, _, err = self.cli("start-worker", "RM-1")
        self.assertEqual(rc, 3); self.assertIn("Workspace not trusted", err)
        self.assertEqual((st.workers("p"), st.events_since("p", 0)), ([], []))
        (self.t / "bg.fail").unlink()
        self.assertEqual(self.cli("start-worker", "RM-1")[0], 0)
        self.assertEqual(st.worker_for("p", task="RM-1")["cwd"], str(self.t / "hub-rm-1"))
        self.assertFalse([l for l in self.at_log() if l.startswith("sup worktree")])

    def test_a_session_not_yet_in_agents_is_waited_for_and_one_that_never_shows_is_stopped(self):
        self.running_pack()
        (self.t / "agents.skip").write_text("2")
        self.assertEqual(self.cli("start-worker", "RM-1")[0], 0)  # two empty answers, then the session shows
        self.assertEqual(st.worker_for("p", task="RM-1")["state"], "running")
        st.drop_worker("p", st.worker_for("p", task="RM-1")["session"])
        (self.t / "agents.fail").write_text("")
        rc, _, err = self.cli("start-worker", "RM-1")
        self.assertEqual(rc, 3); self.assertIn("not in `claude agents`", err)
        self.assertEqual(st.workers("p"), [])
        self.assertEqual(self.log()[-1]["argv"][0], "stop")  # the orphan is stopped, not left running

    def test_a_starting_row_counts_against_the_cap_so_two_starts_cannot_both_pass(self):
        self.running_pack(("RM-1", "RM-2"), parallel=True); self.cli("cap", "1")
        st.set_worker("p", SID % 1, task="RM-1", state="starting")
        rc, _, err = self.cli("start-worker", "RM-2"); self.assertEqual(rc, 3); self.assertIn("cap 1", err)

    def test_headless_start_uses_claude_p_with_a_session_id_and_records_the_pid(self):
        self.running_pack()
        rc, out, _ = self.cli("start-worker", "RM-1", "--headless"); self.assertEqual(rc, 0)
        row = st.worker_for("p", task="RM-1")
        self.assertEqual(row["mode"], "headless"); self.assertRegex(row["session"], r"^[0-9a-f-]{36}$"); self.assertGreater(row["pid"], 0)
        self.assertTrue((st.profile_dir("p") / "logs").is_dir())
        for _ in range(100):
            if self.log(): break
            time.sleep(0.05)
        self.assertEqual(self.log()[0]["argv"][:6], ["-p", "--session-id", row["session"], "--permission-mode", "auto", "--output-format"])

    def test_stop_worker_marks_the_row_first_then_stops_the_short_id(self):
        self.running_pack(); self.cli("start-worker", "RM-1"); sid = st.worker_for("p", task="RM-1")["session"]
        rc, _, _ = self.cli("stop-worker", "RM-1"); self.assertEqual(rc, 0)
        self.assertEqual(self.log()[-1]["argv"], ["stop", sid[:8]])
        row = st.worker_for("p", task="RM-1"); self.assertEqual((row["state"], row["stopped_by"]), ("stopped", "owner"))
        self.assertEqual(self.cli("stop-worker", "RM-1")[0], 3)
        self.assertNotIn("sup:", (st.profile_dir("p") / "touch.log").read_text())

    def test_stop_worker_from_a_supervisor_session_is_not_the_owner_and_a_failed_stop_restores_the_row(self):
        self.live_row(1, state="waiting", waiting_for="lab")
        os.environ["CLAUDE_CODE_SESSION_ID"] = "some-supervisor-session"
        self.assertEqual(self.cli("stop-worker", "RM-1")[0], 0)
        row = st.worker_for("p", task="RM-1"); self.assertEqual((row["state"], row["stopped_by"]), ("stopped", "sup"))
        self.assertIn("\tsup: stop-worker RM-1", (st.profile_dir("p") / "touch.log").read_text())
        st.set_worker("p", SID % 1, state="waiting", waiting_for="lab", stopped_by=None)
        (self.t / "stop.fail").write_text("")
        self.assertEqual(self.cli("stop-worker", "RM-1")[0], 3)
        row = st.worker_for("p", task="RM-1"); self.assertEqual((row["state"], row["waiting_for"]), ("waiting", "lab"))

    def test_wake_stops_then_resumes_in_the_row_cwd_with_the_task_environment(self):
        self.live_row(1, state="waiting", waiting_for="lab", cwd=str(self.t / "wt"))
        os.environ["AGENTS_SUP_ORIG_PATH"] = "/usr/bin:/bin"; os.environ["AGENTS_SUP_CHAT_TOKEN"] = "x" * 32
        os.chdir("/")
        self.assertTrue(sw.wake("p", SID % 1, "go"))
        calls = self.log()
        self.assertEqual([c["argv"] for c in calls], [["stop", (SID % 1)[:8]], ["--bg", "--resume", SID % 1, "go"]])
        for c in calls:
            self.assertEqual((c["cwd"], c["sup"], c["task"], c["path"]), (str(self.t / "wt"), "p", "RM-1", "/usr/bin:/bin"))
        self.assertEqual(st.worker_for("p", task="RM-1")["state"], "waiting")  # the caller (the watcher) sets `running`
        os.environ["FAKE_RESUME_RC"] = "1"
        self.assertFalse(sw.wake("p", SID % 1, "go"))

    def test_wake_is_false_when_the_resume_started_a_copy_or_the_stop_failed_on_a_live_session(self):
        self.live_row(1, state="stopped")
        (self.t / "resume.copy").write_text("")
        self.assertFalse(sw.wake("p", SID % 1, "go"))
        (self.t / "resume.copy").unlink(); (self.t / "stop.fail").write_text(""); (self.t / "stopped").write_text("")
        self.assertFalse(sw.wake("p", SID % 1, "go"))  # stop failed and `agents` shows it running
        (self.t / "dead").write_text(SID % 1 + "\n")
        self.assertTrue(sw.wake("p", SID % 1, "go"))  # stop failed but the session is already stopped

    def test_wake_never_puts_a_bad_session_into_argv(self):
        st.set_worker("p", "--dangerously-skip-permissions", task="RM-3", mode="bg", state="stopped", cwd=str(self.t / "wt"))
        self.assertFalse(sw.wake("p", "--dangerously-skip-permissions", "go")); self.assertEqual(self.log(), [])
        self.live_row(1)
        self.assertEqual(self.cli("stop-worker", "RM-1")[0], 0)
        st.set_worker("p", "-bad", task="RM-2", state="running", mode="bg")
        before = len(self.log()); self.assertEqual(self.cli("stop-worker", "RM-2")[0], 3); self.assertEqual(len(self.log()), before)
        self.assertEqual(st.worker_for("p", task="RM-2")["state"], "running")

    def test_headless_wake_resumes_with_claude_p(self):
        st.set_worker("p", SID % 1, task="RM-1", mode="headless", state="waiting", cwd=str(self.t / "wt"), pid=999999999)
        self.assertTrue(sw.wake("p", SID % 1, "go"))
        for _ in range(100):
            if self.log(): break
            time.sleep(0.05)
        self.assertEqual(self.log()[0]["argv"], ["-p", "--resume", SID % 1, "go"])

    def test_is_alive_checks_the_agents_pid_and_a_failing_call_is_unknown(self):
        self.live_row(1); (self.t / "dead").write_text(SID % 2 + "\n"); self.add_session(SID % 2)
        self.assertTrue(sw.is_alive({"session": SID % 1, "mode": "bg"}))
        self.assertFalse(sw.is_alive({"session": SID % 2, "mode": "bg"}))
        self.assertFalse(sw.is_alive({"session": "nope", "mode": "bg"}))
        (self.t / "agents.fail").write_text("")
        self.assertIsNone(sw.agents()); self.assertIsNone(sw.is_alive({"session": SID % 1, "mode": "bg"}))
        self.assertTrue(sw.is_alive({"session": SID % 1, "mode": "headless", "pid": os.getpid()}))
        self.assertFalse(sw.is_alive({"session": SID % 1, "mode": "headless", "pid": 999999999}))
        self.assertFalse(sw.is_alive({"session": SID % 1, "mode": "headless", "pid": 12345678901234567890}))  # no OverflowError
        self.assertTrue(sw.is_alive({"session": SID % 1, "mode": "headless", "pid": 999999999, "state": "waiting"}))

    def test_next_tasks_serial_moves_on_only_when_the_previous_task_is_landed(self):
        self.running_pack(("RM-1", "RM-2", "RM-3"), name="s")
        self.assertEqual(sw.next_tasks("p"), ["RM-1"])
        st.set_worker("p", SID % 1, task="RM-1", state="running")
        self.assertEqual(sw.next_tasks("p"), [])
        st.set_worker("p", SID % 1, state="done")
        self.assertEqual(sw.next_tasks("p"), [])  # done is not landed (finding 10)
        st.emit("p", "landed", task="RM-1")
        self.assertEqual(sw.next_tasks("p"), ["RM-2"])
        st.set_worker("p", SID % 2, task="RM-2", state="stopped")
        self.assertEqual(sw.next_tasks("p"), [])
        self.cli("pause-pack", "s")
        self.assertEqual(sw.next_tasks("p"), [])

    def test_next_tasks_parallel_gives_all_under_the_cap_and_a_row_due_for_a_wake_holds_a_slot(self):
        self.running_pack(("RM-7", "RM-8", "RM-9", "RM-10"), parallel=True, name="q")
        self.assertEqual(sw.next_tasks("p"), ["RM-7", "RM-8", "RM-9"])
        st.set_worker("p", SID % 1, task="RM-7", state="running")
        self.assertEqual(sw.next_tasks("p"), ["RM-8", "RM-9"])
        self.cli("cap", "2")
        self.assertEqual(sw.next_tasks("p"), ["RM-8"])
        st.set_worker("p", SID % 1, state="stopped"); st.set_worker("p", SID % 2, task="RM-8", state="running")
        st.inbox_add("p", "RM-7", "go")
        self.assertEqual(sw.next_tasks("p"), [])  # RM-7 is stopped with an answer: its slot is kept for the wake
        st.inbox_ack("p", "RM-7", "A1")
        self.assertEqual(sw.next_tasks("p"), ["RM-9"])

    def test_wake_due_skips_owner_stops_paused_packs_acked_entries_and_exhausted_causes(self):
        self.running_pack(("RM-1",), name="q")
        row = lambda **kw: {"session": SID % 1, "task": "RM-1", "state": "stopped", **kw}
        self.assertIsNone(sw.wake_due("p", row()))
        st.inbox_add("p", "RM-1", "go")
        self.assertEqual(sw.wake_due("p", row())[0], "Read your answers with: at sup inbox --task RM-1")
        self.assertIsNone(sw.wake_due("p", row(stopped_by="owner")))
        self.assertIsNone(sw.wake_due("p", row(wake_fail=3, wake_key="A1")))
        self.assertIsNotNone(sw.wake_due("p", row(wake_fail=3, wake_key="A0")))  # a new inbox entry is a new cause
        self.assertEqual(sw.wake_due("p", row(state="running")), None)
        self.cli("pause-pack", "q"); self.assertIsNone(sw.wake_due("p", row()))
        self.cli("start-pack", "q"); st.inbox_ack("p", "RM-1", "A1"); self.assertIsNone(sw.wake_due("p", row()))
        self.assertTrue(sw.wake_due("p", row(restart_pending=True))[0].startswith("Continue the task."))

    def test_every_command_but_packs_refuses_in_a_worker_session(self):
        os.environ["AGENTS_SUP_TASK"] = "RM-1"
        for argv in (("pack", "a", "RM-1"), ("cap", "2"), ("start-worker", "RM-1"), ("stop-worker", "RM-1")):
            rc, _, err = self.cli(*argv); self.assertEqual(rc, 3, argv); self.assertIn("not for a worker", err)
        self.assertEqual(self.cli("packs")[0], 0)

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
        st.set_worker("p", SID % 3, task="RM-1", state="running")
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
        with self.assertRaises(SystemExit) as c, redirect_stderr(io.StringIO()):
            self.cli("packs", profile=False)
        self.assertEqual(c.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
