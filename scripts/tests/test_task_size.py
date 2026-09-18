import os, subprocess, shutil, tempfile, unittest, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
AT = ROOT / "plugins/agents-core/bin/at"
sys.path.insert(0, str(ROOT / "plugins/agents-core/lib"))
import task_size  # noqa: E402
RUNS = "docs/tasks_manager/_runs/TST-009"
STATE = ("---\ntask: TST-009\ntask_file: docs/tasks_manager/_todos/TST-009-F_x.md\nbase_rev: {base}\n---\n# Run ledger — TST-009\n\n"
         "| Phase | Status | Attempt | Spec | Quality | Security | Open | Commit | Agent |\n|---|---|---|---|---|---|---|---|---|\n"
         "| 1 | implementing | 1 | — | — | n/a | 0 | — | implementer |\n\nPhase 1: BASE {base}; attempt 1 (claude)\n")
TASK = "| Field | Value |\n|---|---|\n| Task ID | TST-009 |\n\n## X\n\n### Phases\n\n#### Phase 1: Dedup\n\nShape: b.py net shrinks; ≤ ~100 code lines\n\n- [ ] item\n\n#### Phase 2: More\n\n- [ ] item\n"
def repo():
    tmp = pathlib.Path(tempfile.mkdtemp())
    g = lambda *a: subprocess.run(["git", "-C", str(tmp), "-c", "user.name=t", "-c", "user.email=t@t", *a], capture_output=True, text=True, check=True)
    g("init", "-q")
    (tmp / "src").mkdir(); (tmp / "tests").mkdir(); (tmp / "docs/tasks_manager/_todos").mkdir(parents=True)
    (tmp / "src/a.py").write_text("\n".join(f"a{i}" for i in range(100)) + "\n")
    (tmp / "src/b.py").write_text("\n".join(f"b{i}" for i in range(200)) + "\n")
    (tmp / "tests/test_a.py").write_text("t\n")
    (tmp / "docs/tasks_manager/_todos/TST-009-F_x.md").write_text(TASK)
    (tmp / ".gitignore").write_text("docs/tasks_manager/_runs/**/size*.md\n")
    g("add", "-A"); g("commit", "-q", "-m", "base")
    base = subprocess.run(["git", "-C", str(tmp), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    (tmp / RUNS).mkdir(parents=True); (tmp / RUNS / "state.md").write_text(STATE.format(base=base))
    return tmp, base
def at(tmp, *args):
    return subprocess.run([str(AT), "task", "size", "TST-009", *args], cwd=str(tmp), capture_output=True, text=True,
                          env=dict(os.environ, AT_TASKS_ROOT=str(ROOT / "plugins/agents-tasks")))
class TaskSize(unittest.TestCase):
    def test_measures_grown_new_shrunk_and_test_files_and_flags(self):
        tmp, base = repo()
        (tmp / "src/a.py").write_text("\n".join(f"a{i}" for i in range(160)) + "\n")      # +60 = +60 % → flagged
        (tmp / "src/new.py").write_text("\n".join(f"n{i}" for i in range(130)) + "\n")    # new, 130 ≥ 120 → flagged
        (tmp / "src/small.py").write_text("x\n")                                           # new, small → not flagged
        (tmp / "tests/test_a.py").write_text("\n".join(f"t{i}" for i in range(300)) + "\n")  # test growth never flagged
        (tmp / "runs.bin").write_bytes(b"\x00\x01\xff")
        (tmp / "docs/guide.md").write_text("\n".join(f"d{i}" for i in range(200)) + "\n")   # docs: never flagged, own net
        subprocess.run(["git", "-C", str(tmp), "mv", "src/b.py", "src/b2.py"], check=True)      # rename + shrink: measured on new path
        p = at(tmp, "--phase", "1"); self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        out = (tmp / RUNS / "phase-1/size.md").read_text()
        self.assertIn("Shape: b.py net shrinks; ≤ ~100 code lines", out)
        self.assertIn("| src/a.py | 100 | 160 | +60 | code |", out)
        (tmp / "src/b2.py").write_text("\n".join(f"b{i}" for i in range(150)) + "\n")
        p = at(tmp, "--phase", "1"); out = (tmp / RUNS / "phase-1/size.md").read_text()
        self.assertIn("| src/b.py | 200 | 0 | -200 (deleted) | code |", out); self.assertIn("| src/b2.py | 0 | 150 | +150 (new) | code |", out)
        self.assertIn("| docs/guide.md | 0 | 200 | +200 (new) | docs |", out); self.assertNotIn("guide.md", out.split("Flagged:")[1])
        self.assertIn("| src/new.py | 0 | 130 | +130 (new) | code |", out)
        self.assertIn("| tests/test_a.py | 1 | 300 | +299 | test |", out)
        self.assertIn("| runs.bin | – | – | binary | binary |", out)
        self.assertIn("Code net +141 (5 files). Test net +299 (1 files). Docs net +200 (1 files).", out)
        self.assertIn("Flagged: b2.py (new, 150), new.py (new, 130), a.py (+60 %, +60)", out)
        self.assertNotIn("small.py", out.split("Flagged:")[1]); self.assertNotIn("test_a", out.split("Flagged:")[1])
        self.assertIn("-> docs/tasks_manager/_runs/TST-009/phase-1/size.md", p.stdout)
    def test_no_changes_and_thresholds(self):
        tmp, base = repo()
        p = at(tmp, "--phase", "1"); self.assertEqual(p.returncode, 0, p.stderr); self.assertIn("No changes.", p.stdout)
        (tmp / "src/a.py").write_text("\n".join(f"a{i}" for i in range(139)) + "\n")  # +39 lines: under the 40 floor
        r = task_size.measure(tmp, base); self.assertEqual(r.flagged(), [])
        (tmp / "src/b.py").write_text("\n".join(f"b{i}" for i in range(245)) + "\n")  # +45 lines but +22 %: under the 25 % floor
        r = task_size.measure(tmp, base); self.assertEqual(r.flagged(), [])
        (tmp / "src/c.py").write_text("\n".join(f"c{i}" for i in range(300)) + "\n")  # phase code net ≥ 300
        r = task_size.measure(tmp, base); self.assertIn("code net +384 ≥ 300", r.flagged()); self.assertIn("c.py (new, 300)", r.flagged())
    def test_fix_round_reports_only_what_the_round_changed(self):
        tmp, base = repo()
        (tmp / "src/a.py").write_text("\n".join(f"a{i}" for i in range(110)) + "\n")   # phase work: a +10
        self.assertEqual(at(tmp, "--phase", "1").returncode, 0)
        (tmp / "src/a.py").write_text("\n".join(f"a{i}" for i in range(140)) + "\n")   # fix 1: a +30 more
        (tmp / "src/b.py").write_text("\n".join(f"b{i}" for i in range(190)) + "\n")   # fix 1: b −10
        (tmp / "tests/test_a.py").write_text("t\nt\nt\n")                              # fix 1: test +2
        p = at(tmp, "--phase", "1", "--fix", "1"); self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        out = (tmp / RUNS / "phase-1/size-fix-1.md").read_text()
        self.assertIn("phase 1 fix round 1", out); self.assertIn("| src/a.py | 110 | 140 | +30 | code |", out)
        self.assertIn("| src/b.py | 200 | 190 | -10 | code |", out); self.assertIn("Fix round 1: code net +20 in a.py +30", out)
        (tmp / "src/a.py").write_text("\n".join(f"a{i}" for i in range(110)) + "\n")   # fix 2: a back to +10, b untouched
        p = at(tmp, "--phase", "1", "--fix", "2"); self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        out = (tmp / RUNS / "phase-1/size-fix-2.md").read_text()
        self.assertIn("| src/a.py | 140 | 110 | -30 | code |", out); self.assertNotIn("src/b.py", out)
        self.assertIn("Fix round 2: code net -30 in none", out)
        (tmp / "src/a.py").write_text("\n".join(f"a{i}" for i in range(100)) + "\n")   # fix 3: a fully reverted to base
        p = at(tmp, "--phase", "1", "--fix", "3"); self.assertIn("| src/a.py | 110 | 100 | -10 | code |", (tmp / RUNS / "phase-1/size-fix-3.md").read_text())
        (tmp / RUNS / "phase-1/size-fix-3.md").unlink(); (tmp / "src/a.py").write_text("\n".join(f"a{i}" for i in range(110)) + "\n")
        # --base REV measures the fix from a committed pre-fix state instead of the previous size file
        (tmp / RUNS / "state.md").write_text(STATE.format(base=base).replace(f"Phase 1: BASE {base}", "Phase 1: attempt 1"))  # no BASE line: --base suffices
        p = at(tmp, "--phase", "1", "--fix", "3", "--base", base); self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("Fix round 3: code net +0 in a.py +10", (tmp / RUNS / "phase-1/size-fix-3.md").read_text())
        (tmp / RUNS / "state.md").write_text(STATE.format(base=base))
        (tmp / RUNS / "phase-1/size-fix-3.md").unlink()
        p = at(tmp, "--phase", "1", "--fix", "4"); self.assertEqual(p.returncode, 2); self.assertIn("no previous size file size-fix-3.md", p.stdout)
    def test_final_uses_base_rev_and_bad_base_exits_2(self):
        tmp, base = repo()
        (tmp / "src/a.py").write_text("a\n")
        p = at(tmp, "--final"); self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("TST-009 whole run", (tmp / RUNS / "size.md").read_text()); self.assertIn("| src/a.py | 100 | 1 | -99 | code |", p.stdout)
        p = at(tmp, "--final", "--base", "deadbeef"); self.assertEqual(p.returncode, 2); self.assertIn("base revision not found", p.stdout)
        (tmp / RUNS / "state.md").write_text(STATE.format(base=base).replace(f"Phase 1: BASE {base}", "Phase 1: attempt 1"))
        p = at(tmp, "--phase", "1"); self.assertEqual(p.returncode, 2); self.assertIn("no `Phase 1: BASE <rev>` line", p.stdout)
        self.assertEqual(task_size.phase_shape(tmp / "docs/tasks_manager/_todos/TST-009-F_x.md", 2), [])
if __name__ == "__main__":
    unittest.main()
