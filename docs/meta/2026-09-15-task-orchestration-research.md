# Task orchestration with per-phase subagent threads: research snapshot

Researched on: 2026-09-15. Scope: how `agents-template` (this repo) should execute a tracked task
(`docs/tasks_manager/_todos/<TASK>.md` with phases and acceptance criteria) so that each phase and each
review runs in its own agent thread, the orchestrator keeps only conclusions in context, and a fresh
session can resume from disk. Every non-local claim below links to a page fetched during this research;
where only secondary sources or no source exist, it says so.

## Question

When one agent thread executes a multi-phase task end-to-end, its context explodes. What native
mechanisms (Claude Code, Codex) and community designs (superpowers, GSD, Spec Kit, OpenSpec, Kiro,
Anthropic engineering guidance) exist for a thin orchestrator that dispatches each phase to a fresh
implementer thread and each review (spec compliance, code quality, security) to a separate thread, and
what concrete design should this repo adopt, including the Codex fallback?

## Short answer

1. The cause is local and specific: `plugins/agents-core/skills/execute-plan/SKILL.md` step 5 runs
   every phase inline in the main thread; subagents appear only in step 4 (architect review) and step 7
   (final two-reviewer loop). Every source below agrees on the remedy: **orchestrator never touches
   source files; one fresh implementer per slice; reviews as separate fresh threads; artifacts handed
   over as files; only short verdicts return to the parent** (Anthropic context engineering: subagents
   return "a condensed, distilled summary ... often 1,000-2,000 tokens"; GSD Core: "The orchestrator ...
   never touches source files"; superpowers SDD: "Hand artifacts over as files").
2. Claude Code has the primitives: subagents start with "a fresh, isolated context window", "only its
   final message returns to the parent", each completed subagent returns an **agent ID** that can be
   resumed with `SendMessage` (transcripts persist at
   `~/.claude/projects/{project}/{sessionId}/subagents/agent-{agentId}.jsonl` and survive main-thread
   compaction), plus `maxTurns`, `omitClaudeMd`, `isolation: worktree`, `skills` preload, and a
   `SubagentStop` hook that can block a subagent from finishing (exit 2). Agent teams are experimental,
   never spawn under `-p`, and are not restored by `/resume`. Dynamic workflows move the loop into a JS
   script whose "intermediate results stay in script variables", but allow "no mid-run user input", are
   resumable only in the same session, and a fresh session "starts the workflow over as a new run".
3. Codex enables subagents by default (`[agents]` config, custom agents as TOML in `.codex/agents/`,
   which `scripts/build.py` already generates from `plugins/agents-core/agents/*.md`), returns
   "summaries from subagents instead of raw intermediate output", and exposes `SubagentStart` /
   `SubagentStop` hooks. It does not document nesting or resuming a subagent by ID, and "in
   non-interactive flows ... an action that needs new approval fails and Codex surfaces the error back
   to the parent workflow". `codex exec resume --last`, `--output-schema`, `-o` provide a sequential
   scripted fallback.
4. The community designs differ mainly in where state lives: superpowers keeps a plain-text ledger
   (`progress.md`) plus per-task brief/report/diff files under `.superpowers/sdd/<plan>/`; GSD Core
   keeps `.planning/STATE.md` (YAML frontmatter + body, lockfile-guarded) and per-plan `SUMMARY.md`,
   plus `continue-here.md` for pause/resume; Spec Kit, Kiro and OpenSpec execute tasks inline and
   track progress only with checkboxes in `tasks.md`.
5. For this repo: keep `agents-core:execute-plan` as the entry point; make step 5 a dispatch loop;
   add `docs/tasks_manager/_runs/<TASK-ID>/{state.md, phase-N/…}` as the resume map; add a stdlib
   `at task brief` extractor; split review into parallel `reviewer` (spec stage) + `reviewer`
   (quality stage) + conditional `security-auditor`; cap the fix loop at three rounds with rulings;
   orchestrator commits; execution-log entries become ≤ 10-line pointers into the run directory; Codex
   uses the same flow with fresh re-dispatch instead of resume, and `codex exec` / inline as tiers
   below that.

## Findings per source

### 1. Claude Code native mechanisms

**Subagents** — https://code.claude.com/docs/en/sub-agents

- Isolation: "Each subagent starts with a fresh, isolated context window. It doesn't see your
  conversation history, the skills you've already invoked, or the files Claude has already read." A
  non-fork subagent's initial context is: its own system prompt (not the Claude Code system prompt),
  the delegation prompt, **every level of the CLAUDE.md hierarchy** (unless `omitClaudeMd: true`), a
  git-status snapshot, preloaded `skills`, and a sibling roster.
- What returns: only the final message; the SDK page: "intermediate tool calls and results stay
  inside the subagent; only its final message returns to the parent"
  (https://code.claude.com/docs/en/agent-sdk/subagents).
- Frontmatter fields relevant here: `tools`, `disallowedTools`, `model`, `permissionMode`, `maxTurns`
  ("marks the returned output as partial" at the limit), `skills`, `hooks`, `memory`, `background`,
  `omitClaudeMd`, `effort`, `isolation: worktree` ("automatically cleaned up if the subagent makes no
  changes"; Bash is fenced to the worktree).
- Resume: "When a subagent completes, Claude receives its agent ID" and "Claude uses the `SendMessage`
  tool with the agent's ID or name as the `to` field to resume it. `SendMessage` doesn't require agent
  teams to be enabled". "Resumed subagents retain their full conversation history" and "can keep
  reading the prompt cache the original run warmed". Transcripts live at
  `~/.claude/projects/{project}/{sessionId}/subagents/agent-{agentId}.jsonl`; "when the main
  conversation compacts, subagent transcripts are unaffected"; "You can resume a subagent after
  restarting Claude Code by resuming the same session"; deleted after `cleanupPeriodDays` (30 days).
  Built-in Explore/Plan are one-shot and return no ID.
- Auto-compaction applies inside subagents with the same logic as the main conversation.
- Background is the default in interactive sessions (fork mode on); background subagents keep only
  `Read, Grep, Glob, Bash, PowerShell, Edit, Write, NotebookEdit, WebFetch, WebSearch, TodoWrite,
  Skill, ToolSearch, EnterWorktree, ExitWorktree, Monitor, TaskStop, SendMessage, Artifact`; Claude
  runs one "in the foreground when it needs the result before continuing".
- Nesting: default depth 3 (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`); "To keep one subagent from
  spawning ... omit `Agent` from its `tools` list". Concurrency: 20 (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`).
- Failure: a foreground subagent cut off by an API error returns partial output "with a note that the
  subagent was cut off"; background ones are "marked failed" with last output preserved. Output
  scanning neutralises instruction-shaped text in reports (v2.1.210+).
- Cost: "keep [descriptions] short"; warning when combined descriptions exceed 15,000 tokens.

**Skills that run in a subagent** — https://code.claude.com/docs/en/skills

- `context: fork` + `agent: <name>`: "Claude Code starts a new subagent of the type set in the `agent`
  field and gives it the skill content as its prompt." Forked skills run in the background by default;
  `background: false` waits in the same turn and keeps the full tool set. `$ARGUMENTS`, `$0`, `$name`
  placeholders are available. `disable-model-invocation: true` "also prevents the skill from being
  preloaded into subagents".

**Hooks** — https://code.claude.com/docs/en/hooks

- `SubagentStart` (matcher = agent type; input carries `agent_id`, `agent_type`) and `SubagentStop`
  ("Fires when a subagent finishes"; "Can prevent the subagent from stopping (exit 2)"; input includes
  `last_assistant_message`). Tool hooks fired by a subagent carry `agent_id`/`agent_type`.
- `PreCompact` (matcher `manual|auto`, can block), `PostCompact`, `Stop`, `TaskCompleted` /
  `TeammateIdle` (agent teams). This repo's `plugins/agents-core/hooks/hooks.json` has only
  `PreToolUse`/`PostToolUse` entries today.

**Agent teams** — https://code.claude.com/docs/en/agent-teams

- "experimental and disabled by default" (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`); "Spawning
  teammates also requires an interactive session. In non-interactive mode with the `-p` flag ... Claude
  doesn't spawn teammates"; "No session resumption with in-process teammates: `/resume` and `/rewind`
  do not restore in-process teammates"; "No nested teams"; teammates "use significantly more tokens".
  Comparison table: subagents "Own context window; results return to the caller", token cost "Lower:
  results summarized back to main context". Side effect: with teams enabled, "a subagent that Claude
  names launches as a teammate".

**Dynamic workflows** — https://code.claude.com/docs/en/workflows

- "A dynamic workflow is a JavaScript script that orchestrates many subagents at once ... a runtime
  executes it in the background". Primitives: `agent()` (optionally with `schema` for JSON output,
  five validation retries), `pipeline()`, `parallel()`, `phase()`, `log()`, `args` global.
  "Intermediate results stay in script variables instead of landing in Claude's context."
- Constraints: "No mid-run user input ... For sign-off between stages, run each stage as its own
  workflow"; "No direct filesystem or shell access from the workflow itself"; no `import()`; up to 16
  concurrent agents; `Date.now()`/`Math.random()` throw so a relaunch replays the same calls.
- Resume: "You can resume a run within the same Claude Code session"; completed agents "return [their]
  saved result", failed ones and everything after them rerun; after exit, a `claude --resume` session
  can relaunch, but "In a session you start fresh, Claude has no earlier run to relaunch and starts the
  workflow over as a new run".
- Distribution: saved scripts in `.claude/workflows/` or a plugin `workflows/` directory, namespaced
  `/plugin:name`. `Workflow` can be allow-listed for `-p`/SDK runs.
- Positioning (https://code.claude.com/docs/en/agents): subagents for "a side task [that] would flood
  your main conversation"; workflows for "a job [that] outgrows a handful of subagents".

**Headless / SDK** — https://code.claude.com/docs/en/headless,
https://code.claude.com/docs/en/agent-sdk/subagents

- `claude -p` with `--output-format json` (includes `session_id`, `total_cost_usd`), `--json-schema`
  (result in `structured_output`), `--resume <session_id>` or `--continue`, `--bare` ("recommended mode
  for scripted and SDK calls"), `--agents <json>`, `--append-system-prompt-file`. "If Claude starts a
  background subagent or workflow, `claude -p` instead stays open until that work completes."
  Subagent messages carry `parent_tool_use_id` in `stream-json`.
- SDK: the parent "receives the subagent's final message as the Agent tool result"; resume needs both
  `resume: sessionId` and the `agentId` parsed from the tool result; caps via
  `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`, `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`, `maxBudgetUsd`.

**Context/cost guidance** — https://code.claude.com/docs/en/costs

- "Delegate these to subagents so the verbose output stays in the subagent's context while only a
  summary returns"; `/compact <instructions>` and a `# Compact instructions` block in CLAUDE.md steer
  what compaction preserves; keep CLAUDE.md under ~200 lines.

### 2. Codex

**Subagents** — https://learn.chatgpt.com/docs/agent-configuration/subagents (redirect target of
https://developers.openai.com/codex/multi-agent)

- "Current Codex releases enable subagent workflows by default." Config under `[agents]`:
  `enabled`, `max_concurrent_threads_per_session`, `default_subagent_model`,
  `default_subagent_reasoning_effort`, `interrupt_message`.
- "Current local Codex releases spawn agents after a direct request or applicable project or skill
  instruction." Custom agents are "standalone TOML files under `~/.codex/agents/`" or `.codex/agents/`
  with required `name`, `description`, `developer_instructions` and optional session keys (`model`,
  `model_reasoning_effort`, `sandbox_mode`, `mcp_servers`, `skills.config`). This repo already
  generates `plugins/agents-core/codex/agents/*.toml` from `agents/*.md`.
- What the parent sees: "Return summaries from subagents instead of raw intermediate output"; "The
  main thread collects the subagent results into its final response"; subagents "inherit your current
  sandbox policy".
- Failure/approvals: "In non-interactive flows, or whenever a run can't surface a fresh approval, an
  action that needs new approval fails and Codex surfaces the error back to the parent workflow."
- Not documented (treat as unsupported): nesting depth, resuming a finished subagent by ID, a
  `maxTurns` equivalent, worktree isolation per agent. Guidance: "Be more careful with parallel
  write-heavy workflows, because agents editing code at once can create conflicts."

**Hooks** — https://learn.chatgpt.com/docs/hooks

- Events include `SessionStart/SessionEnd`, `PreToolUse/PostToolUse`, `PermissionRequest`,
  `PreCompact/PostCompact`, `UserPromptSubmit`, `Stop`, `Interrupt`, and **`SubagentStart` /
  `SubagentStop`**. Files: `~/.codex/hooks.json`, `<repo>/.codex/hooks.json`, or inline `[hooks]` in
  `config.toml`. "Before a non-managed hook can run, Codex requires you to review and trust the exact
  hook definition." `SessionEnd` "won't run for subagents". This repo's `hooks.codex.json` is generated
  from `hooks.json`, so a `SubagentStop` entry would need the generator to know the event.

**`codex exec`** — https://learn.chatgpt.com/docs/non-interactive-mode,
https://learn.chatgpt.com/docs/developer-commands?surface=cli

- `codex exec "<task>"` streams progress to stderr and prints the final message to stdout; `codex exec
  -` reads the whole prompt from stdin; `--json` emits JSONL events (`thread.started`, `turn.completed`,
  `item.completed`, `error`); `-o/--output-last-message <path>`; `--output-schema <schema.json>`;
  `--sandbox read-only|workspace-write|danger-full-access` (`--full-auto` deprecated); `-C/--cd`;
  `-m/--model`; `-c` config overrides; `--ephemeral`; `codex exec resume --last | <SESSION_ID>`.
- Secondary/unverified: search-result snippets of https://github.com/openai/codex/issues/22998 and
  https://github.com/openai/codex/issues/14343 state that `codex exec resume` does not accept
  `--output-schema`. The issue pages themselves were not fetched.

### 3. superpowers (obra/superpowers)

**subagent-driven-development** —
https://raw.githubusercontent.com/obra/superpowers/main/skills/subagent-driven-development/SKILL.md
(plus `implementer-prompt.md`, `task-reviewer-prompt.md`, `re-review-prompt.md`,
`scripts/{sdd-workspace,task-brief,review-package}` in the same directory)

- Principle: "Fresh subagent per task + task review (spec + quality) + broad final review = high
  quality, fast iteration." The controller does not pause between tasks except for irreversible
  operations, security-sensitive actions, side effects outside the worktree, or a broken plan.
- Per-task flow: record BASE commit → `scripts/task-brief PLAN_FILE N` (extracts the `Task N` heading
  into `<repo>/.superpowers/sdd/<plan-basename>/task-N-brief.md`) → dispatch implementer → handle
  `DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED` → `scripts/review-package PLAN_FILE BASE HEAD`
  (writes a diff file) → dispatch **one** task reviewer → fix loop → append to ledger.
- The implementer dispatch contains exactly: one line of project context; the brief path ("read this
  first — it is your requirements"); interfaces and decisions from earlier tasks; resolutions of
  ambiguities; the report-file path and report contract. "Never: full plan file, accumulated
  prior-task summaries, or subagent context." The implementer "never dispatches subagents — not
  helpers, and never a reviewer"; its chat reply is ≤ 15 lines and the full report goes to a file.
- Review: a single task reviewer receives brief path, report path, diff-package path, and global
  constraints; must return **both** a spec-compliance verdict and a quality verdict; may flag
  "Cannot verify from diff"; treats implementer claims as unverified; runs focused tests only on
  specific doubt. Re-review is scoped to the findings list and fix diff (`re-review-prompt.md`).
- Fix loop: max 5 rounds; rounds 1–3 resume the original implementer with findings verbatim; rounds
  4–5 dispatch a fresh implementer on a more capable model ("A prior implementer attempted this task
  [N] times; you own it now"); at the cap the controller adjudicates each finding (park with ruling /
  rule on the smallest fix) and stops "only when the defect leaves every path forward a guess".
- Ledger: `<workspace>/progress.md`, first line `# SDD ledger — plan: <path>`, line formats
  `Task <N>: complete (commits <base7>..<head7>, review clean)`, `Task <N>: fix round <R>/5 (...)`,
  `Ruling: <what decided> — <why> — <what costs if wrong>`, `Task <N>: parked — ...`. Written after
  every task, every fix round, and every adjudication; it is "the recovery map" after compaction.
- Final review: one whole-branch review on the most capable model, one fix subagent, one scoped
  re-review, "No second fix wave".

**executing-plans** — https://raw.githubusercontent.com/obra/superpowers/main/skills/executing-plans/SKILL.md:
the inline alternative ("Stop when blocked, don't guess"). **dispatching-parallel-agents** —
https://raw.githubusercontent.com/obra/superpowers/main/skills/dispatching-parallel-agents/SKILL.md:
"Dispatch one agent per independent problem domain"; prompts focused, self-contained, specific about
output. **writing-plans** —
https://raw.githubusercontent.com/obra/superpowers/main/skills/writing-plans/SKILL.md: tasks of 2–5
minutes with exact paths, then offer "Subagent-Driven" vs "Inline Execution".

### 4. GSD Core (successor of gsd-build/get-shit-done)

https://github.com/gsd-build/get-shit-done is "archived on June 26, 2026"; development continues at
https://github.com/open-gsd/gsd-core. Docs fetched:
https://raw.githubusercontent.com/open-gsd/gsd-core/next/docs/explanation/context-engineering.md and
https://raw.githubusercontent.com/open-gsd/gsd-core/next/docs/ARCHITECTURE.md.

- "The orchestrator — your main session — never touches source files." "Because it does very little
  itself, its context window grows slowly and predictably." Heavy work runs in "fresh-context
  subagents" with "a 200k-token clean window".
- Phase loop: Discuss → Plan → Execute ("run plans in parallel waves; each executor starts with a
  clean 200k-token context") → Verify → Ship. Executors receive "a compact JSON context payload
  (project summary, phase goal, relevant config)" plus the plan; per-plan commits are atomic; a
  `SUMMARY.md` is written per plan; a verifier runs after all waves.
- State: `.planning/` with `PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md` ("Living memory:
  position, decisions, blockers, metrics"; YAML frontmatter + Markdown body; "lockfile-based mutual
  exclusion"), `config.json`, and per phase `XX-CONTEXT.md`, `XX-RESEARCH.md`, `XX-YY-PLAN.md`,
  `XX-YY-SUMMARY.md`, `XX-VERIFICATION.md`. Pause writes `continue-here.md`; resume reads it.
- Multi-runtime: a ~10,700-line installer transforms one source into Claude Code (native), Codex
  ("Agent TOML per role"), OpenCode, Gemini, Copilot, Cursor and others. Same shape as this repo's
  `build.py`, at much larger scale.

### 5. Spec Kit, OpenSpec, Kiro

- **Spec Kit `/speckit.implement`** —
  https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/implement.md: inline,
  "Phase-by-phase execution: Complete each phase before moving to the next"; `[P]` marks parallel
  tasks; "mark the task off as [X] in the tasks file"; "Halt execution if any non-parallel task fails.
  For parallel tasks [P], continue with successful tasks, report failed ones"; no commits mandated,
  no subagent dispatch.
- **Kiro** — https://kiro.dev/docs/guides/learn-by-playing/05-using-specs-for-complex-work/ and
  https://kiro.dev/blog/understanding-kiro-pricing-specs-vibes-usage-tracking/: "click the 'Start
  Task' link above the task"; "Starting a task directly from your tasks.md file will be 1 spec
  request". No context isolation or subagent mechanics documented on the pages fetched.
- **OpenSpec** — https://github.com/Fission-AI/OpenSpec/blob/main/docs/getting-started.md:
  `/opsx:apply` works through `tasks.md` checkboxes sequentially; `/opsx:continue` exists; execution
  architecture is not documented.

Conclusion: these solve derivation and tracking, not orchestrator context. The only reusable idea is
the checkbox-in-file progress marker, which this repo already has.

### 6. Anthropic engineering guidance

- **How we built our multi-agent research system** —
  https://www.anthropic.com/engineering/multi-agent-research-system: orchestrator-worker; subagents act
  as "intelligent filters"; delegation needs "an objective, an output format, guidance on the tools
  and sources to use, and clear task boundaries"; the lead saves its plan to memory because "if the
  context window exceeds 200,000 tokens it will be truncated"; multi-agent "use[s] about 15× more
  tokens than chats"; systems should "resume from where the agent was when the errors occurred".
- **Effective context engineering for AI agents** —
  https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents: "context rot";
  compaction; "structured note-taking" persisted outside the window; just-in-time retrieval via
  "lightweight identifiers (file paths ...)"; sub-agents return "only a condensed, distilled summary
  of its work (often 1,000-2,000 tokens)".
- **Building effective agents** —
  https://www.anthropic.com/engineering/building-effective-agents: prompt chaining with programmatic
  gates; orchestrator-workers "where you can't predict the subtasks needed"; evaluator-optimizer "when
  we have clear evaluation criteria"; keep it simple.

### 7. What already exists in this repo

- `plugins/agents-core/skills/execute-plan/SKILL.md` (310 lines): step 4 dispatches `plan-critic`;
  step 5 (lines 187–225) implements each phase inline; step 7 (lines 240–287) dispatches two
  `reviewer` subagents for up to three rounds. Codex fallback is "documented main-thread review labeled
  not independent". Inline step 5 is the context sink.
- `plugins/agents-core/skills/subagent-protocol/SKILL.md`: status vocabulary (`DONE |
  DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED`), report block, six-part briefing format, two-stage
  review order (spec before quality), model-class table, "Never re-dispatch with an identical prompt",
  recursive mitigation. Reusable as-is.
- `.../subagent-protocol/references/agent-loop-recipes.md`: memory section already names task
  execution log, `AGENT_PROGRESS.md`, `docs/resources/_reports/` as loop state; worktree guidance.
  `.../references/prompt-orchestration.md`: decision tree — "Add subagents only when ownership and
  review boundaries are explicit".
- `plugins/agents-core/agents/implementer.md` (model `sonnet`, tools Read/Edit/Write/Bash/Glob/Grep —
  no `Agent`, so nesting is already blocked), `reviewer.md` (two-stage, read-only),
  `spec-validator.md` (spec-blind, writes `tests/spec_validation/`), `security-auditor.md`,
  `plan-critic.md`, `researcher.md`; Codex TOML twins are generated into
  `plugins/agents-core/codex/agents/`.
- `plugins/agents-tasks/skills/task-ledger/SKILL.md` and `references/todo-convention.md`:
  `#### Phase N:` headings with checklists, `### Acceptance criteria`, `### Related tests`, append-only
  `## Execution log`, `Last executed`, `at ledger check`, `at ledger rotate-log <TASK-ID>` →
  `docs/tasks_manager/_logs/<TASK-ID>.md` when the log exceeds 200 lines; pre-implementation gate
  (researcher + spec resolution + plan-critic).
- `plugins/agents-core/skills/handoff/SKILL.md`: "Reference, don't duplicate" — the principle the run
  state file should follow.
- `plugins/agents-core/lib/at.py` (2,123 lines, stdlib): `cmd_ledger`, `cmd_reserve`,
  `_ledger_findings` — natural home for a `task brief` / `task run-state` subcommand.

## Comparison

| Approach | Orchestrator context bound | Per-phase isolation | Separate review threads | State persistence | Resumability | Codex parity |
|---|---|---|---|---|---|---|
| Current `execute-plan` step 5 (inline) | none — all diffs/tests in one thread | no | only final 2×`reviewer` | task execution log | re-read task file | full (same inline flow) |
| Claude Code subagents driven by a skill | yes — only final messages return; enforce short reports | yes, fresh window per dispatch | yes, parallel read-only subagents | whatever the skill writes to disk (+ subagent transcripts in `~/.claude`) | disk state + `SendMessage` resume within the same session | high — Codex subagents + generated TOML; no resume-by-ID |
| Claude Code dynamic workflows | strongest — results in script variables | yes | yes (`parallel()`) | run results under `~/.claude/projects/` | same session only; fresh session restarts | none |
| Claude Code agent teams | weak — lead receives idle notifications + messages | yes | yes | shared task list under `~/.claude/tasks/` | no (`/resume` does not restore teammates) | none |
| superpowers SDD | yes — brief/report/diff as files, ≤ 15-line replies | yes | one combined spec+quality reviewer, scoped re-review | `progress.md` ledger + per-task files | yes (ledger is the "recovery map") | not addressed |
| GSD Core | yes — orchestrator never edits files | yes (wave executors) | verifier after waves | `.planning/STATE.md`, `SUMMARY.md` | `continue-here.md` | installer generates Codex TOML agents |
| Spec Kit / Kiro / OpenSpec | no (inline) | no | no | `tasks.md` checkboxes | checkboxes | n/a (harness-neutral prompts) |
| `codex exec` / `claude -p` script driver | total — no LLM orchestrator | yes (one process per phase/review) | yes | whatever the script writes | yes (`resume --last`, `--resume <id>`) | native on both |

## Recommendation for this repo

Design principle (Anthropic context engineering, superpowers, GSD): **the orchestrator reads the task
file, the run state file, and ≤ 20-line verdicts; everything else is a file path.** Keep
`agents-core:execute-plan` as the user-facing entry point (the seed `AGENTS.md` already routes
"Implement a tracked task" to it) and change how step 5 works rather than adding a competing skill.

### Orchestrator flow (replaces step 5; steps 1–4 and 6–8 stay)

```text
read task file + resolve specs (existing step 1)      -> write _runs/<TASK-ID>/state.md
for each phase N not yet `committed` in state.md:
  at task brief <TASK-ID> --phase N                    -> _runs/<TASK-ID>/phase-N/brief.md
  append rulings/interfaces from earlier phases to brief.md
  record BASE=`git rev-parse --short HEAD` in state.md
  dispatch implementer (fresh)                         -> phase-N/report.md, ≤15-line reply
  on NEEDS_CONTEXT/BLOCKED: answer or triage, re-dispatch (never identical prompt)
  git diff BASE..HEAD > phase-N/diff.patch  (pathspec = phase scope)
  dispatch in parallel: reviewer[stage=spec] -> phase-N/review-spec.md
                        reviewer[stage=quality] -> phase-N/review-quality.md
                        security-auditor (only if phase touches a security surface) -> phase-N/review-security.md
  fix loop (max 3 rounds):
    round 1-2: SendMessage to the same implementer with the open findings list verbatim
    round 3:   fresh implementer, stronger model ("a prior implementer attempted this N times")
    after each fix: scoped re-review of findings + fix diff only
  at cap: adjudicate each finding -> `Ruling:` line in state.md, or stop BLOCKED
  orchestrator commits (pathspec-staged), records SHA in state.md
  append ≤10-line execution-log entry to the task file (pointer to phase-N/), tick phase checkboxes
  at ledger check
final validation (existing step 6) -> optional spec-validator run over ALL acceptance criteria
final whole-task review (existing step 7, now one round + one fix + one re-review)
```

### On-disk state: `docs/tasks_manager/_runs/<TASK-ID>/`

```text
_runs/<TASK-ID>/
  state.md            # resume map, ≤ 60 lines, rewritten by the orchestrator only
  phase-1/brief.md    # self-contained requirements for the implementer
  phase-1/report.md   # implementer's full report (chat reply is ≤ 15 lines)
  phase-1/diff.patch  # review package
  phase-1/review-spec.md, review-quality.md, review-security.md, re-review-R.md
  phase-2/...
```

`state.md` shape (GSD frontmatter + superpowers ledger lines):

```markdown
---
task: EGM-012
base_rev: a1b2c3d
branch: master
work_mode: default-branch
autonomy: L1
current_phase: 2
updated: 2026-09-15T14:02:00
---
# Run ledger — task: docs/tasks_manager/_todos/EGM-012-F_example.md

| Phase | Status | Attempt | Spec | Quality | Security | Open | Commit | Agent |
|---|---|---|---|---|---|---|---|---|
| 1 | committed | 1 | PASS | PASS | n/a | 0 | 9f8e7d6 | agent-… |
| 2 | fixing | 2 | FAIL | PASS | PASS | 1 | — | agent-… |

Phase 1: complete (commits a1b2c3d..9f8e7d6, review clean)
Phase 2: fix round 1/3 (2 addressed, 1 open — validator ignores empty payload; commits 9f8e7d6..c0ffee1)
Ruling: keep token parsing in helper — avoids wider refactor — cost if wrong: duplicate parsing in phase 3
Interface: SessionValidator.validate(token) -> Result[Session, SessionError]  (phase 1, for later phases)
```

Status values: `pending | implementing | reviewing | fixing | committed | blocked | parked`. A fresh
session resumes by reading `state.md`, verifying each recorded commit with `git cat-file -e`, and
continuing at the first phase not `committed`. Agent IDs are an accelerator only (valid inside the same
Claude session via `claude --resume`); the file is the source of truth.

### Brief construction (`at task brief <TASK-ID> --phase N`, stdlib, mirrors superpowers `task-brief`)

Extracts into `brief.md`: task title and one-paragraph brief; the `#### Phase N` heading and its
checklist; `### Acceptance criteria` items; `### Related tests`; task-local `### Specification` /
`### Design`; resolved `Spec refs` paths (paths, not contents); repo `Work mode`/`Autonomy` lines. The
orchestrator appends `Interface:` and `Ruling:` lines from `state.md`. The dispatch prompt itself is
~10 lines: one-line project context, brief path, report path, scope fence (files/dirs; "do not
commit"; "do not spawn subagents"), model hint, report contract. The implementer never receives the
whole task file, prior reports, or the conversation.

### Review verdict compression

Each reviewer writes its full report to its file and replies with only:

```text
## Status: DONE | DONE_WITH_CONCERNS | BLOCKED
## Verdict: PASS | FAIL
## Findings: <count> (C:<n> I:<n> M:<n>)
1. [C] path:line — one line
2. [I] path:line — one line
## Report: docs/tasks_manager/_runs/<TASK-ID>/phase-N/review-spec.md
```

The orchestrator records verdict + counts in `state.md` and passes the numbered findings list (not the
report) into the fix-round prompt. Optional enforcement: a `SubagentStop` hook (matcher
`implementer|reviewer|security-auditor|spec-validator`) that exits 2 when `last_assistant_message`
lacks `## Status:`; Codex has the same event, but `hooks.codex.json` generation must learn it first.

### Changes to existing files

- `execute-plan/SKILL.md`: rewrite step 5 as the dispatch loop above; move the inline variant to
  `references/inline-execution.md` (used when no subagent runtime exists); shorten step 7 to one
  whole-task round with one fix wave; add "resume from `_runs/<TASK-ID>/state.md`" to step 1.
- `subagent-protocol/SKILL.md`: add "artifacts as files, replies ≤ 15/20 lines" rule, the fix-loop
  policy (resume twice, then fresh stronger model, then adjudicate), and the `Ruling:` line format.
- `agents/implementer.md`: add "do not commit" and "write the full report to the path in your brief";
  keep the explicit `tools` list (no `Agent`) so nesting stays off; consider `maxTurns`.
- `agents/reviewer.md`: accept a `Stage: spec | quality | both` line in the brief so the same card runs
  as two parallel threads; keep read-only. `spec-validator.md` stays for the final whole-task
  acceptance pass (it writes tests; too heavy per phase).
- `task-ledger`: register `_runs/` in the directory structure; `at ledger check` warns on a run dir
  whose task is archived; `complete-task` archives or deletes the run dir.
- `hooks/hooks.json` (+ generator): optional `SubagentStop` contract check.
- `at.py`: `task brief`, `task run-state init|set` (small, stdlib).

### Codex fallback (three tiers, declared honestly in the log)

1. **Codex subagents (default-enabled)**: same skill flow; the generated `.codex/agents/*.toml` cards
   are the roles; the parent already receives summaries. Differences: no documented resume-by-ID, so
   every fix round is a fresh dispatch with the findings file; run with `--sandbox workspace-write` or
   approvals fail in non-interactive runs; keep parallel reviewers read-only (write-conflict warning).
2. **Scripted driver**: `at task run <TASK-ID>` (stdlib) loops phases with `codex exec -C <repo>
   --sandbox workspace-write --output-schema report.schema.json -o phase-N/report.json "$(cat
   brief.md)"` and the same for reviewers; the identical driver works with `claude -p --bare
   --output-format json --json-schema … --agents …`. No LLM orchestrator context at all; state file
   identical. Cost: no mid-run conversation with the user except script pauses.
3. **Inline** (current behaviour, `references/inline-execution.md`), labelled "not independent" in the
   execution log, as execute-plan already requires.

### Tradeoffs

- Pros: bounded orchestrator context; independent reviews; resumable from disk on both harnesses;
  reuses existing agents, status vocabulary, task ledger and `build.py`; no new runtime dependency.
- Cons: more total tokens, on both harnesses equally — every fresh thread re-loads the instruction
  hierarchy, the brief and the files the parent already saw (Anthropic measured research-style
  multi-agent fan-out at "about 15× more tokens than chats"; this sequential loop with 1 implementer +
  2–3 reviewers per phase should sit well below that, and tokens *per request* drop, which is what
  matters once the inline thread is near its limit); more wall time per phase (three reviewer threads); a new `_runs/` artifact to govern; every subagent still loads
  the CLAUDE.md hierarchy unless `omitClaudeMd` is set; Codex fix rounds lose the prompt-cache benefit
  of resume.
- Alternatives considered: dynamic workflow (`workflows/execute-task.js` in the plugin) — strongest
  context bound but no mid-run sign-off, no fresh-session resume, no Codex; agent teams — experimental
  and not resumable; per-phase `context: fork` skills — viable for single dispatches but the loop still
  needs an orchestrator holding state.

## Open questions

Decided on 2026-09-15 (implemented in the same day's commits): `_runs/` is committed except
`diff.patch`; `reviewer` per phase and `spec-validator` once at the end; `omitClaudeMd` left to
downstream reviewer overrides; the `SubagentStop` hook and the scripted `at task run` driver are
follow-ups; the fix-loop cap is 3; rulings surface in the task's completion summary.

- Commit `_runs/<TASK-ID>/` with phase commits (resumable across machines, noisy history) or gitignore
  it like `.worktrees/` and keep only `state.md` tracked?
- Spec compliance per phase: `reviewer` stage-spec (diff-based, cheap) or `spec-validator` (spec-blind
  tests, independent but heavier)? Recommendation: reviewer per phase, spec-validator once at the end.
- Should reviewers get `omitClaudeMd: true` (smaller context, but they lose downstream conventions)?
- Add the `SubagentStop` contract hook now, or after the loop has run on a few real tasks?
- Build the scripted driver (`at task run`) in this iteration, or only the skill flow?
- Fix-loop cap: stay at 3 (current execute-plan) or adopt superpowers' 5 with model escalation at 4?
- Where do rulings surface to the human at the end — `Completion summary` in the task file seems right; confirm.

## Known gaps in this research

- `codex exec resume` + `--output-schema` incompatibility rests on GitHub issue search snippets only.
- Codex subagent nesting and resume-by-ID are undocumented; treated as unsupported.
- Exact Codex tool names for spawning/waiting on agents, and whether `codex exec` spawns subagents,
  were not determinable from the fetched pages; needs a live `codex` run.
- Kiro/OpenSpec execution internals are not documented on the fetched pages.
- superpowers' `review-package` script was not fetched; assumed to produce a diff only.

## Sources

Local (read in full):

- `plugins/agents-core/skills/execute-plan/SKILL.md`
- `plugins/agents-core/skills/subagent-protocol/SKILL.md` and `references/{agent-loop-recipes,prompt-orchestration}.md`
- `plugins/agents-core/agents/{implementer,reviewer,spec-validator,security-auditor}.md`
- `plugins/agents-tasks/skills/task-ledger/SKILL.md` and `references/todo-convention.md`
- `plugins/agents-core/skills/handoff/SKILL.md` (lines 1–40)
- `plugins/agents-core/hooks/hooks.json`
- `plugins/agents-core/lib/at.py` (grep only)
- `docs/meta/2026-09-04-architecture-source-of-truth-research.md` (shape reference)

Primary (fetched):

- https://code.claude.com/docs/en/sub-agents — isolation, resume, transcripts, tools, hooks fields
- https://code.claude.com/docs/en/skills — `context: fork`, `agent`, `$ARGUMENTS`
- https://code.claude.com/docs/en/hooks — SubagentStart/Stop, PreCompact, Stop
- https://code.claude.com/docs/en/agent-teams — experimental, no `-p`, no resume
- https://code.claude.com/docs/en/workflows — agent/pipeline/parallel/phase, resume rules
- https://code.claude.com/docs/en/agents — comparison of the four approaches
- https://code.claude.com/docs/en/headless — `-p`, `--resume`, `--json-schema`, `--bare`, `--agents`
- https://code.claude.com/docs/en/agent-sdk/subagents — what returns, resume by agentId, caps
- https://code.claude.com/docs/en/costs — delegation, compact instructions
- https://learn.chatgpt.com/docs/agent-configuration/subagents — Codex subagents
- https://learn.chatgpt.com/docs/hooks — Codex hook events
- https://learn.chatgpt.com/docs/non-interactive-mode , https://learn.chatgpt.com/docs/developer-commands?surface=cli — `codex exec`
- https://raw.githubusercontent.com/obra/superpowers/main/skills/subagent-driven-development/SKILL.md and `implementer-prompt.md`, `task-reviewer-prompt.md`, `re-review-prompt.md`, `scripts/task-brief`
- https://raw.githubusercontent.com/obra/superpowers/main/skills/executing-plans/SKILL.md , `dispatching-parallel-agents/SKILL.md` , `writing-plans/SKILL.md`
- https://github.com/gsd-build/get-shit-done (archived notice), https://github.com/open-gsd/gsd-core , https://raw.githubusercontent.com/open-gsd/gsd-core/next/docs/explanation/context-engineering.md , https://raw.githubusercontent.com/open-gsd/gsd-core/next/docs/ARCHITECTURE.md
- https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/implement.md
- https://kiro.dev/docs/guides/learn-by-playing/05-using-specs-for-complex-work/ , https://kiro.dev/blog/understanding-kiro-pricing-specs-vibes-usage-tracking/
- https://github.com/Fission-AI/OpenSpec/blob/main/docs/getting-started.md
- https://www.anthropic.com/engineering/multi-agent-research-system
- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- https://www.anthropic.com/engineering/building-effective-agents

Secondary (search snippets only, not fetched):

- https://github.com/openai/codex/issues/22998 , https://github.com/openai/codex/issues/14343 — `codex exec resume` lacks `--output-schema`

Not found / 404: https://learn.chatgpt.com/docs/exec , https://learn.chatgpt.com/docs/noninteractive , https://learn.chatgpt.com/docs/agent-configuration/hooks , https://kiro.dev/docs/specs/tasks/ , https://raw.githubusercontent.com/openai/codex/main/docs/exec.md (stub only).
