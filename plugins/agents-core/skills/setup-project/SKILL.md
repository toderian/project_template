---
name: setup-project
description: "Set up or update a repository's agent contract: seed it with `at init`, fill AGENTS.md's Project section with the human, and adopt template updates after the plugins move. Use when setting up a new repo, after pulling or updating the plugins, when `at doctor` reports routing-table drift, or when AGENTS.md has unfilled TODO-FILL slots."
disable-model-invocation: true
metadata:
  source: playbooks/skills/misc/init.md
  pack: core
---

# Setup Project

## Purpose

Turn a plain repository into one an agent can work in: the downstream-owned `AGENTS.md` contract
(plus `CLAUDE.md`, settings, ignore blocks, role mirrors) and, optionally, the task ledger, artifact
registry, workbook index and repo registry. `at init` writes the files; this skill is about the part
only a human can supply — what this project actually is.

## Two modes

**Setting up** a repo that has no contract yet — work through the Process below.

**Adopting an update** in a repo that already has one, after `at update` and a CLI restart — follow
[references/adopting-updates.md](references/adopting-updates.md) instead. Take that path whenever
`at doctor` reports the routing table is behind the plugin seed; it is written as desired-state checks,
so it is safe from any starting version and safe to re-run.

## Process

### 1. Seed the files

Run `at init` with the flags for what the project needs (skip a flag and nothing for it is written):

```bash
at init --with-tasks --with-artifacts --with-workbooks --with-repos   # or: at init --all
```

- `--with-tasks` — `docs/tasks_manager/` (inbox, tasks, archives, logs, areas registry, roadmap,
  ledgers), `docs/areas/`, `docs/resources/`. Take it whenever the project will track work.
- `--with-artifacts` — `artifacts/README.md`, the registry for large/generated/encrypted files.
- `--with-workbooks` — `workbooks/README.md`, the index for repeatable workflow bundles.
- `--with-repos` — `.config/repos.project.md`, the repo registry for multi-repo work.

`at init` is idempotent and never overwrites a file you own: it reports `created` / `kept` / `merged`
per file. Re-run it any time; only `.codex/agents/*.toml` (generated role mirrors) are refreshed.

### 2. Fill the Project section of AGENTS.md — with the human

The seeded `AGENTS.md` ends with a **Project** section of `TODO-FILL` slots. Interview the user (and
read the repo: README, CI config, package manifests, existing docs) and replace each comment with
real content. Do not guess — an invented command or invariant is worse than an empty slot.

- **Summary** — what this repo is, who uses it, and the one thing an agent must not break.
- **Commands** — the real test / lint / build / run commands, verified by running them, plus their
  gotchas (needs a database, slow suite, fast subset).
- **Domain rules and invariants** — what must stay true after any change: data that may never be
  rewritten, ordering guarantees, compatibility windows, regulatory constraints.
- **Repos and areas** — the areas of this codebase and their non-obvious constraints; for multi-repo
  work, point at `.config/repos.project.md` and name the repos that matter.
- **People and coordination** — who to involve for which change, review expectations, and what needs
  a human decision.

Keep the file under 200 lines: it is always in context. Detail that only some tasks need belongs in
`docs/resources/`, a runbook, or a skill — not here.

### 3. Verify

```bash
at doctor
```

Fix every `ERROR`; the `TODO-FILL` warning disappears once the Project slots are filled. With
`--with-tasks`, `at doctor` also runs the ledger check.

### 4. Report

Tell the user what was created, what they still need to fill, and the entry points they now have:
`agents-tasks:capture-idea` to record an idea, `agents-tasks:add-task` when the work is already
clear, `agents-tasks:triage-inbox` to promote ideas into tasks, `agents-tasks:roadmap` to sequence
them, `execute-plan` to implement one. Structure and conventions for the seeded `docs/` tree live in
the `agents-tasks:task-ledger` and `agents-tasks:knowledge-base` skills; workbook shape in
`agents-tasks:workbook`; the artifact registry in `agents-tasks:artifacts-registry`.

## Quality Bar

- Every `TODO-FILL` slot is either filled with verified content or explicitly deferred with the user.
- Commands in `AGENTS.md` were run at least once and work as written.
- `at doctor` exits 0.
- Nothing the project already owned was overwritten.
