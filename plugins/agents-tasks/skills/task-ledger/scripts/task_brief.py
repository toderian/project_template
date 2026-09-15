#!/usr/bin/env python3
"""Per-phase briefs and run state for `agents-core:execute-plan`.

Vendored under the `task-ledger` skill; invoked via `at task brief <TASK-ID> --phase N` and
`at task run-state init|check <TASK-ID>`. Python 3 stdlib only.

  brief      extract one phase of a task file into a self-contained brief for an implementer
             subagent: docs/tasks_manager/_runs/<TASK-ID>/phase-N/brief.md
  run-state  init  — write the resume map docs/tasks_manager/_runs/<TASK-ID>/state.md
             check — validate a state.md the orchestrator has been editing by hand

Phase N is the Nth `#### ` heading in the task file — the same counting rule `sync_todo_ledgers.py`
uses for the `Phase` ledger column, so `--phase 2` here is the `2` in the ledger's `1/2`.

Exit codes: 0 ok, 1 errors, 2 usage.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mdtables  # noqa: E402
from sync_todo_ledgers import Generator, read_lines  # noqa: E402

RUNS_DIR = Path("docs/tasks_manager/_runs")
BRIEF_SECTIONS = ("brief", "specification", "design", "acceptance criteria", "related tests")
META_ROWS = ("Task ID", "Type", "Area", "Repos", "Autonomy", "Spec refs")
RUNTIMES = ("claude", "codex", "inline")
STATUSES = ("pending", "implementing", "reviewing", "fixing", "committed", "blocked", "parked")
VERDICTS = ("—", "n/a", "PASS", "FAIL")
LEDGER_PREFIXES = ("Phase ", "Ruling:", "Interface:", "Note:")
STATE_KEYS = ("task", "task_file", "runtime", "base_rev", "branch", "work_mode", "autonomy",
              "current_phase", "updated")
STATE_MAX_LINES = 60
TABLE_HEADER = "| Phase | Status | Attempt | Spec | Quality | Security | Open | Commit | Agent |"
TABLE_SEP = "|---|---|---|---|---|---|---|---|---|"


@dataclass
class Phase:
    number: int
    heading: str          # text after "#### "
    body: list[str] = field(default_factory=list)


@dataclass
class Task:
    taskid: str
    path: Path
    title: str = ""
    meta: dict[str, str] = field(default_factory=dict)          # original key -> value
    sections: dict[str, list[str]] = field(default_factory=dict)  # lowercased "### x" -> body
    phases: list[Phase] = field(default_factory=list)


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def strip_trailing_blank(lines: list[str]) -> list[str]:
    out = list(lines)
    while out and not out[-1].strip():
        out.pop()
    while out and not out[0].strip():
        out.pop(0)
    return out


def parse_task(taskid: str, path: Path) -> Task:
    task = Task(taskid=taskid, path=path)
    section: str | None = None
    phase: Phase | None = None
    for line in read_lines(path):
        if line.startswith("|") and task.title == "":
            cells = mdtables.split_table_row(line)
            if len(cells) >= 2 and cells[0] and not mdtables.is_separator(cells):
                if cells[0].lower() != "field":
                    task.meta[cells[0]] = cells[1]
            continue
        if line.startswith("## ") and task.title == "":
            task.title = line[3:].strip()
            continue
        if line.startswith("#### "):
            phase = Phase(number=len(task.phases) + 1, heading=line[5:].strip())
            task.phases.append(phase)
            section = None
            continue
        if line.startswith("### "):
            phase = None
            name = line[4:].strip().lower()
            section = name if name in BRIEF_SECTIONS else None
            if section is not None:
                task.sections.setdefault(section, [])
            continue
        if line.startswith("## ") or line.strip() == "---":
            phase = None
            section = None
            continue
        if phase is not None:
            phase.body.append(line)
        elif section is not None:
            task.sections[section].append(line)
    for p in task.phases:
        p.body = strip_trailing_blank(p.body)
    for name in list(task.sections):
        task.sections[name] = strip_trailing_blank(task.sections[name])
    return task


def phase_title(phase: Phase) -> str:
    return re.sub(r"^Phase\s+\d+\s*:\s*", "", phase.heading, flags=re.IGNORECASE)


def render_brief(task: Task, n: int, root: Path) -> str:
    phase = task.phases[n - 1]
    task_rel = task.path.relative_to(root).as_posix()
    report_rel = (RUNS_DIR / task.taskid / f"phase-{n}" / "report.md").as_posix()
    out: list[str] = [
        f"# Brief — {task.taskid} · phase {n} of {len(task.phases)}: {phase_title(phase)}",
        "",
        f"Task file: `{task_rel}` (do not read it; this brief is your full context)",
        f"Report path: `{report_rel}`",
        f"Generated: {now_iso()} by `at task brief {task.taskid} --phase {n}`",
        "",
        "## Task",
        "",
        f"**{task.title}**",
    ]
    if task.sections.get("brief"):
        out += [""] + task.sections["brief"]
    rows = [(k, task.meta[k]) for k in META_ROWS if task.meta.get(k)]
    if rows:
        out += ["", "## Metadata", "", "| Field | Value |", "|---|---|"]
        out += [f"| {k} | {v} |" for k, v in rows]
    out += ["", "## This phase", "", f"#### {phase.heading}"]
    if phase.body:
        out += [""] + phase.body
    for name, heading in (("acceptance criteria", "Acceptance criteria"),
                          ("related tests", "Related tests"),
                          ("specification", "Specification"),
                          ("design", "Design")):
        body = task.sections.get(name)
        if body:
            out += ["", f"## {heading}", ""] + body
    refs = task.meta.get("Spec refs", "")
    if refs and refs.upper() != "N/A":
        out += ["", "## Spec refs", ""]
        for ref in (r.strip() for r in refs.split(",")):
            if not ref:
                continue
            out.append("- the Specification / Design sections above" if ref == "self" else f"- `{ref}`")
    out += [
        "",
        "## Orchestrator notes",
        "",
        "<!-- appended by agents-core:execute-plan: work mode, autonomy, scope fence, Interface:/Ruling: lines -->",
        "",
        "## Report contract",
        "",
        "- Write the full report to the report path above: the `## Status:` block, files changed, and",
        "  every check you ran with its result.",
        "- Reply in at most 15 lines, ending with the `## Status:` block.",
        "- Do not commit or stage. Do not spawn subagents. Do not read AGENTS.md or CLAUDE.md.",
        "- Do not edit outside the scope fence in the orchestrator notes; report NEEDS_CONTEXT instead.",
        "",
    ]
    return "\n".join(out)


def render_state(task: Task, root: Path, args: argparse.Namespace) -> str:
    task_rel = task.path.relative_to(root).as_posix()
    out = [
        "---",
        f"task: {task.taskid}",
        f"task_file: {task_rel}",
        f"runtime: {args.runtime}",
        f"base_rev: {args.base}",
        f"branch: {args.branch}",
        f"work_mode: {args.work_mode}",
        f"autonomy: {args.autonomy}",
        "current_phase: 1",
        f"updated: {now_iso()}",
        "---",
        f"# Run ledger — {task.taskid}",
        "",
        TABLE_HEADER,
        TABLE_SEP,
    ]
    out += [f"| {p.number} | pending | 0 | — | — | — | 0 | — | — |" for p in task.phases]
    out += ["", f"Note: initialised by `at task run-state init {task.taskid}`; edited by the orchestrator only.", ""]
    return "\n".join(out)


def git_has_commit(root: Path, sha: str) -> bool | None:
    """True/False when root is a git repo, None when it is not."""
    if not (root / ".git").exists():
        return None
    rc = subprocess.run(["git", "-C", str(root), "cat-file", "-e", f"{sha}^{{commit}}"],
                        capture_output=True, check=False).returncode
    return rc == 0


def check_state(path: Path, task: Task, root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    lines = read_lines(path)
    rel = path.relative_to(root).as_posix()
    if len(lines) > STATE_MAX_LINES:
        warnings.append(f"{rel} has {len(lines)} lines (keep it under {STATE_MAX_LINES}: it is read every phase)")
    if not lines or lines[0].strip() != "---":
        errors.append(f"{rel}: missing frontmatter (first line must be ---)")
        return errors, warnings
    try:
        end = lines.index("---", 1)
    except ValueError:
        errors.append(f"{rel}: frontmatter is not closed with ---")
        return errors, warnings
    front: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" not in line:
            errors.append(f"{rel}: bad frontmatter line {line!r}")
            continue
        key, _, value = line.partition(":")
        front[key.strip()] = value.strip()
    for key in STATE_KEYS:
        if key not in front:
            errors.append(f"{rel}: frontmatter is missing `{key}`")
    if front.get("task") not in (None, task.taskid):
        errors.append(f"{rel}: frontmatter task {front['task']!r} does not match {task.taskid}")
    if front.get("runtime") not in (None, *RUNTIMES):
        errors.append(f"{rel}: runtime must be one of {', '.join(RUNTIMES)}")
    current = front.get("current_phase", "")
    if current and not (current.isdigit() and 1 <= int(current) <= max(len(task.phases), 1)):
        errors.append(f"{rel}: current_phase {current!r} is outside 1..{len(task.phases)}")

    rows: list[list[str]] = []
    ledger: list[str] = []
    for line in lines[end + 1:]:
        if line.startswith("|"):
            cells = mdtables.split_table_row(line)
            if cells and cells[0].isdigit():
                rows.append(cells)
        elif line.strip() and not line.startswith("#"):
            ledger.append(line)
    if len(rows) != len(task.phases):
        errors.append(f"{rel}: {len(rows)} phase row(s) but the task has {len(task.phases)} phase(s)")
    for cells in rows:
        n = cells[0]
        if len(cells) < 9:
            errors.append(f"{rel}: phase {n} row has {len(cells)} cells, expected 9")
            continue
        status, spec, quality, security, commit = cells[1], cells[3], cells[4], cells[5], cells[7]
        if status not in STATUSES:
            errors.append(f"{rel}: phase {n} status {status!r} is not one of {', '.join(STATUSES)}")
        for label, cell in (("Spec", spec), ("Quality", quality), ("Security", security)):
            if cell not in VERDICTS:
                errors.append(f"{rel}: phase {n} {label} cell {cell!r} must be one of {', '.join(VERDICTS)}")
        if commit not in ("—", "-", ""):
            found = git_has_commit(root, commit)
            if found is None:
                warnings.append(f"{rel}: phase {n} commit {commit} not verified ({root} is not a git repository)")
            elif not found:
                errors.append(f"{rel}: phase {n} commit {commit} does not exist in this repository")
        if status == "committed" and commit in ("—", "-", ""):
            errors.append(f"{rel}: phase {n} is committed but has no commit SHA")
    for line in ledger:
        if not line.startswith(LEDGER_PREFIXES) or (line.startswith("Phase ") and not re.match(r"^Phase \d+:", line)):
            errors.append(f"{rel}: ledger line must start with `Phase N:`, `Ruling:`, `Interface:` or `Note:`: {line!r}")
    return errors, warnings


# ---- commands ----------------------------------------------------------------

def load_task(root: Path, taskid: str) -> Task:
    path = Generator(root, check_mode=False).find_task_path(taskid)
    if path is None:
        raise SystemExit(err(f"no task file found for '{taskid}' under docs/tasks_manager/_todos"))
    return parse_task(taskid, path.resolve())


def err(message: str, code: int = 1) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return code


def write_out(path: Path | None, content: str, force: bool, label: str) -> int:
    if path is None:
        sys.stdout.write(content)
        return 0
    if path.exists() and not force:
        return err(f"{label} already exists: {path} (pass --force to overwrite)")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(path)
    return 0


def cmd_brief(args: argparse.Namespace, root: Path) -> int:
    task = load_task(root, args.task_id)
    if not task.phases:
        return err(f"{task.path.name} has no `#### Phase` headings")
    if not 1 <= args.phase <= len(task.phases):
        return err(f"--phase {args.phase} is outside 1..{len(task.phases)} for {task.taskid}", code=2)
    out = None if args.out == "-" else (Path(args.out) if args.out else root / RUNS_DIR / task.taskid / f"phase-{args.phase}" / "brief.md")
    return write_out(out, render_brief(task, args.phase, root), args.force, "brief")


def cmd_run_state(args: argparse.Namespace, root: Path) -> int:
    task = load_task(root, args.task_id)
    state = root / RUNS_DIR / task.taskid / "state.md"
    if args.action == "init":
        if not task.phases:
            return err(f"{task.path.name} has no `#### Phase` headings")
        return write_out(state, render_state(task, root, args), args.force, "run state")
    if not state.is_file():
        return err(f"no run state at {state.relative_to(root).as_posix()} (run: at task run-state init {task.taskid})")
    errors, warnings = check_state(state, task, root)
    for w in warnings:
        print(f"WARNING: {w}", file=sys.stderr)
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)
    if errors:
        print(f"Run state validation failed: {len(errors)} issue(s).", file=sys.stderr)
        return 1
    print(f"OK run state valid ({len(task.phases)} phase(s))")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="at task", description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", default=".", help="repository root (default: current directory)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_brief = sub.add_parser("brief", help="write phase N of a task as a self-contained implementer brief")
    p_brief.add_argument("task_id")
    p_brief.add_argument("--phase", type=int, required=True)
    p_brief.add_argument("--out", help="output path, or - for stdout (default: _runs/<ID>/phase-N/brief.md)")
    p_brief.add_argument("--force", action="store_true", help="overwrite an existing brief")
    p_brief.set_defaults(func=cmd_brief)

    p_state = sub.add_parser("run-state", help="init | check the _runs/<ID>/state.md resume map")
    p_state.add_argument("action", choices=("init", "check"))
    p_state.add_argument("task_id")
    p_state.add_argument("--base", default="unknown", help="base git revision (init)")
    p_state.add_argument("--branch", default="unknown", help="branch name (init)")
    p_state.add_argument("--work-mode", default="default-branch", help="resolved work mode (init)")
    p_state.add_argument("--autonomy", default="L1", help="resolved autonomy level (init)")
    p_state.add_argument("--runtime", choices=RUNTIMES, default="inline", help="dispatch runtime (init)")
    p_state.add_argument("--force", action="store_true", help="overwrite an existing state.md (init)")
    p_state.set_defaults(func=cmd_run_state)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    if not (root / "docs" / "tasks_manager").is_dir():
        return err(f"{root} has no docs/tasks_manager (run: at init --with-tasks)", code=2)
    try:
        return args.func(args, root)
    except SystemExit as exc:  # raised by load_task with the exit code
        return int(exc.code or 1)


if __name__ == "__main__":
    sys.exit(main())
