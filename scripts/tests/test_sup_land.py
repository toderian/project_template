"""`sup worktree|land|ready` (plugins/agents-core/lib/sup.py) against throwaway git repos."""
import json, os, pathlib, re, shutil, subprocess, sys, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[2]
SUP = ROOT / "plugins/agents-core/lib/sup.py"
ARCH = "docs/tasks_manager/_todos_archived"
TODO = "docs/tasks_manager/_todos"
FIX = ROOT / "scripts/tests/fixtures/task-brief"


def g(path, *a, check=True):
    return subprocess.run(["git", "-C", str(path), *a], capture_output=True, text=True, check=check)


def write(path, text):
    path = pathlib.Path(path); path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text)


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(); self.addCleanup(self._tmp.cleanup)
        self.tmp = pathlib.Path(self._tmp.name).resolve()
        self.hub = self.tmp / "hub"; self.hub.mkdir()
        g(self.hub, "init", "-q", "-b", "main"); g(self.hub, "config", "user.name", "T"); g(self.hub, "config", "user.email", "t@example.invalid")
        write(self.hub / "README.md", "base\n"); write(self.hub / ".gitignore", "*.log\n__pycache__/\n")
        g(self.hub, "add", "-A"); g(self.hub, "commit", "-q", "-m", "base")
        self.env = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_CODE_SESSION_ID", "AGENTS_SUP_TASK", "AGENTS_SUPERVISOR")}
        self.env.update(AGENTS_SUP_DIR=str(self.tmp / "state"), AGENTS_LEASE_DIR=str(self.tmp / "leases"))

    def sup(self, *a, cwd=None):
        return subprocess.run([sys.executable, str(SUP), *a], cwd=str(cwd or self.hub), capture_output=True, text=True, env=self.env)

    def task(self, tid, title="Add thing", archived=True, files=None):
        """Create the task worktree and commit a closed-out task (and `files`) on its branch."""
        p = self.sup("worktree", tid); self.assertEqual(p.returncode, 0, p.stderr)
        wt = pathlib.Path(p.stdout.strip())
        write(wt / f"{ARCH if archived else TODO}/{tid}-F_x.md", f"| Field | Value |\n\n## {title}\n")
        for name, text in (files or {"src/%s.py" % tid.lower().replace("-", "_"): "x = 1\n"}).items():
            write(wt / name, text)
        g(wt, "add", "-A"); g(wt, "commit", "-q", "-m", f"{tid} work")
        return wt

    def snapshot(self):
        return (g(self.hub, "rev-parse", "HEAD").stdout, g(self.hub, "branch", "--list").stdout, g(self.hub, "worktree", "list").stdout,
                g(self.hub, "status", "--porcelain").stdout)


class Worktree(Base):
    def test_creates_branch_and_directory_then_refuses(self):
        p = self.sup("worktree", "TST-001"); self.assertEqual(p.returncode, 0, p.stderr)
        wt = self.tmp / "hub-tst-001"; self.assertEqual(p.stdout.strip(), str(wt)); self.assertTrue((wt / "README.md").exists())
        self.assertEqual(g(wt, "branch", "--show-current").stdout.strip(), "task/TST-001")
        again = self.sup("worktree", "TST-001"); self.assertEqual(again.returncode, 3); self.assertIn(str(wt), again.stderr)

    def test_bad_id_is_usage_error(self):
        self.assertEqual(self.sup("worktree", "../x").returncode, 2)


class Land(Base):
    def test_one_commit_removes_worktree_and_keeps_tip(self):
        wt = self.task("TST-001"); tip = g(wt, "rev-parse", "HEAD").stdout.strip(); before = g(self.hub, "rev-list", "--count", "main").stdout
        p = self.sup("land", "TST-001"); self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(int(g(self.hub, "rev-list", "--count", "main").stdout), int(before) + 1)
        self.assertTrue((self.hub / "src/tst_001.py").exists()); self.assertTrue((self.hub / ARCH / "TST-001-F_x.md").exists())
        self.assertFalse(wt.exists()); self.assertEqual(g(self.hub, "branch", "--list", "task/*").stdout.strip(), "")
        self.assertEqual(g(self.hub, "rev-parse", "refs/archive/task/TST-001").stdout.strip(), tip)
        msg = g(self.hub, "log", "-1", "--format=%B").stdout
        self.assertTrue(msg.startswith("feat: TST-001 Add thing"), msg); self.assertIn("Task: TST-001\nArchive: refs/archive/task/TST-001", msg)

    def test_conventional_title_keeps_its_type(self):
        self.task("TST-001", title="fix: Repair thing"); self.assertEqual(self.sup("land", "TST-001").returncode, 0)
        self.assertTrue(g(self.hub, "log", "-1", "--format=%s").stdout.startswith("fix: TST-001 Repair thing"))

    def refused(self, tid, expect):
        before = self.snapshot(); p = self.sup("land", tid)
        self.assertEqual(p.returncode, 3, p.stderr); self.assertEqual(len(p.stderr.strip().splitlines()), 1); self.assertIn(expect, p.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_refusals_change_nothing(self):
        self.task("TST-001", archived=False); self.refused("TST-001", "not closed out")
        wt = self.task("TST-002")
        write(wt / "stray.txt", "x"); self.refused("TST-002", "task worktree"); (wt / "stray.txt").unlink()
        write(self.hub / "dirty.txt", "x"); self.refused("TST-002", "landing checkout"); (self.hub / "dirty.txt").unlink()
        self.refused("TST-404", "no branch")

    def test_landing_checkout_off_default_branch_is_refused(self):
        self.task("TST-001"); g(self.hub, "checkout", "-q", "-b", "other"); self.refused("TST-001", "not main")

    def test_hand_written_conflict_stops_and_leaves_everything(self):
        wt = self.task("TST-001", files={"README.md": "task side\n"})
        write(self.hub / "README.md", "main side\n"); g(self.hub, "commit", "-qam", "main edit"); before = self.snapshot()
        p = self.sup("land", "TST-001"); self.assertEqual(p.returncode, 3); self.assertIn("README.md", p.stderr)
        self.assertEqual(self.snapshot(), before); self.assertEqual(g(self.hub, "status", "--porcelain").stdout, "")
        self.assertTrue(wt.exists()); self.assertEqual(g(self.hub, "branch", "--list", "task/TST-001").stdout.split()[-1], "task/TST-001")
        self.assertEqual(g(self.hub, "rev-parse", "-q", "--verify", "refs/archive/task/TST-001", check=False).returncode, 1)

    def test_ignored_file_is_kept_and_caches_are_not(self):
        wt = self.task("TST-001"); write(wt / "notes/run.log", "evidence\n"); write(wt / "src/__pycache__/m.pyc", "c")
        p = self.sup("land", "TST-001"); self.assertEqual(p.returncode, 0, p.stderr)
        kept = self.tmp / "state/_host/kept/TST-001"; self.assertIn(str(kept), p.stdout)
        self.assertEqual((kept / "notes/run.log").read_text(), "evidence\n"); self.assertFalse((kept / "src").exists()); self.assertFalse(wt.exists())

    def test_a_linked_local_path_goes_with_the_worktree_and_a_real_file_in_its_place_is_kept(self):
        write(self.hub / ".gitignore", "*.log\n__pycache__/\nshared\n"); g(self.hub, "commit", "-qam", "ignore shared")
        write(self.tmp / "state/p/conf/profile.json", json.dumps({"local": ["shared/"]}))
        for tid, replace in (("TST-001", False), ("TST-002", True)):
            wt = self.task(tid); write(self.hub / "shared/data.txt", "from the hub\n")
            (wt / "shared").symlink_to(self.hub / "shared")
            if replace:
                (wt / "shared").unlink(); write(wt / "shared/own.txt", "a tool wrote this\n")
            p = self.sup("land", tid, "--profile", "p"); self.assertEqual(p.returncode, 0, p.stderr)
            self.assertFalse(wt.exists()); self.assertEqual((self.hub / "shared/data.txt").read_text(), "from the hub\n")
            kept = self.tmp / "state/_host/kept" / tid
            self.assertEqual(sorted(str(f.relative_to(kept)) for f in kept.rglob("*") if f.is_file()), ["shared/own.txt"] if replace else [])
            self.assertEqual(kept.exists(), replace)

    def local(self, *entries):
        write(self.hub / ".gitignore", "*.log\n__pycache__/\nshared\n"); g(self.hub, "commit", "-qam", "ignore shared", check=False)
        write(self.tmp / "state/p/conf/profile.json", json.dumps({"local": list(entries)})); write(self.hub / "shared/data.txt", "from the hub\n")

    def test_a_branch_that_tracks_a_local_path_is_refused_before_any_commit(self):
        self.local("shared/")
        wt = self.task("TST-001"); (wt / "shared").symlink_to(self.hub / "shared"); g(wt, "add", "-f", "shared"); g(wt, "commit", "-qm", "oops")
        before = self.snapshot(); p = self.sup("land", "TST-001", "--profile", "p")
        self.assertEqual(p.returncode, 3); self.assertIn("the hub holds shared untracked", p.stderr)
        self.assertEqual(self.snapshot(), before); self.assertTrue((self.hub / "shared/data.txt").is_file())
        p = self.sup("land", "TST-001")  # by hand, no profile: the same refusal
        self.assertEqual(p.returncode, 3); self.assertEqual(self.snapshot(), before); self.assertTrue((self.hub / "shared/data.txt").is_file())

    def test_a_branch_that_adds_a_parent_of_untracked_hub_content_is_refused_and_one_that_removed_its_link_lands(self):
        write(self.hub / ".gitignore", "lab/\nshared\n"); g(self.hub, "add", ".gitignore"); g(self.hub, "commit", "-qm", "ignore")
        write(self.hub / "lab/results/r.txt", "r\n"); write(self.hub / "shared/data.txt", "d\n")
        wt = self.task("TST-001"); write(wt / "lab", "a file where the hub has a directory\n"); g(wt, "add", "-f", "lab"); g(wt, "commit", "-qm", "oops")
        before = self.snapshot(); p = self.sup("land", "TST-001")
        self.assertEqual(p.returncode, 3); self.assertIn("the hub holds lab untracked", p.stderr)
        self.assertEqual(self.snapshot(), before); self.assertTrue((self.hub / "lab/results/r.txt").is_file())
        (self.tmp / "far").mkdir(); (self.hub / "shared/sl").symlink_to(self.tmp / "far")  # an untracked link as a parent
        wt = self.task("TST-003"); write(wt / "shared/sl/x", "x\n"); g(wt, "add", "-f", "shared/sl/x"); g(wt, "commit", "-qm", "under the link")
        before = self.snapshot(); p = self.sup("land", "TST-003")
        self.assertEqual(p.returncode, 3); self.assertIn("the hub holds shared/sl untracked", p.stderr)
        self.assertEqual(self.snapshot(), before); self.assertEqual(list((self.tmp / "far").iterdir()), [])
        wt = self.task("TST-002"); (wt / "shared").symlink_to(self.hub / "shared"); g(wt, "add", "-f", "shared"); g(wt, "commit", "-qm", "oops")
        g(wt, "rm", "-q", "--cached", "shared"); g(wt, "commit", "-qm", "undo")
        p = self.sup("land", "TST-002"); self.assertEqual(p.returncode, 0, p.stderr); self.assertTrue((self.hub / "shared/data.txt").is_file())

    def test_a_conflict_is_refused_before_the_checkout_is_touched_so_an_ignored_hub_file_survives(self):
        write(self.hub / "conf.local", "v1\n"); g(self.hub, "add", "conf.local"); g(self.hub, "commit", "-qm", "conf")
        wt = self.task("TST-001"); write(wt / "conf.local", "branch edit\n"); g(wt, "commit", "-qam", "edit")
        g(self.hub, "rm", "-q", "--cached", "conf.local"); write(self.hub / ".gitignore", "*.log\n__pycache__/\nconf.local\n")
        g(self.hub, "commit", "-qam", "untrack"); write(self.hub / "conf.local", "the owner's private copy\n")
        before = self.snapshot(); p = self.sup("land", "TST-001")
        self.assertEqual(p.returncode, 3); self.assertIn("conflict landing TST-001", p.stderr); self.assertIn("conf.local", p.stderr)
        self.assertEqual(self.snapshot(), before); self.assertEqual((self.hub / "conf.local").read_text(), "the owner's private copy\n")

    def test_a_directory_renamed_on_default_does_not_carry_a_branch_file_onto_an_ignored_hub_file(self):
        for n in "abc":
            write(self.hub / f"src/{n}.py", f"{n} = 1\n")
        g(self.hub, "add", "-A"); g(self.hub, "commit", "-qm", "src")
        wt = self.task("TST-001", files={"src/local.cfg": "from the branch\n"})
        g(self.hub, "mv", "src", "lib"); write(self.hub / ".gitignore", "*.log\n__pycache__/\nlocal.cfg\n"); g(self.hub, "commit", "-qam", "rename")
        write(self.hub / "lib/local.cfg", "the owner's\n")
        before = self.snapshot(); p = self.sup("land", "TST-001")
        self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
        self.assertEqual(self.snapshot(), before); self.assertEqual((self.hub / "lib/local.cfg").read_text(), "the owner's\n")

    def test_a_branch_that_stops_ignoring_a_file_the_hub_holds_is_refused_and_the_file_stays(self):
        write(self.hub / ".gitignore", "*.log\n__pycache__/\nsecrets.env\n"); g(self.hub, "commit", "-qam", "ignore"); write(self.hub / "secrets.env", "KEY=1\n")
        wt = self.task("TST-001"); write(wt / ".gitignore", "*.log\n__pycache__/\n"); g(wt, "commit", "-qam", "drop the line")
        before = self.snapshot(); p = self.sup("land", "TST-001")
        self.assertEqual(p.returncode, 3); self.assertIn("stops ignoring secrets.env", p.stderr)
        self.assertEqual(self.snapshot(), before); self.assertEqual((self.hub / "secrets.env").read_text(), "KEY=1\n")
        self.assertEqual(g(self.hub, "ls-files", "secrets.env").stdout, "")

    def test_a_second_landing_attempt_does_not_replace_a_file_kept_by_the_first(self):
        wt = self.task("TST-001"); write(wt / "notes/run.log", "second\n"); write(self.tmp / "state/_host/kept/TST-001/notes/run.log", "first\n")
        p = self.sup("land", "TST-001"); self.assertEqual(p.returncode, 0, p.stderr); kept = self.tmp / "state/_host/kept/TST-001/notes"
        self.assertEqual((kept / "run.log").read_text(), "first\n"); self.assertEqual((kept / "run.log.1").read_text(), "second\n")

    def test_a_branch_that_turns_a_tracked_directory_into_a_file_is_refused_while_the_hub_holds_ignored_files_in_it(self):
        write(self.hub / ".gitignore", "*.db\n"); write(self.hub / "data/keep.py", "k = 1\n"); g(self.hub, "add", "-A"); g(self.hub, "commit", "-qm", "data")
        write(self.hub / "data/c.db", "precious\n")
        wt = self.task("TST-001"); g(wt, "rm", "-rq", "data"); write(wt / "data", "now a file\n"); g(wt, "add", "data"); g(wt, "commit", "-qm", "data is a file")
        before = self.snapshot(); p = self.sup("land", "TST-001")
        self.assertEqual(p.returncode, 3); self.assertIn("the hub holds data untracked", p.stderr)
        self.assertEqual(self.snapshot(), before); self.assertEqual((self.hub / "data/c.db").read_text(), "precious\n")
        (self.hub / "data/c.db").unlink(); p = self.sup("land", "TST-001"); self.assertEqual(p.returncode, 0, p.stderr)  # nothing left to lose

    def test_a_retargeted_link_and_a_link_of_a_dropped_entry_are_kept_as_links_and_nothing_behind_them_is_touched(self):
        for tid, entries, target in (("TST-001", ["shared/"], self.tmp / "elsewhere"), ("TST-002", [], self.hub / "shared")):
            self.local(*entries); write(target / "keep.txt", "k\n"); wt = self.task(tid); (wt / "shared").symlink_to(target)
            p = self.sup("land", tid, "--profile", "p"); self.assertEqual(p.returncode, 0, p.stderr)
            link = self.tmp / "state/_host/kept" / tid / "shared"
            self.assertTrue(link.is_symlink()); self.assertEqual(os.readlink(link), str(target)); self.assertTrue((target / "keep.txt").is_file())

    def test_a_link_in_kept_that_points_outside_refuses_the_move(self):
        wt = self.task("TST-001"); write(wt / "a/f.log", "x"); (self.tmp / "outside").mkdir()
        kept = self.tmp / "state/_host/kept/TST-001"; kept.mkdir(parents=True); (kept / "a").symlink_to(self.tmp / "outside")
        p = self.sup("land", "TST-001"); self.assertEqual(p.returncode, 3); self.assertIn("would lie outside", p.stderr)
        self.assertEqual(list((self.tmp / "outside").iterdir()), [])
        (kept / "a").unlink(); write(wt / "b.log", "x"); (kept / "b.log").symlink_to(self.tmp / "outside")  # the destination itself is a link
        p = self.sup("land", "TST-001"); self.assertEqual(p.returncode, 3, p.stderr); self.assertEqual(list((self.tmp / "outside").iterdir()), [])

    def test_a_task_whose_id_is_a_prefix_of_a_landed_one_still_gets_its_own_commit(self):
        self.task("TST-10"); self.assertEqual(self.sup("land", "TST-10").returncode, 0)
        self.task("TST-1"); before = int(g(self.hub, "rev-list", "--count", "main").stdout)
        p = self.sup("land", "TST-1"); self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(int(g(self.hub, "rev-list", "--count", "main").stdout), before + 1)
        self.assertTrue((self.hub / "src/tst_1.py").exists())

    def test_second_task_after_landing_sees_first_archived_file(self):
        self.task("TST-001"); self.assertEqual(self.sup("land", "TST-001").returncode, 0)
        wt2 = self.sup("worktree", "TST-002"); self.assertEqual(wt2.returncode, 0, wt2.stderr)
        self.assertTrue((pathlib.Path(wt2.stdout.strip()) / ARCH / "TST-001-F_x.md").exists())

    def test_dry_run_changes_nothing(self):
        wt = self.task("TST-001"); write(wt / "a.log", "x"); before = self.snapshot()
        p = self.sup("land", "TST-001", "--dry-run"); self.assertEqual(p.returncode, 0, p.stderr); self.assertIn("dry-run", p.stdout)
        self.assertEqual(self.snapshot(), before); self.assertTrue((wt / "a.log").exists()); self.assertFalse((self.tmp / "state").exists())

    def add_origin(self):
        origin = self.tmp / "origin.git"; subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
        g(self.hub, "remote", "add", "origin", str(origin)); g(self.hub, "push", "-q", "origin", "main"); g(self.hub, "fetch", "-q", "origin")
        g(self.hub, "remote", "set-head", "origin", "main")

    def test_worktree_bases_on_local_default_branch_not_origin(self):
        self.add_origin(); self.task("TST-001"); self.assertEqual(self.sup("land", "TST-001").returncode, 0)
        wt2 = self.sup("worktree", "TST-002"); self.assertEqual(wt2.returncode, 0, wt2.stderr)
        self.assertTrue((pathlib.Path(wt2.stdout.strip()) / ARCH / "TST-001-F_x.md").exists())

    def test_bad_base_is_refused(self):
        p = self.sup("worktree", "TST-001", "--base", "nope"); self.assertEqual(p.returncode, 3); self.assertIn("nope", p.stderr)

    def test_rerun_after_failed_removal_only_cleans_up(self):
        wt = self.task("TST-001"); g(self.hub, "worktree", "lock", str(wt)); tip = g(wt, "rev-parse", "HEAD").stdout.strip()
        p = self.sup("land", "TST-001"); self.assertEqual(p.returncode, 3, p.stdout)
        landed = g(self.hub, "rev-parse", "HEAD").stdout; self.assertTrue(wt.exists())
        self.assertEqual(g(self.hub, "rev-parse", "refs/archive/task/TST-001").stdout.strip(), tip)
        g(self.hub, "worktree", "unlock", str(wt)); p = self.sup("land", "TST-001"); self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(g(self.hub, "rev-parse", "HEAD").stdout, landed); self.assertFalse(wt.exists())
        self.assertEqual(g(self.hub, "branch", "--list", "task/*").stdout.strip(), "")

    def test_non_ascii_ignored_file_is_kept(self):
        wt = self.task("TST-001"); write(wt / "notes/données-é.log", "evidence\n")
        p = self.sup("land", "TST-001"); self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual((self.tmp / "state/_host/kept/TST-001/notes/données-é.log").read_text(), "evidence\n")

    def test_held_lease_refuses_landing(self):
        from unittest import mock
        self.env.pop("CLAUDE_CODE_SESSION_ID", None); self.task("TST-001"); before = self.snapshot()
        sys.path.insert(0, str(SUP.parent)); import lease
        with mock.patch.dict(os.environ, {"AGENTS_LEASE_DIR": self.env["AGENTS_LEASE_DIR"]}):
            os.environ.pop("CLAUDE_CODE_SESSION_ID", None); self.assertEqual(lease.take("hub-ledger", 60, own_pid=True), 0)
            p = self.sup("land", "TST-001"); self.assertEqual(p.returncode, 3); self.assertIn("hub-ledger", p.stderr)
            self.assertEqual(self.snapshot(), before); lease.release("hub-ledger", own_pid=True)
        self.assertEqual(self.sup("land", "TST-001").returncode, 0)

    def test_failing_commit_leaves_landing_checkout_clean(self):
        self.task("TST-001"); hook = self.hub / ".git/hooks/pre-commit"; write(hook, "#!/bin/sh\necho no >&2\nexit 1\n"); hook.chmod(0o755)
        before = self.snapshot(); p = self.sup("land", "TST-001")
        self.assertEqual(p.returncode, 3); self.assertEqual(self.snapshot(), before); self.assertEqual(g(self.hub, "status", "--porcelain").stdout, "")

    def test_into_and_detached_head(self):
        self.task("TST-001"); p = self.sup("land", "TST-001", "--into", "other"); self.assertEqual(p.returncode, 3); self.assertIn("not other", p.stderr)
        g(self.hub, "checkout", "-q", "--detach"); p = self.sup("land", "TST-001"); self.assertEqual(p.returncode, 3); self.assertIn("detached", p.stderr)
        g(self.hub, "checkout", "-q", "-b", "other"); p = self.sup("land", "TST-001", "--into", "other"); self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(g(self.hub, "log", "-1", "--format=%s", "other").stdout.strip(), "feat: TST-001 Add thing")

    def events(self):
        f = self.tmp / "state/p/events.jsonl"
        return [json.loads(ln) for ln in f.read_text().splitlines()] if f.exists() else []

    def test_land_emits_landed_for_the_profile_only(self):
        self.task("TST-001"); self.task("TST-002")
        self.assertEqual(self.sup("land", "TST-001").returncode, 0); self.assertEqual(self.events(), [])
        p = self.sup("land", "TST-002", "--profile", "p"); self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual([(e["kind"], e["task"]) for e in self.events()], [("landed", "TST-002")])
        self.env["AGENTS_SUPERVISOR"] = "p"; self.task("TST-003"); self.assertEqual(self.sup("land", "TST-003").returncode, 0)
        self.assertEqual([e["task"] for e in self.events()], ["TST-002", "TST-003"])

    def test_a_worker_session_may_not_land(self):
        self.task("TST-001"); before = self.snapshot(); self.env["AGENTS_SUP_TASK"] = "TST-001"
        p = self.sup("land", "TST-001"); self.assertEqual(p.returncode, 3); self.assertIn("worker", p.stderr); self.assertEqual(self.snapshot(), before)

    def test_claude_files_need_the_owner_flag(self):
        for name in (".claude/settings.json", ".mcp.json", "sub/.claude/agents/x.md"):
            with self.subTest(name):
                tid = "TST-%03d" % (len(name) + 100)
                self.task(tid, files={name: "{}\n"}); before = self.snapshot()
                p = self.sup("land", tid); self.assertEqual(p.returncode, 3); self.assertIn("--allow-claude-files", p.stderr)
                self.assertEqual(self.snapshot(), before)
                self.assertEqual(self.sup("land", tid, "--dry-run").returncode, 3)
                self.env["CLAUDE_CODE_SESSION_ID"] = "chat-sess-0001"
                p = self.sup("land", tid, "--allow-claude-files"); self.assertEqual(p.returncode, 3); self.assertIn("owner", p.stderr)
                self.assertEqual(self.snapshot(), before)
                del self.env["CLAUDE_CODE_SESSION_ID"]
                p = self.sup("land", tid, "--allow-claude-files"); self.assertEqual(p.returncode, 0, p.stderr)

    def test_a_renamed_claude_file_needs_the_owner_flag(self):
        self.task("TST-001", files={".claude/settings.json": "{}\n"}); self.assertEqual(self.sup("land", "TST-001", "--allow-claude-files").returncode, 0)
        wt = self.task("TST-002", files={"x.txt": "1\n"}); g(wt, "mv", ".claude/settings.json", "docs-old-settings.json")
        g(wt, "commit", "-q", "-m", "mv"); before = self.snapshot(); p = self.sup("land", "TST-002")
        self.assertEqual(p.returncode, 3, p.stdout); self.assertIn("--allow-claude-files", p.stderr); self.assertEqual(self.snapshot(), before)

    def test_land_runs_the_hub_hooks_despite_the_launchers_git_config(self):
        self.task("TST-001"); hook = self.hub / ".git/hooks/pre-commit"; write(hook, "#!/bin/sh\necho no >&2\nexit 1\n"); hook.chmod(0o755)
        self.env.update(GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="core.hooksPath", GIT_CONFIG_VALUE_0="/dev/null")
        p = self.sup("land", "TST-001"); self.assertEqual(p.returncode, 3, p.stdout + p.stderr); self.assertIn("commit failed", p.stderr)

    def ledger_hub(self):
        shutil.copytree(FIX, self.hub, dirs_exist_ok=True); g(self.hub, "add", "-A"); g(self.hub, "commit", "-q", "-m", "ledger")

    def archive(self, wt, line):
        src = next((wt / TODO).glob("TST-001-*.md")); text = re.sub(r"(\| Status\s+\| )open", r"\1done", src.read_text())
        write(wt / ARCH / src.name, text); src.unlink()
        write(wt / "docs/tasks_manager/_done.md", line + "\n"); g(wt, "add", "-A"); g(wt, "commit", "-q", "-m", "close out")

    def test_generated_ledger_conflict_is_rebuilt(self):
        self.ledger_hub(); p = self.sup("worktree", "TST-001"); wt = pathlib.Path(p.stdout.strip()); self.archive(wt, "# task side")
        write(self.hub / "docs/tasks_manager/_done.md", "# main side\n"); g(self.hub, "commit", "-qam", "main edit")
        p = self.sup("land", "TST-001"); self.assertEqual(p.returncode, 0, p.stderr)
        done = (self.hub / "docs/tasks_manager/_done.md").read_text(); self.assertIn("TST-001", done); self.assertNotIn("main side", done)
        self.assertEqual(g(self.hub, "status", "--porcelain").stdout, ""); self.assertFalse(wt.exists())

    def test_missing_ledger_tooling_is_refused(self):
        self.ledger_hub(); p = self.sup("worktree", "TST-001"); self.archive(pathlib.Path(p.stdout.strip()), "x"); before = self.snapshot()
        self.env["AT_TASKS_ROOT"] = str(self.tmp / "none"); p = self.sup("land", "TST-001")
        self.assertEqual(p.returncode, 3); self.assertIn("agents-tasks", p.stderr); self.assertEqual(self.snapshot(), before)

    def no_merge_tree(self):
        """A `git` first on PATH that fails `merge-tree`, as git before 2.38 does."""
        fake = self.tmp / "fakegit"
        write(fake / "git", f'#!/bin/bash\nfor a in "$@"; do if [ "$a" = merge-tree ]; then echo unsupported >&2; exit 129; fi; done\nexec {shutil.which("git")} "$@"\n')
        (fake / "git").chmod(0o755); self.env["PATH"] = f"{fake}:{self.env['PATH']}"

    def test_without_merge_tree_a_landing_that_default_has_moved_past_is_refused_before_the_checkout_is_touched(self):
        self.no_merge_tree()
        for n in "abc":
            write(self.hub / f"old/{n}.py", f"{n} = 1\n")
        g(self.hub, "add", "-A"); g(self.hub, "commit", "-qm", "old"); self.task("TST-001", files={"old/f.bin": "from the branch\n"})
        g(self.hub, "mv", "old", "new"); write(self.hub / ".gitignore", "*.log\n__pycache__/\n*.bin\n"); g(self.hub, "commit", "-qam", "rename")
        write(self.hub / "new/f.bin", "the owner's\n")
        self.refused("TST-001", "2.38"); self.assertEqual((self.hub / "new/f.bin").read_text(), "the owner's\n")

    def test_without_merge_tree_a_branch_based_on_the_default_tip_lands_and_the_guard_still_holds(self):
        self.no_merge_tree(); write(self.hub / ".gitignore", "*.log\n__pycache__/\nx.bin\n"); g(self.hub, "commit", "-qam", "ignore"); write(self.hub / "x.bin", "mine\n")
        wt = self.task("TST-001"); write(wt / "x.bin", "branch\n"); g(wt, "add", "-f", "x.bin"); g(wt, "commit", "-qm", "force"); self.refused("TST-001", "the hub holds x.bin untracked")
        self.assertEqual((self.hub / "x.bin").read_text(), "mine\n"); (self.hub / "x.bin").unlink()
        self.task("TST-002"); p = self.sup("land", "TST-002"); self.assertEqual(p.returncode, 0, p.stderr)

    def sync_that_writes(self, note):
        """A ledger sync that rebuilds `_done.md` and, like a hub writer racing the landing, drops `note` into the checkout."""
        write(self.tmp / "tasksroot/skills/task-ledger/scripts/sync_todo_ledgers.py",
              "import pathlib, sys\nroot = pathlib.Path(sys.argv[sys.argv.index('--root') + 1])\n"
              f"if '--check' not in sys.argv:\n    (root / 'docs/tasks_manager/_done.md').write_text('generated done\\n')\n    (root / {note!r}).write_text('owner note\\n')\n")
        self.env["AT_TASKS_ROOT"] = str(self.tmp / "tasksroot")

    def test_a_file_that_appears_in_the_hub_during_landing_is_neither_committed_nor_deleted(self):
        self.ledger_hub(); self.sync_that_writes("owner-note.txt"); wt = pathlib.Path(self.sup("worktree", "TST-001").stdout.strip()); self.archive(wt, "# task side")
        write(self.hub / "docs/tasks_manager/_done.md", "# main side\n"); g(self.hub, "commit", "-qam", "main edit")
        hook = self.hub / ".git/hooks/pre-commit"; write(hook, "#!/bin/sh\nexit 1\n"); hook.chmod(0o755)
        p = self.sup("land", "TST-001"); self.assertEqual(p.returncode, 3); self.assertEqual((self.hub / "owner-note.txt").read_text(), "owner note\n")
        hook.unlink(); (self.hub / "owner-note.txt").unlink(); g(self.hub, "checkout", "-q", "--", "."); p = self.sup("land", "TST-001"); self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(g(self.hub, "show", "--name-only", "--format=", "HEAD").stdout.count("owner-note"), 0)
        self.assertEqual(g(self.hub, "show", "HEAD:docs/tasks_manager/_done.md").stdout, "generated done\n"); self.assertTrue((self.hub / "owner-note.txt").is_file())

    def test_a_ledger_page_the_sync_creates_under_docs_is_committed_with_the_landing(self):
        self.ledger_hub(); self.sync_that_writes("docs/areas/new-page.md"); wt = pathlib.Path(self.sup("worktree", "TST-001").stdout.strip()); self.archive(wt, "# task side")
        p = self.sup("land", "TST-001"); self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("docs/areas/new-page.md", g(self.hub, "show", "--name-only", "--format=", "HEAD").stdout)
        self.assertEqual(g(self.hub, "status", "--porcelain").stdout, "")

    def test_an_edit_hidden_by_assume_unchanged_is_refused_by_name_and_survives(self):
        self.task("TST-001"); g(self.hub, "update-index", "--assume-unchanged", "README.md"); write(self.hub / "README.md", "my edit\n")
        self.refused("TST-001", "README.md"); self.assertEqual((self.hub / "README.md").read_text(), "my edit\n")
        write(self.hub / "README.md", "base\n"); p = self.sup("land", "TST-001"); self.assertEqual(p.returncode, 0, p.stderr)

    def test_a_non_utf8_file_name_neither_crashes_the_kept_move_nor_the_landing(self):
        name = os.fsdecode(b"caf\xe9.log"); wt = self.task("TST-001"); write(wt / name, "evidence\n")
        p = self.sup("land", "TST-001"); self.assertEqual(p.returncode, 0, p.stderr); self.assertEqual((self.tmp / "state/_host/kept/TST-001" / name).read_text(), "evidence\n")
        odd = os.fsdecode(b"src/caf\xe9.py"); self.task("TST-002", files={odd: "x = 1\n"}); p = self.sup("land", "TST-002")
        self.assertEqual(p.returncode, 0, p.stderr); self.assertTrue((self.hub / odd).is_file())

    def test_a_refusal_naming_a_non_utf8_path_is_one_line(self):
        odd = os.fsdecode(b"caf\xe9.txt"); write(self.hub / odd, "base\n"); g(self.hub, "add", "-A"); g(self.hub, "commit", "-qm", "odd")
        self.task("TST-001", files={odd: "task side\n"}); write(self.hub / odd, "main side\n"); g(self.hub, "commit", "-qam", "main edit")
        p = self.sup("land", "TST-001"); self.assertEqual(p.returncode, 3, p.stderr); self.assertEqual(len(p.stderr.strip().splitlines()), 1); self.assertNotIn("Traceback", p.stderr)

    def test_a_rerun_that_only_cleans_up_skips_the_added_path_guard(self):
        wt = self.task("TST-001"); g(self.hub, "worktree", "lock", str(wt)); self.assertEqual(self.sup("land", "TST-001").returncode, 3)
        g(self.hub, "rm", "-q", "--cached", "src/tst_001.py"); write(self.hub / ".gitignore", "*.log\n__pycache__/\nsrc/\n"); g(self.hub, "commit", "-qam", "untrack")
        g(self.hub, "worktree", "unlock", str(wt)); p = self.sup("land", "TST-001"); self.assertEqual(p.returncode, 0, p.stderr); self.assertFalse(wt.exists())

    def test_a_kept_file_whose_parent_name_is_a_file_in_kept_is_refused_with_the_way_out(self):
        wt = self.task("TST-001"); write(wt / "agen/b.log", "x"); write(self.tmp / "state/_host/kept/TST-001/agen", "an earlier file\n")
        p = self.sup("land", "TST-001"); self.assertEqual(p.returncode, 3); self.assertEqual(len(p.stderr.strip().splitlines()), 1)
        self.assertIn(str(self.tmp / "state/_host/kept/TST-001"), p.stderr); self.assertNotIn("Errno", p.stderr)


class PackLand(Base):
    """A pack with one sibling repo `sib`: the pack worktree sib-pk on feat/x, the hub's map pointing at the checkout."""
    def setUp(self):
        super().setUp()
        sys.path.insert(0, str(ROOT / "plugins/agents-core/lib"))
        os.environ["AGENTS_SUP_DIR"] = self.env["AGENTS_SUP_DIR"]; self.addCleanup(os.environ.pop, "AGENTS_SUP_DIR")
        self.sib = self.tmp / "sib"; self.sib.mkdir()
        g(self.sib, "init", "-q", "-b", "dev"); g(self.sib, "config", "user.name", "T"); g(self.sib, "config", "user.email", "t@example.invalid")
        g(self.sib, "commit", "-q", "--allow-empty", "-m", "sib base")
        g(self.sib, "worktree", "add", "-q", "-b", "feat/x", str(self.tmp / "sib-pk"), "dev")
        self.pw = self.tmp / "sib-pk"
        write(self.hub / ".config/repos.project.md", "| Repo | Required | Role | Default branch | Integration branch | Work mode |\n|---|---|---|---|---|---|\n"
              "| hub | yes | x | main | main | d |\n| sib | no | x | dev | dev | d |\n")
        write(self.hub / ".local/repos.map", f"hub: {self.hub}\nsib: {self.sib}\n")
        write(self.hub / ".gitignore", "*.log\n.local/\n"); g(self.hub, "add", "-A"); g(self.hub, "commit", "-q", "-m", "registry")
        self.tip0 = g(self.sib, "rev-parse", "dev").stdout.strip()
        import sup_state as st; self.st = st
        st.write_pack("p", {"name": "pk", "tasks": ["TST-001", "TST-002"], "branches": {"sib": "feat/x"}, "tips": {"sib": self.tip0}})

    def pack_task(self, tid):
        write(self.hub / f"{TODO}/{tid}-F_x.md", f"| Field | Value |\n|---|---|\n| Repos | `sib` |\n\n## Add {tid}\n")
        g(self.hub, "add", "-A"); g(self.hub, "commit", "-q", "-m", f"add {tid}")
        wt = pathlib.Path(self.sup("worktree", tid).stdout.strip())
        write(wt / ARCH / f"{tid}-F_x.md", f"| Field | Value |\n|---|---|\n| Repos | `sib` |\n\n## Add {tid}\n")
        g(wt, "rm", "-q", f"{TODO}/{tid}-F_x.md"); g(wt, "add", "-A"); g(wt, "commit", "-q", "-m", tid)
        return wt

    def land(self, tid):
        return self.sup("land", tid, "--profile", "p")

    def test_the_hub_commit_carries_the_range_and_the_tip_moves(self):
        self.pack_task("TST-001")
        g(self.pw, "commit", "-q", "--allow-empty", "-m", "phase 1"); new = g(self.pw, "rev-parse", "HEAD").stdout.strip()
        p = self.land("TST-001"); self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn(f"sib feat/x {self.tip0}..{new}\n", g(self.hub, "log", "-1", "--format=%B").stdout)
        self.assertEqual(self.st.read_pack("p", "pk")["tips"], {"sib": new})

    def test_a_landing_without_the_holding_profile_refuses_and_changes_nothing(self):
        self.pack_task("TST-001"); self.st.set_config("p", hub=str(self.hub)); before = self.snapshot()
        for args in ((), ("--profile", "q")):
            p = self.sup("land", "TST-001", *args); self.assertEqual(p.returncode, 3, args); self.assertIn("--profile", p.stderr)
        self.assertEqual(self.snapshot(), before)
        self.st.set_config("p", hub=None)  # a profile that never ran init has no hub: it still counts as this hub
        self.assertEqual(self.sup("land", "TST-001").returncode, 3); self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.sup("land", "TST-001", "--profile", "p").returncode, 0)

    def test_a_dirty_pack_worktree_refuses_and_changes_nothing(self):
        self.pack_task("TST-001"); write(self.pw / "half.py", "x\n"); before = self.snapshot()
        self.assertEqual(self.land("TST-001").returncode, 3)
        self.assertEqual(self.snapshot(), before); self.assertEqual(self.st.read_pack("p", "pk")["tips"], {"sib": self.tip0})

    def test_a_rerun_after_a_crash_between_the_commit_and_the_tips_moves_the_tips(self):
        wt = self.pack_task("TST-001"); g(self.pw, "commit", "-q", "--allow-empty", "-m", "phase 1"); new = g(self.pw, "rev-parse", "HEAD").stdout.strip()
        tip = g(wt, "rev-parse", "HEAD").stdout.strip(); self.assertEqual(self.land("TST-001").returncode, 0)
        g(self.hub, "branch", "task/TST-001", tip)  # the state a crash leaves: the hub commit exists, the branch and the old tips remain
        g(self.pw, "commit", "-q", "--allow-empty", "-m", "moved on")  # the branch moved after the landing: the tip stays the commit's
        self.st.write_pack("p", {**self.st.read_pack("p", "pk"), "tips": {"sib": self.tip0}}); count = g(self.hub, "rev-list", "--count", "main").stdout
        p = self.land("TST-001"); self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(g(self.hub, "rev-list", "--count", "main").stdout, count)
        self.assertEqual(self.st.read_pack("p", "pk")["tips"], {"sib": new})


    def test_a_task_without_a_sibling_commit_lands_with_no_range_line_and_leaves_the_tip(self):
        self.pack_task("TST-001"); p = self.land("TST-001"); self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn("sib feat/x", g(self.hub, "log", "-1", "--format=%B").stdout)
        self.assertEqual(self.st.read_pack("p", "pk")["tips"], {"sib": self.tip0})


class Parser(Base):
    def test_top_level_flags_reach_every_part(self):
        # before the subcommand, as `at sup --help` shows them
        p = self.sup("--profile", "p", "queue", cwd=self.tmp); self.assertEqual((p.returncode, p.stdout), (0, ""), p.stderr)
        p = self.sup("--profile", "p", "--hub", str(self.hub), "status", cwd=self.tmp)
        self.assertEqual(p.returncode, 0, p.stderr); self.assertIn("supervisor p", p.stdout)
        p = self.sup("--profile", "p", "watch", "status", cwd=self.tmp)
        self.assertNotIn("no profile", p.stderr)
        self.assertEqual(self.sup("status", "--profile", "p", "--hub", str(self.hub), cwd=self.tmp).returncode, 0)

    def test_every_subcommand_is_registered(self):
        import argparse
        sys.path.insert(0, str(SUP.parent)); import sup
        ap = argparse.ArgumentParser(); sup.add_parser(ap.add_subparsers(dest="cmd"))
        names = set(ap._subparsers._group_actions[0].choices["sup"]._subparsers._group_actions[0].choices)
        want = {"worktree", "land", "ready", "status", "done", "task", "measure", "ask", "need", "release", "inbox", "answer", "grant",
                "deny", "queue", "escalate", "instruct", "instructions"}
        self.assertEqual(want - names, set())


READY = """| Field | Value |
|---|---|
| Task ID | TST-009 |

## Ready task

Resources: none

### Phases

#### Phase 1: Build

Files: `src/a.py`
- Checks: `python3 -m unittest`
- [ ] do it

### Acceptance criteria

- [ ] works

### Unattended run

Checked: 2026-11-26, READY
Authorised: restart the dev server
Owner only: push
Defaults: if X, do Y
"""


class PackReady(Base):
    """`ready --pack`: one line per problem of the pack, `ready` and exit 0 otherwise."""
    def setUp(self):
        super().setUp()
        sys.path.insert(0, str(ROOT / "plugins/agents-core/lib"))
        os.environ["AGENTS_SUP_DIR"] = self.env["AGENTS_SUP_DIR"]; self.addCleanup(os.environ.pop, "AGENTS_SUP_DIR")
        import sup_state as st; self.st = st
        write(self.hub / ".config/repos.project.md", "| Repo | Required | Role | Default branch | Integration branch | Work mode |\n|---|---|---|---|---|---|\n"
              "| hub | yes | x | main | main | d |\n| sib | no | x | dev | dev | d |\n| other | no | x | dev | dev | d |\n")
        write(self.hub / ".local/repos.map", f"hub: {self.hub}\nsib: {self.tmp / 'sib'}\nother: {self.tmp / 'other'}\n")

    def pack(self, tasks=("TST-1", "TST-2"), parallel=False, branches=None, **files):
        """Write each task (`files[ID]` is its text; a default one otherwise) and the pack; return `ready --pack` output."""
        for t in tasks:
            if files.get(t) is not False:
                write(self.hub / f"{TODO}/{t}-F_x.md", files.get(t) or READY.replace("TST-009", t))
        self.st.write_pack("p", {"name": "pk", "tasks": list(tasks), "parallel": parallel, "state": "new", "branches": branches or {}})
        return self.sup("ready", "--pack", "pk", "--profile", "p", "--hub", str(self.hub))

    def row(self, repos, files="src/a.py", extra=""):
        return READY.replace("| Task ID | TST-009 |", f"| Task ID | TST-009 |\n| Repos | {repos} |\n{extra}").replace("`src/a.py`", files)

    def lines(self, p):
        self.assertEqual(p.returncode, 3, p.stdout + p.stderr); return p.stdout.splitlines()

    def test_a_ready_pack_prints_ready_and_a_1_17_pack_without_branches_is_ready_too(self):
        p = self.pack(branches={"sib": "feat/x"}, **{"TST-1": self.row("`sib`", "`sib:x.py`, `src/a.py`")})
        self.assertEqual((p.returncode, p.stdout.strip()), (0, "ready"), p.stdout + p.stderr)
        p = self.pack(); self.assertEqual((p.returncode, p.stdout.strip()), (0, "ready"), p.stdout + p.stderr)

    def test_each_task_problem_is_one_line_with_its_id(self):
        pack = {"TST-1": False, "TST-2": READY.replace("Files: `src/a.py`\n", "")}
        out = self.lines(self.pack(**pack)); self.assertEqual(len(out), 2, out)
        self.assertTrue(out[0].startswith("TST-1: no task file") and out[1].startswith("TST-2: Phase 1: Build: no `Files:` line"), out)
        write(self.hub / f"{TODO}/TST-1-F_x.md", ""); (self.hub / f"{TODO}/TST-1-F_x.md").write_bytes(b"\xff\xfe")
        self.st.write_pack("p", {"name": "pk", "tasks": ["TST-1"], "state": "new"})
        out = self.lines(self.sup("ready", "--pack", "pk", "--profile", "p", "--hub", str(self.hub)))
        self.assertEqual(len(out), 1); self.assertIn("TST-1: TST-1-F_x.md cannot be read", out[0]); self.assertNotIn("Traceback", out[0])

    def test_slugs_of_the_repos_row_and_the_files_entries_must_be_pack_repos_and_in_the_repos_row(self):
        out = self.lines(self.pack(branches={"sib": "feat/x"}, **{"TST-1": self.row("`sib`, `other`"), "TST-2": self.row("`sib`", "`other:y.py`")}))
        self.assertEqual(len(out), 3, out)
        self.assertIn("TST-2: Phase 1: Build: `Files:` names repo 'other', which the `Repos` row does not have", out[0])  # task readiness first
        self.assertIn("TST-1: repo 'other' is not a repo of pack 'pk'", out[1])
        self.assertIn("TST-2: repo 'other' is not a repo of pack 'pk'", out[2])
        out = self.lines(self.pack(**{"TST-1": self.row("`sib`")}))  # a pack without branches
        self.assertEqual(len(out), 1); self.assertIn("TST-1: repo 'sib' is not a repo of pack 'pk' (its branches: none)", out[0])
        write(self.hub / ".local/repos.map", f"hub: {self.hub}\nsib: {self.tmp / 'sib'}\n")  # `other` has a registry row and no map line
        out = self.lines(self.pack(branches={"sib": "feat/x"}, **{"TST-1": self.row("`other`")})); self.assertEqual(len(out), 1); self.assertIn("repo 'other' is not a repo", out[0])
        p = self.pack(**{"TST-1": self.row("`hub`", "`hub:src/a.py`")}); self.assertEqual(p.stdout.strip(), "ready", p.stdout)  # the hub's own slug

    def test_a_repos_row_entry_that_is_no_registry_repo_is_a_problem_and_none_is_not(self):
        out = self.lines(self.pack(branches={"sib": "feat/x"}, **{"TST-1": self.row("`sib`, `other_repo`"), "TST-2": self.row("none")}))
        self.assertEqual(out, ["TST-1: `Repos` names 'other_repo', which the repo registry does not have"])

    def test_a_repos_word_that_only_the_map_has_is_a_problem_while_the_registry_exists_and_empty_cells_pass(self):
        write(self.hub / ".config/repos.project.md", "| Repo | Required | Role | Default branch | Integration branch | Work mode |\n|---|---|---|---|---|---|\n"
              "| hub | yes | x | main | main | d |\n| sib | no | x | dev | dev | d |\n")  # `other` is in the map only
        out = self.lines(self.pack(branches={"other": "f"}, **{"TST-1": self.row("`other`")}))
        self.assertEqual(out, ["TST-1: `Repos` names 'other', which the repo registry does not have"])
        for cell in ("none", "-", "—", ""):
            self.assertEqual(self.pack(**{"TST-1": self.row(cell)}).stdout.strip(), "ready", cell)

    def test_a_hub_whose_own_slug_the_map_does_not_give_is_judged_by_the_map_alone(self):
        (self.hub / ".local/repos.map").unlink()  # a 1.17.0 single-repo hub: a registry, no map
        p = self.pack(**{"TST-1": self.row("`hub`"), "TST-2": self.row("`sib`")}); self.assertEqual(p.stdout.strip(), "ready", p.stdout)
        write(self.hub / ".local/repos.map", f"sib: {self.tmp / 'sib'}\n")  # the map knows a sibling and not the hub
        out = self.lines(self.pack(**{"TST-1": self.row("`hub`"), "TST-2": self.row("`sib`")}))
        self.assertEqual(len(out), 1, out); self.assertIn("TST-2: repo 'sib' is not a repo of pack 'pk'", out[0])

    def test_a_blocker_that_names_a_phase_an_open_blocker_outside_the_pack_and_a_cycle_are_named(self):
        both = lambda a, b: {"TST-1": self.row("none", "src/a.py", f"| Blocked by | {a} |\n"), "TST-2": self.row("none", "src/b.py", f"| Blocked by | {b} |\n")}
        out = self.lines(self.pack(parallel=True, **both("TST-2 Phase 1", "TST-9")))
        self.assertEqual(len(out), 2, out); self.assertIn("TST-2 is blocked by TST-9", "".join(out))  # the edge refusal is one pack line
        self.assertIn("TST-1: `Blocked by` names a phase", "".join(out))
        out = self.lines(self.pack(parallel=True, **both("TST-2", "TST-1"))); self.assertEqual(len(out), 1); self.assertIn("cycle", out[0])
        same = {t: self.row("none", "src/a.py", "| Blocked by | TST-9 |\n") for t in ("TST-1", "TST-2")}
        self.assertEqual(len(self.lines(self.pack(parallel=True, **same))), 1)  # the edge refusal; no shared-file line while the edges are refused
        p = self.pack(parallel=True, **both("TST-2 (after its phase-out)", "none")); self.assertEqual(p.stdout.strip(), "ready", p.stdout)

    def test_a_resource_the_profile_lacks_is_named_and_a_listed_one_passes(self):
        t = {"TST-1": READY.replace("Resources: none", "Resources: lab 20m")}
        out = self.lines(self.pack(tasks=("TST-1",), **t)); self.assertEqual(len(out), 1); self.assertIn("TST-1: Resources: lab is not a resource of the profile", out[0])
        out = self.lines(self.pack(tasks=("TST-1",), **{"TST-1": t["TST-1"].replace("lab 20m", "lab")})); self.assertEqual(len(out), 1)  # no duration: one line
        out = self.lines(self.pack(tasks=("TST-1",), **{"TST-1": t["TST-1"].replace("lab 20m", "Lab_x 20m")})); self.assertIn("Resources: 'Lab_x' is not", out[0])
        write(self.st.profile_dir("p") / "conf/profile.json", "{not json")
        out = self.lines(self.pack(tasks=("TST-1",), **t)); self.assertEqual(len(out), 1); self.assertIn("profile.json cannot be read as a profile", out[0])
        write(self.st.profile_dir("p") / "conf/profile.json", json.dumps({"resources": [{"name": "lab"}]}))
        self.assertEqual(self.pack(tasks=("TST-1",), **t).stdout.strip(), "ready")

    def test_tasks_that_can_run_together_may_not_share_a_files_entry(self):
        def two(a, b, ra="none", rb="none", wait=""):
            return {"TST-1": self.row(ra, a), "TST-2": self.row(rb, b, wait)}
        for a, b in (("src/a.py", "src/a.py"), ("src/", "src"), ("src/", "src/a.py")):  # a directory and a file under it are shared
            with self.subTest((a, b)):
                out = self.lines(self.pack(parallel=True, **two(a, b))); self.assertEqual(len(out), 1)
                self.assertRegex(out[0], r"^pack pk: TST-1 and TST-2 can run together and both list `src(/a.py)?`$")
        out = self.lines(self.pack(parallel=True, **two("`hub:src/a.py`", "src/a.py", "`hub`")))  # the hub's own slug is the unqualified path
        self.assertEqual(out, ["pack pk: TST-1 and TST-2 can run together and both list `src/a.py`"])
        br = {"sib": "f", "other": "g"}
        ok = lambda **kw: self.assertEqual(self.pack(**kw).stdout.strip(), "ready")
        ok(parallel=True, branches=br, **two("`sib:x`", "`other:x`", "`sib`", "`other`"))  # same path in two repos
        ok(parallel=True, branches=br, **two("`sib:x.py`", "`sib:x.py`", "sib, `hub`", "`sib`"))  # the Repos cell is read as phase 1 reads it
        ok(parallel=False, **two("src/a.py", "src/a.py"))  # a serial pack never has two together
        ok(parallel=True, branches=br, **two("`sib:x`", "`sib:x`", "`sib`", "`sib`"))  # a shared pack repo: phase 1 serialises them
        ok(parallel=True, **two("src/a.py", "src/a.py", wait="| Blocked by | TST-1 |\n"))  # one waits for the other
        t = {"TST-1": self.row("none", "src/a.py"), "TST-2": self.row("none", "src/b.py", "| Blocked by | TST-1 |\n"),
             "TST-3": self.row("none", "src/a.py", "| Blocked by | TST-2 |\n")}
        ok(tasks=("TST-1", "TST-2", "TST-3"), parallel=True, **t)  # through another task
        t["TST-3"] = self.row("none", "src/a.py"); self.assertEqual(len(self.lines(self.pack(("TST-1", "TST-2", "TST-3"), parallel=True, **t))), 1)

    def test_no_hub_a_relative_map_path_and_a_missing_pack_never_raise(self):
        import sup; self.assertEqual(sup.pack_problems("p", {"name": "pk", "tasks": ["TST-1"]}, None), ["pack pk: the profile has no hub"])
        write(self.hub / ".local/repos.map", "sib: ../sib\n")
        out = self.lines(self.pack()); self.assertEqual(len(out), 1); self.assertIn("pack pk: repos.map: the path of 'sib' is not absolute", out[0])
        p = self.sup("ready", "--pack", "Bad_Name", "--profile", "p", "--hub", str(self.hub)); self.assertEqual((p.returncode, "Traceback" in p.stderr), (3, False))
        p = self.sup("ready", "--pack", "nope", "--profile", "p", "--hub", str(self.hub)); self.assertEqual((p.returncode, "Traceback" in p.stderr), (3, False))
        self.assertEqual(self.sup("ready", "TST-1", "--pack", "pk").returncode, 2); self.assertEqual(self.sup("ready").returncode, 2)


class Ready(Base):
    def check(self, text):
        write(self.hub / TODO / "TST-009-F_x.md", text); return self.sup("ready", "TST-009")

    def test_complete_task_is_ready(self):
        p = self.check(READY); self.assertEqual((p.returncode, p.stdout.strip()), (0, "ready"), p.stdout + p.stderr)

    def test_each_missing_item_is_named(self):
        cases = [("files", "Files: `src/a.py`\n", "", "no `Files:` line"),
                 ("check", "- Checks: `python3 -m unittest`\n", "", "names no check"),
                 ("phase", "#### Phase 1: Build", "#### Phase 1a: Build", "not `Phase <integer>`"),
                 ("no phase", "#### Phase 1: Build", "", "no `#### Phase <integer>` heading"),
                 ("criteria", "- [ ] works", "works", "acceptance criteria"),
                 ("authorised", "Authorised: restart the dev server\n", "", "`Authorised:`"),
                 ("owner", "Owner only: push\n", "", "`Owner only:`"),
                 ("defaults", "Defaults: if X, do Y\n", "", "`Defaults:`"),
                 ("section", "### Unattended run", "### Other", "`### Unattended run`"),
                 ("resources", "Resources: none\n", "", "`Resources:`")]
        for name, old, new, expect in cases:
            with self.subTest(name):
                p = self.check(READY.replace(old, new, 1)); self.assertEqual(p.returncode, 3, p.stdout); self.assertIn(expect, p.stdout)

    def test_prose_in_files_names_the_entry(self):
        p = self.check(READY.replace("Files: `src/a.py`", "Files: all of the sources", 1))
        self.assertEqual(p.returncode, 3); self.assertIn("plain relative path", p.stdout); self.assertIn("all of the sources", p.stdout)
        self.assertNotIn("no `Files:` line", p.stdout)

    def test_related_tests_section_counts_as_a_check(self):
        text = READY.replace("- Checks: `python3 -m unittest`\n", "").replace("### Unattended", "### Related tests\n\n- `tests/test_a.py`\n\n### Unattended")
        self.assertEqual(self.check(text).stdout.strip(), "ready")

    def test_resource_needs_a_duration(self):
        p = self.check(READY.replace("Resources: none", "Resources: lab")); self.assertEqual(p.returncode, 3); self.assertIn("`lab` has no duration", p.stdout)
        self.assertEqual(self.check(READY.replace("Resources: none", "Resources: lab 20m")).stdout.strip(), "ready")

    def test_a_files_entry_with_a_slug_needs_the_slug_in_the_repos_row(self):
        text = READY.replace("`src/a.py`", "`sib:src/a.py`")
        p = self.check(text); self.assertEqual(p.returncode, 3); self.assertIn("names repo 'sib', which the `Repos` row does not have", p.stdout)
        self.assertEqual(self.check(text.replace("| Task ID | TST-009 |", "| Task ID | TST-009 |\n| Repos | `sib` |")).stdout.strip(), "ready")
        p = self.check(text.replace("sib:src", "sib:../src")); self.assertIn("plain relative path", p.stdout)

    def test_a_heading_is_cut_and_cleaned_in_the_line(self):
        p = self.check(READY.replace("#### Phase 1: Build", "#### Phase 1a: B\x1b[31m" + "x" * 80)); self.assertEqual(p.returncode, 3)
        self.assertNotIn("\x1b", p.stdout); self.assertTrue(all(len(l) < 200 for l in p.stdout.splitlines()))

    def test_child_inherits_parent_unattended_section(self):
        child = READY.replace("TST-009", "TST-010").replace("| Task ID | TST-010 |", "| Task ID | TST-010 |\n| Parent | TST-009 |")
        child = child[:child.index("### Unattended")]
        write(self.hub / TODO / "TST-009-F_x.md", READY); write(self.hub / TODO / "TST-010-F_x.md", child)
        self.assertEqual(self.sup("ready", "TST-010").stdout.strip(), "ready")


if __name__ == "__main__":
    unittest.main()
