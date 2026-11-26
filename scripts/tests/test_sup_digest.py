#!/usr/bin/env python3
"""Tests for plugins/agents-core/lib/sup_digest.py: status, done check, measure."""
import argparse, contextlib, io, json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "plugins/agents-core/lib"))
import lease, sup_digest as dg, sup_state as st

P = "p"
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.old = dict(os.environ); self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self.old)))
        t = Path(self.tmp.name)
        os.environ.update(AGENTS_SUP_DIR=str(t / "sup"), AGENTS_LEASE_DIR=str(t / "leases"))
        os.environ.pop("AGENTS_SUPERVISOR", None)
        self.hub = t / "hub"; self.hub.mkdir()
        self.git("init", "-q", "-b", "master")
        self.todos = self.hub / "docs/tasks_manager/_todos"; self.todos.mkdir(parents=True)
        self.clock = 1_700_000_000
        self.orig_now = st.now; st.now = self.fake_now; self.addCleanup(lambda: setattr(st, "now", self.orig_now))

    def fake_now(self):
        import time
        return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.gmtime(self.clock))

    def git(self, *a):
        subprocess.run([*GIT, "-C", str(self.hub), *a], check=True, capture_output=True)

    def commit_tasks(self, ids):
        for i in ids:
            (self.todos / f"{i}-x.md").write_text(i)
        self.git("add", "-A"); self.git("commit", "-q", "-m", "tasks")

    def close_out(self, task):
        self.git("checkout", "-q", "-b", f"task/{task}")
        self.git("rm", "-q", f"docs/tasks_manager/_todos/{task}-x.md"); self.git("commit", "-q", "-m", "close")
        self.git("checkout", "-q", "master")

    def cli(self, *argv):
        ap = argparse.ArgumentParser(); sub = ap.add_subparsers(); dg.register(sub)
        args = ap.parse_args(list(argv))
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = args.func(args)
        return code, out.getvalue(), err.getvalue()

    def take_lease(self, res, task, restore=False, pid=None):
        import time
        with lease.locked() as d:
            lease.write(d, res, {"pid": pid or os.getpid(), "pid_start": None, "session": None, "task": task,
                                 "start": time.time(), "ttl": 60, "restore": restore})


class Status(Base):
    def test_digest_shows_every_section_and_one_state_word_per_task(self):
        self.commit_tasks(["RM-1", "RM-2", "RM-3", "RM-4", "RM-5"]); self.close_out("RM-2"); self.close_out("RM-3")
        st.write_pack(P, {"name": "pk", "tasks": ["RM-1", "RM-2", "RM-3", "RM-4", "RM-5"], "state": "running"})
        st.set_worker(P, "abcdef123456", task="RM-1", state="running")
        st.set_worker(P, "zzzzzz999999", task="RM-4", state="waiting", waiting_for="lab")
        st.emit(P, "landed", task="RM-3")
        st.queue_add(P, "RM-1", "Use A or B?", ["A", "B"], "A")
        self.take_lease("lab", "RM-4")
        code, out, _ = self.cli("status", "--profile", P, "--hub", str(self.hub))
        self.assertEqual(code, 0)
        for want in ("Q1 RM-1: Use A or B? -> A", "RM-1 running", "RM-2 closed-out", "RM-3 landed", "RM-4 waiting",
                     "RM-5 waiting-to-start", "abcdef12", "lab", "lab RM-4 held", "unhandled: 1", "#1 landed RM-3"):
            self.assertIn(want, out)
        code, out, _ = self.cli("status", "--profile", P, "--hub", str(self.hub), "--json")
        self.assertIn("lines", json.loads(out))

    def test_digest_stays_under_60_lines_with_30_tasks(self):
        ids = [f"RM-{i}" for i in range(1, 31)]
        self.commit_tasks(ids)
        st.write_pack(P, {"name": "big", "tasks": ids[:15]}); st.write_pack(P, {"name": "big2", "tasks": ids[15:]})
        for i in ids:
            st.set_worker(P, f"s{i}", task=i, state="running")
            st.queue_add(P, i, "q " * 80, None, "r " * 50); st.emit(P, "ask", task=i)
            self.take_lease(f"res-{i.lower()}", i)
        text = dg.digest(P, self.hub)
        self.assertLess(len(text.splitlines()), 60)
        self.assertIn("OPEN QUESTIONS (30)", text)

    def test_no_profile_is_a_usage_error(self):
        code, _, err = self.cli("status", "--hub", str(self.hub))
        self.assertEqual(code, 2); self.assertTrue(err.startswith("at: sup: "))


class Done(Base):
    def test_done_check_names_each_failing_item_and_passes_when_clean(self):
        self.commit_tasks(["RM-1", "RM-2", "RM-3"]); self.close_out("RM-1"); self.close_out("RM-2")
        st.write_pack(P, {"name": "pk", "tasks": ["RM-1", "RM-2", "RM-3"]})
        st.emit(P, "landed", task="RM-1")
        st.set_worker(P, "sess1", task="RM-3", state="running")
        qid = st.queue_add(P, "RM-2", "ok?", blocking=True)
        st.queue_add(P, "RM-1", "fyi", blocking=False)
        self.take_lease("lab", "RM-1")
        self.take_lease("dev", "RM-2", restore=True, pid=2 ** 22 + 12345)
        self.take_lease("other", "XX-9")
        bad = "\n".join(dg.done_check(P, "pk", self.hub))
        for want in ("RM-2: closed out but not landed", "RM-3: not closed out (running)", "RM-3: live worker sess1",
                     f"{qid}: open blocking question for RM-2", "lease lab held by RM-1", "lease dev owed by RM-2"):
            self.assertIn(want, bad)
        self.assertNotIn("fyi", bad); self.assertNotIn("other", bad)
        code, out, _ = self.cli("done", "pk", "--profile", P, "--hub", str(self.hub))
        self.assertEqual(code, 3); self.assertIn("lease lab held by RM-1", out)

        st.drop_worker(P, "sess1"); st.queue_close(P, qid, "yes", "owner")
        self.close_out("RM-3"); st.emit(P, "landed", task="RM-2"); st.emit(P, "landed", task="RM-3")
        for r in ("lab", "dev"):
            (lease.lease_dir() / f"{r}.json").unlink()
        self.assertEqual(dg.done_check(P, "pk", self.hub), [])
        self.assertEqual(self.cli("done", "pk", "--profile", P, "--hub", str(self.hub)), (0, "done: pk\n", ""))

    def test_a_task_merged_with_its_branch_gone_is_closed_out_on_the_default_branch(self):
        self.commit_tasks(["RM-1"]); (self.todos / "RM-1-x.md").unlink()
        self.git("add", "-A"); self.git("commit", "-q", "-m", "landed")
        st.write_pack(P, {"name": "pk", "tasks": ["RM-1"]}); st.emit(P, "landed", task="RM-1")
        self.assertEqual(dg.done_check(P, "pk", self.hub), [])

    def test_unknown_pack_is_a_usage_error(self):
        self.assertEqual(self.cli("done", "nope", "--profile", P, "--hub", str(self.hub))[0], 2)


class Measure(Base):
    def test_numbers_come_from_events_queue_and_touch_log(self):
        st.write_pack(P, {"name": "pk", "tasks": ["RM-1", "RM-2"]})
        st.emit(P, "started", task="RM-1")
        self.clock += 60; q1 = st.queue_add(P, "RM-1", "a?"); st.emit(P, "ask", task="RM-1", q=q1)
        q2 = st.queue_add(P, "RM-2", "b?"); st.emit(P, "ask", task="RM-2", q=q2)
        self.clock += 120; st.queue_close(P, q1, "x", "owner")
        self.clock += 360; st.queue_close(P, q2, "y", "sup")
        st.touch(P, "answer Q1"); st.touch(P, "instruct")
        for k in ("restarted", "restarted", "dead", "tick_failed"):
            st.emit(P, k, task="RM-1")
        self.clock += 600; st.emit(P, "landed", task="RM-1"); st.emit(P, "landed", task="RM-2")
        code, out, _ = self.cli("measure", "--profile", P, "--json")
        m = json.loads(out)
        self.assertEqual((code, m["owner_touches"], m["questions"], m["answered_by_sup"], m["answered_by_owner"]),
                         (0, 2, 2, 1, 1))
        self.assertEqual((m["answer_minutes_median"], m["answer_minutes_max"]), (5.0, 8.0))
        self.assertEqual((m["worker_restarts"], m["dead_workers"], m["tick_failures"], m["tasks_landed"]), (2, 1, 1, 2))
        self.assertEqual(m["pack_wall_minutes"], {"pk": 19.0})
        self.assertIn("owner_touches: 2", self.cli("measure", "--profile", P)[1])
        self.assertEqual(json.loads(self.cli("measure", "--profile", P, "--since", "2999-01-01", "--json")[1])["questions"], 0)
        self.assertEqual(self.cli("measure", "--profile", P, "--since", "yesterday")[0], 2)


if __name__ == "__main__":
    unittest.main()
