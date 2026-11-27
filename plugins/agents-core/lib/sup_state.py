"""State of one supervisor profile on this host: the only module that reads or writes it.

Directory: ${AGENTS_SUP_DIR:-${XDG_STATE_HOME:-~/.local/state}/agents-template/sup}/<profile>/

  config.json        {"cap": 3, "auto": ["full-suite"], "land": "auto"}   (all keys optional)
  packs/<name>.json  {"name", "tasks": [id…], "state": "new|running|paused|closed", "parallel": bool,
                      "branches": {repo: branch}, "tips": {repo: first tip sha}, "prs": {repo: url}}
  workers.json       [{"session", "task", "pack", "cwd", "mode": "bg|headless", "started",
                       "state": "starting|running|waiting|stopped|done", "waiting_for": resource|null,
                       "stopped_by": null|"owner"}]
  events.jsonl       one JSON object per line: {"id": n, "ts", "kind", "task", "session", …}; `events.seq` holds
                     the last id given out, `cursor` the id of the last event a tick handled
  queue.json         [{"id": "Q1", "ts", "task", "question", "options": [..], "recommendation", "source",
                       "blocking": bool, "answer": null|str, "by": null|"owner"|"sup"}]   (questions for the owner)
  inbox/<TASK>.json  [{"id": "A1", "ts", "text", "by": "owner"|"sup", "q": "Q1"|null, "ack": bool}]  (answers for a worker)
  instructions.md    the owner's standing instructions, one dated bullet each
  touch.log          one line per owner action through `at sup` (the trial counts them)

Event kinds (every kind a part emits):
  worker:   started, stopped (status BLOCKED|GAVE_UP|EMPTY), done, waiting, idle, dead, restarted (reason answer|dead)
  asks:     ask (q), need (resource, minutes), granted (resource), denied (resource), released (resource),
            answered (q, by), overdue (resource), owed (resource)
  refusals: start_refused (reason), land_refused (reason)
  watcher:  landed, tick_failed (reason), ticks_paused (reason)
JUDGEMENT lists the kinds a tick runs a session for; NO_JUDGEMENT the kinds it advances over without one.
Every change happens under `locked(profile)`, held only around state reads and writes, never across a `claude` or
`at` subprocess; files are replaced atomically. A part that keeps its own small file in the profile directory uses
`read_json(path, default)` and `write_json(path, data)`. stdlib only.
"""
from __future__ import annotations

import contextlib
import fcntl
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

NAME = re.compile(r"[a-z0-9][a-z0-9-]*\Z")
RES = re.compile(r"[a-z0-9][a-z0-9-]*\Z")  # a resource name (same as lease.NAME)
TASK = re.compile(r"[A-Z][A-Z0-9]*-[0-9]+\Z")
KEY = re.compile(r"[a-z][a-z0-9_]*\Z")  # an event field name
QID = re.compile(r"Q[0-9]+\Z")
SESSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{7,63}\Z")
EVENT_KINDS = ("started", "stopped", "done", "waiting", "idle", "dead", "restarted", "ask", "need", "granted",
               "denied", "released", "answered", "overdue", "owed", "start_refused", "land_refused", "landed",
               "tick_failed", "ticks_paused")
WORKER_STATES = ("starting", "running", "waiting", "stopped", "done")
PACK_STATES = ("new", "running", "paused", "closed")
# Which kinds a tick must think about. One place; test_sup_state checks that every kind in EVENT_KINDS is in exactly one group.
JUDGEMENT = ("ask", "need")  # a worker waits for the supervisor's decision: an answer, a grant or a denial
NO_JUDGEMENT = (
    "started", "restarted", "done", "landed",  # the worker's life and the watcher's own landing: nothing to decide
    "granted", "denied", "released", "answered", "waiting",  # results of a decision already made, or a state change
    "stopped", "idle",  # a BLOCKED or GAVE_UP stop is reported to the owner by the watcher (sup_watch._notices)
    "dead", "start_refused", "land_refused", "owed", "overdue", "ticks_paused",  # the watcher reports these to the owner (NOTIFY)
    "tick_failed",  # the watcher's report of a failed tick
)


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def root() -> Path:
    base = os.environ.get("AGENTS_SUP_DIR")
    if base:
        return Path(base)
    state = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(state) / "agents-template" / "sup"


def current_profile(explicit: str | None = None) -> str | None:
    """The profile a command acts on: the flag, else AGENTS_SUPERVISOR (set for supervised workers and ticks)."""
    name = explicit or os.environ.get("AGENTS_SUPERVISOR") or None
    if name is not None and not NAME.match(name):
        raise ValueError(f"profile name {name!r} must match [a-z0-9][a-z0-9-]*")
    return name


def profile_dir(profile: str, create: bool = True) -> Path:
    if not NAME.match(profile):
        raise ValueError(f"profile name {profile!r} must match [a-z0-9][a-z0-9-]*")
    d = root() / profile
    if create:
        (d / "packs").mkdir(parents=True, exist_ok=True)
        (d / "inbox").mkdir(exist_ok=True)
    return d


@contextlib.contextmanager
def locked(profile: str, wait: float | None = None):
    """One lock per profile for every change of its state. Not reentrant: take it once, at the command level.
    `wait` bounds the wait in seconds (TimeoutError); the default waits as long as it takes."""
    with open(profile_dir(profile) / "lock", "a+") as fh:
        if wait is None:
            fcntl.flock(fh, fcntl.LOCK_EX)
        else:
            end = time.monotonic() + wait
            while True:
                try:
                    fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= end:
                        raise TimeoutError(f"profile {profile!r} is locked") from None
                    time.sleep(0.05)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def read_json(path: Path, default):
    """The JSON in `path`, or `default` when the file is missing, broken or of another type."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default
    return data if isinstance(data, type(default)) else default


def write_json(path: Path, data) -> None:
    """Replace `path` atomically; the caller holds `locked(profile)` for a file other parts read."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def hub(profile: str | None, explicit=None) -> Path:
    """The hub every `at sup` command works in: `--hub` when given, else config key `hub` (set by `at sup init`),
    else the git toplevel of the cwd."""
    if explicit:
        return Path(explicit).resolve()
    configured = config(profile).get("hub") if profile else None
    if configured:
        return Path(configured)
    p = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if p.returncode != 0:
        raise ValueError("no hub: pass --hub, run `at sup init`, or work inside the hub checkout")
    return Path(p.stdout.strip())


def config(profile: str) -> dict:
    cfg = {"cap": 3, "auto": ["full-suite"], "land": "auto"}
    cfg.update(read_json(profile_dir(profile) / "config.json", {}))
    return cfg


def local_entries(entries, hub: Path, check: bool = True) -> list[str]:
    """The `local` list of a profile: relative paths without `..`, none a parent of another, not the repos.map that
    start-worker writes per worktree, and (when `check`, an early hint: the worktree's git decides) ignored by git in
    the hub. ValueError names the entry. A trailing `/` marks a directory."""
    if not (isinstance(entries, list) and all(isinstance(e, str) for e in entries)):
        raise ValueError("local must be a list of strings")
    bodies = [e[:-1] if e.endswith("/") else e for e in entries]
    for e, body in zip(entries, bodies):
        if (not body or body[0] == ":" or any(p in ("", ".", "..") for p in body.split("/")) or "\\" in e
                or any(ord(c) < 32 or ord(c) == 127 for c in e) or body in (".local", ".local/repos.map")):
            raise ValueError(f"local entry {e!r} must be a relative path with no empty, '.' or '..' part, not starting with ':', not .local/repos.map")
        if any(o != body and o.startswith(body + "/") for o in bodies):
            raise ValueError(f"local entry {e!r} is a parent of another entry")
        if check:
            p = subprocess.run(["git", "-C", str(hub), "check-ignore", "-q", "--", body], capture_output=True, text=True)
            if p.returncode == 1:
                raise ValueError(f"local entry {e!r} is not ignored by git in {hub} (write `{body}`, not `{body}/`, in .gitignore)")
            if p.returncode:
                raise ValueError(f"git check-ignore of local entry {e!r} failed: {(p.stderr.strip().splitlines() or ['?'])[-1]}")
    return entries


def profile_local(profile: str, hub: Path, check: bool = True) -> list[str]:
    """`local` of the profile's conf/profile.json (empty without the file or the key), checked by local_entries."""
    pf = profile_dir(profile) / "conf" / "profile.json"
    if not pf.is_file():
        return []
    try:
        entries = json.loads(pf.read_text(encoding="utf-8")).get("local", [])
    except (OSError, ValueError, AttributeError) as e:
        raise ValueError(f"{pf} cannot be read as a profile: {e}") from None
    return local_entries(entries, hub, check)


def set_config(profile: str, **changes) -> dict:
    d = profile_dir(profile)
    cfg = read_json(d / "config.json", {})
    cfg.update(changes)
    write_json(d / "config.json", cfg)
    return config(profile)


# ---- packs ---------------------------------------------------------------------------

def read_pack(profile: str, name: str) -> dict | None:
    if not NAME.match(name):
        raise ValueError(f"pack name {name!r} must match [a-z0-9][a-z0-9-]*")
    pack = read_json(profile_dir(profile) / "packs" / f"{name}.json", {})
    return pack or None


def write_pack(profile: str, pack: dict) -> None:
    if not NAME.match(pack.get("name", "")) or pack.get("state", "new") not in PACK_STATES:
        raise ValueError("a pack needs a valid name and state")
    if not pack.get("tasks") or not all(TASK.match(t) for t in pack["tasks"]):
        raise ValueError("a pack needs task IDs like RM-12")
    pack = {"state": "new", "parallel": False, "branches": {}, "tips": {}, "prs": {}, **pack}
    write_json(profile_dir(profile) / "packs" / f"{pack['name']}.json", pack)


def list_packs(profile: str) -> list[dict]:
    d = profile_dir(profile) / "packs"
    return [p for p in (read_json(f, {}) for f in sorted(d.glob("*.json"))) if p]


def pack_of(profile: str, task: str) -> dict | None:
    return next((p for p in list_packs(profile) if task in p.get("tasks", [])), None)


# ---- workers -------------------------------------------------------------------------

def workers(profile: str) -> list[dict]:
    return read_json(profile_dir(profile) / "workers.json", [])


def set_worker(profile: str, session: str, **fields) -> dict:
    """Add the worker or change its fields. `state` must be one of WORKER_STATES."""
    if fields.get("state", "running") not in WORKER_STATES:
        raise ValueError(f"worker state must be one of {WORKER_STATES}")
    rows = workers(profile)
    row = next((w for w in rows if w.get("session") == session), None)
    if row is None:
        row = {"session": session, "task": None, "pack": None, "cwd": None, "mode": "headless",
               "started": now(), "state": "running", "waiting_for": None}
        rows.append(row)
    row.update(fields)
    write_json(profile_dir(profile) / "workers.json", rows)
    return row


def drop_worker(profile: str, session: str) -> None:
    write_json(profile_dir(profile) / "workers.json", [w for w in workers(profile) if w.get("session") != session])


def worker_for(profile: str, task: str | None = None, session: str | None = None) -> dict | None:
    return next((w for w in workers(profile)
                 if (session and w.get("session") == session) or (task and w.get("task") == task)), None)


def live_workers(profile: str) -> list[dict]:
    return [w for w in workers(profile) if w.get("state") in ("starting", "running", "waiting")]


# ---- events --------------------------------------------------------------------------

def _events(profile: str) -> list[dict]:
    out = []
    try:
        lines = (profile_dir(profile) / "events.jsonl").read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    for line in lines:
        with contextlib.suppress(ValueError):
            rec = json.loads(line)
            if isinstance(rec, dict) and isinstance(rec.get("id"), int):
                out.append(rec)
    return out


def _tail(profile: str, nbytes: int = 65536) -> list[dict]:
    """The events in the last `nbytes` of the log (a cut first line is dropped, a torn last line is skipped)."""
    try:
        with open(profile_dir(profile) / "events.jsonl", "rb") as fh:
            size = fh.seek(0, os.SEEK_END)
            fh.seek(max(0, size - nbytes))
            lines = fh.read().decode("utf-8", "replace").splitlines()
            if size > nbytes:
                lines = lines[1:]
    except OSError:
        return []
    out = []
    for line in lines:
        with contextlib.suppress(ValueError):
            rec = json.loads(line)
            if isinstance(rec, dict) and isinstance(rec.get("id"), int):
                out.append(rec)
    return out


def need_open(profile: str, task: str, resource: str) -> bool:
    """True when the newest `need` of this task for the resource is newer than its last granted, denied or released
    (bounded: reads the tail of the log only)."""
    for e in reversed(_tail(profile)):
        if e.get("task") == task and e.get("resource") == resource:
            if e.get("kind") == "need":
                return True
            if e.get("kind") in ("granted", "denied", "released"):
                return False
    return False


def _clean(value):
    if isinstance(value, str):
        return "".join(" " if ord(c) < 32 or ord(c) == 127 else c for c in value[:200])
    if value is None or isinstance(value, (bool, int, float)):
        return value
    raise ValueError(f"event value {value!r} must be a str, int, float, bool or None")


def _atomic_text(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def emit(profile: str, kind: str, task: str | None = None, session: str | None = None, **data) -> int:
    """Append one event; returns its id. Callers hold `locked(profile)`. A kind outside EVENT_KINDS, a task or session
    that does not match TASK or SESSION, or a value that is not a scalar is refused with ValueError. The next id
    comes from `events.seq` (rebuilt from the log when missing), so the log is never parsed here."""
    if kind not in EVENT_KINDS:
        raise ValueError(f"event kind {kind!r} must be one of {EVENT_KINDS}")
    if task is not None and not (isinstance(task, str) and TASK.match(task)):
        raise ValueError(f"task ID {task!r} must look like RM-12")
    if session is not None and not (isinstance(session, str) and SESSION.match(session)):
        raise ValueError(f"session {session!r} must match {SESSION.pattern}")
    if any(not isinstance(k, str) or not KEY.match(k) for k in data):
        raise ValueError("event keys must be lower-case words")
    data = {k: _clean(v) for k, v in data.items()}
    d = profile_dir(profile)
    log, seq = d / "events.jsonl", d / "events.seq"
    try:
        last = int(seq.read_text().strip())
    except (OSError, ValueError):
        last = 0
    last = max([last] + [e["id"] for e in _tail(profile)])  # a stale seq must not fall below the log
    rec = {"id": last + 1, "ts": now(), "kind": kind, "task": task, "session": session, **data}
    _atomic_text(seq, f"{rec['id']}\n")  # before the append: a kill in between leaves a gap, never a reused id
    try:
        with open(log, "rb") as fh:
            fh.seek(-1, os.SEEK_END)
            torn = fh.read(1) != b"\n"
    except OSError:
        torn = False
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(("\n" if torn else "") + json.dumps(rec, ensure_ascii=False) + "\n")
    return rec["id"]


def cursor(profile: str) -> int:
    try:
        return int((profile_dir(profile) / "cursor").read_text().strip())
    except (OSError, ValueError):
        return 0


def events_since(profile: str, after: int | None = None) -> list[dict]:
    after = cursor(profile) if after is None else after
    return [e for e in _events(profile) if e["id"] > after]


def advance(profile: str, last_id: int) -> None:
    if last_id > cursor(profile):
        _atomic_text(profile_dir(profile) / "cursor", f"{last_id}\n")


def landing_message(hub_dir, branch: str, task: str) -> str:
    """The message of the commit on `branch` that landed `task`: the one with the whole line
    `Archive: refs/archive/task/<ID>` (RM-1 is not RM-10); '' when there is none."""
    line = f"Archive: refs/archive/task/{task}"
    log = subprocess.run(["git", "-C", str(hub_dir), "log", branch, "--format=%B%x00", "--fixed-strings", f"--grep={line}"],
                         capture_output=True, text=True)
    return next((m.strip("\n") for m in log.stdout.split("\0") if line in m.splitlines()), "") if log.returncode == 0 else ""


def landed(profile: str, task: str, hub_dir) -> bool:
    """True when a `landed` event exists for the task, or the hub has refs/archive/task/<ID> and the default branch
    log carries `Archive: refs/archive/task/<ID>`."""
    if not TASK.match(task):
        raise ValueError(f"task ID {task!r} must look like RM-12")
    if any(e.get("kind") == "landed" and e.get("task") == task for e in _events(profile)):
        return True
    ref = f"refs/archive/task/{task}"
    git = ["git", "-C", str(hub_dir)]
    if subprocess.run(git + ["rev-parse", "--verify", "--quiet", ref], capture_output=True).returncode != 0:
        return False
    head = subprocess.run(git + ["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"],
                          capture_output=True, text=True)
    branch = head.stdout.strip() if head.returncode == 0 and head.stdout.strip() else None
    if branch is None:
        for cand in ("main", "master"):
            if subprocess.run(git + ["rev-parse", "--verify", "--quiet", cand], capture_output=True).returncode == 0:
                branch = cand
                break
    if branch is None:
        return False
    return bool(landing_message(hub_dir, branch, task))


# ---- the owner's queue and a worker's inbox --------------------------------------------

def _next_id(rows: list[dict], letter: str) -> str:
    return f"{letter}{max([int(r['id'][1:]) for r in rows if str(r.get('id', ''))[1:].isdigit()] or [0]) + 1}"


def queue(profile: str, open_only: bool = True) -> list[dict]:
    rows = read_json(profile_dir(profile) / "queue.json", [])
    return [r for r in rows if r.get("answer") is None] if open_only else rows


def queue_add(profile: str, task: str | None, question: str, options: list[str] | None = None,
              recommendation: str | None = None, source: str = "worker", blocking: bool = True,
              q: str | None = None) -> str:
    rows = queue(profile, open_only=False)
    qid = _next_id(rows, "Q")
    rows.append({"id": qid, "ts": now(), "task": task, "question": question, "options": options or [],
                 "recommendation": recommendation, "source": source, "blocking": blocking, "answer": None, "by": None,
                 **({"q": q} if q else {})})  # q: the worker question an escalation is about
    write_json(profile_dir(profile) / "queue.json", rows)
    return qid


def queue_close(profile: str, qid: str, answer: str, by: str) -> bool:
    """The first answer wins: False when the question is unknown or already answered."""
    rows = queue(profile, open_only=False)
    row = next((r for r in rows if r.get("id") == qid), None)
    if row is None or row.get("answer") is not None:
        return False
    row.update(answer=answer, by=by, answered=now())
    write_json(profile_dir(profile) / "queue.json", rows)
    return True


def _inbox_path(profile: str, task: str) -> Path:
    if not TASK.match(task):
        raise ValueError(f"task ID {task!r} must look like RM-12")
    return profile_dir(profile) / "inbox" / f"{task}.json"


def inbox(profile: str, task: str, unread_only: bool = False) -> list[dict]:
    rows = read_json(_inbox_path(profile, task), [])
    return [r for r in rows if not r.get("ack")] if unread_only else rows


def inbox_add(profile: str, task: str, text: str, by: str = "sup", q: str | None = None) -> str:
    if by not in ("sup", "owner"):
        raise ValueError("an answer comes from 'sup' or 'owner'")
    rows = inbox(profile, task)
    aid = _next_id(rows, "A")
    rows.append({"id": aid, "ts": now(), "text": text, "by": by, "q": q, "ack": False})
    write_json(_inbox_path(profile, task), rows)
    return aid


def inbox_ack(profile: str, task: str, aid: str) -> bool:
    rows = inbox(profile, task)
    row = next((r for r in rows if r.get("id") == aid), None)
    if row is None:
        return False
    row["ack"] = True
    write_json(_inbox_path(profile, task), rows)
    return True


# ---- instructions and the touch log ----------------------------------------------------

def instructions(profile: str) -> str:
    try:
        return (profile_dir(profile) / "instructions.md").read_text(encoding="utf-8")
    except OSError:
        return ""


def instruct(profile: str, text: str) -> None:
    line = " ".join(text.split())
    with open(profile_dir(profile) / "instructions.md", "a", encoding="utf-8") as fh:
        fh.write(f"- {time.strftime('%Y-%m-%d')}: {line}\n")


def touch(profile: str, what: str) -> None:
    """One owner action. Callers: commands the owner runs or that the chat runs on the owner's word."""
    with open(profile_dir(profile) / "touch.log", "a", encoding="utf-8") as fh:
        fh.write(f"{now()}\t{' '.join(what.split())}\n")
