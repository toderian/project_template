"""`at run-guard watch`: the watchdog of an armed run, outside the session it watches.

Started detached by `at run-guard arm --watch` (or in the foreground by `at run-guard watch`). Every
`--interval` seconds it reads the session's marker and `.status` (both under the run-guard dir) and:

  marker gone, `.watch` no longer holds this pid, `--until` passed   exit
  every target read, and DONE or nothing open   notify "finished" (the hook's key), `at task report`,
                                                drop the record, exit
  BLOCKED, no target changed since the stop     notify (the hook's key); session dead: exit, else watch on
                                                (a changed target: the BLOCKED is stale, as if absent)
  session or a restart alive, pid unknown, or   never restart; notify "idle" once on GAVE_UP / EMPTY or
  a target that could not be read               no target change for `--idle` minutes
  dead, open, restarts left                     growing pause, authorise, `claude --resume <id> -p <fixed
                                                prompt>` in the marker's cwd, notify "restarted-<n>"
  dead, cap reached or only missing state       notify "gave-up", exit; a refused authorisation: notify
                                                "refused-<reason>", exit

Everything a watcher must remember lives in one record, `<session>.watch.state` (JSON, temp + rename):
the restart caps of the first `arm --watch` (max-resumes, budget, allow-bypass), the restarts used, the
pid of a running restart, the last permission mode seen, and the watcher-only events already sent. A
later watcher continues from it, and new flags can only lower its caps (`--allow-bypass` is never
added). `--until`, `--idle`, `--interval` and `--pause` belong to each watcher's own argv. `disarm` and
"finished" remove the record. The events that end a watcher (gave up, refused) are never deduped: each
watcher that ends for that reason says so.

The marker, `.status` and the task file are written by the session being watched, so none of them is
trusted: the prompt is fixed, the id and cwd are validated, the mode comes from an allow-list, and
`claude` gets argv, never a shell. Watcher-only events are sent without `--event`, so a key the session
plants in `.sent/` cannot silence them.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from task_run import _pid_alive  # lib/task_run.py, next to this file

ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")  # session and task ids: never an option-like `-x`
SAFE_MODES = ("default", "acceptEdits", "plan")
ROW_RE = re.compile(r"^\|\s*[0-9]+[a-z]?\s*\|([^|\n]*)\|")
LOG_CAP = 64 * 1024
DEFAULTS = {"interval": 600.0, "max_resumes": 4, "budget_usd": 4.0, "until": None, "idle": 90.0,
            "pause": 60.0, "allow_bypass": False}
RECORD_CAPS = ("max_resumes", "budget_usd", "allow_bypass")  # the caps a record keeps across watchers
RECORD_TYPES = {"max_resumes": int, "budget_usd": (int, float), "allow_bypass": bool,
                "used": int, "child": (int, type(None)), "mode": str, "sent": list}
# the resumed session inherits none of the watched session's identity (fact 9: it would not save a transcript)
SESSION_ENV = ("CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_CHILD_SESSION", "CLAUDE_PID", "CLAUDECODE",
               "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SESSION_ATTENDED", "CLAUDE_CODE_CHILD_NOTES_DIR",
               "CLAUDE_CODE_MESSAGING_SOCKET", "CLAUDE_CODE_MESSAGING_TOKEN", "CLAUDE_CODE_EXECPATH", "CLAUDE_EFFORT")
RESUME_PROMPT = (
    "Run guard watchdog: this session's process died with its run still open; this is a headless restart (claude -p). "
    "Nothing outlives this turn: background jobs and scheduled wakeups end with it, and a job you waited on died with "
    "the old process. Resume from the run's state.md (the run guard's reminder names the open rows), not from memory, "
    "following agents-core:execute-plan. Run long jobs in the foreground and wait for them; never end this turn on "
    "`Run: WAITING`. End it only when every row is committed or parked, or on `Run: BLOCKED <the owner's decision>`.")


def build_parser() -> argparse.ArgumentParser:
    # no defaults here: None means "not given", so a re-arm lowers only the caps it names
    p = argparse.ArgumentParser(prog="at run-guard watch", description="the run guard's watchdog", allow_abbrev=False)
    p.add_argument("--interval", type=float, help="seconds between ticks (default 600)")
    p.add_argument("--max-resumes", type=int, help="restarts of a dead session at most (default 4)")
    p.add_argument("--budget-usd", type=float, help="total spend of all restarts (default 4)")
    p.add_argument("--until", help="stop watching at HH:MM (local time) or after +SECONDS")
    p.add_argument("--idle", type=float, help="minutes without a target change before 'idle' (default 90)")
    p.add_argument("--pause", type=float, help="seconds before restart 1; doubled for each next one (default 60)")
    p.add_argument("--allow-bypass", action="store_true", default=None,
                   help="may restart in bypassPermissions (see docs)")
    return p


def share(caps: dict) -> float:
    """The budget of one restart: the total over the cap, floored to cents."""
    return math.floor(caps["budget_usd"] * 100 / max(caps["max_resumes"], 1) + 1e-6) / 100


def restart_caps_ok(c: dict) -> bool:
    """The bounds of the caps a record keeps, checked on the flags (parse_caps), on a loaded record
    (load_record) and on the merge of both (main): each restart also gets at least 0.01 USD."""
    return 0 <= c["max_resumes"] <= 20 and 0 < c["budget_usd"] <= 1000 and (c["max_resumes"] == 0 or share(c) >= 0.01)


def parse_caps(args: list[str], partial: bool = False) -> tuple[dict, list[str]]:
    """(the caps given, `until` made absolute; the other arguments when `partial`). Exits 2 on a bad value."""
    ns, rest = build_parser().parse_known_args(args) if partial else (build_parser().parse_args(args), [])
    caps = {k: v for k, v in vars(ns).items() if v is not None}
    if "until" in caps:
        caps["until"] = deadline(caps["until"])
    c = {**DEFAULTS, **caps}
    timing_ok = 0.05 <= c["interval"] <= 86400 and c["idle"] >= 0 and 0 <= c["pause"] <= 86400
    if not (timing_ok and restart_caps_ok(c) and ("until" not in caps or caps["until"])):
        print("at: run-guard watch: a cap is out of range (interval 0.05..86400 s, max-resumes 0..20, "
              "budget-usd 0..1000 and >= 0.01 per restart, idle >= 0, pause 0..86400 s, until HH:MM or +SECONDS)",
              file=sys.stderr)
        raise SystemExit(2)
    return caps, rest


def flags_of(caps: dict) -> list[str]:
    """The caps given, as watcher argv (`until` as the seconds left)."""
    flags = []
    for key, value in caps.items():
        shown = f"+{max(0.0, value - time.time()):.0f}" if key == "until" else value
        flags.append(f"--{key.replace('_', '-')}" + ("" if key == "allow_bypass" else f"={shown}"))
    return flags


def deadline(until: str, now: float | None = None) -> float | None:
    """`HH:MM`: the next such local time; `+SECONDS`: that long from now; anything else: None."""
    now = time.time() if now is None else now
    if re.fullmatch(r"\+\d+(\.\d+)?", until):
        return now + float(until[1:])
    m = re.fullmatch(r"([01]\d|2[0-3]):([0-5]\d)", until)
    if not m:
        return None
    t = time.localtime(now)
    at_day = lambda day: time.mktime((t.tm_year, t.tm_mon, day, int(m[1]), int(m[2]), 0, 0, 0, -1))
    return at_day(t.tm_mday) if at_day(t.tm_mday) > now else at_day(t.tm_mday + 1)


def hook_key(kind: str, text: str) -> str:
    """The event key hooks/run-guard.sh gives a BLOCKED / DONE stop (`cksum` of "<kind> <text>"), so the hook
    and the watcher dedupe on one key."""
    done = subprocess.run(["cksum"], input=f"{kind} {text}".encode(), capture_output=True, timeout=10)
    return f"{kind.lower()}-{done.stdout.split()[0].decode()}"


def side(marker: Path, suffix: str) -> Path:
    return marker.with_name(marker.name + suffix)


def _lines(path: Path, strict: bool = False) -> list[str]:
    """Lines split on \n only: splitlines() also breaks on U+2028, which a session could plant in a model-derived
    line. A file that cannot be read has no lines, or raises when `strict`."""
    try:
        return [x.rstrip("\r") for x in path.read_text(errors="replace").split("\n") if x]
    except OSError:
        if strict:
            raise
        return []


def to_pid(text: str) -> int | None:
    """A pid from untrusted text; anything but plain ASCII digits is an unknown pid, never an error."""
    text = text.strip()
    return int(text) if text.isascii() and text.isdigit() and 0 < len(text) <= 9 and int(text) > 0 else None


def first_wins(pairs) -> dict:
    """A dict of (key, value) pairs where the FIRST occurrence of a key wins: a later line cannot override it."""
    found: dict = {}
    for key, value in pairs:
        found.setdefault(key, value)
    return found


def parse_marker(path: Path) -> dict:
    cells = [line.split("\t") for line in _lines(path)]
    return {"tasks": [(c[1], c[2]) for c in cells if c[0] == "task" and len(c) == 3],
            "states": [c[1] for c in cells if c[0] == "state" and len(c) == 2],
            "meta": first_wins((c[1], c[2]) for c in cells if c[0] == "meta" and len(c) == 3)}


def parse_status(path: Path) -> dict:
    """`.status` key=value lines; the FIRST occurrence of a key wins (the text line is model-derived)."""
    return first_wins((k, v) for k, sep, v in (line.partition("=") for line in _lines(path)) if sep)


def scan(marker: dict) -> dict:
    """What is open, the python twin of run_guard_open in hooks/lib/run-open.sh. `complete` is the evidence
    "finished" needs: at least one target, and every target read. A missing state file is open, not resumable."""
    found = {"open": 0, "missing": 0, "tasks": {}, "paths": [], "complete": bool(marker["tasks"] or marker["states"])}
    for root, task_id in marker["tasks"]:
        todos = Path(root) / "docs" / "tasks_manager" / "_todos"
        try:
            names = os.listdir(todos) if ID_RE.fullmatch(task_id) and os.path.isabs(root) else None
        except OSError:
            names = None
        found["complete"] &= names is not None
        for name in sorted(n for n in names or [] if n.startswith(task_id + "-") and n.endswith(".md"))[:1]:
            found["tasks"][task_id] = todos / name
            found["paths"] += [todos / name, todos.parent / "_runs" / task_id / "state.md"]
    for state in map(Path, marker["states"]):
        found["paths"].append(state)
        try:
            rows = [m for m in map(ROW_RE.match, _lines(state, strict=True)) if m]
            found["open"] += any(m[1].strip() != "committed" for m in rows)
            found["complete"] &= bool(rows)  # a truncated or empty state file is unknown, never "finished"
        except FileNotFoundError:
            found["missing"] += 1
        except OSError:
            found["complete"] = False
    found["open"] += len(found["tasks"]) + found["missing"]
    return found


def _cmdline(pid: int) -> list[str] | None:
    """argv of a process ([] when it is gone), or None where there is no /proc to read it from."""
    if not Path("/proc/self/cmdline").exists():
        return None
    try:
        return Path(f"/proc/{pid}/cmdline").read_bytes().decode(errors="replace").split("\0")
    except OSError:
        return []


def is_claude(pid: int) -> bool:
    """Alive AND still a claude process: a reused pid is a dead session. Without /proc: alive is enough."""
    argv = _cmdline(pid) if _pid_alive(pid) else []
    return argv is None or any("claude" in os.path.basename(a) for a in argv[:2])


def is_watcher(pid: int, session: str) -> bool:
    """True only for a process whose argv holds `run-guard watch --session <session>`, in that order."""
    argv, want = (_cmdline(pid) if _pid_alive(pid) else []) or [], ["run-guard", "watch", "--session", session]
    return any(argv[i:i + 4] == want for i in range(len(argv)))


def watch_file_pid(marker: Path) -> int | None:
    return to_pid("".join(_lines(side(marker, ".watch")))[:12])


def watcher_pid(marker: Path) -> int | None:
    """The pid of the live watcher attached to this marker, verified by its argv; None otherwise."""
    pid = watch_file_pid(marker)
    return pid if pid and is_watcher(pid, marker.name) else None


def stop_watcher(marker: Path) -> None:
    """Terminate this session's watcher; a pid that is not that watcher is never signalled."""
    pid = watcher_pid(marker)
    if pid is not None:
        os.kill(pid, signal.SIGTERM)
        end = time.time() + 2
        while _pid_alive(pid) and time.time() < end:
            time.sleep(0.05)


def spawn(marker: Path, flags: list[str], at_py: Path) -> int | None:
    """Start a detached watcher (own session, every fd closed); returns the pid of the watcher that holds
    `.watch` afterwards: this one, or the one that won a race with it."""
    env = dict(os.environ, AGENTS_RUN_GUARD_DIR=str(marker.parent.resolve()))
    proc = subprocess.Popen([sys.executable, str(at_py), "run-guard", "watch", "--session", marker.name, *flags],
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True, close_fds=True, env=env)
    end = time.time() + 2
    while watcher_pid(marker) != proc.pid and proc.poll() is None and time.time() < end:
        time.sleep(0.05)
    return watcher_pid(marker)


def load_record(marker: Path) -> dict | None:
    """The watch record, None when there is none, {} when it is unreadable or malformed."""
    try:
        rec = json.loads(side(marker, ".watch.state").read_text())
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        return {}
    typed = isinstance(rec, dict) and all(isinstance(rec.get(k, ()), t) for k, t in RECORD_TYPES.items())
    ok = typed and restart_caps_ok(rec) and rec["used"] >= 0 and (rec["child"] is None or rec["child"] > 0)
    return rec if ok else {}


def open_record(marker: Path, caps: dict) -> dict:
    """The record this watcher continues from: new caps can only lower the recorded ones."""
    rec = load_record(marker)
    fresh = {k: caps.get(k, DEFAULTS[k]) for k in RECORD_CAPS}
    fresh.update(used=0, child=None, mode="", sent=[])
    if rec is None:
        return fresh
    if not rec:  # a damaged record must not hand out a fresh count: no restarts are left
        return {**fresh, "used": fresh["max_resumes"], "allow_bypass": False}
    for key in ("max_resumes", "budget_usd"):
        if key in caps:
            rec[key] = min(rec[key], caps[key])
    return rec  # allow_bypass: only ever the first arm's


class Refused(Exception):
    """args: (reason, why); the reason is the event suffix (`refused-<reason>`)."""


def authorise(marker: dict, tasks: dict[str, Path], mode: str, allow_bypass: bool) -> Path:
    """The cwd for a restart in `mode`, re-read from the files right now; raises Refused."""
    if not tasks:
        raise Refused("state-only", "no open task in the marker: a state file alone is never restarted")
    sections = []
    for tid, path in tasks.items():
        text = path.read_text(errors="replace")
        cell = re.search(r"^\|\s*Execution\s*\|([^|\n]*)\|", text, re.M)
        if "unattended" not in [v.strip() for v in (cell[1] if cell else "").split(",")]:
            raise Refused("unmarked", f"{tid} is no longer marked Execution: unattended")
        sec = re.search(r"^### Unattended run[ \t]*\n(.*?)(?=^#{1,3} |\Z)", text, re.M | re.S)
        sections.append(sec[1] if sec else "")
        watch = re.findall(r"^[ \t]*Watch:[ \t]*(.*?)[ \t]*$", sections[-1], re.M)
        if not watch or any(value != "on" for value in watch):  # fail closed: any other Watch: line wins
            raise Refused("unmarked", f"{tid} does not say only `Watch: on` in its Unattended run section")
    if mode == "bypassPermissions":
        if not allow_bypass or not all(re.search(r"^[ \t]*allow bypass[ \t]*$", s, re.M | re.I) for s in sections):
            raise Refused("mode", "the session ran in bypassPermissions; a restart in it needs --allow-bypass on the "
                          "first arm and an `allow bypass` line in every open task's Unattended run section")
    elif mode not in SAFE_MODES:
        raise Refused("mode", "the recorded permission mode is not on the allow-list")
    cwd = Path(marker["meta"].get("cwd", ""))
    real = cwd.resolve() if cwd.is_absolute() and cwd.is_dir() else None
    tree = None
    if real:  # the git work tree the cwd is in
        tree = next((p for p in (real, *real.parents) if (p / ".git").exists()), None)
    inside = [p for p in [*tasks.values(), *map(Path, marker["states"])] if p.is_file()]
    if tree is None or not any(p.resolve().is_relative_to(tree) for p in inside):
        raise Refused("cwd", "the recorded cwd is not a git work tree holding a guarded task or state file")
    return cwd


def stop_time(status_path: Path, status: dict) -> float:
    """When the session last stopped: the status file's `last_stop` (the hook's local time), else its mtime."""
    try:
        return datetime.strptime(status.get("last_stop", ""), "%Y-%m-%dT%H:%M:%S%z").timestamp()
    except ValueError:
        try:
            return status_path.stat().st_mtime
        except OSError:
            return 0.0


def _ascii(text: str, cap: int) -> str:
    return re.sub(r"[^\x20-\x7e]", " ", text)[:cap]


class Watcher:
    def __init__(self, marker: Path, caps: dict, at_bin: Path):
        self.marker, self.at_bin, self.session = marker, at_bin, marker.name
        own = {**DEFAULTS, **caps}  # this watcher's own timing, never the record's
        self.interval, self.pause, self.idle = own["interval"], own["pause"], own["idle"]
        self.until = own["until"] if own["until"] is not None else math.inf
        self.rec, self.proc, self.pause_until, self.cwd = {}, None, None, None
        self.supervised, self.waited = bool(os.environ.get("AGENTS_SUPERVISOR")), None
        self.floor = time.time()  # idle counts from the later of this and the last target change

    def log(self, message: str) -> None:
        path = side(self.marker, ".watch.log")
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S%z')} {_ascii(message, 400)}\n"
        try:
            if path.is_file() and path.stat().st_size > LOG_CAP:  # simplicity: start over; a log, not evidence
                path.unlink()
            fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            os.write(fd, line.encode())
            os.close(fd)
        except OSError:
            pass  # a log that cannot be written never stops the watcher

    def save(self) -> None:
        path = side(self.marker, ".watch.state")
        tmp = side(self.marker, f".watch.state.{os.getpid()}")
        tmp.unlink(missing_ok=True)
        fd = os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        os.write(fd, json.dumps(self.rec).encode())
        os.close(fd)
        os.replace(tmp, path)

    def claim(self) -> bool:
        """Exclusive create of `.watch`; a live watcher already there wins, a stale file is replaced."""
        other = watcher_pid(self.marker)
        if other and other != os.getpid():
            self.log(f"another watcher (pid {other}) is attached; exiting")
            return False
        side(self.marker, ".watch").unlink(missing_ok=True)  # stale: its pid is no live watcher of this session
        try:  # of two racing watchers one create fails; a later take-over makes the other exit at its next tick
            fd = os.open(side(self.marker, ".watch"), os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        except OSError as err:
            self.log(f"cannot claim .watch: {err}")
            return False
        os.write(fd, f"{os.getpid()}\n".encode())
        os.close(fd)
        return True

    def release(self) -> None:
        if watch_file_pid(self.marker) == os.getpid():
            side(self.marker, ".watch").unlink(missing_ok=True)

    def send(self, event: str, title: str, reason: str, ids: str, shared: bool = False, once: bool = True) -> None:
        """Notify once per record; `once=False` (the events that end a watcher) every time. Only the hook's
        shared events (finished, blocked) pass `--event`."""
        if once and event in self.rec["sent"]:
            return
        # `at notify` runs in OUR cwd: it reads the notify command's git config there, and the marker's cwd is
        # session-written (missing, or a repository with its own notify command)
        extra = ["--event", event, "--session", self.session] if shared else []
        if self.at(f"notify {event} ({title})", ["notify", _ascii(title, 200), *extra],
                   f"tasks: {ids}\nreason: {_ascii(reason, 300)}\n") == 0 and once:
            self.rec["sent"].append(event)
            self.save()

    def at(self, what: str, args: list[str], stdin: str = "", cwd: str | None = None) -> int | None:
        """Run `at <args>` (notify, task report) in `cwd` (default: ours); log what it really returned. It may
        be missing or fail."""
        try:
            p = subprocess.run([str(self.at_bin), *args], input=stdin, text=True, stdout=subprocess.DEVNULL,
                               stderr=subprocess.PIPE, timeout=120, cwd=cwd)
        except (OSError, subprocess.SubprocessError) as err:
            self.log(f"{what}: failed: {err}")
            return None
        self.log(f"{what}: exited {p.returncode}" + (f": {p.stderr.strip()[-200:]}" if p.returncode else ""))
        return p.returncode

    def report(self, id_list: list[str]) -> None:
        """The morning report of the runs that still have a run directory: a closed-out run's directory is gone and
        its committed report is richer than anything rebuilt from the archive. A failed report is said."""
        runs = Path(self.cwd or "/nonexistent") / "docs" / "tasks_manager" / "_runs"
        ids = [tid for tid in id_list if (runs / tid / "state.md").is_file()]
        if ids and self.at(f"report {' '.join(ids)}", ["task", "report", *ids], cwd=self.cwd) != 0:
            text = f"Morning report not written: run `at task report {' '.join(ids)}`"
            self.send("report-failed", text, text, " ".join(ids), once=False)

    def restart_alive(self) -> bool:
        """A restart this watcher (or an earlier one, per the record) started is still running."""
        if self.proc is not None and self.proc.poll() is not None:
            self.log(f"restart {self.rec['used']} exited {self.proc.returncode}")
            self.proc, self.floor = None, time.time()
        if self.proc is None and self.rec["child"] is not None and not is_claude(self.rec["child"]):
            self.rec["child"] = None
            self.save()
        return self.proc is not None or self.rec["child"] is not None

    def tick(self) -> int | None:
        """One look at the marker; returns an exit code to stop, None to keep watching."""
        if not self.marker.is_file() or watch_file_pid(self.marker) != os.getpid() or time.time() >= self.until:
            self.log("the marker is gone, another watcher took over, or --until passed; exiting")
            return 0
        marker, status = parse_marker(self.marker), parse_status(side(self.marker, ".status"))
        self.cwd = marker["meta"].get("cwd") or None  # only `at task report` runs there: it needs the run's repository
        if status.get("mode") and status["mode"] != self.rec["mode"]:
            self.rec["mode"] = _ascii(status["mode"], 40)
            self.save()
        id_list = [tid for _, tid in marker["tasks"] if ID_RE.fullmatch(tid)]
        ids, kind, found = " ".join(id_list), status.get("kind", ""), scan(marker)
        if found["complete"] and (kind == "DONE" or found["open"] == 0):
            # the hook's own key for DONE: one "finished" message whichever side sees it first
            self.send(hook_key("DONE", "nothing is open"), f"Run finished: {ids}", "nothing is open", ids, True)
            self.report(id_list)
            side(self.marker, ".watch.state").unlink(missing_ok=True)
            return 0
        stop = stop_time(side(self.marker, ".status"), status)  # `.status` is written only at a stop the hook allows
        stale = any(p.stat().st_mtime >= stop + 1 for p in found["paths"] if p.is_file())
        if self.supervised and kind == "WAITING" and status.get("text", "").startswith("supervisor") and not stale:
            if self.waited != stop:  # parked on the supervisor: not dead, no restart, no budget; said once per wait
                self.waited = stop
                self.log("waiting on supervisor")
            return None
        pid = to_pid(marker["meta"].get("pid", ""))
        alive = self.restart_alive() or pid is None or is_claude(pid)
        if kind == "BLOCKED" and not stale:
            text = _ascii(status.get("text", ""), 300)
            self.send(hook_key("BLOCKED", text), f"Run BLOCKED: {ids} {text}", text, ids, True)
            return None if alive else 0
        if alive or not found["complete"]:  # an unread target is never taken for "finished" or for "dead"
            changed = max([self.floor] + [p.stat().st_mtime for p in found["paths"] if p.is_file()])
            if kind in ("GAVE_UP", "EMPTY") or time.time() - changed >= self.idle * 60:
                self.send("idle", f"Run idle: {ids}", f"no progress (last stop: {kind or 'none'}); not restarted", ids)
            return None
        used, cap = self.rec["used"], self.rec["max_resumes"]
        if found["open"] == found["missing"] or used >= cap:
            why = (f"the session died again after {used} restart(s)" if used >= cap
                   else "only missing state files are open")
            self.send("gave-up", f"Run gave up: {ids}", why, ids, once=False)
            return 0
        if self.pause_until is None:  # a growing pause, then look again before restarting
            pause = self.pause * 2 ** used
            self.pause_until = time.time() + pause
            self.log(f"session {pid} is dead with work open; restart {used + 1} after a pause of {pause:g} s")
            return None
        if time.time() < self.pause_until:
            return None
        self.pause_until = None
        return self.restart(marker, found["tasks"], status, ids)

    def restart(self, marker: dict, tasks: dict, status: dict, ids: str) -> int | None:
        mode = status.get("mode") or self.rec["mode"] or "default"
        try:
            cwd = authorise(marker, tasks, mode, self.rec["allow_bypass"])
            if not (claude := shutil.which("claude")):
                raise Refused("no-claude", "no claude on PATH")
        except Refused as refused:
            self.send(f"refused-{refused.args[0]}", f"Run not restarted: {ids}", refused.args[1], ids, once=False)
            return 0
        self.rec["used"] += 1
        self.save()  # counted before it starts: a watcher killed now cannot hand out the same restart twice
        n, budget = self.rec["used"], f"{share(self.rec):.2f}"
        env = {k: v for k, v in os.environ.items() if k not in SESSION_ENV}
        self.proc = subprocess.Popen(  # an OSError here is logged by main as a failed tick; the restart stays counted
            [claude, "--resume", self.session, "-p", "--permission-mode", mode, "--max-budget-usd", budget,
             "--", RESUME_PROMPT], cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, start_new_session=True)
        self.rec["child"] = self.proc.pid
        self.save()
        self.log(f"restart {n}/{self.rec['max_resumes']}: pid {self.proc.pid}, mode {mode}, budget {budget} USD")
        if self.supervised:  # the supervisor's event log; sup_event.py never fails and is bounded here
            task = [] if os.environ.get("AGENTS_SUP_TASK") else ["--task", *list(tasks)[:1]]
            try:
                subprocess.run([sys.executable, str(Path(__file__).with_name("sup_event.py")), "restarted", "--session",
                                self.session, *task], timeout=5, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except (OSError, subprocess.SubprocessError):
                pass
        self.send(f"restarted-{n}", f"Run restarted ({n}/{self.rec['max_resumes']}): {ids}",
                  f"the session process was dead; restarted headless with a {budget} USD cap", ids)
        return None


def main(marker: Path, args: list[str], at_bin: Path) -> int:
    caps, _ = parse_caps(args)
    if not shutil.which("cksum"):  # hook_key needs it: without it every tick would fail
        print("at: run-guard watch: no `cksum` on PATH (the hook's event keys need it)", file=sys.stderr)
        return 2
    watcher = Watcher(marker, caps, at_bin)
    if not watcher.claim():
        return 0
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))  # disarm: leave through `finally`
    try:
        rec = watcher.rec = open_record(marker, caps)
        if not restart_caps_ok(rec):  # the 0.01 floor, on the merged caps
            why = f"less than 0.01 USD per restart ({rec['budget_usd']} USD over {rec['max_resumes']} restarts)"
            print(f"at: run-guard watch: {why}", file=sys.stderr)
            watcher.log(why)
            return 2
        watcher.save()
        watcher.log(f"watching (pid {os.getpid()}); record: {json.dumps(watcher.rec)}")
        while True:
            try:
                code = watcher.tick()
            except OSError as err:  # a file vanished between two reads: look again next tick
                watcher.log(f"tick failed: {err}")
                code = None
            if code is not None:
                return code
            wait = watcher.interval
            if watcher.pause_until is not None:  # wake for the end of a pause
                wait = min(wait, max(0.05, watcher.pause_until - time.time()))
            time.sleep(wait)
    finally:
        if watcher.proc is not None and watcher.proc.poll() is None:
            watcher.log(f"exiting; restart pid {watcher.proc.pid} is still running")
        watcher.release()
