"""`at task report <TASK-ID>... [--since REV]` -- the morning report of a run, one file per task.

Writes docs/tasks_manager/_reports/<date>-<TASK-ID>.md, a function of the run's ledger, not of HEAD:
"Commits" lists the commits recorded in the phase rows of state.md, in row order; `--since REV` adds
a section "Commits since REV" (`REV..HEAD`, first-parent, leaving out commits that touch only
`_reports/`), which depends on HEAD by request. <date> is the commit date of `base_rev` (for an archived
task without a run directory: the `Base: <rev>` line of its completion summary, else `--since`; with
neither, exit 2). No clock, no absolute paths, git config neutralised: a rerun is byte-identical.
Exit 0 on success, 2 on usage, input or filesystem errors. Imported by lib/at.py.

"Needs you" is what is open now: rows that are `parked` or `blocked`, each with its ledger lines
(`Phase N: ...`, `Note: parked phase N: ...`), and `Note: parked: <question>` lines while some row is
not `committed`. Once every row is committed, or the task is archived, parked notes are history
("Parked during the run"). `Decision:`, `Ruling:` and parked notes are copied verbatim.
"""
from __future__ import annotations

import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

from task_run import State

TASKS = "docs/tasks_manager"
REPORTS = f"{TASKS}/_reports"
ID_RE = re.compile(r"[A-Z][A-Z0-9]*-[0-9]+")
HEX_RE = re.compile(r"[0-9a-f]{4,40}")
KEPT = re.compile(r"(Decision|Ruling):|Note: parked")
USAGE = "usage: at task report <TASK-ID>... [--since <rev>]"
# user config must not change the output
GIT = ["git", "-c", "core.quotePath=false", "-c", "i18n.logOutputEncoding=UTF-8", "-c", "log.showSignature=false"]


class ReportError(Exception):
    pass


def git(repo: Path, *args: str) -> str:
    p = subprocess.run([*GIT, *args], cwd=repo, capture_output=True, check=False)
    if p.returncode:
        raise ReportError(f"git {args[0]} failed: {p.stderr.decode('utf-8', 'replace').strip() or 'exit ' + str(p.returncode)}")
    return p.stdout.decode("utf-8", "replace")


def resolve(repo: Path, rev: str, what: str) -> str:
    if not rev or rev.startswith("-"):
        raise ReportError(f"{what}: not a revision: {rev!r}")
    try:
        return git(repo, "rev-parse", "--verify", "--quiet", "--end-of-options", f"{rev}^{{commit}}").strip()
    except ReportError:
        raise ReportError(f"{what}: unknown revision {rev!r}") from None


def find_task(repo: Path, taskid: str) -> tuple[Path | None, bool, bool]:
    """The task file (`_todos` first), whether it is archived, whether both places hold it."""
    hits = [sorted((repo / TASKS / sub).glob(f"{taskid}[-_]*.md")) for sub in ("_todos", "_todos_archived")]
    live, old = (h[0] if h else None for h in hits)
    return live or old, live is None and old is not None, live is not None and old is not None


def clean(raw: str) -> str:
    return re.sub(r"^\s*[-*]\s+", "", raw).rstrip()


def commit_of(row: list[str]) -> str:
    return row[7] if len(row) > 7 else ""


def build(repo: Path, taskid: str, since_arg: str | None) -> tuple[str, str]:
    """Return (file name, content) for one task."""
    path, archived, both = find_task(repo, taskid)
    sp = repo / TASKS / "_runs" / taskid / "state.md"
    if path is None and not sp.is_file():
        raise ReportError(f"{taskid}: no task file and no run state")
    if not sp.is_file() and not archived:
        raise ReportError(f"{taskid}: no run state and the task is not archived")
    text = path.read_text(encoding="utf-8", errors="replace") if path else ""
    m = re.search(r"^## Completion summary[ \t]*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    summary = [clean(x) for x in m.group(1).split("\n")] if m else []
    st = None
    if sp.is_file():
        try:
            st = State(sp)
        except (ValueError, IndexError) as exc:
            raise ReportError(f"{taskid}: unreadable run state ({exc})") from None
    rows = st.rows if st else []
    if any(len(r) < 8 for r in rows):
        raise ReportError(f"{taskid}: unreadable run state (a phase row has fewer than 8 cells)")
    ledger = [clean(x) for x in st.ledger] if st else []
    base_arg = st.front.get("base_rev", "") if st else next((x[5:].strip() for x in summary if x.startswith("Base:")), "")
    anchor = resolve(repo, base_arg, f"{taskid} base_rev") if st or base_arg else ""
    since = resolve(repo, since_arg, "--since") if since_arg else ""
    if not (anchor or since):
        raise ReportError(f"{taskid}: no run state to date the report; add a `Base: <rev>` line to the "
                          "task's completion summary or pass --since <rev>")
    date = git(repo, "show", "-s", "--format=%cs", anchor or since).strip()

    status = {r[0]: r[1] for r in rows}
    open_ = not archived and any(s != "committed" for s in status.values())
    needs, hist, notes, explained = [], [], [], set()
    for r in rows:
        if r[1] in ("parked", "blocked"):
            needs.append(f"- Phase {r[0]} is {r[1]}")
            why = [x for x in ledger if re.match(rf"(Phase {r[0]}:|Note: parked phase {r[0]}\b)", x)]
            needs += [f"  - {x}" for x in why]
            explained.update(why)
    for x in dict.fromkeys(x for x in ledger + summary if KEPT.match(x)):
        if x.startswith("Note: parked"):
            pm = re.match(r"Note: parked phase (\d+)\b", x)
            live = open_ and not (pm and status.get(pm.group(1)) == "committed")
            if x not in explained:
                (needs if live else hist).append(f"- {x}")
        else:
            notes.append(f"- {x}")

    out = [f"# Morning report: {taskid}", "", "## Needs you", ""] + (needs or ["Nothing open."])
    sm = re.search(r"^\|\s*Status\s*\|\s*([^|]*?)\s*\|", text, re.M)
    out += ["", "## Task", "", f"Status: {sm.group(1) if sm else 'no task file' if path is None else 'unknown'}"]
    out += [f"Source: {'run state' if rows else 'completion summary of the archived task'}"]
    if both:
        out += ["Also present in _todos_archived; reported from _todos."]
    if rows:
        out += ["", "| Phase | Status | Spec | Quality | Security | Open | Commit |", "|---|---|---|---|---|---|---|"]
        out += ["| " + " | ".join(r[:2] + r[3:8]) + " |" for r in rows]
    out += ["", "## Decisions, rulings and notes", ""] + (notes or ["None."])
    out += ["", "## Parked during the run", ""] + (hist or ["None."])
    out += ["", "## Commits", ""]
    lines, missing = [], False
    for r in rows:
        sha = commit_of(r).strip("`").lower()
        if HEX_RE.fullmatch(sha):
            try:
                lines.append(f"- {sha} {git(repo, 'show', '-s', '--format=%s', '--end-of-options', sha + '^{commit}').strip()}")
            except ReportError:
                lines.append(f"- {sha}")
                missing = True
    out += lines or ["None recorded."]
    if missing:
        out += ["", "Some commits have no subject: they are not in this repository (`code_repo` or rewritten history)."]
    if since:
        log = git(repo, "log", "--first-parent", "--format=%H%x09%s", f"{since}..HEAD", "--", ".", f":(exclude){REPORTS}")
        out += ["", f"## Commits since {since_arg} (depends on HEAD)", ""]
        out += [f"- {h[:12]} {s}" for h, _, s in (ln.partition("\t") for ln in log.splitlines())] or ["None."]
    return f"{date}-{taskid}.md", "\n".join(out) + "\n"


def target_dir(repo: Path, name: str) -> Path:
    """The report directory, refusing symlinks on the way and a target that is not a regular file."""
    d = repo
    for part in REPORTS.split("/"):
        d = d / part
        if d.is_symlink():
            raise ReportError(f"{d.relative_to(repo)} is a symlink")
    target = d / name
    if target.is_symlink() or (target.exists() and not target.is_file()):
        raise ReportError(f"{REPORTS}/{name} is not a regular file")
    return d


def write(repo: Path, name: str, content: str) -> None:
    d = target_dir(repo, name)
    d.mkdir(parents=True, exist_ok=True)
    target = d / name
    if target.exists():
        mode = stat.S_IMODE(target.stat().st_mode)
    else:
        mask = os.umask(0)
        os.umask(mask)
        mode = 0o666 & ~mask
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".report-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        os.chmod(tmp, mode)
        os.replace(tmp, target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def main(argv: list[str], repo: Path) -> int:
    ids, since, i = [], None, 0
    while i < len(argv):
        if argv[i] == "--since" and i + 1 < len(argv):
            since, i = argv[i + 1], i + 2
        elif argv[i].startswith("-"):
            print(USAGE, file=sys.stderr)
            return 2
        else:
            ids.append(argv[i])
            i += 1
    bad = [t for t in ids if not ID_RE.fullmatch(t)]
    if not ids or bad:
        print(f"ERROR: bad task id {bad[0]!r}\n{USAGE}" if bad else USAGE, file=sys.stderr)
        return 2
    try:
        files = [build(repo, t, since) for t in dict.fromkeys(ids)]
        for name, _ in files:
            target_dir(repo, name)
        for name, content in files:
            write(repo, name, content)
            print(f"{REPORTS}/{name}")
    except (ReportError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0
