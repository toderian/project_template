# Peer check

A read-only second opinion from the *other* agent CLI: Codex when you run in Claude Code, Claude
when you run in Codex. A reviewer subagent of your own harness shares your model family and its
blind spots; the peer does not. It adds to the native review, it never replaces it.

## When

Only when `at peer status` exits 0 (the checkout opted in and the other CLI is installed), and only:

- at the gates the workflow skills name: the final review of every run that ends with code commits,
  task verification (`agents-tasks:verify-task`) of every task, the architecture review of a large
  run, critique of a large or high-risk plan;
- or when the user asks for a second opinion, a cross-check or "ask the other model".

Never per phase: a peer check is a whole second agent run. One peer check
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
   Findings count as `[C]`/`[I]`/`[M]` or `[P1]`/`[P2]`/`[P3]` (critical/important/minor) numbered lines.
   When the reply's `## Findings: N (...)` header disagrees with the lines parsed, the line shows the
   header count and `, count mismatch`: read the saved reply, do not trust the parse.

The peer must not edit. Claude runs without edit tools and with read-only `git` commands only.
Codex runs with `--yolo` (no sandbox, no approvals), so only its brief keeps it read-only. It cannot start a peer of its own.

## Exit codes

| Code | Meaning | What you do |
|---|---|---|
| 0 | A reply was saved, whatever its verdict (the stamp rules are below the table) | Weigh it, below |
| 3 | No peer available; one reason line on stdout | Not required: record `Note: peer check unavailable: <reason>`, name it in the report to the owner at a final or task-end review, and go on. Never wait or retry in a loop |
| 3, checkout is `required` (a `BLOCKED:` line follows) | Same, but the gate is BLOCKED | Stop at the gate. Fix the peer setup (CLI on PATH, login, `at peer enable` in the checkout that holds the code) and rerun; only the owner skips it, with `at peer disable` or a `Ruling:` in chat |
| 4 | A reply was saved, but its `## Findings: N` header and the parsed finding lines disagree (`, count mismatch`) | Read the saved reply yourself; no review stamp is written, so a required checkout cannot push until a clean run |
| 2 | Usage error | Fix the command |

A `reviewer` run writes the push stamp only when it exits 0, the reply has a status line and a verdict, and
`HEAD` is the commit that was reviewed when the run began; otherwise a line says why and no stamp exists.

### Re-runs for the push stamp stay bounded

A fix commit after a peer review needs a new stamp before a required checkout can push. That re-run
is not a new review of the whole branch:

- Brief it on the fix diff only (`<last stamped sha>..HEAD`) plus the numbered findings it fixes.
  List every `Ruling:` so far under "Settled, do not re-raise".
- A new finding from a re-run gets a fix commit only when it is a P1 that a realistic input reaches.
  Every other new finding gets a `Ruling:` or a follow-up, and the branch pushes on the stamp it has.
- At most **two** re-runs per push gate. At the cap, stop fixing: write the `Ruling:` lines, push the
  last stamped commit or report the open P1 to the owner. Never commit again just to chase a verdict.

The stamp records that a review ran, not that it passed, so a re-run with open findings still
unblocks the push once those findings are ruled on.

"Never blocks" holds only when the checkout did not opt into `--required`. A peer enabled in one
checkout says nothing about another: the peer runs with cwd = the checkout that holds the code.

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

- **Required mode:** `at peer enable codex --required` also sets `agents.peerRequired=true` (local git
  config); `at peer status` then prints `required`, and a pre-push hook denies a feature-branch push whose
  `HEAD` has no saved peer review (`at peer run --role reviewer` stamps the reviewed `HEAD` on exit 0).
  `at peer disable` clears both. Use it in every checkout that holds code a gate reviews.
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
