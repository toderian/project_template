import os, subprocess, shutil, tempfile, unittest, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
AT = ROOT / "plugins/agents-core/bin/at"
FAKE = ROOT / "scripts/tests/fixtures/fake-harness.py"
FIX = ROOT / "scripts/tests/fixtures/task-brief"
STATE = "docs/tasks_manager/_runs/TST-003/state.md"
def repo():
    tmp = pathlib.Path(tempfile.mkdtemp()); shutil.copytree(FIX, tmp, dirs_exist_ok=True)
    (tmp / ".gitignore").write_text("docs/tasks_manager/_runs/**/diff.patch\n")
    g = lambda *a: subprocess.run(["git", "-C", str(tmp), "-c", "user.name=t", "-c", "user.email=t@t", *a], capture_output=True, text=True, check=True)
    g("init", "-q"); g("add", "-A"); g("commit", "-q", "-m", "base"); return tmp
def run(tmp, *args, scenario="pass", harness="claude"):
    env = dict(os.environ, AT_TASKS_ROOT=str(ROOT / "plugins/agents-tasks"), FAKE_SCENARIO=scenario, FAKE_CALLS=str(tmp.parent / (tmp.name + ".calls")))
    return subprocess.run([str(AT), "task", "run", "TST-003", "--harness", harness, "--driver-cmd", str(FAKE), *args],
                          cwd=str(tmp), capture_output=True, text=True, env=env)
def log(tmp): return subprocess.run(["git", "-C", str(tmp), "log", "--oneline"], capture_output=True, text=True).stdout
class TaskRun(unittest.TestCase):
    def test_runs_all_phases_commits_each_and_records_state(self):
        tmp = repo(); p = run(tmp); self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        commits = log(tmp).splitlines()
        self.assertEqual(sum("TST-003 phase" in c for c in commits), 3, commits)
        self.assertIn("run state", commits[0])
        s = (tmp / STATE).read_text(); self.assertEqual(s.count("| committed |"), 3); self.assertIn("runtime: claude", s)
        self.assertTrue((tmp / "docs/tasks_manager/_runs/TST-003/phase-2/brief.md").exists())
        self.assertTrue((tmp / "docs/tasks_manager/_runs/TST-003/phase-2/review-quality.md").exists())
        task = next((tmp / "docs/tasks_manager/_todos").glob("TST-003-*.md")).read_text()
        self.assertNotIn("- [ ]", task.split("### Acceptance criteria")[0]); self.assertIn("Phase 3: Hardening (at task run", task)
        calls = (tmp.parent / (tmp.name + ".calls")).read_text()
        self.assertIn("reviewer|spec|1|claude|resume=False|ro=True", calls); self.assertIn("reviewer|final-1|0|claude", calls)
        self.assertEqual(subprocess.run(["git", "-C", str(tmp), "status", "--porcelain"], capture_output=True, text=True).stdout.strip(), "")
    def test_fix_round_resumes_implementer_then_passes(self):
        tmp = repo(); p = run(tmp, "--phase", "1", scenario="fail-once"); self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertTrue((tmp / "docs/tasks_manager/_runs/TST-003/phase-1/findings-1.md").exists())
        calls = (tmp.parent / (tmp.name + ".calls")).read_text()
        self.assertIn("implementer||1|claude|resume=True", calls); self.assertIn("fix round 1/3", (tmp / STATE).read_text())
    def test_codex_harness_uses_fresh_dispatch_and_read_only_reviews(self):
        tmp = repo(); p = run(tmp, "--phase", "1", scenario="fail-once", harness="codex"); self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        calls = (tmp.parent / (tmp.name + ".calls")).read_text()
        self.assertIn("implementer||1|codex|resume=False", calls); self.assertNotIn("resume=True", calls); self.assertIn("reviewer|quality|1|codex|resume=False|ro=True", calls)
    def test_missing_status_blocks_the_phase(self):
        tmp = repo(); p = run(tmp, scenario="no-status"); self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        s = (tmp / STATE).read_text(); self.assertIn("| 1 | blocked |", s); self.assertIn("returned MISSING", s)
        self.assertNotIn("TST-003 phase", log(tmp))
        p2 = run(tmp); self.assertEqual(p2.returncode, 1); self.assertIn("--retry-blocked", p2.stdout)
    def test_dirty_tree_and_dry_run(self):
        tmp = repo(); (tmp / "junk.txt").write_text("x"); p = run(tmp); self.assertEqual(p.returncode, 1); self.assertIn("outside the run directory", p.stderr)
        (tmp / "junk.txt").unlink(); p = run(tmp, "--dry-run"); self.assertEqual(p.returncode, 0, p.stderr); self.assertIn("[dry-run] phase 3", p.stdout)
        self.assertFalse((tmp.parent / (tmp.name + ".calls")).exists())
    def test_resume_skips_committed_phases(self):
        tmp = repo(); self.assertEqual(run(tmp, "--phase", "1").returncode, 0)
        p = run(tmp); self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertNotIn("phase 1: implementer", p.stdout); self.assertEqual(sum("TST-003 phase" in c for c in log(tmp).splitlines()), 3)
if __name__ == "__main__": unittest.main()
