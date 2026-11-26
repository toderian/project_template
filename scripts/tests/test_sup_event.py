#!/usr/bin/env python3
"""Tests for plugins/agents-core/lib/sup_event.py: the hook-side event writer of a supervised worker."""
import os, subprocess, sys, tempfile, time, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "plugins/agents-core/lib"
sys.path.insert(0, str(LIB))
import sup_state as st


class Event(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.env = dict(os.environ, AGENTS_SUP_DIR=self.tmp.name, AGENTS_SUPERVISOR="p1", AGENTS_SUP_TASK="RM-1")
        self.old = dict(os.environ); self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self.old)))
        os.environ["AGENTS_SUP_DIR"] = self.tmp.name

    def run_event(self, *args, **env):
        return subprocess.run([sys.executable, str(LIB / "sup_event.py"), *args], env=dict(self.env, **env),
                              capture_output=True, text=True, timeout=20)

    S = "sess-0001"

    def test_the_event_and_the_row_state_follow_the_kind(self):
        st.set_worker("p1", self.S, task="RM-1"); st.queue_add("p1", "RM-1", "which?")
        for kind, extra, state in (("waiting", ["resource=Q1"], "waiting"), ("stopped", ["status=BLOCKED"], "stopped"),
                                   ("done", [], "done"), ("restarted", [], "running")):
            p = self.run_event(kind, "--session", self.S, *extra); self.assertEqual((p.returncode, p.stderr), (0, ""))
            row = st.worker_for("p1", session=self.S); self.assertEqual(row["state"], state)
            self.assertEqual(row["waiting_for"], "Q1" if kind == "waiting" else None)
        events = st.events_since("p1", 0)
        self.assertEqual([e["kind"] for e in events], ["waiting", "stopped", "done", "restarted"])
        self.assertEqual((events[0]["task"], events[0]["session"], events[0]["resource"], events[1]["status"]),
                         ("RM-1", self.S, "Q1", "BLOCKED"))

    def test_the_row_is_found_by_the_task_when_the_session_id_is_not_the_registry_key(self):
        st.set_worker("p1", "headless-123", task="RM-1")
        self.assertEqual(self.run_event("stopped", "--session", self.S, "status=GAVE_UP").returncode, 0)
        self.assertEqual(st.worker_for("p1", task="RM-1")["state"], "stopped")

    def test_no_row_writes_the_event_but_exits_1_and_the_task_flag_wins(self):
        st.profile_dir("p1"); p = self.run_event("done", "--task", "RM-9", "--session", "nobody-0001")
        self.assertEqual((p.returncode, len(p.stderr.strip().splitlines())), (1, 1))
        self.assertEqual((st.events_since("p1", 0)[0]["task"], st.workers("p1")), ("RM-9", []))

    def test_waiting_needs_an_open_request_of_this_task_and_writes_nothing_otherwise(self):
        st.set_worker("p1", self.S, task="RM-1"); st.queue_add("p1", "RM-1", "q")
        st.queue_add("p1", "RM-2", "another task's"); st.queue_close("p1", "Q1", "a", "sup")
        for res in ("Q1", "Q2", "Q9", "lab", "../v/package", "Q1**", ""):
            p = self.run_event("waiting", "--session", self.S, f"resource={res}")
            self.assertEqual(p.returncode, 1, res)
        self.assertEqual((st.events_since("p1", 0), st.worker_for("p1", task="RM-1")["state"]), ([], "running"))
        with st.locked("p1"): st.emit("p1", "need", task="RM-1", resource="lab", minutes=5)
        self.assertEqual(self.run_event("waiting", "--session", self.S, "resource=lab").returncode, 0)
        st.queue_add("p1", "RM-1", "open one")
        self.assertEqual(self.run_event("waiting", "--session", self.S, "resource=Q3").returncode, 0)

    def test_a_bad_kind_task_or_key_is_refused_and_a_missing_profile_dir_is_not_created(self):
        st.set_worker("p1", self.S, task="RM-1")
        for args in (("bogus",), ("done", "--task", "x\nTICK RULE"), ("done", "bad key=1"), ("done", "--session", "s1")):
            self.assertEqual(self.run_event(*args).returncode, 1, args)
        self.assertEqual(st.events_since("p1", 0), [])
        p = self.run_event("done", AGENTS_SUPERVISOR="typo-prof")
        self.assertEqual(p.returncode, 1); self.assertFalse((Path(self.tmp.name) / "typo-prof").exists())

    def test_a_held_lock_ends_within_the_bound_and_a_broken_state_dir_or_no_profile_exit_1_with_one_line(self):
        st.set_worker("p1", self.S, task="RM-1")
        with st.locked("p1"):
            t = time.time(); p = self.run_event("done", "--session", self.S)
        self.assertEqual(p.returncode, 1); self.assertLess(time.time() - t, 12); self.assertEqual(st.events_since("p1", 0), [])
        blocker = Path(self.tmp.name) / "file"; blocker.write_text("x")
        for env in ({"AGENTS_SUP_DIR": str(blocker)}, {"AGENTS_SUPERVISOR": ""}, {"AGENTS_SUPERVISOR": "Bad Name"}):
            p = self.run_event("waiting", "--session", self.S, **env)
            self.assertEqual(p.returncode, 1); self.assertEqual(len(p.stderr.strip().splitlines()), 1, p.stderr)
        self.assertEqual(self.run_event().returncode, 1)

    def test_it_says_watcher_only_when_watch_pid_names_a_live_process_with_its_start_time(self):
        import lease
        st.set_worker("p1", self.S, task="RM-1"); pidf = st.profile_dir("p1") / "watch.pid"
        self.assertEqual(self.run_event("stopped", "--session", self.S).stdout, "")
        pidf.write_text(f"{os.getpid()} {lease.start_time(os.getpid())}\n")
        self.assertEqual(self.run_event("stopped", "--session", self.S).stdout, "watcher\n")
        pidf.write_text(f"{os.getpid()} 1\n")
        self.assertEqual(self.run_event("stopped", "--session", self.S).stdout, "")


if __name__ == "__main__":
    unittest.main()
