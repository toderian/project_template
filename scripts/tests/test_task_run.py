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
import json, os, sys, glob, time
# Test driver around the fake harness. WRAP_PHASE/WRAP_SEV: fail that phase's quality review with one finding (WRAP_HEADER replaces its
# `## Findings:` line). WRAP_FIXBLOCK: a fix-round implementer writes src/half.py and replies BLOCKED. WRAP_EDIT_CAP: an implementer rewrites
# the task file's cap line. WRAP_LOCK: an implementer leaves .git/index.lock, so `git stash` fails. WRAP_HANG_PHASE: that phase's implementer hangs.
E, ph = os.environ.get, os.environ.get("AT_TASK_PHASE")
HDR = "## Findings: 1 (" + " ".join(f"{k}:{int(k == E('WRAP_SEV'))}" for k in "CIM") + ")"
def reply(text, status=0): print(json.dumps({"type": "result", "result": text, "session_id": "s"})); sys.exit(status)
if E("AT_TASK_ROLE") == "reviewer" and E("AT_TASK_STAGE") == "quality" and ph == E("WRAP_PHASE"):
    reply(f"## Status: DONE_WITH_CONCERNS\\n## Verdict: FAIL\\n{E('WRAP_HEADER', HDR)}\\n1. [{E('WRAP_SEV')}] src/x.py:1 - naming\\n## Report: r.md")
if E("AT_TASK_ROLE") == "implementer":
    task = glob.glob("docs/tasks_manager/_todos/TST-003-*.md")[0]; t = open(task).read()
    if E("WRAP_FIXBLOCK") and sys.argv[2].startswith("Fix round"):
        open("src/half.py", "w").write("x = 1\\n"); reply("## Status: BLOCKED\\n## Summary: stuck")
    if E("WRAP_EDIT_CAP"): open(task, "w").write(t.replace("At review cap: park", "At review cap: continue"))
    if E("WRAP_LOCK"): open(".git/index.lock", "w").close()
    if E("WRAP_COMMIT"): open("sneak.py", "w").write("x = 1\\n"); os.system("git add sneak.py && git commit -qm sneak")
    if E("WRAP_HANG_PHASE") == ph: time.sleep(5)
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
def run_ids(tmp, ids, *args, **env):
    drv = tmp.parent / (tmp.name + "-wrap"); drv.write_text(WRAP); drv.chmod(0o755)
    os.symlink(FAKE, str(drv) + ".fake") if not os.path.exists(str(drv) + ".fake") else None
    e = dict(os.environ, AT_TASKS_ROOT=str(ROOT / "plugins/agents-tasks"), FAKE_SCENARIO="pass", FAKE_CALLS=str(tmp.parent / (tmp.name + ".calls")), **env)
    return subprocess.run([str(AT), "task", "run", *ids, "--harness", "claude", "--driver-cmd", str(drv), *args], cwd=str(tmp), capture_output=True, text=True, env=e)
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
        p = run_ids(tmp, ["TST-003"], "--timeout", "1", WRAP_HANG_PHASE="1"); self.assertEqual(p.returncode, 4, p.stdout + p.stderr); self.assertIn("no reply within 1s", p.stderr)
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
if __name__ == "__main__": unittest.main()
