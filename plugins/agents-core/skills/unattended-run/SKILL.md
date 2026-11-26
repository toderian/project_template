---
name: unattended-run
description: "Check that a task, plan or chain of tasks can run from start to end with nobody answering, mark it `Execution: unattended`, record what the agent is authorised to decide, and apply the decision rule while it runs: decide inside the authorised scope and log it, park the rest, keep going. Use when the user wants a task to run overnight, end to end, without stopping or without questions, asks \"can this run autonomously\" or \"will you need anything from me\", or when a task being executed carries `Execution: unattended`."
argument-hint: "Which task, plan or chain should run unattended?"
metadata:
  pack: core
---

# Unattended Run

## Purpose

A run that stops at 23:00 to ask something costs the night. Find every such stop before the run
starts, get the answers once, write them where a later session reads them, and during the run decide
what the owner authorised instead of asking. Every decision taken that way is recorded, so the owner
can audit the run afterwards.

The loop itself is `agents-core:execute-plan`; this skill adds the check before it and the decision
rule during it.

## Process

### 1. Resolve what runs

The task or plan file; for a parent task, every open child in the order the parent gives. Read each
file in full. Done when you can list the tasks and their phases in run order.

### 2. Readiness check

Check each line yourself, with a command where one exists. A line you cannot check is a gap.

| Check | Passes when |
|---|---|
| Plan | every phase has a checklist, acceptance criteria and checks with exact commands; no `TBD`, open question or undecided option anywhere in the chain |
| Dependencies | every `Blocked by` is inside the chain and ordered before its dependant, or already done |
| Decision points | you searched the files for every place that says ask, confirm, approve, decide or "owner", every `Work mode: ask`, every `blocked` / `parked` row of an existing run state; each one is answered now or answered in step 3 |
| Access | a harmless probe of every external system the checks use succeeds now: remote hosts, APIs, containers, lab locks, credentials, free disk and memory |
| Permissions | the commands the plan needs run without a permission prompt in this session, and none of them is one the safety hooks block |
| Autonomy | the effective autonomy level covers every action in the plan; each action above it is listed as owner-only |
| Shared resources | no other session or job holds what the run needs (a lab, a checkout, a port), or the plan says how to wait for it |
| Duration | every long step has a timeout and runs in the background with a named way to notice it finished or died |
| Recovery | the run state is committed per phase, so a session that dies resumes from disk |
| Notification | `git config agents.notifyCommand` or `AGENTS_NOTIFY_CMD` is set, `at notify "unattended run: test" </dev/null` ran, and the owner confirms the message arrived. Without it a blocked run waits unseen: record that as a named gap |

Done when every line has a result: pass, or a named gap.

### 3. Ask everything now

The owner answers once, before the run, and not again until it ends. So collect every decision the
run will need, not only the gaps from step 2. Walk each phase as if you were executing it and write
down each point where you would have to choose or be allowed:

- **About the task:** an ambiguous requirement, two valid designs, a scope edge ("does this include
  X?"), a threshold or name the plan leaves open, what counts as done when a criterion can be read
  two ways, what to do when a likely failure happens (a check that is already red, a missing
  fixture, a host that is down, a review that does not converge).
- **About authorisation:** every system the run touches and what it may do there: restart, reconfigure,
  delete and recreate, switch modes, hold a lock, spend money or quota; which branches it may commit
  to; what it may do to another session's work; what always waits for the owner.

Then make sure you would build what the owner expects, not only what the text allows:

1. **Play it back.** Per phase, tell the owner in two or three sentences what you will build and what
   they will see when it is done: the files or screens that change, the behaviour before and after,
   what you will leave alone. A wrong picture shows here, while it costs one sentence to correct.
2. **Grill the task** with `agents-core:grilling`: treat the plan as the design tree and question
   every branch the playback or your walk left open, each question with your recommended answer,
   until the owner confirms the shared understanding. Authorisation questions go in the same rounds.

Look up what you can; only the owner's choices are asked. Stop when a full walk of the plan produces
no new question and the owner has confirmed the playback.

Verdict: `READY` when step 2 has no gap, this step has no open question and the playback is
confirmed; otherwise `NOT READY`, and the run does not start. Re-run the failed lines of step 2 after the answers.

### 4. Record the mark and the scope

Authorisation is the owner's words, never your inference: draft the section from their answers, show
it, and write it only after they confirm.

1. Set the metadata row `Execution` to include `unattended` (comma-separated with other values). In
   a plan file without metadata rows, a line `Execution: unattended` under the title.
2. Add to the task file (the parent, for a chain; children inherit it):

   ```markdown
   ### Unattended run

   Checked: <date>, READY
   Authorised: <what the agent may do without asking: hosts and services it may restart or
   reconfigure, data it may delete and recreate, modes it may switch, spend>
   Owner only: <what always waits: push, merge, release, deploy, anything that loses data or evidence>
   Defaults: <one line per pre-answered decision: "if X, do Y">
   Watch: <on | off>
   Watch budget: <total USD for all restarts>, at most <N> restarts
   ```

   Restarting a dead session is an authorisation, given per task: ask for it in step 3. `Watch: on`
   lets a watchdog outside the session restart it headless, within that budget, if its process dies;
   `Watch: off` when the owner declines. Add a line `allow bypass` only when the owner grants, in
   words, restarts in `bypassPermissions` mode for a run that already uses it.

   Answers about the task itself go where the task keeps them: the phase checklist, the acceptance
   criteria or the design section they change. `Defaults` holds the rest, one line per answer from
   step 3, so no answer lives only in chat. A corrected playback is a plan change: edit the phase
   it corrects.

Done when the section is in the file, confirmed, and committed with the task.

### 5. Decide during the run

Applies to every task that carries the mark, from the first phase to closeout. At each point where
you would ask the owner:

1. **A `Defaults` line answers it:** do that.
2. **Inside `Authorised`:** take the option you would recommend, act, and add to the run state:

   ```text
   Decision: <the question> — <what you chose> — why: <one clause> — cost if wrong: <one clause>
   ```

3. **`Owner only`, outside both lists, irreversible, or it loses data or evidence:** do not act.
   Set the row to `parked`, add `Note: parked: <the question, with the option you recommend>`, and
   continue with the next phase or task that does not depend on it.

A failing tool or host is not a decision point: retry twice with a changed approach, try the
alternative the plan allows, then park.

Never end a turn on a status summary. The turn ends only when everything is committed or parked, or
on the `Run:` line `agents-core:execute-plan` defines.

### 6. Report

When nothing can proceed: what finished (commits), what is parked, and the path of each run state.
Put the parked questions to the owner through `agents-core:ask`, all at once. List the `Decision:`
lines taken; they are copied into each task's completion summary at closeout.

## Quality bar

- Every stop the plan could cause was found before the run, not during it: a decision point met
  during the run that step 3 could have foreseen is a defect of the check.
- Every answer the owner gave is written in the task file.
- The scope section is the owner's confirmed words and is committed.
- Each decision taken without the owner has a `Decision:` line; each one not taken has a `parked` row.
- A parked row stops only what depends on it.
