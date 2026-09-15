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

Set the model per spawn where the runtime allows it (implementer: the default subagent model;
reviewers, round 3, final fix wave: the strongest available). Where it does not, run the whole
session on the model you would want the reviewers to have.

## Hooks

The plugin's hooks are installed through `hooks.codex.json`; after `at update`, review and trust
them in `/hooks` or they silently stay off. They apply to subagents as to the parent; the
`SubagentStop` hook sends a role subagent back once when its final message lacks the `## Status:`
block, so a missing block after that means re-dispatch fresh.

## Two more fallbacks

- **Scripted driver** (not shipped yet): the same loop can be driven from a shell script that runs
  `codex exec` once per phase and per review with `--output-schema` for the status block and the
  identical `_runs/` files; `codex exec resume --last` continues a thread. Until `at task run` exists,
  this is a manual option, not a supported mode.
- **Inline**: no subagent tooling in this session — switch `runtime:` to `inline` and follow
  `references/inline-execution.md`.
