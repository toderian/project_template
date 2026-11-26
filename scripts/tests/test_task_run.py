import os, re, subprocess, shutil, tempfile, unittest, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
AT = ROOT / "plugins/agents-core/bin/at"
FAKE = ROOT / "scripts/tests/fixtures/fake-harness.py"
FIX = ROOT / "scripts/tests/fixtures/task-brief"
STATE = "docs/tasks_manager/_runs/TST-003/state.md"
def repo():
    tmp = pathlib.Path(tempfile.mkdtemp()); shutil.copytree(FIX, tmp, dirs_exist_ok=True)
    (tmp / ".gitignore").write_text("docs/tasks_manager/_runs/**/diff.patch\n")
    g = lambda *a: subprocess.run(["git", "-C", str(tmp), *a], capture_output=True, text=True, check=True)
    g("init", "-q")
    # The driver commits in a separate process, so identity must persist in the fixture.
    g("config", "user.name", "Task runner test"); g("config", "user.email", "task-runner@example.invalid")
    g("add", "-A"); g("commit", "-q", "-m", "base"); return tmp
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
        self.assertNotIn("- [ ]", task.split("### Related tests")[0]); self.assertIn("Phase 3: Hardening (at task run", task)
        self.assertIn("- Final review (at task run", task)
        calls = (tmp.parent / (tmp.name + ".calls")).read_text()
        self.assertIn("reviewer|spec|1|claude|resume=False|ro=True", calls); self.assertIn("reviewer|final-1|0|claude", calls)
        self.assertIn("reviewer|final-simplicity|0|claude", calls); self.assertNotIn("reviewer|final-1|0|claude|resume=False|ro=True|mode=dontAsk|allowed=-|budget=5.0|structural", calls)
        self.assertTrue(all("|size" in c for c in calls.splitlines() if c.startswith(("reviewer|quality", "reviewer|final"))), calls)
        self.assertFalse(any("|size" in c for c in calls.splitlines() if c.startswith("reviewer|spec")), calls)
        size = (tmp / "docs/tasks_manager/_runs/TST-003/phase-1/size.md").read_text(); self.assertIn("| src/phase1.py | 0 | 1 | +1 (new) | code |", size)
        self.assertIn("TST-003 whole run", (tmp / "docs/tasks_manager/_runs/TST-003/size.md").read_text())
        self.assertIn("- size: +1/−0, code net +1, test net +0, fixture net +0; flagged: none", subprocess.run(["git", "-C", str(tmp), "log", "-1", "--format=%B", "HEAD~1"], capture_output=True, text=True).stdout)
        self.assertIn("**Size:** +1/−0", task); self.assertIn("Note: run size +", s); self.assertIn("Note: final review simplicity: PASS", s)
        self.assertEqual(subprocess.run(["git", "-C", str(tmp), "status", "--porcelain"], capture_output=True, text=True).stdout.strip(), "")
    def test_fix_round_resumes_implementer_then_passes(self):
        tmp = repo(); p = run(tmp, "--phase", "1", scenario="fail-once"); self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertTrue((tmp / "docs/tasks_manager/_runs/TST-003/phase-1/findings-1.md").exists())
        calls = (tmp.parent / (tmp.name + ".calls")).read_text()
        self.assertIn("implementer||1|claude|resume=True", calls); self.assertIn("fix round 1/3", (tmp / STATE).read_text())
    def test_two_growing_fix_rounds_trigger_a_structural_round_then_block(self):
        tmp = repo(); p = run(tmp, "--phase", "1", "--mode", "large", scenario="grow"); self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        calls = (tmp.parent / (tmp.name + ".calls")).read_text().splitlines(); impl = [c for c in calls if c.startswith("implementer|")]
        self.assertEqual(len(impl), 4, impl); self.assertNotIn("structural", impl[2]); self.assertIn("|structural", impl[3])
        s = (tmp / STATE).read_text(); self.assertIn("| 1 | blocked |", s); self.assertIn("structural round still grew phase1.py", s)
        self.assertIn("Note: Phase 1 fix 1: code net +51 (phase1.py +51)", s); self.assertIn("Note: Phase 1 fix 3: code net +51", s)
        self.assertTrue((tmp / "docs/tasks_manager/_runs/TST-003/phase-1/size-fix-3.md").exists())
        self.assertTrue(all("|size" in c for c in calls if c.startswith("reviewer|quality")), calls)
    def test_codex_harness_uses_fresh_dispatch_and_read_only_reviews(self):
        tmp = repo(); p = run(tmp, "--phase", "1", scenario="fail-once", harness="codex"); self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        calls = (tmp.parent / (tmp.name + ".calls")).read_text()
        self.assertIn("implementer||1|codex|resume=False", calls); self.assertNotIn("resume=True", calls); self.assertIn("reviewer|quality|1|codex|resume=False|ro=True", calls)
    def test_effort_flags_reach_every_dispatch_and_the_execution_log(self):
        for harness in ("claude", "codex"):
            tmp = repo(); p = run(tmp, "--phase", "1", "--effort", "medium", "--strong-effort", "high", "--strong-model", "big", harness=harness)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            calls = (tmp.parent / (tmp.name + ".calls")).read_text().splitlines()
            implementers = [c for c in calls if c.startswith("implementer|")]; reviewers = [c for c in calls if c.startswith("reviewer|")]
            self.assertTrue(implementers and reviewers, calls)
            self.assertTrue(all(c.endswith("|effort=medium") for c in implementers), implementers)
            self.assertTrue(all(c.endswith("|effort=high") for c in reviewers), reviewers)
            task = next((tmp / "docs/tasks_manager/_todos").glob("TST-003-*.md")).read_text()
            label = {"claude": "claude, model default/big, effort medium/high",
                     "codex": "codex, model gpt-6-sol/big, effort medium/high, cyber daybreak_blue"}[harness]
            self.assertIn(f"(at task run, {label})", task)
        tmp = repo(); p = run(tmp, "--phase", "1"); self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertNotIn("effort=", (tmp.parent / (tmp.name + ".calls")).read_text())
        self.assertIn("(at task run, claude)", next((tmp / "docs/tasks_manager/_todos").glob("TST-003-*.md")).read_text())
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
    def test_permissions_budget_and_status_retry(self):
        tmp = repo(); p = run(tmp, "--phase", "1", scenario="status-retry"); self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        calls = (tmp.parent / (tmp.name + ".calls")).read_text().splitlines()
        impl = [c for c in calls if c.startswith("implementer|")]; rev = [c for c in calls if c.startswith("reviewer|")]
        self.assertEqual(len(impl), 2); self.assertIn("resume=True", impl[1]); self.assertIn("asking once more", p.stdout)
        self.assertTrue(all("mode=acceptEdits|allowed=Bash|budget=5.0" in c for c in impl), impl)
        self.assertTrue(all("mode=dontAsk|allowed=-|budget=5.0" in c and "ro=True" in c for c in rev), rev)
        p2 = run(tmp, "--phase", "2", "--budget-usd", "0", "--check", "true"); self.assertEqual(p2.returncode, 0, p2.stderr)
        tail = (tmp.parent / (tmp.name + ".calls")).read_text().splitlines()[-3:]
        self.assertTrue(all("budget=-" in c for c in tail), tail)
        self.assertTrue(any("reviewer|" in c and "allowed=Bash(true)" in c for c in tail), tail)
    def test_timeout_blocks_phase_and_releases_lock(self):
        tmp = repo(); p = run(tmp, "--phase", "1", "--timeout", "1", scenario="hang"); self.assertEqual(p.returncode, 1)
        self.assertIn("no reply within 1s", p.stderr); s = (tmp / STATE).read_text()
        self.assertIn("| 1 | blocked |", s); self.assertIn("run aborted", s)
        self.assertFalse((tmp / "docs/tasks_manager/_runs/TST-003/lock").exists())
    def test_lock_refuses_live_run_and_replaces_stale(self):
        tmp = repo(); lock = tmp / "docs/tasks_manager/_runs/TST-003/lock"; lock.parent.mkdir(parents=True)
        lock.write_text(f"{os.getpid()} {os.uname().nodename} now\n")
        p = run(tmp, "--phase", "1"); self.assertEqual(p.returncode, 1); self.assertIn("run in progress", p.stderr)
        self.assertTrue(lock.exists())
        lock.write_text(f"999999 {os.uname().nodename} earlier\n")
        p = run(tmp, "--phase", "1"); self.assertEqual(p.returncode, 0, p.stderr); self.assertIn("stale lock", p.stdout)
        self.assertFalse(lock.exists())
    def test_auto_mode_counts_repos_in_the_repos_row(self):
        def mode(value):
            # Drop the other large triggers (Design section, a third phase) so only the Repos row decides.
            t = repo(); f = next((t / "docs/tasks_manager/_todos").glob("TST-003-*.md")); text = f.read_text()
            text = text[:text.index("### Design")] + text[text.index("### Phases"):]
            text = text[:text.index("#### Phase 3")] + text[text.index("### Acceptance criteria"):]
            f.write_text(text.replace("| Repos         | demo-service                                  |", f"| Repos         | {value} |"))
            subprocess.run(["git", "-C", str(t), "commit", "-qam", "repos"], check=True)
            p = run(t, "--phase", "1", "--dry-run"); self.assertEqual(p.returncode, 0, p.stderr)
            return p.stdout.split("[mode ")[1].split("]")[0]
        self.assertEqual(mode("demo-service"), "small: no large trigger")
        self.assertEqual(mode("N/A"), "small: no large trigger")
        self.assertEqual(mode("demo-service, edge-node"), "large: 2 repos")
    def test_small_mode_uses_one_reviewer_per_phase_and_one_final(self):
        tmp = repo(); p = run(tmp, "--mode", "small"); self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        calls = (tmp.parent / (tmp.name + ".calls")).read_text()
        self.assertIn("reviewer|both|1|claude|resume=False|ro=True", calls); self.assertNotIn("reviewer|spec|", calls)
        self.assertIn("reviewer|final-1|0|claude", calls); self.assertNotIn("reviewer|final-2|", calls)
        self.assertTrue((tmp / "docs/tasks_manager/_runs/TST-003/phase-2/review.md").exists())
        s = (tmp / STATE).read_text(); self.assertIn("mode: small", s); self.assertEqual(s.count("| committed |"), 3)
        self.assertIn("mode: large", (lambda t: (run(t, "--dry-run"), (t / STATE).read_text())[1])(repo()))  # auto: 3 phases
    def test_codex_runs_with_yolo_and_fences_reviewers_by_prompt(self):
        tmp = repo(); p = run(tmp, "--phase", "1", harness="codex"); self.assertEqual(p.returncode, 0, p.stderr)
        calls = (tmp.parent / (tmp.name + ".calls")).read_text()
        self.assertIn("implementer||1|codex|resume=False|ro=False|mode=yolo", calls)
        self.assertIn("reviewer|spec|1|codex|resume=False|ro=True|mode=yolo", calls)
    def test_codex_runs_on_gpt_6_sol_under_daybreak_blue_with_resolved_cards(self):
        import sys; sys.path.insert(0, str(ROOT / "plugins/agents-core/lib")); import task_run
        tmp = repo(); p = run(tmp, "--phase", "1", harness="codex"); self.assertEqual(p.returncode, 0, p.stderr)
        log = (tmp / "docs/tasks_manager/_runs/TST-003/driver.log").read_text()
        self.assertIn("-m gpt-6-sol --cyber-access-program daybreak_blue -", log)
        h = task_run.Harness("codex", tmp, ROOT / "plugins/agents-core", None, None, None, tmp / "x.log", 1, None)
        self.assertEqual(h.label(), "codex, model gpt-6-sol, cyber daybreak_blue")
        card = task_run.card_body(ROOT / "plugins/agents-core", "security-auditor")
        self.assertNotIn("${CLAUDE_PLUGIN_ROOT}", card); self.assertIn(str(ROOT / "plugins/agents-core/skills/security-review-owasp/SKILL.md"), card)
    def test_run_prompts_carry_the_same_test_rules_as_the_briefs(self):
        import sys; sys.path.insert(0, str(ROOT / "plugins/agents-core/lib")); import task_run
        briefs = (ROOT / "plugins/agents-core/skills/execute-plan/references/briefs.md").read_text()
        for text in (task_run.reviewer_prompt("r", 1, "quality", "abc"), task_run.reviewer_prompt("r", 1, "both", "abc"),
                     task_run.final_prompt("r", 1, "abc", "t.md"), task_run.final_prompt("r", "simplicity", "abc", "t.md")):
            self.assertTrue("test-ratio" in text or "test ratio" in text, text)
        for text in (task_run.reviewer_prompt("r", 1, "quality", "abc"), task_run.final_prompt("r", 1, "abc", "t.md")):
            self.assertIn(task_run.SIZE_SEVERITY, text); self.assertIn(task_run.SIZE_SEVERITY, briefs)
        self.assertIn(task_run.TEST_REDUNDANCY, task_run.reviewer_prompt("r", 1, "both", "abc")); self.assertIn(task_run.TEST_REDUNDANCY, briefs)
        self.assertIn("Test plan", task_run.implementer_prompt("r", 1, "p"))
        for text in (task_run.implementer_prompt("r", 1, "p"), task_run.implementer_prompt("r", 1, "p", round_no=1)): self.assertIn(task_run.CHECK_SCOPE, text)  # the ladder's subagent rung, in the first dispatch and in a fix round
        self.assertEqual(briefs.count(task_run.CHECK_SCOPE), 2)  # implementer brief and fix-round brief
        self.assertIn("duplicated between phases", task_run.final_prompt("r", 1, "abc", "t.md")); self.assertIn("duplicated between phases", briefs)
        self.assertIn("one behaviour tested at several layers", task_run.SIMPLICITY_SCOPE)
    def test_final_review_carries_the_consequence_checklist_like_the_brief_and_reviewer(self):
        import sys; sys.path.insert(0, str(ROOT / "plugins/agents-core/lib")); import task_run
        briefs = (ROOT / "plugins/agents-core/skills/execute-plan/references/briefs.md").read_text()
        reviewer = (ROOT / "plugins/agents-core/agents/reviewer.md").read_text()
        self.assertIn(task_run.CONSEQUENCES, task_run.final_prompt("r", 1, "abc", "t.md")); self.assertIn(task_run.CONSEQUENCES, briefs)
        self.assertNotIn("Consequence checklist", task_run.final_prompt("r", "simplicity", "abc", "t.md"))
        for line in task_run.CONSEQUENCES.splitlines()[1:7]: self.assertIn(line[3:], reviewer)
    def test_unanchored_final_brief_carries_no_plan_design_or_rulings(self):
        briefs = (ROOT / "plugins/agents-core/skills/execute-plan/references/briefs.md").read_text()
        brief = briefs.split("## Final review 2, unanchored")[1].split("\n## ")[0].split("```text")[1].split("```")[0]
        for leaked in ("state.md", "Ruling", "Context:", "plan/task file", "size.md", "Design"): self.assertNotIn(leaked, brief)
        self.assertIn("Find what breaks", brief); import sys; sys.path.insert(0, str(ROOT / "plugins/agents-core/lib")); import task_run
        self.assertIn(task_run.CONSEQUENCES, brief)
    def test_findings_accept_p_tags_and_header(self):
        import sys; sys.path.insert(0, str(ROOT / "plugins/agents-core/lib")); import task_run
        msg = "## Findings: 3 (C:1 I:1 M:1)\n1. **[P1]** [f:5](a.py) — x\n2. **[P2]** y\n3. [M] z\n4. [P3] w"
        self.assertEqual([s for s, _ in task_run.findings(msg)], ["C", "I", "M", "M"])
        self.assertEqual(task_run.findings_header(msg), (3, {"C": 1, "I": 1, "M": 1}))
        self.assertIsNone(task_run.findings_header("## Findings\n1. [C] a"))
WRAP = """#!/usr/bin/env python3
import json, os, sys, glob, time, subprocess
# Test driver around the fake harness. WRAP_PHASE/WRAP_SEV: fail that phase's quality review with one finding (WRAP_HEADER replaces its
# `## Findings:` line). WRAP_FIXBLOCK: a fix-round implementer writes src/half.py and replies BLOCKED. WRAP_EDIT_CAP: an implementer rewrites
# the task file's cap line. WRAP_LOCK: an implementer leaves .git/index.lock, so `git stash` fails. WRAP_HANG_PHASE: those phases' implementers
# (comma-separated) hang WRAP_HANG_SECS (default 5), after writing their pid to WRAP_PIDS/<phase> when set.
# Lanes, phase 2 unless named: WRAP_STRAY=<path> its implementer writes that path; WRAP_EXTRA writes extra.txt (outside its fence); WRAP_TAG tags
# a commit holding evil.py as at-lane/TST-003-p2; WRAP_SYMREF=<branch> points its lane HEAD at that branch; WRAP_MOVE=during: its spec reviewer
# moves the lane branch to a child commit; WRAP_MOVE=after: phase 3's implementer waits for phase 2's commit, then moves the branch past it.
# WRAP_LATE=<phase>: that phase's reviewers write src/late.py. The wave reviewer appends its prompt to WRAP_PROMPTS and FAILs with WRAP_WAVE_FAIL.
# WRAP_REPLACE: phase 1's implementer writes src/x.py and replaces its blob with a benign one (`git replace`).
E, ph = os.environ.get, os.environ.get("AT_TASK_PHASE")
HDR = "## Findings: 1 (" + " ".join(f"{k}:{int(k == E('WRAP_SEV'))}" for k in "CIM") + ")"
def reply(text, status=0): print(json.dumps({"type": "result", "result": text, "session_id": "s"})); sys.exit(status)
sh = lambda c: subprocess.run(c, shell=True, capture_output=True)
if E("AT_TASK_ROLE") == "reviewer":
    if E("WRAP_LATE") == ph: open("src/late.py", "w").write("late = 1\\n")
    if E("WRAP_MOVE") == "during" and ph == "2" and E("AT_TASK_STAGE") == "spec": sh("git update-ref refs/heads/at-lane/TST-003-p2 $(git commit-tree HEAD^{tree} -p HEAD -m moved)")
    if "integrated result" in sys.argv[2]:
        if E("WRAP_PROMPTS"): open(E("WRAP_PROMPTS"), "a").write(sys.argv[2])
        if E("WRAP_WAVE_FAIL"): reply("## Status: DONE\\n## Verdict: FAIL\\n## Findings: 1 (C:1 I:0 M:0)\\n1. [C] src/x.py:1 - broken\\n## Report: r.md")
if E("AT_TASK_ROLE") == "reviewer" and E("AT_TASK_STAGE") == "quality" and ph == E("WRAP_PHASE"):
    reply(f"## Status: DONE_WITH_CONCERNS\\n## Verdict: FAIL\\n{E('WRAP_HEADER', HDR)}\\n1. [{E('WRAP_SEV')}] src/x.py:1 - naming\\n## Report: r.md")
if E("AT_TASK_ROLE") == "implementer":
    task = glob.glob("docs/tasks_manager/_todos/TST-003-*.md")[0]; t = open(task).read()
    if E("WRAP_FIXBLOCK") and sys.argv[2].startswith("Fix round"):
        open("src/half.py", "w").write("x = 1\\n"); reply("## Status: BLOCKED\\n## Summary: stuck")
    if E("WRAP_EDIT_CAP"): open(task, "w").write(t.replace("At review cap: park", "At review cap: continue"))
    if E("WRAP_LOCK"): open(".git/index.lock", "w").close()
    if E("WRAP_COMMIT") and E("WRAP_COMMIT_PHASE", ph) == ph: open("sneak.py", "w").write("x = 1\\n"); os.system("git add sneak.py && git commit -qm sneak")
    if ph == "1" and E("WRAP_REPLACE"): sh("mkdir -p src && printf 'evil = 1\\n' > src/x.py && git replace $(git hash-object -w src/x.py) $(printf 'good = 1\\n' | git hash-object -w --stdin)")
    if ph == "2" and E("WRAP_STRAY"): open(E("WRAP_STRAY"), "w").write("x = 1\\n")
    if ph == "2" and E("WRAP_EXTRA"): open("extra.txt", "w").write("x\\n")
    if ph == "2" and E("WRAP_SYMREF"): sh(f"git symbolic-ref HEAD refs/heads/{E('WRAP_SYMREF')}")
    if ph == "2" and E("WRAP_TAG"): sh("echo evil > evil.py && git add evil.py && git tag at-lane/TST-003-p2 $(git commit-tree $(git write-tree) -p HEAD -m evil) && git rm -q --cached evil.py && rm evil.py")
    if ph == "3" and E("WRAP_MOVE") == "after":
        for _ in range(300):
            if sh("git log -1 --format=%s refs/heads/at-lane/TST-003-p2").stdout.startswith(b"feat: TST-003 phase 2"): break
            time.sleep(0.1)
        sh("git update-ref refs/heads/at-lane/TST-003-p2 $(git commit-tree refs/heads/at-lane/TST-003-p2^{tree} -p refs/heads/at-lane/TST-003-p2 -m moved)")
    if ph in E("WRAP_HANG_PHASE", "").split(","):
        if E("WRAP_PIDS"): open(f"{E('WRAP_PIDS')}/{ph}", "w").write(str(os.getpid()))
        time.sleep(float(E("WRAP_HANG_SECS", "5")))
os.execv(sys.argv[0] + ".fake", sys.argv)
"""
def edit_task(tmp, fn, tid="TST-003"):
    f = next((tmp / "docs/tasks_manager/_todos").glob(f"{tid}-*.md")); f.write_text(fn(f.read_text()))
    subprocess.run(["git", "-C", str(tmp), "commit", "-qam", "edit task"], check=True)
def mark_unattended(cap=None):
    def fn(t):
        t = t.replace("| Blocked by    |", "| Execution     | unattended |\n| Blocked by    |")
        return t.replace("### Acceptance criteria", f"### Unattended run\n\nChecked: today, READY\n{cap + chr(10) if cap else ''}\n### Acceptance criteria", 1)
    return fn
def after(*pairs):  # (phase title, "After: ...") lines under the phase headings
    def fn(t):
        for title, line in pairs: t = t.replace(f"#### Phase {title}\n", f"#### Phase {title}\n\n{line}\n", 1)
        return t
    return fn
def driver(tmp, ids, *args, **env):  # (argv, env) of an `at task run` on the wrapped fake harness
    drv = tmp.parent / (tmp.name + "-wrap"); drv.write_text(WRAP); drv.chmod(0o755)
    os.symlink(FAKE, str(drv) + ".fake") if not os.path.exists(str(drv) + ".fake") else None
    e = dict(dict(os.environ, AT_TASKS_ROOT=str(ROOT / "plugins/agents-tasks"), FAKE_SCENARIO="pass", FAKE_CALLS=str(tmp.parent / (tmp.name + ".calls"))), **env)
    return [str(AT), "task", "run", *ids, "--harness", "claude", "--driver-cmd", str(drv), *args], e
def run_ids(tmp, ids, *args, **env):
    argv, e = driver(tmp, ids, *args, **env)
    return subprocess.run(argv, cwd=str(tmp), capture_output=True, text=True, env=e)
def rows(tmp): return [l.split("|")[2].strip() for l in (tmp / STATE).read_text().splitlines() if l[:3] in ("| 1", "| 2", "| 3")]
def git(tmp, *a): return subprocess.run(["git", "-C", str(tmp), *a], capture_output=True, text=True).stdout
def state(tmp): return (tmp / STATE).read_text()
class Marks(unittest.TestCase):
    def test_blocked_row_does_not_end_the_run_dependants_park_and_exit_is_4(self):
        tmp = repo(); edit_task(tmp, lambda t: mark_unattended()(t.replace("#### Phase 3: Hardening\n", "#### Phase 3: Hardening\n\nAfter: 1\n")))
        p = run_ids(tmp, ["TST-003"], "--check", "test ! -f src/phase2.py || test -f ok"); self.assertEqual(p.returncode, 4, p.stdout + p.stderr)
        self.assertEqual(rows(tmp), ["committed", "parked", "committed"], state(tmp)); self.assertEqual(git(tmp, "status", "--porcelain").strip(), "")
        self.assertIn('as "at task run: TST-003 phase 2 not finished"', state(tmp))  # 7: the stash name is in the row's note
        self.assertIn("phase 2 not finished", git(tmp, "stash", "list"))
    def test_without_unattended_the_row_stays_blocked_exit_1_and_serial_dependants_park(self):
        tmp = repo(); p = run_ids(tmp, ["TST-003"], "--check", "test ! -f src/phase2.py"); self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertEqual(rows(tmp), ["committed", "blocked", "parked"]); self.assertIn("Note: parked phase 3: waits on phase 2", state(tmp))
        p = run_ids(tmp, ["TST-003"]); self.assertEqual(p.returncode, 1); self.assertIn("--retry-blocked", p.stdout)
        p = run_ids(tmp, ["TST-003"], "--retry-blocked"); self.assertEqual(p.returncode, 0, p.stdout + p.stderr); self.assertEqual(rows(tmp), ["committed"] * 3)
    def test_a_dependency_parked_row_runs_once_its_blocker_commits_but_a_row_parked_for_itself_stays(self):  # 6
        tmp = repo(); run_ids(tmp, ["TST-003"], "--check", "test ! -f src/phase2.py"); self.assertEqual(rows(tmp), ["committed", "blocked", "parked"])
        (tmp / STATE).write_text(state(tmp).replace("| 2 | blocked |", "| 2 | pending |") + "Note: parked phase 3: it did not finish; see the notes above\n")  # 4: a later note does not hide the row's own reason
        p = run_ids(tmp, ["TST-003"]); self.assertEqual((p.returncode, rows(tmp)), (0, ["committed"] * 3), p.stdout + p.stderr)
        tmp = repo(); edit_task(tmp, mark_unattended()); run_ids(tmp, ["TST-003"], "--check", "test ! -f src/phase2.py"); self.assertEqual(rows(tmp), ["committed", "parked", "parked"])
        old = re.sub(r"(?m)^updated: .*", "updated: 2000-01-01T00:00:00", state(tmp)); (tmp / STATE).write_text(old); git(tmp, "commit", "-qam", "age the state")
        before = git(tmp, "rev-parse", "HEAD"); p = run_ids(tmp, ["TST-003"]); self.assertEqual((p.returncode, rows(tmp)), (4, ["committed", "parked", "parked"]), p.stdout)
        self.assertEqual((git(tmp, "rev-parse", "HEAD"), state(tmp)), (before, old))  # 5: a rerun that changes nothing adds no Note: and no commit
    def test_after_none_and_after_lines(self):
        import sys; sys.path.insert(0, str(ROOT / "plugins/agents-core/lib")); import task_run
        ph = lambda *b: type("T", (), {"phases": [type("P", (), {"body": list(x)}) for x in b]})
        t = ph([], ["After: none"], ["", "After: 1, 2"], [])
        self.assertEqual([task_run.phase_deps(t, n) for n in (1, 2, 3, 4)], [[], [], [1, 2], [3]]); self.assertEqual(task_run.after_problems(t), [])
    def test_after_naming_a_missing_phase_or_forming_a_cycle_exits_2_before_any_phase(self):  # 9
        for fn in (after(("1: Current-state review", "After: 9")), after(("1: Current-state review", "After: 2"), ("2: Implementation", "After: 1")),
                   after(("2: Implementation", "After: 2"))):
            tmp = repo(); edit_task(tmp, fn); p = run_ids(tmp, ["TST-003"]); self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            self.assertFalse((tmp.parent / (tmp.name + ".calls")).exists()); self.assertFalse((tmp / STATE).exists())
    def test_a_bad_task_id_anywhere_in_a_chain_exits_2_before_the_first_task_runs(self):  # 10
        for bad in ("../x", "NOPE-9", "tst-003"):
            tmp = repo(); p = run_ids(tmp, ["TST-003", bad]); self.assertEqual(p.returncode, 2, p.stdout + p.stderr); self.assertFalse((tmp / STATE).exists())
    def cap(self, flag="continue", sev="I", line="", edit=None, header=None, **env):
        tmp = repo(); edit_task(tmp, mark_unattended(line))
        if edit: edit_task(tmp, edit)
        env.update(WRAP_PHASE="1", WRAP_SEV=sev, **({"WRAP_HEADER": header} if header else {}))
        return tmp, run_ids(tmp, ["TST-003"], "--phase", "1", "--max-rounds", "2", *(["--at-review-cap", flag] if flag else []), **env)
    def test_review_cap_continue_commits_with_a_decision_line_naming_findings_without_their_text(self):  # 11
        tmp, p = self.cap(); self.assertEqual(p.returncode, 0, p.stdout + p.stderr); self.assertEqual(rows(tmp)[0], "committed")
        d = "Decision: phase 1 committed at the fix-loop cap with 1 open finding(s), none critical: [I] quality review, docs/tasks_manager/_runs/TST-003/phase-1/re-review-2-quality.md"
        self.assertIn(d, state(tmp)); self.assertIn(d, git(tmp, "log", "--format=%B")); self.assertNotIn("naming", state(tmp) + git(tmp, "log", "--format=%B"))
    def test_review_cap_parks_without_the_flag_on_a_critical_or_when_not_unattended_even_if_the_task_file_says_continue(self):  # 1
        for flag, sev, line, edit, code, status in ((None, "I", "", None, 4, "parked"), ("park", "I", "", None, 4, "parked"), (None, "I", "At review cap: continue", None, 4, "parked"),
                                                    ("continue", "C", "", None, 4, "parked"), ("continue", "I", "", lambda t: t.replace("| unattended |", "| not unattended |"), 1, "blocked")):
            tmp, p = self.cap(flag, sev, line, edit); self.assertEqual((p.returncode, rows(tmp)[0]), (code, status), (flag, sev, line, p.stdout + p.stderr))
    def test_an_implementer_rewriting_the_task_file_to_continue_does_not_change_the_rule(self):  # 1
        tmp, p = self.cap(None, line="At review cap: park", WRAP_EDIT_CAP="1"); self.assertEqual((p.returncode, rows(tmp)[0]), (4, "parked"), p.stdout + p.stderr)
    def test_a_chain_applies_the_flag_to_every_task(self):  # 1
        tmp = repo(); edit_task(tmp, mark_unattended())
        p = run_ids(tmp, ["TST-003", "TST-003"], "--phase", "1", "--max-rounds", "2", "--at-review-cap", "continue", WRAP_PHASE="1", WRAP_SEV="I")
        self.assertEqual((p.returncode, rows(tmp)[0]), (0, "committed"), p.stdout + p.stderr)
    def test_review_header_that_reports_a_critical_or_a_different_count_or_repeats_never_continues(self):  # 3
        for header in ("## Findings: 2 (C:1 I:1)", "## Findings: 2", "## Findings: 1 (C:1)", "## Findings", "## Findings: 1 (C: 1, I: 0, M: 0)",
                       "## Findings: 1 (C:0 I:1)", "## Findings: 1", "## Findings: 0/1/0", "## Findings: 1 (C:0 I:1 M:0 C:0)", "## Findings: 1 (x C:0 I:1 M:0)",
                       "## Findings: 1 (C:0 I:1 M:0)\n## Findings: 1 (C:0 I:1 M:0)"):
            tmp, p = self.cap(header=header); self.assertEqual((p.returncode, rows(tmp)[0]), (4, "parked"), (header, p.stdout + p.stderr))
        tmp, p = self.cap(sev="Z", header="## Findings: 0 (C:0 I:0 M:0)"); self.assertEqual((p.returncode, rows(tmp)[0]), (4, "parked"))  # nothing parsed
        tmp, p = self.cap(header="## Findings: 1 (C: 0, I: 1, M: 0)"); self.assertEqual((p.returncode, rows(tmp)[0]), (0, "committed"), p.stdout + p.stderr)  # spaced form is read
    def test_an_implementer_that_commits_aborts_the_run_and_a_header_with_trailing_text_parks(self):
        tmp = repo()
        p = run_ids(tmp, ["TST-003"], WRAP_COMMIT="1"); self.assertEqual((p.returncode, rows(tmp)[0]), (1, "blocked"), p.stdout + p.stderr)
        self.assertIn("HEAD moved from ", p.stderr); self.assertIn("git reset --soft", state(tmp)); self.assertEqual(rows(tmp)[1:], ["pending"] * 2)
        tmp, p = self.cap(header="## Findings: 1 (C:0 I:1 M:0) (C:1)"); self.assertEqual((p.returncode, rows(tmp)[0]), (4, "parked"), p.stdout + p.stderr)
    def test_a_fix_round_implementer_that_returns_blocked_commits_nothing_even_at_continue(self):  # 1
        tmp, p = self.cap(WRAP_FIXBLOCK="1"); self.assertEqual((p.returncode, rows(tmp)[0]), (4, "parked"), p.stdout + p.stderr)
        self.assertNotIn("half.py", git(tmp, "ls-files")); self.assertNotIn("Decision:", state(tmp)); self.assertIn("half.py", git(tmp, "stash", "show", "-u", "--name-only"))
    def test_the_execution_cell_is_read_value_by_value_and_a_fence_above_it_does_not_matter(self):  # 2
        row = lambda cell: lambda t: t.replace("| unattended |", f"| {cell} |")
        for edit, code, status in ((row("orchestrated, unattended"), 0, "committed"), (row("unattended, parallel"), 0, "committed"),
                                   (row("not unattended"), 1, "blocked"), (row("unattended is forbidden here"), 1, "blocked"),
                                   (lambda t: t.replace("| Execution", "```\nx\n```\n| Execution", 1), 0, "committed")):
            tmp, p = self.cap(edit=edit); self.assertEqual((p.returncode, rows(tmp)[0]), (code, status), (edit("| unattended |"), p.stdout + p.stderr))
    def test_a_failed_post_phase_check_stops_the_run_with_exit_1(self):  # 4
        import sys, io, contextlib; sys.path.insert(0, str(ROOT / "plugins/agents-core/lib")); import task_run; from unittest import mock
        tmp = repo(); env = dict(AT_TASKS_ROOT=str(ROOT / "plugins/agents-tasks"), FAKE_SCENARIO="pass", FAKE_CALLS=str(tmp.parent / (tmp.name + ".calls")))
        with mock.patch.object(task_run.Runner, "post_phase_checks", return_value=False), mock.patch.dict(os.environ, env), contextlib.redirect_stdout(io.StringIO()):
            code = task_run.main(["TST-003", "--harness", "claude", "--driver-cmd", str(FAKE)], tmp, ROOT / "plugins/agents-core", ROOT / "plugins/agents-tasks/skills/task-ledger/scripts")
        self.assertEqual((code, rows(tmp)), (1, ["committed", "pending", "pending"]))
    def test_the_run_state_commit_leaves_the_users_staged_work_alone(self):  # 5
        tmp = repo(); run_ids(tmp, ["TST-003"], "--check", "test ! -f src/phase2.py"); (tmp / "user.txt").write_text("mine"); git(tmp, "add", "user.txt")
        p = run_ids(tmp, ["TST-003"]); self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertNotIn("user.txt", git(tmp, "show", "--name-only", "--format=", "HEAD")); self.assertEqual(git(tmp, "diff", "--cached", "--name-only").strip(), "user.txt")
    def test_a_failing_git_stash_stops_the_run_with_a_message_and_a_note(self):  # 7
        tmp = repo(); p = run_ids(tmp, ["TST-003"], "--phase", "1", "--check", "test ! -f src/phase1.py", WRAP_LOCK="1")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr); self.assertIn("git stash failed", p.stderr); self.assertIn("`git stash` failed", state(tmp))
    def test_a_dispatch_timeout_sets_the_row_aside_like_a_blocked_one_and_independent_phases_still_run(self):  # 8
        tmp = repo(); edit_task(tmp, lambda t: mark_unattended()(after(("2: Implementation", "After: none"), ("3: Hardening", "After: 1"))(t)))
        p = run_ids(tmp, ["TST-003"], "--timeout", "5", WRAP_HANG_PHASE="1"); self.assertEqual(p.returncode, 4, p.stdout + p.stderr); self.assertIn("no reply within 5s", p.stderr)  # 5s, not 1s: phase 2 must answer in time while the suite's steps run side by side
        self.assertEqual(rows(tmp), ["parked", "committed", "parked"], state(tmp)); self.assertEqual(git(tmp, "status", "--porcelain").strip(), "")
        self.assertIn("implementer dispatch failed; see docs/tasks_manager/_runs/TST-003/driver.log", state(tmp)); self.assertNotIn("no reply within", state(tmp))  # 4
    def test_chain_runs_in_order_skips_a_task_whose_blocker_is_not_done_and_counts_only_fully_committed_tasks(self):
        tmp = repo(); edit_task(tmp, lambda t: t.replace("| Status   |", "| Blocked by | TST-003 |\n| Status   |"), "TST-001")
        p = run_ids(tmp, ["TST-001", "TST-003"]); self.assertEqual(p.returncode, 4, p.stdout + p.stderr); self.assertIn("skipping TST-001: Blocked by TST-003", p.stderr)
        self.assertEqual(rows(tmp), ["committed"] * 3)
        p = run_ids(tmp, ["TST-003", "TST-001"]); self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertTrue((tmp / "docs/tasks_manager/_runs/TST-001/state.md").exists())
        tmp = repo(); edit_task(tmp, lambda t: t.replace("| Status   |", "| Blocked by | TST-003 |\n| Status   |"), "TST-001")  # 12: --phase 1 does not finish TST-003
        p = run_ids(tmp, ["TST-003", "TST-001"], "--phase", "1"); self.assertEqual(p.returncode, 4, p.stdout + p.stderr); self.assertIn("skipping TST-001", p.stderr)
def lane_task(f2="src/phase2.py", f3="src/phase3.py", unattended=True):  # phases 2 and 3 wait only for phase 1; their fences are the `Files:` lines
    def fn(t):
        t = after(("2: Implementation", "After: 1" + (f"\nFiles: {f2}" if f2 else "")), ("3: Hardening", "After: 1" + (f"\nFiles: {f3}" if f3 else "")))(t)
        return mark_unattended()(t) if unattended else t
    return fn
def lane_dir(tmp, n): return tmp.parent / f"{tmp.name}-lane-TST-003-p{n}"
def lanes(tmp, *args, **env): return run_ids(tmp, ["TST-003"], "--lanes", "2", *args, **env)
def impl_calls(tmp, n): return [c for c in (tmp.parent / (tmp.name + ".calls")).read_text().splitlines() if c.startswith(f"implementer||{n}|")]
def hook(tmp, name, body): f = tmp / ".git/hooks" / name; f.write_text("#!/bin/sh\n" + body); f.chmod(0o755)
FORGE = """b=$(git symbolic-ref -q --short HEAD); [ "$b" = at-lane/TST-003-p2 ] || exit 0
idx=$(git rev-parse --git-dir)/forge-idx; GIT_INDEX_FILE=$idx git read-tree HEAD; blob=$(echo 'evil = 1' | git hash-object -w --stdin)
GIT_INDEX_FILE=$idx git update-index --add --cacheinfo 100644,$blob,evil.py; rm -f "$idx.lock"
git update-ref refs/heads/$b $(git commit-tree $(GIT_INDEX_FILE=$idx git write-tree) -p HEAD^ -m forged); rm -f "$idx"
"""  # post-commit in a lane: the branch moves to a forged commit on the same base before the driver reads the SHA
def killed(tmp, merge2):  # what a driver killed mid-wave leaves: phase 1 committed, lane 2 committed (and merged when merge2), lane 3 empty
    edit_task(tmp, lane_task()); run_ids(tmp, ["TST-003"], "--phase", "1"); base = git(tmp, "rev-parse", "HEAD").strip()
    for n in (2, 3): git(tmp, "worktree", "add", "-q", "-b", f"at-lane/TST-003-p{n}", str(lane_dir(tmp, n)), base)
    (lane_dir(tmp, 2) / "src/phase2.py").write_text("lane work\n"); git(lane_dir(tmp, 2), "add", "src"); git(lane_dir(tmp, 2), "commit", "-qm", "feat: TST-003 phase 2 — lane")
    if merge2: git(tmp, "merge", "--no-ff", "-qm", "merge: TST-003 phase 2 lane", "at-lane/TST-003-p2")
    return base
class Lanes(unittest.TestCase):
    def test_two_independent_phases_run_at_the_same_time_and_merge_in_phase_order_with_one_wave_review(self):
        tmp = repo(); edit_task(tmp, lane_task()); p = lanes(tmp, FAKE_BARRIER=f"{tmp.parent}/{tmp.name}-bar:2:2,3")  # each implementer waits for the other: serial runs fail
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr); self.assertEqual(rows(tmp), ["committed"] * 3, state(tmp))
        merges = git(tmp, "log", "--merges", "--format=%s").splitlines(); self.assertEqual([m.split(" lane")[0] for m in merges], ["merge: TST-003 phase 3", "merge: TST-003 phase 2"])
        self.assertTrue(all((tmp / f"src/phase{n}.py").exists() for n in (1, 2, 3)))
        self.assertEqual(git(tmp, "status", "--porcelain").strip(), ""); self.assertEqual(git(tmp, "branch", "--list", "at-lane/*").strip(), "")
        self.assertEqual(git(tmp, "worktree", "list").count("\n"), 1); self.assertFalse(lane_dir(tmp, 2).exists())
        runs = tmp / "docs/tasks_manager/_runs/TST-003"; self.assertIn("PASS", (runs / "wave-1/review.md").read_text()); self.assertTrue((runs / "phase-2/brief.md").exists())
        self.assertEqual((tmp.parent / (tmp.name + ".calls")).read_text().count("reviewer|both|2|"), 1)  # one review of the wave, run on its lowest phase
        self.assertEqual((tmp / "docs/tasks_manager/_todos").glob("TST-003-*.md").__next__().read_text().count("- [ ]"), 0)
        s = state(tmp); self.assertLess(s.index("Note: wave 1: base "), s.index("Note: wave 1: done"))
        self.assertTrue(all(f.startswith("docs/") for f in git(tmp, "show", "--name-only", "--format=", ":/chore: TST-003 wave 1").split()))  # 1: the wave commit holds bookkeeping only
    def test_overlapping_or_missing_fences_fall_back_to_serial(self):
        for f2, f3 in (("src", "src/phase3.py"), ("src/phase2.py", None), ("../x", "src/phase3.py")):
            tmp = repo(); edit_task(tmp, lane_task(f2, f3)); p = lanes(tmp); self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertEqual((git(tmp, "log", "--merges", "--format=%s"), (tmp / "docs/tasks_manager/_runs/TST-003/wave-1").exists()), ("", False), (f2, f3))
    def test_lanes_cap_the_wave_and_dry_run_prints_the_planned_waves(self):  # 10, 14
        tmp = repo(); edit_task(tmp, lambda t: mark_unattended()(after(*((f"{n}: {h}", f"After: none\nFiles: src/phase{n}.py") for n, h in ((1, "Current-state review"), (2, "Implementation"), (3, "Hardening"))))(t)))
        p = lanes(tmp, "--dry-run"); self.assertIn("[dry-run] wave 1: phases 1, 2 in lanes", p.stdout); self.assertIn("[dry-run] phase 3: serial", p.stdout)
        p = lanes(tmp); self.assertEqual(p.returncode, 0, p.stdout + p.stderr); self.assertEqual(rows(tmp), ["committed"] * 3)
        self.assertEqual(len(git(tmp, "log", "--merges", "--format=%s").splitlines()), 2); self.assertFalse((tmp / "docs/tasks_manager/_runs/TST-003/wave-2").exists())
    def test_a_conflict_parks_one_lane_keeps_its_worktree_and_commits_the_other(self):
        tmp = repo(); edit_task(tmp, lane_task()); p = lanes(tmp, "--check", "true", FAKE_SHARED="shared.txt")  # both lanes add shared.txt with different text
        self.assertEqual(p.returncode, 4, p.stdout + p.stderr); self.assertEqual(rows(tmp), ["committed", "committed", "parked"], state(tmp))
        self.assertEqual(git(tmp, "status", "--porcelain").strip(), ""); self.assertFalse((tmp / ".git/MERGE_HEAD").exists()); self.assertEqual((tmp / "shared.txt").read_text(), "phase 2\n")
        self.assertEqual(git(tmp, "log", "--merges", "--format=%s").count("merge:"), 1)
        self.assertTrue(lane_dir(tmp, 3).exists() and not lane_dir(tmp, 2).exists()); self.assertIn("at-lane/TST-003-p3", git(tmp, "branch", "--list"))
        self.assertIn(f"Note: parked phase 3: lane its merge conflicts (merge aborted); work kept in {lane_dir(tmp, 3)} (branch at-lane/TST-003-p3)", state(tmp))
        self.assertIn(f"Note: lane phase 3: worktree {lane_dir(tmp, 3)}, branch at-lane/TST-003-p3", state(tmp))
    def test_a_red_check_that_also_dirties_a_tracked_file_undoes_that_merge_and_parks_that_lane(self):  # 2
        tmp = repo(); edit_task(tmp, lane_task()); p = lanes(tmp, "--check", "test ! -f src/phase2.py -o ! -f src/phase3.py || { echo dirt >> src/phase3.py; echo junk > junk.txt; git init -q sub; false; }")
        self.assertEqual(p.returncode, 4, p.stdout + p.stderr); self.assertEqual(rows(tmp), ["committed", "committed", "parked"], state(tmp))
        self.assertTrue((tmp / "src/phase2.py").exists() and not (tmp / "src/phase3.py").exists()); self.assertEqual(git(tmp, "status", "--porcelain").strip(), "")
        self.assertTrue(lane_dir(tmp, 3).exists()); self.assertIn("check failed after its merge (merge undone)", state(tmp)); self.assertFalse((tmp / "junk.txt").exists() or (tmp / "sub").exists())  # 4 (round 2); a nested repository is one directory entry
    def test_a_lane_implementer_writing_into_the_integration_checkout_undoes_the_wave(self):  # 1
        tmp = repo(); edit_task(tmp, lane_task()); stray = tmp / "src/evil_direct.py"; p = lanes(tmp, WRAP_STRAY=str(stray))
        self.assertEqual(p.returncode, 4, p.stdout + p.stderr); self.assertEqual(rows(tmp), ["committed", "parked", "parked"], state(tmp))
        self.assertNotIn("evil_direct", git(tmp, "log", "--all", "--name-only", "--format=")); self.assertTrue(stray.exists())
        self.assertEqual(git(tmp, "log", "--merges", "--format=%s"), ""); self.assertFalse((tmp / "src/phase2.py").exists())
        self.assertIn("Note: wave 1: undone — paths changed in the integration checkout outside every lane: src/evil_direct.py; edits to tracked files saved", state(tmp))
        self.assertTrue(lane_dir(tmp, 2).exists() and lane_dir(tmp, 3).exists())
        tmp = repo(); edit_task(tmp, lane_task()); p = lanes(tmp, WRAP_STRAY=str(tmp / ".gitignore"))  # round 2, 5: a stray edit to a tracked file is kept as a patch
        self.assertEqual(p.returncode, 4, p.stdout + p.stderr); self.assertIn("edits to tracked files saved to docs/tasks_manager/_runs/TST-003/wave-1/stray.patch", state(tmp))
        patch = (tmp / "docs/tasks_manager/_runs/TST-003/wave-1/stray.patch").read_text(); self.assertIn("+x = 1", patch); self.assertIn("-docs/tasks_manager/_runs/**/diff.patch", patch)
    def test_a_failed_wave_review_undoes_the_wave_and_a_rerun_does_not_forget_it(self):  # 7
        tmp = repo(); edit_task(tmp, lane_task()); p = lanes(tmp, WRAP_WAVE_FAIL="1")
        self.assertEqual(p.returncode, 4, p.stdout + p.stderr); self.assertEqual(rows(tmp), ["committed", "parked", "parked"], state(tmp))
        self.assertEqual(git(tmp, "log", "--merges", "--format=%s"), ""); self.assertFalse((tmp / "src/phase2.py").exists()); self.assertEqual(git(tmp, "status", "--porcelain").strip(), "")
        self.assertIn("Note: wave 1: undone — its review did not pass", state(tmp)); self.assertTrue(lane_dir(tmp, 2).exists() and lane_dir(tmp, 3).exists())
        for a in ((), ("--retry-blocked",)):
            p = lanes(tmp, *a); self.assertEqual(p.returncode, 4, p.stdout + p.stderr); self.assertEqual(len(impl_calls(tmp, 2)), 1)
    def test_the_task_file_is_ticked_only_together_with_the_ledger_sync(self):  # 8
        chk = f"python3 {ROOT}/plugins/agents-tasks/skills/task-ledger/scripts/sync_todo_ledgers.py --check --root ."
        tmp = repo(); edit_task(tmp, lane_task()); p = lanes(tmp, "--check", chk); self.assertEqual((p.returncode, rows(tmp)), (0, ["committed"] * 3), p.stdout + p.stderr)
    def test_the_merge_takes_the_reviewed_commit_by_sha_never_a_tag_of_the_same_name(self):  # 4
        tmp = repo(); edit_task(tmp, lane_task()); p = lanes(tmp, WRAP_TAG="1"); self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("at-lane/TST-003-p2", git(tmp, "tag")); self.assertNotIn("evil.py", git(tmp, "ls-files")); self.assertTrue((tmp / "src/phase2.py").exists())
    def test_what_is_committed_is_what_was_reviewed(self):  # 5
        tmp = repo(); p = run_ids(tmp, ["TST-003"], "--phase", "1", WRAP_LATE="1"); self.assertEqual((p.returncode, rows(tmp)[0]), (1, "blocked"), p.stdout + p.stderr)
        self.assertIn("Phase 1: the tree changed after review (src/late.py); nothing committed", state(tmp)); self.assertNotIn("TST-003 phase 1", log(tmp))
        tmp = repo(); branch = git(tmp, "branch", "--show-current").strip()
        for env, why in (({"WRAP_SYMREF": branch}, "the lane worktree's HEAD is not refs/heads/at-lane/TST-003-p2"), ({"WRAP_MOVE": "during"}, "does not sit directly on the wave base"),
                         ({"FORGE": "1"}, "does not hold the tree its reviews saw")):  # round 2, 2
            tmp = repo(); edit_task(tmp, lane_task()); hook(tmp, "post-commit", FORGE) if env.pop("FORGE", None) else None; p = lanes(tmp, **env); self.assertEqual(p.returncode, 4, (env, p.stdout + p.stderr))
            self.assertEqual(rows(tmp), ["committed", "parked", "committed"], (env, state(tmp))); self.assertIn(why, state(tmp))
            self.assertNotIn("phase 2", git(tmp, "log", "--first-parent", "--format=%s", branch)); self.assertNotIn("moved", git(tmp, "log", "--format=%s")); self.assertNotIn("evil.py", git(tmp, "ls-files"))
        tmp = repo(); edit_task(tmp, lane_task()); p = lanes(tmp, WRAP_MOVE="after")  # the branch moved after the commit: the reviewed SHA is merged, not the branch
        self.assertEqual((p.returncode, rows(tmp)), (0, ["committed"] * 3), p.stdout + p.stderr); self.assertNotIn("moved", git(tmp, "log", "--format=%s"))
    def test_a_replace_ref_cannot_show_reviewers_other_content_than_the_commit_stores(self):  # round 2, 1
        tmp = repo(); p = run_ids(tmp, ["TST-003"], "--phase", "1", WRAP_REPLACE="1"); self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        diff = (tmp / "docs/tasks_manager/_runs/TST-003/phase-1/diff.patch").read_text(); self.assertIn("+evil = 1", diff); self.assertNotIn("good = 1", diff)
    def test_a_rejected_wave_commit_leaves_the_wave_open_and_nothing_staged(self):  # round 2, 3
        tmp = repo(); edit_task(tmp, lane_task())
        hook(tmp, "pre-commit", "git diff --cached --name-only | grep -q _active.md && ! git diff --cached --name-only | grep -q '^src/' && exit 1\nexit 0\n")
        p = lanes(tmp); self.assertEqual(p.returncode, 1, p.stdout + p.stderr); self.assertIn("commit `chore: TST-003 wave 1` failed", p.stderr)
        self.assertNotIn("Note: wave 1: done", state(tmp)); self.assertEqual(git(tmp, "diff", "--cached", "--name-only").strip(), "")
        p = lanes(tmp); self.assertEqual(p.returncode, 1, p.stdout + p.stderr); self.assertIn("wave 1 of TST-003 did not finish", p.stderr)
    def test_an_implementer_commit_in_a_lane_parks_that_lane_and_never_reaches_the_integration_branch(self):
        tmp = repo(); edit_task(tmp, lane_task(unattended=False)); p = lanes(tmp, WRAP_COMMIT="1", WRAP_COMMIT_PHASE="2")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr); self.assertEqual(rows(tmp), ["committed", "blocked", "committed"], state(tmp))  # not unattended: blocked, not parked
        self.assertFalse((tmp / "sneak.py").exists()); self.assertIn("HEAD moved", state(tmp)); self.assertIn("sneak.py", git(lane_dir(tmp, 2), "ls-files"))
    def test_a_rerun_after_a_kill_reports_a_lane_holding_work_and_reuses_an_empty_one(self):
        tmp = repo(); edit_task(tmp, lane_task()); self.assertEqual(run_ids(tmp, ["TST-003"], "--phase", "1").returncode, 0)
        for n in (2, 3): git(tmp, "worktree", "add", "-q", "-b", f"at-lane/TST-003-p{n}", str(lane_dir(tmp, n)), "HEAD")
        (lane_dir(tmp, 2) / "half.py").write_text("unfinished\n")  # what a killed lane leaves
        p = lanes(tmp); self.assertEqual(p.returncode, 4, p.stdout + p.stderr); self.assertEqual(rows(tmp), ["committed", "parked", "committed"], state(tmp))
        self.assertEqual((lane_dir(tmp, 2) / "half.py").read_text(), "unfinished\n"); self.assertFalse(lane_dir(tmp, 3).exists())
        self.assertIn(f"Note: parked phase 2: an earlier lane holds work in {lane_dir(tmp, 2)}", state(tmp)); self.assertEqual(git(tmp, "status", "--porcelain").strip(), "")
    def test_a_kill_mid_wave_stops_the_rerun_and_a_merged_lane_is_never_implemented_again(self):  # 3
        tmp = repo(); base = killed(tmp, merge2=True); (tmp / STATE).write_text(state(tmp) + f"Note: wave 1: base {base}, phases 2, 3\n")
        head = git(tmp, "rev-parse", "HEAD"); before = len(impl_calls(tmp, 1))
        for a in (("--lanes", "2"), ("--phase", "2"), ()):
            p = run_ids(tmp, ["TST-003"], *a); self.assertEqual(p.returncode, 1, p.stdout + p.stderr); self.assertIn(f"Recover with `git reset --hard {base}`", p.stderr)
        self.assertEqual((git(tmp, "rev-parse", "HEAD"), len(impl_calls(tmp, 1)), impl_calls(tmp, 2)), (head, before, []))  # nothing reset, nothing dispatched
        git(tmp, "reset", "-q", "--hard", base); p = lanes(tmp); self.assertEqual(p.returncode, 4, p.stdout + p.stderr)
        self.assertEqual((rows(tmp), impl_calls(tmp, 2)), (["committed", "parked", "committed"], []), state(tmp)); self.assertEqual((lane_dir(tmp, 2) / "src/phase2.py").read_text(), "lane work\n")
        tmp = repo(); killed(tmp, merge2=True); p = lanes(tmp)  # no wave note (killed before it was saved, or removed by hand): the merged lane still holds work
        self.assertEqual((p.returncode, rows(tmp)[1], impl_calls(tmp, 2)), (4, "parked", []), p.stdout + p.stderr)
    def test_a_merged_lane_of_a_committed_row_left_by_a_kill_is_removed_not_reported(self):  # round 2, 7
        tmp = repo(); killed(tmp, merge2=True); sha = git(tmp, "rev-parse", "--short", "HEAD").strip()
        (tmp / STATE).write_text(re.sub(r"(?m)^\| 2 \|.*$", f"| 2 | committed | 1 | PASS | PASS | n/a | 0 | {sha} | — |", state(tmp))); p = lanes(tmp)
        self.assertNotIn("holds work", p.stdout); self.assertFalse(lane_dir(tmp, 2).exists()); self.assertEqual(git(tmp, "branch", "--list", "at-lane/*").strip(), "")
    def test_leftover_lanes_are_reported_on_a_serial_rerun_a_retry_or_phase_n_and_their_phase_never_runs(self):  # 6
        tmp = repo(); killed(tmp, merge2=False)
        for a in ((), ("--retry-blocked",), ("--phase", "2")):
            p = run_ids(tmp, ["TST-003"], *a); self.assertIn(f"phase 2: an earlier lane holds work in {lane_dir(tmp, 2)}", p.stdout, a)
            self.assertEqual((rows(tmp)[1], impl_calls(tmp, 2)), ("parked", []), (a, p.stdout + p.stderr)); self.assertTrue(lane_dir(tmp, 2).exists())
        self.assertFalse(lane_dir(tmp, 3).exists()); self.assertEqual(rows(tmp)[2], "committed")  # the empty lane was removed and phase 3 ran
    def test_a_foreign_directory_or_dangling_link_at_a_lane_path_parks_that_phase_only(self):  # 10, 11
        for make in (lambda d: (d.mkdir(), (d / "mine.txt").write_text("not a lane\n")), lambda d: d.symlink_to(d.parent / "nowhere")):
            tmp = repo(); edit_task(tmp, lane_task()); make(lane_dir(tmp, 3)); p = lanes(tmp)
            self.assertEqual((p.returncode, rows(tmp)), (4, ["committed", "committed", "parked"]), p.stdout + p.stderr); self.assertTrue(os.path.lexists(lane_dir(tmp, 3)))
    def test_the_wave_review_names_every_fence_and_the_paths_a_lane_changed_outside_it(self):  # 12
        import sys; sys.path.insert(0, str(ROOT / "plugins/agents-core/lib")); import task_run, task_lanes
        t = type("T", (), {"phases": [type("P", (), {"body": ["Files: a.py, b/", "x", "Files: `c`"]}), type("P", (), {"body": ["Files: /abs"]})]})
        self.assertEqual((task_lanes.fence(t, 1), task_lanes.fence(t, 2)), (["a.py", "b", "c"], None))
        tmp = repo(); edit_task(tmp, lane_task(f3="src/phase3.py\nFiles: docs/notes")); prompts = tmp.parent / (tmp.name + ".prompts")
        p = lanes(tmp, WRAP_EXTRA="1", WRAP_PROMPTS=str(prompts)); self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("phase 2: Files: src/phase2.py (changed outside it: extra.txt); phase 3: Files: src/phase3.py, docs/notes.", prompts.read_text())
    def test_sigterm_ends_the_lane_harnesses_and_releases_the_lock(self):  # 9
        import signal, time
        tmp = repo(); edit_task(tmp, lane_task()); run_ids(tmp, ["TST-003"], "--phase", "1"); pids = tmp.parent / (tmp.name + "-pids"); pids.mkdir()
        argv, e = driver(tmp, ["TST-003"], "--lanes", "2", WRAP_HANG_PHASE="2,3", WRAP_HANG_SECS="60", WRAP_PIDS=str(pids))
        proc = subprocess.Popen(argv, cwd=str(tmp), env=e, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True); kids = []
        try:
            for _ in range(200):
                if len(list(pids.iterdir())) == 2: break
                time.sleep(0.1)
            kids = [int(f.read_text()) for f in pids.iterdir()]; self.assertEqual(len(kids), 2)
            proc.send_signal(signal.SIGTERM); out, err = proc.communicate(timeout=30); self.assertEqual(proc.returncode, 143, out + err)
            def alive(pid):
                try: os.kill(pid, 0); return True
                except ProcessLookupError: return False
            for _ in range(50):
                if not any(map(alive, kids)): break
                time.sleep(0.1)
            self.assertEqual([k for k in kids if alive(k)], []); self.assertFalse((tmp / "docs/tasks_manager/_runs/TST-003/lock").exists()); self.assertIn("interrupted", err)
        finally:
            proc.kill() if proc.poll() is None else None
            for k in kids:
                try: os.kill(k, signal.SIGKILL)
                except ProcessLookupError: pass
    def test_lanes_must_be_1_to_3_and_cannot_skip_commits(self):
        tmp = repo()
        for a in (("--lanes", "4"), ("--lanes", "0"), ("--lanes", "2", "--no-commit")):
            p = run_ids(tmp, ["TST-003"], *a); self.assertEqual(p.returncode, 2, p.stderr)
def ledger_tools(tmp, body):  # a copy of agents-tasks whose sync_todo_ledgers.py gets `body` after its __future__ import (task_brief imports it); returns the AT_TASKS_ROOT to use
    dst = tmp.parent / (tmp.name + "-tasks"); shutil.copytree(ROOT / "plugins/agents-tasks", dst)
    f = dst / "skills/task-ledger/scripts/sync_todo_ledgers.py"; fut = "from __future__ import annotations\n"; f.write_text(f.read_text().replace(fut, fut + body, 1)); return str(dst)
class FixWave(unittest.TestCase):
    def test_a_reviewing_row_satisfies_after_only_under_no_commit(self):  # D1
        tmp = repo(); edit_task(tmp, lambda t: mark_unattended()(after(("2: Implementation", "After: 1\nFiles: src/phase2.py"), ("3: Hardening", "After: 2\nFiles: src/phase3.py"))(t)))
        run_ids(tmp, ["TST-003"], "--phase", "1"); (tmp / STATE).write_text(state(tmp).replace("| 2 | pending |", "| 2 | reviewing |"))
        p = lanes(tmp, "--dry-run"); self.assertEqual(p.returncode, 0, p.stdout + p.stderr); self.assertNotIn("in lanes", p.stdout)
        p = run_ids(tmp, ["TST-003"], "--no-commit", "--retry-blocked"); self.assertNotIn("waits on phase 2", state(tmp), p.stdout + p.stderr)  # phase 2's reviewing row opens phase 3 (it then stops on the dirty tree)
    def test_an_aborted_run_leaves_one_note_and_the_report_lists_the_open_rows(self):  # D3
        tmp = repo()
        for _ in range(2): p = run_ids(tmp, ["TST-003"], "--check", "false"); self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertEqual(state(tmp).count("Note: run aborted: baseline check failed before phase 1: false"), 1, state(tmp))
        p = subprocess.run([str(AT), "task", "report", "TST-003"], cwd=str(tmp), capture_output=True, text=True); self.assertEqual(p.returncode, 0, p.stderr)
        rep = (tmp / p.stdout.strip()).read_text(); needs = rep.split("## Needs you")[1].split("## Task")[0]
        self.assertIn("- Phase 1 is pending", needs); self.assertIn("Note: run aborted: baseline check failed", needs); self.assertNotIn("Nothing open", needs)
        # D4: the untracked report does not make the next run refuse the tree
        p = run_ids(tmp, ["TST-003"], "--phase", "1"); self.assertEqual(p.returncode, 0, p.stdout + p.stderr); self.assertEqual(rows(tmp)[0], "committed")
        tracked = subprocess.run(["git", "ls-files", "docs/tasks_manager/_reports"], cwd=str(tmp), capture_output=True, text=True).stdout
        self.assertEqual(tracked, "", "the report rode into the phase commit"); self.assertTrue((tmp / "docs/tasks_manager/_reports").is_dir())
    def test_a_ledger_script_that_dies_with_a_traceback_stops_the_run(self):  # D6
        for only in ("--check", "sync"):
            tmp = repo(); body = "import sys\nif __name__ == '__main__' and %s: raise RuntimeError('ledger boom')\n" % ("'--check' in sys.argv" if only == "--check" else "'--check' not in sys.argv")
            p = run_ids(tmp, ["TST-003"], AT_TASKS_ROOT=ledger_tools(tmp, body)); self.assertEqual(p.returncode, 1, (only, p.stdout + p.stderr))
            self.assertIn("ledger boom", p.stdout + p.stderr + state(tmp), only); self.assertNotEqual(rows(tmp), ["committed"] * 3)
    def test_a_lane_adds_only_its_own_log_entries_to_the_run_log(self):  # D5
        tmp = repo(); edit_task(tmp, lane_task()); run_ids(tmp, ["TST-003"], "--phase", "1"); p = lanes(tmp); self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        calls = (tmp.parent / (tmp.name + ".calls")).read_text().splitlines()
        self.assertEqual((tmp / "docs/tasks_manager/_runs/TST-003/driver.log").read_text().count(" rc="), len(calls))
if __name__ == "__main__": unittest.main()
