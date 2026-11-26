"""`at run-guard watch` (plugins/agents-core/lib/run_watch.py) against a fake `claude` on PATH."""
import json, os, pathlib, shutil, signal, subprocess, sys, tempfile, time, unittest
ROOT = pathlib.Path(__file__).resolve().parents[2]
AT = ROOT / "plugins/agents-core/bin/at"
sys.path.insert(0, str(ROOT / "plugins/agents-core/lib"))
import run_watch  # noqa: E402

TASK = """| Field | Value |
|---|---|
| Task ID | {tid} |
| Execution | {execution} |

## Fixture task

### Unattended run

Checked: 2026-11-26, READY
{watch}
{bypass}
### Phases
"""
# the fake records time, cwd, a leaked session id and argv; the FAKE_* switches play a resumed session:
# FAKE_REARM re-arms with bigger caps (its own pid, which dies with it), FAKE_KILL_WATCHER kills the
# watcher, FAKE_SLEEP keeps it running, FAKE_FINISH archives the task (the run is done)
FAKE = """#!/bin/bash
echo "$(date +%s.%N)|$PWD|${{CLAUDE_CODE_SESSION_ID:-none}}|$*" >> "{calls}"
[ -z "$FAKE_REARM" ] || CLAUDE_PID=$$ "{at}" run-guard arm --session s1 --watch --max-resumes 9 --budget-usd 1000 --allow-bypass TST-001 >/dev/null 2>&1
[ -z "$FAKE_KILL_WATCHER" ] || kill "$(cat "$AGENTS_RUN_GUARD_DIR/s1.watch")"
[ -z "$FAKE_SLEEP" ] || sleep "$FAKE_SLEEP"
[ -z "$FAKE_FINISH" ] || mv docs/tasks_manager/_todos/TST-001-*.md docs/tasks_manager/_todos_archived/
date +%s.%N >> "{calls}.end"
"""


def wait_for(pred, seconds=2.0):
    end = time.time() + seconds
    while time.time() < end:
        if pred():
            return True
        time.sleep(0.05)
    return pred()


class Watch(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.repo, self.guard, self.bin = self.tmp / "repo", self.tmp / "guard", self.tmp / "bin"
        for d in ("docs/tasks_manager/_todos", "docs/tasks_manager/_todos_archived", "docs/tasks_manager/_runs/TST-001"):
            (self.repo / d).mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.guard.mkdir(mode=0o700); self.bin.mkdir()
        self.task()
        (self.repo / "docs/tasks_manager/_runs/TST-001/state.md").write_text("| Phase | Status |\n|---|---|\n| 1 | pending |\n")
        self.calls, self.notes = self.tmp / "calls", self.tmp / "notes"
        (self.bin / "claude").write_text(FAKE.format(calls=self.calls, at=AT))
        (self.tmp / "notify.sh").write_text('#!/bin/sh\necho "$1" >> "%s"\n' % self.notes)
        for f in (self.bin / "claude", self.tmp / "notify.sh"):
            f.chmod(0o755)
        self.procs = []
        self.env = dict(os.environ, PATH=f"{self.bin}:{os.environ['PATH']}", AGENTS_RUN_GUARD_DIR=str(self.guard),
                        AGENTS_NOTIFY_CMD=str(self.tmp / "notify.sh"), CLAUDE_CODE_SESSION_ID="leak")
        self.env.pop("CLAUDE_PID", None)

    def tearDown(self):
        self.reset()
        for p in self.procs:
            p.kill(); p.wait()
        for pid in self.fake_pids():
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    def fake_pids(self):
        out = subprocess.run(["pgrep", "-f", str(self.bin / "claude")], capture_output=True, text=True).stdout
        return [int(x) for x in out.split()]

    def reset(self):
        subprocess.run([str(AT), "run-guard", "disarm", "--session", "s1"], env=self.env, capture_output=True, timeout=10)
        self.calls.unlink(missing_ok=True); self.notes.unlink(missing_ok=True)

    def task(self, execution="unattended, orchestrated", watch="Watch: on", bypass="", tid="TST-001"):
        (self.repo / f"docs/tasks_manager/_todos/{tid}-F_x.md").write_text(TASK.format(tid=tid, execution=execution, watch=watch, bypass=bypass))

    def dead_pid(self):
        p = subprocess.Popen(["true"]); p.wait(); return p.pid

    def live(self, name="claude"):
        """A live process whose argv[0] is <dir>/<name>: named claude it is a session, otherwise a reused pid."""
        d = self.tmp / ("live-" + name); d.mkdir(exist_ok=True)
        (d / name).write_text('#!/bin/bash\nexec -a "$0" sleep 30\n'); (d / name).chmod(0o755)
        p = subprocess.Popen([str(d / name)]); self.procs.append(p)
        self.assertTrue(wait_for(lambda: pathlib.Path(f"/proc/{p.pid}/cmdline").read_bytes().startswith(str(d).encode())))
        return p

    def marker(self, pid, status="kind=WAITING\nmode=acceptEdits\n", task=True, cwd=None, extra=()):
        lines = [f"task\t{self.repo}\tTST-001"] if task else []
        lines += [*extra, f"meta\tpid\t{pid}", f"meta\tcwd\t{cwd or self.repo}"]
        (self.guard / "s1").write_text("\n".join(lines) + "\n")
        (self.guard / "s1.status").write_text(status)

    def watch(self, *flags, **env):
        return subprocess.run([str(AT), "run-guard", "watch", "--session", "s1", "--interval", "0.1", "--pause", "0", *flags],
                              cwd=self.repo, env=dict(self.env, **env), capture_output=True, text=True, timeout=20)

    def watch_once(self, *flags):
        """Start a watcher, let it tick once, and stop it (SIGTERM): its record stays behind."""
        p = subprocess.Popen([str(AT), "run-guard", "watch", "--session", "s1", "--interval", "0.1", *flags],
                             cwd=self.repo, env=self.env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.assertTrue(wait_for(lambda: self.log().count("watching") > self.ticks))
        time.sleep(0.3); p.terminate(); p.wait(); self.ticks += 1

    ticks = 0

    def lines(self, path):
        return path.read_text().split("\n")[:-1] if path.exists() else []

    def argv(self):
        return [c.split("|", 3)[3] for c in self.lines(self.calls)]

    def log(self):
        return (self.guard / "s1.watch.log").read_text() if (self.guard / "s1.watch.log").exists() else ""

    def record(self):
        return json.loads((self.guard / "s1.watch.state").read_text())

    def test_dead_pid_resumes_once_then_reports_finished(self):
        self.marker(self.dead_pid())
        p = self.watch(FAKE_FINISH="1"); self.assertEqual(p.returncode, 0, p.stderr)
        calls = self.lines(self.calls); self.assertEqual(len(calls), 1, calls)
        self.assertTrue(calls[0].split("|", 1)[1].startswith(f"{self.repo}|none|--resume s1 -p --permission-mode acceptEdits "
                                                             "--max-budget-usd 1.00 -- Run guard watchdog:"), calls[0])
        self.assertEqual([n.split(":")[0] for n in self.lines(self.notes)], ["Run restarted (1/4)", "Run finished",
                                                                            "Morning report not written"])  # the fixture state is no real run
        self.assertFalse((self.guard / "s1.watch").exists()); self.assertFalse((self.guard / "s1.watch.state").exists())
        self.assertIn("report TST-001: exited", self.log())

    def test_the_report_is_written_in_the_runs_repository_wherever_the_watcher_started(self):
        self.marker(self.dead_pid())
        state = self.repo / "docs/tasks_manager/_runs/TST-001/state.md"
        state.unlink()
        todo = self.repo / "docs/tasks_manager/_todos/TST-001-F_x.md"
        todo.write_text(todo.read_text() + "\n#### Phase 1: one\n\n- [x] done\n")
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base", "--allow-empty"],
                       cwd=self.repo, check=True)
        p = subprocess.run([str(AT), "task", "run-state", "init", "TST-001", "--base", "HEAD", "--branch", "main",
                            "--work-mode", "default-branch", "--autonomy", "L1"], cwd=self.repo, env=self.env,
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        state.write_text(state.read_text().replace("| pending | 0 |", "| committed | 1 |"))
        todo.rename(self.repo / "docs/tasks_manager/_todos_archived" / todo.name)  # the run is done
        p = subprocess.run([str(AT), "run-guard", "watch", "--session", "s1", "--interval", "0.1"], cwd=self.tmp,
                           env=self.env, capture_output=True, text=True, timeout=20)
        self.assertEqual(p.returncode, 0, p.stderr); self.assertIn("report TST-001: exited 0", self.log())
        self.assertEqual(len(list((self.repo / "docs/tasks_manager/_reports").glob("*-TST-001.md"))), 1)

    def test_a_reused_pid_counts_as_dead(self):
        self.marker(self.live("sleeper").pid)
        self.assertEqual(self.watch(FAKE_FINISH="1").returncode, 0); self.assertEqual(len(self.argv()), 1)

    def test_live_session_is_never_resumed_idle_is_notified_once_and_until_ends_it(self):
        self.marker(self.live().pid)
        start = time.time(); p = self.watch("--idle", "0", "--until", "+1")
        self.assertEqual(p.returncode, 0, p.stderr); self.assertLess(time.time() - start, 5)
        self.assertEqual(self.argv(), []); self.assertEqual(self.lines(self.notes), ["Run idle: TST-001"])
        self.assertIn("--until passed", self.log())

    def test_blocked_is_not_resumed_and_shares_the_hooks_key(self):
        self.marker(self.dead_pid(), "kind=BLOCKED\ntext=pick a name\nkind=DONE\nmode=acceptEdits\n")
        self.assertEqual(self.watch().returncode, 0); self.assertEqual(self.argv(), [])
        key = subprocess.run(["cksum"], input=b"BLOCKED pick a name", capture_output=True).stdout.split()[0].decode()
        self.assertTrue((self.guard / f"s1.sent/blocked-{key}").exists(), list((self.guard / "s1.sent").iterdir()))
        self.assertEqual(self.lines(self.notes), ["Run BLOCKED: TST-001 pick a name"])

    def test_finished_is_not_sent_twice_when_the_hook_sent_it(self):
        self.marker(self.dead_pid(), "kind=DONE\n")
        key = subprocess.run(["cksum"], input=b"DONE nothing is open", capture_output=True).stdout.split()[0].decode()
        (self.guard / "s1.sent").mkdir(); (self.guard / f"s1.sent/done-{key}").touch()
        self.assertEqual(self.watch().returncode, 0)  # only the report failure (the fixture state is no real run)
        self.assertEqual([n.split(":")[0] for n in self.lines(self.notes)], ["Morning report not written"])
        self.assertEqual(run_watch.hook_key("DONE", "nothing is open"), f"done-{key}")

    def test_the_resume_cap_holds_and_the_budget_is_divided_and_floored(self):
        self.marker(self.dead_pid())
        self.assertEqual(self.watch("--max-resumes", "3", "--budget-usd", "0.2").returncode, 0)
        argv = self.argv(); self.assertEqual(len(argv), 3, argv)
        self.assertTrue(all("--max-budget-usd 0.06 " in a for a in argv), argv)
        self.assertEqual([n for n in self.lines(self.notes) if n.startswith("Run gave up")], ["Run gave up: TST-001"])

    def test_finding1_a_rearm_with_bigger_caps_cannot_reset_the_cap(self):
        self.marker(self.dead_pid())
        self.assertEqual(self.watch("--max-resumes", "2", "--budget-usd", "2", FAKE_REARM="1").returncode, 0)
        time.sleep(1)  # a watcher the re-arm might have started would restart again by now
        argv = self.argv(); self.assertEqual(len(argv), 2, argv)
        self.assertTrue(all("--max-budget-usd 1.00 " in a for a in argv), argv)
        self.assertEqual([n for n in self.lines(self.notes) if n.startswith("Run gave up")], ["Run gave up: TST-001"])

    def test_finding1_watchers_in_a_row_share_one_count(self):
        self.marker(self.dead_pid())
        for i in range(4):  # each restart kills its watcher; later watchers ask for more and get the record's 3
            self.watch("--max-resumes", "3" if i == 0 else "9", FAKE_KILL_WATCHER="1")
            wait_for(lambda: not self.fake_pids())
        self.assertEqual(len(self.argv()), 3, self.argv())
        self.assertEqual(self.record()["used"], 3)
        self.assertEqual([n for n in self.lines(self.notes) if n.startswith("Run gave up")], ["Run gave up: TST-001"])

    def test_finding2_bypass_cannot_be_added_by_a_later_watcher(self):
        self.task(bypass="allow bypass"); self.marker(self.live().pid)
        self.watch_once()  # the first arm: no --allow-bypass
        self.marker(self.dead_pid(), "kind=WAITING\nmode=bypassPermissions\n")
        self.assertEqual(self.watch("--allow-bypass").returncode, 0); self.assertEqual(self.argv(), [])
        self.assertEqual(self.lines(self.notes), ["Run not restarted: TST-001"])

    def test_finding3_a_planted_sent_key_cannot_silence_the_watcher(self):
        self.marker(self.dead_pid())
        for event in ("restarted-1", "gave-up", "idle"):
            subprocess.run([str(AT), "notify", "all fine", "--event", event, "--session", "s1"], input="", text=True, env=self.env)
        self.notes.unlink()
        self.assertEqual(self.watch("--max-resumes", "1").returncode, 0)
        self.assertEqual(self.lines(self.notes), ["Run restarted (1/1): TST-001", "Run gave up: TST-001"])
        self.assertIn("notify gave-up (Run gave up: TST-001): exited 0", self.log())

    def test_finding4_a_new_watcher_waits_for_a_restart_still_running(self):
        self.marker(self.dead_pid())
        self.watch("--max-resumes", "3", FAKE_KILL_WATCHER="1", FAKE_SLEEP="3")
        self.assertTrue(wait_for(lambda: self.record()["child"] is not None))
        self.assertEqual(self.watch(FAKE_FINISH="1").returncode, 0)  # restarts once the first restart has ended
        starts = [float(c.split("|")[0]) for c in self.lines(self.calls)]
        ends = [float(x) for x in self.lines(pathlib.Path(f"{self.calls}.end"))]
        self.assertEqual(len(starts), 2, starts); self.assertGreater(starts[1], ends[0])

    def test_finding5_no_targets_or_an_unread_target_is_never_finished(self):
        self.marker(self.dead_pid(), "kind=DONE\n", task=False)
        self.assertEqual(self.watch("--until", "+0.5").returncode, 0); self.assertEqual(self.lines(self.notes), [])
        self.assertTrue((self.guard / "s1.watch.state").exists())
        if os.geteuid() == 0:
            self.skipTest("root reads a mode-000 file")
        self.reset(); state = self.repo / "docs/tasks_manager/_runs/TST-001/state.md"
        self.marker(self.dead_pid(), "kind=WAITING\n", task=False, extra=[f"state\t{state}"]); state.chmod(0)
        try:
            self.assertEqual(self.watch("--until", "+0.5", "--idle", "0").returncode, 0)
        finally:
            state.chmod(0o600)
        self.assertEqual(self.lines(self.notes), ["Run idle: "]); self.assertEqual(self.argv(), [])

    def test_finding11_the_mode_comes_from_the_record_when_status_is_gone(self):
        self.marker(self.live().pid, "kind=WAITING\nmode=plan\n")
        self.watch_once()
        self.marker(self.dead_pid()); (self.guard / "s1.status").unlink()
        self.assertEqual(self.watch(FAKE_FINISH="1").returncode, 0)
        self.assertIn("--permission-mode plan ", self.argv()[0])

    def test_a_task_no_longer_marked_is_not_resumed(self):
        for execution, watch in (("orchestrated", "Watch: on"), ("unattended-ish", "Watch: on"), ("unattended", "Watch: off"),
                                 ("unattended", ""), ("unattended", "Watch: on\nWatch: off"), ("unattended", "Watch: off\nWatch: on")):
            with self.subTest(execution=execution, watch=watch):
                self.reset(); self.task(execution, watch); self.marker(self.dead_pid())
                self.assertEqual(self.watch().returncode, 0); self.assertEqual(self.argv(), [])
                self.assertEqual(self.lines(self.notes), ["Run not restarted: TST-001"])
                self.assertIn("notify refused-unmarked (", self.log())

    def test_bypass_needs_the_flag_and_a_line_in_every_open_task(self):
        cases = (("bypassPermissions", "", [], False), ("bypassPermissions", "allow bypass", [], False),
                 ("bypassPermissions", "", ["--allow-bypass"], False), ("dontAsk", "allow bypass", ["--allow-bypass"], False),
                 ("bypassPermissions", "allow bypass", ["--allow-bypass"], True))
        for mode, line, flags, resumes in cases:
            with self.subTest(mode=mode, line=line, flags=flags):
                self.reset(); self.task(bypass=line); self.marker(self.dead_pid(), f"kind=WAITING\nmode={mode}\n")
                self.assertEqual(self.watch(*flags, FAKE_FINISH="1" if resumes else "").returncode, 0)
                if resumes:
                    self.assertEqual(len(self.argv()), 1); self.assertIn("--permission-mode bypassPermissions ", self.argv()[0])
                    (self.repo / "docs/tasks_manager/_todos_archived/TST-001-F_x.md").rename(self.repo / "docs/tasks_manager/_todos/TST-001-F_x.md")
                else:
                    self.assertEqual(self.argv(), []); self.assertIn("notify refused-mode (", self.log())
        self.reset(); self.task(bypass="allow bypass"); self.task(bypass="", tid="TST-002")
        self.marker(self.dead_pid(), "kind=WAITING\nmode=bypassPermissions\n", extra=[f"task\t{self.repo}\tTST-002"])
        self.assertEqual(self.watch("--allow-bypass").returncode, 0); self.assertEqual(self.argv(), [])

    def test_a_state_only_marker_or_a_cwd_without_a_guarded_file_is_never_resumed(self):
        self.marker(self.dead_pid(), task=False, extra=[f"state\t{self.repo}/docs/tasks_manager/_runs/TST-001/state.md"])
        self.assertEqual(self.watch().returncode, 0); self.assertIn("notify refused-state-only (", self.log())
        other = self.tmp / "elsewhere"; subprocess.run(["git", "init", "-q", str(other)], check=True)
        for extra in ((), (f"state\t{other}/no/such/state.md",)):  # a git tree, but no EXISTING guarded file in it
            with self.subTest(extra=extra):
                self.reset(); self.marker(self.dead_pid(), cwd=other, extra=extra)
                self.assertEqual(self.watch().returncode, 0); self.assertIn("notify refused-cwd (", self.log())
        self.assertEqual(self.argv(), [])

    def test_the_pause_doubles(self):
        self.marker(self.dead_pid())
        self.assertEqual(self.watch("--max-resumes", "3", "--pause", "0.1").returncode, 0)
        self.assertEqual(len(self.argv()), 3)
        for n, pause in ((1, "0.1"), (2, "0.2"), (3, "0.4")):
            self.assertIn(f"restart {n} after a pause of {pause} s", self.log())

    def test_a_watcher_that_exits_logs_the_restart_it_leaves_running(self):
        self.marker(self.dead_pid())
        p = subprocess.Popen([str(AT), "run-guard", "watch", "--session", "s1", "--interval", "0.1", "--pause", "0"],
                             cwd=self.repo, env=dict(self.env, FAKE_SLEEP="3"), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.assertTrue(wait_for(lambda: self.calls.exists())); time.sleep(0.2); p.terminate(); p.wait()
        self.assertRegex(self.log(), r"exiting; restart pid \d+ is still running")

    def test_arm_watch_attaches_one_detached_watcher_that_rearm_keeps_and_disarm_stops(self):
        env = dict(self.env, CLAUDE_PID=str(self.live().pid))
        arm = lambda *a: subprocess.run([str(AT), "run-guard", "arm", "--session", "s1", *a, "TST-001"], cwd=self.repo,
                                        env=env, capture_output=True, text=True, timeout=10)
        p = arm("--watch", "--interval", "0.1", "--budget-usd=2"); self.assertEqual(p.returncode, 0, p.stderr)
        pid = int((self.guard / "s1.watch").read_text()); self.assertTrue(run_watch.is_watcher(pid, "s1"))
        self.assertIn("meta\twatch\ton --interval=0.1 --budget-usd=2.0", (self.guard / "s1").read_text())
        self.assertEqual(arm().returncode, 0)  # a resumed session re-arms without --watch
        p = arm("--watch", "--max-resumes", "9"); self.assertIn("already running", p.stdout)  # ... or with it
        self.assertEqual(int((self.guard / "s1.watch").read_text()), pid)
        self.assertIn("meta\twatch\ton", (self.guard / "s1").read_text())
        status = subprocess.run([str(AT), "run-guard", "status", "--session", "s1"], env=env, capture_output=True, text=True).stdout
        self.assertIn(f"watcher pid {pid} is running", status); self.assertIn("watch record: 0 of 4 restarts used, budget 2.0", status)
        self.assertEqual(self.watch().returncode, 0); self.assertIn("another watcher", self.log())
        for temp in ("s1.watch.state.123", "s1.arm.456", "s1.status.789"):  # left by a writer killed mid-write
            (self.guard / temp).touch()
        subprocess.run([str(AT), "run-guard", "disarm", "--session", "s1"], env=env, capture_output=True, timeout=10)
        self.assertTrue(wait_for(lambda: not run_watch.is_watcher(pid, "s1")))
        self.assertEqual(sorted(x.name for x in self.guard.iterdir()), [])

    def test_two_racing_arm_watch_calls_leave_one_watcher_and_both_succeed(self):
        env = dict(self.env, CLAUDE_PID=str(self.live().pid))
        cmd = [str(AT), "run-guard", "arm", "--session", "s1", "--watch", "--interval", "0.1", "TST-001"]
        ps = [subprocess.Popen(cmd, cwd=self.repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
        outs = [p.communicate(timeout=10) for p in ps]
        self.assertEqual([p.returncode for p in ps], [0, 0], outs)
        self.assertTrue(all("is running" in o or "already running" in o for o, _ in outs), outs)
        time.sleep(0.3)
        watchers = [int(x) for x in subprocess.run(["pgrep", "-f", "run-guard watch --session s1"], capture_output=True, text=True).stdout.split()]
        mine = f"AGENTS_RUN_GUARD_DIR={self.guard}".encode()  # another run of this suite has watchers of its own "s1"
        def ours(w):
            try:
                return mine in pathlib.Path(f"/proc/{w}/environ").read_bytes().split(b"\0")
            except OSError:
                return False
        self.assertEqual(len([w for w in watchers if run_watch.is_watcher(w, "s1") and ours(w)]), 1, watchers)

    def test_disarm_never_signals_a_pid_that_is_not_the_watcher(self):
        other = self.live(); self.marker(other.pid); (self.guard / "s1.watch").write_text(f"{other.pid}\n")
        subprocess.run([str(AT), "run-guard", "disarm", "--session", "s1"], env=self.env, capture_output=True, timeout=10)
        time.sleep(0.2); self.assertIsNone(other.poll())

    def test_is_watcher_needs_watch_session_id_adjacent(self):
        loose = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)", "run-guard", "watch", "--interval", "s1"])
        exact = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)", "run-guard", "watch", "--session", "s1"])
        self.procs += [loose, exact]
        self.assertTrue(wait_for(lambda: run_watch.is_watcher(exact.pid, "s1")))
        self.assertFalse(run_watch.is_watcher(loose.pid, "s1"))

    def test_bad_pids_are_unknown_never_a_traceback(self):
        self.marker("²"); (self.guard / "s1.watch").write_text("²\n")
        for args in (["status"], ["watch", "--until", "+0.3", "--interval", "0.1"], ["disarm"]):
            p = subprocess.run([str(AT), "run-guard", *args, "--session", "s1"], cwd=self.repo, env=self.env, capture_output=True, text=True, timeout=10)
            self.assertEqual(p.returncode, 0, (args, p.stderr)); self.assertNotIn("Traceback", p.stderr)
        self.assertEqual(self.argv(), [])

    def test_usage_errors(self):
        for args in (["--allow-bypass"], ["--watch", "--interval", "0"], ["--watch", "--until", "25:00"],
                     ["--watch", "--budget-usd", "0.01", "--max-resumes", "4"]):
            p = subprocess.run([str(AT), "run-guard", "arm", "--session", "s1", *args, "TST-001"], cwd=self.repo,
                               env=self.env, capture_output=True, text=True)
            self.assertEqual(p.returncode, 2, (args, p.stderr)); self.assertFalse((self.guard / "s1").exists())
        for action in (["arm", "TST-001"], ["watch"], ["disarm"]):  # an id never starts with `-` or `.`
            for session in (".hidden", "-x"):
                p = subprocess.run([str(AT), "run-guard", *action, "--session", session], cwd=self.repo, env=self.env,
                                   capture_output=True, text=True, timeout=10)
                self.assertEqual(p.returncode, 3, (action, session, p.stderr))

    def test_item1_the_events_that_end_a_watcher_are_said_by_every_watcher(self):
        self.task(watch="Watch: off"); self.marker(self.dead_pid())
        self.watch(); self.watch()  # refused-*: both watchers say so
        self.assertEqual(self.lines(self.notes), ["Run not restarted: TST-001"] * 2)
        self.reset(); self.task(); self.marker(self.dead_pid())
        self.assertEqual(self.watch("--max-resumes", "1").returncode, 0)
        self.assertEqual(self.watch().returncode, 0)  # the session died again after a resume by hand
        self.assertEqual([n for n in self.lines(self.notes) if n.startswith("Run gave up")], ["Run gave up: TST-001"] * 2)
        env = dict(self.env, CLAUDE_PID=str(self.live().pid))
        p = subprocess.run([str(AT), "run-guard", "arm", "--session", "s1", "--watch", "--interval", "0.1", "TST-001"],
                           cwd=self.repo, env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(p.returncode, 0, p.stderr); self.assertIn("0 of 1 restarts left", p.stdout)
        self.assertIn("the watcher only reports", p.stderr); self.assertIn("`at run-guard disarm`, then", p.stderr)
        p = subprocess.run([str(AT), "run-guard", "arm", "--session", "s1", "--watch", "TST-001"], cwd=self.repo,
                           env=env, capture_output=True, text=True, timeout=10)
        self.assertIn("the caps of a live watcher are kept", p.stdout); self.assertIn("0 of 1 restarts left", p.stdout)

    def test_item3_until_and_idle_belong_to_each_watcher(self):
        self.marker(self.live().pid)
        self.assertEqual(self.watch("--until", "+0.3", "--idle", "0").returncode, 0)
        self.assertNotIn("until", self.record()); self.assertNotIn("idle", self.record())
        self.notes.unlink(); rec = self.record(); rec["sent"] = []  # so a recorded --idle 0 would say idle again
        (self.guard / "s1.watch.state").write_text(json.dumps(rec))
        start = time.time(); self.assertEqual(self.watch("--until", "+1").returncode, 0)
        self.assertGreaterEqual(time.time() - start, 1)  # a passed --until of an earlier watcher is not kept
        self.assertEqual(self.lines(self.notes), [])  # nor its --idle 0

    def test_item4_the_floor_holds_on_the_merged_caps(self):
        self.marker(self.live().pid); self.watch_once("--max-resumes", "20", "--budget-usd", "20")
        self.marker(self.dead_pid())
        p = self.watch("--budget-usd", "0.04")  # 0.01 each over 4 restarts, but the record allows 20: 0.002
        self.assertEqual(p.returncode, 2); self.assertEqual(len(p.stderr.strip().split("\n")), 1, p.stderr)
        self.assertIn("less than 0.01 USD per restart", p.stderr); self.assertEqual(self.argv(), [])
        before = (self.guard / "s1").read_text()  # `arm --watch` says so itself, and arms nothing
        p = subprocess.run([str(AT), "run-guard", "arm", "--session", "s1", "--watch", "--budget-usd", "0.04", "TST-001"],
                           cwd=self.repo, env=self.env, capture_output=True, text=True, timeout=10)
        self.assertEqual(p.returncode, 2, p.stderr); self.assertIn("less than 0.01 USD per restart", p.stderr)
        self.assertEqual((self.guard / "s1").read_text(), before); self.assertFalse((self.guard / "s1.watch").exists())

    def test_item5_6_a_damaged_or_out_of_range_record_leaves_no_restarts(self):
        good = {"max_resumes": 2, "budget_usd": 2, "allow_bypass": False, "used": 0, "child": None, "mode": "", "sent": []}
        for bad in ("{not json", {**good, "used": -50}, {**good, "max_resumes": 99}, {**good, "budget_usd": 0},
                    {**good, "child": -1}, {**good, "used": "0"}):
            with self.subTest(bad=bad):
                self.reset(); self.marker(self.dead_pid())
                (self.guard / "s1.watch.state").write_text(bad if isinstance(bad, str) else json.dumps(bad))
                self.assertEqual(self.watch().returncode, 0); self.assertEqual(self.argv(), [])
                self.assertEqual(self.lines(self.notes), ["Run gave up: TST-001"])

    def test_item8_no_cksum_on_path_refuses_to_start(self):
        farm = self.tmp / "farm"; farm.mkdir()
        for tool in ("bash", "env", "dirname", "readlink", "python3", "git", "sh"):
            (farm / tool).symlink_to(shutil.which(tool))
        env = dict(self.env, PATH=str(farm), CLAUDE_PID=str(self.live().pid))
        for args in (["arm", "--watch", "TST-001"], ["watch", "--until", "+1", "--interval", "0.1"]):
            p = subprocess.run([str(AT), "run-guard", *args, "--session", "s1"], cwd=self.repo, env=env,
                               capture_output=True, text=True, timeout=10)
            self.assertEqual(p.returncode, 2, (args, p.stderr)); self.assertIn("cksum", p.stderr)
            self.assertFalse((self.guard / "s1.watch").exists())
        self.assertFalse((self.guard / "s1").exists())

    def test_w1_a_stale_blocked_does_not_switch_the_watchdog_off(self):
        self.marker(self.dead_pid(), "kind=BLOCKED\ntext=pick a name\n")
        later = time.time() + 30  # the owner answered and the session worked on: a guarded file changed after the stop
        os.utime(self.repo / "docs/tasks_manager/_runs/TST-001/state.md", (later, later))
        self.assertEqual(self.watch(FAKE_FINISH="1").returncode, 0); self.assertEqual(len(self.argv()), 1)
        self.assertNotIn("Run BLOCKED: TST-001 pick a name", self.lines(self.notes))  # a fresh one still says so (above)

    def test_w2_only_the_report_runs_in_the_markers_cwd(self):
        self.marker(self.dead_pid(), cwd=self.tmp / "gone")  # missing: notify must still be delivered
        self.assertEqual(self.watch().returncode, 0)
        self.assertEqual(self.lines(self.notes), ["Run not restarted: TST-001"])
        other, evil = self.tmp / "other", self.tmp / "evil"
        subprocess.run(["git", "init", "-q", str(other)], check=True)
        subprocess.run(["git", "config", "agents.notifyCommand", str(self.tmp / "notify.sh")], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "agents.notifyCommand", f"touch {evil} #"], cwd=other, check=True)
        self.reset(); self.marker(self.dead_pid(), cwd=other); self.env.pop("AGENTS_NOTIFY_CMD")
        self.assertEqual(self.watch().returncode, 0)
        self.assertEqual(self.lines(self.notes), ["Run not restarted: TST-001"]); self.assertFalse(evil.exists())

    def test_w3_a_closed_out_run_keeps_its_committed_report(self):
        self.marker(self.dead_pid())
        reports = self.repo / "docs/tasks_manager/_reports"; reports.mkdir()
        (reports / "2026-11-26-TST-001.md").write_text("the committed morning report\n")
        (self.repo / "docs/tasks_manager/_todos/TST-001-F_x.md").rename(self.repo / "docs/tasks_manager/_todos_archived/TST-001-F_x.md")
        shutil.rmtree(self.repo / "docs/tasks_manager/_runs/TST-001")  # closeout
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
        subprocess.run([*git, "add", "-A"], cwd=self.repo, check=True)
        subprocess.run([*git, "commit", "-qm", "closeout"], cwd=self.repo, check=True)
        self.assertEqual(self.watch().returncode, 0); self.assertEqual(self.lines(self.notes), ["Run finished: TST-001"])
        self.assertEqual((reports / "2026-11-26-TST-001.md").read_text(), "the committed morning report\n")
        self.assertEqual(subprocess.run(["git", "status", "--porcelain"], cwd=self.repo, capture_output=True, text=True).stdout, "")
        self.assertNotIn("report", self.log().replace("morning report", ""))

    def test_w4_a_truncated_state_file_is_not_finished(self):
        state = self.repo / "docs/tasks_manager/_runs/TST-001/state.md"
        for text in ("", "| Phase | Status |\n|---|---|\n"):
            with self.subTest(text=text):
                state.write_text(text); self.reset()
                self.marker(self.live().pid, "kind=WAITING\n", task=False, extra=[f"state\t{state}"])
                self.assertEqual(self.watch("--until", "+0.5").returncode, 0); self.assertEqual(self.lines(self.notes), [])
        self.assertFalse(run_watch.scan({"tasks": [], "states": [str(state)], "meta": {}})["complete"])

    def test_w5_a_failed_report_is_notified(self):
        self.marker(self.dead_pid())
        (self.repo / "docs/tasks_manager/_reports").write_text("a file, so no report can be written there\n")
        (self.repo / "docs/tasks_manager/_todos/TST-001-F_x.md").rename(self.repo / "docs/tasks_manager/_todos_archived/TST-001-F_x.md")
        self.assertEqual(self.watch().returncode, 0)
        self.assertEqual(self.lines(self.notes), ["Run finished: TST-001",
                                                  "Morning report not written: run `at task report TST-001`"])

    def test_until_hh_mm_is_the_next_such_time(self):
        now = time.mktime((2026, 11, 26, 10, 0, 0, 0, 0, -1))
        self.assertEqual(run_watch.deadline("10:30", now) - now, 1800)
        self.assertEqual(run_watch.deadline("09:00", now) - now, 23 * 3600)
        self.assertIsNone(run_watch.deadline("9:00", now))


if __name__ == "__main__":
    unittest.main()
