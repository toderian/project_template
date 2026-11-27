"""Packs and worker sessions of `at sup`: pack commands, start-worker, stop-worker, and the helpers other lanes call.

Commands (all take --profile, default $AGENTS_SUPERVISOR; exit 0 ok, 2 usage, 3 refused):
  pack <name> <TASK-ID>... [--parallel] [--branch <slug>=<branch>]...   create, or replace while the pack is `new`;
                                          without --branch a replaced pack keeps its recorded branches
  packs | start-pack | pause-pack | close-pack <name> | order <name> <TASK-ID>... | cap <n>
  start-worker <TASK-ID> [--headless] [--hub <path>] | stop-worker <TASK-ID> | reap [--dry-run]
start-pack, pause-pack, close-pack, order and cap are chat-only (sup_ask.require_chat); `pack` starts nothing, so any
session but a worker may run it (sup_ask.not_worker). Every command except `packs` refuses (exit 3) in a worker session
(AGENTS_SUP_TASK set): an honest-mistake check, not a fence, because a worker runs under the same uid as the state directory.

Pack repos: a key of the pack's `branches` is a slug of .config/repos.project.md with a line in .local/repos.map. start-pack
creates (or attaches to) the branch off the repo's integration branch and the worktree <checkout>-<pack>; start-worker
writes .local/repos.map in the task worktree (pack repos at their pack worktree). start-pack records the first tip of each
pack repo in pack["tips"] (never overwritten). A key with no map line is the directory of that name beside the hub, as in 1.17.0.

Sessions: a headless start passes `--session-id <uuid4>`; `claude --bg` ignores that flag and picks its own id, so a bg
start reads the short id from its `backgrounded · <id> · <name>` line, finds the full id in `claude agents` and re-keys
the row. The full session id is the registry key. start-worker writes a row
in state `starting` under the first lock (it counts against the cap and shuts out a second start of the task), then
becomes `running`; a failed start removes the row. An existing task worktree with no live row is reused.
Locking: state is read and written under `sup_state.locked(profile)`, but start-worker and stop-worker release it
before every `at` or `claude` subprocess. The helpers below never take it and never write state:
  agents() -> list|None                      the rows of `claude agents --json --all`; None on any error
  is_alive(row, agents) -> bool|None         bg: a row with the sessionId and a non-null pid (None: `agents` failed, cannot
                                             tell); headless: the row's pid exists (a waiting headless worker has no process)
  wake_due(profile, row) -> (text, key)|None what to say when waking the row now, None when it must not be woken
  wake(profile, session, text) -> bool|int   `claude stop` (or already stopped), then `claude --bg --resume` (headless:
                                             `claude -p --resume <id> <session_flags> --output-format json`, its own
                                             logs/<task>.wake-<n>.json) in the row's cwd with AGENTS_SUPERVISOR and
                                             AGENTS_SUP_TASK; bg: True only when the resume says it woke that session;
                                             headless: the Popen pid (store it in the row); False on failure
  session_flags() -> list[str]               the permission mode (and model) of a start and of a headless wake, in one place
  slots_used(profile) -> int                 live rows plus stopped rows claimed by a wake (`waking`, fresh); counts against the cap
  age(stamp) -> float                        seconds since a sup_state.now() stamp (0.0 when unreadable)
  next_tasks(profile) -> list[str]           tasks that may start now: pack running, no worker row, not landed, under the
                                             cap (live rows and rows due for a wake count); a serial pack offers its first
                                             open task, and only when the previous one is landed
  orphans(profile, agents) -> list[dict]    live bg sessions named `<profile>-<TASK>` (a task of a pack) or
                                             `<profile>-topic-<name>` whose session sup does not track, started more than
                                             REAP_GRACE seconds ago (a start in progress is not yet re-keyed)
  reap(profile, agents?, dry=False)          `claude stop` each orphan; returns one line per orphan. The watcher runs it
                                             every pass, so a start that lost track of its session never leaves a
                                             second worker running in the same worktree
  clean_env(**extra) -> dict                 os.environ without GIT_CONFIG_* and the chat token, PATH restored from
                                             AGENTS_SUP_ORIG_PATH (the supervisor launcher saves it)

The `claude` binary is $AGENTS_CLAUDE_BIN and `at` is $AGENTS_AT_BIN. Workers get AGENTS_SUPERVISOR and AGENTS_SUP_TASK.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import sup_state as st
from task_lanes import SLUG

WORKER_PROMPT = (
    "Execute task {task} with agents-core:execute-plan as an unattended run. You are supervised by profile {profile}. "
    "For a decision outside your authority run `at sup ask`. For a shared resource run `at sup need <resource> "
    "--minutes <n>` (--minutes is required); once it is granted, run the resource's script yourself while you hold the lease, "
    "then `at sup release <resource>` as soon as you are done with it. Only after "
    "an `ask` or a `need` that was not granted at once, end your turn with the line `WAITING supervisor: <id>`, where "
    "<id> is the question id or the resource name that the command printed. When you are woken, read your answers with `at sup inbox` and "
    "acknowledge each one with `at sup inbox --ack <id>`. Never ask the user. Close the task out with "
    "agents-tasks:complete-task. Arm the run guard first (`at run-guard arm {task}`) and never disarm it. "
    "Do not push and do not merge. You are on task/{task} in a task worktree on purpose: a work mode of default-branch for the hub "
    "does not apply to you. Code for a sibling repo goes to the path in .local/repos.map, one commit per phase, on the branch "
    "checked out there; create no branch and push nothing."
)
CAP_RANGE = range(1, 9)
WAKE_TRIES = 3
DEAD_RESTARTS = 2
STARTING_TTL = 300.0
POLL_TRIES, POLL_DELAY = 6, 0.5
GONE_TRIES = 20  # times POLL_DELAY: how long a stopped bg session may take to exit before a resume
COPY = re.compile(r"started a copy as ([0-9a-f]{8})")
REAP_GRACE = 120.0
RESTART_TEXT = "Continue the task. Read your answers with: at sup inbox --task {task}"
ANSWER_TEXT = "Read your answers with: at sup inbox --task {task}"


class Refused(Exception):
    pass


def _claude() -> str:
    return os.environ.get("AGENTS_CLAUDE_BIN", "claude")


def _at() -> str:
    return os.environ.get("AGENTS_AT_BIN", "at")


def clean_env(**extra) -> dict:
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("GIT_CONFIG_") and k not in ("AGENTS_SUP_CHAT_TOKEN", "AGENTS_SUP_TASK", "AGENTS_SUP_TOPIC",
                                                            "AGENTS_SUP_ORIG_PATH")}
    if os.environ.get("AGENTS_SUP_ORIG_PATH"):
        env["PATH"] = os.environ["AGENTS_SUP_ORIG_PATH"]
    env.update(extra)
    return env


def session_flags() -> list[str]:
    return ["--permission-mode", "auto"]


def age(stamp) -> float:
    try:
        return time.time() - datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%S%z").timestamp()
    except (TypeError, ValueError):
        return 0.0


def _waking(row: dict) -> bool:
    """True while a wake has claimed the row (watcher mid-wake); the claim expires after STARTING_TTL and never drops the row."""
    return bool(row.get("waking")) and age(row["waking"]) <= STARTING_TTL


def slots_used(profile: str) -> int:
    return len(st.live_workers(profile)) + sum(1 for w in st.workers(profile) if w.get("state") == "stopped" and _waking(w))


def _run(argv: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, timeout=kw.pop("timeout", 60), stdin=subprocess.DEVNULL, **kw)


def agents() -> list[dict] | None:
    """The rows of `claude agents --json --all`; None when the call or its output is bad (never read that as "no workers")."""
    try:
        out = _run([_claude(), "agents", "--json", "--all"], env=clean_env())
        rows = json.loads(out.stdout) if out.returncode == 0 else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else None


def _pid_exists(pid) -> bool:
    if not isinstance(pid, int) or not 0 < pid < 2**31:
        return False
    try:
        if os.waitpid(pid, os.WNOHANG)[0] == pid:
            return False  # our own child, now reaped: a zombie answers kill(pid, 0) as alive
    except ChildProcessError:
        pass
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True
    return True


_UNSET = object()


def is_alive(row: dict, rows=_UNSET) -> bool | None:
    if row.get("mode") == "headless":
        return row.get("state") == "waiting" or _pid_exists(row.get("pid"))
    found = agents() if rows is _UNSET else rows
    if found is None:
        return None
    return any(r.get("sessionId") == row.get("session") and r.get("pid") is not None for r in found)


def orphans(profile: str, found) -> list[dict]:
    if found is None:
        return []
    known = {w.get("session") for w in st.workers(profile)}
    try:
        import sup_topics
        known |= sup_topics.topic_sessions(profile)
    except ImportError:
        pass
    tasks = {t for p in st.list_packs(profile) for t in p.get("tasks", [])}
    out, now = [], time.time()
    for r in found:
        name, sid, started = r.get("name") or "", r.get("sessionId"), r.get("startedAt")
        if r.get("pid") is None or r.get("kind", "background") != "background" or not _session_ok(sid) or sid in known:
            continue
        rest = name[len(profile) + 1:] if name.startswith(f"{profile}-") else None
        if rest is None or not (rest in tasks or rest.startswith("topic-")):
            continue
        if not isinstance(started, (int, float)) or now - started / 1000 < REAP_GRACE:
            continue
        out.append(r)
    return out


def reap(profile: str, found=_UNSET, dry: bool = False) -> list[str]:
    found = agents() if found is _UNSET else found
    acts = []
    for r in orphans(profile, found):
        if not dry:
            _stop_session(r["sessionId"])
        acts.append(f"{'would reap' if dry else 'reaped'} {r['name']} {r['sessionId'][:8]}")
    return acts


def _pack_blocked(profile: str, task: str) -> bool:
    pack = st.pack_of(profile, task)
    return bool(pack) and pack.get("state") in ("paused", "closed")


def wake_due(profile: str, row: dict):
    """(text, key) when the watcher should wake this row now: an unread answer or a pending restart, and the row is not
    owner-stopped, not claimed by a wake, its pack is not paused or closed, the answer was not already woken for
    (`woken` holds the last inbox id woken), a final `dead` (`dead_key`) is not for this same answer, and the failures
    for this cause are under WAKE_TRIES."""
    task = row.get("task")
    if row.get("state") not in ("stopped", "waiting") or not task or row.get("stopped_by") == "owner" or _waking(row):
        return None
    unread = st.inbox(profile, task, unread_only=True)
    pending = bool(row.get("restart_pending"))
    if not unread and not pending:
        return None
    if _pack_blocked(profile, task):
        return None
    last = unread[-1]["id"] if unread else None
    key = f"restart{row.get('restarts', 0)}" if pending else last
    if not pending and row.get("woken") == last:
        return None
    if row.get("dead_key") is not None and key == row["dead_key"]:
        return None
    if row.get("wake_key") == key and row.get("wake_fail", 0) >= WAKE_TRIES:
        return None
    return (RESTART_TEXT if pending else ANSWER_TEXT).format(task=task), key


def _session_ok(session) -> bool:
    return isinstance(session, str) and bool(st.SESSION.match(session))


def wake(profile: str, session: str, text: str) -> bool | int:
    row = st.worker_for(profile, session=session)
    if row is None or not _session_ok(session) or not row.get("task"):
        return False
    cwd = row.get("cwd")
    if not cwd or not os.path.isdir(cwd):
        return False
    env = clean_env(AGENTS_SUPERVISOR=profile, AGENTS_SUP_TASK=row["task"])
    try:
        if row.get("mode") == "headless":
            if _pid_exists(row.get("pid")):
                return False  # still running: nothing to resume
            logs = st.profile_dir(profile) / "logs"
            logs.mkdir(exist_ok=True)
            n = len(list(logs.glob(f"{row['task']}.wake-*.json"))) + 1
            with open(logs / f"{row['task']}.wake-{n}.json", "w", encoding="utf-8") as out:
                proc = subprocess.Popen([_claude(), "-p", "--resume", session, *session_flags(), "--output-format", "json", text, *_add_dirs(profile, _wake_hub(profile, cwd), cwd)],
                                        cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                                        start_new_session=True)
            return proc.pid
        if _run([_claude(), "stop", session[:8]], env=env, cwd=cwd).returncode != 0:
            found = agents()
            if found is None or any(r.get("sessionId") == session and r.get("pid") is not None for r in found):
                return False  # the stop failed and the session may still run: a resume would start a copy
        if not wait_gone(session):
            return False  # still exiting: a resume now would start an untracked copy
        return resume_bg(session, text, _add_dirs(profile, _wake_hub(profile, cwd), cwd), env, cwd)
    except (OSError, subprocess.SubprocessError):
        return False


def _wake_hub(profile: str, cwd) -> Path | None:
    """The hub of a woken worker: config key `hub`, else the repo the worktree `cwd` belongs to (a start with `--hub` stored no
    key, and the wake may run from any directory), else the hub of the process cwd."""
    if st.config(profile).get("hub"):
        return _hub_or_none(profile)
    try:
        common = Path(_git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip())
    except Refused:
        return _hub_or_none(profile)
    return common.parent if common.name == ".git" else _hub_or_none(profile)


def _landed(profile: str, task: str, hub) -> bool:
    if hub is None:
        return any(e.get("kind") == "landed" and e.get("task") == task for e in st.events_since(profile, 0))
    return st.landed(profile, task, hub)


def _hub_or_none(profile: str):
    try:
        return st.hub(profile)
    except ValueError:
        return None


def _lines(f: Path) -> list[str]:
    """The lines of a UTF-8 file; [] when it is no file; Refused (naming it) when it cannot be read."""
    try:
        return f.read_text(encoding="utf-8").splitlines() if f.is_file() else []
    except (OSError, ValueError) as e:
        raise Refused(f"{f} cannot be read: {e}") from None


def _repos(hub: Path) -> tuple[dict, dict]:
    """(registry {slug: (default branch, integration branch)}, map {slug: absolute path}) of the hub: the one reader of both
    files; a missing file is empty; a map path that is not absolute is refused by name."""
    reg, cols, mp = {}, (3, 4), {}
    f = hub / ".config" / "repos.project.md"
    for line in _lines(f):
        cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")] if line.lstrip().startswith("|") else []
        if cells[:1] == ["Repo"] and "Integration branch" in cells and "Default branch" in cells:
            cols = (cells.index("Default branch"), cells.index("Integration branch"))
        elif cells and SLUG.fullmatch(cells[0]):
            reg[cells[0]] = tuple(cells[c] if c < len(cells) else "unknown" for c in cols)
    f = hub / ".local" / "repos.map"
    for line in _lines(f):
        slug, sep, path = line.partition(":")
        if sep and SLUG.fullmatch(slug.strip()) and path.strip():
            if not os.path.isabs(path.strip()):
                raise Refused(f"repos.map: the path of {slug.strip()!r} is not absolute")
            mp[slug.strip()] = path.strip()
    return reg, mp


def _checkout(hub: Path, slug: str, mp: dict) -> Path:
    return Path(mp[slug]) if slug in mp else hub.parent / slug


def _task_meta(root: Path, task: str) -> dict:
    """The meta rows of the task file under root (the hub or a task worktree), read with the task parser `sup.readiness`
    uses; {} when there is no file; Refused when the file cannot be read."""
    import sup  # lazily: sup imports this module through add_parser
    try:
        task_brief = sup._brief()
    except sup.Refuse as e:
        raise Refused(str(e)) from e
    for f in sorted(g for d in (sup.TODOS, sup.ARCHIVED) for g in (root / d).glob(f"{task}-*.md")):  # a landed task is archived
        try:
            return task_brief.parse_task(task, f).meta
        except (OSError, ValueError) as e:
            raise Refused(f"{f.name} cannot be read: {e}") from e
    return {}


def _task_repos(root: Path | None, task: str, meta: dict | None = None) -> set[str]:
    """The slugs of the `Repos` row of the task file under root (or of `meta`, already read); empty when there is no file or row."""
    return {r for r in re.split(r"[,\s]+", (_task_meta(root, task) if meta is None else meta).get("Repos", "").replace("`", "")) if SLUG.fullmatch(r)}


def _blockers(profile: str, hub: Path | None, task: str) -> list[str]:
    """The open blockers of `task`: ids in its `Blocked by` row (hub working tree) that neither landed in this profile nor
    sit in the archive of the default branch; a phase counts as the whole task. The one rule for offers, refusals and status."""
    if hub is None:
        return []
    import sup, task_run
    return [b for b in task_run.blocker_ids(_task_meta(hub, task).get("Blocked by", ""))
            if st.TASK.match(b) and not _landed(profile, b, hub) and not any((hub / sup.ARCHIVED).glob(f"{b}-*.md"))]


def _edges(profile: str, pack: dict, hub: Path | None) -> dict[str, list[str]]:
    """{task: open blockers} of the pack's unlanded tasks that have any. Refused when the pack would wait for ever: a blocker
    open and outside the pack, a cycle, a serial order against an edge."""
    tasks = pack["tasks"]
    deps = {t: bs for t in tasks if not _landed(profile, t, hub) and (bs := _blockers(profile, hub, t))}
    for t, bs in deps.items():
        for b in bs:
            if b not in tasks:
                raise Refused(f"{t} is blocked by {b}, which is open and not in pack {pack['name']!r}")
    rest = dict(deps)
    while stuck := {t: [b for b in bs if b in rest] for t, bs in rest.items()}:
        free = [t for t, bs in stuck.items() if not bs]
        if not free:
            seen, t = [], next(iter(stuck))
            while t not in seen:  # every stuck task has a stuck blocker: follow them until one repeats
                seen.append(t); prev, t = t, stuck[t][0]
            raise Refused(f"{prev} is blocked by {t}, and the blockers of the pack form a cycle")
        for t in free:
            del rest[t]
    if not pack.get("parallel"):
        for i, t in enumerate(tasks):
            for b in deps.get(t, []):
                if tasks.index(b) > i:
                    raise Refused(f"{t} is blocked by {b}, which a serial pack runs later; reorder the tasks")
    return deps


def _pack_repos(pack: dict, hub: Path | None, task: str) -> set[str]:
    """The pack repos `task` names in its `Repos` row; a pack without branches never reads a task file."""
    shared = set(pack.get("branches") or {})
    return _task_repos(hub, task) & shared if shared and hub else set()


def _held(profile: str, pack: dict, hub: Path | None, rows: list[dict]) -> dict[str, str]:
    """Pack repo -> the task that has a worker row and has not landed: nobody else works there until it lands."""
    started = [t for t in pack["tasks"] if any(w.get("task") == t for w in rows) and not _landed(profile, t, hub)]
    return {slug: t for t in started for slug in _pack_repos(pack, hub, t)}


def next_tasks(profile: str) -> list[str]:
    rows = st.workers(profile)
    hub = _hub_or_none(profile)
    waking = sum(1 for w in rows if w.get("state") == "stopped" and wake_due(profile, w))
    free = st.config(profile)["cap"] - slots_used(profile) - waking
    out: list[str] = []
    late: list[str] = []  # tasks of a pack whose edges are refused: offered so `start-worker` says why, after the healthy packs
    for pack in st.list_packs(profile):
        if pack.get("state") != "running":
            continue
        try:  # only a healthy wait holds a task back; a task file git or the disk cannot read makes the pack unhealthy too
            busy = _held(profile, pack, hub, rows)
            deps, offer = _edges(profile, pack, hub), out
        except Refused:
            busy, deps, offer = {}, {}, late
        open_ = [t for t in pack["tasks"] if not _landed(profile, t, hub)]
        for task in open_:
            if any(w.get("task") == task for w in rows):
                if not pack.get("parallel"):
                    break  # the previous task is not landed yet: a serial pack waits
                continue
            if deps.get(task):
                if not pack.get("parallel"):
                    break
                continue
            try:
                mine = _pack_repos(pack, hub, task)
            except Refused:
                offer.append(task)  # `start-worker` names the unreadable file
                if not pack.get("parallel"):
                    break
                continue
            if mine & set(busy):
                continue  # another task of the pack works in the same pack repo and has not landed
            busy.update(dict.fromkeys(mine, task))
            offer.append(task)
            if not pack.get("parallel"):
                break
    return (out + late)[:max(free, 0)]


def _need_profile(args) -> str:
    try:
        profile = st.current_profile(getattr(args, "profile", None))
    except ValueError as e:
        raise SystemExit(f"at: sup: {e}") from None
    if not profile:
        print("at: sup: no profile: pass --profile or set AGENTS_SUPERVISOR", file=sys.stderr)
        raise SystemExit(2)
    return profile


def _command(fn=None, *, chat: bool = False, lock: bool = True, guard: bool = True):
    """Wrap a command: profile, worker-session check, chat check, the lock around the whole command when `lock`
    (else fn locks itself)."""
    if fn is None:
        return lambda f: _command(f, chat=chat, lock=lock, guard=guard)

    def run(args) -> int:
        profile = _need_profile(args)
        if guard and (os.environ.get("AGENTS_SUP_TASK") or os.environ.get("AGENTS_SUP_TOPIC")):
            who = "a worker" if os.environ.get("AGENTS_SUP_TASK") else "a topic"
            print(f"at: sup: this command is for the supervisor and the owner, not for {who} session", file=sys.stderr)
            return 3
        if chat:
            import sup_ask  # lazily: sup_ask is another part
            if not sup_ask.require_chat():
                return 3
        try:
            if not lock:
                return fn(profile, args) or 0
            with st.locked(profile):
                return fn(profile, args) or 0
        except Refused as e:
            print(f"at: sup: {e}", file=sys.stderr)
            return 3
        except ValueError as e:
            print(f"at: sup: {e}", file=sys.stderr)
            return 2
    return run


def _get_pack(profile: str, name: str) -> dict:
    pack = st.read_pack(profile, name)
    if pack is None:
        raise Refused(f"no pack {name!r}")
    return pack


def _started_tasks(profile: str) -> set[str]:
    return {w["task"] for w in st.workers(profile)}


def _git(path, *args: str) -> subprocess.CompletedProcess:
    try:
        return _run(["git", "-C", str(path), *args], env=clean_env())
    except (OSError, subprocess.SubprocessError) as e:
        raise Refused(f"git {args[0]} failed: {e}") from None


def _valid_branch(branch: str) -> bool:
    return bool(branch) and not branch.startswith("-") and "@{" not in branch and \
        _git(".", "check-ref-format", "--branch", branch).returncode == 0


def _pack_wt(checkout: Path, pack: dict) -> Path:
    """The pack worktree of a pack repo: the one rule for its path."""
    return checkout.parent / f"{checkout.name}-{pack['name']}"


def _clean(path) -> bool:
    p = _git(path, "status", "--porcelain")
    return p.returncode == 0 and not p.stdout.strip()


def _tip(checkout, branch: str) -> str:
    return _git(checkout, "rev-parse", "--verify", "-q", f"refs/heads/{branch}^{{commit}}").stdout.strip()


def land_ranges(main: Path, pack: dict, task: str) -> dict:
    """{slug: (branch, old tip, new tip)} of the pack repos `task` names, for `at sup land`; refuses a dirty pack worktree
    or a repo with no recorded tip. The tips in the pack move only after the hub commit (see advance_tips)."""
    _, mp = _repos(main)
    out = {}
    for slug in sorted(_pack_repos(pack, main, task)):
        checkout, branch = _checkout(main, slug, mp), pack["branches"][slug]
        wt = _pack_wt(checkout, pack)
        if wt.exists() and not _clean(wt):
            raise Refused(f"pack worktree {wt} has uncommitted changes")
        old, new = (pack.get("tips") or {}).get(slug), _tip(checkout, branch)
        if not old or not new:
            raise Refused(f"{slug}: no recorded tip or no branch {branch}; run start-pack")
        out[slug] = (branch, old, new)
    return out


def pack_for_land(main: Path, profile: str | None, task: str):
    """(profile, pack) the landing of `task` works with, or (None, None) when no pack with branches holds it. Every profile
    whose hub is `main` (and the given one) is searched: landing past a pack never depends on the flag or the environment."""
    held = {}
    for d in sorted(st.root().iterdir()) if st.root().is_dir() else ():
        if d.is_dir() and st.NAME.match(d.name):
            pack = st.pack_of(d.name, task)
            hub = st.config(d.name).get("hub")
            # a profile with no usable hub in its config counts as this hub: the landing fails closed
            if pack and pack.get("branches") and (d.name == profile or not isinstance(hub, str) or not hub or Path(hub).resolve() == main.resolve()):
                held[d.name] = pack
    if held and profile not in held:
        raise Refused(f"{task} is in a pack of {', '.join(held)} with pack branches; pass --profile of the one that holds it")
    return (profile, held[profile]) if held else (None, None)


def advance_tips(profile: str, pack: dict, main: Path, message: str) -> None:
    """Move the tips to the `<slug> <branch> <old>..<new>` lines of the hub landing commit `message`: one source for a first
    landing and a rerun. A tip never moves backwards: a new tip that does not descend from the stored one is left, and said."""
    _, mp = _repos(main)
    new = {}
    for slug, b, tip in re.findall(r"^(\S+) (\S+) [0-9a-f]{40}\.\.([0-9a-f]{40})$", message, re.M):
        cur = (pack.get("tips") or {}).get(slug)
        if pack["branches"].get(slug) != b or cur == tip:
            continue
        if cur and _git(_checkout(main, slug, mp), "merge-base", "--is-ancestor", cur, tip).returncode:
            print(f"{slug}: the stored tip {cur[:12]} is not an ancestor of {tip[:12]}; left as it is (`at sup accept-tip {pack['name']} {slug}` takes the branch head)")
        else:
            new[slug] = tip
    if new:
        with st.locked(profile):
            fresh = _get_pack(profile, pack["name"])
            st.write_pack(profile, {**fresh, "tips": {**(fresh.get("tips") or {}), **new}})


def pack_ahead(hub: Path, pack: dict) -> dict:
    """{slug: (branch, commits above the recorded tip)} for the pack repos whose branch is past its tip."""
    _, mp = _repos(hub)
    out = {}
    for slug, branch in (pack.get("branches") or {}).items():
        tip = (pack.get("tips") or {}).get(slug)
        n = _git(_checkout(hub, slug, mp), "rev-list", "--count", f"{tip}..refs/heads/{branch}") if tip else None
        if n is not None and n.returncode == 0 and int(n.stdout) > 0:
            out[slug] = (branch, int(n.stdout))
    return out


def _pack_worktrees(profile: str, pack: dict) -> dict:
    """Per pack repo: the branch (off the integration branch, or the existing one) and the worktree <checkout>-<pack>.
    Returns {slug: tip of the worktree}. Safe to run twice; refuses a path that is not that worktree on that branch.
    Takes no lock."""
    if not pack.get("branches"):
        return {}
    hub = st.hub(profile)
    reg, mp = _repos(hub)
    tips = {}
    for slug, branch in pack["branches"].items():
        checkout = _checkout(hub, slug, mp)
        if not checkout.is_dir() or _git(checkout, "rev-parse", "--git-dir").returncode:
            raise Refused(f"{slug}: {checkout} is not a git repository")
        wt = _pack_wt(checkout, pack)
        if wt.exists():
            same = _git(wt, "rev-parse", "--git-common-dir").stdout.strip(), _git(checkout, "rev-parse", "--git-common-dir").stdout.strip()
            if (_git(wt, "symbolic-ref", "--short", "HEAD").stdout.strip() != branch
                    or Path(wt, same[0]).resolve() != Path(checkout, same[1]).resolve()):
                raise Refused(f"{wt} exists and is not a worktree of {slug} on {branch}")
            tips[slug] = _git(wt, "rev-parse", "HEAD").stdout.strip()
            continue
        if _git(checkout, "rev-parse", "--verify", "-q", f"refs/heads/{branch}").returncode == 0:
            args = ["worktree", "add", str(wt), branch]
        else:
            base = reg.get(slug, ("unknown", "unknown"))[1]
            if base not in ("N/A", "unknown") and not _valid_branch(base):
                raise Refused(f"{slug}: the integration branch {base!r} in the registry is not a usable branch name")
            if base in ("N/A", "unknown"):
                base = _git(checkout, "symbolic-ref", "--short", "HEAD").stdout.strip()
                print(f"{slug}: no integration branch in the registry; branching from {base or 'HEAD'}, the one checked out")
            args = ["worktree", "add", "-b", branch, str(wt), base or "HEAD"]
        made = _git(checkout, *args)
        if made.returncode:
            raise Refused(f"{slug}: git worktree add failed: {(made.stderr.strip().splitlines() or ['?'])[-1]}")
        tips[slug] = _git(wt, "rev-parse", "HEAD").stdout.strip()
        print(f"{slug}: {wt} on {branch}")
    return tips


@_command
def cmd_pack(profile: str, args) -> int:
    import sup_ask  # lazily: sup_ask is another part
    if not sup_ask.not_worker(profile):
        return 3
    old = st.read_pack(profile, args.name)
    if old and old.get("state") != "new":
        raise Refused(f"pack {args.name!r} is {old['state']}; only a new pack can be replaced")
    if len(set(args.tasks)) != len(args.tasks):
        raise ValueError("a task is listed twice")
    for task in args.tasks:
        other = st.pack_of(profile, task)
        if other and other["name"] != args.name:
            raise Refused(f"{task} is already in pack {other['name']!r}")
    _edges(profile, {"name": args.name, "tasks": args.tasks, "parallel": args.parallel}, _hub_or_none(profile))
    branches = (old or {}).get("branches") or {}
    if args.branch:
        reg, mp = _repos(st.hub(profile))
        branches = {}
        for item in args.branch:
            slug, _, branch = item.partition("=")
            if slug in branches:
                raise Refused(f"repo {slug!r} is given twice in --branch")
            if slug not in reg:
                raise Refused(f"repo {slug!r} is not in .config/repos.project.md")
            if slug not in mp:
                raise Refused(f"repo {slug!r} has no path in .local/repos.map")
            if not _valid_branch(branch):
                raise Refused(f"{branch!r} is not a usable branch name")
            if branch in reg[slug]:
                raise Refused(f"{branch!r} is the default or integration branch of {slug!r}; name a feature branch")
            branches[slug] = branch
    st.write_pack(profile, {"name": args.name, "tasks": args.tasks, "parallel": args.parallel, "state": "new", "branches": branches,
                            "tips": (old or {}).get("tips") or {}})
    st.touch(profile, f"pack {args.name} {' '.join(args.tasks)}{' --parallel' if args.parallel else ''}"
                      + "".join(f" --branch {s}={b}" for s, b in branches.items()))
    print(f"pack {args.name}: {len(args.tasks)} tasks, {'parallel' if args.parallel else 'serial'}, new")
    return 0


@_command(guard=False)
def cmd_packs(profile: str, args) -> int:
    for p in st.list_packs(profile):
        print(f"{p['name']} {p.get('state')} {'parallel' if p.get('parallel') else 'serial'} {' '.join(p['tasks'])}")
    return 0


def _set_state(profile: str, name: str, state: str, allowed: tuple[str, ...], verb: str) -> int:
    pack = _get_pack(profile, name)
    if pack["state"] not in allowed:
        raise Refused(f"pack {name!r} is {pack['state']}; cannot {verb}")
    if state == "closed" and any(w.get("task") in pack["tasks"] for w in st.live_workers(profile)):
        raise Refused(f"pack {name!r} has a live worker")
    st.write_pack(profile, {**pack, "state": state})
    st.touch(profile, f"{verb}-pack {name}")
    print(f"pack {name}: {state}")
    return 0


@_command(chat=True, lock=False)
def cmd_start_pack(profile: str, args) -> int:
    pack = _get_pack(profile, args.name)
    live = pack.get("state") in ("new", "paused", "running")
    if live:
        import sup  # lazily: sup_workers is loaded by sup.add_parser
        if problems := sup.pack_problems(profile, pack, _hub_or_none(profile)):
            raise Refused(f"pack {args.name!r} is not ready:\n" + "\n".join(problems))
    tips = _pack_worktrees(profile, pack) if live else {}  # git first, no lock
    with st.locked(profile):
        fresh = _get_pack(profile, args.name)
        if (fresh.get("branches") or {}) != (pack.get("branches") or {}):
            raise Refused(f"pack {args.name!r} changed its branches during start-pack; run it again")
        st.write_pack(profile, {**fresh, "tips": {**tips, **(fresh.get("tips") or {})}})  # the first tip of a repo stays
        return _set_state(profile, args.name, "running", ("new", "paused", "running"), "start")


@_command(chat=True)
def cmd_pause_pack(profile: str, args) -> int:
    return _set_state(profile, args.name, "paused", ("running", "paused"), "pause")


@_command(chat=True)
def cmd_close_pack(profile: str, args) -> int:
    import sup  # lazily: sup_workers is loaded by sup.add_parser
    pack = _get_pack(profile, args.name)
    hub = st.hub(profile) if pack.get("branches") and pack.get("tips") else None
    _, mp = _repos(hub) if hub else (0, {})
    plan = []  # decided before `closed` is written; never --force, never a branch delete
    for slug, branch in (pack.get("branches") or {}).items() if hub else ():
        checkout = _checkout(hub, slug, mp)
        wt = _pack_wt(checkout, pack)
        if wt.exists():
            clean = _clean(wt)
            kept = len(sup.kept_ignored(wt)) if clean else 0  # the same ignored files `land` keeps
            why = "uncommitted changes" if not clean else f"{kept} ignored file(s)" if kept else \
                "not at the landed tip" if _git(wt, "rev-parse", "HEAD").stdout.strip() != pack["tips"].get(slug) else ""
            plan.append((slug, branch, checkout, wt, why))
    rc = _set_state(profile, args.name, "closed", ("new", "running", "paused", "closed"), "close")
    for slug, branch, checkout, wt, why in plan:
        if not why and _git(checkout, "worktree", "remove", str(wt)).returncode:
            why = "git worktree remove refused"
        print(f"{slug}: kept {wt} ({why}); branch {branch} kept" if why else f"{slug}: removed {wt}; branch {branch} kept")
    return rc


@_command(chat=True)
def cmd_accept_tip(profile: str, args) -> int:
    """Record the head of the pack branch of `slug` as its landed tip: for a branch that moved above or away from the tip
    (an owner fixup, an amended landed commit), which `done` and `close-pack` would refuse for ever."""
    pack = _get_pack(profile, args.name)
    branch = (pack.get("branches") or {}).get(args.slug)
    if not branch:
        raise Refused(f"pack {args.name!r} has no repo {args.slug!r}")
    hub = st.hub(profile)
    checkout = _checkout(hub, args.slug, _repos(hub)[1])
    wt = _pack_wt(checkout, pack)
    if wt.exists() and not _clean(wt):
        raise Refused(f"pack worktree {wt} has uncommitted changes")
    if pack.get("state") != "closed" and (holder := _held(profile, pack, hub, st.workers(profile)).get(args.slug)):
        raise Refused(f"{holder} was started and is not landed, so it holds repo {args.slug!r}: land it, or give the task up "
                      f"with `at sup close-pack {args.name}` and accept the tip then")
    tip = _tip(checkout, branch)
    if not tip:
        raise Refused(f"{args.slug}: no branch {branch}")
    st.write_pack(profile, {**pack, "tips": {**(pack.get("tips") or {}), args.slug: tip}})
    st.touch(profile, f"accept-tip {args.name} {args.slug}")
    print(f"{args.slug}: landed tip is now {tip[:12]} on {branch}")
    return 0


@_command(chat=True)
def cmd_order(profile: str, args) -> int:
    pack = _get_pack(profile, args.name)
    started = _started_tasks(profile)
    fixed = [t for t in pack["tasks"] if t in started]
    open_ = [t for t in pack["tasks"] if t not in started]
    if sorted(args.tasks) != sorted(open_):
        raise ValueError(f"list exactly the tasks not started yet: {' '.join(open_) or '(none)'}")
    st.write_pack(profile, {**pack, "tasks": fixed + args.tasks})
    st.touch(profile, f"order {args.name} {' '.join(args.tasks)}")
    print(f"pack {args.name}: {' '.join(fixed + args.tasks)}")
    return 0


@_command(chat=True)
def cmd_cap(profile: str, args) -> int:
    if args.n not in CAP_RANGE:
        raise ValueError("cap must be 1..8")
    st.set_config(profile, cap=args.n)
    st.touch(profile, f"cap {args.n}")
    print(f"cap {args.n}")
    return 0


def _refusal(profile: str, task: str) -> str | None:
    """Why `task` may not start now, from state only (the caller holds the lock)."""
    pack = st.pack_of(profile, task)
    if pack is None:
        return f"{task} is in no pack"
    if pack.get("state") != "running":
        return f"pack {pack['name']!r} is {pack.get('state')}, not running"
    if any(w.get("task") == task for w in st.live_workers(profile)):
        return f"{task} already has a live worker"
    cap = st.config(profile)["cap"]
    if slots_used(profile) >= cap:
        return f"session cap {cap} reached"
    hub = _hub_or_none(profile)
    try:
        waits = _edges(profile, pack, hub).get(task)
    except Refused as e:
        return str(e)
    if waits:
        return f"{task} is blocked by {waits[0]}, which has not landed"
    held = _held(profile, pack, hub, st.workers(profile))
    for slug in sorted(_pack_repos(pack, hub, task)):
        if held.get(slug, task) != task:
            return f"{held[slug]} holds repo {slug!r} and has not landed"
    return None


def _not_ready(task: str, hub: Path, profile: str) -> str | None:
    try:
        ready = _run([_at(), "sup", "ready", task, "--hub", str(hub), "--profile", profile], cwd=hub,
                     env=clean_env(AGENTS_SUPERVISOR=profile))
    except (OSError, subprocess.SubprocessError) as e:
        return f"cannot run `at sup ready`: {e}"
    if ready.returncode != 0:
        lines = (ready.stdout + ready.stderr).strip().splitlines()
        return f"{task} is not ready: {lines[0] if lines else 'at sup ready failed'}"
    return None


def _existing_worktree(task: str, hub: Path) -> str | None:
    """The worktree already on branch task/<ID> (an earlier start that failed), else None."""
    try:
        out = _run(["git", "-C", str(hub), "worktree", "list", "--porcelain"], env=clean_env())
    except (OSError, subprocess.SubprocessError):
        return None
    path = None
    for line in out.stdout.splitlines():
        if line.startswith("worktree "):
            path = line[9:]
        elif line == f"branch refs/heads/task/{task}" and path and os.path.isdir(path):
            return path
    return None


def _worktree(task: str, hub: Path, profile: str) -> str:
    reuse = _existing_worktree(task, hub)
    if reuse:
        return reuse
    try:
        out = _run([_at(), "sup", "worktree", task, "--hub", str(hub), "--profile", profile], cwd=hub,
                   env=clean_env(AGENTS_SUPERVISOR=profile))
    except (OSError, subprocess.SubprocessError) as e:
        raise Refused(f"cannot run `at sup worktree`: {e}") from None
    lines = out.stdout.strip().splitlines()
    if out.returncode != 0 or not lines or not Path(lines[-1]).is_dir():
        raise Refused(f"no worktree for {task}: {(out.stderr.strip().splitlines() or lines or ['failed'])[-1]}")
    return lines[-1]


def wait_gone(session: str) -> bool:
    """True once `claude agents` lists no live process for the session; `claude stop` returns before it exits."""
    for i in range(GONE_TRIES):
        found = agents()
        if found is not None and not any(r.get("sessionId") == session and r.get("pid") is not None for r in found):
            return True
        if i < GONE_TRIES - 1:
            time.sleep(POLL_DELAY)
    return False


RESUME_SAID: list[str] = []  # the last line claude printed on a failed resume_bg, for the caller's message


def resume_bg(session: str, text: str, dirs: list[str], env: dict, cwd) -> bool:
    """`claude --bg --resume`: True only when that session woke. When it was still up, claude starts a copy under a new
    id and name instead; the copy is stopped at once, so it never runs untracked beside the worker. One attempt: the
    caller retries (the watcher on its next pass, `delegate` in its own loop)."""
    RESUME_SAID.clear()
    out = _run([_claude(), "--bg", "--resume", session, text, *dirs], env=env, cwd=cwd)
    said = out.stdout + out.stderr
    copy = COPY.search(said)
    if copy:
        _stop_session(copy.group(1))
        RESUME_SAID.append(f"claude started a copy {copy.group(1)} instead (stopped)")
        return False
    if out.returncode == 0 and f"woke session {session[:8]}" in said:
        return True
    RESUME_SAID.append((said.strip().splitlines() or ["no output"])[-1])
    return False


def _stop_session(session: str) -> None:
    try:
        _run([_claude(), "stop", session[:8]], env=clean_env())
    except (OSError, subprocess.SubprocessError):
        pass


def _bg_session(profile: str, task: str, cwd: str, env: dict, prompt: str, dirs: list[str]) -> str:
    """Start a bg worker and return its session id. `claude --bg` picks the id itself (it ignores --session-id), so
    the short id comes from its `backgrounded · <id> · <name>` line and the full one from `claude agents`."""
    name = f"{profile}-{task}"
    try:
        proc = subprocess.run([_claude(), "--bg", "--name", name, *session_flags(), prompt, *dirs],
                              cwd=cwd, env=env, capture_output=True, text=True, timeout=120, start_new_session=True,
                              stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as e:
        raise Refused(f"cannot start claude: {e}") from None
    if proc.returncode != 0:
        tail = (proc.stderr.strip() or proc.stdout.strip()).splitlines()
        raise Refused(f"claude --bg failed: {tail[-1] if tail else 'no output'}")
    m = re.search(r"^backgrounded \u00b7 ([0-9a-f]{8}) \u00b7", proc.stdout, re.M)
    if not m:
        raise Refused(f"started {name} but `claude --bg` printed no session id; check `claude agents`")
    short = m.group(1)
    for i in range(POLL_TRIES):
        rows = agents()
        for r in rows or []:
            sid = r.get("sessionId")
            if isinstance(sid, str) and sid.startswith(short):
                return sid
        if i < POLL_TRIES - 1:
            time.sleep(POLL_DELAY)
    _stop_session(short)
    raise Refused(f"started {name} ({short}) but it is not in `claude agents`; stopped it")


def _headless_session(profile: str, task: str, session: str, cwd: str, env: dict, prompt: str, dirs: list[str]) -> int | None:
    logs = st.profile_dir(profile) / "logs"
    logs.mkdir(exist_ok=True)
    try:
        with open(logs / f"{task}.json", "w", encoding="utf-8") as out:
            proc = subprocess.Popen([_claude(), "-p", "--session-id", session, *session_flags(),
                                     "--output-format", "json", prompt, *dirs],
                                    cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                                    start_new_session=True)
    except OSError as e:
        raise Refused(f"cannot start claude: {e}") from None
    return proc.pid


def _write_map(hub: Path, cwd: Path, pack: dict) -> None:
    """Write .local/repos.map in the task worktree: pack repos at their pack worktree, the rest as the hub has them.
    A pack without branches writes nothing; a symbolic link at .local or the map is refused."""
    if not pack.get("branches"):
        return
    _, mp = _repos(hub)
    mine = {slug: str(_pack_wt(_checkout(hub, slug, mp), pack)) for slug in pack["branches"]}
    local = cwd / ".local"
    if local.is_symlink() or (local / "repos.map").is_symlink():
        raise Refused(f"{local} or its repos.map is a symbolic link; not writing the map")
    try:
        local.mkdir(exist_ok=True)
        (local / "repos.map").write_text("# written by `at sup start-worker`: pack repos at their pack worktree\n"
                                         + "".join(f"{s}: {p}\n" for s, p in {**mp, **mine}.items()), encoding="utf-8")
    except OSError as e:
        raise Refused(f"cannot write {local / 'repos.map'}: {e}") from None


def _add_dirs(profile: str, hub: Path | None, cwd) -> list[str]:
    """`--add-dir <hub path>` for each `local` entry linked in the worktree `cwd` (the hub directory of a `/` entry, the parent
    of a file): a session may not write through a link that leaves its working directories. The flag takes several values, so
    callers put it after the prompt. A file at the hub root adds nothing (its parent is the whole hub): the worker reads the
    link, it cannot write through it. [] without linked entries; a `local` that cannot be read is said on stderr."""
    try:
        entries = st.profile_local(profile, hub, check=False) if hub else []
    except ValueError as e:
        print(f"sup: {profile}: local entries unreadable, session started without --add-dir: {e}", file=sys.stderr)
        return []
    dirs = []
    for e in entries:
        src, dst = hub / e.rstrip("/"), Path(cwd) / e.rstrip("/")
        try:
            linked = dst.is_symlink() and dst.resolve() == src.resolve()
        except (OSError, RuntimeError):
            linked = False
        d = str(src if e.endswith("/") else src.parent)
        own = Path(d).relative_to(hub).parts[:1] in ((), (".claude",), (".git",))  # the hub itself, its agent settings, its git
        if linked and not own and d not in dirs:
            dirs.append(d)
    return ["--add-dir", *dirs] if dirs else []


def _link_local(profile: str, hub: Path, cwd: Path) -> list[str]:
    """Link each `local` path of the profile from the task worktree to the hub; a restart leaves a correct link alone and
    anything else at the path is refused. Returns the entries skipped (missing in the hub, no trailing `/`)."""
    try:
        entries = st.profile_local(profile, hub, check=False)  # the worktree's git decides below, not the hub's
    except ValueError as e:
        raise Refused(str(e)) from None
    skipped, top = [], cwd.resolve()
    for e in entries:
        body = e.rstrip("/")
        src, dst = hub / body, cwd / body
        if not os.path.lexists(src) and not e.endswith("/"):
            skipped.append(e); continue
        try:
            if dst.is_symlink() and dst.resolve() == src.resolve():
                continue
        except RuntimeError:  # a symbolic link loop
            raise Refused(f"{dst} is a symbolic link loop") from None
        if os.path.lexists(dst):
            raise Refused(f"{dst} exists and is not the link to {src}")
        if not Path(os.path.realpath(dst.parent)).is_relative_to(top):  # a tracked symlinked directory could redirect it
            raise Refused(f"{dst} would lie outside {top}")
        if (ign := _git(cwd, "check-ignore", "-q", "--", body)).returncode > 1:
            raise Refused(f"git check-ignore {body} in {cwd}: {(ign.stderr.strip().splitlines() or ['failed'])[-1]}")
        if ign.returncode:  # the link must not be committable into the hub
            raise Refused(f"git does not ignore {body} in {cwd}: write `{body}` (no trailing /: it is a link there) in .gitignore on the branch the task starts from")
        try:
            (src if e.endswith("/") else src.parent).mkdir(parents=True, exist_ok=True)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.symlink_to(src)
        except OSError as x:
            raise Refused(f"cannot link {dst}: {x}") from None
    return skipped


@_command(lock=False)
def cmd_start_worker(profile: str, args) -> int:
    """Under the lock: check and write a `starting` row (it counts against the cap, so a second start cannot pass).
    Outside it: `at` and `claude`. Under it again: `running` and the `started` event. A failed start removes the row."""
    task, session = args.task, str(uuid.uuid4())
    headless = args.headless or st.config(profile).get("worker_mode") == "headless"
    mode = "headless" if headless else "bg"
    with st.locked(profile):
        why = _refusal(profile, task)
        if why:
            raise Refused(why)
        pack = st.pack_of(profile, task)
        for old in [w for w in st.workers(profile) if w.get("task") == task]:
            st.drop_worker(profile, old["session"])
        st.set_worker(profile, session, task=task, pack=pack["name"], cwd=None, mode=mode, state="starting", started=st.now())
    try:
        try:
            hub = st.hub(profile, getattr(args, "hub", None))
        except ValueError as e:
            raise Refused(str(e)) from None
        why = _not_ready(task, hub, profile)
        if why:
            raise Refused(why)
        cwd = _worktree(task, hub, profile)
        _write_map(hub, Path(cwd), pack)
        for e in _link_local(profile, hub, Path(cwd)):
            print(f"local {e}: not in the hub, skipped")
        for e in st.profile_local(profile, hub, check=False):
            if "/" not in e.rstrip("/") and not e.endswith("/") and (Path(cwd) / e).is_symlink():
                print(f"{e}: linked, not writable by the worker: a file at the hub root; put it in a directory to make it writable")
        env = clean_env(AGENTS_SUPERVISOR=profile, AGENTS_SUP_TASK=task)
        prompt = WORKER_PROMPT.format(task=task, profile=profile)
        dirs = _add_dirs(profile, hub, cwd)
        pid = _headless_session(profile, task, session, cwd, env, prompt, dirs) if headless else None
        real = session if headless else _bg_session(profile, task, cwd, env, prompt, dirs)
        with st.locked(profile):
            if real != session:  # re-key the `starting` row under the id claude chose
                row = st.worker_for(profile, session=session) or {}
                st.drop_worker(profile, session)
                st.set_worker(profile, real, **{k: v for k, v in row.items() if k != "session"})
                session = real
            st.set_worker(profile, session, cwd=cwd, state="running", **({"pid": pid} if pid else {}))
            st.emit(profile, "started", task=task, session=session, mode=mode)
    except BaseException:
        with st.locked(profile):
            st.drop_worker(profile, session)
        raise
    print(f"started {task} {session}")
    return 0


def _owner_here() -> bool:
    """True at a plain shell or in the chat that holds a valid token; a record, not proof (see the module docstring)."""
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if sid is None:
        return not os.environ.get("AGENTS_SUPERVISOR")  # a process the supervisor started is not the owner at a shell
    import sup_guard
    return bool(sup_guard.check_chat_token(sid))


@_command(lock=False)
def cmd_stop_worker(profile: str, args) -> int:
    """Mark the row `stopped` first (so the watcher never reads the stop as a death), then stop the session; on a
    failed stop put the row back."""
    owner = _owner_here()
    with st.locked(profile):
        row = st.worker_for(profile, task=args.task)
        if row is None or row.get("state") not in ("running", "waiting"):
            raise Refused(f"{args.task} has no live worker")
        session, before = row["session"], {k: row.get(k) for k in ("state", "waiting_for", "stopped_by")}
        st.set_worker(profile, session, state="stopped", waiting_for=None, stopped_by="owner" if owner else "sup")
    try:
        if not _session_ok(session):
            raise Refused(f"the row of {args.task} has no valid session id")
        if row.get("mode") == "headless":
            if _pid_exists(row.get("pid")):
                os.kill(row["pid"], signal.SIGTERM)
        elif _run([_claude(), "stop", session[:8]], env=clean_env()).returncode != 0:
            raise Refused(f"claude stop {session[:8]} failed")
    except BaseException:
        with st.locked(profile):
            st.set_worker(profile, session, **before)
        raise
    with st.locked(profile):
        st.touch(profile, f"stop-worker {args.task}" if owner else f"sup: stop-worker {args.task}")
    print(f"stopped {args.task} {session}")
    return 0


@_command(lock=False)
def cmd_reap(profile: str, args) -> int:
    found = agents()
    if found is None:
        raise Refused("`claude agents` failed: nothing reaped")
    acts = reap(profile, found, dry=args.dry_run)
    print("\n".join(acts) if acts else "no orphan sessions")
    return 0


def register(sup_sub) -> None:
    def add(name, func, *pos, flags=()):
        p = sup_sub.add_parser(name)
        p.add_argument("--profile")
        for arg, kw in pos:
            p.add_argument(arg, **kw)
        for flag, kw in flags:
            p.add_argument(flag, **kw)
        p.set_defaults(func=func)

    name = ("name", {})
    tasks = ("tasks", {"nargs": "+", "metavar": "TASK-ID"})
    add("pack", cmd_pack, name, tasks, flags=[("--parallel", {"action": "store_true"}),
                                              ("--branch", {"action": "append", "metavar": "SLUG=BRANCH"})])
    add("packs", cmd_packs)
    for cmd, fn in (("start-pack", cmd_start_pack), ("pause-pack", cmd_pause_pack), ("close-pack", cmd_close_pack)):
        add(cmd, fn, name)
    add("accept-tip", cmd_accept_tip, name, ("slug", {}))
    add("order", cmd_order, name, tasks)
    add("cap", cmd_cap, ("n", {"type": int}))
    add("start-worker", cmd_start_worker, ("task", {"metavar": "TASK-ID"}),
        flags=[("--headless", {"action": "store_true"}), ("--hub", {"help": "hub (default: the profile's, else the cwd's git toplevel)"})])
    add("stop-worker", cmd_stop_worker, ("task", {"metavar": "TASK-ID"}))
    add("reap", cmd_reap, flags=[("--dry-run", {"action": "store_true"})])
