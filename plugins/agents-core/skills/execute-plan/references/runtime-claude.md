# Runtime: Claude Code

Use this reference when you can dispatch the plugin's named subagents (`implementer`, `reviewer`,
`security-auditor`, `spec-validator`, `plan-critic`) and resume a finished one by its id.

## Dispatch

- Start a subagent with the named card as its type and the prompt from `references/briefs.md`. The
  card's `tools` list already fences it: implementers cannot spawn subagents, reviewers cannot edit.
- Run the implementer in the **foreground** — you need its status before packaging the diff.
- Run the phase reviewers **in parallel in one turn** (spec, quality, security when applicable),
  each read-only, each with its own report path. Do the same for the two final reviewers. They must
  not see each other's replies; you merge the verdicts.
- Pass paths, not contents. The subagent reads `brief.md` and `diff.patch` itself.
- Every subagent still receives the repo's CLAUDE.md/AGENTS.md hierarchy by default. That is fine for
  implementers (repo conventions) but is pure overhead for reviewers of a diff; when the downstream
  contract is long, a project may set `omitClaudeMd: true` on its own reviewer card override.

## Resume for fix rounds 1–2

A finished subagent returns an id. Record it in the `Agent` column of the row, and for fix rounds
1–2 send the round prompt **to that id** instead of starting a new implementer: it keeps its working
memory of the phase and the warm prompt cache. Round 3 is always a fresh implementer on the strongest
model.

Ids are valid inside the session that created them (and a `claude --resume` of it). On a resumed run
in a new session, ignore the stored id and dispatch fresh; `state.md` is the source of truth.

## Model hints

| Dispatch | Model |
|---|---|
| implementer, rounds 1–2 | the card default (Sonnet-class) — the brief carries the decisions |
| implementer, round 3 and final fix wave | strongest available |
| reviewers, security-auditor, plan-critic | strongest available (`inherit` from your session is usually right) |
| scoped re-review | the same class as the original review; a faster model is acceptable when the findings list is short |

## Isolation

Phase implementers may run in an isolated worktree when the phase touches files you also need to keep
editable in the main tree; the card can request it. When they do, package `diff.patch` from that
worktree, and apply the patch to the main tree before review and commit. The default — the shared
tree with a strict scope fence — is simpler and is what the loop assumes.

## Failure handling

- A foreground subagent cut off mid-run returns partial output flagged as such: treat it as `BLOCKED`,
  keep its `report.md` if written, and re-dispatch fresh with a note about what was already done.
- A reply without a `## Status:` block is not a report. Ask the same subagent (by id) for the block
  once; if it still does not comply, re-dispatch fresh.
- Hooks shipped with the plugin block dangerous git and secret-path writes inside subagents too; a
  blocked subagent reports `BLOCKED` and you decide, you do not route around the hook.
