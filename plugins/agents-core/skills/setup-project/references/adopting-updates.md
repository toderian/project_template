# Adopting a template update

What to bring into a repo that already uses the template, after the plugins are updated
(`at update`) and the CLI restarted.

Written as **desired state**, not as a per-release changelog: every item below is a condition to
check and fix, so it is safe to run from any starting version and safe to re-run. Nothing here needs
to know which version the repo adopted last.

Work through it in order. Anything ambiguous is a **stop**: ask the user rather than guessing, because
these files are downstream-owned.

## 1. The seed files are current

```bash
at init          # add the flags for what this repo already has, see below
```

`at init` never overwrites a file the repo owns; it reports `created` / `kept` / `merged` per file.
Infer the flags from what is already there, so nothing gets dropped:

| Present in the repo | Flag to pass |
|---|---|
| `docs/tasks_manager/` | `--with-tasks` |
| `artifacts/README.md` | `--with-artifacts` |
| `workbooks/README.md` | `--with-workbooks` |
| `.config/repos.project.md` | `--with-repos` |

Done when `at init` reports no `created` rows you did not expect. `.codex/agents/*.toml` are
copied, never merged: when a plugin release changes an agent card (the 1.4.x releases changed the
implementer and reviewer contracts), refresh them from the installed plugin —
`cp "$(dirname "$(at seed-path)")/../codex/agents/"*.toml .codex/agents/` — and commit the result. A `merged` row for
`.claude/settings.json` usually means a plugin the seed newly enables (such as the
`caveman@caveman` companion) was added; Claude Code installs it at the next session start, and
`at doctor` lists each plugin the seed enables so a repo that is still missing one shows a `WARN`.
A `created` row for `.caveman.json` is expected once: it is the local, git-ignored caveman switch
(inherits the user config, `full` by default), so leave it out of any commit.

## 2. The routing table covers what the seed routes

`AGENTS.md` is downstream-owned, so `at init` leaves it alone — new skills stay unrouted until
someone merges them in. This is the step that actually needs an agent.

`at doctor` names the gap: *"AGENTS.md routing table is N row(s) behind the plugin seed: …"*.
Resolve the active agents-core seed with `at seed-path`; this follows whichever harness supplies
the running `at` instead of assuming a Claude-only environment variable.

Merge the missing rows into the repo's table:

- **Keep every local row.** A downstream row that has no seed equivalent is deliberate; never drop it.
- **Preserve local edits to a shared row.** If a row's key matches but the wording differs, the repo
  may have customised it — keep the local wording and add only what the seed's row newly mentions.
- **Insert each new row next to its seed neighbours**, so the table keeps the seed's reading order.
- **Stop and ask** when a seed row conflicts with a local row rather than extending it.

Done when `at doctor` reports *"AGENTS.md routing table matches the plugin seed"*.

Watch the size: `at doctor` warns past 200 lines, and adding rows can cross it. If it does, say so —
trimming a downstream's own content is the user's call, not yours.

## 3. Conventions the current plugins expect

Check each; fix only what is actually present.

- **One glossary.** The project glossary is `docs/resources/CONTEXT.md` (or the contexts named by
  `docs/resources/CONTEXT-MAP.md`); a root `CONTEXT.md` is a pointer or legacy fallback. If a root
  `UBIQUITOUS_LANGUAGE.md` exists, fold its terms into the glossary and delete it — it competes with
  the file every other skill reads.
- **No legacy tree.** `_base/`, `playbooks/`, `.claude/skills/`, `.claude/hooks/`, `.claude/agents/`
  or `.agents/skills/` means the repo predates the plugin layout: stop and run `at migrate` instead
  of continuing here.
- **Status line.** `.claude/statusline.sh` exists and `.claude/settings.json` points at it, unless
  the repo set a `statusLine` of its own — `at init` never replaces a custom one.
- **Run state.** `docs/tasks_manager/_runs/` exists (seeded by `at init --with-tasks`) and the
  managed `.gitignore` block carries the `_runs/**/diff.patch` and `_runs/*/lock` rules — re-run
  `at init` if the block predates them. Codex users open `/hooks` once after the update to trust the
  `SubagentStop` hook (`require-subagent-status.sh`); untrusted hooks stay silently off.

## 4. The ledger is consistent

With `docs/tasks_manager/`:

```bash
at ledger check
at repos-check          # when the repo has .config/repos.project.md
```

`at doctor` runs the ledger check for you. Duplicate task IDs are the common finding after a gap
between machines: two task files can claim one ID when one of them was never committed. **Never
renumber or delete a task to clear the error** — report the collision, name both files and their
`Created` dates, and let the user choose which survives.

## 5. Commit

Stage only the files this adoption touched — typically `AGENTS.md`, `.claude/settings.json`,
`.claude/statusline.sh` — and never `git add -A`: downstream repos routinely carry unrelated
untracked work.

```
chore: adopt agents-template <version>
```

with the `What changed:` / `Why:` / `Checks:` body the repo's own `AGENTS.md` asks for.

## 6. Report

Say what changed, what `at doctor` says now, and every decision left to the user: a collision you
did not resolve, a size warning you crossed, a legacy tree needing `at migrate`. Do not push.
