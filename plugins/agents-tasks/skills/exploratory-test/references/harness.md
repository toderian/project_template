# The harness a repo provides

The loop needs four things from the repo. Keep them in one folder (default `tests/e2e-explore/`,
`at explore --dir <path>` for another) with a README that says how to start, run and stop.

## 1. A stack that starts with one command

- Starts the product locally with test data and stops it again; a second start is safe.
- Uses credentials made for the run. No real secret is written to disk or to a committed file.
- Says plainly what it does not cover (a demo mode, a stubbed backend), so a pass is not read as more
  than it is.

## 2. A scenario helper

One function a scenario calls once. It:

- signs in, and resets any role or mode the last scenario left behind;
- records a trace or equivalent, console errors, page errors, failed requests and server errors;
- writes `result.json` (cell, leaf, expected, verdict, actual, route, notes) beside the scenario;
- keeps the earlier result when a scenario is replayed;
- refuses to run against anything but the local stack.

Evidence goes to a git-ignored folder, one sub-folder per run and cell.

## 3. A rule about concurrency

State whether scenarios may run together. When they share one account or one data set, run them one at
a time through a lock, and say so. Give each explorer its own account to remove the lock.

## 4. A limit on what the product can reach

When the product acts on other systems (sends mail, scans hosts, charges cards, calls partner APIs),
the limit is enforced outside the model: a network without a route out, a firewall, a recording
stand-in for the outside service, an account that lacks the dangerous permission. A sentence in a
prompt is not a limit. The helper checks after every scenario that nothing left the box.

## What goes wrong in practice

Wrong results come from the harness far more often than from the model's judgement.

- A check made before the screen settled passes or fails for the wrong reason. Wait for a control that
  proves the screen rendered; network idle is not enough.
- A route that refuses every role says nothing about one role. Hence the control in step 4.
- A request the scenario builds differs from the one the product sends (a missing body, a missing
  header). Prefer the real control; when calling a route directly, send what the product sends.
- A scenario that creates data deletes it before it ends, or the next one counts it.
- A navigation aborts requests in flight. Do not record those as failures.
- Do not wrap the run command in a timeout of your own; let the harness stop a stuck scenario.
