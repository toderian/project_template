"""`at sup status`, `at sup done`, `at sup measure`: what the owner reads, and what "done" means in code.

digest(profile) -> str        one screen, under 60 lines: owner questions, packs with one state word per task
                              (waiting-to-start|running|waiting|stopped|closed-out|landed), workers, leases, events
done_check(profile, pack, hub) -> list[str]   one line per failed item; empty means done
measure(profile, since)       trial numbers from events, queue and touch.log only

A task is closed out when no docs/tasks_manager/_todos/<ID>-*.md exists on its branch task/<ID>, or, when the
branch is gone, on the default branch. Hub root: `sup_state.hub`: `--hub`, else the profile's config, else the git toplevel of the cwd.
Exit codes: 0 ok, 2 usage, 3 refused. stdlib only.
"""
from __future__ import annotations

import datetime
import json
import statistics
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import lease
import sup_state

TODOS = "docs/tasks_manager/_todos/"
MAX_LINES = 59
TASK_STATES = ("waiting-to-start", "running", "waiting", "stopped", "closed-out", "landed")


def _git(hub: Path, *args: str) -> tuple[int, str]:
    p = subprocess.run(["git", "-C", str(hub), *args], capture_output=True, text=True)
    return p.returncode, p.stdout


def _has_todo(hub: Path, ref: str, task: str) -> bool:
    rc, out = _git(hub, "ls-tree", "--name-only", ref, TODOS)
    return rc == 0 and any(Path(n).name.startswith(f"{task}-") for n in out.splitlines())


def _default_ref(hub: Path) -> str:
    for name in ("main", "master"):
        if _git(hub, "rev-parse", "--verify", "-q", f"refs/heads/{name}")[0] == 0:
            return f"refs/heads/{name}"
    return "HEAD"


def closed_out(hub: Path, task: str, default_ref: str | None = None) -> bool:
    branch = f"refs/heads/task/{task}"
    if _git(hub, "rev-parse", "--verify", "-q", branch)[0] == 0:
        return not _has_todo(hub, branch, task)
    return not _has_todo(hub, default_ref or _default_ref(hub), task)


def _epoch(ts) -> float | None:
    try:
        return datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z").timestamp()
    except (TypeError, ValueError):
        return None


def _leases() -> list[dict]:
    rows = []
    with lease.locked() as d:
        for p in sorted(d.glob("*.json")):
            rec, st = lease.read(d, p.stem)
            if rec:
                rows.append({"resource": p.stem, "state": st, "task": rec.get("task")})
    return rows


def task_states(profile: str, pack: dict, hub: Path, events: list[dict] | None = None) -> dict[str, str]:
    events = sup_state.events_since(profile, 0) if events is None else events
    landed = {e.get("task") for e in events if e.get("kind") == "landed"}
    ref = _default_ref(hub)
    out = {}
    for t in pack["tasks"]:
        w = sup_state.worker_for(profile, task=t)
        if t in landed:
            out[t] = "landed"
        elif closed_out(hub, t, ref):
            out[t] = "closed-out"
        elif w and w.get("state") in ("running", "waiting"):
            out[t] = w["state"]
        elif w or any(e.get("kind") in ("done", "stopped") and e.get("task") == t for e in events):
            out[t] = "stopped"
        else:
            out[t] = "waiting-to-start"
    return out


def done_check(profile: str, pack_name: str, hub: Path) -> list[str]:
    pack = sup_state.read_pack(profile, pack_name)
    if pack is None:
        raise ValueError(f"no pack {pack_name!r}")
    states = task_states(profile, pack, hub)
    tasks = set(pack["tasks"])
    bad = []
    for t, s in states.items():
        if s in ("waiting-to-start", "running", "waiting", "stopped"):
            bad.append(f"{t}: not closed out ({s})")
        elif s == "closed-out":
            bad.append(f"{t}: closed out but not landed")
    bad += [f"{w['task']}: live worker {w['session']} ({w['state']})"
            for w in sup_state.live_workers(profile) if w.get("task") in tasks]
    bad += [f"{q['id']}: open blocking question for {q['task']}"
            for q in sup_state.queue(profile) if q.get("task") in tasks and q.get("blocking")]
    bad += [f"lease {r['resource']} {r['state']} by {r['task']}" for r in _leases() if r["task"] in tasks]
    return bad


def _cut(s, n: int = 110) -> str:
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1] + "…"


def _capped(rows: list[str], limit: int) -> list[str]:
    return rows if len(rows) <= limit else rows[:limit] + [f"  … {len(rows) - limit} more"]


def _age(ts, now: float) -> str:
    t = _epoch(ts)
    if t is None:
        return "?"
    m = max(0, int((now - t) // 60))
    return f"{m}m" if m < 120 else f"{m // 60}h"


def digest(profile: str, hub: Path | None = None) -> str:
    hub = hub or sup_state.hub(profile)
    now = time.time()
    events = sup_state.events_since(profile, 0)
    out = [f"supervisor {profile}  {sup_state.now()}"]

    qs = [f"  {q['id']} {q.get('task') or '-'}: {_cut(q.get('question'), 70)} -> {_cut(q.get('recommendation') or '-', 30)}"
          for q in sup_state.queue(profile)]
    out += [f"OPEN QUESTIONS ({len(qs)})"] + _capped(qs, 6)

    rows = []
    for p in sup_state.list_packs(profile):
        st = task_states(profile, p, hub, events)
        rows.append(f"  {p['name']} [{p.get('state')}]")
        rows += textwrap.wrap(", ".join(f"{t} {s}" for t, s in st.items()), 118,
                              initial_indent="    ", subsequent_indent="    ")
    out += [f"PACKS ({len(sup_state.list_packs(profile))})"] + _capped(rows, 18)

    ws = [f"  {w.get('task')} {str(w.get('session'))[:8]} {w.get('state')} {w.get('waiting_for') or '-'} {_age(w.get('started'), now)}"
          for w in sup_state.workers(profile)]
    out += [f"WORKERS ({len(ws)})  task session state waiting_for age"] + _capped(ws, 6)

    ls = [f"  {r['resource']} {r['task'] or '-'} {r['state']}" for r in _leases()]
    out += [f"LEASES ({len(ls)})  resource holder state"] + _capped(ls, 4)

    new = sup_state.events_since(profile)
    need = sum(1 for e in new if e.get("kind") not in sup_state.NO_JUDGEMENT)
    out.append(f"EVENTS unhandled: {len(new)} ({need} need a tick)")
    out += [f"  #{e['id']} {e.get('kind')} {e.get('task') or '-'}" for e in new[-5:]]
    return "\n".join(out[:MAX_LINES]) + "\n"


def _since_ok(ts, since: str | None) -> bool:
    return since is None or str(ts or "")[:10] >= since


def measure(profile: str, since: str | None = None) -> dict:
    events = [e for e in sup_state.events_since(profile, 0) if _since_ok(e.get("ts"), since)]
    count = lambda kind: sum(1 for e in events if e.get("kind") == kind)  # noqa: E731
    asked = {e.get("q"): e for e in events if e.get("kind") == "ask" and e.get("q")}
    qs = [q for q in sup_state.queue(profile, open_only=False) if _since_ok(q.get("ts"), since)]
    mins = []
    for q in qs:
        t0 = _epoch((asked.get(q.get("id")) or q).get("ts"))
        t1 = _epoch(q.get("answered"))
        if q.get("answer") is not None and t0 is not None and t1 is not None:
            mins.append(max(0.0, (t1 - t0) / 60))
    try:
        touches = [ln for ln in (sup_state.profile_dir(profile) / "touch.log").read_text(encoding="utf-8").splitlines()
                   if ln.strip() and _since_ok(ln.split("\t")[0], since)]
    except OSError:
        touches = []
    wall = {}
    for p in sup_state.list_packs(profile):
        starts = [_epoch(e.get("ts")) for e in events if e.get("kind") == "started" and e.get("task") in p["tasks"]]
        ends = [_epoch(e.get("ts")) for e in events if e.get("kind") == "landed" and e.get("task") in p["tasks"]]
        starts, ends = [x for x in starts if x is not None], [x for x in ends if x is not None]
        if starts and ends:
            wall[p["name"]] = round((max(ends) - min(starts)) / 60, 1)
    return {
        "since": since, "owner_touches": len(touches), "questions": len(qs),
        "answered_by_sup": sum(1 for q in qs if q.get("by") == "sup"),
        "answered_by_owner": sum(1 for q in qs if q.get("by") == "owner"),
        "answer_minutes_median": round(statistics.median(mins), 1) if mins else None,
        "answer_minutes_max": round(max(mins), 1) if mins else None,
        "worker_restarts": count("restarted"), "dead_workers": count("dead"), "tick_failures": count("tick_failed"),
        "tasks_landed": count("landed"), "pack_wall_minutes": wall,
    }


def _profile(args) -> str | None:
    try:
        profile = sup_state.current_profile(args.profile)
    except ValueError as e:
        print(f"at: sup: {e}", file=sys.stderr)
        return None
    if profile is None:
        print("at: sup: no profile; pass --profile or set AGENTS_SUPERVISOR", file=sys.stderr)
    return profile


def cmd_status(args) -> int:
    profile = _profile(args)
    if profile is None:
        return 2
    try:
        hub = sup_state.hub(profile, args.hub)
    except ValueError as e:
        print(f"at: sup: {e}", file=sys.stderr)
        return 2
    text = digest(profile, hub)
    if args.json:
        print(json.dumps({"profile": profile, "lines": text.splitlines()}))
    else:
        print(text, end="")
    return 0


def cmd_done(args) -> int:
    profile = _profile(args)
    if profile is None:
        return 2
    try:
        bad = done_check(profile, args.pack, sup_state.hub(profile, args.hub))
    except ValueError as e:
        print(f"at: sup: {e}", file=sys.stderr)
        return 2
    for line in bad:
        print(line)
    if bad:
        return 3
    print(f"done: {args.pack}")
    return 0


def cmd_measure(args) -> int:
    profile = _profile(args)
    if profile is None:
        return 2
    if args.since:
        try:
            datetime.date.fromisoformat(args.since)
        except ValueError:
            print("at: sup: --since must be an ISO date (YYYY-MM-DD)", file=sys.stderr)
            return 2
    m = measure(profile, args.since)
    if args.json:
        print(json.dumps(m))
        return 0
    for k, v in m.items():
        print(f"{k}: {json.dumps(v) if isinstance(v, dict) else v}")
    return 0


def register(sup_sub) -> None:
    for name, func, help_ in (("status", cmd_status, "print the digest"),
                              ("done", cmd_done, "check that a pack is done"),
                              ("measure", cmd_measure, "print the trial numbers")):
        p = sup_sub.add_parser(name, help=help_)
        p.add_argument("--profile")
        if name != "measure":
            p.add_argument("--hub", help="hub checkout (default: the profile's hub, else the cwd's git toplevel)")
        if name == "done":
            p.add_argument("pack")
        else:
            p.add_argument("--json", action="store_true")
        if name == "measure":
            p.add_argument("--since", help="ISO date")
        p.set_defaults(func=func)
