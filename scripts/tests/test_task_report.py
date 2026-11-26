import os, shutil, subprocess, tempfile, unittest, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
AT = ROOT / "plugins/agents-core/bin/at"
TM = "docs/tasks_manager"
ROWS = "| Phase | Status | Attempt | Spec | Quality | Security | Open | Commit | Agent |\n|---|---|---|---|---|---|---|---|---|\n"
def task(i, status, extra=""):
    return f"| Field | Value |\n|---|---|\n| Task ID | {i} |\n| Status | {status} |\n\n## X\n\n### Phases\n\n#### Phase 1: A\n\n{extra}"
def state(i, base, rows, lines):
    return (f"---\ntask: {i}\ntask_file: x\nbase_rev: {base}\ncurrent_phase: 1\n---\n# Run ledger — {i}\n\n{ROWS}{rows}\n\n{lines}\n")
def row(n, status, sha="—"):
    return f"| {n} | {status} | 1 | — | — | n/a | 0 | {sha} | — |"
class Report(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.env = dict(os.environ, GIT_CONFIG_GLOBAL=str(self.tmp / "gitconfig"), GIT_CONFIG_NOSYSTEM="1")
        self.repo = self.tmp / "r"; self.repo.mkdir()
        self.g("init", "-q"); (self.repo / "f").write_text("0\n"); self.g("add", "-A")
        # author date differs from committer date: the file name must follow the committer date
        self.g("commit", "-q", "-m", "base", env={"GIT_AUTHOR_DATE": "2026-01-02T10:00:00+0000", "GIT_COMMITTER_DATE": "2026-01-05T10:00:00+0000"})
        self.base = self.sha()
        self.sha1 = self.commit("feat: TST-001 phase 1")
        self.sha2 = self.commit("feat: TST-001 phase 2")
        for d in ("_todos", "_todos_archived", "_runs/TST-001"):
            (self.repo / TM / d).mkdir(parents=True)
        self.put("_todos/TST-001-F_a.md", task("TST-001", "in_progress"))
        self.state("TST-001", [row(1, "committed", self.sha1), row(2, "committed", self.sha2)], "Decision: use sqlite — why: x\nRuling: F1 — accepted")
        self.g("add", "-A"); self.g("commit", "-qm", "chore: tasks")
    def g(self, *a, env=None):
        return subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=t", "-c", "user.email=t@t", *a],
                              capture_output=True, text=True, check=True, env=dict(self.env, **(env or {})))
    def sha(self):
        return self.g("rev-parse", "--short", "HEAD").stdout.strip()
    def commit(self, msg):
        (self.repo / "f").write_text(msg + "\n"); self.g("commit", "-qam", msg); return self.sha()
    def put(self, rel, text):
        p = self.repo / TM / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text)
    def state(self, i, rows, lines, base=None):
        (self.repo / TM / "_runs" / i).mkdir(parents=True, exist_ok=True)
        self.put(f"_runs/{i}/state.md", state(i, base or self.base, "\n".join(rows), lines))
    def at(self, *a):
        return subprocess.run([str(AT), "task", "report", *a], cwd=str(self.repo), capture_output=True, text=True, env=self.env)
    def ok(self, *a):
        p = self.at(*a); self.assertEqual(p.returncode, 0, p.stderr); self.assertNotIn("Traceback", p.stderr); return p
    def bad(self, *a):
        p = self.at(*a); self.assertEqual(p.returncode, 2, p.stdout); self.assertNotIn("Traceback", p.stderr)
        self.assertEqual(len(p.stderr.strip().splitlines()) <= 3, True, p.stderr); return p
    def rep(self, i="TST-001", day="2026-01-05"):
        return (self.repo / TM / "_reports" / f"{day}-{i}.md").read_text()
    def reports(self):
        d = self.repo / TM / "_reports"
        return {f: (d / f).read_text() for f in os.listdir(d)} if d.is_dir() else {}
    def needs(self, text):
        return text.split("## Needs you")[1].split("## Task")[0]

    def test_commits_in_row_order_dated_by_committer_date_and_rerun_identical(self):
        self.state("TST-001", [row(1, "committed", self.sha2), row(2, "committed", self.sha1)], "")
        self.ok("TST-001"); one = self.rep()              # committer date 01-05, not author date 01-02
        self.assertLess(one.index(f"- {self.sha2} feat: TST-001 phase 2"), one.index(f"- {self.sha1} feat: TST-001 phase 1"))
        before = self.reports()
        self.commit("chore: unrelated later commit")      # HEAD moves: the report must not
        self.ok("TST-001"); self.assertEqual(before, self.reports())
        self.g("add", "-A"); self.g("commit", "-qm", "chore: report with state")   # report + state.md in one commit
        self.ok("TST-001"); self.assertEqual(before, self.reports())
    def test_since_positive_leaves_out_reports_only_commits(self):
        self.ok("TST-001"); self.g("add", "-A"); self.g("commit", "-qm", "chore: only the report")
        self.commit("feat: later work"); head = self.g("rev-parse", "HEAD").stdout[:12]
        self.ok("TST-001", "--since", self.sha1); t = self.rep()
        sec = t.split("## Commits since")[1]
        self.assertIn(f"- {head} feat: later work", sec); self.assertIn("depends on HEAD", sec)
        self.assertNotIn("only the report", sec)
        self.ok("TST-001", "--since", "HEAD~1"); self.assertEqual(self.rep().count("feat: later work"), 1)  # recorded commits unaffected
    def test_symlinked_report_file_and_directory_are_refused(self):
        outside = self.tmp / "outside.md"; outside.write_text("keep\n")
        rd = self.repo / TM / "_reports"; rd.mkdir()
        (rd / "2026-01-05-TST-001.md").symlink_to(outside)
        self.bad("TST-001"); self.assertEqual(outside.read_text(), "keep\n")
        (rd / "2026-01-05-TST-001.md").unlink(); rd.rmdir()
        other = self.tmp / "elsewhere"; other.mkdir(); rd.symlink_to(other)
        self.bad("TST-001"); self.assertEqual(os.listdir(other), [])
    def test_blocked_row_shows_its_reason_and_open_parked_note(self):
        self.state("TST-001", [row(1, "committed", self.sha1), row(2, "blocked")],
                   "Phase 2: fix-loop cap reached with 2 open finding(s)\nPhase 1: complete\nNote: parked: which region?")
        self.ok("TST-001"); n = self.needs(self.rep())
        self.assertIn("- Phase 2 is blocked", n); self.assertIn("fix-loop cap reached", n)
        self.assertNotIn("Phase 1: complete", n); self.assertIn("- Note: parked: which region?", n)
    def test_driver_form_parked_note_follows_its_row(self):
        self.state("TST-001", [row(1, "committed", self.sha1), row(2, "parked")], "Note: parked phase 2: needs the key")
        self.ok("TST-001"); n = self.needs(self.rep())
        self.assertIn("- Phase 2 is parked", n); self.assertIn("Note: parked phase 2: needs the key", n)
    def test_parked_note_is_history_once_every_row_is_committed(self):
        self.state("TST-001", [row(1, "committed", self.sha1)], "Note: parked: rotate keys?")
        self.ok("TST-001"); t = self.rep()
        self.assertNotIn("rotate keys", self.needs(t)); self.assertIn("Nothing open.", t)
        self.assertIn("rotate keys", t.split("## Parked during the run")[1].split("## Commits")[0])
    def test_duplicate_ids_report_once(self):
        p = self.ok("TST-001", "TST-001"); self.assertEqual(len(p.stdout.split()), 1)
    def test_state_parse_error_and_unknown_task_exit_2_and_write_nothing(self):
        self.put("_runs/TST-001/state.md", "no front matter\n")
        self.bad("TST-001"); self.assertEqual(self.reports(), {})
        self.bad("TST-404")
        self.put("_todos/TST-005-F_x.md", task("TST-005", "open"))      # task file, no state, not archived
        self.bad("TST-005")
        self.put("_runs/TST-001/state.md", b"\xff\xfe\n".decode("latin1"))
        self.bad("TST-001", "TST-404"); self.assertEqual(self.reports(), {})   # one bad id: nothing written
    def test_archived_task_needs_base_line_or_since(self):
        self.put("_todos_archived/TST-003-F_c.md", task("TST-003", "done", "## Completion summary\n\nDone.\n- Decision: keep v1\n- Note: parked: rotate keys?\n"))
        p = self.bad("TST-003"); self.assertIn("Base:", p.stderr); self.assertIn("--since", p.stderr)
        self.ok("TST-003", "--since", self.base); t = self.rep("TST-003")
        self.assertIn("- Decision: keep v1", t); self.assertIn("Nothing open.", t)
        self.assertIn("rotate keys", t.split("## Parked during the run")[1])
        self.put("_todos_archived/TST-003-F_c.md", task("TST-003", "done", f"## Completion summary\n\n- Base: {self.base}\n"))
        self.ok("TST-003"); self.assertIn("2026-01-05-TST-003.md", self.reports())
    def test_archived_with_run_dir_reads_summary_and_todos_wins_over_archive(self):
        self.put("_todos_archived/TST-001-F_a.md", task("TST-001", "done", "## Completion summary\n\n- Decision: from archive\n"))
        os.remove(self.repo / TM / "_todos/TST-001-F_a.md")
        self.ok("TST-001"); t = self.rep()
        self.assertIn("- Decision: from archive", t); self.assertIn("- Decision: use sqlite", t); self.assertIn("Status: done", t)
        self.put("_todos/TST-001-F_a.md", task("TST-001", "in_progress"))
        self.ok("TST-001"); t = self.rep()
        self.assertIn("Status: in_progress", t); self.assertIn("Also present in _todos_archived", t)
    def test_hostile_git_config_changes_nothing(self):
        self.put("_runs/TST-001/state.md", state("TST-001", self.base, row(1, "committed", self.sha1), ""))
        self.ok("TST-001"); plain = self.reports()
        self.g("config", "log.showSignature", "true"); self.g("config", "core.abbrev", "40")
        self.g("config", "i18n.logOutputEncoding", "latin1"); self.g("config", "core.quotePath", "true")
        self.ok("TST-001", "--since", self.base)
        self.assertEqual(plain["2026-01-05-TST-001.md"], self.rep().split("\n## Commits since")[0])
        c = self.commit("feat: café ünïcode"); self.state("TST-001", [row(1, "committed", c)], "")
        self.ok("TST-001"); t = self.rep()
        self.assertIn(f"- {c} feat: café ünïcode", t); self.assertNotIn("No signature", t)
    def test_filesystem_errors_are_one_line_exit_2(self):
        rd = self.repo / TM / "_reports"; rd.write_text("a file\n")          # _reports is a file
        self.bad("TST-001"); rd.unlink()
        (rd / "2026-01-05-TST-001.md").mkdir(parents=True)                  # the target is a directory
        self.bad("TST-001"); shutil.rmtree(rd)
        rd.mkdir(); rd.chmod(0o500)                                         # read-only directory
        try:
            if os.access(rd, os.W_OK): self.skipTest("running as a user that ignores modes")
            self.bad("TST-001"); self.assertEqual(os.listdir(rd), [])
        finally:
            rd.chmod(0o755)
    def test_ledger_check_accepts_reports_dir(self):
        repo = self.tmp / "seeded"; shutil.copytree(ROOT / "plugins/agents-tasks/seed/docs", repo / "docs")
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True, env=self.env)
        run = lambda: subprocess.run([str(AT), "ledger", "check"], cwd=str(repo), capture_output=True, text=True, env=self.env)
        self.assertEqual(run().returncode, 0, "the seed alone must pass: " + run().stdout + run().stderr)
        (repo / TM / "_reports").mkdir(); (repo / TM / "_reports/2026-01-05-TST-001.md").write_text("# r\n")
        p = run(); self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
    def test_all_or_nothing_including_the_target_check(self):
        self.put("_todos/TST-002-F_b.md", task("TST-002", "open")); self.state("TST-002", [row(1, "committed", self.sha1)], "")
        (self.repo / TM / "_reports/2026-01-05-TST-002.md").mkdir(parents=True)
        self.bad("TST-001", "TST-002"); self.assertFalse((self.repo / TM / "_reports/2026-01-05-TST-001.md").exists())
    def test_symlinked_tasks_manager_is_refused(self):
        other = self.tmp / "moved"; shutil.move(str(self.repo / TM), str(other)); (self.repo / TM).symlink_to(other)
        self.bad("TST-001"); self.assertFalse((other / "_reports").exists())
    def test_symlinked_docs_is_refused(self):
        other = self.tmp / "moved"; shutil.move(str(self.repo / "docs"), str(other)); (self.repo / "docs").symlink_to(other)
        self.bad("TST-001"); self.assertFalse((other / "tasks_manager/_reports").exists())
    def test_phase_1_does_not_match_phase_12_lines(self):
        self.state("TST-001", [row(1, "blocked")], "Phase 1: reason one\nPhase 12: other phase")
        self.ok("TST-001"); n = self.needs(self.rep())
        self.assertIn("reason one", n); self.assertNotIn("other phase", n)
    def test_commit_cells(self):
        self.state("TST-001", [row(1, "committed", f"`{self.sha1.upper()}`"), row(2, "committed", "deadbeef"),
                               row(3, "committed", f"--output={self.tmp}/pwn")], "")
        self.ok("TST-001"); t = self.rep()
        self.assertIn(f"- {self.sha1} feat: TST-001 phase 1", t)             # backticks and upper case are read
        self.assertIn("- deadbeef\n", t); self.assertIn("not in this repository", t)   # missing object: no subject, one note
        self.assertFalse((self.tmp / "pwn").exists())                         # a non-hex cell never reaches git
        self.assertNotIn("--output", t.split("## Commits")[1])                # and is not listed as a commit
    def test_short_state_row_is_exit_2(self):
        self.state("TST-001", ["| 1 |"], ""); self.bad("TST-001")
    def test_file_mode_follows_umask_and_replace_keeps_mode(self):
        old = os.umask(0o027)
        try:
            self.ok("TST-001")
        finally:
            os.umask(old)
        f = self.repo / TM / "_reports/2026-01-05-TST-001.md"
        self.assertEqual(f.stat().st_mode & 0o777, 0o640)
        f.chmod(0o600); self.ok("TST-001"); self.assertEqual(f.stat().st_mode & 0o777, 0o600)
    def test_usage_errors(self):
        self.bad("../x"); self.assertIn("not a revision", self.bad("TST-001", "--since", "-x").stderr)
        self.bad("TST-001", "--since", "nope")
        self.assertEqual(self.reports(), {})
if __name__ == "__main__":
    unittest.main()
