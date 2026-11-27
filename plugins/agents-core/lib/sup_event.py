"""Hook-side event writer of a supervised worker: `sup_event.py <kind> [--task ID] [--session ID] [key=value]...`.

Profile from AGENTS_SUPERVISOR, default task from AGENTS_SUP_TASK. Emits one event under `sup_state.locked` (the lock
wait is bounded to 4 seconds) and sets the registry row of the worker (found by --session, else by the task):
stopped, done and waiting set that state, restarted sets `running` with waiting_for cleared. `done` with
`close_questions=moot` also closes the worker's own open questions.
Exit code: 0 only when the row was found (else nothing is written) AND, for `waiting`, the id in `resource=` is
an open queue question (Q<n>) of this task or a resource whose last `need` of this task is newer than its last
granted, denied or released. Anything else prints one line to
stderr and exits 1: the caller (hooks/run-guard.sh, lib/run_watch.py) then does not treat the stop as handed
to the supervisor. On success it prints `watcher` when the profile's watcher is alive (the tick then decides, so
the hook does not notify the owner itself). A bad kind, task, session, key or resource is refused before anything is written.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lease  # noqa: E402
import sup_state  # noqa: E402

ROW_STATES = {"stopped": "stopped", "done": "done", "waiting": "waiting", "restarted": "running"}


def _open_request(profile: str, ident: str, task: str | None) -> bool:
    if not task:
        return False
    if sup_state.QID.match(ident):
        return any(q.get("id") == ident and q.get("task") == task for q in sup_state.queue(profile))
    return sup_state.need_open(profile, task, ident)


def _watcher_alive(profile: str) -> bool:
    """watch.pid holds "<pid> <start time>" (written by sup_watch); a reused pid is not the watcher."""
    try:
        pid, started = (sup_state.profile_dir(profile, create=False) / "watch.pid").read_text().split()
        os.kill(int(pid), 0)
    except (OSError, ValueError):
        return False
    return str(lease.start_time(int(pid))) == started


def run(argv: list[str]) -> None:
    profile = sup_state.current_profile()
    if not profile or not argv:
        raise ValueError("usage: sup_event.py <kind> [--task ID] [--session ID] [key=value]... (AGENTS_SUPERVISOR set)")
    kind, task, session, data = argv[0], os.environ.get("AGENTS_SUP_TASK") or None, None, {}
    rest = iter(argv[1:])
    for arg in rest:
        if arg == "--task":
            task = next(rest, None) or task
        elif arg == "--session":
            session = next(rest, None)
        elif "=" in arg:
            key, _, value = arg.partition("=")
            data[key] = value
    if kind == "waiting" and not (sup_state.QID.match(data.get("resource", "")) or sup_state.RES.match(data.get("resource", ""))):
        raise ValueError("waiting needs resource=<Q id or resource name>")
    if not sup_state.profile_dir(profile, create=False).is_dir():
        raise ValueError(f"profile {profile!r} has no state here")
    with sup_state.locked(profile, wait=4):
        row = (session and sup_state.worker_for(profile, session=session)) or (task and sup_state.worker_for(profile, task=task))
        if not row:
            raise LookupError("no registry row for this worker; nothing written")
        task = row.get("task") or task  # the row found by session names the task: env may be another session's (bg-spare)
        if kind == "waiting" and not _open_request(profile, data["resource"], row.get("task")):
            raise LookupError(f"{data['resource']} is not an open request of this worker; nothing written")
        sup_state.emit(profile, kind, task=task, session=session, **data)
        if kind == "done" and data.get("close_questions") == "moot":  # a finished worker's own questions need no answer
            for q in sup_state.queue(profile):
                if q.get("task") == row.get("task") and q.get("source", "worker") == "worker":
                    sup_state.queue_close(profile, q["id"], "moot", "sup")
        if kind in ROW_STATES:
            extra = {"waiting_for": data.get("resource") if kind == "waiting" else None}
            sup_state.set_worker(profile, row["session"], state=ROW_STATES[kind], **extra)
    if _watcher_alive(profile):
        print("watcher")


if __name__ == "__main__":
    try:
        run(sys.argv[1:])
    except Exception as err:  # the caller reads the exit code; one line says why
        print(f"sup_event: {err}", file=sys.stderr)
        sys.exit(1)
