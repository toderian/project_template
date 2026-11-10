import subprocess, shutil, tempfile, unittest, pathlib
SCRIPT = pathlib.Path(__file__).resolve().parents[2] / "plugins/agents-tasks/skills/task-ledger/scripts/sync_todo_ledgers.py"
FIX = pathlib.Path(__file__).resolve().parent / "fixtures"
def run(fixture, *args):
    tmp = pathlib.Path(tempfile.mkdtemp()); shutil.copytree(FIX / fixture, tmp, dirs_exist_ok=True)
    p = subprocess.run(["python3", str(SCRIPT), "--root", str(tmp), *args], capture_output=True, text=True)
    return p, tmp
def backlog(wip, updated, ideas, captured):
    """A copy of ledger-minimal plus `wip` in_progress tasks and `ideas` new inbox ideas."""
    tmp = pathlib.Path(tempfile.mkdtemp()); shutil.copytree(FIX / "ledger-minimal", tmp, dirs_exist_ok=True)
    tm = tmp / "docs/tasks_manager"
    (tm / "_todos/TST-002-C_oversized-execution-log.md").unlink()
    source = (tm / "_todos/TST-001-F_minimal-metadata-task.md").read_text()
    for n in range(wip):
        text = source.replace("TST-001", f"TST-01{n}").replace("| open  ", "| in_progress")
        text = text.replace("| Updated  | 2026-08-10T09:00:00", f"| Updated  | {updated}T09:00:00")
        (tm / f"_todos/TST-01{n}-F_minimal-metadata-task.md").write_text(text)
    (tm / "_inbox").mkdir(exist_ok=True)
    for n in range(1, ideas + 1):
        (tm / f"_inbox/I-{n:03d}_idea.md").write_text(
            f"| Field | Value |\n|---|---|\n| Inbox ID | I-{n:03d} |\n| Captured | {captured}T09:00:00 |\n"
            f"| Area | tst |\n| Status | new |\n\n## Idea {n}\n")
    return tmp
def sync(tmp, today, *args):
    return subprocess.run(["python3", str(SCRIPT), "--root", str(tmp), *args], capture_output=True, text=True,
                          env={**__import__("os").environ, "AT_TODAY": today})
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
    def test_rotate_all_moves_only_oversized_logs(self):
        p, tmp = run("ledger-minimal", "rotate-log", "--all")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("rotated 1 execution log(s)", p.stdout)
        logs = sorted(x.name for x in (tmp / "docs/tasks_manager/_logs").glob("*.md"))
        self.assertEqual(logs, ["TST-002.md"])
        p2 = subprocess.run(["python3", str(SCRIPT), "--root", str(tmp), "rotate-log", "--all"],
                            capture_output=True, text=True)
        self.assertEqual(p2.returncode, 0, p2.stderr)
        self.assertIn("rotated 0 execution log(s)", p2.stdout)
    def test_sync_rotates_oversized_logs(self):
        p, tmp = run("ledger-minimal")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue((tmp / "docs/tasks_manager/_logs/TST-002.md").exists())
        self.assertNotIn("execution log exceeds", p.stderr)
        p2 = subprocess.run(["python3", str(SCRIPT), "--root", str(tmp), "--check"],
                            capture_output=True, text=True)
        self.assertEqual(p2.returncode, 0, p2.stderr)
        self.assertNotIn("execution log exceeds", p2.stderr)
    def test_check_never_rotates(self):
        p, tmp = run("ledger-minimal", "--check")
        self.assertIn("at ledger rotate-log TST-002, or --all", p.stderr)
        self.assertFalse((tmp / "docs/tasks_manager/_logs").exists())
        p2 = subprocess.run(["python3", str(SCRIPT), "--root", str(tmp), "--check", "rotate-log", "--all"],
                            capture_output=True, text=True)
        self.assertEqual(p2.returncode, 2)
        self.assertFalse((tmp / "docs/tasks_manager/_logs").exists())
    def test_backlog_health_is_quiet_on_a_small_fresh_backlog(self):
        tmp = backlog(wip=2, updated="2026-08-10", ideas=3, captured="2026-08-05")
        p = sync(tmp, "2026-08-20")
        self.assertEqual(p.returncode, 0, p.stderr)
        for needle in ("untriaged", "in_progress at once", "not updated for more than"):
            self.assertNotIn(needle, p.stderr)
    def test_backlog_health_warns_on_stale_inbox_wip_and_stalled_work(self):
        tmp = backlog(wip=6, updated="2026-08-10", ideas=3, captured="2026-08-05")
        p = sync(tmp, "2026-10-01")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("inbox holds 3 untriaged idea(s), oldest I-001 captured 57 days ago", p.stderr)
        self.assertIn("agents-tasks:triage-inbox", p.stderr)
        self.assertIn("6 tasks are in_progress at once, more than 5", p.stderr)
        self.assertIn("6 in_progress task(s) not updated for more than 30 days, oldest first: TST-010, TST-011, TST-012",
                      p.stderr)
        check = sync(tmp, "2026-10-01", "--check")
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertIn("in_progress at once", check.stderr)
    def test_backlog_health_counts_a_large_fresh_inbox(self):
        tmp = backlog(wip=0, updated="2026-08-10", ideas=21, captured="2026-08-19")
        p = sync(tmp, "2026-08-20")
        self.assertIn("inbox holds 21 untriaged idea(s), oldest I-001 captured 1 days ago", p.stderr)
        self.assertNotIn("in_progress", p.stderr)
    def test_missing_harvest_is_warning_not_error(self):
        # ledger-legacy has a second archived task without harvest section
        p, _ = run("ledger-legacy", "--check"); self.assertEqual(p.returncode, 0); self.assertIn("Completion harvest", p.stderr)
    def test_wayfinder_map_checks_clean(self):
        p, _ = run("wayfinder-map", "--check"); self.assertEqual(p.returncode, 0, p.stderr)
    def test_wayfinder_ticket_rows_do_not_override_task_metadata(self):
        # The tickets index says claimed/resolved; the task itself must stay open with 1/3 phases,
        # because ticket rows lead with a `Ticket` column and ticket bodies use `###`, not `####`.
        p, tmp = run("wayfinder-map"); self.assertEqual(p.returncode, 0, p.stderr)
        row = [l for l in (tmp / "docs/tasks_manager/_active.md").read_text().splitlines() if "TST-003" in l][0]
        self.assertIn("| open |", row); self.assertIn("| 1/3 |", row)
    def test_run_dir_for_archived_task_warns(self):
        p, _ = run("ledger-legacy", "--check"); self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("_runs/TST-002 outlives archived task TST-002", p.stderr)
    def test_run_dir_for_active_task_is_silent(self):
        p, _ = run("ledger-minimal", "--check"); self.assertNotIn("_runs/TST-001", p.stderr)
    def test_run_dir_without_task_warns(self):
        tmp = pathlib.Path(tempfile.mkdtemp()); shutil.copytree(FIX / "ledger-minimal", tmp, dirs_exist_ok=True)
        (tmp / "docs/tasks_manager/_runs/TST-099").mkdir()
        p = subprocess.run(["python3", str(SCRIPT), "--root", str(tmp), "--check"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr); self.assertIn("_runs/TST-099 has no matching task", p.stderr)
    def test_sync_writes_ledgers(self):
        p, tmp = run("ledger-minimal"); self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("TST-001", (tmp / "docs/tasks_manager/_active.md").read_text())
if __name__ == "__main__": unittest.main()
