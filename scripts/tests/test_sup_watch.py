#!/usr/bin/env python3
"""Tests for plugins/agents-core/lib/sup_watch.py: one pass of the watcher (through `step`) and the detached process."""
import argparse, os, subprocess, sys, tempfile, time, types, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "plugins/agents-core/lib"))
import lease, sup_state as st, sup_watch as sw

P = "p"
FAKE_AT = """#!/usr/bin/env python3
import os, sys, time
d = os.environ["FAKE_AT_DIR"]
open(d + "/argv.log", "a").write(" ".join(sys.argv[1:]) + "\\n")
key = "-".join(sys.argv[1:3])
if os.path.exists(f"{d}/sleep-{key}"): time.sleep(float(open(f"{d}/sleep-{key}").read()))
if os.path.exists(f"{d}/rc-{key}"):
    sys.stderr.write("refused: " + open(f"{d}/rc-{key}").read().strip() + "\\n"); sys.exit(3)
"""
FAKE_WORKERS = "def is_alive(row): return True\ndef wake(profile, session, text): return True\ndef next_tasks(profile): return []\n"


def row(session="s1", task="RM-1", state="running", **kw):
    st.set_worker(P, session, task=task, state=state, **kw)


class Watch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        t = Path(self.tmp.name); self.fake = t / "fake"; self.fake.mkdir()
        self.old = dict(os.environ); self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self.old)))
        os.environ.update(AGENTS_SUP_DIR=str(t / "sup"), AGENTS_LEASE_DIR=str(t / "leases"), FAKE_AT_DIR=str(self.fake),
                          AGENTS_AT_BIN=str(self.fake / "at"))
        for k in ("AGENTS_SUPERVISOR", "CLAUDE_CODE_SESSION_ID", "AGENTS_SUP_CHAT_TOKEN"):
            os.environ.pop(k, None)
        (self.fake / "at").write_text(FAKE_AT); (self.fake / "at").chmod(0o755)
        self.wakes, self.wake_ok, self.next, self.dead = [], True, [], set()
        mod = types.ModuleType("sup_workers")
        mod.is_alive = lambda r: r["session"] not in self.dead
        mod.wake = lambda p, s, text: (self.wakes.append((s, text)), self.wake_ok)[1]
        mod.next_tasks = lambda p: list(self.next)
        saved = sys.modules.get("sup_workers"); sys.modules["sup_workers"] = mod
        self.addCleanup(lambda: sys.modules.pop("sup_workers", None) if saved is None else sys.modules.update(sup_workers=saved))
        old_t = sw.TICK_TIMEOUT; self.addCleanup(lambda: setattr(sw, "TICK_TIMEOUT", old_t))

    def argv(self):
        f = self.fake / "argv.log"
        return f.read_text().splitlines() if f.exists() else []

    def kinds(self):
        return [e["kind"] for e in st.events_since(P, 0)]

    def test_dead_worker_is_stopped_with_one_dead_event(self):
        st.set_config(P, land="manual"); row(); row("s2", "RM-2"); self.dead.add("s1")
        self.assertEqual(sw.step(P, None, tick=False), ["dead RM-1"])
        self.assertEqual(st.worker_for(P, session="s1")["state"], "stopped")
        self.assertEqual(st.worker_for(P, session="s2")["state"], "running")
        self.assertEqual(sw.step(P, None, tick=False), []); self.assertEqual(self.kinds(), ["dead"])

    def test_overdue_and_owed_leases_each_give_one_event(self):
        gone = subprocess.run([sys.executable, "-c", "import os; print(os.getpid())"], capture_output=True, text=True)
        with lease.locked() as d:
            me = {"pid": os.getpid(), "pid_start": lease.start_time(os.getpid()), "session": None, "task": "RM-1",
                  "start": time.time() - 7200, "ttl": 1}
            lease.write(d, "lab", me)
            lease.write(d, "target", {**me, "pid": int(gone.stdout), "pid_start": None, "restore": True})
            lease.write(d, "fresh", {**me, "start": time.time(), "ttl": 60})
        self.assertEqual(sorted(sw.step(P, None, tick=False)), ["overdue lab", "owed target"])
        self.assertEqual(sw.step(P, None, tick=False), [])
        ev = {e["kind"]: e for e in st.events_since(P, 0)}
        self.assertEqual((ev["overdue"]["resource"], ev["owed"]["resource"], ev["owed"]["task"]), ("lab", "target", "RM-1"))

    def test_unread_answer_wakes_a_stopped_row_once(self):
        row(state="stopped"); row("s2", "RM-2", state="stopped")
        st.inbox_add(P, "RM-1", "go")
        self.assertEqual(sw.step(P, None, tick=False), ["restarted RM-1"])
        self.assertEqual(self.wakes, [("s1", "Read your answers with: at sup inbox")])
        self.assertEqual(self.kinds(), ["restarted"]); self.assertEqual(st.worker_for(P, session="s1")["state"], "running")

    def test_wake_gives_up_after_three_failures_with_one_dead_event(self):
        row(state="stopped"); st.inbox_add(P, "RM-1", "go"); self.wake_ok = False
        for _ in range(5): sw.step(P, None, tick=False)
        self.assertEqual(len(self.wakes), 3); self.assertEqual(self.kinds(), ["dead"])

    def test_free_resource_adds_an_inbox_entry_once_and_the_next_pass_wakes(self):
        row(state="waiting", waiting_for="full-suite")
        with st.locked(P): st.emit(P, "need", "RM-1", "s1", resource="full-suite", minutes=20)
        self.assertEqual(sw.step(P, None, tick=False), ["free full-suite for RM-1"])
        self.assertEqual(st.inbox(P, "RM-1")[0]["text"], 'free: run "at sup need full-suite --minutes 20" again')
        self.assertEqual(sw.step(P, None, tick=False), ["restarted RM-1"])
        row(state="waiting", waiting_for="full-suite")
        st.inbox_ack(P, "RM-1", "A1")
        self.assertEqual(sw.step(P, None, tick=False), [])

    def test_free_resource_needs_a_grant_or_auto_and_a_free_lease(self):
        row(state="waiting", waiting_for="lab")
        with st.locked(P): st.emit(P, "need", "RM-1", "s1", resource="lab", minutes=5)
        self.assertEqual(sw.step(P, None, tick=False), [])
        with st.locked(P): st.emit(P, "granted", "RM-1", "s1", resource="lab")
        with lease.locked() as d:
            lease.write(d, "lab", {"pid": os.getpid(), "pid_start": lease.start_time(os.getpid()), "session": None,
                                   "start": time.time(), "ttl": 60})
        self.assertEqual(sw.step(P, None, tick=False), [])
        (Path(os.environ["AGENTS_LEASE_DIR"]) / "lab.json").unlink()
        self.assertEqual(sw.step(P, None, tick=False), ["free lab for RM-1"])

    def test_starts_run_start_worker_and_a_refusal_is_emitted_once(self):
        self.next = ["RM-1", "RM-2"]; (self.fake / "rc-sup-start-worker").write_text("over the cap\n")
        self.assertEqual(sw.step(P, None, tick=False), ["start_refused RM-1", "start_refused RM-2"])
        self.assertEqual(sw.step(P, None, tick=False), [])
        self.assertEqual(self.argv()[0], f"sup start-worker RM-1 --profile {P}"); self.assertEqual(len(self.argv()), 4)
        self.assertEqual(st.events_since(P, 0)[0]["reason"], "refused: over the cap")
        (self.fake / "rc-sup-start-worker").unlink(); self.next = ["RM-3"]
        self.assertEqual(sw.step(P, None, tick=False), ["started RM-3"])

    def test_landing_of_a_done_or_dead_worker_when_land_is_auto(self):
        row(state="done"); row("s2", "RM-2"); row("s3", "RM-3"); self.dead.add("s3")
        self.assertEqual(sw.step(P, None, tick=False), ["dead RM-3", "landed RM-1", "landed RM-3"])
        self.assertEqual(sw.step(P, None, tick=False), []); self.assertEqual(self.kinds().count("landed"), 2)

    def test_land_refusal_once_and_land_manual_skips(self):
        row(state="done"); (self.fake / "rc-sup-land").write_text("not closed out\n")
        self.assertEqual(sw.step(P, None, tick=False), ["land_refused RM-1"])
        self.assertEqual(sw.step(P, None, tick=False), []); self.assertEqual(len(self.argv()), 2)
        (self.fake / "rc-sup-land").unlink(); st.set_config(P, land="manual")
        self.assertEqual(sw.step(P, None, tick=False), []); self.assertEqual(len(self.argv()), 2)

    def test_tick_runs_on_events_not_on_an_empty_log_and_not_with_no_tick(self):
        self.assertEqual(sw.step(P, None), [])
        with st.locked(P): st.emit(P, "ask", "RM-1", "s1")
        self.assertEqual(sw.step(P, None, tick=False), []); self.assertEqual(self.argv(), [])
        self.assertEqual(sw.step(P, None), ["tick"]); self.assertEqual(self.argv(), [f"sup tick --profile {P}"])
        self.assertFalse((st.profile_dir(P) / "tick.pid").exists())

    def test_no_second_tick_while_one_runs(self):
        with st.locked(P): st.emit(P, "ask", "RM-1", "s1")
        (st.profile_dir(P) / "tick.pid").write_text(f"{os.getpid()}\n")
        self.assertEqual(sw.step(P, None), [])

    def test_three_failed_ticks_pause_until_an_owner_touch(self):
        with st.locked(P): st.emit(P, "ask", "RM-1", "s1")
        (self.fake / "rc-sup-tick").write_text("boom\n")
        self.assertEqual(sw.step(P, None), ["tick_failed"]); self.assertEqual(sw.step(P, None), ["tick_failed"])
        self.assertEqual(sw.step(P, None), ["tick_failed", "ticks_paused"])
        self.assertEqual(sw.step(P, None), []); self.assertEqual(sw.step(P, None), [])
        self.assertEqual(self.kinds().count("ticks_paused"), 1); self.assertEqual(len(self.argv()), 3)
        st.touch(P, "answered Q1")
        self.assertEqual(sw.step(P, None), ["tick_failed"]); self.assertEqual(len(self.argv()), 4)

    def test_a_good_tick_resets_the_failure_count(self):
        with st.locked(P): st.emit(P, "ask", "RM-1", "s1")
        rc = self.fake / "rc-sup-tick"; rc.write_text("boom\n")
        sw.step(P, None); sw.step(P, None); rc.unlink()
        self.assertEqual(sw.step(P, None), ["tick"]); rc.write_text("boom\n")
        self.assertEqual(sw.step(P, None), ["tick_failed"]); self.assertEqual(sw.step(P, None), ["tick_failed"])

    def test_a_tick_past_the_timeout_is_killed_and_fails(self):
        with st.locked(P): st.emit(P, "ask", "RM-1", "s1")
        (self.fake / "sleep-sup-tick").write_text("30"); sw.TICK_TIMEOUT = 0.5
        t0 = time.time(); self.assertEqual(sw.step(P, None), ["tick_failed"]); self.assertLess(time.time() - t0, 10)


class Process(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        t = Path(self.tmp.name); (t / "ext").mkdir(); (t / "ext" / "sup_workers.py").write_text(FAKE_WORKERS)
        self.old = dict(os.environ); self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self.old)))
        os.environ.update(AGENTS_SUP_DIR=str(t / "sup"), AGENTS_LEASE_DIR=str(t / "leases"), PYTHONPATH=str(t / "ext"))
        for k in ("CLAUDE_CODE_SESSION_ID", "AGENTS_SUP_CHAT_TOKEN"):
            os.environ.pop(k, None)
        self.addCleanup(lambda: sw.cmd_stop(self.args()))

    def args(self):
        return argparse.Namespace(profile=P, interval=1.0, no_tick=True)

    def test_start_refuses_a_second_watcher_and_stop_ends_it_cleanly(self):
        self.assertEqual(sw.cmd_status(self.args()), 3)
        self.assertEqual(sw.cmd_start(self.args()), 0)
        pid = sw.running_pid(P); self.assertTrue(pid)
        self.assertEqual((st.profile_dir(P) / "watch.pid").read_text().split(), [str(pid), str(lease.start_time(pid))])
        self.assertEqual(sw.cmd_status(self.args()), 0); self.assertEqual(sw.cmd_start(self.args()), 3)
        time.sleep(1.5)
        self.assertEqual(sw.cmd_stop(self.args()), 0)
        self.assertFalse((st.profile_dir(P) / "watch.pid").exists()); self.assertEqual(sw.cmd_status(self.args()), 3)
        log = (st.profile_dir(P) / "watch.log").read_text()
        self.assertIn("watcher started", log); self.assertIn("watcher stopped", log); self.assertNotIn("Traceback", log)

    def test_a_failing_pass_is_logged_and_the_loop_goes_on(self):
        # the child imports lib/sup_workers.py (the script directory wins over PYTHONPATH): fail in the lease step instead
        blocker = Path(self.tmp.name) / "blocker"; blocker.write_text("x")
        os.environ["AGENTS_LEASE_DIR"] = str(blocker / "leases")
        self.assertEqual(sw.cmd_start(self.args()), 0)
        time.sleep(2.5)
        self.assertTrue(sw.running_pid(P))
        self.assertGreaterEqual((st.profile_dir(P) / "watch.log").read_text().count("pass failed"), 2)


if __name__ == "__main__":
    unittest.main()
