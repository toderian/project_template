# Brief: supervisor-packs, phase 5

Plan: docs/specs/2026-11-26-supervisor-packs-plan.md (read "Where we are" and "Decided against" for context).
Repo: a plugin marketplace; the supervisor is `at sup` in plugins/agents-core/lib/sup*.py (python3, stdlib only).

## Context for all phases

Tests are stdlib `unittest` under `scripts/tests/`, run by `scripts/tests/run-all.sh`. Each phase
ends with the touched `test_sup_*.py` files; the full suite runs once per phase before the commit.

Terms used below. A **pack repo** is a key of the pack's `branches`: a slug from
`.config/repos.project.md`. Its **checkout** is the path the hub's `.local/repos.map` gives for the
slug; its **pack worktree** is `<checkout>-<pack>`. A key with no line in the map resolves, as in
1.17.0, to the directory of that name beside the hub, so a pack written by 1.17.0 (`branches: {}`
or directory names) keeps working and `test_sup_digest.py` keeps its case. The profile's `repos`
list (absolute paths the supervisor may read) is not changed and not used for this.


## This phase

#### Phase 5: Lab runs and linked local paths

- Files: `plugins/agents-core/lib/sup_workers.py`, `plugins/agents-core/lib/sup.py`,
  `plugins/agents-core/lib/sup_tick.py` (`init` keeps the new key),
  `plugins/agents-tasks/skills/supervise/SKILL.md`,
  `plugins/agents-tasks/skills/supervise/assets/profile.json`,
  `scripts/tests/test_sup_workers.py`, `scripts/tests/test_sup_land.py`,
  `scripts/tests/test_sup_tick.py`. Ceiling: 60 code lines, 25 skill lines.
- Session-plan decisions this touches. D21 (built) is about the supervisor: its lab scripts run
  only through `at sup op`. It stays. A worker that holds a lease it got with `at sup need` runs
  commands itself; that is the built behaviour of the session plan's "A resource" paragraph, and
  D20 says nothing in `at sup` fences a worker. This phase only writes it into the worker prompt.
- Worker prompt: for a resource, run its script yourself while you hold the lease, then release.
- Skill text, the contract of a lab script in a hub: absolute path, arguments only, exit 0 means
  pass, its own timeout below the lease minutes, a fresh output directory per attempt, a separate
  restore script, last lines as the summary plus a log path. A gate is the `Checks:` line of the
  step's last phase; a gate that must test landed state is a one-phase task of its own.
- Profile key `local`: a list of relative paths, each ignored by git in the hub (checked with
  `git check-ignore`), no `..`. Absent in a 1.17.0 profile, which means empty. `start-worker`
  creates the hub path as a directory when it is missing and its name ends in `/`, then makes a
  symbolic link at the same relative path in the task worktree. When something that is not that
  link already exists there, `start-worker` refuses and names it. At landing `kept_ignored` skips
  an entry only while it still is a symbolic link that resolves to the hub path; anything else at
  that path (a tool replaced the link with a file) moves to `kept/<ID>` like any ignored file.
- Generated ledgers: nothing to build. `squash_and_commit` already takes the hub's side of
  `_active.md` and `_done.md` and rebuilds them (`GENERATED`, tested in `test_sup_land.py`); a
  conflict in an area page is hand-written text and still stops the landing with the file named.
- First real run of the lease path: one headless worker with `need`, a granted lease, a script,
  `release`, in a scratch hub. The result goes to the facts file.
- Checks: a linked path is present in the task worktree and its content is in the hub after the
  landing; a real file that replaced a link is in `kept/<ID>`; a pre-existing real directory
  refuses the start; `init` of a profile with `local` keeps it and one without it loads.


## Task-wide acceptance (context, verified after the last phase)


- A pack of three tasks, two of them with code in one sibling repo and one blocked by another,
  runs to `at sup done` in a scratch hub with real sessions: the sibling branch holds one commit
  per phase in task order, nothing is pushed, the hub has one squash commit per task, and the owner
  typed only `prepare-pack` answers, `start-pack` and `watch start`.
- `at sup ready --pack` refuses that pack when an edge, a resource or a repo branch is missing.
- A worker took a lease, ran a script and released it in that run.


## Orchestrator notes

- Work mode: default-branch (`master`), autonomy L1. Do not commit or stage. No new dependency.
- Phases 1-4 are committed (fc0c526, 37d7474, 5e6e330, 71bf02b).
- Scope fence: plugins/agents-core/lib/sup_workers.py, plugins/agents-core/lib/sup.py,
  plugins/agents-core/lib/sup_tick.py, plugins/agents-core/lib/sup_state.py (only if the profile key needs a
  reader there), plugins/agents-tasks/skills/supervise/SKILL.md,
  plugins/agents-tasks/skills/supervise/assets/profile.json, scripts/tests/test_sup_workers.py,
  scripts/tests/test_sup_land.py, scripts/tests/test_sup_tick.py. Nothing else.
- The "first real run of the lease path" item is the orchestrator's (it needs real sessions); do not do it.
  The generated-ledger item needs no code.
- `local` rules, exact:
  - profile.json key `local`: list of strings. Each: relative, no empty, `.` or `..` part, not absolute, no
    backslash, no control character, not `.local/repos.map` or a parent of it (`.local`, `.local/`: that file is
    written per worktree by start-worker). A trailing `/` marks a directory entry. Validate where the profile is
    read for use (one validator; `at sup init` uses the same one and refuses a bad list), and `git check-ignore`
    in the hub must say each is ignored, else Refused naming the entry.
  - `at sup init` (sup_tick.py, the dict built near "out = {"profile": {...") keeps `local` from the spec; a
    profile.json without the key loads as an empty list everywhere.
  - `start-worker`, after the hub worktree exists and before the session starts: for each entry, hub path
    `<hub>/<entry>`; when it is missing and the entry ends in `/`, create the directory (parents too); when it is
    missing and has no trailing `/`, skip the entry (nothing to link) and say so in the output. In the task
    worktree at the same relative path: nothing there -> create parent directories and a symbolic link to the
    absolute hub path; a symbolic link that already resolves to the hub path -> leave it (a restart); anything
    else -> Refused naming the path, and nothing of this start is left half done that a retry cannot pass
    (links already made by this start stay; they are correct). Never follow or replace an existing link that
    points elsewhere. The link must not land outside the worktree: resolve the link's parent and check it is
    inside the worktree (a tracked symlinked directory in the repo could redirect it).
  - Landing (`kept_ignored` in sup.py) and `close-pack` (which calls it): an ignored path is skipped only when
    it is a symbolic link whose target resolves to `<hub>/<entry>` for a `local` entry of the profile;
    everything else is kept as today. `git worktree remove` on a worktree holding only such links must not
    delete the hub content: prove it in a test with a real git worktree (the link is removed, the hub directory
    and its files stay). Check how git reports an ignored symlinked directory in `git status --ignored`
    (entry with or without trailing `/`) and handle both spellings.
  - `kept_ignored(wt)` has two callers (sup.py land, sup_workers.py close-pack); a pack worktree of a sibling
    repo gets no links (only the hub task worktree does), so there it behaves as today.
- Worker prompt (sup_workers.py, where the prompt sentences of phases 1-3 are): one or two sentences. When a
  phase names a resource: ask with `at sup need <resource> <minutes>`, wait for the grant, run the resource's
  script yourself while you hold the lease, then `at sup release <resource>`. Read the existing prompt and the
  `need`/`release` commands first and use their real argument forms; do not invent a flag.
- Skill text (supervise/SKILL.md, at most 25 added lines): the contract of a lab script exactly as the phase
  checklist lists it, the `local` key with one example, and where a gate lives (`Checks:` of the step's last
  phase; a gate on landed state is a one-phase task of its own). assets/profile.json gains `"local": []` or a
  commented example in the form the file already uses. Full `plugin:skill` ids; plain short sentences.
- Code ceiling 60 net lib lines. Earlier phases overran through refusals added in fix rounds: design the
  failure paths above now, in one helper for validation and one for linking.
- Interface: sup_workers._repos(hub) -> ({slug: (default, integration)}, {slug: absolute path}); Refused on a relative map path  (phase 1)
- Interface: sup_workers._checkout(hub, slug, mp) -> Path; pack worktree = <checkout>.parent/<checkout.name>-<pack name>  (phase 1)
- Interface: sup_workers._task_repos(root, task) -> set of slugs; _pack_repos(pack, hub, task); _held(profile, pack, hub, rows) -> {slug: task}  (phase 1)
- Interface: sup_workers._pack_worktrees(profile, pack) -> {slug: tip}, idempotent; _git(path, *args) raises Refused on OSError/timeout; _valid_branch(b)  (phase 1)
- Interface: pack["branches"] {slug: branch}; pack["tips"] {slug: sha} written once by start-pack, phase 2 advances it at landing (this is the plan's `landed_tip`)  (phase 1)
- Interface: sup_state.landing_message(hub_dir, branch, task) -> message of the commit with the whole line `Archive: refs/archive/task/<ID>`, or ''  (phase 2; also fixes a 1.17.0 defect: RM-1 matched the commit of RM-10)
- Interface: sup_workers.pack_for_land(main, profile|None, task) -> (profile, pack) or (None, None); Refused when a pack with branches holds the task under another profile  (phase 2)
- Interface: sup_workers.land_ranges(main, pack, task) -> {slug: (branch, old, new)}; advance_tips(profile, pack, main, hub_commit_message); pack_ahead(hub, pack) -> {slug: (branch, n)}; _pack_wt(checkout, pack); _clean(path); _tip(checkout, branch)  (phase 2)
- Interface: sup_digest._pack_repo_problems / _pack_ready_lines / _ahead_lines return lines, never raise Refused; _branch_exists(hub, repo, branch, mp)  (phase 2)
- Interface: sup_workers._edges(profile, pack, hub|None) -> {task: [open blockers]}; Refused, in this order, on an open blocker outside the pack, a cycle, a serial order against an edge; each names `<task> is blocked by <blocker>`  (phase 3)
- Interface: sup_workers._blockers(profile, hub|None, task) -> list[str]; _task_meta(root, task) -> dict ({} without a file; Refused when unreadable); task_run.blocker_ids(cell) -> list[str] (phases dropped)  (phase 3)
- Interface: sup_watch._starts retries a start refused before claude every 5 minutes (BACKOFF[0]); next_tasks puts tasks of a pack that _edges refuses after the others  (phase 3)
- Interface: sup.pack_problems(profile, pack, hub|None) -> list[str], never raises; lines `<ID>: <problem>` or `pack <name>: <problem>`; `at sup ready --pack <name>` exit 0 `ready` or exit 3; start-pack refuses with the same lines  (phase 4)
- Interface: sup.readiness(task_parsed, path, known=None) -> list[str]; sup._brief() -> the task_brief module; sup_workers._task_repos(root, task, meta=None) -> set[str]  (phase 4)
- Interface: task_lanes.entry_ok(entry) -> bool; task_lanes.split_entry(entry) -> (slug|None, path); `Files:` entries `path` or `<slug>:path`, no `.` or `..` segment  (phase 4)

## Report contract

Write the report to docs/_plans/_runs/supervisor-packs/phase-5/report.md: `## Test plan` first (one row per
checklist behaviour -> lowest layer that proves it -> test name), then what changed per file, the real output of
the tests you ran, code lines added per file against the ceiling, and anything left open. End with
`## Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED`.
