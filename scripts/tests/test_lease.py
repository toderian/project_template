"""`at lease` (plugins/agents-core/lib/lease.py) and the host-wide high-water mark of `at reserve`."""
import json, os, pathlib, subprocess, sys, tempfile, time, unittest
ROOT = pathlib.Path(__file__).resolve().parents[2]
AT = str(ROOT / "plugins/agents-core/bin/at")
RESERVE = ROOT / "plugins/agents-tasks/skills/task-ledger/scripts/reserve_work_item.sh"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = pathlib.Path(self.tmp.name) / "leases"
        self.env = {k: v for k, v in os.environ.items()
                    if k not in ("CLAUDE_CODE_SESSION_ID", "CLAUDE_PID", "AGENTS_LEASE_OWNER")}
        self.env.update(AGENTS_LEASE_DIR=str(self.dir), XDG_STATE_HOME=str(pathlib.Path(self.tmp.name) / "state"))

    def at(self, *args, env=None, **kw):
        return subprocess.run([AT, "lease", *args], env={**self.env, **(env or {})}, capture_output=True, text=True, **kw)

    def child(self):
        p = subprocess.Popen(["sleep", "30"])
        self.addCleanup(lambda: (p.kill(), p.wait()))
        return p

    def states(self):
        return {r["resource"]: r["state"] for r in json.loads(self.at("list", "--json").stdout)}


class Lease(Base):
    def test_race_one_winner(self):
        procs = [subprocess.Popen([AT, "lease", "take", "disk", "--ttl", "5"], env={**self.env, "CLAUDE_PID": str(self.child().pid)},
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE) for i in range(2)]
        codes = sorted(p.wait() for p in procs)
        for p in procs:
            p.stdout.close(); p.stderr.close()
        self.assertEqual(codes, [0, 3])

    def test_dead_holder(self):
        kids = []
        for name, extra in (("plain", []), ("keep", ["--restore"])):
            kids.append(self.child())
            self.assertEqual(self.at("take", name, "--ttl", "5", *extra, env={"CLAUDE_PID": str(kids[-1].pid)}).returncode, 0)
        self.assertEqual(self.states(), {"plain": "held", "keep": "held"})
        for k in kids:
            k.kill(); k.wait()
        self.assertEqual(self.states(), {"keep": "owed"})
        self.assertFalse((self.dir / "plain.json").exists())
        self.assertEqual(self.at("take", "keep", "--ttl", "5").returncode, 3)
        self.assertEqual(self.at("take", "plain", "--ttl", "5").returncode, 0)

    def test_reused_pid_is_gone(self):
        c = self.child()
        self.at("take", "gpu", "--ttl", "5", env={"CLAUDE_PID": str(c.pid)})
        f = self.dir / "gpu.json"
        rec = json.loads(f.read_text())
        self.assertEqual(self.states(), {"gpu": "held"})
        rec["pid_start"] = (rec["pid_start"] or 0) + 1
        f.write_text(json.dumps(rec))
        if rec["pid_start"] == 1:
            self.skipTest("no /proc")
        self.assertEqual(self.states(), {})
        self.assertEqual(self.at("take", "gpu", "--ttl", "5").returncode, 0)

    def test_overdue_blocks_take(self):
        c = self.child()
        self.at("take", "port", "--ttl", "5", "--for", "AUTH-001", env={"CLAUDE_PID": str(c.pid)})
        f = self.dir / "port.json"
        rec = json.loads(f.read_text()); rec["start"] -= 3600
        f.write_text(json.dumps(rec))
        self.assertEqual(self.states(), {"port": "overdue"})
        r = self.at("take", "port", "--ttl", "5")
        self.assertEqual(r.returncode, 3)
        self.assertIn("AUTH-001", r.stderr)

    def test_run_releases_and_returns_code(self):
        r = self.at("run", "suite", "--", sys.executable, "-c", "import sys; sys.exit(7)")
        self.assertEqual(r.returncode, 7)
        self.assertEqual(self.states(), {})
        self.at("take", "suite", "--ttl", "5", env={"CLAUDE_PID": str(self.child().pid)})
        r = self.at("run", "suite", "--", "true")
        self.assertEqual(r.returncode, 3)

    def test_clear_rules(self):
        c = self.child()
        self.at("take", "dev", "--ttl", "5", "--restore", env={"CLAUDE_PID": str(c.pid)})
        c.kill(); c.wait()
        self.assertEqual(self.states(), {"dev": "owed"})
        r = self.at("clear", "dev", "--restored", env={"CLAUDE_CODE_SESSION_ID": "s1"})
        self.assertEqual(r.returncode, 3)
        self.assertEqual(self.at("clear", "dev", "--restored", env={"CLAUDE_CODE_SESSION_ID": "s1", "AGENTS_LEASE_OWNER": "1"}).returncode, 0)
        self.at("take", "dev", "--ttl", "5", "--restore", env={"CLAUDE_PID": str(self.child().pid)})
        (self.dir / "dev.json").write_text(json.dumps({**json.loads((self.dir / "dev.json").read_text()), "pid": 2 ** 22 + 5}))
        self.assertEqual(self.states(), {"dev": "owed"})
        r = self.at("clear", "dev")
        self.assertEqual(r.returncode, 3)
        self.assertIn("restored first", r.stderr)
        self.assertEqual(self.at("clear", "dev", "--restored").returncode, 0)
        self.assertEqual(self.states(), {})

    def test_only_holder_releases(self):
        self.assertEqual(self.at("take", "bus", "--ttl", "5", env={"CLAUDE_CODE_SESSION_ID": "a", "CLAUDE_PID": str(self.child().pid)}).returncode, 0)
        self.assertEqual(self.at("release", "bus", env={"CLAUDE_CODE_SESSION_ID": "b"}).returncode, 3)
        self.assertEqual(self.at("release", "bus", env={"CLAUDE_CODE_SESSION_ID": "a"}).returncode, 0)
        self.assertEqual(self.at("release", "bus").returncode, 0)  # free: ok

    def test_shared_claude_pid_sessions_do_not_release_each_other(self):
        shared = {"CLAUDE_PID": str(self.child().pid)}
        self.assertEqual(self.at("take", "web", "--ttl", "5", env={**shared, "CLAUDE_CODE_SESSION_ID": "a"}).returncode, 0)
        self.assertEqual(self.at("release", "web", env={**shared, "CLAUDE_CODE_SESSION_ID": "b"}).returncode, 3)
        self.assertEqual(self.at("release", "web", env=shared).returncode, 3)
        self.assertEqual(self.at("take", "web", "--ttl", "5", env={**shared, "CLAUDE_CODE_SESSION_ID": "a"}).returncode, 0)  # renew
        self.assertEqual(self.at("release", "web", env={**shared, "CLAUDE_CODE_SESSION_ID": "a"}).returncode, 0)

    def test_run_releases_on_sigterm(self):
        p = subprocess.Popen([AT, "lease", "run", "sig", "--", "sleep", "30"], env=self.env)
        self.addCleanup(p.wait)
        end = time.time() + 5
        while self.states().get("sig") != "held" and time.time() < end:
            time.sleep(0.05)
        self.assertEqual(self.states(), {"sig": "held"})
        p.terminate()
        self.assertEqual(p.wait(timeout=5), 128 + 15)
        self.assertEqual(self.states(), {})

    def test_bad_ttl_and_damaged_record(self):
        for bad in ("nan", "0", "-1", "inf"):
            self.assertEqual(self.at("take", "t", "--ttl", bad).returncode, 2, bad)
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "x.json").write_text("[1]")
        (self.dir / "y.json").write_text('{"pid": 1}')
        self.assertEqual(self.states(), {})
        self.assertEqual(self.at("take", "x", "--ttl", "5").returncode, 0)
        self.assertEqual(sorted(p.name for p in self.dir.iterdir() if p.name.startswith(".tmp")), [])


class Reserve(Base):
    def repo(self, root, prefix="AUTH"):
        tm = root / "docs/tasks_manager"
        for d in ("_todos", "_todos_archived", "_inbox", "_inbox_archived"):
            (tm / d).mkdir(parents=True, exist_ok=True)
        (tm / "_areas.md").write_text(f"| Area | Prefix |\n|---|---|\n| x | {prefix} | y |\n")

    def reserve(self, root, env=None):
        r = subprocess.run(["bash", str(RESERVE), "--root", str(root), "task", "AUTH", "F", "thing"],
                           env={**self.env, **(env or {})}, capture_output=True, text=True)
        return r

    def setUp(self):
        super().setUp()
        self.main = pathlib.Path(self.tmp.name) / "main"
        self.main.mkdir()
        g = lambda *a, cwd=self.main: subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True,
                                                       env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                                                            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})
        g("init", "-q"); g("commit", "-q", "--allow-empty", "-m", "i")
        self.wt = pathlib.Path(self.tmp.name) / "wt"
        g("worktree", "add", "-q", str(self.wt))
        self.repo(self.main); self.repo(self.wt)

    def test_two_checkouts_differ(self):
        a = self.reserve(self.main).stdout.strip()
        b = self.reserve(self.wt).stdout.strip()
        self.assertTrue(a.endswith("AUTH-001-F_thing.md"), a)
        self.assertTrue(b.endswith("AUTH-002-F_thing.md"), b)

    def test_stale_host_lock_is_taken_over(self):
        self.reserve(self.main)
        lock = next((pathlib.Path(self.env["XDG_STATE_HOME"]) / "agents-template/reserve").glob("*.lock"), None)
        self.assertIsNone(lock)  # released
        d = pathlib.Path(self.env["XDG_STATE_HOME"]) / "agents-template/reserve"
        key = next(d.glob("*-AUTH")).name[:-5]
        (d / f"{key}.lock").mkdir()
        dead = subprocess.Popen(["true"]); dead.wait()
        (d / f"{key}.lock/pid").write_text(str(dead.pid))
        self.assertTrue(self.reserve(self.wt).stdout.strip().endswith("AUTH-002-F_thing.md"))

    def test_unwritable_state_behaves_as_before(self):
        blocker = pathlib.Path(self.tmp.name) / "file"
        blocker.write_text("")
        env = {"XDG_STATE_HOME": str(blocker)}
        a = self.reserve(self.main, env)
        b = self.reserve(self.wt, env)
        self.assertEqual((a.returncode, b.returncode, a.stderr, b.stderr), (0, 0, "", ""))
        self.assertTrue(a.stdout.strip().endswith("AUTH-001-F_thing.md"))
        self.assertTrue(b.stdout.strip().endswith("AUTH-001-F_thing.md"))  # as today: the checkouts do not see each other


if __name__ == "__main__":
    unittest.main()
