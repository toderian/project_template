# Changelog

Notable changes to agents-template. All four plugins share the version of the repository.

## Unreleased

### Changed

- Every Codex dispatch (`at peer run`, `at task run --harness codex`) runs on `gpt-6-sol` unless a
  model is set, and always under OpenAI's Daybreak Blue cyber access program
  (`--cyber-access-program daybreak_blue`). With `daybreak = true` in the Codex config, the earlier
  headless pin `gpt-6-astra` failed before it started, because that model has no Blue. The account
  needs Daybreak access. `at peer status`, the saved reply's `Peer:` line and the task-run label name
  the model and the program.
- Seed `AGENTS.md`: an authorized security task the main model refuses or flags goes to
  `at task run <TASK-ID> --harness codex`.
- The release check expects Codex CLI 0.172.0.

### Fixed

- A role card sent to Codex or `claude -p` carried `${CLAUDE_PLUGIN_ROOT}` unexpanded, so the agent
  could not open the skill files the card names. `card_body` now puts in the plugin path.
- `at peer enable codex:<model>::<effort>` (one colon too many) stored the effort as `:<effort>`,
  which every later call passed to Codex. A peer entry with more than three fields is now refused.

- The sensitive-path guard had gaps, found by a Codex peer security review of the hook.
  - Shell writes were not guarded at all. `block-dangerous-bash.sh` now blocks a redirect, `tee`,
    the destination of `cp`/`mv`/`install`, and `sed -i` when the target is under `.creds/` or is a
    `.env` file. Reading stays allowed, and so does writing `.env.example`.
  - `block-write-sensitive.sh` now blocks `credentials.json`, `secrets.yaml` and the like (a
    sensitive name with a config-file extension), any `*.env` file, `.envrc`, `id_ecdsa`, `id_dsa`
    and `*.pfx`.
  - A path that reaches a protected directory through a symlink is blocked (needs GNU `realpath`).

## 1.13.1 — 2026-11-21

### Fixed

- `at design stale` reads square brackets in a `code_paths` entry as part of a folder name. A route
  folder such as `app/[jobId]/**` was read as a character class and never matched, so the leaf was
  reported as current.

## 1.13.0 — 2026-11-21

### Added

- `at design stale` lists every implemented design leaf whose `code_paths` hold a file that changed
  since the leaf's `verified` commit. It reads the product checkouts from `.local/repos.map` and the
  path prefixes from the tree's root `README.md`. On the pilot tree it named 29 of 116 leaves after
  one product merge.

## 1.12.2 — 2026-11-20

### Fixed

- `at explore --dir <path> ...` was rejected as an unknown argument; the option now reaches the ledger
  script.

## 1.12.1 — 2026-11-20

### Fixed

- `at design sync`: a module summary in a generated index is the first sentence of the README's first
  paragraph. It was cut at the first line break, so a wrapped sentence lost its end.
- The 1.12.0 section of this file was still titled Unreleased in the `v1.12.0` tag.

## 1.12.0 — 2026-11-20

### Added

- Design trees: `docs/resources/<area>/design/` is the source of truth for how a product works and
  why. One leaf per feature, grouped in modules, each with frontmatter (`summary`, `status`,
  `verified`), fixed sections and an append-only Decisions table. The format is
  `agents-tasks:knowledge-base` `references/design-convention.md`; the new skill
  `agents-tasks:design-doc` writes, refreshes, splits and converts leaves. Piloted on a 151-file
  tree converted from 26 feature contracts.
- `at design sync` writes the generated index and open-task blocks in design `README.md` files;
  `at design check` fails on a missing or invalid leaf header, a leaf over 500 lines, a broken
  relative link, an invalid Decisions table, an unindexed leaf, a stale generated block, and an
  open task whose `Spec refs` names a design path that does not exist. `at ledger sync`,
  `at ledger check` and `at doctor` include the design trees when a repository has one.
- Write-time simplicity rules, adapted from Ponytail 5: the seed `AGENTS.md` Build pass and the
  `implementer` agent now list where a change must reach and take the first option that works
  (nothing, existing repo code, standard library or platform, installed dependency, one line, new
  code). A test is owed only for logic that can break; a trivial change gets none. Status blocks end
  with `## Not checked:`.
- Review rules: a finding needs a concrete case, a split is by job and never by line count, and a
  `simplicity:` comment that names its ceiling is a decision. `agents-core:simplicity-review` gains
  the `split` tag.
- `agents-tasks:exploratory-test`: agents test a running product end to end against its design tree.
  One leaf statement per scenario, a replay of every mismatch, a clean-context refuter that tries to
  explain it away, and a fingerprint so a finding is filed once, as an inbox idea. `at explore`
  keeps the coverage ledger (`build`, `next`, `record`) and the fingerprints (`fingerprint`,
  `known`). The repo provides the harness; `references/harness.md` says what it must do. Piloted on
  45 cells of one product: five findings filed, all five accepted as bugs by the owner.
- A task that changes behaviour names the design leaf in `Spec refs`; `agents-tasks:complete-task`
  brings the leaf up to date before closeout.

### Changed

- Release checks expect Codex CLI 0.171.0 (was 0.169.0); CI tests 0.147.0 and 0.171.0.

## 1.11.0 — 2026-11-19

### Added

- Review rounds have at least two independent reviewers with different focus
  (`agents-core:subagent-protocol` §"Review round"). Small-mode `execute-plan` gets a second
  per-phase reviewer (tests and failure paths) and a two-reviewer final review; the peer joins every
  final review and every `verify-task` run, and an unavailable peer is named to the owner.
- Re-reviews are bounded. A new finding outside the fixed ones joins the fix loop only when it is a
  `[C]` finding on a realistic input or an unmet acceptance criterion. In a `required` checkout, peer
  re-runs for the push stamp review the fix diff only, add no fix rounds, and count every run (at
  most two after the first per push). At the cap with an unstamped `HEAD` or an open `[C]` finding,
  the agent stops and reports to the owner (`peer-check.md` §"Push stamp in a required checkout").
  Measured on a scratch project: 4 fix commits and 5 peer runs before, 1 and 2 after.
- The pre-push stamp check accepts commits that change only `docs/tasks_manager/` on top of a
  stamped commit, so run state and rulings committed after the review do not block the push.
- Review round shape: one reviewer checks the spec and acceptance criteria, one hunts for what
  breaks. An A/B run (6 seeded cases, 72 reviews) showed two attackers find 56% of spec-only bugs,
  a spec reviewer plus an attacker 100%.

- `at peer enable <cli> --required` stores `agents.peerRequired`; `at peer disable` clears it and `at peer status`
  prints `required`. With it, exit 3 (peer unavailable) also prints a `BLOCKED` line and a gate must stop: "an
  unavailable peer never blocks" holds only when the checkout did not opt in.
- Pre-push stamp: `at peer run --role reviewer` records the reviewed `HEAD` under
  `<git-common-dir>/agents/peer-reviewed/<sha>` on exit 0. `block-dangerous-git.sh` denies a feature-branch push whose
  commit has no stamp when `agents.peerRequired` is true, naming the command to run. Tag pushes, branch deletes,
  protected-branch and force-push rules are unchanged.
- Run state takes an optional `code_repo` (`at task run-state init --code-repo`) and
  `at task run-state check <ID> --final` fails a run with a committed phase and no `final-review-peer.md` when the
  peer is required in that checkout. `execute-plan` runs the final peer review with cwd = the code checkout at every
  rung that ends with code commits, not only large mode.
- Consequence checklist (callers of changed contracts, reused-helper behaviour, newly reachable paths, sibling paths
  of the invariant, failure-path logging and persistence, the input that fails each new test) in the reviewer's
  Stage 2, the final-review brief and the `at task run` final prompt, answered in `## Evidence`.
- Large-mode final reviewer 2 is unanchored: goal sentence, diff range and checklist only, no plan, design or rulings.
- Review-escapes log convention in `agents-tasks:knowledge-base` and an escape-ratchet rule in
  `agents-core:subagent-protocol`.

### Known limits

- The `at task run` driver still runs one reviewer per small-mode phase and no small-mode final
  review 2; the skill's two-reviewer rule applies to the manual path.
- The scripted `at task run` driver does not dispatch the peer, run `--final`, or give final reviewer 2 the
  unanchored brief.
- After a `cd` to a path the push hook cannot resolve, the required-review check reads the original checkout's
  config.

### Changed

- `at peer run` counts `[P1]`/`[P2]`/`[P3]` findings (bold or plain) as critical/important/minor next to
  `[C]/[I]/[M]`, shared with `at task run`. A `## Findings: N (...)` header that disagrees with the parsed lines is
  reported as the header count plus `, count mismatch`, not 0.
- `execute-plan` step 0 security surface adds error handling and logging of user or target data, persistence of
  reports or evidence, and redaction; `security-auditor` checks failure-path data exposure.
- A design line or `Ruling:` that accepts losing data or evidence, or a "known gap" on the changed path, needs the
  owner's ruling in chat; `plan-critic` flags it as blocking.

## 1.10.0 — 2026-11-18

### Changed

- `at task size` measures fixtures as their own kind (data files, and non-code files under `fixtures/`, `testdata/`,
  `mocks/`, `__mocks__/` or `__snapshots__/`, wherever they sit). Co-located tests (`foo.test.ts`, `foo.spec.tsx`,
  `x_test.go`) now count as test. It flags a fixture of 500 lines or more, and a phase whose test+fixture net is at
  least 300 and over 2x its code net. The Total line gains `Fixture net`.
- Reviewer, execute-plan briefs and the `Shape:` convention review those flags and
  judge test redundancy: one behaviour asserted at several layers, near-duplicate cases, fixtures that
  copy derived data.
- Implementers write a `## Test plan` first (behaviour -> lowest layer -> test names; fixtures with size, one of 500 lines or more needs a reason): `at task brief` Report contract, the implementer prompt and briefs. Reviewers check every test maps to a row, and an unjustified fixture or test-ratio flag is critical (fails the review), stricter than a code flag since bulk data growth has no logic to review. `at task run` prompts, `execute-plan` and the implementer report shape carry the same rules. The final review adds one cross-phase pass for duplicated tests and fixtures. `agents-core:tdd` starts the red step from the behaviour list.
- Seed `AGENTS.md` gains a "Lean tests" principle; `agents-core:tdd` points at it. `at init` never
  overwrites `AGENTS.md`: downstream repos adopt the bullet through `agents-core:setup-project`.
- Release checks expect Codex CLI 0.169.0 (was 0.167.0); CI tests 0.147.0 and 0.169.0.

## 1.9.2 — 2026-11-16

### Fixed

- Empty plugin-inventory tests use a controlled CLI stub, so they exercise the same behavior on
  development machines and CI runners where Claude Code is not installed.

## 1.9.1 — 2026-11-16

### Fixed

- Task-run test repositories now configure their own Git author identity, including commits made
  by driver subprocesses. CI verifies the suite without global or system Git configuration.

## 1.9.0 — 2026-11-16

### Added

- `agents-extras:sync`: explicitly reconcile Claude and Codex memories for the current repository
  into shared local context, with preview, source provenance, conflict resolution, and project
  startup pointers. Native memory stores remain intact; global preferences are excluded.

### Changed

- Agents may invoke `agents-tasks:complete-task` automatically after authorized implementation and
  verification. `agents-core:execute-plan` now hands off to closeout before advancing an authorized
  task chain. Closure still requires acceptance evidence, required checks, ledger validation, and
  a closeout commit; explicit human acceptance gates remain in effect.
- The seed operating contract includes automatic verified closeout. Existing repositories can
  adopt it through `agents-core:setup-project` after updating plugins and restarting.

## 1.8.2 — 2026-11-15

### Fixed

- The implementer subagent allows `TaskStop`, so it can stop background commands started with Bash.

## 1.8.1 — 2026-11-14

### Changed

- Every Codex process the template starts (`at task run --harness codex` implementers and reviewers,
  `at peer run`) now runs with `--yolo`, which turns off Codex's sandbox and approval prompts.
  A headless run cannot answer an approval prompt, so the sandbox kept blocking real work. Reviewers
  and peers are now read-only by prompt alone: the reviewer prompts already carry a scope fence, and
  `at peer run` puts one at the top of every brief.
- The seed `.claude/settings.json` no longer denies `Read(./.creds/**)`, and `at init` removes that
  rule from a repo seeded earlier. A deny rule cannot be overridden, so it blocked every session
  from reading a credential the task needs, which the seed `AGENTS.md` permits ("read one only when
  the task needs it, never echo or commit a value"). `Edit(./.creds/**)` stays denied, and the hooks
  still refuse to write, stage or commit anything under `.creds/`. A repo that wants reads blocked
  puts the rule in `.claude/settings.local.json`, which `at init` never touches.

## 1.8.0 — 2026-11-10

Seven fixes taken from how the downstream repos actually use the template: a survey of their
ledgers, their `at doctor` output and their session transcripts. Plus two new opt-in capabilities:
a read-only second opinion from the other agent CLI, and UI add-ons a repository switches on for
itself.

### Fixed

- `block-dangerous-git` hook: the staging guards read only the `git add` segments of a command, and
  heredoc bodies are skipped. A later `git commit -m "drop the -f flag"`, a heredoc commit message
  containing `rm -f`, or a `grep` for the flag text is no longer refused as a forced add.
- `at init` merges the seed `permissions.ask` rules like it merges `permissions.deny`. The 1.7.0
  rules for the protected-push marker and `gh pr merge` never reached a repo seeded earlier, so its
  protected push had no second confirmation. Run `at init` once in each such repo.

### Added

- `at doctor` names every seed `deny` / `ask` rule a repo's `.claude/settings.json` lacks.
- `at ledger rotate-log --all` rotates every execution log over the 200-line limit, and
  `at ledger sync` does that first. `at ledger check` never writes. The first sync in a repo with
  many long logs moves them all into `docs/tasks_manager/_logs/` in one diff.
- `at doctor --drift` and a `SessionStart` hook (`session-drift.sh`) that runs it: a session started
  in a repo behind the plugin seed says so in one line. Silent when the repo is current or was never
  seeded. Codex users review and trust the new hook under `/hooks`.
- `at ledger check` warns, without failing, when the backlog decays: more than 20 untriaged inbox
  ideas or one older than 30 days that no roadmap horizon holds; more than 5 tasks `in_progress`;
  `in_progress` tasks not updated for 30 days. Each warning names the skill that clears it.

- Peer check: `at peer enable <claude|codex>[:<model>[:<effort>]]` opts one checkout in (local git config
  `agents.peers`, never committed), and `at peer run --role reviewer|plan-critic|security-auditor
  --brief F --out F` asks the other agent CLI for a read-only review: Codex from a Claude Code
  session, Claude from a Codex session. The caller picks the peer's model and reasoning effort per
  call with `--model` / `--effort`. `agents-core:execute-plan` (architecture and final review of
  a large run), `agents-tasks:verify-task` and `agents-core:planning-workflow` use it when it is
  enabled, next to the native reviewers; an unavailable peer (exit 3) never blocks. The peer's
  provider receives the code it reads, so nothing is enabled by default. `at doctor` reports the
  listed CLIs. From Codex the call needs network access outside the default sandbox.
- Optional add-ons: `at addon enable browser|shadcn` switches a tool on for one repository, and
  `at addon list|status|disable` manage it. `browser` is ChromeDevTools/chrome-devtools-mcp (the
  agent sees the rendered page in a headless Chrome; usage statistics off), `shadcn` is the shadcn
  MCP server for React + Tailwind repos. Each is an MCP server from its upstream, pinned and started
  with `npx`, never copied in. A non-interactive `codex exec` run needs the server's tools
  pre-approved by hand (see the README). `enable` commits the choice in `.mcp.json`, enables `agents-extras` in
  `.claude/settings.json`, and registers the server for Codex in the checkout's git-ignored
  `.codex/config.toml`. `at doctor` reports enabled add-ons; `agents-extras:frontend-design` and
  `agents-extras:ui-design-review` use the tools when a session has them, and the seed routing
  table gains a UI row.
- `at task run --effort <level>` and `--strong-effort <level>`: reasoning effort for implementers,
  and for reviewers plus the fix round after two failed ones, next to `--model` / `--strong-model`.
  The execution-log headings record the model and effort a run set.
- Dispatch guidance names a reasoning effort next to the model class: the model-selection table in
  `agents-core:subagent-protocol`, the `Model hint:` lines of the `agents-core:execute-plan` briefs,
  and the Claude Code and Codex runtime references. The dispatching session sets both per spawn.

### Changed

- `at doctor` prints a ledger warning repeated across four or more tasks as one line with a count
  and three examples.
- `block-dangerous-git` hook: a bare `git push` after `cd <literal path>` or `pushd <literal path>`
  is resolved against that checkout instead of refused; a directory change the hook cannot follow is
  still refused. The protected-branch list comes from the repository being pushed.
- Seed `AGENTS.md`: Frame now has the agent state its assumptions, present competing readings of a
  request and name a simpler way before building; the surgical-diff principle adds "match the
  existing style" and "report unrelated problems, do not fix them unasked"; "Simplicity first" bars
  unrequested features, options, abstractions and error handling. Ideas taken from
  `multica-ai/andrej-karpathy-skills`; an existing repo adopts them through
  `agents-core:setup-project`.
- Repository tooling: CI runs the task size gate tests; the live Codex gate in CI and in
  `scripts/release.sh` moves from 0.155.1 to 0.167.0 (0.147.0 stays the minimum);
  `scripts/tests/run-all.sh` runs the two-minute half of the release test only when a release file
  differs from `HEAD`, and `release.sh` always runs it; `scripts/check-addon-pins.sh` compares the
  add-on pins with npm and `release.sh` prints its result without blocking. The `at migrate` code
  moved from `lib/at.py` into `lib/migrate.py`, with no change in behaviour. The two executed plans
  under `docs/plans/` are removed; they stay in git history.

## 1.7.0 — 2026-09-25

Agents may push feature branches and open PRs. A push to a protected branch needs two confirmations
from the user.

### Changed

- `block-dangerous-git` hook: `git push` is no longer refused in every form. It allows a push to a
  feature branch. It refuses force pushes (`-f`, `--force*`, `+refspec`) and a push that reaches a
  protected branch (`main`, `master`, `develop`, or `git config agents.protectedBranches`, globs
  allowed) or whose target it cannot resolve. A protected push passes only with
  `git -c agents.allowProtectedPush=<branch>`, which the agent adds after an explicit yes in chat.
- Seed `settings.json` adds `ask` rules for that marker and for `gh pr merge`, so the harness prompts
  the user a second time, even in auto mode. Codex has no equivalent rule; there the hook and the chat
  confirmation are the gate. Existing repos copy the `permissions.ask` block into
  `.claude/settings.json`.
- `agents-core:git-discipline`, the autonomy ladder and the seed `AGENTS.md` describe the new rule.
- CI and releases validate against current Codex `0.155.1` (minimum stays `0.147.0`).

## 1.6.0 — 2026-09-18

Size is measured at every review point. A five-round fix loop on a downstream task had turned a
386-line component into 680 lines with 13 new state primitives; every finding was right and every
fix added a guard, and nothing in the loop looked at the total until the human read the PR diffstat.

### Added

- `at task size <TASK-ID> --phase N [--fix R] | --final` (agents-core `lib/task_size.py`): lines per
  file before and after, code/test split, a `Flagged:` line (code file +40 lines and +25 %, new code
  file ≥ 120 lines, phase code net ≥ 300) and, for a fix round, what that round alone changed.
  Writes `phase-N/size.md`, `phase-N/size-fix-R.md` or the run's `size.md`; prints the phase's
  `Shape:` line when the task file has one.
- `agents-core:execute-plan` structural-round rule: when fix rounds 1 and 2 each grew the same code
  file, round 3 restructures instead of adding a third guard; if it still grows, the phase blocks and
  the user decides. `at task run` implements it.
- `reviewer` card `Stage: simplicity` (delete / shrink / reuse / yagni findings; fails on an
  unjustified flagged file or a code net over the plan's `Shape:`). The final whole-task review
  dispatches it as a third reviewer in large mode and folds it into the single reviewer in small mode.
- Optional `Shape:` line under a phase heading (`agents-tasks:task-ledger` todo convention) stating
  the size the phase should end at; the spec reviewer checks it like a checklist item.
- Final validation logs the run's size and a `Note: PR size … split candidate` line at code net ≥ 600
  or ≥ 15 files, so the size is seen before a PR exists.

### Changed

- Quality reviewers and re-reviews receive the size table; unexplained growth is a finding and a
  file that grew in a phase meant to shrink it is critical. The fix-round prompt prefers
  restructuring or deleting over adding a flag, ref, effect, lock or retry.
- Phase commits carry a `size:` line under `Checks:`; execution-log entries carry the size.
- `agents-tasks:add-task`: a second independent report against an open task becomes a second task,
  not another phase. `agents-tasks:verify-task` reports the size table in `Scope:`.
- `agents-core:planning-workflow` and the `plan-critic` card ask for an expected shape per phase.

## 1.5.1 — 2026-09-17

- Seed `statusline.sh` shows absolute context tokens next to the percentage, e.g.
  `ctx 10% (96k/1M)`, also when a GSD status line renders line 1. Existing downstream repos keep
  their copy (`at init` never overwrites it); copy the new seed file to adopt it.

## 1.5.0 — 2026-09-15

The simplicity release (`docs/meta/2026-09-15-simplicity-audit.md`): the skills now do the simplest
plan that works and climb to the heavy machinery on a trigger instead of starting there.

### Removed

Five skills whose job another one already covered. `at doctor` warns while a downstream `AGENTS.md`
still routes to one; `agents-core:setup-project` references/adopting-updates.md §"Removed skill ids"
has the mapping.

| Old id | Use instead |
|---|---|
| `agents-core:grill-me` | `agents-core:grilling` |
| `agents-extras:grill-with-docs` | `agents-core:grilling` + `agents-extras:domain-modeling` |
| `agents-core:research` | a `researcher` dispatch (`agents-core:subagent-protocol` §"Research dispatch") |
| `agents-core:task-spec-workflow` | `agents-tasks:add-task` step 4b (references/spec-sections.md) |
| `agents-tasks:prd-to-plan` | `agents-core:planning-workflow` step 7 "From a PRD" |

### Changed

- `agents-core:execute-plan` picks a rung. **Small** (default: ≤ 2 phases, ≤ ~10 files, no trigger):
  the orchestrator implements each phase itself, one read-only `reviewer` with `Stage: both` judges
  the phase checklist first, one final reviewer only for a two-phase task. **Large** (≥ 3 phases, a
  security surface, migration, public contract, multi-repo scope, a `### Design` section or external
  `Spec refs`, `Execution: orchestrated`, or a small run that blows its context): the unchanged
  pipeline. A run never de-escalates. `state.md` carries `mode:` / `mode_reason:`; `phase-N/review.md`
  holds the single review. The inline runtime is small mode and no longer stops to ask about a rerun.
- Task files have a required core (Task ID, Type, Area, Created, Updated, Status, Priority, Source,
  title, brief, phases, acceptance criteria); everything else is optional and added when first
  needed. `add-task` writes no execution-log, harvest or summary placeholders and prefers one phase.
  The pre-implementation gate is a ≤ 3-line current-state note for a trivial task. Repo registry and
  spec lifecycle moved to `task-ledger/references/repos-and-autonomy.md` and `spec-lifecycle.md`.
- Plan critique: the score decides; no minimum rounds, no "surface at least one gap" rule.
- Seed `AGENTS.md`: a one-sentence diff skips Frame and Critique; the two planning rows merged (a
  downstream table shows "1 row behind" once); caveman detail moved to adopting-updates; the
  anti-patterns section (all duplicates) removed. 153 → 138 lines.
- Skills hand off to a peer once and never describe it; task-ledger, setup-project, codebase-design
  and wayfinder lost their sibling lists. Repo `AGENTS.md` records the rule.
- `remind-archive-done-todo.sh` says REMINDER, not BLOCKED (it is PostToolUse and never blocked).

### Added

- `agents-tasks:simplify-task` (explicit-only): reduces an existing task to the smallest plan —
  keep / merge / cut / defer per item, brief-stated items protected, deferred work recorded — and
  rewrites the file only after showing the diff.
- `agents-tasks:verify-task` (report-only): re-runs the task's tests fresh, checks each criterion
  goal-backward (exists / substantive / wired), detects criteria that changed during the task from
  the file's git history, dispatches `spec-validator` and a `Stage: both` reviewer, and reports
  MET / NOT MET / UNVERIFIABLE per criterion with PASS / GAPS / HUMAN_NEEDED.
- `at task run --mode small|large|auto` (auto: large on ≥ 3 phases, `--security`, a `Repos` row, a
  `### Design` section or `Execution: orchestrated`).
- `at doctor` warning for removed skill ids (`REMOVED_SKILL_IDS`, append-only).

## 1.4.4 — 2026-09-15

### Changed

- `at task run` on Claude lets reviewers execute exactly the `--check` commands (`Bash(<cmd>)`
  allow rules under `dontAsk`) so they can confirm a test result instead of inferring it; edits stay
  disallowed and no other command is approved.

## 1.4.3 — 2026-09-15

Found by the first real run of the flow (a two-phase task driven by `at task run` against the
Claude CLI: both phases committed, final review green, $2.68).

### Fixed

- A phase was judged against the task-wide acceptance criteria: the spec reviewer failed phase 1
  for criteria that belonged to phase 2, the fix round pulled phase 2's work forward, and phase 2
  then burned three fix rounds on "implementer changed no files" before blocking. `at task brief`
  now states that the phase checklist is the whole scope and that the task-wide criteria are
  verified after the last phase; reviewer prompts and SKILL.md step 5.6 say the same; an empty
  phase diff is reviewed against the run's diff since `base_rev` instead of failing on principle.

### Added

- After a passing final review the driver ticks the task-wide acceptance criteria, logs the
  review in the execution log, and includes the task file in the closing run-state commit; the
  skill's step 7 does the same.

## 1.4.2 — 2026-09-15

### Fixed

- `at task run` built the `claude -p` command with the prompt after `--allowedTools` /
  `--disallowedTools`; both flags take a space-separated list, so the prompt was consumed as a tool
  name and the dispatch ran without one. The prompt now follows `-p` directly and tool lists are
  comma-joined. The test fake harness parses argv like the CLI so a misplaced positional fails the
  suite.

## 1.4.1 — 2026-09-15

### Fixed

- Reviewers are read-only on both harnesses (`reviewer` / `security-auditor` cards, `codex -s
  read-only`), so 1.4.0's "write the review to a report path" could never be honoured. The reply is
  now the report — verdict block first, evidence after, under 40 lines — and the orchestrator (or
  `at task run`) saves it to `review-<stage>.md`. Briefs, SKILL.md, run-state layout and
  subagent-protocol updated; Codex TOML regenerated.
- `at task run` on Claude ran implementers with `--permission-mode acceptEdits` only, so every Bash
  call (running the tests the brief asks for) was denied in `-p` mode. Implementers now get
  `--allowedTools Bash` (the plugin's dangerous-git/bash hooks still gate each command); reviewers
  run `dontAsk` with the edit tools disallowed.
- Two parallel Codex reviewers shared one `-o` output file and raced on it; the file is now unique
  per dispatch.

### Added

- `at task run`: `--timeout` (1800 s) kills a silent dispatch and marks the row `blocked`;
  `--budget-usd` (5) is passed to `claude -p` as `--max-budget-usd` and the reported cost is logged
  per dispatch and per phase (Codex: timeout only); a `lock` file in the run directory refuses a
  second concurrent driver (`--force-unlock` for a stale one); after each phase commit the driver
  runs the run-state and ledger checks (ledgers are synced before the commit); a status-less
  implementer reply is asked for once more, as the `SubagentStop` hook does for subagents. Seed
  `.gitignore` block ignores `_runs/*/lock`.
- CI now runs `test_task_brief.py` and `test_task_run.py`.

### Changed

- `agents-core:execute-plan` documents its limits: one checkout per run (multi-repo tasks are one
  run per repo), phases in order, and the trust boundary of an implementer with Bash approval (use
  worktree isolation for untrusted repositories). Step 9 runs `at ledger sync` before the phase
  commit so the regenerated ledgers ride in it.
- README lists the `at task` commands; the setup-project adopt-updates reference covers refreshing
  `.codex/agents/*.toml`, the `_runs/` ignore rules and trusting the new hook in Codex.

## 1.4.0 — 2026-09-15

### Added

- `at task brief <TASK-ID> --phase N` writes one phase of a task file — plus the task brief,
  acceptance criteria, related tests, specification, design and spec-ref paths, never the execution
  log or other phases — to `docs/tasks_manager/_runs/<TASK-ID>/phase-N/brief.md` as the sole context
  for an implementer subagent. `at task run-state init|check <TASK-ID>` writes and validates the
  `_runs/<TASK-ID>/state.md` resume map (one row per phase with status, review verdicts, commit SHA;
  `Ruling:` / `Interface:` / `Note:` lines). Both are stdlib scripts under the task-ledger skill,
  delegated like `at ledger`.
- `docs/tasks_manager/_runs/` is a governed directory: seeded by `at init --with-tasks`, listed in the
  task convention, committed with phase commits (only `diff.patch` is git-ignored), removed by
  `agents-tasks:complete-task` after its rulings are copied into the completion summary, and flagged by
  `at ledger check` when it outlives its task.
- `agents-core:execute-plan` ships five references: `run-state.md`, `briefs.md`, `runtime-claude.md`,
  `runtime-codex.md`, `inline-execution.md`.
- `at task run <TASK-ID>`: the scripted driver for that loop. One `claude -p` or `codex exec` process
  per implementer or reviewer dispatch (role card as system prompt, writable vs read-only fences,
  `--resume` for Claude fix rounds), the same `_runs/` files, a commit per phase, an optional
  `--check` command before and after each phase, `--security` for the auditor, `--dry-run`, and a
  strict clean-tree gate. It stops at the fix-loop cap (`blocked` row, exit 1) instead of adjudicating.
  Tested against a fake harness (`scripts/tests/test_task_run.py`).
- A `SubagentStop` hook (`require-subagent-status.sh`) sends `implementer`, `reviewer`,
  `security-auditor`, `spec-validator`, `plan-critic` and `researcher` subagents back once when their
  final message lacks the `## Status:` block; it never loops (`stop_hook_active`) and allows the stop
  when the message is unavailable. Same event, matcher and exit-2 semantics on Claude Code and Codex,
  so `hooks.codex.json` is generated unchanged. Codex users must trust the new hook in `/hooks`.

### Changed

- `agents-core:execute-plan` is now a thin orchestrator. It detects the runtime once (Claude Code
  subagents, Codex subagents, or inline), dispatches a fresh `implementer` per phase from a
  self-contained brief, packages the diff, runs a spec reviewer and a quality reviewer in parallel
  (plus `security-auditor` when the phase touches a security surface), caps the fix loop at three
  rounds before adjudicating with `Ruling:` lines, runs the checks and commits itself, and records
  every step in `_runs/<TASK-ID>/state.md` so a later session resumes from disk. Reports, diffs and
  reviews are files; the orchestrator's context holds paths and ≤ 20-line verdicts. The final review
  is one whole-task round with one fix wave. Inline execution remains available and is labelled
  "not independent".
- `agents-core:subagent-protocol` gains the artifacts-as-files rule, the fix-loop policy (resume
  twice, fresh strongest model, then rulings) and the `Stage: spec | quality | both` reviewer line.
- Agent cards: `implementer` never commits, stages or spawns subagents and writes its report to the
  brief's report path; `reviewer` honours `Stage:` and replies with a compressed verdict block
  (`## Verdict`, `## Findings: n (C/I/M)`, `## Report`); `security-auditor` and `spec-validator`
  take a report path. Codex TOML twins regenerated.

## 1.3.0 — 2026-09-12

### Added

- The [caveman](https://github.com/JuliusBrussee/caveman) skill ships as a companion, installed
  from its own marketplace rather than vendored. `at bootstrap` and `at update` install or refresh
  it on the machine for each harness they touch (Claude as the `caveman@caveman` plugin, Codex as a
  global skill through `npx skills add`), and the seed `.claude/settings.json` enables it, so a
  downstream repo picks it up on its next `at init` and Claude Code installs it at the next session
  start. `at doctor` now checks every plugin the seed enables and warns when `node`, which the
  caveman hooks need, is missing. The seed routing table gains a row for it, so existing repos see
  the drift and adopt it through `agents-core:setup-project`. `at init` writes a local
  `.caveman.json` with a null `defaultMode` (inherits the user config, default `full`), which the
  seed `.gitignore` block ignores and `at migrate --commit` never stages, so switching it to `off`
  is a per-checkout edit that cannot be committed and a machine-wide opt-out is still honoured. Terse mode
  is session-wide in Claude and per-session (`$caveman`) in Codex. The companion is optional: a
  missing `npx` or a failed install is reported and never fails `at bootstrap` or `at update`, and
  `at doctor --codex` reports whether the Codex skill landed.

### Changed

- CI and releases validate against current Codex `0.154.0` (minimum stays `0.147.0`).

### Fixed

- `at` finds the installed `agents-tasks` seed through the cache next to its own plugin root, so
  `at init --with-tasks` works when the harness cache is not under `$HOME` (`CLAUDE_CONFIG_DIR`,
  `CODEX_HOME`).

## 1.2.1 — 2026-09-02

### Fixed

- Codex now receives generated `agents/openai.yaml` policy files for the ten skills whose Claude
  source frontmatter disables model invocation. Those skills remain explicitly invocable, but are
  no longer selected implicitly by either harness.
- Generated Codex roles preserve full `agents-core:<skill>` ids when translating references from
  Claude plugin-root paths, so role delegation can resolve the intended skill.
- `at` discovers installed plugins and the optional `agents-tasks` seed independently across Claude
  and Codex caches. Mixed installations, semantic version ordering, live-versus-stale cache display,
  and current Codex local/Git marketplace update flows are handled explicitly.
- `at doctor` keeps its repository-only default and adds strict `--claude`, `--codex`, and `--all`
  checks; `at seed-path` exposes the installed seed used to adopt routing updates.

### Changed

- Agent-facing documentation consistently uses full `plugin:skill` ids and documents the distinct
  Claude `/plugin:skill` and Codex `$plugin:skill` invocation forms, Codex hook trust, and `jq`.
- CI and releases run a hermetic Codex compatibility smoke covering plugin installation, all 71
  skills, ten invocation policies, six roles, hooks, updates, task capture, and ledger validation.
  CI tests the minimum supported Codex `0.147.0` and current Codex `0.152.1`; ordinary local checks
  still skip the live smoke when Codex is absent.
- Claude manifests, source hook declarations, slash invocation, and update behavior remain intact;
  the generated Codex additions are derived from the same existing sources.

## 1.2.0 — 2026-08-20

### Added

- `at update` — refresh the marketplace and update every plugin installed from it on this machine,
  with `--check` for a read-only report of what is installed and at which version. Plugins install
  per machine, and `at bootstrap` only ever *installed* them, so an existing machine had no update
  path short of running the harness commands by hand.
- `at doctor` reports routing-table drift: `AGENTS.md` is downstream-owned, so `at init` never
  touches it and skills added upstream stayed unrouted silently. Doctor now names the exact seed rows
  a repo is missing, and points at `/setup-project`.
- `setup-project` gains an adoption mode and `references/adopting-updates.md`: the steps for bringing
  a template update into a repo that already has a contract. Written as desired-state checks rather
  than a per-release changelog, so it works from any starting version and is safe to re-run.

## 1.1.0 — 2026-08-19

### Added

- `grilling` (agents-core): the reusable interview primitive — design tree, frontier, one round of
  numbered questions with recommended answers at a time. `grill-me` moves to agents-core and becomes
  a router over it; `write-a-prd`, `github-triage`, `planning-workflow`, `spec-workflow` and
  `task-spec-workflow` now invoke it instead of restating the technique.
- `domain-modeling` (agents-extras): the glossary/ADR half of `grill-with-docs`, now model-invoked so
  any skill can reach it. `grill-with-docs` becomes a router over `grilling` + `domain-modeling`.
- `wayfinder` (agents-tasks): charts an effort too big for one session as a map — one task file
  holding decision tickets as dotted sub-ids (`T-042.1`) — and resolves them one per session.
- `research` and `wait-what` (agents-core), `to-questionnaire` (agents-extras).
- `writing-for-agents` (agents-extras): how to write anything an agent reads — context pointers, the
  two loads, progressive disclosure, completion criteria, leading words, pruning. `write-a-skill`
  drops the prose advice it duplicated and keeps the marketplace mechanics.
- `codebase-design` (agents-core, + references/deepening.md): one home for the module / interface /
  adapter / depth / seam / leverage / locality vocabulary, the deep-vs-shallow model, the deletion
  test, the dependency categories and the replace-don't-layer testing rule. Six skills used these
  words; three defined "deep module" differently. `tdd/references/deep-modules.md` and
  `interface-design.md` are absorbed into it.

### Fixed

- **`diagnose` referenced a minimised repro that no phase produced.** Phase 2 is now
  "Reproduce + minimise" and produces it. Phase 1 gained a real completion criterion (one command,
  already run, red-capable / deterministic / fast / agent-runnable) in place of "a loop you believe
  in", plus a `## Redact` section and a bundled `scripts/hitl-loop.template.sh`.
- **`github-triage` poisoned its own dedup store.** An enhancement closed as `wontfix` because it is
  *already implemented* is no longer written to `.out-of-scope/`, which is read back as the record of
  prior *rejections*. Triage also gained a redundancy check and an AI disclaimer on posted comments.

### Changed

- `todo-convention.md` documents the optional `## Tickets` section used by wayfinder maps, and the
  two layout rules that keep ticket state from leaking into task state.
- `vertical-slicing.md` gains the wide-refactor exception (expand → migrate → contract), reaching
  `prd-to-plan`, `prd-to-issues` and `prd-to-todos` from one file.
- `ubiquitous-language` now writes into `docs/resources/CONTEXT.md` using `domain-modeling`'s format
  instead of maintaining a competing root `UBIQUITOUS_LANGUAGE.md`; it keeps its distinct
  retrospective/batch trigger. Downstream repos with an existing `UBIQUITOUS_LANGUAGE.md` should fold
  it into the glossary.
- `tdd` confirms the seams tests are written at and names the tautological-test anti-pattern;
  `handoff` redacts secrets and personal data; `improve-codebase-architecture` scopes its search by
  git-log hot spots and screens with the deletion test.
- Skills adapted from `mattpocock/skills` now name that provenance in `metadata.source`.

### Known follow-ups

- `prototype` predates upstream's redesign (logic prototypes as one shareable HTML file; a prototype
  kept on a throwaway branch rather than deleted).
- `github-triage` does not treat external PRs as a request surface.
- No lint enforces the `AGENTS.md` skill rules (name/description/line limits, README skill counts);
  today they hold, but only by hand.

## 1.0.1 — 2026-08-19

Fixes found by actually migrating nine real downstream repositories with `at migrate`,
plus the rollout itself.

### Fixed

- `at migrate --allow-untracked` could delete untracked files that lived *inside* a tree
  it removes (a wholly-untracked ancestor directory, e.g. `?? .claude/`, hid a removal
  target such as `.claude/hooks/` from the leak guard). Containment is now checked in
  both directions.
- `at migrate --commit` used `git add -A` internally in one path, which could sweep
  untracked content into the migration commit; it now stages only the exact paths it
  touched (`git add -u` plus explicit adds), force-added so a downstream's own
  `.gitignore` can't cause a silent partial commit, and rolls back cleanly if the leak
  guard trips.
- `at migrate` on a repo whose untracked path collides with a file the plugin itself
  manages (e.g. a hand-edited untracked `.codex/agents/*.toml`) now **adopts** it
  (backs the old content up to `.no-commit/pre-migration/`, then proceeds) instead of
  silently overwriting it or refusing after the tree was already rewritten.
- `at bootstrap --clean-global-skills` only flagged a global skill symlink as stale if
  its target repo *still had* `_base/`/`playbooks/`. Once a repo is migrated those
  directories are gone, so the symlink is genuinely dangling but was invisible to the
  old check — it now flags any symlink whose target no longer exists, in addition to
  the pre-migration case.
- `scripts/release.sh` rolled its version bump back with `git checkout -- .`, which
  restores the worktree but not the index; a commit failure after `git add -A` could
  leave the bump staged. Rollback now restores both.

### Rollout

Migrated to the plugin layout: `project_r1_redmesh`, `project_r1_edge_node`,
`project_r1_infra`, `bootstrap_work`, `models_playground`, `project_fl_godfather`,
`project_technical_writing` (its downstream-authored `google-docs-refine` skill was
adopted into `agents-personal` first, then dropped from the downstream copy).
`learning_project_vi` was found not to be a consumer of this template (its `template`
remote points elsewhere). `ubuntu-setup` has real in-progress uncommitted work and was
left untouched pending the owner's own commit/stash. Every migration created a
`backup/pre-plugin-migration-<timestamp>` branch before changing anything.

## 1.0.0 — 2026-08-18

The repository stops being a git-merged monolith and becomes a **plugin marketplace plus a
thin seed**. Design: [`docs/specs/2026-08-18-plugin-restructure-design.md`](docs/specs/2026-08-18-plugin-restructure-design.md).
Upgrading an existing downstream: [`docs/migration.md`](docs/migration.md).

### Added

- **Marketplace `agents-template`** with four plugins under `plugins/`: `agents-core`
  (16 skills, 5 hooks, 6 subagent roles, the `at` CLI), `agents-tasks` (22), `agents-extras`
  (17), `agents-personal` (8). Installable natively by Claude Code
  (`.claude-plugin/marketplace.json`) and Codex (`.agents/plugins/marketplace.json`).
- **`at` CLI** (`agents-core`, bash + python3 stdlib): `bootstrap`, `init`, `migrate`,
  `doctor`, `version`, `ledger sync|check|rotate-log`, `reserve`, `repos-check`.
- **Seed** (`plugins/*/seed/`): the ~8 files a downstream owns — `AGENTS.md` (≤ 200-line
  contract with a routing table), `CLAUDE.md`, `.claude/settings.json`, managed `.gitignore`
  and `.gitattributes` blocks, Codex agent mirrors, and optional `docs/tasks_manager/`,
  artifacts, workbooks and repo-registry skeletons. Written once by `at init`, never merged.
- **Codex parity**: generated `.codex-plugin/plugin.json`, `hooks/hooks.codex.json` and
  `codex/agents/*.toml`; the sensitive-write hook now also understands `apply_patch`.
- **Tooling**: `scripts/build.py` (regenerates every derived file, `--check` in CI),
  `scripts/release.sh`, `scripts/install-pre-commit.sh`, `scripts/tests/run-all.sh` (hook,
  ledger, CLI and release tests), `.github/workflows/check.yml`.

### Changed

- Playbooks became **skills** that follow the Agent Skills spec: one `SKILL.md` (≤ 500
  lines) with `references/`, `assets/` and `scripts/` beside it; no wrapper-to-playbook hop;
  harness-neutral descriptions.
- Task ledger slimmed: fewer required fields, optional roadmap horizons, execution logs
  offloadable to `docs/tasks_manager/_logs/` via `at ledger rotate-log`.
- Third-party plugins (superpowers, github) are no longer vendored — install them from
  their own marketplaces.

### Removed

- The vendored template trees and their machinery: `_base/`, `playbooks/`, the three
  generated skill trees (`skills/`, `.claude/skills/`, `.agents/skills/`), the root plugin
  manifest, `.claude/hooks/`, `.claude/agents/`, `.codex/`, `.agents/skill-library.json`,
  `.agents/skills.enabled.json`, `scripts/convert_playbook.py`, and the `.gitattributes`
  merge-driver block. Updates now arrive through the plugin manager, not a `template` remote.
- Dedicated Antigravity/Gemini support (those harnesses read `.agents/skills` anyway).

### Verified

- End-to-end on Claude Code 2.1.234 and Codex CLI 0.147.0: `at bootstrap --local . --claude
  --codex --tasks --extras` installed all three plugins on the first try in both harnesses;
  `at init --all` + `at doctor` passed in a scratch repo; Claude Code's `block-dangerous-git.sh`
  hook blocked `git push --force` and both harnesses' agents saw `AGENTS.md` and the
  `agents-core` skills (`agents-core:tdd`, `$tdd`/`agents-core:execute-plan`). Details and
  token-cost numbers in `docs/meta/RESEARCH_SNAPSHOT.md` "Verification 2026-08-18".

Earlier history: `_base/CHANGELOG.md` before commit `a90cf0d` in git history.
