# Runtime: Codex

Use this reference when you can spawn agents from the project's `.codex/agents/*.toml` roles
(`implementer`, `reviewer`, `security-auditor`, `spec-validator`, `plan-critic` — generated from the
plugin's agent cards, so the contracts match Claude Code's) but cannot resume a finished agent by id.

## Dispatch

- Spawn a subagent with the role name and the prompt from `references/briefs.md`. The role's
  `developer_instructions` carry the card; your prompt carries the paths and the contract. The parent
  receives the agent's final summary — insist on the status block by naming the reply limit.
- Roles do not carry tool fences on Codex. Restate them in the prompt every time: implementers "do
  not commit, do not spawn agents"; reviewers "read-only, do not edit files".
- Run the phase reviewers in parallel; they are read-only, so parallel is safe. Never run two
  write-capable agents on the same tree at once: one implementer at a time.
- Subagents inherit the parent's sandbox. Run the session with a workspace-write sandbox; in a
  non-interactive run any action that needs a new approval fails inside the subagent and surfaces to
  you as an error, which you treat as `BLOCKED`.
- Pass paths, not contents.

## Fix rounds: fresh every time

There is no resume-by-id. Every fix round is a fresh dispatch of the same role with the round prompt
and the `findings-R.md` path; the `Agent` column stays `—`. Because the new agent has no memory of
the phase, the round prompt must also name the implementer's `report.md` so it can read what was
already done. Round 3 still switches to the strongest model.

## Model hints

The spawn takes a model override and a reasoning-effort override; omitted, the child inherits the
parent's. This section is the repository's standing instruction to set them, which is the explicit
request the spawn tool asks for before an override:

| Dispatch | Model | Effort |
|---|---|---|
| implementer, rounds 1–2 | the default subagent model | medium |
| implementer, round 3 and final fix wave | strongest available | high |
| phase reviewers, scoped re-review | strongest available | high |
| plan-critic, final reviewers, security-auditor | strongest available | highest available |

A model and effort the runtime does not support together are refused with the supported efforts
listed: retry once with the nearest one. Where a session cannot override per spawn, run the whole
session on the model and effort you would want the reviewers to have.

## Hooks

The plugin's hooks are installed through `hooks.codex.json`; after `at update`, review and trust
them in `/hooks` or they silently stay off. They apply to subagents as to the parent; the
`SubagentStop` hook sends a role subagent back once when its final message lacks the `## Status:`
block, so a missing block after that means re-dispatch fresh.

## Peer check

Pass `--from codex` to `at peer run` and `at peer status`. The peer (`claude -p`) needs the network:
run the command outside the sandbox when asked for approval, or enable `network_access` under
`[sandbox_workspace_write]`; otherwise it exits 3 and the gate goes on without the peer.

## Two more fallbacks

- **Scripted driver**: `at task run <TASK-ID> --harness codex` runs the same loop with no
  orchestrator session at all — one `codex exec` process per implementer or reviewer dispatch
  (`-s workspace-write` / `-s read-only`, the role card prepended to the prompt, `-o` for the final
  message), the identical `_runs/` files, and a commit per phase. It does not adjudicate: at the
  fix-loop cap it marks the row `blocked` and exits 1 for you to add `Ruling:` lines and rerun. See
  `references/run-state.md` §"Scripted driver".
- **Inline**: no subagent tooling in this session — switch `runtime:` to `inline` and follow
  `references/inline-execution.md`.
