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

    def test_child_inherits_parent_unattended_section(self):
        child = READY.replace("TST-009", "TST-010").replace("| Task ID | TST-010 |", "| Task ID | TST-010 |\n| Parent | TST-009 |")
        child = child[:child.index("### Unattended")]
        write(self.hub / TODO / "TST-009-F_x.md", READY); write(self.hub / TODO / "TST-010-F_x.md", child)
        self.assertEqual(self.sup("ready", "TST-010").stdout.strip(), "ready")


if __name__ == "__main__":
    unittest.main()
