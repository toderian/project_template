#!/usr/bin/env python3
"""`at sup worktree|land|ready`: one hub worktree per task, landing it, and the readiness check.

The hub is `--hub <path>` (alias `--repo`) when given, else config key `hub` of the profile (`--profile` or
AGENTS_SUPERVISOR; set by `at sup init`), else the git toplevel of the current directory. Exit codes: 0 ok,
2 usage, 3 refused (one line on stderr saying why). Standalone: `python3 sup.py worktree ...`.

`land` refuses before it touches the checkout when it cannot compute the merge result (`git merge-tree --write-tree`,
git 2.38+) unless the branch sits on the tip of the landing branch, and when an assume-unchanged hub file differs from the
index. It stages only the merge result, tracked changes and the generated ledger pages. It writes the archive ref after the
squash commit (a failed landing leaves no ref), and a rerun after a failure past the commit skips the squash and only
cleans up.
Not built here: the permission preflight of `ready` (plan D9).

`land` refuses under AGENTS_SUP_TASK (a worker session), emits `landed` when a profile is known (--profile or
AGENTS_SUPERVISOR), and refuses a branch whose diff against the landing branch touches `.claude/` or `.mcp.json`
unless `--allow-claude-files` is given, which only the owner may do (refused when CLAUDE_CODE_SESSION_ID is set).
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
PARTS = ("sup_digest", "sup_workers", "sup_ask", "sup_watch", "sup_tick", "sup_topics")
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


def _git_env() -> dict:
    """The environment without GIT_CONFIG_*: the launcher's core.hooksPath=/dev/null must not skip the hub's hooks."""
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_CONFIG_")}


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    # surrogateescape: a file name that is not UTF-8 round-trips to the file system instead of raising
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, errors="surrogateescape", env=_git_env())


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


def kept_ignored(wt: Path, linked=()) -> list[str]:
    """Ignored files `land` keeps. `linked` holds the real hub paths of the profile's `local` entries: a symbolic link
    still resolving to one of them is the worker's own link and goes with the worktree; anything else is kept."""
    out = git_z(wt, "ls-files", "--others", "--ignored", "--exclude-standard")
    return [f for f in out if f != ".local/repos.map" and not (set(f.split("/")) & CACHES or f.endswith(".pyc"))
            and not ((wt / f).is_symlink() and os.path.realpath(wt / f) in linked)]


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
        p = subprocess.run([sys.executable, str(script), "--root", str(main), *extra], capture_output=True, text=True, env=_git_env())
        if p.returncode:
            last = ((p.stderr + p.stdout).strip().splitlines() or ["no output"])[-1]
            raise Refuse(f"ledger {'check' if extra else 'sync'} failed: {last}")


def squash_and_commit(main: Path, tid: str, branch: str, task_file: str, body: str = "") -> None:
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
        # the checkout was clean, so an untracked file now is one the branch stopped ignoring: staging it would commit it
        loose = git_z(main, "ls-files", "--others", "--exclude-standard")
        if loose:
            raise Refuse(f"{branch} stops ignoring {loose[0]}, which the hub holds: landing would commit it; "
                         f"keep the ignore line on the branch, or move the hub's copy away")
        ledger_sync(main)
        # only what the landing owns: the merge result is staged already, the sync rewrote tracked files and may have
        # created ledger pages in its two directories. A file another writer drops elsewhere in the checkout now is neither committed
        # nor, on a failure, reset away.
        git_out(main, "add", "-u")
        if pages := git_z(main, "ls-files", "--others", "--exclude-standard", "--", "docs/areas", "docs/tasks_manager"):
            git_out(main, "add", "--", *pages)
        if git(main, "diff", "--cached", "--quiet").returncode == 0:
            raise Refuse(f"nothing to land: {branch} adds nothing to the default branch")
        heading = next((ln[3:].strip() for ln in (main / task_file).read_text().splitlines() if ln.startswith("## ")), tid)
        m = CONVENTIONAL.match(heading)
        kind, title = (m.group(1), heading[m.end():]) if m else ("feat", heading)
        git_out(main, "commit", "-q", "-m", f"{kind}: {tid} {title}\n\nTask: {tid}\nArchive: refs/archive/task/{tid}\n{body}")
    except BaseException:
        git(main, "reset", "--hard", "HEAD")  # the landing checkout was clean before the merge
        raise


def merge_result(main: Path, default: str, branch: str) -> tuple[str, list[str]] | None:
    """(tree, conflicted paths) of merging the branch into default, computed without touching the checkout.
    None when this git has no `merge-tree --write-tree` (before 2.38) or the command fails."""
    p = git(main, "merge-tree", "--write-tree", "--name-only", "--no-messages", "-z", default, f"refs/heads/{branch}")
    parts = p.stdout.split("\0")
    return (parts[0], [f for f in parts[1:] if f]) if p.returncode in (0, 1) and parts[0] else None


def state_dir() -> Path:
    base = os.environ.get("AGENTS_SUP_DIR") or str(
        Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "agents-template" / "sup")
    return Path(base) / "_host"


def _claude_file(path: str) -> bool:
    parts = path.split("/")
    return ".claude" in parts[:-1] or parts[-1] == ".mcp.json"


def _emit_landed(tid: str, profile: str | None) -> None:
    """The `landed` event of the profile (--profile, else AGENTS_SUPERVISOR); no profile, no event."""
    import sup_state
    name = sup_state.current_profile(profile)
    if name:
        with sup_state.locked(name):
            sup_state.emit(name, "landed", task=tid)


def cmd_land(args) -> int:
    if os.environ.get("AGENTS_SUP_TASK"):
        raise Refuse("a worker session may not land")
    if args.allow_claude_files and os.environ.get("CLAUDE_CODE_SESSION_ID"):
        raise Refuse("--allow-claude-files is for the owner's shell, not a Claude session")
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
    if hidden := [e[2:] for e in git_z(main, "ls-files", "-v") if e[0].islower()]:  # assume-unchanged: `status` does not show an edit
        index = {e.split("\t", 1)[1]: e.split()[1] for e in git_z(main, "ls-files", "-s")}
        for f in hidden:
            if (main / f).is_file() and not (main / f).is_symlink() and git_out(main, "hash-object", "--", f) != index.get(f):
                raise Refuse(f"{f} is marked assume-unchanged and differs from the index: landing could lose your edit; "
                             f"run `git update-index --no-assume-unchanged {f}`, commit or stash the edit, then rerun `sup land {tid}`")
    import sup_state, sup_workers
    try:
        prof = sup_state.current_profile(args.profile)
        entries = sup_state.profile_local(prof, main, check=False) if prof else []  # the links `kept_ignored` skips
    except ValueError as e:
        raise Refuse(str(e)) from e
    try:  # the pack repos the task names: dirty pack worktree refuses; the ranges go into the hub commit
        profile, pack = sup_workers.pack_for_land(main, prof, tid)
        ranges = sup_workers.land_ranges(main, pack, tid) if pack else {}
    except sup_workers.Refused as e:
        raise Refuse(str(e)) from e
    # a repo the task names without a new commit (old == new) gets no range line, and no tip to move
    body = "".join(f"{s} {b} {o}..{n}\n" for s, (b, o, n) in ranges.items() if o != n)
    default = args.into or default_branch(main)
    head = git(main, "symbolic-ref", "--short", "-q", "HEAD")
    if head.returncode:
        raise Refuse(f"landing checkout {main} is on a detached HEAD, not {default}")
    if head.stdout.strip() != default:
        raise Refuse(f"landing checkout {main} is on {head.stdout.strip()}, not {default}")
    # git overwrites what it ignores: a path the merge adds must not land on, or under, something the hub holds untracked
    # (a committed link to a `local` directory would replace that directory with a link to itself). The paths are those of
    # the merge result, not of the branch: default may have renamed a directory. A conflict is refused here, before the
    # checkout is touched: a merge that stops half-way has already written over ignored files, and the reset removes them.
    rerun = bool(sup_state.landing_message(main, default, tid))  # the commit exists: only the cleanup runs, no merge, no guard
    merged = None if rerun else merge_result(main, default, branch)
    if merged is None and not rerun:  # no merge-tree: the merged tree is known only when the branch sits on the default's tip
        if git(main, "merge-base", default, f"refs/heads/{branch}").stdout.strip() != git_out(main, "rev-parse", default):
            raise Refuse(f"git cannot compute the merge for landing {tid} (no merge-tree --write-tree before git 2.38, or unrelated histories): merge or rebase "
                         f"{default} into {branch} in the task worktree, then rerun `sup land {tid}`")
        merged = (f"refs/heads/{branch}", [])
    if merged and (hand := [f for f in merged[1] if f not in GENERATED]):
        raise Refuse(f"conflict landing {tid}; resolve in the task worktree: {', '.join(hand)}")
    tracked = set(git_z(main, "ls-tree", "-r", "-z", "--name-only", default))
    for f in [] if rerun else git_z(main, "diff", "--name-only", "--no-renames", "--diff-filter=A", default, merged[0]):
        for q in (Path(f), *Path(f).parents[:-1]):
            at = main / q
            if at.is_dir() and not at.is_symlink():  # a directory the branch turns into a file: its ignored content would go
                hit = q == Path(f) and bool(git_z(main, "ls-files", "-z", "--others", "--ignored", "--exclude-standard", "--", f))
            else:
                hit = os.path.lexists(at) and str(q) not in tracked
            if hit:
                raise Refuse(f"landing {branch} adds {f}, and the hub holds {q} untracked: landing would replace it; "
                             f"remove {f} from the branch, or move the hub's copy away")
    touched = [f for f in git_z(main, "diff", "--name-only", "--no-renames", f"{default}...refs/heads/{branch}") if _claude_file(f)]
    if touched and not args.allow_claude_files:
        raise Refuse(f"{branch} changes {', '.join(touched[:3])}: files the supervisor's sessions load; the owner lands it with --allow-claude-files")
    old = git(main, "rev-parse", "--verify", "-q", ref).stdout.strip()
    if old and old != tip:
        raise Refuse(f"{ref} already exists at another commit")
    done = rerun
    ledger_script(main)
    steps = [] if done else [f"squash-merge {branch} into {default} and commit once (hub-ledger lease, ledger sync and check)"]
    steps += [f"git update-ref {ref} {tip[:12]}"] if old != tip else []
    if wt:
        steps.append(f"move ignored files other than caches to {state_dir() / 'kept' / tid}, then remove worktree {wt}")
    steps += [f"record the pack tips of {', '.join(ranges)}"] if ranges else []
    steps.append(f"delete branch {branch}")
    if args.dry_run:
        print("\n".join("dry-run: " + s for s in steps))
        return 0
    if not done:
        _with_lease("hub-ledger", lambda: squash_and_commit(main, tid, branch, task_file, body), tid)
    if old != tip:
        git_out(main, "update-ref", ref, tip)
    if pack:  # after the hub commit, from its body (new or found): a crash here leaves the tips behind, the rerun moves them
        try:
            sup_workers.advance_tips(profile, pack, main, sup_state.landing_message(main, default, tid))
        except sup_workers.Refused as e:
            raise Refuse(f"the commit is made; {e}; rerun `sup land {tid}`") from e
    if wt and wt.exists():
        if is_dirty(wt):  # recomputed now: the worker may have written since the first check
            raise Refuse(f"task worktree {wt} changed during landing; the commit is made, rerun `sup land {tid}`")
        linked = {os.path.realpath(main / e.rstrip("/")) for e in entries}
        keep, kept = kept_ignored(wt, linked), state_dir() / "kept" / tid
        for f in keep:  # a link left in kept/<ID> by an earlier failed landing must not redirect the move
            if (kept / f).is_symlink() or not Path(os.path.realpath((kept / f).parent)).is_relative_to(os.path.realpath(kept)):
                raise Refuse(f"the commit is made; {kept / f} would lie outside {kept}: remove that link, then rerun `sup land {tid}`")
        for f in keep:  # `git worktree remove` deletes ignored files silently
            dest, n = kept / f, 1
            while os.path.lexists(dest):  # a file kept by an earlier attempt of this landing is evidence too
                dest, n = kept / f"{f}.{n}", n + 1
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(wt / f), str(dest))
            except OSError as e:  # e.g. a part of the path is a file kept earlier
                raise Refuse(f"the commit is made; cannot keep {f} in {kept} ({e.strerror}): move {kept} away, then rerun `sup land {tid}`") from e
        if keep:
            print(f"kept ignored files: {kept}")
        git_out(main, "worktree", "remove", str(wt))
    git_out(main, "branch", "-D", branch)
    _emit_landed(tid, args.profile)
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


def _files_problem(task, n: int) -> str:
    """Why the lane planner reads no fence in phase `n`: no `Files:` line, or an entry that is not a plain path."""
    import task_lanes as tl
    body = "\n".join(task.phases[n - 1].body)
    items = [x.strip().strip("`").rstrip("/") for m in tl.FILES_RE.findall(body) for x in m.split(",")]
    bad = next((i for i in items if not tl.entry_ok(i)), None)
    if bad is None:
        return "no `Files:` line"
    return f"every `Files:` entry must be a plain relative path (comma-separated, no prose); not a plain path: {bad[:60]!r}"


def _brief():
    """The task parser of agents-tasks: metadata, phases, acceptance criteria."""
    scripts = str(tasks_root() / "skills" / "task-ledger" / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import task_brief
    return task_brief


def _resources(task, path: Path) -> str:
    return task.meta.get("Resources") or next((m.group(1) for ln in path.read_text().splitlines()
                                               if (m := re.match(r"\s*(?:[-*]\s*)?Resources:\s*(\S.*)", ln))), "")


def readiness(task, path: Path, known=None) -> list[str]:
    """What is missing from the parsed `task` (file `path`); `known` (resource names of the profile) adds the resources it lacks."""
    import sup_state as st, sup_workers as sw
    from task_lanes import fence, split_entry  # the `Files:` rule of the lane planner
    missing: list[str] = []
    phases = [(n, p, st._clean(p.heading)[:60]) for n, p in enumerate(task.phases, 1) if p.heading.lower().startswith("phase")]
    for _, p, h in phases:
        if not PHASE_RE.match(p.heading):
            missing.append(f"phase heading is not `Phase <integer>`: {h}")
    if not any(PHASE_RE.match(p.heading) for _, p, _ in phases):
        missing.append("no `#### Phase <integer>` heading")
    related = [ln.strip(" -*`") for ln in task.sections.get("related tests", []) if ln.strip()]
    related_ok = bool(related) and "".join(related).upper() != "N/A"
    repos = sw._task_repos(None, "", task.meta)
    for n, p, h in phases:
        entries = fence(task, n)
        if not entries:
            missing.append(f"{h}: {_files_problem(task, n)}")
        for slug in sorted({split_entry(e)[0] for e in entries or ()} - {None} - repos ):
            missing.append(f"{h}: `Files:` names repo {slug!r}, which the `Repos` row does not have")
        if not related_ok and not re.search(r"^\s*(?:[-*]\s*)?\**checks?\**\s*:\s*\S", "\n".join(p.body), re.I | re.M):
            missing.append(f"{h}: names no check (`Checks:` line, or a `### Related tests` section)")
    if not any(re.match(r"\s*[-*] \[[ xX]\]", ln) for ln in task.sections.get("acceptance criteria", [])):
        missing.append("acceptance criteria: no checkbox")
    sec = unattended(path)
    if not sec:
        missing.append("no `### Unattended run` section (own or parent's)")
    else:
        for key in ("Authorised", "Owner only", "Defaults"):
            if not any(re.match(rf"{key}:\s*\S", ln) for ln in sec):
                missing.append(f"Unattended run: no `{key}:` line")
    res = _resources(task, path)
    if not res:
        missing.append("no `Resources:` line (write `Resources: none` when there are none)")
    elif res.strip().lower() != "none":
        for entry in (e.strip() for e in re.split(r"[,;]", res) if e.strip()):
            name = entry.split()[0].strip("`")
            if not DURATION_RE.search(entry):
                missing.append(f"Resources: `{entry}` has no duration (write e.g. `lab 20m`)")
            elif known is not None and name not in known:
                missing.append(f"Resources: {name if st.RES.match(name) else repr(name[:40])} is not a resource of the profile")
    return missing


def pack_problems(profile: str, pack: dict, hub: Path | None) -> list[str]:
    """One line per reason the pack cannot start: `<ID>: <problem>` or `pack <name>: <problem>`; [] when it is ready. Never raises:
    a Refused of a helper is one line. A task landed or archived is skipped. A `Files:` directory and a file under it count as shared."""
    import json, sup_tick, sup_workers as sw, task_lanes as tl
    name, out = pack["name"], []

    def add(tid, msg):
        out.append(f"{tid}: {msg}" if tid else f"pack {name}: {msg}")
    if hub is None:
        return [f"pack {name}: the profile has no hub"]
    try:
        reg, mp = sw._repos(hub)
        branches, own = set(pack.get("branches") or {}), {s for s, p in mp.items() if Path(p).resolve() == hub.resolve()}
        pf, known = sup_tick._files(profile)["profile"], set()  # a missing profile file names no resources
        if pf.exists():
            try:
                known = {r["name"] for r in json.loads(pf.read_text(encoding="utf-8"))["resources"]}
            except (OSError, ValueError, KeyError, TypeError) as e:
                known = None; add(None, f"{pf.name} cannot be read as a profile: {e!r:.80}")
        parsed = {}
        for t in pack["tasks"]:
            found = sorted((hub / TODOS).glob(f"{t}-*.md"))
            if sw._landed(profile, t, hub) or any((hub / ARCHIVED).glob(f"{t}-*.md")):
                continue
            if not found:
                add(t, f"no task file {TODOS}/{t}-*.md")
                continue
            try:
                task = _brief().parse_task(t, found[0])
                for m in readiness(task, found[0], known):
                    add(t, m)
                parsed[t] = task
            except (OSError, ValueError) as e:
                add(t, f"{found[0].name} cannot be read: {e}")
        try:
            deps = sw._edges(profile, pack, hub)
        except sw.Refused as e:
            deps = None
            if not any(str(e) in m for m in out):  # an unreadable file is already its task's line
                add(None, str(e))
        files, row = {}, {}
        for t, task in parsed.items():
            if re.search(r"[A-Z][A-Z0-9]*-[0-9]+\W*phase\s*[0-9]", cell := task.meta.get("Blocked by", ""), re.I):
                add(t, f"`Blocked by` names a phase ({cell.strip()[:60]!r}); name the task")
            row[t] = sw._task_repos(hub, t, task.meta)
            ents = [e for n in range(1, len(task.phases) + 1) for e in tl.fence(task, n) or []]
            for slug in sorted((row[t] & set(reg if own else mp) | {tl.split_entry(e)[0] for e in ents} - {None}) - branches - own):
                add(t, f"repo {slug!r} is not a repo of pack {name!r} (its branches: {', '.join(sorted(branches)) or 'none'})")
            for r in re.split(r"[,\s]+", task.meta.get("Repos", "").replace("`", "")) if reg or mp else ():
                if r and r.lower() not in ("none", "-", "—") and r not in (reg or mp):  # a typo must not read as "no repo"; the registry is the reference, the map only when there is none
                    add(t, f"`Repos` names {r[:40]!r}, which the repo registry does not have")
            files[t] = [p if s in own else e for e in ents for s, p in [tl.split_entry(e)]]

        def after(t, seen):
            for b in deps.get(t, []):
                if b not in seen:
                    seen.add(b); after(b, seen)
            return seen
        for i, a in enumerate(files if pack.get("parallel") and deps is not None else ()):
            for b in list(files)[i + 1:]:
                if b in after(a, set()) or a in after(b, set()) or row[a] & row[b] & branches:
                    continue
                for x in sorted({x for x in files[a] for y in files[b] if tl.overlap([x], [y])}):
                    add(None, f"{a} and {b} can run together and both list `{x}`")
    except (Refuse, sw.Refused, OSError, ValueError) as e:
        add(None, str(e))
    return out


def cmd_ready(args) -> int:
    if args.pack:
        import sup_state as st
        profile = st.current_profile(args.profile)
        try:
            pack = st.read_pack(profile, args.pack) if profile else None
        except ValueError as e:
            raise Refuse(str(e))
        if pack is None:
            raise Refuse(f"no pack {args.pack!r}" + ("" if profile else " (a profile is needed: --profile or AGENTS_SUPERVISOR)"))
        problems = pack_problems(profile, pack, args.repo)
        print("\n".join(problems or ["ready"]))
        return 3 if problems else 0
    top = Path(git_out(args.repo, "rev-parse", "--show-toplevel"))
    files = sorted((top / TODOS).glob(f"{args.task_id}-*.md"))
    if not files:
        raise Refuse(f"no task file {TODOS}/{args.task_id}-*.md")
    missing = readiness(_brief().parse_task(args.task_id, files[0]), files[0])
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
    p.add_argument("--repo", "--hub", dest="repo", type=Path, default=None,
                   help="hub repository (default: the profile's hub, else the git toplevel of the cwd)")
    p.add_argument("--profile", default=None)
    ss = p.add_subparsers(dest="sup_cmd", required=True)

    def leaf(name, **kw):
        q = ss.add_parser(name, **kw)
        q.add_argument("--repo", "--hub", dest="repo", type=Path, default=argparse.SUPPRESS,
                       help="hub repository (also accepted before the subcommand)")
        q.add_argument("--profile", default=argparse.SUPPRESS)
        return q
    w = leaf("worktree", help="create the task's hub worktree and branch")
    w.add_argument("task_id", type=_task_id)
    w.add_argument("--base", help="base ref (default: the local default branch)")
    w.set_defaults(sup_func=cmd_worktree)
    ln = leaf("land", help="squash-merge a closed-out task into the default branch")
    ln.add_argument("task_id", type=_task_id)
    ln.add_argument("--dry-run", action="store_true")
    ln.add_argument("--allow-claude-files", action="store_true",
                    help="owner only: land a branch that changes .claude/ or .mcp.json")
    ln.add_argument("--into", help="branch to land on (default: the default branch); the landing checkout must be on it")
    ln.set_defaults(sup_func=cmd_land)
    r = leaf("ready", help="check a task file is ready to dispatch (the permission preflight is not built)")
    one = r.add_mutually_exclusive_group(required=True)
    one.add_argument("task_id", nargs="?", type=_task_id)
    one.add_argument("--pack", help="check every task of a pack and the pack itself")
    r.set_defaults(sup_func=cmd_ready)
    p.set_defaults(func=run)
    for name in PARTS:  # each part adds its own subcommands; a part that is not installed is skipped
        try:
            __import__(name).register(ss)
        except ModuleNotFoundError as e:
            if e.name != name:
                print(f"at: sup: part {name} failed to load: {e}", file=sys.stderr)
        except ImportError as e:
            print(f"at: sup: part {name} failed to load: {e}", file=sys.stderr)
    _top_level_flags(ss)
    return p


def _top_level_flags(ss) -> None:
    """Make `at sup --profile P --hub H <part command>` work for every part: each leaf accepts both flags, and a flag the
    leaf did not see keeps the value given before the subcommand (default SUPPRESS). `--hub` also fills args.hub."""
    for q in ss.choices.values():
        for sub in (a for a in q._actions if isinstance(a, argparse._SubParsersAction)):
            _top_level_flags(sub)  # `at sup watch status`: the leaves under a part's own subcommand
        for a in q._actions:
            if {"--profile", "--hub", "--repo"} & set(a.option_strings):
                a.default = argparse.SUPPRESS
        have = {o for a in q._actions for o in a.option_strings}
        if "--profile" not in have:
            q.add_argument("--profile", default=argparse.SUPPRESS)
        if not {"--hub", "--repo"} & have:
            q.add_argument("--hub", "--repo", dest="repo", type=Path, default=argparse.SUPPRESS)
        f = q.get_default("func")
        if f is not None and f is not run:
            q.set_defaults(func=_with_hub(f))


def _with_hub(f):
    def call(args):
        hub = getattr(args, "hub", None) or getattr(args, "repo", None)
        args.hub = str(hub) if hub is not None else None
        args.profile = getattr(args, "profile", None)
        return f(args)
    return call


def run(args) -> int:
    try:
        import sup_state
        args.repo = Path(sup_state.hub(sup_state.current_profile(args.profile), args.repo)).resolve()
    except ValueError as e:
        print(f"sup: {e}", file=sys.stderr)
        return 2
    try:
        return args.sup_func(args)
    except (Refuse, OSError) as e:
        print("sup: refused: " + str(e).encode("utf-8", "backslashreplace").decode(), file=sys.stderr)  # a path may not be UTF-8
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
