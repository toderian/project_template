import subprocess, shutil, tempfile, unittest, pathlib
SCRIPT = pathlib.Path(__file__).resolve().parents[2] / "plugins/agents-tasks/skills/task-ledger/scripts/sync_todo_ledgers.py"
FIX = pathlib.Path(__file__).resolve().parent / "fixtures"
def run(fixture, *args):
    tmp = pathlib.Path(tempfile.mkdtemp()); shutil.copytree(FIX / fixture, tmp, dirs_exist_ok=True)
    p = subprocess.run(["python3", str(SCRIPT), "--root", str(tmp), *args], capture_output=True, text=True)
    return p, tmp
class Ledger(unittest.TestCase):
    def test_legacy_full_table_checks_clean(self):
        p, _ = run("ledger-legacy", "--check"); self.assertEqual(p.returncode, 0, p.stderr)
    def test_minimal_table_checks_clean(self):
        p, _ = run("ledger-minimal", "--check"); self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn("missing Owner", p.stderr); self.assertNotIn("missing Last executed", p.stderr)
    def test_oversized_log_warns(self):
        p, _ = run("ledger-minimal", "--check"); self.assertIn("execution log exceeds 200 lines", p.stderr)
    def test_rotate_log_moves_body_and_leaves_pointer(self):
        p, tmp = run("ledger-minimal", "rotate-log", "TST-002")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue((tmp / "docs/tasks_manager/_logs/TST-002.md").exists())
        task = next((tmp / "docs/tasks_manager/_todos").glob("TST-002-*.md")).read_text()
        self.assertIn("_logs/TST-002.md", task); self.assertLess(task.count("\n"), 120)
    def test_rotate_log_is_idempotent(self):
        p1, tmp = run("ledger-minimal", "rotate-log", "TST-002")
        self.assertEqual(p1.returncode, 0, p1.stderr)
        log_path = tmp / "docs/tasks_manager/_logs/TST-002.md"
        lines_after_first = log_path.read_text().count("\n")
        p2 = subprocess.run(
            ["python3", str(SCRIPT), "--root", str(tmp), "rotate-log", "TST-002"],
            capture_output=True, text=True,
        )
        self.assertEqual(p2.returncode, 0, p2.stderr)
        lines_after_second = log_path.read_text().count("\n")
        self.assertEqual(lines_after_first, lines_after_second)
        self.assertEqual(log_path.read_text().count("# Execution log — TST-002"), 1)
        task = next((tmp / "docs/tasks_manager/_todos").glob("TST-002-*.md")).read_text()
        self.assertEqual(task.count("See [_logs/TST-002.md]"), 1)
    def test_missing_harvest_is_warning_not_error(self):
        # ledger-legacy has a second archived task without harvest section
        p, _ = run("ledger-legacy", "--check"); self.assertEqual(p.returncode, 0); self.assertIn("Completion harvest", p.stderr)
    def test_sync_writes_ledgers(self):
        p, tmp = run("ledger-minimal"); self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("TST-001", (tmp / "docs/tasks_manager/_active.md").read_text())
if __name__ == "__main__": unittest.main()
