# Peer check

A read-only second opinion from the *other* agent CLI: Codex when you run in Claude Code, Claude
when you run in Codex. A reviewer subagent of your own harness shares your model family and its
blind spots; the peer does not. It adds to the native review, it never replaces it.

## When

Only when `at peer status` exits 0 (the checkout opted in and the other CLI is installed), and only:

- at the gates the workflow skills name: architecture review and final review of a large run, task
  verification of a large task, critique of a large or high-risk plan;
- or when the user asks for a second opinion, a cross-check or "ask the other model".

Never per phase and never on small work: a peer check is a whole second agent run. One peer check
per gate; re-review after fixes stays native.

## How

1. Write the brief the native role gets to a file, unchanged. It must be self-contained: the peer
   sees no chat history. Name the diff range or the plan path in it, never paste a diff.
2. Start the peer in the background, then go on with the native dispatch:

   ```bash
   at peer run --from <claude|codex> --role <reviewer|plan-critic|security-auditor> \
     --brief <brief file> --out <reply file> [--model <model>] [--effort <level>]
   ```

   `--from` is the CLI you run in. Claude Code is detected without it; Codex is not.
   `--model` and `--effort` are yours to choose per call, by the same rule as any dispatch
   (strongest model and high effort for architecture and final review, less for a narrow
   question). Both use the peer CLI's own names; without them the checkout's defaults apply, then
   the CLI's own.
3. When it returns, read the one summary line, then the saved reply:
   `peer codex (reviewer): FAIL, 3 finding(s), 1 critical -> <reply file>`.

The peer cannot edit: Codex runs in its read-only sandbox, Claude without edit tools and with
read-only `git` commands only. It cannot start a peer of its own.

## Exit codes

| Code | Meaning | What you do |
|---|---|---|
| 0 | A reply was saved, whatever its verdict | Weigh it, below |
| 3 | No peer available; one reason line on stdout | Record `Note: peer check unavailable: <reason>` and go on. Never wait, retry in a loop, or block the gate |
| 2 | Usage error | Fix the command |

## Weighing the reply

Peer findings are evidence, not orders, and the peer's verdict does not overrule the native one.

- Check every `[C]` and `[I]` finding against the code yourself before acting on it.
- A confirmed finding joins the native findings in the normal fix loop.
- A finding you reject gets a `Ruling:` line with the reason, like any other.
- `[M]` findings are recorded as non-blocking.
- Native `PASS` with a confirmed peer `[C]` finding is a `FAIL` for the gate.

Record the outcome where the gate records its own, one line:
`Note: peer <role> (<cli>): <verdict>, <n> finding(s), <m> confirmed`.

## Setup and limits

- **Opt in per checkout:** `at peer enable codex` (or `claude`, or both). The setting is local git
  config (`agents.peers`), never committed. The peer's provider receives the brief and every file the
  peer reads, so enable it only where that is acceptable; `at peer disable` turns it off.
- **Model and effort defaults:** `at peer enable codex:<model>:<effort>` stores them for that peer
  (`codex::high` sets an effort and no model); `--model` / `--effort` override them for one call.
  Pin a model when the CLI's configured default is refused in non-interactive runs. `at peer status`
  shows what a call would use, and the saved reply's `Peer:` line records what was used.
- **Calling from Codex:** the peer needs the network. A sandboxed shell command has none by default,
  so approve `at peer run` to run outside the sandbox, or set `network_access = true` under
  `[sandbox_workspace_write]` in the Codex config. Without it the call exits 3 with an API error.
- **Time:** about a minute for one commit, several for a whole task. The default limit is 900 s
  (`--timeout`).
- **Cost:** the peer bills its own account; the caller sees no figure for it.
