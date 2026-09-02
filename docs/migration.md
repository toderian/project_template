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
when there is no `_base/`/`playbooks/` tree to migrate, or when one of the trees it deletes
(`playbooks/`, `skills/`, `.claude/skills/`, `.agents/skills/`) holds a file no version of the
template ever shipped. That last one is deliberate: migration deletes those trees whole, so
anything of your own inside them — a project playbook such as
`playbooks/skills/personal/my-thing.md` and its sidecar scripts — has to come out first. Move or
delete the listed paths (or adopt them into a plugin of your own), then re-run. The check runs
before anything is written, so an abort leaves the repo exactly as it was.

If the only dirtiness is untracked files — a build output, a huge attachments tree, a WIP file
you are not ready to commit — pass `--allow-untracked` instead of stashing or committing them:
`git status --porcelain` may contain any number of `??` entries, but a single tracked
modification or staged change still refuses with the same message. Untracked files migrate does
not manage are never staged, committed or deleted. If any of them lie inside a tree migrate
removes — `_base/`, `.claude/hooks/`, `.claude/skills/`, `.claude-plugin/`, a template
`.claude/agents/*.md`, `.agents/skill-library.json`/`skills.enabled.json`, and the rest of the
list above — migrate refuses instead of deleting them, the same way it refuses on a
downstream-authored file inside `playbooks/`/`skills/`. That check is bidirectional: it also
catches an untracked *ancestor* directory git collapses to one entry (`?? .claude/`) when that
ancestor contains a removal target, not just an untracked file sitting directly inside one.
Untracked files at paths migrate manages — `.codex/agents/*.toml`, `.claude/settings.json`,
`.gitignore`, `.gitattributes` — are *adopted* instead: the plan prints an `adopt` line for
each, `.codex/agents/*.toml` (regenerated wholesale) has its pre-existing content saved to
`.no-commit/pre-migration/<path>` before being overwritten, and `.claude/settings.json`/
`.gitignore`/`.gitattributes` (merged, never wholesale replaced) keep their existing content
with migrate's managed keys/block added on top. Either way the adopted path ends up committed.

With `--allow-untracked`, `--commit` never runs `git add -A`; it stages tracked changes (`git
add -u`) plus the exact paths migration itself created, merged or adopted, force-added one by
one (`git add -f`, since a downstream's own `.gitignore` may ignore a path migration manages
regardless of that local rule), then asserts none of the newly staged paths were on the
pre-migration untracked list — excluding the paths migration itself just staged (its own
created/merged/adopted paths), so seeding its own files into a directory that happened to be
untracked before is never mistaken for a leak. Any add failure or a genuine leak unstages
everything (`git reset -q`) before it dies; nothing is committed.

One gap worth knowing about: a *gitignored* file inside a tree migrate removes (a build
artifact such as `_base/scripts/lib/__pycache__/`) never shows up in `git status --porcelain`
at all, so it is not protected by any of the above — it is deleted along with the tree it lives
in. That is intentional: a gitignored file is regenerable by definition.

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
3. Remotes that point at the template are removed — one named `template` or `templates`, or any
   remote whose fetch URL ends in `toderian/project_template.git` or `/project_template`; the
   plan lists them by name, and your own remotes are untouched. The `merge.template-keep-*` git
   config goes too, and the
   `# BEGIN agents-template merge rules` block plus every `merge=template-keep-*` line leave
   `.gitattributes`. Project rules in that file — Git LFS patterns especially — are untouched.
4. `.claude/settings.json` loses the hook entries that ran scripts from `.claude/hooks/`
   (hooks now come from the plugin); every other key you set survives.
5. `AGENTS.md` becomes the ≤ 200-line plugin seed. Your project rules are carried over into
   `## Project` → `### Domain rules and invariants`: everything under the old file's
   `## Project-specific overrides` heading (any capitalisation) that was not template
   boilerplate, with references to deleted `_base/` scripts repointed at the `at` CLI. If the old
   file has no such heading, nothing is carried over and migrate prints a WARN — merge your rules
   in by hand afterwards. Either way the complete old file is saved to
   `.no-commit/AGENTS.md.pre-migration` (gitignored).
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
`agents-core:setup-project` skill walks through it.

```bash
at doctor      # 0 warnings once the slots are filled
```

## 5. Check both harnesses

- **Claude Code**: open the repo, accept the plugin install prompt for `agents-template`, and run
  `/context` — `AGENTS.md` must appear (it is loaded through `CLAUDE.md`'s `@AGENTS.md`).
  `/agents-core:tdd` should be invocable and `git push --force` should be blocked by the hook.
- **Codex**: `codex plugin add agents-core@agents-template` if you have not already. Open `/hooks`
  to review and trust the bundled hooks, confirm `$agents-core:tdd` appears in `/skills`, and verify
  that the same dangerous git command is blocked. `.codex/agents/*.toml` provides the role mirrors.

If a harness still shows the old skills, they are stale global symlinks — see
`at bootstrap --clean-global-skills`.

## 6. Repos that were never seeded from the template

There is nothing to migrate: run `at init` (with the `--with-*` flags you want), add
`CLAUDE.md`, and remove the template remote (`git remote remove template`, or `templates` —
check `git remote -v`) if one is set.
