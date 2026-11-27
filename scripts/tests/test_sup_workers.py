#!/usr/bin/env python3
"""Tests for plugins/agents-core/lib/sup_workers.py with a fake `claude` and a fake `at`."""
import argparse, io, json, os, shutil, subprocess, sys, tempfile, time, unittest
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
if has("hold") and a[0] == "-p":
    import time; time.sleep(float(open(d + "/hold").read()))
if "--resume" in a:
    sid = a[a.index("--resume") + 1]
    if has("resume.copy"): print("started a copy as e8ad3784")
    else:
        print("woke session " + sid[:8] + " with its saved options")
        open(d + "/stopped", "w").write(" ".join(x for x in lines("stopped") if x != sid[:8]))
    sys.exit(int(os.environ.get("FAKE_RESUME_RC", "0")))
if a[0] == "--bg":
    if has("bg.fail"):
        sys.stderr.write((open(d + "/bg.fail").read().strip() or "Workspace not trusted") + "\\n"); sys.exit(1)
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
                          AGENTS_SUP_ORIG_PATH="/usr/bin:/bin", PATH="/restricted:" + os.path.dirname(shutil.which("git")))  # git stays reachable for the landed check
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
        pid = sw.wake("p", SID % 1, "go")
        self.assertGreater(pid, 1)  # the Popen pid, for the row
        for _ in range(100):
            if self.log(): break
            time.sleep(0.05)
        self.assertEqual(self.log()[0]["argv"], ["-p", "--resume", SID % 1, "--permission-mode", "auto", "--output-format", "json", "go"])
        self.assertEqual(sw.wake("p", SID % 1, "go2") > 1, True)
        time.sleep(0.3)  # each wake has its own log file, so each stays JSON
        logs = sorted(p.name for p in (st.profile_dir("p") / "logs").iterdir())
        self.assertEqual(logs, ["RM-1.wake-1.json", "RM-1.wake-2.json"])

    def test_a_headless_start_follows_worker_mode_and_the_prompt_says_arm_and_never_disarm(self):
        self.running_pack(); st.set_config("p", worker_mode="headless")
        self.assertEqual(self.cli("start-worker", "RM-1")[0], 0)
        self.assertEqual(st.worker_for("p", task="RM-1")["mode"], "headless")
        for _ in range(100):
            if self.log(): break
            time.sleep(0.05)
        self.assertIn("Arm the run guard first", self.log()[0]["argv"][-1]); self.assertIn("never disarm", self.log()[0]["argv"][-1])

    def test_wake_due_wakes_once_per_inbox_id_and_never_on_a_final_dead_or_a_fresh_claim(self):
        row = lambda **kw: {"session": SID % 1, "task": "RM-1", "state": "stopped", **kw}
        st.inbox_add("p", "RM-1", "go")
        self.assertIsNotNone(sw.wake_due("p", row()))
        self.assertIsNone(sw.wake_due("p", row(woken="A1")))  # already woken for A1
        self.assertIsNone(sw.wake_due("p", row(dead_key="A1")))
        self.assertIsNone(sw.wake_due("p", row(waking=st.now())))
        self.assertIsNotNone(sw.wake_due("p", row(waking="2020-01-01T00:00:00+0000")))  # an old claim expires
        self.assertIsNotNone(sw.wake_due("p", row(woken="A1", restart_pending=True, restarts=1)))
        st.inbox_add("p", "RM-1", "more")
        self.assertIsNotNone(sw.wake_due("p", row(woken="A1", dead_key="A1")))  # a new entry
        st.set_worker("p", SID % 2, task="RM-2", state="stopped", waking=st.now())
        self.assertEqual(sw.slots_used("p"), 1)  # a claim counts against the cap

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

    # pack branches, pack worktrees, the worker's map and the one-task-per-repo rule
    def repos(self):
        self.sib = self.t / "sib"; self.sib.mkdir()
        git(self.sib, "init", "-q", "-b", "dev"); git(self.sib, "config", "user.name", "T"); git(self.sib, "config", "user.email", "t@x.invalid")
        git(self.sib, "commit", "-q", "--allow-empty", "-m", "sib base")
        (self.hub / ".config").mkdir(); (self.hub / ".local").mkdir()
        (self.hub / ".config" / "repos.project.md").write_text(
            "| Repo | Required | Role | Default branch | Integration branch | Work mode |\n|---|---|---|---|---|---|\n"
            "| hub | yes | x | main | main | default-branch |\n| sib | no | x | dev | dev | ask |\n| a-b | no | x | unknown | unknown | ask |\n")
        (self.hub / ".local" / "repos.map").write_text(f"# map\nhub: {self.hub}\nsib: {self.sib}\n")
        self.wt = self.t / "wt"

    def task_file(self, task, repos, root=None):
        d = (root or self.hub) / "docs/tasks_manager/_todos"; d.mkdir(parents=True, exist_ok=True)
        (d / f"{task}-x.md").write_text(f"# x\n\n| Repos | {repos} |\n")

    def test_start_pack_makes_branch_and_worktree_and_is_safe_twice_and_refuses_a_foreign_path(self):
        self.repos()
        self.assertEqual(self.cli("pack", "a", "RM-1", "--branch", "sib=feat/x")[0], 0)
        self.assertEqual(st.read_pack("p", "a")["branches"], {"sib": "feat/x"})
        self.assertEqual(self.cli("pack", "a", "RM-1", "RM-2")[0], 0)  # written again without --branch: kept
        self.assertEqual(st.read_pack("p", "a")["branches"], {"sib": "feat/x"})
        for _ in range(2):
            self.assertEqual(self.cli("start-pack", "a")[0], 0)
        pw = self.t / "sib-a"
        self.assertEqual(git(pw, "symbolic-ref", "--short", "HEAD"), "feat/x")
        self.assertEqual(git(pw, "rev-parse", "HEAD"), git(self.sib, "rev-parse", "dev"))
        self.cli("pause-pack", "a"); git(self.sib, "worktree", "remove", str(pw)); pw.mkdir()
        rc, _, err = self.cli("start-pack", "a")
        self.assertEqual(rc, 3); self.assertIn("is not a worktree of sib on feat/x", err)

    def test_start_pack_attaches_to_an_existing_branch_and_falls_back_to_the_checked_out_one_for_na(self):
        self.repos()
        git(self.sib, "branch", "feat/old"); git(self.sib, "commit", "-q", "--allow-empty", "-m", "later")
        self.cli("pack", "a", "RM-1", "--branch", "sib=feat/old"); self.assertEqual(self.cli("start-pack", "a")[0], 0)
        self.assertEqual(git(self.t / "sib-a", "symbolic-ref", "--short", "HEAD"), "feat/old")
        r = self.hub / ".config" / "repos.project.md"; r.write_text(r.read_text().replace("| dev | dev |", "| dev | N/A |"))
        git(self.sib, "checkout", "-q", "-b", "elsewhere")
        self.cli("pack", "b", "RM-2", "--branch", "sib=feat/new")
        rc, out, _ = self.cli("start-pack", "b")
        self.assertEqual(rc, 0); self.assertIn("branching from elsewhere", out)
        self.assertEqual(git(self.t / "sib-b", "rev-parse", "HEAD"), git(self.sib, "rev-parse", "elsewhere"))

    def test_hand_start_refuses_a_task_whose_repo_is_held_and_a_relative_map_path_and_a_linked_map_dir(self):
        self.repos()
        for t in ("RM-1", "RM-2"):
            self.task_file(t, "`sib`")
        self.cli("pack", "a", "RM-1", "RM-2", "--parallel", "--branch", "sib=feat/x"); self.cli("start-pack", "a")
        st.set_worker("p", SID % 1, task="RM-1", state="running")
        rc, _, err = self.cli("start-worker", "RM-2"); self.assertEqual(rc, 3); self.assertIn("RM-1 holds repo 'sib'", err)
        (self.hub / ".local" / "repos.map").write_text("sib: rel/path\n")
        rc, _, err = self.cli("pack", "c", "RM-5", "--branch", "sib=f/z"); self.assertEqual(rc, 3); self.assertIn("'sib' is not absolute", err)
        (self.hub / ".local" / "repos.map").write_text(f"sib: {self.sib}\n")
        st.drop_worker("p", SID % 1); self.task_file("RM-2", "hub", self.wt)
        (self.t / "elsewhere").mkdir(); (self.wt / ".local").symlink_to(self.t / "elsewhere")
        rc, _, err = self.cli("start-worker", "RM-2"); self.assertEqual(rc, 3); self.assertIn("symbolic link", err)
        self.assertEqual(list((self.t / "elsewhere").iterdir()), [])

    def test_pack_branch_refuses_an_unknown_slug_a_slug_without_a_map_line_and_a_bad_branch(self):
        self.repos()
        for argv, word in ((("--branch", "nope=x"), "'nope'"), (("--branch", "a-b=x"), "'a-b' has no path"),
                           (("--branch", "sib=-x"), "not a usable"), (("--branch", "sib=dev"), "default or integration"),
                           (("--branch", "sib=f/x", "--branch", "sib=f/y"), "twice"), (("--branch", "sib=a..b"), "not a usable")):
            rc, _, err = self.cli("pack", "a", "RM-1", *argv)
            self.assertEqual(rc, 3, argv); self.assertIn(word, err)
        self.assertIsNone(st.read_pack("p", "a"))

    def test_start_worker_writes_a_map_that_resolves_and_keeps_the_first_tip_in_the_pack(self):
        self.repos()
        self.task_file("RM-1", "sib", self.wt)
        self.cli("pack", "a", "RM-1", "--branch", "sib=feat/x"); self.cli("start-pack", "a")
        self.assertEqual(self.cli("start-worker", "RM-1")[0], 0)
        lines = (self.wt / ".local" / "repos.map").read_text().splitlines()
        self.assertIn(f"sib: {self.t / 'sib-a'}", lines); self.assertIn(f"hub: {self.hub}", lines)
        row = st.worker_for("p", task="RM-1")
        tip = git(self.sib, "rev-parse", "dev")
        self.assertEqual(st.read_pack("p", "a")["tips"], {"sib": tip})
        git(self.t / "sib-a", "commit", "-q", "--allow-empty", "-m", "phase 1")
        self.cli("pause-pack", "a"); self.assertEqual(self.cli("start-pack", "a")[0], 0)
        self.assertEqual(st.read_pack("p", "a")["tips"], {"sib": tip})  # a second start-pack keeps the first tip
        os.environ["FAKE_READY_RC"] = "1"; self.assertEqual(self.cli("start-worker", "RM-1")[0], 3); os.environ.pop("FAKE_READY_RC")
        self.assertEqual(st.read_pack("p", "a")["tips"], {"sib": tip})  # and so does a failed worker start
        self.assertIn("one commit per phase", next(l for l in self.log() if l["argv"][0] == "--bg")["argv"][-1])

    def test_close_pack_removes_only_a_clean_worktree_at_the_tip_and_keeps_the_branch(self):
        self.repos(); self.cli("pack", "a", "RM-1", "--branch", "sib=feat/x"); self.cli("start-pack", "a")
        wt = self.t / "sib-a"; (wt / "half.py").write_text("x")
        rc, out, _ = self.cli("close-pack", "a"); self.assertEqual(rc, 0); self.assertIn("kept", out); self.assertIn("uncommitted changes", out); self.assertTrue(wt.exists())
        (wt / "half.py").unlink(); git(wt, "commit", "-q", "--allow-empty", "-m", "phase 1")
        rc, out, _ = self.cli("close-pack", "a"); self.assertIn("not at the landed tip", out); self.assertTrue(wt.exists())
        st.write_pack("p", {**st.read_pack("p", "a"), "tips": {"sib": git(wt, "rev-parse", "HEAD")}})
        (self.sib / ".git/info/exclude").write_text("*.log\n")
        (wt / "run.log").write_text("evidence")  # an ignored file survives: the worktree stays
        rc, out, _ = self.cli("close-pack", "a"); self.assertIn("1 ignored file(s)", out); self.assertTrue((wt / "run.log").exists())
        (wt / "run.log").unlink()
        rc, out, _ = self.cli("close-pack", "a"); self.assertIn(f"removed {wt}", out); self.assertFalse(wt.exists())
        git(self.sib, "rev-parse", "--verify", "feat/x")  # the branch is still there (git raises when it is gone)

    def test_a_pack_without_branches_writes_no_map_and_no_worktree(self):
        self.repos()
        self.running_pack(("RM-1",))
        self.assertEqual(self.cli("start-worker", "RM-1")[0], 0)
        self.assertFalse((self.wt / ".local").exists()); self.assertFalse((self.t / "sib-a").exists())

    def test_two_tasks_on_one_pack_repo_are_never_offered_together_and_the_second_follows_the_first_landing(self):
        self.repos()
        for t, r in (("RM-1", "sib"), ("RM-2", "sib"), ("RM-3", "hub")):
            self.task_file(t, r)
        self.cli("pack", "a", "RM-1", "RM-2", "RM-3", "--parallel", "--branch", "sib=feat/x"); self.cli("start-pack", "a")
        self.assertEqual(sw.next_tasks("p"), ["RM-1", "RM-3"])
        st.set_worker("p", SID % 1, task="RM-1", state="running")
        self.assertEqual(sw.next_tasks("p"), ["RM-3"])
        st.set_worker("p", SID % 1, state="done")
        self.assertEqual(sw.next_tasks("p"), ["RM-3"])
        st.emit("p", "landed", task="RM-1")
        self.assertEqual(sw.next_tasks("p"), ["RM-2", "RM-3"])

    def blocked(self, task, cell):
        d = self.hub / "docs/tasks_manager/_todos"; d.mkdir(parents=True, exist_ok=True)
        (d / f"{task}-x.md").write_text(f"# x\n\n| Blocked by | {cell} |\n")

    def test_blocked_by_offers_the_task_after_its_blocker_landed_and_a_started_blocker_alone_does_not_free_it(self):
        self.blocked("RM-2", "`RM-1` Phase 1, RM-1")
        self.running_pack(("RM-1", "RM-2"), parallel=True)
        self.assertEqual(sw.next_tasks("p"), ["RM-1"])
        st.set_worker("p", SID % 1, task="RM-1", state="done")
        self.assertEqual(sw.next_tasks("p"), [])
        rc, _, err = self.cli("start-worker", "RM-2")
        self.assertNotEqual(rc, 0); self.assertIn("RM-2 is blocked by RM-1", err)
        st.emit("p", "landed", task="RM-1")
        self.assertEqual(sw.next_tasks("p"), ["RM-2"])

    def test_an_archived_blocker_outside_the_pack_does_not_block_and_dash_or_none_names_no_blocker(self):
        arch = self.hub / "docs/tasks_manager/_todos_archived"; arch.mkdir(parents=True); (arch / "RM-9-x.md").write_text("# x\n")
        self.blocked("RM-1", "RM-9 Phase 2"); self.blocked("RM-2", "\u2014"); self.blocked("RM-3", "none")
        self.running_pack(parallel=True)
        self.assertEqual(sw.next_tasks("p"), ["RM-1", "RM-2", "RM-3"])

    def test_pack_and_start_pack_refuse_an_open_blocker_outside_the_pack_a_serial_order_against_an_edge_and_a_cycle(self):
        self.blocked("RM-2", "RM-1"); self.blocked("RM-3", "RM-7")
        for argv, edge in ((("RM-3",), "RM-3 is blocked by RM-7"), (("RM-2", "RM-1"), "RM-2 is blocked by RM-1")):
            rc, _, err = self.cli("pack", "a", *argv); self.assertEqual(rc, 3, err); self.assertIn(edge, err)
        self.assertEqual(self.cli("pack", "a", "RM-2", "RM-1", "--parallel")[0], 0)  # parallel: the order is free
        self.blocked("RM-4", "RM-5"); self.blocked("RM-5", "RM-4")
        rc, _, err = self.cli("pack", "b", "RM-4", "RM-5", "--parallel"); self.assertEqual(rc, 3); self.assertIn("cycle", err)
        self.assertIn("is blocked by", err)
        self.blocked("RM-6", "RM-6")
        rc, _, err = self.cli("pack", "c", "RM-6"); self.assertEqual(rc, 3); self.assertIn("RM-6 is blocked by RM-6", err)
        self.blocked("RM-1", "RM-5")  # the task file changed after `pack`: start-pack checks again
        rc, _, err = self.cli("start-pack", "a"); self.assertEqual(rc, 3); self.assertIn("RM-1 is blocked by RM-5", err)

    def test_an_unreadable_task_file_in_a_serial_pack_is_offered_and_start_worker_refuses_it_by_name(self):
        self.running_pack(("RM-1", "RM-2"))
        (self.hub / "docs/tasks_manager/_todos").mkdir(parents=True, exist_ok=True)
        (self.hub / "docs/tasks_manager/_todos/RM-1-x.md").write_bytes(b"\xff\xfe")
        self.assertEqual(sw.next_tasks("p"), ["RM-1"])
        rc, _, err = self.cli("start-worker", "RM-1"); self.assertEqual(rc, 3); self.assertIn("RM-1-x.md cannot be read", err)

    def test_a_non_ascii_digit_in_a_blocked_by_cell_neither_raises_nor_blocks(self):
        self.blocked("RM-2", "RM-\u0661")
        self.running_pack(("RM-1", "RM-2"), parallel=True)
        self.assertEqual(sw.next_tasks("p"), ["RM-1", "RM-2"])

    def test_an_edge_written_after_start_pack_is_offered_and_refused_with_the_edge_named(self):
        self.running_pack(("RM-1", "RM-2"), parallel=True)
        self.blocked("RM-1", "RM-7")
        self.assertEqual(sw.next_tasks("p"), ["RM-1", "RM-2"])
        rc, _, err = self.cli("start-worker", "RM-1"); self.assertEqual(rc, 3); self.assertIn("RM-1 is blocked by RM-7", err)
        self.blocked("RM-1", "RM-2"); self.blocked("RM-2", "RM-1")
        self.assertEqual(sw.next_tasks("p"), ["RM-1", "RM-2"])
        rc, _, err = self.cli("start-worker", "RM-2"); self.assertEqual(rc, 3); self.assertIn("RM-2 is blocked by RM-1, and", err)

    def test_the_cycle_message_names_an_edge_on_the_cycle_for_a_serial_self_edge_and_a_task_that_only_waits_on_it(self):
        self.blocked("RM-1", "RM-1")
        rc, _, err = self.cli("pack", "a", "RM-1"); self.assertEqual(rc, 3); self.assertIn("RM-1 is blocked by RM-1, and the blockers of the pack form a cycle", err)
        self.blocked("RM-1", "RM-2"); self.blocked("RM-2", "RM-3"); self.blocked("RM-3", "RM-2")
        rc, _, err = self.cli("pack", "a", "RM-1", "RM-2", "RM-3", "--parallel"); self.assertEqual(rc, 3)
        self.assertTrue("RM-2 is blocked by RM-3, and" in err or "RM-3 is blocked by RM-2, and" in err, err)

    def test_a_healthy_pack_listed_after_an_unhealthy_one_still_gets_the_only_slot(self):
        self.blocked("RM-1", "RM-7")
        for name, task in (("a", "RM-1"), ("b", "RM-2")):  # written as a running pack, as if the edge came after start-pack
            st.write_pack("p", {"name": name, "tasks": [task], "parallel": True, "state": "running"})
        self.cli("cap", "1")
        self.assertEqual(sw.next_tasks("p"), ["RM-2"])

    def test_no_profile_is_a_usage_error(self):
        with self.assertRaises(SystemExit) as c, redirect_stderr(io.StringIO()):
            self.cli("packs", profile=False)
        self.assertEqual(c.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
