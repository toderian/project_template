"""`at explore`: the exploratory-test coverage ledger and finding fingerprints."""
import os, pathlib, subprocess, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[2]
AT = ROOT / "plugins/agents-core/bin/at"
LEAF = ("# Feedback\n\n### FBK-01 One toast\n\n- **Check.** Is there one toast?\n- **Holds.** Yes.\n\n"
        "### FBK-02 Later\n\n- **Check.** Is it announced?\n- **Holds.** Target.\n\n"
        "### FBK-03 Partly\n\n- **Check.** Does it close?\n- **Holds.** Partly, 3 of 5.\n")
def repo():
    tmp = pathlib.Path(tempfile.mkdtemp())
    subprocess.run(["git", "-C", str(tmp), "init", "-q"], check=True)
    for d in ("docs/resources/shop/design/ux", "docs/tasks_manager/_inbox", "tests/e2e-explore"):
        (tmp / d).mkdir(parents=True)
    (tmp / "docs/resources/shop/design/ux/feedback.md").write_text(LEAF)
    (tmp / "tests/e2e-explore/cells.tsv").write_text("cell\tleaf\texpected\nROLE:buy:guest\troles.md\trefused\n")
    return tmp
def at(tmp, *args):
    return subprocess.run([str(AT), "explore", *args], cwd=str(tmp), capture_output=True, text=True,
                          env=dict(os.environ, AT_TASKS_ROOT=str(ROOT / "plugins/agents-tasks")))
class Explore(unittest.TestCase):
    def built(self):
        tmp = repo(); p = at(tmp, "build"); self.assertEqual(p.returncode, 0, p.stderr); return tmp
    def test_build_takes_rules_that_hold_and_repo_cells_and_keeps_run_state(self):
        tmp = self.built()
        cells = [line.split("\t")[0] for line in at(tmp, "next", "9").stdout.splitlines()]
        self.assertEqual(sorted(cells), ["FBK-01", "ROLE:buy:guest"])  # Target and Partly rules are known gaps
        self.assertEqual(at(tmp, "record", "FBK-01", "pass").returncode, 0)
        self.assertEqual(at(tmp, "build").stdout.strip(), "2 cells")
        self.assertIn("\tpass\t1\t", (tmp / "tests/e2e-explore/ledger.tsv").read_text())
    def test_next_puts_run_cells_last_and_skips_untestable(self):
        tmp = self.built()
        at(tmp, "record", "FBK-01", "pass")
        self.assertEqual(at(tmp, "next", "1").stdout.split("\t")[0], "ROLE:buy:guest")
        at(tmp, "record", "ROLE:buy:guest", "untestable")
        self.assertEqual([l.split("\t")[0] for l in at(tmp, "next", "9").stdout.splitlines()], ["FBK-01"])
    def test_record_refuses_an_unknown_cell_or_verdict(self):
        tmp = self.built()
        self.assertEqual(at(tmp, "record", "NOPE", "pass").returncode, 2)
        self.assertEqual(at(tmp, "record", "FBK-01", "fine").returncode, 2)
    def test_fingerprint_ignores_numbers_ids_query_and_case(self):
        tmp = repo()
        one = at(tmp, "fingerprint", "FBK-01", "/cart/123?x=1", "Two toasts after 5 s").stdout
        two = at(tmp, "fingerprint", "FBK-01", "/cart/9f8e7d6c5b4a", "two toasts  after 12 s").stdout
        self.assertEqual(one, two)
        self.assertNotEqual(one, at(tmp, "fingerprint", "FBK-02", "/cart/123", "Two toasts after 5 s").stdout)
    def test_known_finds_a_filed_finding_and_an_owner_decision(self):
        tmp = self.built()
        value = at(tmp, "fingerprint", "FBK-01", "/cart", "two toasts").stdout.strip()
        self.assertEqual(at(tmp, "known", value).returncode, 1)
        (tmp / "docs/tasks_manager/_inbox/I-001_x.md").write_text(f"## Two toasts\n\nFingerprint: {value}\n")
        p = at(tmp, "known", value); self.assertEqual(p.returncode, 0); self.assertIn("I-001_x.md", p.stdout)
        (tmp / "docs/tasks_manager/_inbox/I-001_x.md").unlink()
        (tmp / "tests/e2e-explore/decisions.tsv").write_text(f"fingerprint\tdecision\tdate\tnote\n{value}\texpected\t2026-01-01\tby design\n")
        self.assertIn("decisions.tsv", at(tmp, "known", value).stdout)
if __name__ == "__main__":
    unittest.main()
