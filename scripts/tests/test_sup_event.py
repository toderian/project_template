#!/usr/bin/env python3
"""Tests for plugins/agents-core/lib/sup_event.py: the hook-side event writer of a supervised worker."""
import os, subprocess, sys, tempfile, unittest
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

    def test_the_event_and_the_row_state_follow_the_kind(self):
        st.set_worker("p1", "s1", task="RM-1")
        for kind, extra, state in (("waiting", ["resource=Q1"], "waiting"), ("stopped", ["status=BLOCKED"], "stopped"),
                                   ("done", [], "done"), ("restarted", [], "done")):
            p = self.run_event(kind, "--session", "s1", *extra); self.assertEqual((p.returncode, p.stderr), (0, ""))
            self.assertEqual(st.worker_for("p1", session="s1")["state"], state)
            if kind == "waiting":
                self.assertEqual(st.worker_for("p1", session="s1")["waiting_for"], "Q1")
        events = st.events_since("p1", 0)
        self.assertEqual([e["kind"] for e in events], ["waiting", "stopped", "done", "restarted"])
        self.assertEqual((events[0]["task"], events[0]["session"], events[0]["resource"], events[1]["status"]),
                         ("RM-1", "s1", "Q1", "BLOCKED"))

    def test_no_row_still_emits_and_the_task_flag_wins(self):
        self.assertEqual(self.run_event("done", "--task", "RM-9", "--session", "nobody").returncode, 0)
        self.assertEqual((st.events_since("p1", 0)[0]["task"], st.workers("p1")), ("RM-9", []))

    def test_a_broken_state_dir_or_no_profile_exits_0_with_one_line(self):
        blocker = Path(self.tmp.name) / "file"; blocker.write_text("x")
        for env in ({"AGENTS_SUP_DIR": str(blocker)}, {"AGENTS_SUPERVISOR": ""}, {"AGENTS_SUPERVISOR": "Bad Name"}):
            p = self.run_event("waiting", "--session", "s1", **env)
            self.assertEqual(p.returncode, 0); self.assertEqual(len(p.stderr.strip().splitlines()), 1, p.stderr)
        self.assertEqual(self.run_event().returncode, 0)


if __name__ == "__main__":
    unittest.main()
