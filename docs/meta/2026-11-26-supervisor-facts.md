# Supervisor plan: harness facts (Phase 0)

Date: 2026-11-26. Claude Code 2.1.332, Linux, model `haiku` for every test session. Plan:
`docs/specs/2026-11-26-supervisor-session-plan.md`. Each entry: what was run, what was seen, what it
means for the plan. Test sessions and worktrees were removed afterwards.

## Summary

| # | Fact | Result |
|---|---|---|
| 1 | A `--bg` session started by a detached process runs, and `claude agents --json` shows it | yes; one state seen |
| 2 | A `--bg` worker in an existing worktree does not push or open a draft PR | not tested |
| 3 | A stopped worker can be woken by a process | yes: `claude stop`, then `claude --bg --resume` |
| 4 | Plugin hooks fire in a `--bg` session in a worktree, with `CLAUDE_PID` and the session id | yes |
| 5 | A `hooks` entry in a custom agent file runs for a session started with `--agent` | **no**; the tool list applies |
| 6 | A subagent runs under the hook in its own agent file | **no**; the settings hook sees its calls with `agent_type`; a main session with `--agent X` has `agent_type: X` too |
| 7 | A headless session can use the Agent tool, in bounded time | yes, 10 seconds |
| 8 | A denied or waiting worker can be told apart in `claude agents --json` | **no** |
| 9 | A headless session reports cost | yes, `total_cost_usd` and `usage` |
| 10 | A PreToolUse denial holds in `bypassPermissions` | yes, from a settings hook |
| 11 | `auto` mode works in a `--bg` session a process starts | yes; no classifier block was produced |
| 12 | `--setting-sources user` hides `.claude/agents/` of the cwd; `--agents <json>` supplies them | yes |
| + | A `--bg` session needs a trusted workspace | new |
| + | `git worktree remove` deletes ignored files without refusing | confirmed |

## Entries

**1. Detached start.** `setsid nohup claude --bg --name spike-w2 --model haiku --permission-mode auto
"<prompt>" </dev/null` inside a worktree. Output: `backgrounded · f82c2f56 · spike-w2`. The work was
done within 20 seconds. `claude agents --json --all` row: `{"pid":…,"id":"f82c2f56","cwd":…,
"kind":"background","startedAt":…,"sessionId":"f82c2f56-…","name":"spike-w2","status":"idle",
"state":"done"}`. Every poll after the first turn showed `status: idle`, `state: done`; no other
value was caught. After `claude stop`: `status: null`, `state: done`, `pid: null`. The `pid` of a
live row is a shared daemon process (`claude bg-spare`), and `CLAUDE_PID` in the session's Bash had
the same value. Meaning: use `sessionId` as the key; a live worker is a row with a non-null `pid`.

**2. Push and draft PR at the end.** Not tested. A background session needs a trusted workspace (see
"Trust"), the only trusted repos on the host have a real remote, and a test that might push to it
was not run. To test: the owner trusts a scratch repo with a local bare remote once
(`claude` in it, accept the prompt). Until then workers that must not push run headless
(`claude -p`), which was already the fallback.

**3. Wake.** On a session that had finished its turn and was still alive,
`claude --bg --resume <sessionId> "<text>"` printed `session f82c2f56 is already running in the
background, so this started a copy as e8ad3784`: a new session id with the old history. After
`claude stop f82c2f56`, the same command printed `woke session f82c2f56 with its saved options
(--name, --permission-mode, --model)` and the session did the new instruction under its old id.
`claude -p --resume <sessionId> "<text>"` on the stopped session also answered under the same id.
Meaning: the watcher wakes a worker with `claude stop <id>` followed by `claude --bg --resume`.
Without the stop the session id changes and the run-guard marker no longer matches.

**4. Hooks and environment in a background worker.** In a worktree of this repo the worker ran
`git push --dry-run origin master`; the transcript shows `PreToolUse:Bash hook error: […]
block-dangerous-git.sh: BLOCKED: … push to protected branch 'master'`. Its Bash wrote
`pid=1917309 sid=f82c2f56-bd2b-4c6f-9936-9d5ba8fa8f94`. Meaning: plugin hooks and both variables
work as in a foreground session.

**5. Agent-file hooks with `--agent`.** `.claude/agents/sup.md` with `tools: [Bash]` and a
`hooks: PreToolUse` entry (matcher `Bash`, a script that denies everything but `echo ok`). Run:
`claude -p --agent sup --permission-mode bypassPermissions` and again with `acceptEdits`. Both
times the script never ran (no log line) and `touch pwned.txt` created the file. The tool list did
apply: the session reported `Bash` as its only tool and had no Write tool. Meaning: the D1 hook
cannot live in the agent file. It is a `hooks` entry in a settings file passed with `--settings`.

**6. Subagent hooks.** `.claude/agents/op.md` with its own `hooks: PreToolUse` entry; the main
session called it through the Agent tool. The agent-file hook never ran. The hook from `--settings`
ran for the subagent's Bash calls, and its input carried `agent_type: "op"` and an `agent_id`. For the
main session's calls the fields were absent only when it was started without `--agent`; a session started
with `--agent X` sends `agent_type: X` on its own Bash calls (seen in the first trial, claude 2.1.332).
Meaning: one settings hook guards the supervisor and its operators, with one command table per
`agent_type`, and the main table answers to `<profile>-supervisor` as well as to no type.

**7. Agent tool in a headless session.** The run of entry 6 took 10.4 seconds and reported
`total_cost_usd` 0.003 for a main session plus one subagent on `haiku`.

**8. A denied worker in `claude agents --json`.** The worker of entry 4 was denied by the hook,
ended its turn with a question to the user, and showed `status: idle`, `state: done`, the same as a
worker that finished its work. Meaning: the JSON cannot tell "finished" from "stopped on a
question". The run guard's `.status` file and the run state on disk stay the source.

**9. Cost.** The headless JSON result has `total_cost_usd`, `usage`, `modelUsage`, `num_turns`,
`permission_denials`, `session_id`, `duration_ms`. A background session prints none of this; its
transcript is at `~/.claude/projects/<cwd-slug>/<sessionId>.jsonl` and holds the usage per message.

**10. Hook denial under `bypassPermissions`.** `claude -p --agent sup --settings <file>
--permission-mode bypassPermissions`: the script ran for both commands, `echo ok` passed,
`touch pwned.txt` got exit 2 and the file was not created. The session reported the denial and did
not retry. Only the headless form was tested; the interactive form was not.

**11. `auto` mode.** `--permission-mode auto` was accepted by a `--bg` session started from a
detached process. An `rm -rf` of a scratch directory outside the working directory ran without a
block. No classifier block was produced, so how one looks from outside is still unknown.

**12. `--agents` with `--setting-sources user`.** In the first trial `claude -p --agent trial-supervisor
--setting-sources user` in a directory with `.claude/agents/trial-supervisor.md` exited 1 (agent not found);
without the flag it worked. Run: `claude -p --model haiku --setting-sources user --agent tt-supervisor
--agents '{"tt-supervisor":{"description":"probe","prompt":"...","tools":["Bash","Read","Glob"],
"model":"inherit"}}' --permission-mode bypassPermissions "say ok"` in a new empty directory under `$HOME`.
Output: `ok`, exit 0. Meaning: the tick and the chat pass the agents inline (`--agents` takes inline JSON, or
with `--print` a file path), keep `--setting-sources user`, and write the agent files only as the readable
source.

**Trust.** `claude --bg` in a new directory exits 1 with `Workspace not trusted. Run 'claude' in
<dir> once and accept the trust prompt, then retry.` The same happened in a subdirectory of a
trusted repo that was its own git repo. A git worktree of a trusted repo, placed beside it, started
without a prompt. Headless `claude -p` ran in the untrusted directory. Meaning: hub worktrees
created by `at sup start-worker` can host background workers; a worktree of a sibling repo that was
never opened cannot, so workers start in the hub worktree and reach sibling worktrees by path.

**Worktree removal.** `git worktree remove` on a worktree holding only an ignored file
(`.local/x`) exited 0 and deleted the file. With an untracked, not ignored file it refused:
`contains modified or untracked files, use --force`. Meaning: `at sup land` must move ignored files
out before it removes a worktree, as the plan says.

## Not observed

- Fact 2 (push and draft PR).
- The state values of a session in the middle of a turn, and of one waiting on the question tool.
- A block by the `auto` mode classifier.
- Entry 10 in an interactive session.
- Whether a message from another session reaches a background worker (the plan no longer needs it).

## From the trials (2026-11-26, same version)

- `claude -p --resume <id>` keeps the session id and the transcript, runs the SessionStart and Stop
  hooks, and does NOT inherit the permission mode: the wake must pass it again.
- `claude -p --session-id <uuid>` is accepted, and `--output-format json` gives the cost per run.
- A Stop hook in a `-p` session works as in an interactive one.
- A background start in an untrusted workspace fails before anything else, so `--bg --session-id`,
  the `woke session` wording after `claude stop`, and liveness through `claude agents` are still
  known only from entries 1 and 3, not from a supervised run.
- The Glob and Grep tools were not available to a `-p --agent` session of this build.
- `--plugin-dir` may be given twice; a development copy took over from the older installed plugin
  and its hooks ran once.

- Sibling worktree (supervisor packs plan, phase 1): `claude -p --model haiku --permission-mode auto` started in
  a hub worktree wrote a file with the Write tool and ran `git add` and `git commit` in a worktree of another
  repo outside its cwd; `permission_denials` was empty. Meaning: a headless worker reaches a pack worktree by
  path with no `--add-dir`. Not tried: the same from a `--bg` worker.

## From the supervisor packs trial (2026-11-27, Claude Code 2.1.332, model `haiku`, headless workers)

Scratch hub with a repo registry, one sibling repo, a pack of three tasks (`--parallel`, `--branch sib=feat/trial`,
cap 2), profile with an `auto` resource `lab` and `local: ["shared/"]`.

- Lease path, first real run: the worker of TST-001 ran `at sup need lab --minutes 5`, was granted at once, ran the
  hub's lab script itself (one line in the script's log, 16 seconds after the start), released, and no lease was left.
- Sibling code: both sibling tasks committed in the pack worktree by the path from `.local/repos.map`; the pack
  branch holds one commit per task in task order; each hub landing commit carries `sib feat/trial <old>..<new>`;
  TST-002 (`Blocked by TST-001`) started 11 seconds after TST-001 landed. Wall time for both: under 2 minutes.
- A write through a symbolic link that leaves the working directory is refused, for the Write tool and for Bash
  (`permission_denials` names the resolved path, "outside the allowed working directories"). The worker of TST-003
  stopped on it and asked. Probe in a scratch directory: the same writes pass when the session is started with
  `--add-dir <target directory>` (the prompt must come before `--add-dir`, which takes several values). Meaning:
  `start-worker` and the wake must pass `--add-dir` for each `local` hub path.
- A write by absolute path into a sibling pack worktree outside the working directory was not refused (as in the
  phase 1 fact); only the path through a link was.
- After the fix (`--add-dir` for each linked `local` entry, after the prompt, on start and on wake) the same worker
  was woken with `-p --resume … --add-dir <hub>/shared`, wrote `shared/notes.txt` through the link, closed out and
  landed; `at sup done` printed `sib: feat/trial, 2 commit(s) over main, ready for PR` and `done: pk`, and
  `close-pack` removed the pack worktree and kept the branch. Not tried: `--add-dir` with `--bg`.
- The `haiku` worker needed two more owner answers on the way: after the first refusal it had asked for a lease
  named after the directory, was denied (`Resources: none`), and asked again instead of retrying the write.
  Meaning: a `local` path must not look like a resource to the worker; the task text should say it is a plain path.
- Result: three hub commits (one squash per task), the pack branch with one commit per sibling task in task
  order, nothing pushed (the scratch repos have no remote), no lease left, no worker left.
