import subprocess, shutil, tempfile, unittest, pathlib
SCRIPT = pathlib.Path(__file__).resolve().parents[2] / "plugins/agents-tasks/skills/task-ledger/scripts/task_brief.py"
FIX = pathlib.Path(__file__).resolve().parent / "fixtures" / "task-brief"
def fresh(git=False):
    tmp = pathlib.Path(tempfile.mkdtemp()); shutil.copytree(FIX, tmp, dirs_exist_ok=True)
    if git:
        subprocess.run(["git", "-C", str(tmp), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(tmp), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "base"], check=True)
    return tmp
def run(tmp, *args):
    return subprocess.run(["python3", str(SCRIPT), "--root", str(tmp), *args], capture_output=True, text=True)
STATE = "docs/tasks_manager/_runs/TST-003/state.md"
class Brief(unittest.TestCase):
    def test_phase_2_brief_contains_only_that_phase(self):
        tmp = fresh(); p = run(tmp, "brief", "TST-003", "--phase", "2", "--out", "-")
        self.assertEqual(p.returncode, 0, p.stderr); b = p.stdout
        self.assertIn("#### Phase 2: Implementation", b); self.assertIn("Add `WidgetValidator`", b)
        self.assertNotIn("Phase 1: Current-state review", b); self.assertNotIn("Phase 3: Hardening", b)
        self.assertNotIn("SECRET-LOG-MARKER", b); self.assertNotIn("Completion", b)
        for h in ("## Acceptance criteria", "## Related tests", "## Specification", "## Design", "## Spec refs",
                  "## Orchestrator notes", "## Report contract", "| Repos | demo-service |", "| Spec refs |"):
            self.assertIn(h, b)
        self.assertIn("Report path: `docs/tasks_manager/_runs/TST-003/phase-2/report.md`", b)
        self.assertIn("- `docs/resources/demo/contracts/widget.md`", b)
    def test_brief_writes_default_path_and_refuses_overwrite(self):
        tmp = fresh(); p = run(tmp, "brief", "TST-003", "--phase", "1"); self.assertEqual(p.returncode, 0, p.stderr)
        out = tmp / "docs/tasks_manager/_runs/TST-003/phase-1/brief.md"; self.assertTrue(out.exists())
        p2 = run(tmp, "brief", "TST-003", "--phase", "1"); self.assertEqual(p2.returncode, 1); self.assertIn("--force", p2.stderr)
        p3 = run(tmp, "brief", "TST-003", "--phase", "1", "--force"); self.assertEqual(p3.returncode, 0, p3.stderr)
    def test_phase_out_of_range_and_unknown_task_fail(self):
        tmp = fresh()
        self.assertEqual(run(tmp, "brief", "TST-003", "--phase", "4").returncode, 2)
        p = run(tmp, "brief", "TST-999", "--phase", "1"); self.assertEqual(p.returncode, 1); self.assertIn("no task file", p.stderr)
class RunState(unittest.TestCase):
    def test_init_writes_one_row_per_phase_and_check_passes(self):
        tmp = fresh(git=True); p = run(tmp, "run-state", "init", "TST-003", "--runtime", "claude", "--base", "abc1234")
        self.assertEqual(p.returncode, 0, p.stderr); s = (tmp / STATE).read_text()
        self.assertEqual(s.count("| pending |"), 3); self.assertIn("current_phase: 1", s); self.assertIn("runtime: claude", s)
        c = run(tmp, "run-state", "check", "TST-003"); self.assertEqual(c.returncode, 0, c.stderr); self.assertIn("OK run state valid", c.stdout)
        self.assertEqual(run(tmp, "run-state", "init", "TST-003").returncode, 1)
    def test_check_rejects_bad_status_missing_commit_and_bad_ledger_line(self):
        tmp = fresh(git=True); run(tmp, "run-state", "init", "TST-003")
        s = (tmp / STATE).read_text().replace("| 1 | pending | 0 | — | — | — | 0 | — | — |", "| 1 | flying | 1 | PASS | PASS | n/a | 0 | deadbeef | — |")
        (tmp / STATE).write_text(s + "Random: not a ledger line\n")
        c = run(tmp, "run-state", "check", "TST-003"); self.assertEqual(c.returncode, 1)
        self.assertIn("status 'flying'", c.stderr); self.assertIn("deadbeef does not exist", c.stderr); self.assertIn("ledger line must start", c.stderr)
    def test_check_accepts_real_commit_and_ruling_lines(self):
        tmp = fresh(git=True); run(tmp, "run-state", "init", "TST-003")
        sha = subprocess.run(["git", "-C", str(tmp), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
        s = (tmp / STATE).read_text().replace("| 1 | pending | 0 | — | — | — | 0 | — | — |", f"| 1 | committed | 1 | PASS | PASS | n/a | 0 | {sha} | — |")
        (tmp / STATE).write_text(s + "Phase 1: complete (review clean)\nRuling: keep helper — smaller diff — cost if wrong: duplicate parsing\nInterface: Validator.validate(w) -> Result\n")
        c = run(tmp, "run-state", "check", "TST-003"); self.assertEqual(c.returncode, 0, c.stderr)
    def test_check_without_git_only_warns_on_commit(self):
        tmp = fresh(); run(tmp, "run-state", "init", "TST-003")
        s = (tmp / STATE).read_text().replace("| 1 | pending | 0 | — | — | — | 0 | — | — |", "| 1 | committed | 1 | PASS | PASS | n/a | 0 | abc1234 | — |")
        (tmp / STATE).write_text(s); c = run(tmp, "run-state", "check", "TST-003")
        self.assertEqual(c.returncode, 0, c.stderr); self.assertIn("not verified", c.stderr)
    def test_check_without_state_fails(self):
        tmp = fresh(); c = run(tmp, "run-state", "check", "TST-003"); self.assertEqual(c.returncode, 1); self.assertIn("run-state init", c.stderr)
if __name__ == "__main__": unittest.main()
