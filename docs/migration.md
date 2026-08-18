# Migrating a legacy downstream to the agents-template plugins

For a repository that was seeded from the pre-plugin template — the one with `_base/`,
`playbooks/`, generated `skills/` trees, `.claude/hooks/` and a `template` git remote.
`at migrate` deletes only what it recognises as template-owned, keeps everything else, and
always leaves a backup branch behind.

## 1. Install the plugins on this machine (once)

```bash
at bootstrap --tasks              # or: at bootstrap --local /path/to/project_template --tasks
```

`at bootstrap` adds the marketplace to Claude Code and Codex, installs `agents-core` (plus
`agents-tasks` with `--tasks`) and writes the `~/.local/bin/at` resolver. Make sure
`~/.local/bin` is on your `PATH`. Add `--clean-global-skills` to list global skill symlinks
that still point into a legacy template tree (`--yes` removes them).

## 2. Look at the plan

```bash
cd /path/to/your/repo
at migrate --dry-run
```

`at migrate` is a dry run unless you pass `--yes`, so the command above and a bare
`at migrate` both print the plan and change nothing. Read it: every path it will remove,
rewrite, keep and seed is listed.

It refuses to go further when the working tree is dirty, when you are not on `master`/`main`,
when there is no `_base/`/`playbooks/` tree to migrate, or when `skills/` holds files that are
not part of a template skill tree. That last one is deliberate — move or delete those files
yourself (they are your project's, not the template's), then re-run.

## 3. Apply it

```bash
at migrate --yes --commit
```

What happens, in order:

1. A `backup/pre-plugin-migration-<YYYYMMDD-HHMMSS>` branch is created from `HEAD`.
2. The vendored template trees go: `_base/`, `playbooks/`, `skills/`, `.claude/skills/`,
   `.agents/skills/`, `.agents/skill-library.json`, `.agents/skills.enabled.json`,
   `.claude/hooks/`, `.claude-plugin/`, the six template subagents in `.claude/agents/`, and a
   `CONTEXT.md` that is still the template stub. Your own files in those directories stay.
3. The `template` git remote and the `merge.template-keep-*` git config are removed, and the
   `# BEGIN agents-template merge rules` block plus every `merge=template-keep-*` line leave
   `.gitattributes`. Project rules in that file — Git LFS patterns especially — are untouched.
4. `.claude/settings.json` loses the hook entries that ran scripts from `.claude/hooks/`
   (hooks now come from the plugin); every other key you set survives.
5. `AGENTS.md` becomes the ≤ 200-line plugin seed. Your project rules are carried over into
   `## Project` → `### Domain rules and invariants`: everything the old file said that was not
   template boilerplate, with references to deleted `_base/` scripts repointed at the `at` CLI.
   The complete old file is saved to `.no-commit/AGENTS.md.pre-migration` (gitignored).
6. A `README.md` that is still the template's is replaced by a short project stub, or trimmed
   down to your own content when your README was appended below the template's. A README that
   was already your own is left alone. The old file is saved to
   `.no-commit/README.md.pre-migration`.
7. `at init` writes the rest of the seed — `CLAUDE.md`, the managed `.gitignore`/`.gitattributes`
   blocks, `.claude/settings.json` marketplace and plugin entries, `.codex/agents/*.toml`,
   `docs/_plans/` — with the opt-in seeds inferred from the repo: the task ledger when
   `docs/tasks_manager/_todos` exists (override with `--keep-tasks` / `--no-tasks`), artifacts
   when `artifacts/` exists, workbooks when `workbooks/` exists, and the repo registry when
   `.config/repos.project.md` exists.
8. `at doctor` runs, then the summary prints. With `--commit` the result is committed as
   `chore: migrate to agents-template plugins`.

To undo everything: `git reset --hard backup/pre-plugin-migration-<stamp>`.

## 4. Fill in the project contract

Open `AGENTS.md` and replace each `<!-- TODO-FILL … -->` slot: summary, commands, domain rules
(already populated if the old file had project rules), repos/areas, people. Use
`.no-commit/AGENTS.md.pre-migration` and the old `README.md` as source material. The
`setup-project` skill walks through it.

```bash
at doctor      # 0 warnings once the slots are filled
```

## 5. Check both harnesses

- **Claude Code**: open the repo, accept the plugin install prompt for `agents-template`, and
  run `/context` — `AGENTS.md` must appear (it is loaded through `CLAUDE.md`'s `@AGENTS.md`).
  `/agents-core:tdd` should be invocable and `git push --force` should be blocked by the hook.
- **Codex**: `codex plugin add agents-core@agents-template` if you have not already; the hook
  trust prompt appears once per machine — accept it. `$execute-plan` and the other skills
  should be listed, and `.codex/agents/*.toml` gives you the subagent mirrors.

If a harness still shows the old skills, they are stale global symlinks — see
`at bootstrap --clean-global-skills`.

## 6. Repos that were never seeded from the template

There is nothing to migrate: run `at init` (with the `--with-*` flags you want), add
`CLAUDE.md`, and `git remote remove template` if one is set.
