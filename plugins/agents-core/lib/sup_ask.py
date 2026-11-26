"""`at sup ask|need|release|inbox|answer|grant|deny|queue|instruct|instructions`: questions, leases and answers.

Worker side (task from --task or AGENTS_SUP_TASK, session from CLAUDE_CODE_SESSION_ID): `ask` queues a question
for the owner and `need` takes a lease or asks for it. Both set the worker row to `waiting` and print the last
line the worker ends its turn with, `WAITING supervisor: <Q-id or resource>`. `inbox` shows the answers.
Supervisor and owner side: `answer` closes a question (first answer wins) and puts the answer in the task's
inbox; `grant` and `deny` settle a `need`; `queue` lists the owner's open questions. A row set to `stopped`
with `waiting_for` None is what the watcher wakes. Chat-only commands (`instruct`, `answer --owner`, and the ones in the
other parts: sup_guard.CHAT_COMMANDS) call `require_chat()`: allowed in a plain shell, and in a Claude session only with
the chat token of that session (sup_guard.check_chat_token).
Exit codes: 0 ok, 2 usage, 3 refused. stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import lease
import sup_state as st

REFUSED = "at: sup: only the owner's chat may run this"
DEFAULT_MINUTES = 30


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


def require_chat() -> bool:
    """True for the owner at a plain shell (no CLAUDE_CODE_SESSION_ID) or in the chat session that holds a valid
    token (sup_guard.check_chat_token). Every chat-only command of `at sup` calls this, from any part."""
    session = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if session is None:
        return True
    import sup_guard
    if sup_guard.check_chat_token(session):
        return True
    print(REFUSED, file=sys.stderr)
    return False


def _run(fn, args, chat: bool = False, task: bool = False) -> int:
    """Resolve profile (and task for worker commands), check the chat token, then call fn under the lock."""
    try:
        profile = _profile(args)
        if profile is None:
            return _err("no profile: pass --profile or set AGENTS_SUPERVISOR", 2)
        tid = None
        if task:
            tid = getattr(args, "task", None) or os.environ.get("AGENTS_SUP_TASK")
            if not tid or not st.TASK.match(tid):
                return _err("no task: pass --task or set AGENTS_SUP_TASK (like RM-12)", 2)
        if chat and not require_chat():
            return 3
        with st.locked(profile):
            return fn(profile, tid, args)
    except _Usage as e:
        return _err(str(e), 2)
    except ValueError as e:
        return _err(str(e), 2)


def _session(profile: str, task: str | None) -> str | None:
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if sid:
        return sid
    row = st.worker_for(profile, task=task)
    return row.get("session") if row else None


def _row(profile: str, task: str | None, **fields) -> None:
    sid = _session(profile, task)
    if sid:
        st.set_worker(profile, sid, task=task, **fields)


def _wake(profile: str, task: str, waiting_for: str | None = None) -> None:
    """Mark the worker `stopped` so the watcher resumes it; only a worker waiting on this very thing."""
    row = st.worker_for(profile, task=task)
    if row and row.get("state") == "waiting" and (waiting_for is None or row.get("waiting_for") == waiting_for):
        st.set_worker(profile, row["session"], state="stopped", waiting_for=None)


# ---- worker side ---------------------------------------------------------------------------

def _ask(profile: str, task: str, a) -> int:
    blocking = not a.no_block
    qid = st.queue_add(profile, task, a.question, a.option or [], a.recommend, a.source or "worker", blocking)
    st.emit(profile, "ask", task=task, session=_session(profile, task), q=qid, blocking=blocking)
    if blocking:
        _row(profile, task, state="waiting", waiting_for=qid)
    print(qid)
    if blocking:
        print(f"WAITING supervisor: {qid}")
    return 0


def _need(profile: str, task: str, a) -> int:
    res, cfg = a.resource, st.config(profile)
    grants = cfg.get("grants") or {}
    granted = res in (grants.get(task) or [])
    if res in cfg.get("auto", []) or granted:
        with lease.locked() as d:
            free = lease.read(d, res)[0] is None
        if free and lease.take(res, a.minutes, task=task, reason=a.reason, restore=a.restore) == 0:
            if granted:
                left = [r for r in grants[task] if r != res]
                grants = {**grants, task: left}
                if not left:
                    del grants[task]
                st.set_config(profile, grants=grants)
            st.emit(profile, "granted", task=task, session=_session(profile, task), resource=res, minutes=a.minutes)
            print(f"granted: {res} for {a.minutes} minutes")
            return 0
    st.emit(profile, "need", task=task, session=_session(profile, task), resource=res, minutes=a.minutes, reason=a.reason)
    _row(profile, task, state="waiting", waiting_for=res)
    print(f"WAITING supervisor: {res}")
    return 0


def _release(profile: str, task: str, a) -> int:
    code = lease.release(a.resource)
    if code == 0:
        st.emit(profile, "released", task=task, session=_session(profile, task), resource=a.resource)
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
        about = f" (answers {q['id']}: {q['question']})" if q else ""
        print(f"{e['id']} from {e['by']}: {e['text']}{about}")
    return 0


# ---- supervisor and owner side -------------------------------------------------------------

def _answer(profile: str, _task, a) -> int:
    by = "owner" if a.owner else "sup"
    q = next((r for r in st.queue(profile, open_only=False) if r.get("id") == a.qid), None)
    if q is None:
        return _err(f"no question {a.qid}")
    if not st.queue_close(profile, a.qid, a.text, by):
        return _err(f"{a.qid} is already answered")
    if q.get("task"):
        st.inbox_add(profile, q["task"], a.text, by=by, q=a.qid)
        _wake(profile, q["task"], a.qid)
    st.emit(profile, "answered", task=q.get("task"), q=a.qid, by=by)
    if a.owner:
        st.touch(profile, f"answer {a.qid}")
    print(f"answered: {a.qid} by {by}")
    return 0


def _minutes_asked(profile: str, task: str, res: str) -> int:
    for e in reversed(st.events_since(profile, 0)):
        if e.get("kind") == "need" and e.get("task") == task and e.get("resource") == res:
            return int(e.get("minutes") or DEFAULT_MINUTES)
    return DEFAULT_MINUTES


def _grant(profile: str, _task, a) -> int:
    task, res = a.task_id, a.resource
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
    st.inbox_add(profile, a.task_id, f"denied: {a.resource}: {a.reason}", by="sup")
    _wake(profile, a.task_id, a.resource)
    st.emit(profile, "denied", task=a.task_id, resource=a.resource, reason=a.reason)
    print(f"denied: {a.resource} to {a.task_id}")
    return 0


def _age(ts: str) -> str:
    try:
        secs = max(0, int(time.time() - time.mktime(time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S"))))
    except (ValueError, TypeError):
        return "?"
    return f"{secs // 86400}d" if secs >= 86400 else f"{secs // 3600}h" if secs >= 3600 else f"{secs // 60}m"


def _queue(profile: str, _task, a) -> int:
    rows = st.queue(profile, open_only=not a.all)
    if a.json:
        print(json.dumps(rows, indent=1, ensure_ascii=False))
        return 0
    for r in rows:
        line = f"{r['id']} {r.get('task') or '-'} [{_age(r.get('ts', ''))}] {r['question']}"
        if r.get("options"):
            line += " | options: " + "; ".join(r["options"])
        if r.get("recommendation"):
            line += f" | recommend: {r['recommendation']}"
        line += f" | source: {r.get('source')}"
        if r.get("answer") is not None:
            line += f" | answered by {r.get('by')}: {r['answer']}"
        print(line)
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

def register(sup_sub) -> None:
    def add(name, fn, **kw):
        p = sup_sub.add_parser(name, help=fn.__doc__)
        p.add_argument("--profile")
        p.set_defaults(func=lambda a, f=fn: _run(f, a, **kw))
        return p

    def worker(name, fn):
        p = add(name, fn, task=True)
        p.add_argument("--task", help="task ID (default: AGENTS_SUP_TASK)")
        return p

    p = worker("ask", _ask)
    p.add_argument("question")
    p.add_argument("--option", action="append")
    p.add_argument("--recommend")
    p.add_argument("--source")
    p.add_argument("--no-block", action="store_true")
    p = worker("need", _need)
    p.add_argument("resource")
    p.add_argument("--minutes", type=int, required=True)
    p.add_argument("--reason")
    p.add_argument("--restore", action="store_true")
    worker("release", _release).add_argument("resource")
    worker("inbox", _inbox).add_argument("--ack", metavar="A-ID")

    p = add("answer", _answer)
    p.add_argument("qid", metavar="Q-id")
    p.add_argument("text")
    p.add_argument("--owner", action="store_true")
    p.set_defaults(func=lambda a: _run(_answer, a, chat=a.owner))
    p = add("grant", _grant)
    p.add_argument("task_id", metavar="TASK-ID")
    p.add_argument("resource")
    p = add("deny", _deny)
    p.add_argument("task_id", metavar="TASK-ID")
    p.add_argument("resource")
    p.add_argument("reason")
    p = add("queue", _queue)
    p.add_argument("--all", action="store_true")
    p.add_argument("--json", action="store_true")
    add("instruct", _instruct, chat=True).add_argument("text")
    add("instructions", _instructions)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="at sup")
    register(ap.add_subparsers(dest="cmd", required=True))
    a = ap.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
