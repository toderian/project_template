"""`at sup ask|need|release|inbox|answer|grant|deny|queue|instruct|instructions`: questions, leases and answers.

Worker side (task from --task or AGENTS_SUP_TASK, session from CLAUDE_CODE_SESSION_ID): `ask` queues a question
for the owner and `need` takes a lease or asks for it. Both set the worker row to `waiting` and print the last
line the worker ends its turn with, `WAITING supervisor: <Q-id or resource>`. `inbox` shows the answers.
Supervisor and owner side: `answer` closes a question (first answer wins) and puts the answer in the task's
inbox; `grant` and `deny` settle a `need`; `queue` lists the owner's open questions. A row set to `stopped`
with `waiting_for` None is what the watcher wakes. Chat-only commands (`instruct`, `answer --owner`, and the ones in the
other parts: sup_guard.CHAT_COMMANDS but `pack`) call `require_chat()`: allowed in a plain shell, and in a Claude session only with
the chat token of that session (sup_guard.check_chat_token).

Trust model: a worker runs under the same uid as the state directory, so nothing here is a fence against a worker. The
checks stop the guarded supervisor (tick or chat) and honest mistakes: supervisor- and owner-side commands (`answer`,
`grant`, `deny`, `instruct`, `escalate`) refuse when AGENTS_SUP_TASK is set or the caller's session is a registered
worker of the profile, and chat-only ones also without a chat token. `touch.log` and `by: owner` are records, not proof.
`ask` and `need` never create a worker row: they update the row found by session id, else by task, else refuse (3).
`answer` without --owner takes worker questions only; `escalate --q <Q-id>` links an entry to the worker question it is about.
Exit codes: 0 ok, 2 usage, 3 refused. stdlib only.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import time

import lease
import sup_state as st

REFUSED = "at: sup: only the owner's chat may run this"
REFUSED_WORKER = "at: sup: a worker session may not run this"
DEFAULT_MINUTES = 30
MAX_MINUTES = 480  # profile key max_minutes overrides


def _err(msg: str, code: int = 3) -> int:
    print(f"at: sup: {msg}", file=sys.stderr)
    return code


def _profile(args):
    try:
        return st.current_profile(args.profile)
    except ValueError as e:
        raise _Usage(str(e))


class _Usage(Exception):
    pass


def _one(s, n: int = 300) -> str:
    """One line: whitespace collapsed, cut."""
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1] + "…"


def require_chat() -> bool:
    """True for the owner at a plain shell or in the chat session that holds a valid token (sup_guard.check_chat_token).
    Every chat-only command of `at sup` calls this, from any part. Refused under AGENTS_SUP_TASK (a worker session) and
    in a process with AGENTS_SUPERVISOR but no session id. Not a fence against a worker: see the module docstring."""
    session = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if os.environ.get("AGENTS_SUP_TASK"):
        print(REFUSED, file=sys.stderr)
        return False
    if session is None and os.environ.get("AGENTS_SUPERVISOR"):
        print(f"{REFUSED}; this shell has AGENTS_SUPERVISOR set: run `unset AGENTS_SUPERVISOR` or use the owner's chat",
              file=sys.stderr)
        return False
    if session is None:
        return True
    import sup_guard
    if sup_guard.check_chat_token(session):
        return True
    print(REFUSED, file=sys.stderr)
    return False


def not_worker(profile: str) -> bool:
    """False under AGENTS_SUP_TASK or when the caller's session is a registered worker of the profile."""
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if os.environ.get("AGENTS_SUP_TASK") or (sid and st.worker_for(profile, session=sid)):
        print(REFUSED_WORKER, file=sys.stderr)
        return False
    return True


def _run(fn, args, chat: bool = False, task: bool = False, sup: bool = False) -> int:
    """Resolve profile (and task for worker commands), refuse a worker for supervisor-side commands, check the chat
    token, then call fn under the lock."""
    try:
        profile = _profile(args)
        if profile is None:
            return _err("no profile: pass --profile or set AGENTS_SUPERVISOR", 2)
        tid = None
        if task:
            tid = getattr(args, "task", None) or os.environ.get("AGENTS_SUP_TASK")
            if not tid or not st.TASK.match(tid):
                return _err("no task: pass --task or set AGENTS_SUP_TASK (like RM-12)", 2)
        if (sup or chat) and not not_worker(profile):
            return 3
        if chat and not require_chat():
            return 3
        with st.locked(profile):
            return fn(profile, tid, args)
    except _Usage as e:
        return _err(str(e), 2)
    except ValueError as e:
        return _err(str(e), 2)


def _worker_row(profile: str, task: str) -> dict | None:
    """The worker's row: by the caller's session id, else by task. Never created here."""
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
    return (sid and st.worker_for(profile, session=sid)) or st.worker_for(profile, task=task)


def _set_row(profile: str, row: dict, **fields) -> None:
    st.set_worker(profile, row["session"], **fields)


def _wake(profile: str, task: str, waiting_for: str | None = None) -> None:
    """Mark the worker `stopped` so the watcher resumes it; only a worker waiting on this very thing."""
    row = st.worker_for(profile, task=task)
    if row and row.get("state") == "waiting" and (waiting_for is None or row.get("waiting_for") == waiting_for):
        st.set_worker(profile, row["session"], state="stopped", waiting_for=None)


def _no_row(task: str) -> int:
    return _err(f"no worker row for {task}: a worker started by `at sup start-worker` asks, nobody else")


# ---- worker side ---------------------------------------------------------------------------

def _ask(profile: str, task: str, a) -> int:
    row = _worker_row(profile, task)
    if row is None:
        return _no_row(task)
    blocking = not a.no_block
    qid = st.queue_add(profile, task, a.question, a.option or [], a.recommend, a.source or "worker", blocking)
    st.emit(profile, "ask", task=task, session=row["session"], q=qid, blocking=blocking)
    print(qid)
    if blocking:
        _set_row(profile, row, state="waiting", waiting_for=qid)
        print("next: end your turn with the last line below; when you wake, read the answer with: at sup inbox")
        print(f"WAITING supervisor: {qid}")
    else:
        print("next: keep working; the answer arrives in: at sup inbox")
    return 0


def _need(profile: str, task: str, a) -> int:
    row = _worker_row(profile, task)
    if row is None:
        return _no_row(task)
    res, cfg = a.resource, st.config(profile)
    if a.minutes > cfg.get("max_minutes", MAX_MINUTES):
        return _err(f"--minutes {a.minutes} is above the profile maximum {cfg.get('max_minutes', MAX_MINUTES)}", 2)
    grants = cfg.get("grants") or {}
    granted = res in (grants.get(task) or [])
    if res in cfg.get("auto", []) or granted:
        with lease.locked() as d:
            rec = lease.read(d, res)[0]
        # the holder may re-take its own lease (a renewal); lease.take refuses anyone else
        if (rec is None or lease.is_holder(rec)) and lease.take(res, a.minutes, task=task, reason=a.reason, restore=a.restore) == 0:
            if granted:
                left = [r for r in grants[task] if r != res]
                grants = {**grants, task: left}
                if not left:
                    del grants[task]
                st.set_config(profile, grants=grants)
            st.emit(profile, "granted", task=task, session=row["session"], resource=res, minutes=a.minutes)
            print(f"granted: {res} for {a.minutes} minutes")
            print(f"next: when you are done with it, run: at sup release {res}")
            return 0
    st.emit(profile, "need", task=task, session=row["session"], resource=res, minutes=a.minutes, reason=a.reason)
    _set_row(profile, row, state="waiting", waiting_for=res)
    print("next: end your turn with the last line below; when you wake, read the answer with: at sup inbox")
    print(f"WAITING supervisor: {res}")
    return 0


def _release(profile: str, task: str, a) -> int:
    with lease.locked() as d:
        rec = lease.read(d, a.resource)[0]
    if rec is None:
        print(f"not held: {a.resource}")
        return 0
    code = lease.release(a.resource)
    if code == 0:
        row = _worker_row(profile, task)
        st.emit(profile, "released", task=task, session=row["session"] if row else None, resource=a.resource)
        print(f"released: {a.resource}")
    return code


def _inbox(profile: str, task: str, a) -> int:
    if a.ack:
        if not st.inbox_ack(profile, task, a.ack):
            return _err(f"{task} has no inbox entry {a.ack}")
        print(f"acked: {a.ack}")
        return 0
    qs = {q["id"]: q for q in st.queue(profile, open_only=False)}
    for e in st.inbox(profile, task, unread_only=True):
        q = qs.get(e.get("q"))
        about = f" (answers {q['id']}: {_one(q['question'])})" if q else ""
        print(f"{e['id']} from {e['by']}: {_one(e['text'], 1000)}{about}")
        print(f"next: once read, run: at sup inbox --ack {e['id']}")
    return 0


# ---- supervisor and owner side -------------------------------------------------------------

def _answered_event(profile: str, qid: str) -> bool:
    return any(e.get("kind") == "answered" and e.get("q") == qid for e in st.events_since(profile, 0))


def _finished(profile: str, task: str | None) -> bool:
    """The task's row is done or the task landed: nobody reads an inbox for it any more."""
    if not task:
        return False
    row = st.worker_for(profile, task=task)
    return bool(row and row.get("state") == "done") or any(
        e.get("kind") == "landed" and e.get("task") == task for e in st.events_since(profile, 0))


def _close_linked(profile: str, qid: str, by: str) -> None:
    """Open escalation entries about worker question `qid` close with it; they get no inbox entry."""
    for r in st.queue(profile):
        if r.get("q") == qid and r.get("source") != "worker":
            st.queue_close(profile, r["id"], f"answered in {qid}", by)


def _answer(profile: str, _task, a) -> int:
    """The inbox entry comes first and the close second, so a kill between them leaves a question that a rerun finishes:
    the entry already written decides the text (the first answer wins). Without --owner only a worker question may be
    answered; the owner answering an escalation that names a worker question (`escalate --q`) answers that question."""
    by = "owner" if a.owner else "sup"
    rows = st.queue(profile, open_only=False)
    q = next((r for r in rows if r.get("id") == a.qid), None)
    if q is None:
        return _err(f"no question {a.qid}")
    if q.get("source") != "worker" and not a.owner:
        return _err(f"{a.qid} is an entry from {q.get('source')}, not a worker question: only the owner answers it")
    asked = a.qid
    if q.get("source") != "worker" and q.get("q") and q.get("answer") is None:
        target = next((r for r in rows if r.get("id") == q["q"]), None)
        if target is not None and target.get("answer") is None and target.get("source") == "worker":
            asked, q = target["id"], target  # delivered as the answer to the worker question; the entry closes with it
    task = q.get("task")
    live = not _finished(profile, task)
    prior = next((e for e in st.inbox(profile, task) if e.get("q") == asked), None) if task else None
    text = prior["text"] if prior else a.text
    closed = q.get("answer") is not None
    if closed and (q["answer"] != text or _answered_event(profile, asked)):
        return _err(f"{asked} is already answered")
    if task and live and prior is None:
        st.inbox_add(profile, task, text, by=by, q=asked)
    if not closed:
        st.queue_close(profile, asked, text, by)
    _close_linked(profile, asked, by)
    if task and live:
        _wake(profile, task, asked)
    st.emit(profile, "answered", task=task, q=asked, by=by)
    if a.owner:
        st.touch(profile, f"answer {a.qid}")
    print(f"answered: {asked} by {by}" + (f" (from {a.qid})" if asked != a.qid else ""))
    return 0


def _minutes_asked(profile: str, task: str, res: str) -> int:
    for e in reversed(st.events_since(profile, 0)):
        if e.get("kind") == "need" and e.get("task") == task and e.get("resource") == res:
            return int(e.get("minutes") or DEFAULT_MINUTES)
    return DEFAULT_MINUTES


def _grant(profile: str, _task, a) -> int:
    task, res = a.task_id, a.resource
    row = st.worker_for(profile, task=task)
    if not row or row.get("state") != "waiting" or row.get("waiting_for") != res:
        return _err(f"{task} is not waiting for {res}: a grant answers a `need`")
    grants = st.config(profile).get("grants") or {}
    if res not in grants.get(task, []):
        st.set_config(profile, grants={**grants, task: [*grants.get(task, []), res]})
    mins = _minutes_asked(profile, task, res)
    st.inbox_add(profile, task, f'granted: run "at sup need {res} --minutes {mins}" again now', by="sup")
    _wake(profile, task, res)
    st.emit(profile, "granted", task=task, resource=res, minutes=mins)
    print(f"granted: {res} to {task}")
    return 0


def _deny(profile: str, _task, a) -> int:
    grants = st.config(profile).get("grants") or {}
    if a.resource in grants.get(a.task_id, []):  # a grant not yet used is withdrawn
        left = {**grants, a.task_id: [r for r in grants[a.task_id] if r != a.resource]}
        st.set_config(profile, grants={k: v for k, v in left.items() if v})
    st.inbox_add(profile, a.task_id, f"denied: {a.resource}: {a.reason}", by="sup")
    _wake(profile, a.task_id, a.resource)
    st.emit(profile, "denied", task=a.task_id, resource=a.resource, reason=a.reason)
    print(f"denied: {a.resource} to {a.task_id}")
    return 0


def _age(ts: str) -> str:
    try:
        secs = max(0, int(time.time() - datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z").timestamp()))
    except (ValueError, TypeError):
        return "?"
    return f"{secs // 86400}d" if secs >= 86400 else f"{secs // 3600}h" if secs >= 3600 else f"{secs // 60}m"


def _queue(profile: str, _task, a) -> int:
    rows = st.queue(profile, open_only=not a.all)
    if a.json:
        print(json.dumps(rows, indent=1, ensure_ascii=False))
        return 0
    for r in rows:
        line = f"{r['id']} {r.get('task') or '-'} [{_age(r.get('ts', ''))}] worker text: {_one(r['question'])}"
        if r.get("options"):
            line += " | options: " + "; ".join(_one(o, 100) for o in r["options"])
        if r.get("recommendation"):
            line += f" | recommend: {_one(r['recommendation'])}"
        line += f" | source: {_one(r.get('source'), 60)}"
        if r.get("answer") is not None:
            line += f" | answered by {r.get('by')}: {_one(r['answer'])}"
        print(line)
    return 0


def _escalate(profile: str, _task, a) -> int:
    """One open entry per task and worker question (`--q`; without it, per identical text): a second call prints the
    first one's id. A blocking escalation tells the owner once with `at notify`; a failing notify is not an error."""
    rows = st.queue(profile, open_only=False)
    task = a.task
    if a.q:
        link = next((r for r in rows if r.get("id") == a.q and r.get("source") == "worker"), None)
        if link is None:
            return _err(f"{a.q} is not a worker question")
        if task is not None and link.get("task") != task:
            return _err(f"{a.q} belongs to {link.get('task')}, not {task}")
        task = link.get("task")
    same = (lambda r: r.get("q") == a.q) if a.q else (lambda r: r.get("question") == a.text)
    old = next((r for r in rows if r.get("source") == "sup" and r.get("answer") is None and r.get("task") == task
                and same(r)), None)
    if old:
        print(old["id"])
        return 0
    qid = st.queue_add(profile, task, a.text, source="sup", blocking=a.blocking, q=a.q)
    print(qid)
    if a.blocking:
        import sup_watch  # the watcher's own notify call; its failure is not ours
        sup_watch._run_at(profile, ["notify", f"{profile}: {_one(a.text, 150)}"], timeout=30, with_profile=False)
    return 0


def _instruct(profile: str, _task, a) -> int:
    st.instruct(profile, a.text)
    st.touch(profile, "instruct")
    print("instruction recorded")
    return 0


def _instructions(profile: str, _task, a) -> int:
    print(st.instructions(profile), end="")
    return 0


# ---- argparse ------------------------------------------------------------------------------

def _pattern(rx, what):
    def conv(v: str) -> str:
        if not rx.match(v):
            raise argparse.ArgumentTypeError(f"{what} {v!r} is not valid")
        return v
    return conv


def _text(v: str) -> str:
    if not v.strip():
        raise argparse.ArgumentTypeError("text must not be empty")
    return v


def _minutes(v: str):
    f = lease.ttl_arg(v)
    return int(f) if f == int(f) else f


def register(sup_sub) -> None:
    res, qid, task_id = _pattern(st.RES, "resource"), _pattern(st.QID, "question id"), _pattern(st.TASK, "task ID")

    def add(name, fn, **kw):
        p = sup_sub.add_parser(name, help=fn.__doc__)
        p.add_argument("--profile")
        p.set_defaults(func=lambda a, f=fn: _run(f, a, **kw))
        return p

    def worker(name, fn):
        p = add(name, fn, task=True)
        p.add_argument("--task", type=task_id, help="task ID (default: AGENTS_SUP_TASK)")
        return p

    p = worker("ask", _ask)
    p.add_argument("question", type=_text)
    p.add_argument("--option", action="append")
    p.add_argument("--recommend")
    p.add_argument("--source")
    p.add_argument("--no-block", action="store_true")
    p = worker("need", _need)
    p.add_argument("resource", type=res)
    p.add_argument("--minutes", type=_minutes, required=True, help="how long you need it (required)")
    p.add_argument("--reason")
    p.add_argument("--restore", action="store_true")
    worker("release", _release).add_argument("resource", type=res)
    worker("inbox", _inbox).add_argument("--ack", metavar="A-ID")

    p = add("answer", _answer, sup=True)
    p.add_argument("qid", metavar="Q-id", type=qid)
    p.add_argument("text", type=_text)
    p.add_argument("--owner", action="store_true")
    p.set_defaults(func=lambda a: _run(_answer, a, chat=a.owner, sup=True))
    p = add("grant", _grant, sup=True)
    p.add_argument("task_id", metavar="TASK-ID", type=task_id)
    p.add_argument("resource", type=res)
    p = add("deny", _deny, sup=True)
    p.add_argument("task_id", metavar="TASK-ID", type=task_id)
    p.add_argument("resource", type=res)
    p.add_argument("reason")
    p = add("queue", _queue)
    p.add_argument("--all", action="store_true")
    p.add_argument("--json", action="store_true")
    p = add("escalate", _escalate, sup=True)
    p.add_argument("text", type=_text)
    p.add_argument("--task", type=task_id)
    p.add_argument("--blocking", action="store_true")
    p.add_argument("--q", type=qid, help="the worker question this is about")
    add("instruct", _instruct, chat=True).add_argument("text", type=_text)
    add("instructions", _instructions)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="at sup")
    register(ap.add_subparsers(dest="cmd", required=True))
    a = ap.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
