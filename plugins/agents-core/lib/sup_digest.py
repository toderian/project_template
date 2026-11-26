"""`at sup status`, `at sup done`, `at sup measure`: what the owner reads, and what "done" means in code.

digest(profile) -> str        one screen, under 60 lines: owner questions (blocking first), packs with one state word per
                              task (waiting-to-start|running|waiting|stopped|closed-out|landed|unknown), live workers,
                              leases, events
done_check(profile, pack, hub) -> list[str]   one line per failed item; empty means done
measure(profile, since)       trial numbers from events, queue, ticks.jsonl and touch.log only

A task is closed out when its branch task/<ID> (else the default branch) holds a file `<ID>-*.md` under
docs/tasks_manager/_todos_archived/ and none under _todos/ (`sup.archived_file`). A git failure is an error, never
"closed out": the task shows `unknown` and `done` names it. A live worker shows as running or waiting before anything else.
Hub root: `sup_state.hub`: `--hub`, else the profile's config, else the git toplevel of the cwd.

Done check, built from the hub and the state: the task landed (`sup_state.landed`); its file is archived on the default
branch; no live worker; no open blocking question; no lease held or owed; the archived file has no unchecked checkbox under
a `Phase N` heading and no open entry (a list item not checked `[x]`) in a `Parked` section; every branch the pack records
(`branches: {repo: branch}`, repo = the hub or a sibling directory of the hub) exists.
Spec items of "Done check" not built: the run's final review passed, and the checks ran (the run state `_runs/<ID>/` lives
in the worker's worktree and is gone after landing, so the hub and the state hold no record of either); downstream pins
(no manifest names them); and "commits exist on the named branches" beyond the branch existing, and the task file's Repos
row (not parsed: a repo's reason for having no branch is free text).
Exit codes: 0 ok, 2 usage, 3 refused. stdlib only.
"""
from __future__ import annotations

import datetime
import json
import re
import statistics
import sys
import textwrap
import time
from pathlib import Path

import lease
import sup_state

TASK_STATES = ("waiting-to-start", "running", "waiting", "stopped", "closed-out", "landed", "unknown")
UNCHECKED = re.compile(r"\s*[-*]\s+\[ \]")
HEADING = re.compile(r"(#{1,6})\s+(.*)")


class GitError(ValueError):
    pass


def _sup():
    import sup  # lib/sup.py; imported late: sup.add_parser imports this module
    return sup


def _branch(hub: Path, task: str) -> str:
    sup = _sup()
    rc = sup.git(hub, "rev-parse", "--verify", "-q", f"refs/heads/task/{task}").returncode
    if rc not in (0, 1):
        raise sup.Refuse(f"git failed in {hub}")
    return f"task/{task}" if rc == 0 else sup.default_branch(hub)


def closed_out(hub: Path, task: str) -> bool:
    sup = _sup()
    try:
        return bool(sup.archived_file(hub, task, _branch(hub, task)))
    except sup.Refuse as e:
        raise GitError(str(e))


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
    out = {}
    for t in pack["tasks"]:
        w = sup_state.worker_for(profile, task=t)
        try:
            if sup_state.landed(profile, t, hub):
                out[t] = "landed"
            elif w and w.get("state") in ("running", "waiting"):
                out[t] = w["state"]
            elif closed_out(hub, t):
                out[t] = "closed-out"
            elif w or any(e.get("kind") in ("done", "stopped") and e.get("task") == t for e in events):
                out[t] = "stopped"
            else:
                out[t] = "waiting-to-start"
        except (GitError, ValueError):
            out[t] = "unknown"
    return out


def _section_problems(text: str) -> list[str]:
    """Unchecked checkboxes under `Phase N` headings and open entries in a `Parked` section of a task file."""
    bad, scope, level = [], None, 0
    for ln in text.splitlines():
        h = HEADING.match(ln)
        if h:
            title = h.group(2).strip()
            if re.match(r"Phase\s+\d+", title, re.I):
                scope, level = "phase", len(h.group(1))
            elif re.match(r"Parked\b", title, re.I):
                scope, level = "parked", len(h.group(1))
            elif scope == "parked" and len(h.group(1)) > level:
                pass  # a sub-heading stays inside the Parked section
            else:
                scope = None
            continue
        if scope == "phase" and UNCHECKED.match(ln):
            bad.append(f"unchecked phase item: {ln.strip()[:60]}")
        elif scope == "parked" and re.match(r"\s*[-*]\s+\S", ln) and not re.match(r"\s*[-*]\s+\[[xX]\]", ln):
            bad.append(f"open Parked entry: {ln.strip()[:60]}")
    return bad


def _branch_exists(hub: Path, repo: str, branch: str) -> bool:
    sup = _sup()
    d = hub if repo in (".", hub.name) else hub.parent / repo
    return d.is_dir() and sup.git(d, "rev-parse", "--verify", "-q", f"{branch}^{{commit}}").returncode == 0


def done_check(profile: str, pack_name: str, hub: Path) -> list[str]:
    pack = sup_state.read_pack(profile, pack_name)
    if pack is None:
        raise ValueError(f"no pack {pack_name!r}")
    sup = _sup()
    states = task_states(profile, pack, hub)
    tasks = set(pack["tasks"])
    bad = []
    for t, s in states.items():
        if s != "landed":
            bad.append(f"{t}: not landed ({s})")
            continue
        try:
            default = sup.default_branch(hub)
            f = sup.archived_file(hub, t, default)
            if not f:
                bad.append(f"{t}: task file is not archived on {default}")
            else:
                bad += [f"{t}: {m}" for m in _section_problems(sup.git_out(hub, "show", f"refs/heads/{default}:{f}"))]
        except sup.Refuse as e:
            bad.append(f"{t}: cannot check the archived file: {e}")
    bad += [f"{w['task']}: live worker {w['session']} ({w['state']})"
            for w in sup_state.live_workers(profile) if w.get("task") in tasks]
    bad += [f"{q['id']}: open blocking question for {q['task']}"
            for q in sup_state.queue(profile) if q.get("task") in tasks and q.get("blocking")]
    bad += [f"lease {r['resource']} {r['state']} by {r['task']}" for r in _leases() if r["task"] in tasks]
    bad += [f"branch {b} of {repo} does not exist" for repo, b in (pack.get("branches") or {}).items()
            if not _branch_exists(hub, repo, b)]
    return bad


def _capped(rows: list[str], limit: int, urgent: str = "") -> list[str]:
    """The first `limit` rows; callers sort what matters first. `urgent` marks rows to count in the "more" line."""
    if len(rows) <= limit:
        return rows
    hidden = [r for r in rows[limit:] if urgent and urgent in r]
    return rows[:limit] + [f"  … {len(rows) - limit} more" + (f" ({len(hidden)} blocking)" if hidden else "")]


def _age(ts, now: float) -> str:
    t = _epoch(ts)
    if t is None:
        return "?"
    m = max(0, int((now - t) // 60))
    return f"{m}m" if m < 120 else f"{m // 60}h"


def _cut(s, n: int = 70) -> str:
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1] + "…"


def _kind(v) -> str:
    return v if isinstance(v, str) and v in sup_state.EVENT_KINDS else "?"


def _task(v) -> str:
    return v if isinstance(v, str) and sup_state.TASK.match(v) else "?"


def digest(profile: str, hub: Path | None = None, for_prompt: bool = False) -> str:
    """`for_prompt=True` (the tick's prompt): question ids, tasks and the blocking mark only, no worker text.
    In every mode an event shows its kind only when it is in EVENT_KINDS and its task only when it matches TASK."""
    hub = hub or sup_state.hub(profile)
    now = time.time()
    events = sup_state.events_since(profile, 0)
    out = [f"supervisor {profile}  {sup_state.now()}"]

    qrows = sorted(sup_state.queue(profile), key=lambda q: not q.get("blocking"))
    qs = []
    for q in qrows:
        line = f"  {q['id']} {_task(q['task']) if q.get('task') else '-'}{' BLOCKING' if q.get('blocking') else ''}"
        if not for_prompt:
            line += f": {_cut(q.get('question'))} -> {_cut(q.get('recommendation') or '-', 30)}"
        qs.append(line)
    out += [f"OPEN QUESTIONS ({len(qs)}{'; text: at sup queue' if for_prompt else ''})"] + _capped(qs, 6, " BLOCKING")

    rows = []
    for p in sup_state.list_packs(profile):
        st = task_states(profile, p, hub, events)
        rows.append(f"  {p['name']} [{p.get('state')}]")
        rows += textwrap.wrap(", ".join(f"{t} {s}" for t, s in st.items()), 118,
                              initial_indent="    ", subsequent_indent="    ")
    out += [f"PACKS ({len(sup_state.list_packs(profile))})"] + _capped(rows, 18)

    order = {"waiting": 0, "running": 1, "stopped": 2}
    rows_w = sorted((w for w in sup_state.workers(profile) if w.get("state") != "done"),
                    key=lambda w: order.get(w.get("state"), 3))
    ndone = sum(1 for w in sup_state.workers(profile) if w.get("state") == "done")
    ws = [f"  {w.get('task')} {str(w.get('session'))[:8]} {w.get('state')} {w.get('waiting_for') or '-'} {_age(w.get('started'), now)}"
          for w in rows_w]
    out += [f"WORKERS ({len(ws)}, {ndone} done hidden)  task session state waiting_for age"] + _capped(ws, 6)

    ls = [f"  {r['resource']} {r['task'] or '-'} {r['state']}" for r in _leases()]
    out += [f"LEASES ({len(ls)})  resource holder state"] + _capped(ls, 4)

    new = sup_state.events_since(profile)
    need = sum(1 for e in new if e.get("kind") not in sup_state.NO_JUDGEMENT)
    out.append(f"EVENTS unhandled: {len(new)} ({need} need a tick)")
    out += [f"  #{e['id']} {_kind(e.get('kind'))} {_task(e['task']) if e.get('task') else '-'}" for e in new[-5:]]
    return "\n".join(out) + "\n"  # at most 1+8+20+8+6+7 = 50 lines by the caps above


def _norm_since(since: str | None) -> str | None:
    return None if since is None else datetime.date.fromisoformat(since).isoformat()


def _since_ok(ts, since: str | None) -> bool:
    return since is None or str(ts or "")[:10] >= since


def _median_max(mins: list[float]) -> tuple:
    return (round(statistics.median(mins), 1), round(max(mins), 1)) if mins else (None, None)


def _ticks(profile: str, since: str | None) -> list[dict]:
    """The rows of ticks.jsonl (one JSON object per line: ts, events, cost, duration, ok)."""
    try:
        lines = (sup_state.profile_dir(profile) / "ticks.jsonl").read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows = []
    for ln in lines:
        try:
            rec = json.loads(ln)
        except ValueError:
            continue
        if isinstance(rec, dict) and _since_ok(rec.get("ts"), since):
            rows.append(rec)
    return rows


def _num(v) -> float:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0


def measure(profile: str, since: str | None = None) -> dict:
    since = _norm_since(since)
    events = [e for e in sup_state.events_since(profile, 0) if _since_ok(e.get("ts"), since)]
    by_kind: dict[str, int] = {}
    for e in events:
        by_kind[str(e.get("kind"))] = by_kind.get(str(e.get("kind")), 0) + 1
    count = lambda kind: by_kind.get(kind, 0)  # noqa: E731
    asked = {e.get("q"): e for e in events if e.get("kind") == "ask" and e.get("q")}
    qs = [q for q in sup_state.queue(profile, open_only=False) if _since_ok(q.get("ts"), since)]
    mins = []
    for q in qs:
        t0 = _epoch((asked.get(q.get("id")) or q).get("ts"))
        t1 = _epoch(q.get("answered"))
        if q.get("answer") is not None and t0 is not None and t1 is not None:
            mins.append(max(0.0, (t1 - t0) / 60))
    restart = []  # minutes from an answer to the same task's next `restarted`
    for e in events:
        if e.get("kind") != "answered" or not e.get("task"):
            continue
        nxt = next((r for r in events if r.get("kind") == "restarted" and r.get("task") == e["task"] and r["id"] > e["id"]), None)
        t0, t1 = _epoch(e.get("ts")), _epoch(nxt.get("ts")) if nxt else None
        if t0 is not None and t1 is not None:
            restart.append(max(0.0, (t1 - t0) / 60))
    try:  # `sup:` lines are the supervisor's own commands, not the owner's touches
        lines = (sup_state.profile_dir(profile) / "touch.log").read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = []
    touches = [ln for ln in lines if ln.strip() and _since_ok(ln.split("\t")[0], since)
               and not ln.partition("\t")[2].startswith("sup:")]
    ticks = _ticks(profile, since)
    wall = {}
    for p in sup_state.list_packs(profile):
        starts = [_epoch(e.get("ts")) for e in events if e.get("kind") == "started" and e.get("task") in p["tasks"]]
        ends = [_epoch(e.get("ts")) for e in events if e.get("kind") == "landed" and e.get("task") in p["tasks"]]
        starts, ends = [x for x in starts if x is not None], [x for x in ends if x is not None]
        if starts and ends:
            wall[p["name"]] = round((max(ends) - min(starts)) / 60, 1)
    med, mx = _median_max(mins)
    rmed, rmx = _median_max(restart)
    return {
        "since": since, "owner_touches": len(touches), "questions": len(qs),
        "answered_by_sup": sum(1 for q in qs if q.get("by") == "sup"),
        "answered_by_owner": sum(1 for q in qs if q.get("by") == "owner"),
        "answer_minutes_median": med, "answer_minutes_max": mx,
        "answer_to_restart_minutes_median": rmed, "answer_to_restart_minutes_max": rmx,
        "events": len(events), "events_by_kind": dict(sorted(by_kind.items())),
        "ticks": len(ticks), "tick_failures": sum(1 for t in ticks if not t.get("ok")),
        "tick_cost_total": round(sum(_num(t.get("cost")) for t in ticks), 4),
        "tick_duration_total": round(sum(_num(t.get("duration")) for t in ticks), 1),
        "worker_restarts": count("restarted"), "dead_workers": count("dead"), "tick_failed_events": count("tick_failed"),
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
            _norm_since(args.since)
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
