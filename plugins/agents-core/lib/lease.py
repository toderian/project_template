"""`at lease`: host-wide single-holder leases on shared resources (a port, a device, the full suite).

One JSON file per resource under AGENTS_LEASE_DIR, every read and write under flock on a lock file there.
States: held, overdue (TTL passed, holder alive: still held), owed (holder gone, restore flag: stays
unavailable until `clear --restored`), free (no file, or holder gone without restore flag).
Exit codes: 0 ok, 2 usage, 3 refused. stdlib only.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import math
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

NAME = re.compile(r"[a-z0-9][a-z0-9-]*\Z")


def lease_dir() -> Path:
    d = os.environ.get("AGENTS_LEASE_DIR")
    if d:
        return Path(d)
    state = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(state) / "agents-template" / "leases"


def start_time(pid: int):
    """Field 22 of /proc/<pid>/stat (read after the last ')': the command name may hold spaces); None without /proc."""
    try:
        return int(Path(f"/proc/{pid}/stat").read_text().rpartition(")")[2].split()[19])
    except (OSError, ValueError, IndexError):
        return None


def alive(rec: dict) -> bool:
    pid = rec.get("pid")
    if not isinstance(pid, int):
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass
    if rec.get("pid_start") is not None:
        now = start_time(pid)
        return now is None or now == rec["pid_start"]  # a different start time: the pid was reused
    return True


def state_of(rec: dict) -> str:
    if alive(rec):
        return "overdue" if time.time() > rec["start"] + rec["ttl"] * 60 else "held"
    return "owed" if rec.get("restore") else "free"


def me(own_pid: bool = False) -> dict:
    # `take` records CLAUDE_PID (else the parent). In a background session CLAUDE_PID is a shared daemon
    # that outlives the session, so such a lease ends by release or TTL (overdue), never by "holder gone".
    # `run` records its own pid: that lease lives exactly as long as the `at lease run` process.
    pid = os.getpid() if own_pid else int(os.environ.get("CLAUDE_PID") or 0) or os.getppid()
    return {"session": os.environ.get("CLAUDE_CODE_SESSION_ID") or None, "pid": pid, "pid_start": start_time(pid)}


def is_holder(rec: dict, own_pid: bool = False) -> bool:
    m = me(own_pid)
    if m["session"] and rec.get("session"):
        return m["session"] == rec["session"]  # sessions may share a CLAUDE_PID: ids alone decide
    if rec.get("session"):
        return False
    return m["pid"] == rec.get("pid") and m["pid_start"] == rec.get("pid_start")


def describe(res: str, rec: dict) -> str:
    left = int(rec["start"] + rec["ttl"] * 60 - time.time())
    when = f"{left // 60} min left" if left >= 0 else f"{-left // 60} min over"
    who = f"session {rec['session']}" if rec.get("session") else f"pid {rec.get('pid')}"
    return f"lease: {res} is {state_of(rec)}, holder {who}, task {rec.get('task') or '-'}, {when}"


@contextlib.contextmanager
def locked():
    d = lease_dir()
    d.mkdir(parents=True, exist_ok=True)
    with open(d / ".lock", "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        yield d


def read(d: Path, res: str):
    """The record and its state; a stale (free) file is removed here."""
    p = d / f"{res}.json"
    try:
        rec = json.loads(p.read_text())
    except (OSError, ValueError):
        return None, "free"
    ok = isinstance(rec, dict) and isinstance(rec.get("pid"), int) and all(
        isinstance(rec.get(k), (int, float)) and not isinstance(rec.get(k), bool) for k in ("start", "ttl"))
    if not ok:  # damaged record: free
        p.unlink(missing_ok=True)
        return None, "free"
    st = state_of(rec)
    if st == "free":
        p.unlink(missing_ok=True)
        return None, "free"
    return rec, st


def write(d: Path, res: str, rec: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp-")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(rec, fh)
        os.replace(tmp, d / f"{res}.json")
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def take(res: str, ttl: float, task=None, reason=None, restore=False, own_pid=False) -> int:
    with locked() as d:
        rec, st = read(d, res)
        if rec and not is_holder(rec, own_pid):  # the holder may re-take its own lease to renew the TTL
            print(describe(res, rec), file=sys.stderr)
            return 3
        write(d, res, {**me(own_pid), "task": task, "reason": reason, "start": time.time(), "ttl": ttl, "restore": restore})
    return 0


def release(res: str, own_pid: bool = False) -> int:
    with locked() as d:
        rec, st = read(d, res)
        if rec is None:
            return 0
        if not is_holder(rec, own_pid):
            print(f"lease: {res} is not yours to release. " + describe(res, rec), file=sys.stderr)
            return 3
        (d / f"{res}.json").unlink(missing_ok=True)
    return 0


def clear(res: str, restored: bool) -> int:
    if os.environ.get("CLAUDE_CODE_SESSION_ID") and os.environ.get("AGENTS_LEASE_OWNER") != "1":
        print("lease clear: refused inside a session; the owner runs it in their own shell", file=sys.stderr)
        return 3
    with locked() as d:
        rec, st = read(d, res)
        if rec is None:
            return 0
        if st == "held":
            print(f"lease: {res} is still held, nothing to clear. " + describe(res, rec), file=sys.stderr)
            return 3
        if st == "owed" and not restored:
            print(f"lease: {res} is owed; the resource must be restored first, then `at lease clear {res} --restored`", file=sys.stderr)
            return 3
        (d / f"{res}.json").unlink(missing_ok=True)
    return 0


def list_all(as_json: bool) -> int:
    rows = []
    with locked() as d:
        for p in sorted(d.glob("*.json")):
            rec, st = read(d, p.stem)
            if rec:
                rows.append({"resource": p.stem, "state": st, **rec})
    if as_json:
        print(json.dumps(rows))
    for r in rows:
        if not as_json:
            print(describe(r["resource"], r))
    return 0


def run(res: str, ttl: float, cmd: list) -> int:
    code = take(res, ttl, own_pid=True)
    if code:
        return code
    child = []
    for sig in (signal.SIGTERM, signal.SIGHUP):  # forward to the command; the finally below still releases
        signal.signal(sig, lambda n, _f: child and child[0].send_signal(n))
    try:
        child.append(subprocess.Popen(cmd))
        rc = child[0].wait()
        return rc if rc >= 0 else 128 - rc
    except OSError as e:
        print(f"lease run: {e}", file=sys.stderr)
        return 127
    finally:
        release(res, own_pid=True)


def ttl_arg(v: str) -> float:
    try:
        f = float(v)
    except ValueError:
        f = math.nan
    if not (math.isfinite(f) and f > 0):
        raise argparse.ArgumentTypeError(f"ttl must be a finite number of minutes above 0, not {v!r}")
    return f


def main(argv: list) -> int:
    cmd = []
    if "--" in argv:
        i = argv.index("--")
        argv, cmd = argv[:i], argv[i + 1:]
    ap = argparse.ArgumentParser(prog="at lease")
    sub = ap.add_subparsers(dest="verb", required=True)
    t = sub.add_parser("take")
    t.add_argument("--ttl", type=ttl_arg, required=True)
    t.add_argument("--for", dest="task")
    t.add_argument("--reason")
    t.add_argument("--restore", action="store_true")
    r = sub.add_parser("run", help="take, run the command after --, release; exit 3 with 'lease: <resource> is held' "
                       "on stderr means refused before the command ran")
    r.add_argument("--ttl", type=ttl_arg, default=30)
    c = sub.add_parser("clear")
    c.add_argument("--restored", action="store_true")
    ls = sub.add_parser("list")
    ls.add_argument("--json", action="store_true")
    for p in (t, r, c, sub.add_parser("release")):
        p.add_argument("resource")
    a = ap.parse_args(argv)
    if a.verb != "list" and not NAME.match(a.resource):
        ap.error("resource must match [a-z0-9][a-z0-9-]*")
    if a.verb == "run" and not cmd:
        ap.error("run needs a command after --")
    if a.verb != "run" and cmd:
        ap.error("unexpected --")
    if a.verb == "take":
        return take(a.resource, a.ttl, a.task, a.reason, a.restore)
    if a.verb == "run":
        return run(a.resource, a.ttl, cmd)
    if a.verb == "release":
        return release(a.resource)
    if a.verb == "clear":
        return clear(a.resource, a.restored)
    return list_all(a.json)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
