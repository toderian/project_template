"""Hook-side event writer of a supervised worker: `sup_event.py <kind> [--task ID] [--session ID] [key=value]...`.

Profile from AGENTS_SUPERVISOR, default task from AGENTS_SUP_TASK. Emits one event under `sup_state.locked`; for the
kinds stopped, done and waiting it also sets the registry row of the session to that state, when the row exists.
Called by hooks/run-guard.sh and lib/run_watch.py, which must never break on it: any error prints one line to
stderr and the exit code is 0.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sup_state  # noqa: E402

ROW_STATES = ("stopped", "done", "waiting")


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
    with sup_state.locked(profile):
        sup_state.emit(profile, kind, task=task, session=session, **data)
        if kind in ROW_STATES and session and sup_state.worker_for(profile, session=session):
            extra = {"waiting_for": data.get("resource")} if kind == "waiting" else {}
            sup_state.set_worker(profile, session, state=kind, **extra)


if __name__ == "__main__":
    try:
        run(sys.argv[1:])
    except Exception as err:  # a hook must not break on the supervisor's state
        print(f"sup_event: {err}", file=sys.stderr)
    sys.exit(0)
