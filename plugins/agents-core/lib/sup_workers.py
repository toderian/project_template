"""Packs and worker sessions of `at sup`: pack commands, start-worker, stop-worker, and the helpers other lanes call.

Commands (all take --profile, default $AGENTS_SUPERVISOR; exit 0 ok, 2 usage, 3 refused):
  pack <name> <TASK-ID>... [--parallel]   create, or replace while the pack is `new`
  packs | start-pack | pause-pack | close-pack <name> | order <name> <TASK-ID>... | cap <n>
  start-worker <TASK-ID> [--headless] [--hub <path>] | stop-worker <TASK-ID>
pack, start-pack, pause-pack, close-pack, order and cap are chat-only (sup_ask.require_chat).

Locking: state is read and written under `sup_state.locked(profile)`, but start-worker and stop-worker release it
before every `at` or `claude` subprocess. The helpers below never take it and never write state:
  wake(profile, session, text) -> bool       `claude stop`, then `claude --bg --resume`; True when the resume exits 0
                                             (the caller then sets the row `running`)
  next_tasks(profile) -> list[str]           tasks that may start now: pack running, no worker row, not landed, under the cap;
                                             a serial pack offers its first open task, and only when none of its tasks is live
  is_alive(row) -> bool                      bg: a `claude agents --json --all` row with the sessionId and a non-null pid;
                                             headless: the pid of `headless-<pid>` exists

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
from pathlib import Path

import sup_state as st

WORKER_PROMPT = (
    "Execute task {task} with agents-core:execute-plan as an unattended run. You are supervised by profile {profile}. "
    "For a decision outside your authority run `at sup ask`; for a shared resource run `at sup need`; then end your "
    "turn with the line `WAITING supervisor: <id>`. Never ask the user. Close the task out with "
    "agents-tasks:complete-task. Do not push and do not merge."
)
STARTED = re.compile(r"backgrounded\s*·\s*(\S+)\s*·\s*(\S+)")
CAP_RANGE = range(1, 9)


class Refused(Exception):
    pass


def _claude() -> str:
    return os.environ.get("AGENTS_CLAUDE_BIN", "claude")


def _at() -> str:
    return os.environ.get("AGENTS_AT_BIN", "at")


def _run(argv: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, timeout=kw.pop("timeout", 60), **kw)


def _agents() -> list[dict]:
    try:
        out = _run([_claude(), "agents", "--json", "--all"])
        rows = json.loads(out.stdout) if out.returncode == 0 else []
    except (OSError, ValueError, subprocess.SubprocessError):
        return []
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def _pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True
    return True


def is_alive(row: dict) -> bool:
    session = str(row.get("session", ""))
    if row.get("mode") == "headless" or session.startswith("headless-"):
        tail = session.rpartition("-")[2]
        return tail.isdigit() and _pid_exists(int(tail))
    return any(r.get("sessionId") == session and r.get("pid") is not None for r in _agents())


def wake(profile: str, session: str, text: str) -> bool:
    row = st.worker_for(profile, session=session)
    if row is not None and row.get("mode") == "headless":
        return False
    try:
        _run([_claude(), "stop", session[:8]])
        return _run([_claude(), "--bg", "--resume", session, text]).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _landed(profile: str) -> set[str]:
    return {e["task"] for e in st.events_since(profile, 0) if e.get("kind") == "landed" and e.get("task")}


def next_tasks(profile: str) -> list[str]:
    rows = st.workers(profile)
    landed = _landed(profile)
    free = st.config(profile)["cap"] - len(st.live_workers(profile))
    out: list[str] = []
    for pack in st.list_packs(profile):
        if pack.get("state") != "running":
            continue
        for task in pack["tasks"]:
            row = next((w for w in rows if w.get("task") == task), None)
            if task in landed or (row and row.get("state") == "done"):
                continue
            if row:
                if not pack.get("parallel"):
                    break
                continue
            out.append(task)
            if not pack.get("parallel"):
                break
    return out[:max(free, 0)]


def _need_profile(args) -> str:
    try:
        profile = st.current_profile(args.profile)
    except ValueError as e:
        raise SystemExit(f"at: sup: {e}") from None
    if not profile:
        print("at: sup: no profile: pass --profile or set AGENTS_SUPERVISOR", file=sys.stderr)
        raise SystemExit(2)
    return profile


def _command(fn=None, *, chat: bool = False, lock: bool = True):
    """Wrap a command: profile, chat check, the lock around the whole command when `lock` (else fn locks itself)."""
    if fn is None:
        return lambda f: _command(f, chat=chat, lock=lock)

    def run(args) -> int:
        profile = _need_profile(args)
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


@_command
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
    if any(w.get("task") == task for w in st.live_workers(profile)):
        return f"{task} already has a live worker"
    cap = st.config(profile)["cap"]
    if len(st.live_workers(profile)) >= cap:
        return f"session cap {cap} reached"
    return None


def _not_ready(task: str, hub: Path, profile: str) -> str | None:
    try:
        ready = _run([_at(), "sup", "ready", task, "--hub", str(hub), "--profile", profile], cwd=hub)
    except (OSError, subprocess.SubprocessError) as e:
        return f"cannot run `at sup ready`: {e}"
    if ready.returncode != 0:
        lines = (ready.stdout + ready.stderr).strip().splitlines()
        return f"{task} is not ready: {lines[0] if lines else 'at sup ready failed'}"
    return None


def _worktree(task: str, hub: Path, profile: str) -> str:
    try:
        out = _run([_at(), "sup", "worktree", task, "--hub", str(hub), "--profile", profile], cwd=hub)
    except (OSError, subprocess.SubprocessError) as e:
        raise Refused(f"cannot run `at sup worktree`: {e}") from None
    lines = out.stdout.strip().splitlines()
    if out.returncode != 0 or not lines or not Path(lines[-1]).is_dir():
        raise Refused(f"no worktree for {task}: {(out.stderr.strip().splitlines() or lines or ['failed'])[-1]}")
    return lines[-1]


def _bg_session(profile: str, task: str, cwd: str, env: dict, prompt: str) -> str:
    name = f"{profile}-{task}"
    try:
        proc = subprocess.run([_claude(), "--bg", "--name", name, "--permission-mode", "auto", prompt], cwd=cwd, env=env,
                              capture_output=True, text=True, timeout=120, start_new_session=True)
    except (OSError, subprocess.SubprocessError) as e:
        raise Refused(f"cannot start claude: {e}") from None
    found = STARTED.search(proc.stdout)
    if proc.returncode != 0 or not found:
        tail = (proc.stderr.strip() or proc.stdout.strip()).splitlines()
        raise Refused(f"claude --bg failed: {tail[-1] if tail else 'no output'}")
    short = found.group(1)
    rows = [r for r in _agents() if r.get("name") == name and str(r.get("sessionId", "")).startswith(short)]
    if not rows:
        raise Refused(f"started {name} ({short}) but its session id is not in `claude agents`")
    return rows[0]["sessionId"]


def _headless_session(profile: str, task: str, cwd: str, env: dict, prompt: str) -> str:
    logs = st.profile_dir(profile) / "logs"
    logs.mkdir(exist_ok=True)
    try:
        with open(logs / f"{task}.json", "w", encoding="utf-8") as out:
            proc = subprocess.Popen([_claude(), "-p", "--permission-mode", "auto", "--output-format", "json", prompt],
                                    cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                                    start_new_session=True)
    except OSError as e:
        raise Refused(f"cannot start claude: {e}") from None
    return f"headless-{proc.pid}"


@_command(lock=False)
def cmd_start_worker(profile: str, args) -> int:
    """Check under the lock, run `at` and `claude` outside it, record the row under it again.
    simplicity: two start-workers for one task are stopped by `at sup worktree` refusing an existing branch;
    revisit when a second starter exists besides the watcher."""
    task = args.task
    with st.locked(profile):
        why = _refusal(profile, task)
    if why:
        raise Refused(why)
    try:
        hub = st.hub(profile, args.hub)
    except ValueError as e:
        raise Refused(str(e)) from None
    why = _not_ready(task, hub, profile)
    if why:
        raise Refused(why)
    cwd = _worktree(task, hub, profile)
    env = {**os.environ, "AGENTS_SUPERVISOR": profile, "AGENTS_SUP_TASK": task}
    env.pop("AGENTS_SUP_CHAT_TOKEN", None)
    prompt = WORKER_PROMPT.format(task=task, profile=profile)
    start = _headless_session if args.headless else _bg_session
    session = start(profile, task, cwd, env, prompt)
    mode = "headless" if args.headless else "bg"
    with st.locked(profile):
        pack = st.pack_of(profile, task)
        for old in [w for w in st.workers(profile) if w.get("task") == task]:
            st.drop_worker(profile, old["session"])
        st.set_worker(profile, session, task=task, pack=pack["name"] if pack else None, cwd=cwd, mode=mode,
                      state="running", started=st.now())
        st.emit(profile, "started", task=task, session=session, mode=mode)
    print(f"started {task} {session}")
    return 0


@_command(lock=False)
def cmd_stop_worker(profile: str, args) -> int:
    with st.locked(profile):
        row = st.worker_for(profile, task=args.task)
    if row is None or row.get("state") not in ("running", "waiting"):
        raise Refused(f"{args.task} has no live worker")
    session = row["session"]
    if row.get("mode") == "headless":
        pid = int(session.rpartition("-")[2])
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
    elif _run([_claude(), "stop", session[:8]]).returncode != 0:
        raise Refused(f"claude stop {session[:8]} failed")
    with st.locked(profile):
        st.set_worker(profile, session, state="stopped", waiting_for=None)
        st.touch(profile, f"stop-worker {args.task}")
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
