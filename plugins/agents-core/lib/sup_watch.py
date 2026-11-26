"""`at sup watch`: the detached watcher of one supervisor profile. No LLM in it.

  at sup watch start [--interval S] [--no-tick]   fork a detached watcher; refused while one is alive (exit 3)
  at sup watch stop | status                      status exits 0 when running, 3 when not
  at sup watch once [--no-tick]                   one pass in the foreground; prints the actions taken

Files in the profile directory: watch.pid ("<pid> <start time>"), watch.log, watch.json (what was already
emitted, so each notice is sent once), tick.pid (written by the running tick only; the watcher reads it, and emits
`tick_failed` when a tick exits non-zero). `watch start` and `watch stop` are chat-only (sup_ask.require_chat). One pass is `step(profile, hub)`, in order:
liveness, leases, answers, free resources, starts, landing, notices, tick. Every change of supervisor state takes
`sup_state.locked` briefly; external programs (`at`, `sup_workers`) run outside it, because they lock themselves.
Policy: a dead worker is woken with a restart text up to sup_workers.DEAD_RESTARTS times before `dead` is final; a bad
`claude agents` answer never declares anyone dead; paused and closed packs get no start, wake or landing; an owner-stopped
row is never woken; a refused start is retried only when the owner touches or the pack file changes, a refused landing only
when task/<ID> has a new tip or the owner touches; `dead`, `start_refused`, `land_refused`, `owed`, `overdue`,
`ticks_paused` and a BLOCKED or GAVE_UP stop add a non-blocking queue entry (source `watcher`) and run `at notify`.
`sup_workers` (is_alive, wake, next_tasks) is imported inside the functions. `at` is $AGENTS_AT_BIN. Every `at`
subprocess runs with cwd = the profile's hub (config key `hub`) and AGENTS_SUPERVISOR set, never with the chat token.
Exit codes: 0 ok, 2 usage, 3 refused. stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

import lease
import sup_state

TICK_TIMEOUT = 600.0
TICK_TRIES = 3
STOP = False


def _at() -> str:
    return os.environ.get("AGENTS_AT_BIN", "at")


def _workers():
    import sup_workers
    return sup_workers


def _log(profile: str, text: str) -> None:
    with open(sup_state.profile_dir(profile) / "watch.log", "a", encoding="utf-8") as fh:
        fh.write(f"{sup_state.now()} {text}\n")


def _memory(profile: str) -> dict:
    return sup_state.read_json(sup_state.profile_dir(profile) / "watch.json", {})


def _remember(profile: str, mem: dict) -> None:
    sup_state.write_json(sup_state.profile_dir(profile) / "watch.json", mem)


def _once(mem: dict, group: str, key: str) -> bool:
    """True the first time `key` is seen in `group`."""
    seen = mem.setdefault(group, [])
    if key in seen:
        return False
    seen.append(key)
    return True


def _emit(profile: str, kind: str, task=None, session=None, **data) -> None:
    with sup_state.locked(profile):
        sup_state.emit(profile, kind, task, session, **data)


def _env(profile: str) -> dict:
    return _workers().clean_env(AGENTS_SUPERVISOR=profile)


def _cwd(profile: str) -> str | None:
    hub = sup_state.config(profile).get("hub")
    return hub if hub and os.path.isdir(hub) else None


def _run_at(profile: str, args: list[str], timeout: float = 300, with_profile: bool = True) -> tuple[int, str]:
    """Run `at <args>` in the hub; returns (exit code, first line of the reason)."""
    try:
        p = subprocess.run([_at(), *args, *(["--profile", profile] if with_profile else [])], capture_output=True, text=True,
                           cwd=_cwd(profile), timeout=timeout, env=_env(profile), stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, f"{type(e).__name__}: {e}"
    reason = next((ln.strip() for ln in (p.stderr + p.stdout).splitlines() if ln.strip()), "")
    return p.returncode, reason[:300]


def _owner_touches(profile: str) -> int:
    """Lines of touch.log that are the owner's; a supervisor-run command writes `sup: ...` and is not counted."""
    try:
        lines = (sup_state.profile_dir(profile) / "touch.log").read_text(encoding="utf-8").splitlines()
    except OSError:
        return 0
    return sum(1 for ln in lines if not ln.partition("\t")[2].startswith("sup:"))


def _age(stamp: str) -> float:
    try:
        return time.time() - datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%S%z").timestamp()
    except (TypeError, ValueError):
        return 0.0


# ---- the pass --------------------------------------------------------------------------

def _liveness(profile: str, mem: dict, acts: list[str]) -> None:
    w = _workers()
    rows = sup_state.live_workers(profile)
    found = w.agents() if any(r.get("mode") != "headless" and r.get("state") != "starting" for r in rows) else None
    for row in rows:
        task, session = row.get("task"), row["session"]
        if row.get("state") == "starting":
            if _age(row.get("started")) > w.STARTING_TTL:  # a start-worker that died: no session was recorded
                with sup_state.locked(profile):
                    sup_state.drop_worker(profile, session)
                acts.append(f"start abandoned {task}")
            continue
        if w.is_alive(row, found) is not False:  # None: `claude agents` failed, so nobody is declared dead
            continue
        restarts = row.get("restarts", 0)
        with sup_state.locked(profile):
            if restarts < w.DEAD_RESTARTS:
                sup_state.set_worker(profile, session, state="stopped", restarts=restarts + 1, restart_pending=True)
            else:
                sup_state.set_worker(profile, session, state="stopped")
                sup_state.emit(profile, "dead", task, session)
        if restarts < w.DEAD_RESTARTS:
            acts.append(f"dead {task}, restart {restarts + 1}")
        else:
            mem.setdefault("dead", []).append(session)
            acts.append(f"dead {task}")


def _leases(profile: str, mem: dict, acts: list[str]) -> None:
    with lease.locked() as d:
        found = [(p.stem, *lease.read(d, p.stem)) for p in sorted(d.glob("*.json"))]
    for res, rec, state in found:
        if state not in ("overdue", "owed") or rec is None:
            continue
        if _once(mem, "leases", f"{res}:{state}:{rec.get('pid')}:{rec.get('start')}"):
            _emit(profile, state, rec.get("task"), rec.get("session"), resource=res)
            acts.append(f"{state} {res}")


def _answers(profile: str, mem: dict, acts: list[str]) -> None:
    w = _workers()
    for row in sup_state.workers(profile):
        due = w.wake_due(profile, row)
        if due is None:
            continue
        (text, key), task, session = due, row["task"], row["session"]
        with sup_state.locked(profile):  # claim a slot first: a wake never takes a slot a start has filled
            cur = sup_state.worker_for(profile, session=session)
            others = [x for x in sup_state.live_workers(profile) if x["session"] != session]
            if cur is None or cur.get("state") not in ("stopped", "waiting") or len(others) >= sup_state.config(profile)["cap"]:
                continue
            sup_state.set_worker(profile, session, state="starting", started=sup_state.now())
        ok = w.wake(profile, session, text)
        with sup_state.locked(profile):
            if ok:
                sup_state.set_worker(profile, session, state="running", waiting_for=None, restart_pending=False,
                                     wake_fail=0, wake_key=None)
                sup_state.emit(profile, "restarted", task, session)
            else:
                fails = (row.get("wake_fail", 0) if row.get("wake_key") == key else 0) + 1
                sup_state.set_worker(profile, session, state=cur["state"], started=cur.get("started"), wake_fail=fails,
                                     wake_key=key)
                if fails >= w.WAKE_TRIES:
                    sup_state.emit(profile, "dead", task, session, reason=f"wake failed {fails} times")
        if ok:
            acts.append(f"restarted {task}")
            continue
        acts.append(f"wake failed {task}")
        if fails >= w.WAKE_TRIES:
            acts.append(f"dead {task}")


def _free(profile: str, mem: dict, acts: list[str]) -> None:
    cfg = sup_state.config(profile)
    events = sup_state.events_since(profile, 0)
    for row in sup_state.workers(profile):
        res, task = row.get("waiting_for"), row.get("task")
        if row.get("state") != "waiting" or not res or not task or not sup_state.RES.match(res):
            continue
        with lease.locked() as d:
            _, state = lease.read(d, res)
        mine = [e for e in events if e.get("task") == task and e.get("resource") == res]
        need = next((e for e in reversed(mine) if e["kind"] == "need"), None)
        granted = any(e["kind"] == "granted" and e["id"] > (need or {"id": 0})["id"] for e in mine)
        if state != "free" or not (granted or res in cfg.get("auto", [])):
            continue
        key = f"{task}:{res}:{need['id'] if need else 0}"
        if _once(mem, "free", key):
            minutes = (need or {}).get("minutes") or 30
            with sup_state.locked(profile):
                sup_state.inbox_add(profile, task, f'free: run "at sup need {res} --minutes {minutes}" again')
            acts.append(f"free {res} for {task}")


def _starts(profile: str, mem: dict, acts: list[str]) -> None:
    """A refused start is tried again only when the owner touches or the pack file changes."""
    tried = mem.setdefault("start_tried", {})
    for task in _workers().next_tasks(profile):
        key = [_owner_touches(profile), json.dumps(sup_state.pack_of(profile, task), sort_keys=True)]
        if tried.get(task) == key:
            continue
        rc, reason = _run_at(profile, ["sup", "start-worker", task])
        if rc == 0:
            tried.pop(task, None)
            acts.append(f"started {task}")
            continue
        tried[task] = key
        _log(profile, f"start-worker {task} refused: {reason}")
        if _once(mem, "start_refused", f"{task}:{reason}"):
            _emit(profile, "start_refused", task, reason=reason)
            acts.append(f"start_refused {task}")
        _remember(profile, mem)


def _tip(profile: str, task: str) -> str:
    hub = _cwd(profile)
    if hub is None:
        return ""
    try:
        p = subprocess.run(["git", "-C", hub, "rev-parse", "--verify", "-q", f"refs/heads/task/{task}"], capture_output=True,
                           text=True, timeout=30, env=_env(profile))
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return p.stdout.strip()


def _landing(profile: str, mem: dict, acts: list[str]) -> None:
    """A refused landing is tried again only when the tip of task/<ID> changes or the owner touches."""
    if sup_state.config(profile).get("land") != "auto":
        return
    tried = mem.setdefault("land_tried", {})
    for row in sup_state.workers(profile):
        task = row.get("task")
        gone = row.get("state") == "stopped" and row.get("session") in mem.get("dead", [])
        if not task or task in mem.get("landed", []) or not (row.get("state") == "done" or gone):
            continue
        pack = sup_state.pack_of(profile, task)
        if pack and pack.get("state") in ("paused", "closed"):
            continue
        key = [_tip(profile, task), _owner_touches(profile)]
        if tried.get(task) == key:
            continue
        rc, reason = _run_at(profile, ["sup", "land", task])
        if rc == 0:
            tried.pop(task, None)
            mem.setdefault("landed", []).append(task)
            if not any(e.get("kind") == "landed" and e.get("task") == task for e in sup_state.events_since(profile, 0)):
                _emit(profile, "landed", task, row.get("session"))  # `at sup land` emits it itself; this is the fallback
            acts.append(f"landed {task}")
        else:
            tried[task] = key
            _emit(profile, "land_refused", task, row.get("session"), reason=reason)
            acts.append(f"land_refused {task}")
        _remember(profile, mem)


NOTIFY = ("dead", "start_refused", "land_refused", "owed", "overdue", "ticks_paused")


def _notices(profile: str, mem: dict, acts: list[str]) -> None:
    """Trouble reaches the owner without a tick: a non-blocking queue entry and a best-effort `at notify`, once per event."""
    last = mem.get("notice_id", 0)
    for e in sup_state.events_since(profile, last):
        last = max(last, e["id"])
        kind, task = e.get("kind"), e.get("task")
        if not (kind in NOTIFY or (kind == "stopped" and e.get("status") in ("BLOCKED", "GAVE_UP"))):
            continue
        what = f"{kind} {e.get('status') or ''}".strip()
        detail = e.get("reason") or e.get("resource") or ""
        with sup_state.locked(profile):
            sup_state.queue_add(profile, task if task and sup_state.TASK.match(task) else None,
                                f"{what} {task or ''}: {detail}".strip()[:200], source="watcher", blocking=False)
        _run_at(profile, ["notify", f"{profile}: {what} {task or ''}".strip()], timeout=30, with_profile=False)
        acts.append(f"notified {what} {task or ''}".strip())
    mem["notice_id"] = last


def _pid_file_alive(path: Path) -> bool:
    try:
        pid = int(path.read_text().split()[0])
        os.kill(pid, 0)
    except (OSError, ValueError, IndexError):
        return False
    return True


def _run_tick(profile: str) -> bool:
    """Run `at sup tick` and wait. The tick writes tick.pid itself; a killed tick leaves a stale pid that is not alive."""
    proc = subprocess.Popen([_at(), "sup", "tick", "--profile", profile], env=_env(profile), cwd=_cwd(profile),
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
    end = time.time() + TICK_TIMEOUT
    while proc.poll() is None:
        if STOP or time.time() >= end:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            return False
        time.sleep(0.2)
    return proc.returncode == 0


def _tick(profile: str, mem: dict, acts: list[str]) -> None:
    if mem.get("paused") is not None:
        if _owner_touches(profile) == mem["paused"]:
            return
        mem["paused"], mem["tick_fail"] = None, 0
    if not sup_state.events_since(profile) or _pid_file_alive(sup_state.profile_dir(profile) / "tick.pid"):
        return
    if _run_tick(profile):
        mem["tick_fail"] = 0
        acts.append("tick")
        return
    mem["tick_fail"] = mem.get("tick_fail", 0) + 1
    _emit(profile, "tick_failed", reason=f"failure {mem['tick_fail']} of {TICK_TRIES}")
    acts.append("tick_failed")
    if mem["tick_fail"] >= TICK_TRIES:
        mem["paused"] = _owner_touches(profile)
        _emit(profile, "ticks_paused", reason="3 failed ticks in a row; resumes after an owner touch")
        acts.append("ticks_paused")


def step(profile: str, hub=None, tick: bool = True) -> list[str]:
    """One pass; returns the actions taken. watch.json is saved after every step that changed it."""
    mem, acts = _memory(profile), []
    saved = json.dumps(mem, sort_keys=True)
    try:
        for part in (_liveness, _leases, _answers, _free, _starts, _landing, _notices) + ((_tick,) if tick else ()):
            part(profile, mem, acts)
            now = json.dumps(mem, sort_keys=True)
            if now != saved:
                _remember(profile, mem)
                saved = now
    finally:
        _remember(profile, mem)
    for a in acts:
        _log(profile, a)
    return acts


# ---- the process -----------------------------------------------------------------------

def _pid_path(profile: str) -> Path:
    return sup_state.profile_dir(profile) / "watch.pid"


def running_pid(profile: str) -> int | None:
    """The pid in watch.pid when it is alive with the recorded start time; a reused pid is not the watcher."""
    try:
        pid, started = _pid_path(profile).read_text().split()
        os.kill(int(pid), 0)
    except (OSError, ValueError):
        return None
    return int(pid) if str(lease.start_time(int(pid))) == started else None


def _claim(profile: str) -> bool:
    p = _pid_path(profile)
    if running_pid(profile):
        return False
    p.unlink(missing_ok=True)
    try:
        fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w") as fh:
        fh.write(f"{os.getpid()} {lease.start_time(os.getpid())}\n")
    return True


def loop(profile: str, interval: float, tick: bool) -> int:
    global STOP
    if not _claim(profile):
        return 3

    def _stop(*_):
        global STOP
        STOP = True

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    _log(profile, f"watcher started pid {os.getpid()} interval {interval} tick {tick}")
    try:
        while not STOP:
            try:
                step(profile, None, tick)
            except Exception:
                _log(profile, "pass failed:\n" + traceback.format_exc())
            end = time.time() + interval
            while not STOP and time.time() < end:
                time.sleep(min(0.2, max(0.0, end - time.time())))
    finally:
        _log(profile, "watcher stopped")
        if _pid_path(profile).read_text().split()[:1] == [str(os.getpid())]:
            _pid_path(profile).unlink(missing_ok=True)
    return 0


# ---- commands --------------------------------------------------------------------------

def _profile(args) -> str | None:
    try:
        profile = sup_state.current_profile(getattr(args, "profile", None))
    except ValueError as e:
        print(f"at: sup: {e}", file=sys.stderr)
        return None
    if profile is None:
        print("at: sup: no profile: pass --profile or set AGENTS_SUPERVISOR", file=sys.stderr)
    return profile


def _chat_only() -> bool:
    import sup_ask
    return sup_ask.require_chat()


def cmd_start(args) -> int:
    if not _chat_only():
        return 3
    profile = _profile(args)
    if profile is None:
        return 2
    if args.interval <= 0:
        print("at: sup: --interval must be positive", file=sys.stderr)
        return 2
    if running_pid(profile):
        print(f"at: sup: a watcher is already running for {profile} (pid {running_pid(profile)})", file=sys.stderr)
        return 3
    cmd = [sys.executable, str(Path(__file__).resolve()), "run", "--profile", profile, "--interval", str(args.interval)]
    log = open(sup_state.profile_dir(profile) / "watch.log", "a")
    proc = subprocess.Popen(cmd + (["--no-tick"] if args.no_tick else []), stdin=subprocess.DEVNULL, stdout=log,
                            stderr=log, start_new_session=True, close_fds=True, env=_env(profile))
    log.close()
    end = time.time() + 5
    while running_pid(profile) != proc.pid and proc.poll() is None and time.time() < end:
        time.sleep(0.05)
    if running_pid(profile) != proc.pid:
        print(f"at: sup: watcher for {profile} did not start (see watch.log)", file=sys.stderr)
        return 3
    print(f"watcher started for {profile} (pid {proc.pid})")
    return 0


def cmd_stop(args) -> int:
    if not _chat_only():
        return 3
    profile = _profile(args)
    if profile is None:
        return 2
    pid = running_pid(profile)
    if pid is None:
        _pid_path(profile).unlink(missing_ok=True)
        print(f"no watcher running for {profile}")
        return 0
    os.kill(pid, signal.SIGTERM)
    end = time.time() + 10
    while running_pid(profile) and time.time() < end:
        time.sleep(0.05)
    if running_pid(profile):
        print(f"at: sup: watcher pid {pid} did not stop", file=sys.stderr)
        return 3
    print(f"watcher stopped for {profile}")
    return 0


def cmd_status(args) -> int:
    profile = _profile(args)
    if profile is None:
        return 2
    pid = running_pid(profile)
    print(f"watcher running for {profile} (pid {pid})" if pid else f"watcher not running for {profile}")
    return 0 if pid else 3


def cmd_once(args) -> int:
    profile = _profile(args)
    if profile is None:
        return 2
    for a in step(profile, None, not args.no_tick):
        print(a)
    return 0


def cmd_run(args) -> int:
    profile = _profile(args)
    return 2 if profile is None else loop(profile, args.interval, not args.no_tick)


def register(sup_sub) -> None:
    watch = sup_sub.add_parser("watch", help="the detached watcher of a profile")
    sub = watch.add_subparsers(dest="watch_cmd", required=True)
    for name, func, help_ in (("start", cmd_start, "start the detached watcher"), ("stop", cmd_stop, "stop it"),
                              ("status", cmd_status, "is it running"), ("once", cmd_once, "one pass in the foreground")):
        p = sub.add_parser(name, help=help_)
        p.add_argument("--profile")
        if name in ("start", "once"):
            p.add_argument("--no-tick", action="store_true", help="never start a supervisor tick (trial arm A)")
        if name == "start":
            p.add_argument("--interval", type=float, default=30.0, help="seconds between passes (default 30)")
        p.set_defaults(func=func)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(prog="sup_watch")
    ap.add_argument("run")
    ap.add_argument("--profile")
    ap.add_argument("--interval", type=float, default=30.0)
    ap.add_argument("--no-tick", action="store_true")
    sys.exit(cmd_run(ap.parse_args()))
