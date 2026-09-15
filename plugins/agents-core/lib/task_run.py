"""`at task run <TASK-ID>` — drive the execute-plan loop from a script, no orchestrator context.

One `claude -p` or `codex exec` process per implementer or reviewer dispatch; the same
`docs/tasks_manager/_runs/<TASK-ID>/` files as the skill; the script commits each phase. This is
the tier-2 runtime from the `agents-core:execute-plan` skill: it needs no session, so nothing
accumulates in a context window, and a stopped run resumes from `state.md` like any other.

Not covered on purpose: adjudication. When a phase does not converge within the fix-loop cap, the
row is set to `blocked` with the open findings and the script exits 1; a person or an orchestrating
agent records `Ruling:` lines and reruns.

Python 3 stdlib only. Imported by lib/at.py; do not run directly.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

STATUS_RE = re.compile(r"^\s*(?:#+\s*)?Status:\s*(DONE_WITH_CONCERNS|DONE|NEEDS_CONTEXT|BLOCKED)\b", re.M)
VERDICT_RE = re.compile(r"^\s*(?:#+\s*)?Verdict:\s*(PASS|FAIL)\b", re.M)
FINDING_RE = re.compile(r"^\s*\d+\.\s*\[([CIM])\]\s*(.+?)\s*$", re.M)
CARD_ROLES = ("implementer", "reviewer", "security-auditor")
STATUS_REMINDER = ("Your previous reply was missing the report block. Finish with, last and exactly:\n"
                   "## Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED\n## Summary: <one line>\n\n")


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class RunError(Exception):
    pass


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def sh(args: list[str], cwd: Path, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, check=False, **kw)


def card_body(core_root: Path, role: str) -> str:
    text = (core_root / "agents" / f"{role}.md").read_text(encoding="utf-8")
    if text.startswith("---"):
        text = text.split("\n---", 1)[1]
    return text.strip()


# ---- state.md ------------------------------------------------------------------

class State:
    """In-memory copy of `_runs/<ID>/state.md`; `save()` rewrites the whole file."""

    def __init__(self, path: Path) -> None:
        self.path = path
        lines = path.read_text(encoding="utf-8").split("\n")
        end = lines.index("---", 1)
        self.front: dict[str, str] = {}
        for line in lines[1:end]:
            k, _, v = line.partition(":")
            self.front[k.strip()] = v.strip()
        self.title = ""
        self.rows: list[list[str]] = []
        self.ledger: list[str] = []
        for line in lines[end + 1:]:
            if line.startswith("# "):
                self.title = line
            elif line.startswith("|"):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if cells and cells[0].isdigit():
                    self.rows.append(cells)
            elif line.strip():
                self.ledger.append(line.rstrip())

    def row(self, n: int) -> list[str]:
        return self.rows[n - 1]

    def set(self, n: int, **cells: str) -> None:
        idx = {"status": 1, "attempt": 2, "spec": 3, "quality": 4, "security": 5, "open": 6, "commit": 7, "agent": 8}
        for k, v in cells.items():
            self.row(n)[idx[k]] = v

    def note(self, line: str) -> None:
        self.ledger.append(line)

    def save(self, **front: str) -> None:
        self.front.update(front)
        self.front["updated"] = now_iso()
        out = ["---"] + [f"{k}: {v}" for k, v in self.front.items()] + ["---", self.title, "",
               "| Phase | Status | Attempt | Spec | Quality | Security | Open | Commit | Agent |",
               "|---|---|---|---|---|---|---|---|---|"]
        out += ["| " + " | ".join(r) + " |" for r in self.rows]
        out += [""] + self.ledger + [""]
        self.path.write_text("\n".join(out), encoding="utf-8")


# ---- harness ---------------------------------------------------------------------

class Harness:
    def __init__(self, name: str, repo: Path, core_root: Path, model: str | None, strong: str | None,
                 driver_cmd: str | None, log: Path, timeout: int, budget_usd: float | None) -> None:
        self.name, self.repo, self.core_root = name, repo, core_root
        self.model, self.strong = model, strong or model
        self.driver_cmd = driver_cmd
        self.log = log
        self.timeout, self.budget_usd = timeout, budget_usd
        self.cost_usd = 0.0  # running total of what Claude reported (Codex reports nothing)

    def _sh(self, role: str, cmd: list[str], **kw) -> subprocess.CompletedProcess:
        try:
            return sh(cmd, self.repo, timeout=self.timeout, **kw)
        except subprocess.TimeoutExpired as exc:
            with self.log.open("a", encoding="utf-8") as fh:
                fh.write(f"\n### {now_iso()} {role} TIMEOUT after {self.timeout}s\n")
            raise RunError(f"{role}: no reply within {self.timeout}s (--timeout); process killed") from exc

    def run(self, role: str, prompt: str, *, writable: bool, strong: bool = False,
            session: str | None = None, env: dict[str, str] | None = None) -> tuple[str, str | None]:
        """Dispatch one subagent; return (final message, session id or None)."""
        model = self.strong if strong else self.model
        system = card_body(self.core_root, role)
        run_env = dict(os.environ, AT_TASK_ROLE=role, **(env or {}))
        if self.name == "claude":
            # The prompt sits right after -p: --allowedTools/--disallowedTools are variadic and would
            # swallow a trailing positional as another tool name.
            cmd = [self.driver_cmd or "claude", "-p", prompt, "--output-format", "json",
                   "--append-system-prompt", system]
            if model:
                cmd += ["--model", model]
            if writable:
                # acceptEdits covers file edits; Bash needs its own allow rule or every test run is
                # denied in -p mode. The plugin's dangerous-git/bash hooks still gate each command.
                cmd += ["--permission-mode", "acceptEdits", "--allowedTools", "Bash"]
            else:
                cmd += ["--permission-mode", "dontAsk",
                        "--disallowedTools", "Edit,Write,MultiEdit,NotebookEdit"]
            if self.budget_usd:
                cmd += ["--max-budget-usd", str(self.budget_usd)]
            if session:
                cmd += ["--resume", session]
            proc = self._sh(role, cmd, env=run_env)
            self._log(role, cmd, proc)
            if proc.returncode != 0:
                raise RunError(f"{role}: claude exited {proc.returncode}: {proc.stderr.strip()[-400:]}")
            try:
                data = json.loads(proc.stdout)
            except json.JSONDecodeError:
                return proc.stdout, None
            if isinstance(data, list):
                data = next((d for d in reversed(data) if d.get("type") == "result"), data[-1] if data else {})
            cost = data.get("total_cost_usd")
            if isinstance(cost, (int, float)):
                self.cost_usd += float(cost)
                with self.log.open("a", encoding="utf-8") as fh:
                    fh.write(f"cost: ${cost:.4f} (run total ${self.cost_usd:.4f})\n")
            return str(data.get("result", "")), data.get("session_id")
        # codex
        out_file = self.log.parent / f"last-message-{role}-{uuid.uuid4().hex[:8]}.txt"  # parallel reviewers share a role
        cmd = [self.driver_cmd or "codex", "exec", "-C", str(self.repo),
               "-s", "workspace-write" if writable else "read-only", "-o", str(out_file)]
        if model:
            cmd += ["-m", model]
        cmd.append("-")
        proc = self._sh(role, cmd, input=system + "\n\n---\n\n" + prompt, env=run_env)
        self._log(role, cmd, proc)
        if proc.returncode != 0:
            raise RunError(f"{role}: codex exited {proc.returncode}: {proc.stderr.strip()[-400:]}")
        message = proc.stdout
        if out_file.exists():
            message = out_file.read_text(encoding="utf-8")
            out_file.unlink()
        return message, None

    def _log(self, role: str, cmd: list[str], proc: subprocess.CompletedProcess) -> None:
        with self.log.open("a", encoding="utf-8") as fh:
            shown = [c if len(c) < 80 else c[:77] + "..." for c in cmd]
            fh.write(f"\n### {now_iso()} {role} rc={proc.returncode}\n$ {' '.join(shown)}\n")
            if proc.stderr.strip():
                fh.write(proc.stderr.strip()[-2000:] + "\n")


# ---- prompts ---------------------------------------------------------------------

def implementer_prompt(runs_rel: str, n: int, project: str, round_no: int = 0, strong: bool = False) -> str:
    base = f"{runs_rel}/phase-{n}"
    head = ""
    if round_no:
        head = (f"Fix round {round_no} of 3 for phase {n}.\n"
                f"Open findings: {base}/findings-{round_no}.md — address every numbered item, nothing else.\n"
                f"What was already done: {base}/report.md (append a '## Fix round {round_no}' section to it).\n")
        if strong:
            head = ("A prior implementer attempted this phase twice; you own it now. Read the brief and the "
                    "findings file fresh; do not trust the earlier report sections.\n") + head
    return (f"{head}Project: {project}\n"
            f"Brief: {base}/brief.md — read this first; it is your full context.\n"
            f"Report path: {base}/report.md\n"
            "Scope fence: only what the brief's phase requires. Do not commit or stage. Do not spawn subagents. "
            "Do not read AGENTS.md, CLAUDE.md, or other skills. Honour the Interface:/Ruling: lines in the brief.\n"
            "Run the checks named in the brief and record real output in the report.\n"
            "Reply with at most 15 lines ending in the ## Status: block (DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED).")


def reviewer_prompt(runs_rel: str, n: int, stage: str, base_rev: str, round_no: int = 0) -> str:
    base = f"{runs_rel}/phase-{n}"
    report = f"{base}/re-review-{round_no}-{stage}.md" if round_no else f"{base}/review-{stage}.md"
    scope = (f"Re-review round {round_no}: judge first whether each item in {base}/findings-{round_no}.md is resolved "
             "without a new defect, then the diff as a whole.\n") if round_no else ""
    return (f"Stage: {stage}\n{scope}"
            f"Brief: {base}/brief.md (requirements and acceptance criteria)\n"
            f"Diff: {base}/diff.patch (BASE {base_rev} → working tree)\n"
            f"Implementer report: {base}/report.md — treat its claims as unverified.\n"
            "Scope fence: read-only; do not edit files. Run tests only to check a specific doubt.\n"
            f"Your reply is the report (it is saved to {report}): the ## Status / ## Verdict / ## Findings block first, "
            "each finding as a numbered line '[C|I|M] path:line — one line', then ## Evidence; at most 40 lines.")


def security_prompt(runs_rel: str, n: int, base_rev: str) -> str:
    base = f"{runs_rel}/phase-{n}"
    return (f"Surface: the orchestrator flagged this phase for a security audit.\n"
            f"Brief: {base}/brief.md\nDiff: {base}/diff.patch (BASE {base_rev} → working tree)\n"
            "Scope fence: read-only; do not edit files.\n"
            f"Your reply is the audit (it is saved to {base}/review-security.md): the ## Status / ## Verdict / ## Findings "
            "block first, each finding as a numbered line '[C|I|M] path:line — one line', then the detail; at most 40 lines.")


def final_prompt(runs_rel: str, k: int, base_rev: str, task_rel: str) -> str:
    return ("Stage: both\nTask description: Review the completed execution of this approved plan as a whole.\n"
            f"Context: {task_rel}, {runs_rel}/state.md (Ruling: lines are decisions, not defects), "
            f"git diff {base_rev}..HEAD.\nScope fence: read-only; do not edit files.\n"
            f"Your reply is the review (it is saved to {runs_rel}/final-review-{k}.md): the ## Status / ## Verdict / "
            "## Findings block first, then ## Evidence; at most 40 lines.")


# ---- parsing replies -------------------------------------------------------------

def parse_status(message: str) -> str:
    m = STATUS_RE.findall(message)
    return m[-1] if m else "MISSING"


def parse_verdict(message: str) -> str:
    m = VERDICT_RE.findall(message)
    return m[-1] if m else "FAIL"


def findings(message: str) -> list[tuple[str, str]]:
    return FINDING_RE.findall(message)


# ---- task file updates -----------------------------------------------------------

def tick_phase(task_path: Path, n: int, entry: str) -> None:
    lines = task_path.read_text(encoding="utf-8").split("\n")
    count = 0
    inphase = False
    stamp = now_iso()
    for i, line in enumerate(lines):
        if line.startswith("#### "):
            count += 1
            inphase = count == n
            continue
        if line.startswith("#") or line.strip() == "---":
            inphase = False
        if inphase and line.lstrip().startswith("- [ ]"):
            lines[i] = line.replace("- [ ]", "- [x]", 1)
        low = line.lower()
        if low.startswith("| updated ") or low.startswith("| last executed "):
            cells = line.split("|")
            cells[2] = f" {stamp} "
            lines[i] = "|".join(cells)
    try:
        at = lines.index("## Completion harvest")
        while at > 0 and (not lines[at - 1].strip() or lines[at - 1].strip() == "---"):
            at -= 1
        lines[at:at] = [""] + entry.split("\n") + [""]
    except ValueError:
        lines += [""] + entry.split("\n")
    task_path.write_text("\n".join(lines), encoding="utf-8")


# ---- the loop --------------------------------------------------------------------

class Runner:
    def __init__(self, args: argparse.Namespace, repo: Path, core_root: Path, tasks_scripts: Path) -> None:
        sys.path.insert(0, str(tasks_scripts))
        import task_brief  # noqa: E402  (agents-tasks skill script)
        self.tb = task_brief
        self.args, self.repo, self.core_root = args, repo, core_root
        self.task = task_brief.load_task(repo, args.task_id)
        self.runs = repo / task_brief.RUNS_DIR / self.task.taskid
        self.runs_rel = self.runs.relative_to(repo).as_posix()
        self.task_rel = self.task.path.relative_to(repo).as_posix()
        self.runs.mkdir(parents=True, exist_ok=True)
        self.harness = Harness(args.harness, repo, core_root, args.model, args.strong_model,
                               args.driver_cmd, self.runs / "driver.log", args.timeout, args.budget_usd)
        self.project = args.project or f"{repo.name}; checks: {', '.join(args.check) or 'none configured'}"
        self.lock = self.runs / "lock"
        self.ledger_script = tasks_scripts / "sync_todo_ledgers.py"

    # -- lock: one driver (or orchestrator) per run directory
    def acquire_lock(self) -> None:
        if self.lock.exists() and not self.args.force_unlock:
            pid, host, started = (self.lock.read_text(encoding="utf-8").split() + ["?", "?", "?"])[:3]
            alive = host == os.uname().nodename and pid.isdigit() and _pid_alive(int(pid))
            if alive:
                raise RunError(f"run in progress (pid {pid} on {host} since {started}); "
                               f"wait for it or pass --force-unlock")
            self.say(f"replacing stale lock (pid {pid} on {host}, not running)")
        self.lock.write_text(f"{os.getpid()} {os.uname().nodename} {now_iso()}\n", encoding="utf-8")

    def release_lock(self) -> None:
        if self.lock.exists() and self.lock.read_text(encoding="utf-8").split()[:1] == [str(os.getpid())]:
            self.lock.unlink()

    # -- helpers
    def say(self, msg: str) -> None:
        print(f"at task run: {msg}")

    def git(self, *a: str) -> subprocess.CompletedProcess:
        return sh(["git", *a], self.repo)

    def head(self) -> str:
        return self.git("rev-parse", "--short", "HEAD").stdout.strip()

    def dispatch(self, role: str, prompt: str, *, writable: bool, strong: bool = False,
                 session: str | None = None, stage: str = "", phase: int = 0) -> tuple[str, str | None]:
        return self.harness.run(role, prompt, writable=writable, strong=strong, session=session,
                                env={"AT_TASK_STAGE": stage, "AT_TASK_PHASE": str(phase)})

    # -- state
    def open_state(self) -> State:
        path = self.runs / "state.md"
        if not path.exists():
            ns = argparse.Namespace(runtime=self.harness.name, base=self.head(),
                                    branch=self.git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip(),
                                    work_mode="same-branch", autonomy="L1")
            path.write_text(self.tb.render_state(self.task, self.repo, ns), encoding="utf-8")
            self.say(f"opened {path.relative_to(self.repo)}")
        errors, _ = self.tb.check_state(path, self.task, self.repo)
        if errors:
            raise RunError("state.md is invalid; fix it first:\n  " + "\n  ".join(errors))
        return State(path)

    def require_clean_tree(self) -> None:
        dirty = [l for l in self.git("status", "--porcelain").stdout.splitlines()
                 if not l[3:].startswith(self.runs_rel)]
        if dirty:
            raise RunError("working tree has changes outside the run directory; commit or stash them first:\n  "
                           + "\n  ".join(dirty[:10]))

    # -- one phase
    def phase(self, state: State, n: int) -> bool:
        pdir = self.runs / f"phase-{n}"
        pdir.mkdir(exist_ok=True)
        self.require_clean_tree()
        for cmd in self.args.check:
            if sh(["bash", "-lc", cmd], self.repo).returncode != 0:
                raise RunError(f"baseline check failed before phase {n}: {cmd}")

        brief = pdir / "brief.md"
        brief.write_text(self.tb.render_brief(self.task, n, self.repo), encoding="utf-8")
        notes = [l for l in state.ledger if l.startswith(("Interface:", "Ruling:"))]
        with brief.open("a", encoding="utf-8") as fh:
            fh.write(f"Work mode: {state.front.get('work_mode')}; autonomy: {state.front.get('autonomy')}.\n")
            fh.write("Scope fence: only the files this phase requires; report NEEDS_CONTEXT for anything else.\n")
            for l in notes:
                fh.write(l + "\n")
        base = self.head()
        attempt = int(state.row(n)[2]) + 1
        state.set(n, status="implementing", attempt=str(attempt), spec="—", quality="—",
                  security="—" if self.args.security else "n/a", open="0")
        state.note(f"Phase {n}: BASE {base}; attempt {attempt} ({self.harness.name})")
        state.save(current_phase=str(n))
        self.say(f"phase {n}: implementer")

        reply, session = self.dispatch("implementer", implementer_prompt(self.runs_rel, n, self.project),
                                       writable=True, phase=n)
        if parse_status(reply) == "MISSING":  # the SubagentStop hook does this for subagents; once, like it
            self.say(f"phase {n}: reply lacks a status block; asking once more")
            reply, session = self.dispatch("implementer", STATUS_REMINDER + implementer_prompt(self.runs_rel, n, self.project),
                                           writable=True, phase=n,
                                           session=session if self.harness.name == "claude" else None)
        (pdir / "implementer-reply.md").write_text(reply, encoding="utf-8")
        status = parse_status(reply)
        if status in ("NEEDS_CONTEXT", "BLOCKED", "MISSING"):
            state.set(n, status="blocked")
            state.note(f"Phase {n}: implementer returned {status}; see {self.runs_rel}/phase-{n}/implementer-reply.md")
            state.save()
            self.say(f"phase {n}: implementer {status}; stopping")
            return False

        verdicts = self.review_round(state, n, pdir, base, round_no=0)
        round_no = 0
        while not verdicts_pass(verdicts) and round_no < self.args.max_rounds:
            round_no += 1
            items = [f"{i}. [{sev}] {text}  (from {stage})" for i, (sev, text, stage)
                     in enumerate(open_findings(verdicts), 1)]
            (pdir / f"findings-{round_no}.md").write_text(
                f"# Open findings — phase {n}, round {round_no}\n\n" + "\n".join(items) + "\n", encoding="utf-8")
            state.set(n, status="fixing", attempt=str(int(state.row(n)[2]) + 1), open=str(len(items)))
            state.note(f"Phase {n}: fix round {round_no}/{self.args.max_rounds} ({len(items)} open)")
            state.save()
            strong = round_no >= self.args.max_rounds
            resume = session if (self.harness.name == "claude" and not strong) else None
            self.say(f"phase {n}: fix round {round_no} ({'fresh, strong' if strong else 'resume' if resume else 'fresh'})")
            reply, new_session = self.dispatch("implementer",
                                               implementer_prompt(self.runs_rel, n, self.project, round_no, strong),
                                               writable=True, strong=strong, session=resume, phase=n)
            session = new_session or session
            (pdir / f"implementer-reply-{round_no}.md").write_text(reply, encoding="utf-8")
            if parse_status(reply) in ("NEEDS_CONTEXT", "BLOCKED", "MISSING"):
                break
            verdicts = self.review_round(state, n, pdir, base, round_no=round_no)

        if not verdicts_pass(verdicts):
            open_items = open_findings(verdicts)
            state.set(n, status="blocked", open=str(len(open_items)))
            state.note(f"Phase {n}: fix-loop cap reached with {len(open_items)} open finding(s); "
                       f"add Ruling: lines (or fix by hand), set the row to pending, and rerun")
            state.save()
            self.say(f"phase {n}: did not converge; row set to blocked")
            return False

        for cmd in self.args.check:
            proc = sh(["bash", "-lc", cmd], self.repo)
            if proc.returncode != 0:
                state.set(n, status="blocked")
                state.note(f"Phase {n}: post-implementation check failed: {cmd}")
                state.save()
                (pdir / "check-failure.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
                self.say(f"phase {n}: check failed: {cmd}")
                return False

        summary = ", ".join(f"{k} {v['verdict']}" for k, v in verdicts.items())
        entry = (f"### {now_iso()} - Phase {n}: {self.tb.phase_title(self.task.phases[n - 1])} (at task run, {self.harness.name})\n\n"
                 f"**Actions taken:** implementer dispatch ×{state.row(n)[2]}; reviews: {summary}.\n"
                 f"**Decisions made:** see `Ruling:` lines in `{self.runs_rel}/state.md` (if any).\n"
                 f"**Test results:** {', '.join(self.args.check) or 'no --check command configured'}: pass.\n"
                 f"**Outcome:** see `{self.runs_rel}/phase-{n}/` for the brief, report and reviews.")
        tick_phase(self.task.path, n, entry)

        if self.args.no_commit:
            state.set(n, status="reviewing")
            state.note(f"Phase {n}: reviews clean; left uncommitted (--no-commit)")
            state.save()
            return True
        # The phase commit carries the code, the task file and the run directory as reviewed. The
        # SHA is then written into state.md, which stays dirty until the next phase's commit sweeps
        # it in (the run directory is exempt from the clean-tree gate); the last one is committed by
        # `run()`. Same rule as the skill: no metadata-only commit per phase.
        if self.ledger_script.exists():  # ticked checkboxes change the generated ledgers; they ride in the commit
            sh([sys.executable, str(self.ledger_script), "--root", str(self.repo)], self.repo)
        self.git("add", "-A", "--", ".", f":(exclude){self.runs_rel}/lock")
        title = self.tb.phase_title(self.task.phases[n - 1])
        msg = (f"feat: {self.task.taskid} phase {n} — {title}\n\nWhat changed:\n- phase {n} of {self.task.title}\n\n"
               f"Why:\n- {self.task_rel}\n\nChecks:\n- {', '.join(self.args.check) or 'none configured'}: pass\n"
               f"- reviews: {summary}\n")
        proc = self.git("commit", "-q", "-m", msg)
        if proc.returncode != 0:
            raise RunError(f"commit failed: {proc.stderr.strip()[-400:]}")
        sha = self.head()
        state.set(n, status="committed", commit=sha, open="0")
        state.note(f"Phase {n}: complete (commit {sha}, {summary})")
        if self.harness.cost_usd:
            state.note(f"Note: phase {n} Claude spend so far ${self.harness.cost_usd:.2f} (run total)")
        state.save()
        self.say(f"phase {n}: committed {sha}")
        return self.post_phase_checks(state, n)

    def post_phase_checks(self, state: State, n: int) -> bool:
        """The same two checks the skill runs after every phase; a failure blocks the next phase."""
        problems: list[str] = []
        errors, _ = self.tb.check_state(state.path, self.task, self.repo)
        problems += errors
        if self.ledger_script.exists():
            proc = sh([sys.executable, str(self.ledger_script), "--check", "--root", str(self.repo)], self.repo)
            if proc.returncode != 0:
                problems += [l for l in (proc.stdout + proc.stderr).splitlines() if l.startswith("ERROR")]
        if problems:
            state.note(f"Note: post-phase checks failed after phase {n}; fix before continuing: " + "; ".join(problems[:3]))
            state.save()
            self.say(f"phase {n}: ledger/run-state check failed:\n  " + "\n  ".join(problems[:5]))
            return False
        return True

    def review_round(self, state: State, n: int, pdir: Path, base: str, round_no: int) -> dict[str, dict]:
        self.git("add", "--intent-to-add", "-A", "--", ".", f":(exclude){self.runs_rel}")  # new files show in the diff
        diff = self.git("diff", base, "--", ".", f":(exclude){self.runs_rel}").stdout
        (pdir / "diff.patch").write_text(diff, encoding="utf-8")
        if not diff.strip():
            return {"spec": {"verdict": "FAIL", "findings": [("C", "implementer changed no files outside the run directory")]}}
        state.set(n, status="reviewing"); state.save()
        jobs = {"spec": ("reviewer", reviewer_prompt(self.runs_rel, n, "spec", base, round_no)),
                "quality": ("reviewer", reviewer_prompt(self.runs_rel, n, "quality", base, round_no))}
        if self.args.security:
            jobs["security"] = ("security-auditor", security_prompt(self.runs_rel, n, base))
        self.say(f"phase {n}: reviews ({', '.join(jobs)})" + (f" re-review {round_no}" if round_no else ""))
        with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
            futures = {k: pool.submit(self.dispatch, role, prompt, writable=False, strong=True, stage=k, phase=n)
                       for k, (role, prompt) in jobs.items()}
            replies = {k: f.result()[0] for k, f in futures.items()}
        out: dict[str, dict] = {}
        for k, reply in replies.items():
            name = f"re-review-{round_no}-{k}.md" if round_no else f"review-{k}.md"
            (pdir / name).write_text(reply, encoding="utf-8")
            out[k] = {"verdict": parse_verdict(reply), "findings": findings(reply)}
            state.set(n, **{k: out[k]["verdict"]})
        state.save()
        return out

    def final_review(self, state: State) -> bool:
        base = state.front.get("base_rev", "")
        self.say("final review (two reviewers, Stage: both)")
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.dispatch, "reviewer", final_prompt(self.runs_rel, k, base, self.task_rel),
                                   writable=False, strong=True, stage=f"final-{k}") for k in (1, 2)]
            replies = [f.result()[0] for f in futures]
        ok = True
        for k, reply in enumerate(replies, 1):
            (self.runs / f"final-review-{k}.md").write_text(reply, encoding="utf-8")
            v = parse_verdict(reply)
            crit = [f for f in findings(reply) if f[0] == "C"]
            state.note(f"Note: final review {k}: {v}, {len(findings(reply))} finding(s), {len(crit)} critical")
            ok = ok and v == "PASS" and not crit
        state.save()
        return ok

    def run(self) -> int:
        state = self.open_state()
        self.acquire_lock()
        try:
            return self._run(state)
        except RunError as exc:
            n = int(state.front.get("current_phase", "0") or 0)
            if n and state.row(n)[1] in ("implementing", "reviewing", "fixing"):
                state.set(n, status="blocked")
                state.note(f"Phase {n}: run aborted — {exc}")
                state.save()
            raise
        finally:
            self.release_lock()

    def _run(self, state: State) -> int:
        todo = [int(r[0]) for r in state.rows if r[1] != "committed"]
        if self.args.phase:
            todo = [n for n in todo if n == self.args.phase]
        if not todo:
            self.say("every phase is already committed")
        if self.args.dry_run:
            for n in todo:
                self.say(f"[dry-run] phase {n}: implementer ({self.harness.name}) -> reviews spec, quality"
                         + (", security" if self.args.security else "") + f" -> up to {self.args.max_rounds} fix rounds -> commit")
            return 0
        for n in todo:
            if state.row(n)[1] in ("blocked", "parked") and not self.args.retry_blocked:
                self.say(f"phase {n} is {state.row(n)[1]}; resolve it in state.md or pass --retry-blocked")
                return 1
            if not self.phase(state, n):
                return 1
        ok = True
        if self.args.final_review and not self.args.phase and all(r[1] == "committed" for r in state.rows):
            ok = self.final_review(state)
        self.commit_run_dir(f"chore: {self.task.taskid} run state")
        return 0 if ok else 1

    def commit_run_dir(self, message: str) -> None:
        dirty = [l for l in self.git("status", "--porcelain", "--", self.runs_rel).stdout.splitlines()
                 if not l.endswith("/lock")]
        if self.args.no_commit or not dirty:
            return
        self.git("add", "--", self.runs_rel, f":(exclude){self.runs_rel}/lock")
        self.git("commit", "-q", "-m", message)


def verdicts_pass(v: dict[str, dict]) -> bool:
    return bool(v) and all(x["verdict"] == "PASS" and not any(s == "C" for s, _ in x["findings"]) for x in v.values())


def open_findings(v: dict[str, dict]) -> list[tuple[str, str, str]]:
    out = []
    for stage in ("spec", "quality", "security"):
        if stage in v and (v[stage]["verdict"] == "FAIL" or any(s == "C" for s, _ in v[stage]["findings"])):
            out += [(s, t, stage) for s, t in v[stage]["findings"]] or [("C", f"{stage} review returned FAIL without findings", stage)]
    return out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="at task run", description=__doc__.split("\n\n")[0])
    p.add_argument("task_id")
    p.add_argument("--harness", choices=("claude", "codex"), help="default: claude if on PATH, else codex")
    p.add_argument("--phase", type=int, help="run only this phase")
    p.add_argument("--model", help="model for implementers (harness default when omitted)")
    p.add_argument("--strong-model", help="model for reviewers and fix round 3 (defaults to --model)")
    p.add_argument("--check", action="append", default=[], metavar="CMD",
                   help="shell command run before and after each phase; repeatable")
    p.add_argument("--security", action="store_true", help="also run security-auditor on every phase")
    p.add_argument("--max-rounds", type=int, default=3)
    p.add_argument("--project", help="one-line project context for the implementer prompt")
    p.add_argument("--no-commit", action="store_true", help="stop after reviews pass; leave the tree uncommitted")
    p.add_argument("--no-final-review", dest="final_review", action="store_false")
    p.add_argument("--retry-blocked", action="store_true", help="re-run rows marked blocked")
    p.add_argument("--timeout", type=int, default=1800, metavar="SECONDS", help="per-dispatch limit (default 1800)")
    p.add_argument("--budget-usd", type=float, default=5.0, metavar="USD",
                   help="per-dispatch spend cap passed to claude -p (default 5; 0 disables; Codex: timeout only)")
    p.add_argument("--force-unlock", action="store_true", help="replace a lock left by another live run")
    p.add_argument("--dry-run", action="store_true", help="print the dispatches without running any harness")
    p.add_argument("--driver-cmd", help=argparse.SUPPRESS)  # test hook: binary standing in for the harness
    return p


def main(argv: list[str], repo: Path, core_root: Path, tasks_scripts: Path) -> int:
    args = build_parser().parse_args(argv)
    if not args.harness:
        args.harness = "claude" if shutil.which(args.driver_cmd or "claude") else "codex" if shutil.which("codex") else None
        if not args.harness:
            print("at: neither `claude` nor `codex` is on PATH", file=sys.stderr)
            return 2
    try:
        return Runner(args, repo, core_root, tasks_scripts).run()
    except RunError as exc:
        print(f"at task run: {exc}", file=sys.stderr)
        return 1
