"""Topic sessions of `at sup`: a small pool of long-lived helper sessions the supervisor hands owner asks to.

The supervisor is guarded to `at sup` commands, so an ask that needs git, a shell or reading code goes to a topic
session instead of back to the owner. Each topic is one bg session named `<profile>-topic-<name>`, started in the hub
with the owner's PATH and `--permission-mode auto`, and kept alive between asks: the next ask on the same topic
resumes it with its context. The supervisor reads only the topic's last result line, so its own context stays small.

Commands (all take --profile, default $AGENTS_SUPERVISOR; exit 0 ok, 2 usage, 3 refused):
  delegate <topic> '<ask>' [--fresh] [--interrupt]   chat only. Start the topic, or resume it with the ask. A busy topic
                                                      is refused unless --interrupt. --fresh stops the old session and
                                                      starts a new one that reads the topic's notes file instead of an
                                                      old transcript (the way to give a long topic a clean context).
  topics                                              the topics: state, asks, age and the last result line
  topic-log <topic> [--lines N]                       the last N lines (default 40) of the topic's terminal output
  stop-topic <topic>                                  chat only. Stop the session; its notes and row stay, so a later
                                                      delegate resumes it
State: topics.json in the profile directory, a list of {name, session, started, asks, last_ask, state}; under topics/,
<name>.md (notes) and <name>.result (the last TOPIC line, cleared at each ask), both written by the topic session.
A resume waits until the stopped session has exited (sup_workers.wait_gone) and stops any copy claude starts instead. config key `topic_cap` (default 3) caps the topics
that run at once. A worker or a topic session may run none of these (sup_workers._command refuses both).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import sup_state as st
import sup_workers as sw

TOPIC = re.compile(r"[a-z0-9][a-z0-9-]{0,39}\Z")
TOPIC_CAP = 3
RESUME_TRIES = 3
RESULT = re.compile(r"^\s*TOPIC (\S+) (done|blocked): (.*)$")
ANSI_MOVE = re.compile(r"\x1b\[[0-9;]*[CG]")  # cursor moves inside a line: read as a space
ANSI = re.compile(r"\x1b(\[[0-9;?]*[A-Za-z]|\][^\x07]*\x07|.)")
TOPIC_PROMPT = (
    "You are the helper session for topic `{topic}` of supervisor profile `{profile}` (hub {hub}). The supervisor cannot "
    "run git, a shell or read code; it hands such asks to you and keeps your session alive for later asks on this topic. "
    "Do the work yourself: git, shell, reading and editing files in the hub and the repos of {hub}/.local/repos.map and their "
    "worktrees. Do not push, do not merge, do not force, do not delete a branch someone else is working on, and do not edit "
    "files under the supervisor state directory ({state}). Do not run `at sup` commands: the supervisor does those. "
    "Keep a short notes file at {notes}: what the topic is, what you found, what you changed (commits, paths) and what is "
    "open; update it before you end every turn, because a fresh session of this topic starts from it. End every turn with "
    "exactly one line `TOPIC {topic} done: <one-line result>` or `TOPIC {topic} blocked: <the question for the owner>`, "
    "and write that same line to {result} (replace the file): the supervisor reads it there.{notes_hint}"
    "\n\nThe ask: {ask}"
)
NOTES_HINT = " Read your notes file first: it holds what an earlier session of this topic did."


def _path(profile: str) -> Path:
    return st.profile_dir(profile) / "topics.json"


def topics(profile: str) -> list[dict]:
    return st.read_json(_path(profile), [])


def _save(profile: str, rows: list[dict]) -> None:
    st.write_json(_path(profile), rows)


def notes_path(profile: str, name: str) -> Path:
    return st.profile_dir(profile) / "topics" / f"{name}.md"


def result_path(profile: str, name: str) -> Path:
    return st.profile_dir(profile) / "topics" / f"{name}.result"


def _row(profile: str, name: str) -> dict | None:
    return next((t for t in topics(profile) if t.get("name") == name), None)


def _set(profile: str, name: str, **fields) -> None:
    rows = topics(profile)
    row = next((t for t in rows if t.get("name") == name), None)
    if row is None:
        row = {"name": name}
        rows.append(row)
    row.update(fields)
    _save(profile, rows)


def _agent(row: dict | None, found) -> dict | None:
    """The `claude agents` row of a topic's session when its process is up."""
    if not row or not found:
        return None
    return next((r for r in found if r.get("sessionId") == row.get("session") and r.get("pid") is not None), None)


def _busy(agent: dict | None) -> bool:
    return bool(agent) and (agent.get("status") == "busy" or agent.get("state") == "working")


def _name(value: str) -> str:
    if not TOPIC.match(value or ""):
        raise ValueError(f"topic {value!r}: use lower-case letters, digits and '-', at most 40")
    return value


def plain(text: str) -> str:
    """Terminal output of `claude logs` as plain lines: cursor moves become spaces, other escapes go."""
    return ANSI.sub("", ANSI_MOVE.sub(" ", text)).replace("\r", "")


def last_result(profile: str, name: str) -> str | None:
    """`done: ...` or `blocked: ...` from the last TOPIC line the topic wrote to its result file."""
    try:
        lines = result_path(profile, name).read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    hits = [m for m in (RESULT.match(l) for l in lines) if m]
    return f"{hits[-1].group(2)}: {' '.join(hits[-1].group(3).split())}" if hits else None


@sw._command(chat=True, lock=False)
def cmd_delegate(profile: str, args) -> int:
    name, ask = _name(args.topic), " ".join(args.ask).strip()
    if not ask:
        raise ValueError("say what the topic should do")
    try:
        hub = st.hub(profile)
    except ValueError as e:
        raise sw.Refused(str(e)) from None
    env = sw.clean_env(AGENTS_SUPERVISOR=profile, AGENTS_SUP_TOPIC=name)
    found = sw.agents()
    if found is None:
        raise sw.Refused("`claude agents` failed: cannot tell whether the topic runs")
    with st.locked(profile):
        row = _row(profile, name)
    agent = _agent(row, found)
    if row and row.get("session") and not args.fresh:
        if _busy(agent) and not args.interrupt:
            raise sw.Refused(f"topic {name} is busy; wait, or pass --interrupt to stop its turn")
        if agent:
            sw._stop_session(row["session"])
            if not sw.wait_gone(row["session"]):
                raise sw.Refused(f"topic {name} ({row['session'][:8]}) did not stop; try again")
        result_path(profile, name).unlink(missing_ok=True)
        woke = False
        for attempt in range(RESUME_TRIES):  # a session that just stopped may still be exiting: claude then starts a copy
            woke = sw.resume_bg(row["session"], ask, [], env, str(hub))
            if woke or not any(x.startswith("claude started a copy") for x in sw.RESUME_SAID):
                break
            if attempt < RESUME_TRIES - 1:
                sw.time.sleep(sw.POLL_DELAY * 4)
                sw.wait_gone(row["session"])
        if not woke:
            said = sw.RESUME_SAID[-1] if sw.RESUME_SAID else "no output"
            raise sw.Refused(f"could not resume topic {name} ({row['session'][:8]}): {said}; try --fresh")
        with st.locked(profile):
            _set(profile, name, asks=row.get("asks", 0) + 1, last_ask=st.now(), state="running")
            st.touch(profile, f"delegate {name}")
        print(f"resumed topic {name} {row['session']}")
        return 0
    if agent:
        sw._stop_session(row["session"])
    others = [t for t in topics(profile) if t.get("name") != name and _agent(t, found)]
    cap = int(st.config(profile).get("topic_cap", TOPIC_CAP))
    if len(others) >= cap:
        raise sw.Refused(f"topic cap {cap} reached ({', '.join(t['name'] for t in others)}); stop one with `at sup stop-topic`")
    notes = notes_path(profile, name)
    notes.parent.mkdir(exist_ok=True)
    result_path(profile, name).unlink(missing_ok=True)
    prompt = TOPIC_PROMPT.format(topic=name, profile=profile, hub=hub, state=st.profile_dir(profile), notes=notes,
                                 result=result_path(profile, name), notes_hint=NOTES_HINT if notes.is_file() else "",
                                 ask=ask)
    session = sw._bg_session(profile, f"topic-{name}", str(hub), env, prompt, [])  # no --add-dir: an untrusted folder refuses the start; the sibling repos are reached by path, as a worker does
    with st.locked(profile):
        _set(profile, name, session=session, started=st.now(), asks=1, last_ask=st.now(), state="running")
        st.touch(profile, f"delegate {name}{' --fresh' if args.fresh else ''}")
    print(f"started topic {name} {session}")
    return 0


@sw._command(lock=False)
def cmd_topics(profile: str, args) -> int:
    rows = topics(profile)
    if not rows:
        print("no topics")
        return 0
    found = sw.agents()
    for t in rows:
        agent = _agent(t, found)
        state = "?" if found is None else ("busy" if _busy(agent) else "idle" if agent else "stopped")
        result = last_result(profile, t["name"])
        print(f"{t['name']}  {state}  asks {t.get('asks', 0)}  {(t.get('session') or '-')[:8]}  "
              f"last ask {int(sw.age(t.get('last_ask')) // 60)}m ago  {result or '-'}")
    return 0


@sw._command(lock=False)
def cmd_topic_log(profile: str, args) -> int:
    row = _row(profile, _name(args.topic))
    if not row or not row.get("session"):
        raise sw.Refused(f"no topic {args.topic}")
    out = sw._run([sw._claude(), "logs", row["session"][:8]], env=sw.clean_env())
    if out.returncode != 0:
        raise sw.Refused(f"claude logs {row['session'][:8]} failed")
    lines = [l.rstrip() for l in plain(out.stdout).splitlines() if l.strip()]
    print("\n".join(lines[-max(1, args.lines):]))
    print(f"notes: {notes_path(profile, row['name'])}")
    return 0


@sw._command(chat=True, lock=False)
def cmd_stop_topic(profile: str, args) -> int:
    row = _row(profile, _name(args.topic))
    if not row or not row.get("session"):
        raise sw.Refused(f"no topic {args.topic}")
    if sw._run([sw._claude(), "stop", row["session"][:8]], env=sw.clean_env()).returncode != 0:
        found = sw.agents()
        if found is None or _agent(row, found):
            raise sw.Refused(f"claude stop {row['session'][:8]} failed")
    with st.locked(profile):
        _set(profile, row["name"], state="stopped")
        st.touch(profile, f"stop-topic {row['name']}")
    print(f"stopped topic {row['name']} {row['session']}")
    return 0


def topic_sessions(profile: str) -> set[str]:
    return {t["session"] for t in topics(profile) if t.get("session")}


def register(sup_sub) -> None:
    def add(name, func, *pos, flags=()):
        p = sup_sub.add_parser(name)
        p.add_argument("--profile")
        for arg, kw in pos:
            p.add_argument(arg, **kw)
        for flag, kw in flags:
            p.add_argument(flag, **kw)
        p.set_defaults(func=func)

    topic = ("topic", {})
    add("delegate", cmd_delegate, topic, ("ask", {"nargs": "+"}),
        flags=[("--fresh", {"action": "store_true"}), ("--interrupt", {"action": "store_true"})])
    add("topics", cmd_topics)
    add("topic-log", cmd_topic_log, topic, flags=[("--lines", {"type": int, "default": 40})])
    add("stop-topic", cmd_stop_topic, topic)


if __name__ == "__main__":  # pragma: no cover
    sys.exit("run through `at sup`")
