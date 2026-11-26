#!/usr/bin/env python3
"""`at sup worktree|land|ready`: one hub worktree per task, landing it, and the readiness check.

The hub is the git repository of the current directory (`--repo` overrides). Exit codes: 0 ok,
2 usage, 3 refused (one line on stderr saying why). Standalone: `python3 sup.py worktree ...`.

`land` writes the archive ref after the squash commit (a failed landing leaves no ref), and a rerun
after a failure past the commit skips the squash and only cleans up.
Not built here: the permission preflight of `ready` (plan D9).
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

LIB = Path(__file__).resolve().parent
PARTS = ("sup_digest", "sup_workers", "sup_ask", "sup_watch", "sup_tick")
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))
TODOS = "docs/tasks_manager/_todos"
ARCHIVED = "docs/tasks_manager/_todos_archived"
ACTIVE = "docs/tasks_manager/_active.md"
# Files the ledger sync rewrites whole: a conflict in them takes our side and the sync rebuilds them.
# Area pages and the area overview only carry generated blocks inside hand-written text, so a
# conflict there is a hand-written conflict and `land` stops with the file named.
GENERATED = (ACTIVE, "docs/tasks_manager/_done.md")
CACHES = {"__pycache__", "node_modules", ".pytest_cache", ".venv"}
CONVENTIONAL = re.compile(r"^(feat|fix|docs|chore|refactor|test|perf|build|ci|style|revert)(\([^)]*\))?!?:\s*")
ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


class Refuse(Exception):
    pass


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)


def git_out(cwd: Path, *args: str) -> str:
    p = git(cwd, *args)
    if p.returncode:
        raise Refuse(f"git {args[0]} failed: {(p.stderr.strip().splitlines() or ['?'])[-1]}")
    return p.stdout.strip()


def git_z(cwd: Path, *args: str) -> list[str]:
    """A NUL-separated git file list (`-z`): paths with non-ASCII or odd characters stay exact."""
    return [x for x in git_out(cwd, args[0], "-z", *args[1:]).split("\0") if x]


def main_worktree(repo: Path) -> Path:
    if git(repo, "rev-parse", "--git-dir").returncode:
        raise Refuse(f"{repo} is not a git repository")
    first = git_out(repo, "worktree", "list", "--porcelain").splitlines()[0]
    return Path(first.removeprefix("worktree "))


def worktree_of(main: Path, branch: str) -> Path | None:
    path = None
    for line in git_out(main, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            path = Path(line[9:])
        elif line == f"branch refs/heads/{branch}":
            return path
    return None


def default_branch(main: Path) -> str:
    p = git(main, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if p.returncode == 0 and p.stdout.strip():
        return p.stdout.strip().removeprefix("origin/")
    for name in ("main", "master"):  # the checkout may be on another branch; prefer the usual names
        if git(main, "rev-parse", "--verify", "-q", f"refs/heads/{name}").returncode == 0:
            return name
    return git_out(main, "symbolic-ref", "--short", "HEAD")


def is_dirty(path: Path) -> bool:
    return bool(git_out(path, "status", "--porcelain"))


def _with_lease(name: str, fn, tid: str):
    import lease  # lib/lease.py
    if lease.take(name, ttl=10, task=tid, reason="sup land", own_pid=True):
        raise Refuse(f"lease {name} is held")
    try:
        return fn()
    finally:
        lease.release(name, own_pid=True)


def tasks_root() -> Path:
    """The agents-tasks plugin root, found the way `at` finds it."""
    import at  # lib/at.py
    found = at.find_tasks_root()
    if found is None:
        raise Refuse("agents-tasks is not installed (set AT_TASKS_ROOT)")
    return found


# ---- worktree ------------------------------------------------------------

def cmd_worktree(args) -> int:
    main = main_worktree(args.repo)
    branch = f"task/{args.task_id}"
    path = main.parent / f"{main.name}-{args.task_id.lower()}"
    if git(main, "rev-parse", "--verify", "-q", f"refs/heads/{branch}").returncode == 0:
        raise Refuse(f"branch {branch} exists" + (f" at {worktree_of(main, branch)}" if worktree_of(main, branch) else ""))
    if path.exists():
        raise Refuse(f"directory exists: {path}")
    # Landing is local, so the base is the local default branch: a landed blocker is on it.
    base = args.base or default_branch(main)
    if git(main, "rev-parse", "--verify", "-q", f"{base}^{{commit}}").returncode:
        raise Refuse(f"base {base} is not a commit")
    git_out(main, "worktree", "add", "-b", branch, str(path), base)
    print(path)
    return 0


# ---- land ----------------------------------------------------------------

def archived_file(main: Path, tid: str, branch: str) -> str:
    """The task's file under _todos_archived on `branch` (the rule of complete-task and run-open.sh), or ''."""
    names = git_z(main, "ls-tree", "-r", "--name-only", f"refs/heads/{branch}", "--", f"{TODOS}/", f"{ARCHIVED}/")
    if any(n.startswith(f"{TODOS}/{tid}-") for n in names):
        return ""
    return next((n for n in names if n.startswith(f"{ARCHIVED}/{tid}-") and n.endswith(".md")), "")


def kept_ignored(wt: Path) -> list[str]:
    out = git_z(wt, "ls-files", "--others", "--ignored", "--exclude-standard")
    return [f for f in out if not (set(f.split("/")) & CACHES or f.endswith(".pyc"))]


def ledger_script(main: Path) -> Path | None:
    """The sync script when the repo has a ledger; refuses when it has one and the tooling is missing."""
    if not (main / ACTIVE).is_file():
        return None
    script = tasks_root() / "skills" / "task-ledger" / "scripts" / "sync_todo_ledgers.py"
    if not script.is_file():
        raise Refuse(f"{main} has a task ledger but {script} is missing")
    return script


def ledger_sync(main: Path) -> None:
    script = ledger_script(main)
    for extra in ([], ["--check"]) if script else ():
        p = subprocess.run([sys.executable, str(script), "--root", str(main), *extra], capture_output=True, text=True)
        if p.returncode:
            last = ((p.stderr + p.stdout).strip().splitlines() or ["no output"])[-1]
            raise Refuse(f"ledger {'check' if extra else 'sync'} failed: {last}")


def squash_and_commit(main: Path, tid: str, branch: str, task_file: str) -> None:
    try:
        p = git(main, "merge", "--squash", f"refs/heads/{branch}")
        if p.returncode:
            conflicted = git_z(main, "diff", "--name-only", "--diff-filter=U")
            hand = [f for f in conflicted if f not in GENERATED]
            if not conflicted or hand:
                raise Refuse(f"conflict landing {tid}; resolve in the task worktree: " + (", ".join(hand) or p.stderr.strip()))
            ledger_script(main)
            for f in conflicted:
                git_out(main, "checkout", "--ours", "--", f)
                git_out(main, "add", "--", f)
        ledger_sync(main)
        git_out(main, "add", "-A")
        if git(main, "diff", "--cached", "--quiet").returncode == 0:
            raise Refuse(f"nothing to land: {branch} adds nothing to the default branch")
        heading = next((ln[3:].strip() for ln in (main / task_file).read_text().splitlines() if ln.startswith("## ")), tid)
        m = CONVENTIONAL.match(heading)
        kind, title = (m.group(1), heading[m.end():]) if m else ("feat", heading)
        git_out(main, "commit", "-q", "-m", f"{kind}: {tid} {title}\n\nTask: {tid}\nArchive: refs/archive/task/{tid}\n")
    except BaseException:
        git(main, "reset", "--hard", "HEAD")  # the landing checkout was clean before the merge
        raise


def state_dir() -> Path:
    base = os.environ.get("AGENTS_SUP_DIR") or str(
        Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "agents-template" / "sup")
    return Path(base) / "_host"


def cmd_land(args) -> int:
    main, tid = main_worktree(args.repo), args.task_id
    branch, ref = f"task/{tid}", f"refs/archive/task/{tid}"
    if git(main, "rev-parse", "--verify", "-q", f"refs/heads/{branch}").returncode:
        raise Refuse(f"no branch {branch}")
    tip = git_out(main, "rev-parse", f"refs/heads/{branch}")
    task_file = archived_file(main, tid, branch)
    if not task_file:
        raise Refuse(f"task {tid} is not closed out on {branch}: no file in {ARCHIVED}/")
    wt = worktree_of(main, branch)
    if wt and is_dirty(wt):
        raise Refuse(f"task worktree {wt} has uncommitted changes")
    if is_dirty(main):
        raise Refuse(f"landing checkout {main} has uncommitted changes")
    default = args.into or default_branch(main)
    head = git(main, "symbolic-ref", "--short", "-q", "HEAD")
    if head.returncode:
        raise Refuse(f"landing checkout {main} is on a detached HEAD, not {default}")
    if head.stdout.strip() != default:
        raise Refuse(f"landing checkout {main} is on {head.stdout.strip()}, not {default}")
    old = git(main, "rev-parse", "--verify", "-q", ref).stdout.strip()
    if old and old != tip:
        raise Refuse(f"{ref} already exists at another commit")
    done = bool(git_out(main, "log", "-1", "--format=%H", "--fixed-strings", f"--grep=Archive: {ref}", default))
    ledger_script(main)
    steps = [] if done else [f"squash-merge {branch} into {default} and commit once (hub-ledger lease, ledger sync and check)"]
    steps += [f"git update-ref {ref} {tip[:12]}"] if old != tip else []
    if wt:
        steps.append(f"move ignored files other than caches to {state_dir() / 'kept' / tid}, then remove worktree {wt}")
    steps.append(f"delete branch {branch}")
    if args.dry_run:
        print("\n".join("dry-run: " + s for s in steps))
        return 0
    if not done:
        _with_lease("hub-ledger", lambda: squash_and_commit(main, tid, branch, task_file), tid)
    if old != tip:
        git_out(main, "update-ref", ref, tip)
    if wt and wt.exists():
        if is_dirty(wt):  # recomputed now: the worker may have written since the first check
            raise Refuse(f"task worktree {wt} changed during landing; the commit is made, rerun `sup land {tid}`")
        keep, kept = kept_ignored(wt), state_dir() / "kept" / tid
        for f in keep:  # `git worktree remove` deletes ignored files silently
            dest = kept / f
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(wt / f), str(dest))
        if keep:
            print(f"kept ignored files: {kept}")
        git_out(main, "worktree", "remove", str(wt))
    git_out(main, "branch", "-D", branch)
    print(f"landed {tid}: {git_out(main, 'rev-parse', '--short', default)}")
    return 0


# ---- ready ---------------------------------------------------------------

PHASE_RE = re.compile(r"Phase\s+\d+\s*(:|$)", re.I)
DURATION_RE = re.compile(r"\d+(\.\d+)?\s*(s|sec|secs|m|min|mins|minutes?|h|hr|hrs|hours?)\b", re.I)


def unattended(path: Path, depth: int = 0) -> list[str]:
    """The lines of the task's `### Unattended run` section; a child task inherits its parent's (`Parent` row)."""
    text = path.read_text().splitlines()
    for i, ln in enumerate(text):
        if re.match(r"###\s+Unattended run\s*$", ln):
            sec = text[i + 1:]
            return next((sec[:j] for j, nxt in enumerate(sec) if nxt.startswith("#")), sec)
    parent = next((m.group(1) for ln in text if (m := re.match(r"\|\s*Parent\s*\|\s*(\S+)\s*\|", ln))), "")
    if depth < 3 and ID_RE.fullmatch(parent):
        for d in (path.parent, path.parent.parent / "_todos_archived"):
            for f in sorted(d.glob(f"{parent}-*.md")):
                return unattended(f, depth + 1)
    return []


def readiness(tid: str, path: Path) -> list[str]:
    scripts = tasks_root() / "skills" / "task-ledger" / "scripts"
    sys.path.insert(0, str(scripts))
    import task_brief  # parse_task: metadata, phases, acceptance criteria
    try:
        from task_lanes import fence  # the `Files:` rule of the lane planner
    except ImportError:
        def fence(task, n):  # fallback: a line starting `Files:` with something after it
            return re.search(r"^\s*Files:\s*\S", "\n".join(task.phases[n - 1].body), re.M)
    task = task_brief.parse_task(tid, path)
    missing: list[str] = []
    phases = [(n, p) for n, p in enumerate(task.phases, 1) if p.heading.lower().startswith("phase")]
    for _, p in phases:
        if not PHASE_RE.match(p.heading):
            missing.append(f"phase heading is not `Phase <integer>`: {p.heading}")
    if not any(PHASE_RE.match(p.heading) for _, p in phases):
        missing.append("no `#### Phase <integer>` heading")
    related = [ln.strip(" -*`") for ln in task.sections.get("related tests", []) if ln.strip()]
    related_ok = bool(related) and "".join(related).upper() != "N/A"
    for n, p in phases:
        if not fence(task, n):
            missing.append(f"{p.heading}: no `Files:` line")
        if not related_ok and not re.search(r"^\s*(?:[-*]\s*)?\**checks?\**\s*:\s*\S", "\n".join(p.body), re.I | re.M):
            missing.append(f"{p.heading}: names no check (`Checks:` line, or a `### Related tests` section)")
    if not any(re.match(r"\s*[-*] \[[ xX]\]", ln) for ln in task.sections.get("acceptance criteria", [])):
        missing.append("acceptance criteria: no checkbox")
    sec = unattended(path)
    if not sec:
        missing.append("no `### Unattended run` section (own or parent's)")
    else:
        for key in ("Authorised", "Owner only", "Defaults"):
            if not any(re.match(rf"{key}:\s*\S", ln) for ln in sec):
                missing.append(f"Unattended run: no `{key}:` line")
    res = task.meta.get("Resources") or next((m.group(1) for ln in path.read_text().splitlines()
                                              if (m := re.match(r"\s*(?:[-*]\s*)?Resources:\s*(\S.*)", ln))), "")
    if not res:
        missing.append("no `Resources:` line (write `Resources: none` when there are none)")
    elif res.strip().lower() != "none":
        for entry in (e.strip() for e in re.split(r"[,;]", res) if e.strip()):
            if not DURATION_RE.search(entry):
                missing.append(f"Resources: `{entry}` has no duration (write e.g. `lab 20m`)")
    return missing


def cmd_ready(args) -> int:
    top = Path(git_out(args.repo, "rev-parse", "--show-toplevel"))
    files = sorted((top / TODOS).glob(f"{args.task_id}-*.md"))
    if not files:
        raise Refuse(f"no task file {TODOS}/{args.task_id}-*.md")
    missing = readiness(args.task_id, files[0])
    if missing:
        print("\n".join(missing))
        return 3
    print("ready")
    return 0


# ---- wiring --------------------------------------------------------------

def _task_id(value: str) -> str:
    if not ID_RE.fullmatch(value) or ".." in value:
        raise argparse.ArgumentTypeError(f"bad task id: {value}")
    return value


def add_parser(sub) -> argparse.ArgumentParser:
    p = sub.add_parser("sup", help="supervisor tools: worktree | land | ready")
    p.add_argument("--repo", type=Path, default=Path.cwd(), help="hub repository (default: current directory)")
    ss = p.add_subparsers(dest="sup_cmd", required=True)

    def leaf(name, **kw):
        q = ss.add_parser(name, **kw)
        q.add_argument("--repo", type=Path, default=argparse.SUPPRESS, help="hub repository (also accepted before the subcommand)")
        return q
    w = leaf("worktree", help="create the task's hub worktree and branch")
    w.add_argument("task_id", type=_task_id)
    w.add_argument("--base", help="base ref (default: the local default branch)")
    w.set_defaults(sup_func=cmd_worktree)
    ln = leaf("land", help="squash-merge a closed-out task into the default branch")
    ln.add_argument("task_id", type=_task_id)
    ln.add_argument("--dry-run", action="store_true")
    ln.add_argument("--into", help="branch to land on (default: the default branch); the landing checkout must be on it")
    ln.set_defaults(sup_func=cmd_land)
    r = leaf("ready", help="check a task file is ready to dispatch (the permission preflight is not built)")
    r.add_argument("task_id", type=_task_id)
    r.set_defaults(sup_func=cmd_ready)
    p.set_defaults(func=run)
    for name in PARTS:  # each part adds its own subcommands; a part that is not installed is skipped
        try:
            __import__(name).register(ss)
        except ImportError:
            pass
    return p


def run(args) -> int:
    args.repo = Path(args.repo).resolve()
    try:
        return args.sup_func(args)
    except (Refuse, OSError) as e:
        print(f"sup: refused: {e}", file=sys.stderr)
        return 3


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sup")
    add_parser(parser.add_subparsers(dest="cmd", required=True))
    try:
        args = parser.parse_args(["sup", *(sys.argv[1:] if argv is None else argv)])
    except SystemExit as e:
        return 2 if e.code else 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
