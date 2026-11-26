#!/usr/bin/env python3
"""Tests for plugins/agents-core/lib/sup_watch.py: one pass of the watcher (through `step`) and the detached process."""
import argparse, json, os, subprocess, sys, tempfile, time, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "plugins/agents-core/lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lease, sup_state as st, sup_watch as sw
from test_sup_workers import FAKE_CLAUDE

P = "p"
LIB = ROOT / "plugins/agents-core/lib"
FAKE_AT = """#!/usr/bin/env python3
import os, sys, time
d = os.environ["FAKE_AT_DIR"]
a = sys.argv[1:]
open(d + "/argv.log", "a").write(" ".join(a) + "\\n")
key = "-".join(a[:2])
if os.path.exists(f"{d}/sleep-{key}"): time.sleep(float(open(f"{d}/sleep-{key}").read()))
if os.path.exists(f"{d}/rc-{key}"):
    sys.stderr.write("refused: " + open(f"{d}/rc-{key}").read().strip() + "\\n"); sys.exit(3)
if a[:2] == ["sup", "start-worker"]:  # the real command, so the watcher is tested against the real sup_workers
    sys.path.insert(0, os.environ["FAKE_LIB"])
    import argparse, sup_workers
    top = argparse.ArgumentParser(); sup_workers.register(top.add_subparsers())
    args = top.parse_args(a[1:]); sys.exit(args.func(args))
if a[:2] == ["sup", "worktree"]:
    print(d + "/wt")
"""


def git(path, *a):
    return subprocess.run(["git", "-C", str(path), *a], capture_output=True, text=True, check=True).stdout.strip()


def sid(n):
    return "abcd1234-0000-4000-8000-00000000000%d" % n


class Watch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        t = Path(self.tmp.name).resolve(); self.fake = t / "fake"; (self.fake / "wt").mkdir(parents=True)
        self.old = dict(os.environ); self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self.old)))
        self.cwd = os.getcwd(); self.addCleanup(lambda: os.chdir(self.cwd))
        os.environ.update(AGENTS_SUP_DIR=str(t / "sup"), AGENTS_LEASE_DIR=str(t / "leases"), FAKE_AT_DIR=str(self.fake),
                          FAKE_DIR=str(self.fake), FAKE_LIB=str(LIB), AGENTS_AT_BIN=str(self.fake / "at"),
                          AGENTS_CLAUDE_BIN=str(self.fake / "claude"))
        for k in ("AGENTS_SUPERVISOR", "CLAUDE_CODE_SESSION_ID", "AGENTS_SUP_CHAT_TOKEN", "AGENTS_SUP_TASK", "AGENTS_SUP_ORIG_PATH"):
            os.environ.pop(k, None)
        for name, body in (("at", FAKE_AT), ("claude", FAKE_CLAUDE)):
            (self.fake / name).write_text(body); (self.fake / name).chmod(0o755)
        self.hub = t / "hub"; self.hub.mkdir()
        git(self.hub, "init", "-q", "-b", "main"); git(self.hub, "config", "user.name", "T"); git(self.hub, "config", "user.email", "t@x.invalid")
        git(self.hub, "commit", "-q", "--allow-empty", "-m", "base")
        st.set_config(P, hub=str(self.hub))
        import sup_workers
        self.sw = sup_workers
        for name, val in (("POLL_DELAY", 0),):
            old_v = getattr(sup_workers, name); setattr(sup_workers, name, val); self.addCleanup(setattr, sup_workers, name, old_v)
        old_t = sw.TICK_TIMEOUT; self.addCleanup(lambda: setattr(sw, "TICK_TIMEOUT", old_t))

    def row(self, n=1, task="RM-1", state="running", alive=True, **kw):
        st.set_worker(P, sid(n), **{"task": task, "state": state, "mode": "bg", "cwd": str(self.fake / "wt"), **kw})
        with open(self.fake / "sessions", "a") as f:
            f.write(sid(n) + "\n")
        if not alive:
            self.kill(n)

    def kill(self, n):
        with open(self.fake / "dead", "a") as f:
            f.write(sid(n) + "\n")

    def pack(self, *tasks, parallel=True, state="running", name="pk"):
        st.write_pack(P, {"name": name, "tasks": list(tasks), "parallel": parallel, "state": state})

    def argv(self):
        f = self.fake / "argv.log"
        return f.read_text().splitlines() if f.exists() else []

    def claude(self):
        f = self.fake / "claude.log"
        return [json.loads(x) for x in f.read_text().splitlines()] if f.exists() else []

    def kinds(self):
        return [e["kind"] for e in st.events_since(P, 0)]

    def state(self, n=1):
        return st.worker_for(P, session=sid(n))["state"]

    def test_dead_worker_is_restarted_twice_then_dead_once_with_one_queue_entry_and_a_notice(self):
        st.set_config(P, land="manual"); self.row(alive=False); self.row(2, "RM-2")
        for _ in range(2):
            self.assertEqual(sw.step(P, None, tick=False)[:2], ["dead RM-1, restart %d" % (_ + 1), "restarted RM-1"])
            self.assertEqual(self.state(), "running")
        self.assertEqual(self.state(2), "running")
        self.assertEqual(sw.step(P, None, tick=False), ["dead RM-1", "notified dead RM-1"])
        self.assertEqual(self.state(), "stopped"); self.assertEqual(sw.step(P, None, tick=False), [])
        self.assertEqual(self.kinds(), ["restarted", "restarted", "dead"])
        self.assertEqual([(q["source"], q["blocking"], q["task"]) for q in st.queue(P)], [("watcher", False, "RM-1")])
        self.assertIn("notify p: dead RM-1", self.argv())
        resumes = [c for c in self.claude() if "--resume" in c["argv"]]
        self.assertEqual(resumes[0]["argv"][-1], "Continue the task. Read your answers with: at sup inbox --task RM-1")

    def test_a_failing_agents_call_declares_nobody_dead_and_one_call_serves_every_row(self):
        self.row(); self.row(2, "RM-2")
        self.assertEqual(sw.step(P, None, tick=False), [])
        self.assertEqual(len([c for c in self.claude() if c["argv"][0] == "agents"]), 1)
        (self.fake / "agents.fail").write_text(""); self.kill(1)
        self.assertEqual(sw.step(P, None, tick=False), []); self.assertEqual(self.kinds(), [])
        self.assertEqual((self.state(), self.state(2)), ("running", "running"))

    def test_an_unknown_stale_starting_row_is_dropped_and_a_fresh_one_is_left(self):
        st.set_worker(P, sid(1), task="RM-1", state="starting", started=st.now())
        st.set_worker(P, sid(2), task="RM-2", state="starting", started="2020-01-01T00:00:00+0000")
        self.assertEqual(sw.step(P, None, tick=False), ["start abandoned RM-2"])
        self.assertEqual([w["task"] for w in st.workers(P)], ["RM-1"])

    def test_overdue_and_owed_leases_each_give_one_event(self):
        gone = subprocess.run([sys.executable, "-c", "import os; print(os.getpid())"], capture_output=True, text=True)
        with lease.locked() as d:
            me = {"pid": os.getpid(), "pid_start": lease.start_time(os.getpid()), "session": None, "task": "RM-1",
                  "start": time.time() - 7200, "ttl": 1}
            lease.write(d, "lab", me)
            lease.write(d, "target", {**me, "pid": int(gone.stdout), "pid_start": None, "restore": True})
            lease.write(d, "fresh", {**me, "start": time.time(), "ttl": 60})
        acts = sw.step(P, None, tick=False)
        self.assertEqual(sorted(a for a in acts if not a.startswith("notified")), ["overdue lab", "owed target"])
        self.assertEqual(sw.step(P, None, tick=False), [])
        ev = {e["kind"]: e for e in st.events_since(P, 0)}
        self.assertEqual((ev["overdue"]["resource"], ev["owed"]["resource"], ev["owed"]["task"]), ("lab", "target", "RM-1"))
        self.assertEqual(len(st.queue(P)), 2)  # both reach the owner without a tick

    def test_unread_answer_wakes_a_stopped_row_in_its_cwd_with_the_task_environment_once(self):
        self.row(state="stopped"); self.row(2, "RM-2", state="stopped"); st.inbox_add(P, "RM-1", "go")
        os.chdir("/")
        self.assertEqual(sw.step(P, None, tick=False), ["restarted RM-1"])
        resume = [c for c in self.claude() if "--resume" in c["argv"]]
        self.assertEqual([c["argv"] for c in resume], [["--bg", "--resume", sid(1), "Read your answers with: at sup inbox --task RM-1"]])
        self.assertEqual((resume[0]["cwd"], resume[0]["sup"], resume[0]["task"]), (str(self.fake / "wt"), P, "RM-1"))
        self.assertEqual(self.kinds(), ["restarted"]); self.assertEqual(self.state(), "running")
        self.assertEqual(sw.step(P, None, tick=False), [])

    def test_an_acknowledged_entry_never_wakes_again(self):
        self.row(state="stopped"); st.inbox_add(P, "RM-1", "go"); st.inbox_ack(P, "RM-1", "A1")
        self.assertEqual(sw.step(P, None, tick=False), []); self.assertEqual(self.claude(), [])

    def test_wake_gives_up_after_three_failures_with_one_dead_event_and_a_new_answer_tries_again(self):
        self.row(state="stopped"); st.inbox_add(P, "RM-1", "go"); (self.fake / "resume.copy").write_text("")
        for _ in range(5): sw.step(P, None, tick=False)
        self.assertEqual(len([c for c in self.claude() if "--resume" in c["argv"]]), 3); self.assertEqual(self.kinds(), ["dead"])
        st.inbox_add(P, "RM-1", "again")
        sw.step(P, None, tick=False)
        self.assertEqual(len([c for c in self.claude() if "--resume" in c["argv"]]), 4)

    def test_a_headless_wake_stores_the_pid_so_the_next_pass_sees_a_live_row(self):
        (self.fake / "hold").write_text("4"); self.row(state="stopped", mode="headless", pid=999999999, restarts=2)
        st.inbox_add(P, "RM-1", "go")
        self.assertEqual(sw.step(P, None, tick=False), ["restarted RM-1"])
        pid = st.worker_for(P, session=sid(1))["pid"]; self.assertNotEqual(pid, 999999999)
        for _ in range(3): self.assertEqual(sw.step(P, None, tick=False), [])  # alive: no `dead`, no second resume
        time.sleep(0.5); self.assertEqual(len([c for c in self.claude() if "--resume" in c["argv"]]), 1)
        self.assertEqual(self.kinds(), ["restarted"]); os.kill(pid, 9)

    def test_an_unacked_answer_wakes_once_and_a_final_dead_is_not_woken_or_declared_again(self):
        st.set_config(P, land="manual"); self.row(state="stopped"); st.inbox_add(P, "RM-1", "go")
        resumes = lambda: len([c for c in self.claude() if "--resume" in c["argv"]])
        sw.step(P, None, tick=False)
        for _ in range(3):
            st.set_worker(P, sid(1), state="waiting", waiting_for=None)  # parked again, answer still unacked
            self.assertEqual(sw.step(P, None, tick=False), [])
        self.assertEqual(resumes(), 1)
        self.kill(1); st.set_worker(P, sid(1), state="running", restarts=2)
        self.assertEqual(sw.step(P, None, tick=False), ["dead RM-1", "notified dead RM-1"])
        for _ in range(3): self.assertEqual(sw.step(P, None, tick=False), [])
        self.assertEqual((resumes(), self.kinds().count("dead")), (1, 1))
        st.inbox_add(P, "RM-1", "new"); self.assertEqual(sw.step(P, None, tick=False), ["restarted RM-1"])  # a new entry
        self.assertEqual(resumes(), 2)

    def test_an_owner_touch_gives_a_final_dead_row_its_restarts_back(self):
        st.set_config(P, land="manual"); self.row(restarts=2, alive=False); st.inbox_add(P, "RM-1", "go"); sw.step(P, None, tick=False)
        st.touch(P, "answered Q1"); sw.step(P, None, tick=False)
        self.assertEqual(self.state(), "running")

    def test_a_lease_whose_task_is_free_text_still_gives_overdue_and_the_pass_goes_on(self):
        with lease.locked() as d:
            lease.write(d, "lab", {"pid": os.getpid(), "pid_start": lease.start_time(os.getpid()), "session": "x",
                                   "task": "nightly build", "start": time.time() - 7200, "ttl": 1})
        self.assertEqual(sw.step(P, None, tick=False)[0], "overdue lab")
        self.assertEqual(st.events_since(P, 0)[0]["resource"], "lab")

    def test_a_part_that_raises_is_logged_and_the_next_part_still_runs(self):
        old = sw._leases; self.addCleanup(setattr, sw, "_leases", old)
        def boom(*a): raise RuntimeError("kaput")
        sw._leases = boom
        st.set_worker(P, sid(2), task="RM-2", state="starting", started="2020-01-01T00:00:00+0000")
        self.assertEqual(sw.step(P, None, tick=False), ["start abandoned RM-2"])
        self.assertIn("kaput", (st.profile_dir(P) / "watch.log").read_text())

    def test_a_dead_row_whose_task_is_archived_on_its_branch_is_done_not_dead(self):
        st.set_config(P, land="manual")
        (self.hub / "docs/tasks_manager/_todos_archived").mkdir(parents=True)
        (self.hub / "docs/tasks_manager/_todos_archived/RM-1-F_x.md").write_text("x")
        git(self.hub, "add", "-A"); git(self.hub, "commit", "-q", "-m", "archive")
        self.row(alive=False)
        self.assertEqual(sw.step(P, None, tick=False), ["done RM-1 (inferred)"])
        self.assertEqual((self.state(), self.kinds()), ("done", ["done"])); self.assertTrue(st.events_since(P, 0)[0]["inferred"])
        self.assertEqual([c for c in self.claude() if "--resume" in c["argv"]], [])

    def test_a_landed_task_settles_its_row_and_closes_the_watchers_queue_entries(self):
        self.row(state="stopped", restarts=2); st.set_config(P, land="manual")
        st.queue_add(P, "RM-1", "dead RM-1", source="watcher", blocking=False)
        st.queue_add(P, "RM-1", "worker question", source="worker")
        self.assertEqual(sw.step(P, None, tick=False), [])
        with st.locked(P): st.emit(P, "landed", "RM-1", sid(1))
        self.assertEqual(sw.step(P, None, tick=False), ["settled RM-1"])
        self.assertEqual(self.state(), "done"); self.assertEqual([q["source"] for q in st.queue(P)], ["worker"])

    def test_the_commands_but_run_refuse_in_a_worker_session(self):
        os.environ["AGENTS_SUP_TASK"] = "RM-1"; a = argparse.Namespace(profile=P, interval=1.0, no_tick=True)
        self.assertEqual([sw.cmd_once(a), sw.cmd_status(a), sw.cmd_start(a), sw.cmd_stop(a)], [3, 3, 3, 3])
        self.assertEqual(self.argv(), [])

    def test_free_resource_adds_an_inbox_entry_once_and_the_next_pass_wakes(self):
        self.row(state="waiting", waiting_for="full-suite")
        with st.locked(P): st.emit(P, "need", "RM-1", sid(1), resource="full-suite", minutes=20)
        self.assertEqual(sw.step(P, None, tick=False), ["free full-suite for RM-1"])
        self.assertEqual(st.inbox(P, "RM-1")[0]["text"], 'free: run "at sup need full-suite --minutes 20" again')
        self.assertEqual(sw.step(P, None, tick=False), ["restarted RM-1"])
        st.set_worker(P, sid(1), state="waiting", waiting_for="full-suite")
        st.inbox_ack(P, "RM-1", "A1")
        self.assertEqual(sw.step(P, None, tick=False), [])

    def test_free_resource_needs_a_grant_or_auto_and_a_free_lease(self):
        self.row(state="waiting", waiting_for="lab")
        with st.locked(P): st.emit(P, "need", "RM-1", sid(1), resource="lab", minutes=5)
        self.assertEqual(sw.step(P, None, tick=False), [])
        with st.locked(P): st.emit(P, "granted", "RM-1", sid(1), resource="lab")
        with lease.locked() as d:
            lease.write(d, "lab", {"pid": os.getpid(), "pid_start": lease.start_time(os.getpid()), "session": None,
                                   "start": time.time(), "ttl": 60})
        self.assertEqual(sw.step(P, None, tick=False), [])
        (Path(os.environ["AGENTS_LEASE_DIR"]) / "lab.json").unlink()
        self.assertEqual(sw.step(P, None, tick=False), ["free lab for RM-1"])

    def test_a_refused_start_is_retried_only_after_an_owner_touch_or_a_pack_change(self):
        self.pack("RM-1", "RM-2"); (self.fake / "rc-sup-start-worker").write_text("over the cap\n")
        self.assertEqual(sw.step(P, None, tick=False), ["start_refused RM-1", "start_refused RM-2",
                                                       "notified start_refused RM-1", "notified start_refused RM-2"])
        starts = lambda: [l for l in self.argv() if l.startswith("sup start-worker")]
        self.assertEqual(starts()[0], f"sup start-worker RM-1 --profile {P}"); self.assertEqual(len(starts()), 2)
        self.assertEqual(st.events_since(P, 0)[0]["reason"], "refused: over the cap")
        self.assertEqual(sw.step(P, None, tick=False), []); self.assertEqual(len(starts()), 2)
        self.assertEqual(len((st.profile_dir(P) / "watch.log").read_text().splitlines()), 6)  # no line per pass
        st.touch(P, "answered Q1")
        self.assertEqual(sw.step(P, None, tick=False), []); self.assertEqual(len(starts()), 4)  # same reason: no new event
        self.pack("RM-1", "RM-2", "RM-3")
        sw.step(P, None, tick=False); self.assertEqual(len(starts()), 7)
        self.assertEqual(st.events_since(P, 0)[-1]["task"], "RM-3")
        (self.fake / "rc-sup-start-worker").unlink(); st.touch(P, "again")
        self.assertEqual([a for a in sw.step(P, None, tick=False) if a.startswith("started")], ["started RM-1", "started RM-2", "started RM-3"])

    def test_a_failed_claude_start_leaves_no_row_and_the_retry_after_a_touch_starts_the_worker(self):
        self.pack("RM-1"); (self.fake / "bg.fail").write_text("no network")
        self.assertEqual(sw.step(P, None, tick=False), ["start_refused RM-1", "notified start_refused RM-1"])
        self.assertEqual(st.workers(P), []); self.assertIn("no network", st.events_since(P, 0)[0]["reason"])
        (self.fake / "bg.fail").unlink(); self.assertEqual(sw.step(P, None, tick=False), [])
        st.touch(P, "answered Q1")
        self.assertEqual(sw.step(P, None, tick=False), ["started RM-1"])
        self.assertEqual((st.worker_for(P, task="RM-1")["state"], self.kinds()), ("running", ["start_refused", "started"]))

    def test_an_untrusted_workspace_switches_the_profile_to_headless_and_retries_in_the_same_pass(self):
        self.pack("RM-1"); (self.fake / "bg.fail").write_text("")
        self.assertEqual(sw.step(P, None, tick=False), ["started RM-1"])
        self.assertEqual((st.config(P)["worker_mode"], st.worker_for(P, task="RM-1")["mode"]), ("headless", "headless"))
        self.assertIn("worker_mode is now headless", (st.profile_dir(P) / "watch.log").read_text())
        self.pack("RM-1", "RM-2")
        self.assertEqual(sw.step(P, None, tick=False), ["started RM-2"])
        self.assertIn(f"sup start-worker RM-2 --headless --profile {P}", self.argv())  # the config key is passed on

    def test_a_claude_start_failure_is_retried_after_5_then_15_minutes_and_a_task_file_edit_retries_at_once(self):
        self.pack("RM-1"); (self.fake / "bg.fail").write_text("no network")
        todo = self.hub / "docs/tasks_manager/_todos"; todo.mkdir(parents=True); (todo / "RM-1-F_x.md").write_text("a")
        starts = lambda: [l for l in self.argv() if l.startswith("sup start-worker")]
        def age(sec):
            m = json.loads((st.profile_dir(P) / "watch.json").read_text()); m["start_backoff"]["RM-1"]["at"] -= sec
            (st.profile_dir(P) / "watch.json").write_text(json.dumps(m))
        sw.step(P, None, tick=False); sw.step(P, None, tick=False); self.assertEqual(len(starts()), 1)
        age(301); sw.step(P, None, tick=False); self.assertEqual(len(starts()), 2)
        age(301); sw.step(P, None, tick=False); self.assertEqual(len(starts()), 2)  # the second wait is 15 minutes
        age(900); sw.step(P, None, tick=False); self.assertEqual(len(starts()), 3)
        age(10 ** 6); sw.step(P, None, tick=False); self.assertEqual(len(starts()), 3)  # then only on a key change
        (todo / "RM-1-F_x.md").write_text("b"); sw.step(P, None, tick=False); self.assertEqual(len(starts()), 4)
        self.assertEqual(self.kinds().count("start_refused"), 1)  # the owner is told once

    def test_a_session_not_yet_in_agents_is_waited_for_and_one_that_never_shows_is_not_orphaned(self):
        self.pack("RM-1"); (self.fake / "agents.skip").write_text("2")
        self.assertEqual(sw.step(P, None, tick=False), ["started RM-1"])
        self.assertEqual(st.worker_for(P, task="RM-1")["state"], "running")
        st.drop_worker(P, st.worker_for(P, task="RM-1")["session"]); (self.fake / "agents.fail").write_text("")
        st.touch(P, "x")
        acts = sw.step(P, None, tick=False)
        self.assertEqual(acts[0], "start_refused RM-1"); self.assertEqual(st.workers(P), [])
        self.assertEqual(self.claude()[-1]["argv"][0], "stop")

    def test_the_cap_is_never_exceeded_across_a_wake_and_a_start(self):
        st.set_config(P, cap=1); self.pack("RM-1", "RM-2"); self.row(state="stopped"); st.inbox_add(P, "RM-1", "go")
        self.assertEqual(sw.step(P, None, tick=False), ["restarted RM-1"])
        self.assertEqual(len(st.live_workers(P)), 1); self.assertFalse([l for l in self.argv() if "start-worker" in l])
        st.set_worker(P, sid(1), state="stopped"); st.inbox_add(P, "RM-1", "again"); (self.fake / "resume.copy").write_text("")
        self.assertEqual(sw.step(P, None, tick=False), ["wake failed RM-1"])
        self.assertFalse([l for l in self.argv() if "start-worker" in l])  # a row due for a wake keeps its slot

    def test_a_paused_pack_gets_no_start_wake_or_landing_and_an_owner_stop_is_never_woken(self):
        self.pack("RM-1", "RM-2", "RM-3", state="paused")
        self.row(1, "RM-1", state="stopped"); st.inbox_add(P, "RM-1", "go")
        self.row(2, "RM-2", state="done")
        self.assertEqual(sw.step(P, None, tick=False), [])
        self.assertEqual(self.argv(), []); self.assertEqual(self.claude(), [])
        self.pack("RM-1", "RM-2", "RM-3")
        st.set_config(P, land="manual")
        st.set_worker(P, sid(1), stopped_by="owner")
        self.assertEqual(sw.step(P, None, tick=False), ["started RM-3"]); self.assertEqual(self.state(), "stopped")
        self.assertEqual([c for c in self.claude() if "--resume" in c["argv"]], [])

    def test_a_refused_landing_is_retried_only_when_the_branch_tip_changes_or_the_owner_touches(self):
        self.pack("RM-1"); self.row(state="done"); (self.fake / "rc-sup-land").write_text("conflict\n")
        git(self.hub, "branch", "task/RM-1")
        lands = lambda: [l for l in self.argv() if l.startswith("sup land")]
        self.assertEqual(sw.step(P, None, tick=False), ["land_refused RM-1", "notified land_refused RM-1"])
        self.assertEqual(sw.step(P, None, tick=False), []); self.assertEqual(len(lands()), 1)
        git(self.hub, "checkout", "-q", "task/RM-1"); git(self.hub, "commit", "-q", "--allow-empty", "-m", "fix"); git(self.hub, "checkout", "-q", "main")
        self.assertEqual(sw.step(P, None, tick=False)[0], "land_refused RM-1"); self.assertEqual(len(lands()), 2)
        sw.step(P, None, tick=False); self.assertEqual(len(lands()), 2)
        st.touch(P, "answered Q1"); sw.step(P, None, tick=False); self.assertEqual(len(lands()), 3)
        (self.fake / "rc-sup-land").unlink()
        st.touch(P, "again"); self.assertEqual(sw.step(P, None, tick=False), ["landed RM-1", "settled RM-1"])  # the open land_refused entry is closed
        self.assertEqual(self.kinds().count("landed"), 1); self.assertEqual(sw.step(P, None, tick=False), [])

    def test_landing_of_a_done_or_dead_final_worker_when_land_is_auto_and_land_manual_skips(self):
        self.row(state="done"); self.row(2, "RM-2"); self.row(3, "RM-3", restarts=2, alive=False)
        self.assertEqual(sw.step(P, None, tick=False), ["dead RM-3", "landed RM-1", "landed RM-3", "settled RM-3", "notified dead RM-3"])
        self.assertEqual(sw.step(P, None, tick=False), ["settled RM-3"])  # the notice added after the settle is closed next pass
        self.assertEqual(sw.step(P, None, tick=False), []); self.assertEqual(self.kinds().count("landed"), 2)
        self.row(4, "RM-4", state="done"); st.set_config(P, land="manual")
        self.assertEqual(sw.step(P, None, tick=False), [])

    def test_a_blocked_stop_and_ticks_paused_reach_the_owner_without_a_tick(self):
        with st.locked(P):
            st.emit(P, "stopped", "RM-1", sid(1), status="BLOCKED"); st.emit(P, "stopped", "RM-2", sid(2), status="EMPTY")
        self.assertEqual(sw.step(P, None, tick=False), ["notified stopped BLOCKED RM-1"])
        self.assertEqual(self.argv(), [f"notify {P}: stopped BLOCKED RM-1"])
        self.assertEqual(sw.step(P, None, tick=False), [])

    def test_watch_json_is_saved_after_the_step_that_changed_it(self):
        self.pack("RM-1"); (self.fake / "rc-sup-start-worker").write_text("no\n"); seen = []
        def spy(profile, mem, acts): seen.append(json.loads((st.profile_dir(profile) / "watch.json").read_text()))
        old = sw._landing; sw._landing = spy; self.addCleanup(setattr, sw, "_landing", old)
        sw.step(P, None, tick=False)
        self.assertIn("RM-1", seen[0]["start_tried"])  # on disk before the landing step ran

    def test_tick_runs_on_events_not_on_an_empty_log_and_not_with_no_tick(self):
        self.assertEqual(sw.step(P, None), [])
        with st.locked(P): st.emit(P, "ask", "RM-1", sid(1))
        self.assertEqual(sw.step(P, None, tick=False), []); self.assertEqual(self.argv(), [])
        self.assertEqual(sw.step(P, None), ["tick"]); self.assertEqual(self.argv(), [f"sup tick --profile {P}"])
        self.assertFalse((st.profile_dir(P) / "tick.pid").exists())

    def test_no_second_tick_while_one_runs(self):
        with st.locked(P): st.emit(P, "ask", "RM-1", sid(1))
        (st.profile_dir(P) / "tick.pid").write_text(f"{os.getpid()}\n")
        self.assertEqual(sw.step(P, None), [])

    def test_three_failed_ticks_pause_until_an_owner_touch(self):
        with st.locked(P): st.emit(P, "ask", "RM-1", sid(1))
        ticks = lambda: [l for l in self.argv() if l.startswith("sup tick")]
        (self.fake / "rc-sup-tick").write_text("boom\n")
        self.assertEqual(sw.step(P, None), ["tick_failed"]); self.assertEqual(sw.step(P, None), ["tick_failed"])
        self.assertEqual(sw.step(P, None), ["tick_failed", "ticks_paused"])
        self.assertEqual(sw.step(P, None), ["notified ticks_paused"]); self.assertEqual(sw.step(P, None), [])
        self.assertEqual(self.kinds().count("ticks_paused"), 1); self.assertEqual(len(ticks()), 3)
        st.touch(P, "answered Q1")
        self.assertEqual(sw.step(P, None), ["tick_failed"]); self.assertEqual(len(ticks()), 4)

    def test_a_good_tick_resets_the_failure_count(self):
        with st.locked(P): st.emit(P, "ask", "RM-1", sid(1))
        rc = self.fake / "rc-sup-tick"; rc.write_text("boom\n")
        sw.step(P, None); sw.step(P, None); rc.unlink()
        self.assertEqual(sw.step(P, None), ["tick"]); rc.write_text("boom\n")
        self.assertEqual(sw.step(P, None), ["tick_failed"]); self.assertEqual(sw.step(P, None), ["tick_failed"])

    def test_a_tick_past_the_timeout_is_killed_and_fails(self):
        with st.locked(P): st.emit(P, "ask", "RM-1", sid(1))
        (self.fake / "sleep-sup-tick").write_text("30"); sw.TICK_TIMEOUT = 0.5
        t0 = time.time(); self.assertEqual(sw.step(P, None), ["tick_failed"]); self.assertLess(time.time() - t0, 10)


class Process(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        t = Path(self.tmp.name)
        self.old = dict(os.environ); self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self.old)))
        os.environ.update(AGENTS_SUP_DIR=str(t / "sup"), AGENTS_LEASE_DIR=str(t / "leases"))
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
        # fail in the lease step: the lease directory is below a plain file
        blocker = Path(self.tmp.name) / "blocker"; blocker.write_text("x")
        os.environ["AGENTS_LEASE_DIR"] = str(blocker / "leases")
        self.assertEqual(sw.cmd_start(self.args()), 0)
        time.sleep(2.5)
        self.assertTrue(sw.running_pid(P))
        self.assertGreaterEqual((st.profile_dir(P) / "watch.log").read_text().count("pass failed"), 2)


if __name__ == "__main__":
    unittest.main()
