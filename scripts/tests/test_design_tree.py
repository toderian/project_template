"""`at design sync|check`: the design-tree generator and gate."""
import datetime, os, pathlib, subprocess, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[2]
AT = ROOT / "plugins/agents-core/bin/at"
TODAY = datetime.date.today().isoformat()
DESIGN = "docs/resources/shop/design"
LEAF = """---
summary: {summary}
status: {status}
code_paths:
  - src/cart.py
verified:
  shop: abc1234
  date: {date}
  method: read in full
---

# Cart

## Current behaviour

1. A cart holds at most 50 lines. See [`pricing.md`](pricing.md).

## Decisions

| ID | Date | Decision | Why | Source | Supersedes | Status |
|---|---|---|---|---|---|---|
| D-01 | 2026-01-05 | A cart holds 20 lines. | Page size. | SH-001 | — | superseded by D-02 |
| D-02 | not recorded | A cart holds 50 lines. | Wholesale orders. | SH-002 | D-01 | active |

## Pending changes

{pending}
"""
README = "# Cart module\n\nThe cart and\nits prices. Second sentence.\n\n<!-- BEGIN generated-design-index -->\n<!-- END generated-design-index -->\n\n<!-- BEGIN generated-design-tasks -->\n<!-- END generated-design-tasks -->\n"
TASK = "| Field | Value |\n|---|---|\n| Task ID | {id} |\n| Status | {status} |\n| Spec refs | self, `{ref}` |\n\n## {title}\n\n### Brief\n"
def leaf(**kw):
    kw = {"summary": "What a cart holds.", "status": "implemented", "date": TODAY, "pending": "- SH-003: raise the limit.", **kw}
    return LEAF.format(**kw)
def repo():
    tmp = pathlib.Path(tempfile.mkdtemp())
    subprocess.run(["git", "-C", str(tmp), "init", "-q"], check=True)
    for d in (f"{DESIGN}/cart", "docs/tasks_manager/_todos", "docs/tasks_manager/_todos_archived"):
        (tmp / d).mkdir(parents=True)
    (tmp / DESIGN / "README.md").write_text("# Shop design\n\n<!-- BEGIN generated-design-index -->\n<!-- END generated-design-index -->\n")
    (tmp / DESIGN / "cart/README.md").write_text(README)
    (tmp / DESIGN / "cart/cart.md").write_text(leaf())
    (tmp / DESIGN / "cart/pricing.md").write_text("---\nsummary: How a line is priced.\nstatus: accepted\n---\n\n# Pricing\n")
    (tmp / DESIGN / "cart/cart.reference.md").write_text("---\nsummary: Cart fields.\n---\n" + "row\n" * 600)
    (tmp / "docs/tasks_manager/_todos/SH-003-F_raise-limit.md").write_text(
        TASK.format(id="SH-003", status="in_progress", ref=f"{DESIGN}/cart/cart.md", title="Raise the cart limit"))
    (tmp / "docs/tasks_manager/_todos_archived/SH-002-F_wholesale.md").write_text(
        TASK.format(id="SH-002", status="done", ref=f"{DESIGN}/cart/gone.md", title="Wholesale"))
    return tmp
def at(tmp, *args):
    return subprocess.run([str(AT), *(args if args[0] in ("doctor", "ledger") else ("design", *args))], cwd=str(tmp), capture_output=True, text=True,
                          env=dict(os.environ, AT_TASKS_ROOT=str(ROOT / "plugins/agents-tasks")))
class DesignTree(unittest.TestCase):
    def synced(self):
        tmp = repo(); p = at(tmp, "sync"); self.assertEqual(p.returncode, 0, p.stdout + p.stderr); return tmp
    def failing(self, tmp, text):
        p = at(tmp, "check"); self.assertEqual(p.returncode, 1, p.stdout); self.assertIn(text, p.stdout)
    def test_sync_writes_indexes_and_open_tasks_and_is_idempotent(self):
        tmp = repo()
        self.failing(tmp, "generated block is stale; run `at design sync`")
        p = at(tmp, "sync"); self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        module = (tmp / DESIGN / "cart/README.md").read_text()
        self.assertIn("| [`cart.md`](cart.md) | What a cart holds. | implemented |", module)
        self.assertIn("| [`pricing.md`](pricing.md) | How a line is priced. | accepted |", module)
        self.assertNotIn("cart.reference.md", module)
        self.assertIn("| SH-003 | Raise the cart limit | `cart.md` |", module)
        self.assertNotIn("SH-002", module)  # an archived task's Spec refs are not read
        self.assertIn("| [`cart/`](cart/README.md) | The cart and its prices. | 1 accepted, 1 implemented |",
                      (tmp / DESIGN / "README.md").read_text())
        p = at(tmp, "check"); self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("design check ok: 1 tree(s), 2 leaves, 0 error(s), 0 warning(s)", p.stdout)
        self.assertNotIn("updated", at(tmp, "sync").stdout)
    def test_no_design_tree_is_ok(self):
        tmp = pathlib.Path(tempfile.mkdtemp()); subprocess.run(["git", "-C", str(tmp), "init", "-q"], check=True)
        p = at(tmp, "check"); self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
    def test_leaf_errors(self):
        for change, message in (
            (lambda t: t.replace("status: implemented", "status: live"), "status is 'live'"),
            (lambda t: t.replace("summary: What a cart holds.\n", ""), "frontmatter has no summary"),
            (lambda t: t.replace(f"  date: {TODAY}\n", ""), "needs verified.date"),
            (lambda t: t.replace("---\n", "", 1), "no frontmatter block"),
            (lambda t: t + "x\n" * 500, "split a leaf at 500"),
            (lambda t: t.replace("(pricing.md)", "(prices.md)"), "link target prices.md does not exist"),
            (lambda t: t.replace("| ID | Date |", "| ID | When |"), "Decisions columns must be"),
            (lambda t: t.replace("| D-02 |", "| D-01 |"), "decision ID D-01 is used twice"),
            (lambda t: t.replace("superseded by D-02", "active"), "whose Status is not 'superseded by D-02'"),
            (lambda t: t.replace("| D-01 | active", "| — | active"), "whose Supersedes cell does not name D-01"),
            (lambda t: t.replace("| D-01 | active", "| D-09 | active"), "supersedes D-09, which is not in the table"),
            (lambda t: t.replace("2026-01-05", "January"), "neither YYYY-MM-DD nor 'not recorded'"),
            (lambda t: t.replace("| — | superseded by D-02", "| — | retired"), "status 'retired'"),
        ):
            with self.subTest(message):
                tmp = self.synced(); path = tmp / DESIGN / "cart/cart.md"
                path.write_text(change(path.read_text())); self.failing(tmp, message)
    def test_links_inside_code_are_not_checked(self):
        tmp = self.synced(); path = tmp / DESIGN / "cart/cart.md"
        path.write_text(path.read_text() + "\n`[x](nope.md)`\n\n```md\n[y](nope2.md)\n```\n")
        self.assertEqual(at(tmp, "check").returncode, 0)
    def test_tree_errors(self):
        tmp = self.synced(); deep = tmp / DESIGN / "a/b/c/d"; deep.mkdir(parents=True)
        (deep / "x.md").write_text("---\nsummary: s\nstatus: draft\n---\n")
        self.failing(tmp, "deeper than 3 folder levels")
        tmp = self.synced()
        (tmp / DESIGN / "README.md").write_text("# Shop design\n\n[cart](cart/README.md)\n")
        (tmp / DESIGN / "extra.md").write_text("---\nsummary: s\nstatus: draft\n---\n")
        self.failing(tmp, "README.md: does not link to extra.md")
        tmp = self.synced(); (tmp / DESIGN / "README.md").unlink()
        self.failing(tmp, f"{DESIGN}: no README.md")
        tmp = self.synced(); task = tmp / "docs/tasks_manager/_todos/SH-003-F_raise-limit.md"
        task.write_text(task.read_text().replace("cart/cart.md", "cart/basket.md"))
        self.failing(tmp, "task SH-003: Spec refs names docs/resources/shop/design/cart/basket.md, which does not exist")
    def test_warnings_do_not_fail(self):
        tmp = self.synced(); path = tmp / DESIGN / "cart/cart.md"
        path.write_text(leaf(date="2020-01-01", pending="- SH-002: wholesale."))
        p = at(tmp, "check"); self.assertEqual(p.returncode, 0, p.stdout)
        for text in ("last verified 2020-01-01", "Pending changes names SH-002, which is closed",
                     "open task SH-003 names this leaf in Spec refs; list it under Pending changes"):
            self.assertIn(f"WARNING: {DESIGN}/cart/cart.md: {text}", p.stdout)
    def test_doctor_reports_the_design_check(self):
        tmp = self.synced()
        self.assertRegex(at(tmp, "doctor").stdout, r"OK +design trees are valid")
        (tmp / DESIGN / "cart/pricing.md").write_text("# Pricing\n")
        self.assertRegex(at(tmp, "doctor").stdout, r"ERROR +design: .*pricing.md: no frontmatter block")
    def test_ledger_commands_carry_the_design_trees(self):
        tmp = repo()
        self.assertIn("generated block is stale", at(tmp, "ledger", "check").stdout)
        self.assertIn("updated docs/resources/shop/design/cart/README.md", at(tmp, "ledger", "sync").stdout)
        self.assertIn("design check ok", at(tmp, "ledger", "check").stdout)
if __name__ == "__main__":
    unittest.main()
