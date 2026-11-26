"""Packs and worker sessions of `at sup`: pack commands, start-worker, stop-worker, and the helpers other lanes call.

Commands (all take --profile, default $AGENTS_SUPERVISOR; exit 0 ok, 2 usage, 3 refused):
  pack <name> <TASK-ID>... [--parallel]   create, or replace while the pack is `new`
  packs | start-pack | pause-pack | close-pack <name> | order <name> <TASK-ID>... | cap <n>
  start-worker <TASK-ID> [--headless] [--hub <path>] | stop-worker <TASK-ID>
pack, start-pack, pause-pack, close-pack, order and cap are chat-only (sup_ask.require_chat). Every command except `packs`
refuses (exit 3) in a worker session (AGENTS_SUP_TASK set): an honest-mistake check, not a fence, because a worker runs
under the same uid as the state directory.

Sessions: both modes start with `--session-id <uuid4>`, and the full uuid is the registry key. start-worker writes a row
in state `starting` under the first lock (it counts against the cap and shuts out a second start of the task), then
becomes `running`; a failed start removes the row. An existing task worktree with no live row is reused.
Locking: state is read and written under `sup_state.locked(profile)`, but start-worker and stop-worker release it
before every `at` or `claude` subprocess. The helpers below never take it and never write state:
  agents() -> list|None                      the rows of `claude agents --json --all`; None on any error
  is_alive(row, agents) -> bool|None         bg: a row with the sessionId and a non-null pid (None: `agents` failed, cannot
                                             tell); headless: the row's pid exists (a waiting headless worker has no process)
  wake_due(profile, row) -> (text, key)|None what to say when waking the row now, None when it must not be woken
  wake(profile, session, text) -> bool       `claude stop` (or already stopped), then `claude --bg --resume` (headless:
                                             `claude -p --resume`) in the row's cwd with AGENTS_SUPERVISOR and AGENTS_SUP_TASK;
                                             True only when the resume says it woke that session
  next_tasks(profile) -> list[str]           tasks that may start now: pack running, no worker row, not landed, under the
                                             cap (live rows and rows due for a wake count); a serial pack offers its first
                                             open task, and only when the previous one is landed
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
from pathlib import Path

import sup_state as st

WORKER_PROMPT = (
    "Execute task {task} with agents-core:execute-plan as an unattended run. You are supervised by profile {profile}. "
    "For a decision outside your authority run `at sup ask`. For a shared resource run `at sup need <resource> "
    "--minutes <n>` (--minutes is required) and `at sup release <resource>` as soon as you are done with it. Then end "
    "your turn with the line `WAITING supervisor: <id>`. When you are woken, read your answers with `at sup inbox` and "
    "acknowledge each one with `at sup inbox --ack <id>`. Never ask the user. Close the task out with "
    "agents-tasks:complete-task. Do not push and do not merge."
)
CAP_RANGE = range(1, 9)
WAKE_TRIES = 3
DEAD_RESTARTS = 2
STARTING_TTL = 300.0
POLL_TRIES, POLL_DELAY = 6, 0.5
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
           if not k.startswith("GIT_CONFIG_") and k not in ("AGENTS_SUP_CHAT_TOKEN", "AGENTS_SUP_TASK", "AGENTS_SUP_ORIG_PATH")}
    if os.environ.get("AGENTS_SUP_ORIG_PATH"):
        env["PATH"] = os.environ["AGENTS_SUP_ORIG_PATH"]
    env.update(extra)
    return env


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


def _pack_blocked(profile: str, task: str) -> bool:
    pack = st.pack_of(profile, task)
    return bool(pack) and pack.get("state") in ("paused", "closed")


def wake_due(profile: str, row: dict):
    """(text, key) when the watcher should wake this row now: an unread answer or a pending restart, and the row is not
    owner-stopped, its pack is not paused or closed, and the failures for this cause are under WAKE_TRIES."""
    task = row.get("task")
    if row.get("state") not in ("stopped", "waiting") or not task or row.get("stopped_by") == "owner":
        return None
    unread = st.inbox(profile, task, unread_only=True)
    if not unread and not row.get("restart_pending"):
        return None
    if _pack_blocked(profile, task):
        return None
    key = unread[-1]["id"] if unread else "restart"
    if row.get("wake_key") == key and row.get("wake_fail", 0) >= WAKE_TRIES:
        return None
    return (ANSWER_TEXT if unread else RESTART_TEXT).format(task=task), key


def _session_ok(session) -> bool:
    return isinstance(session, str) and bool(st.SESSION.match(session))


def wake(profile: str, session: str, text: str) -> bool:
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
            with open(logs / f"{row['task']}.json", "a", encoding="utf-8") as out:
                subprocess.Popen([_claude(), "-p", "--resume", session, text], cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                 stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
            return True
        if _run([_claude(), "stop", session[:8]], env=env, cwd=cwd).returncode != 0:
            found = agents()
            if found is None or any(r.get("sessionId") == session and r.get("pid") is not None for r in found):
                return False  # the stop failed and the session may still run: a resume would start a copy
        out = _run([_claude(), "--bg", "--resume", session, text], env=env, cwd=cwd)
        return out.returncode == 0 and f"woke session {session[:8]}" in out.stdout
    except (OSError, subprocess.SubprocessError):
        return False


def _landed(profile: str, task: str, hub) -> bool:
    if hub is None:
        return any(e.get("kind") == "landed" and e.get("task") == task for e in st.events_since(profile, 0))
    return st.landed(profile, task, hub)


def _hub_or_none(profile: str):
    try:
        return st.hub(profile)
    except ValueError:
        return None


def next_tasks(profile: str) -> list[str]:
    rows = st.workers(profile)
    hub = _hub_or_none(profile)
    waking = sum(1 for w in rows if w.get("state") == "stopped" and wake_due(profile, w))
    free = st.config(profile)["cap"] - len(st.live_workers(profile)) - waking
    out: list[str] = []
    for pack in st.list_packs(profile):
        if pack.get("state") != "running":
            continue
        for task in pack["tasks"]:
            if _landed(profile, task, hub):
                continue
            if any(w.get("task") == task for w in rows):
                if not pack.get("parallel"):
                    break  # the previous task is not landed yet: a serial pack waits
                continue
            out.append(task)
            if not pack.get("parallel"):
                break
    return out[:max(free, 0)]


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
        if guard and os.environ.get("AGENTS_SUP_TASK"):
            print("at: sup: this command is for the supervisor and the owner, not for a worker session", file=sys.stderr)
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


@_command(chat=True)
def cmd_pack(profile: str, args) -> int:
    old = st.read_pack(profile, args.name)
    if old and old.get("state") != "new":
        raise Refused(f"pack {args.name!r} is {old['state']}; only a new pack can be replaced")
    if len(set(args.tasks)) != len(args.tasks):
        raise ValueError("a task is listed twice")
    for task in args.tasks:
        other = st.pack_of(profile, task)
        if other and other["name"] != args.name:
            raise Refused(f"{task} is already in pack {other['name']!r}")
    st.write_pack(profile, {"name": args.name, "tasks": args.tasks, "parallel": args.parallel, "state": "new"})
    st.touch(profile, f"pack {args.name} {' '.join(args.tasks)}{' --parallel' if args.parallel else ''}")
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


@_command(chat=True)
def cmd_start_pack(profile: str, args) -> int:
    return _set_state(profile, args.name, "running", ("new", "paused", "running"), "start")


@_command(chat=True)
def cmd_pause_pack(profile: str, args) -> int:
    return _set_state(profile, args.name, "paused", ("running", "paused"), "pause")


@_command(chat=True)
def cmd_close_pack(profile: str, args) -> int:
    return _set_state(profile, args.name, "closed", ("new", "running", "paused", "closed"), "close")


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
    live = st.live_workers(profile)
    if any(w.get("task") == task for w in live):
        return f"{task} already has a live worker"
    cap = st.config(profile)["cap"]
    if len(live) >= cap:
        return f"session cap {cap} reached"
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


def _stop_session(session: str) -> None:
    try:
        _run([_claude(), "stop", session[:8]], env=clean_env())
    except (OSError, subprocess.SubprocessError):
        pass


def _bg_session(profile: str, task: str, session: str, cwd: str, env: dict, prompt: str) -> int | None:
    name = f"{profile}-{task}"
    try:
        proc = subprocess.run([_claude(), "--bg", "--session-id", session, "--name", name, "--permission-mode", "auto", prompt],
                              cwd=cwd, env=env, capture_output=True, text=True, timeout=120, start_new_session=True,
                              stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as e:
        _stop_session(session)
        raise Refused(f"cannot start claude: {e}") from None
    if proc.returncode != 0:
        tail = (proc.stderr.strip() or proc.stdout.strip()).splitlines()
        raise Refused(f"claude --bg failed: {tail[-1] if tail else 'no output'}")
    for i in range(POLL_TRIES):
        rows = agents()
        if rows is not None and any(r.get("sessionId") == session for r in rows):
            return None
        if i < POLL_TRIES - 1:
            time.sleep(POLL_DELAY)
    _stop_session(session)
    raise Refused(f"started {name} ({session[:8]}) but it is not in `claude agents`; stopped it")


def _headless_session(profile: str, task: str, session: str, cwd: str, env: dict, prompt: str) -> int | None:
    logs = st.profile_dir(profile) / "logs"
    logs.mkdir(exist_ok=True)
    try:
        with open(logs / f"{task}.json", "w", encoding="utf-8") as out:
            proc = subprocess.Popen([_claude(), "-p", "--session-id", session, "--permission-mode", "auto",
                                     "--output-format", "json", prompt],
                                    cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                                    start_new_session=True)
    except OSError as e:
        raise Refused(f"cannot start claude: {e}") from None
    return proc.pid


@_command(lock=False)
def cmd_start_worker(profile: str, args) -> int:
    """Under the lock: check and write a `starting` row (it counts against the cap, so a second start cannot pass).
    Outside it: `at` and `claude`. Under it again: `running` and the `started` event. A failed start removes the row."""
    task, session = args.task, str(uuid.uuid4())
    mode = "headless" if args.headless else "bg"
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
        env = clean_env(AGENTS_SUPERVISOR=profile, AGENTS_SUP_TASK=task)
        prompt = WORKER_PROMPT.format(task=task, profile=profile)
        pid = (_headless_session if args.headless else _bg_session)(profile, task, session, cwd, env, prompt)
        with st.locked(profile):
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
    add("pack", cmd_pack, name, tasks, flags=[("--parallel", {"action": "store_true"})])
    add("packs", cmd_packs)
    for cmd, fn in (("start-pack", cmd_start_pack), ("pause-pack", cmd_pause_pack), ("close-pack", cmd_close_pack)):
        add(cmd, fn, name)
    add("order", cmd_order, name, tasks)
    add("cap", cmd_cap, ("n", {"type": int}))
    add("start-worker", cmd_start_worker, ("task", {"metavar": "TASK-ID"}),
        flags=[("--headless", {"action": "store_true"}), ("--hub", {"help": "hub (default: the profile's, else the cwd's git toplevel)"})])
    add("stop-worker", cmd_stop_worker, ("task", {"metavar": "TASK-ID"}))
