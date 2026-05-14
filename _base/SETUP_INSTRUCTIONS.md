# Setting up a new project from this template

> **Audience:** an agent (or a human) executing the setup of a fresh project that was seeded from this template.
> **Format:** numbered, mechanical steps. Each step has a check that confirms success. Execute in order. If a check fails, stop and report — do **not** continue to the next step.

The agent invoking this file should announce at the start: "Following `_base/SETUP_INSTRUCTIONS.md`. I will run the steps for my runtime and stop on any failed check."

## Each agent sets up its own runtime

This file is **not** a "set up both Claude and Codex" guide. Each agent reading it sets up **only its own runtime**:

- If you are **Claude Code**, run Phases 0 → 2, **Phase 3 (Claude only)**, Phase 5 (optional), Phase 6.
- If you are **Codex**, run Phases 0 → 2, **Phase 4 (Codex only)**, Phase 5 (optional), Phase 6.

A different agent on the other runtime can run this file later to set up its side. Phases 0, 1, 2, 5, 6 are idempotent — running them again on the same project is safe and reports "already done" for each step that was completed before.

---

## Phase 0 — Prerequisites

| Tool | Required for | Check |
|------|--------------|-------|
| `bash` ≥ 4 | every installer in this template | `bash --version` returns a version |
| `python3` | the Codex marketplace + Claude plugin installers | `python3 --version` |
| `git` | template remote and commits | `git --version` |
| `gh` | optional; only if you want to operate on issues/PRs | `gh --version` |

The runtime CLI (`claude` or `codex`) is implicitly available — you, the agent reading this, are it. No separate check needed.

**Check:** `bash`, `python3`, and `git` are all callable. If any is missing, stop and ask the user to install it.

---

## Phase 1 — Wire up the `template` git remote

This template publishes updates at `git@github.com:toderian/project_template.git`. Every downstream project should keep a fetch-only `template` remote pointing at it.

1. Verify there is no existing `template` remote:
   ```bash
   git remote -v | grep -q '^template' && echo "template already configured" || echo "needs setup"
   ```
2. If `needs setup`, run:
   ```bash
   git remote add template git@github.com:toderian/project_template.git
   git remote set-url --push template DISABLE
   git fetch template
   ```
3. **Check:** `git remote -v` shows `template` with the fetch URL `git@github.com:toderian/project_template.git` and the push URL `DISABLE`.

If the check fails, the most likely cause is missing SSH access to the upstream repo. Stop and ask the user.

---

## Phase 2 — Replace the downstream-owned slot files

The template ships placeholder versions of two files that the downstream project must own:

### 2a — `README.md`

The template's own `README.md` describes the template, not your project. Replace it with a short README for **this** project. A minimum acceptable version:

```markdown
# <Project name>

<One-paragraph description of what this project does.>

## Agent contract

This project extends the agents template — see [`_base/README.md`](./_base/README.md)
([upstream](https://github.com/toderian/project_template)).
```

**Check:** `head -1 README.md` shows the project's name (not "Agents Template"). `grep -q '_base/README.md' README.md` succeeds.

### 2b — `AGENTS.md`

The template ships a `AGENTS.md` that auto-loads `_base/AGENTS.md` and reserves a `## Project-specific overrides` slot that says `_None for the base template itself._` Replace the placeholder line under `## Project-specific overrides` with rules specific to this project — domain language, repo-specific test/lint/deploy commands, areas with non-obvious constraints, stakeholder routing rules. Do **not** edit anything else in `AGENTS.md` (the auto-load directive at the top must stay intact).

**Check:** `grep -A3 '^## Project-specific overrides' AGENTS.md | tail -1` does **not** equal `_None for the base template itself._`. The literal string `_base/AGENTS.md` still appears at the top (the auto-load directive is intact).

---

## Phase 3 — Claude Code setup (run **only if you are Claude Code**)

> Codex agents: skip to Phase 5. Do not run this phase.

### 3a — Skills

Claude Code auto-discovers `.claude/skills/`. No installer.

**Check:** `ls .claude/skills/ | wc -l` ≥ 1.

### 3b — Plugins

Run the Claude plugins installer. It merges into `~/.claude/settings.json` without touching unrelated keys.

```bash
./plugins/install-claude-plugins.sh
```

The default curated list is hard-coded at the top of that script under `PLUGINS=( … )`. To change which plugins get installed, edit the array in the script before re-running. The installer is **idempotent** — re-running is safe and reports `already present, left as-is` for entries already in `settings.json`.

**Check:** the installer's stdout shows either `+ plugin: …` (newly added) or `= plugin: … (already present)` for each entry in `PLUGINS`. Exit code 0.

After the installer finishes, tell the user to **restart Claude Code** so the plugins are fetched and enabled.

---

## Phase 4 — Codex setup (run **only if you are Codex**)

> Claude Code agents: skip to Phase 5. Do not run this phase.

### 4a — Skills

Run the Codex skills installer. It symlinks `skills/<name>/` into `~/.codex/skills/`.

```bash
./skills/install-codex-skills.sh
```

**Check:** the installer prints `Installed <name> -> ~/.codex/skills/<name>` for each new skill. Exit code 0. Re-running is idempotent (`Skipping <name>: … already exists`).

### 4b — Plugins

Run the Codex plugins installer. It symlinks `plugins/<name>/` into `~/plugins/` and adds entries to `~/.agents/plugins/marketplace.json`.

```bash
./plugins/install-codex-plugins.sh
```

**Check:** the installer prints `Installed <name> -> ~/plugins/<name>` and `Added marketplace entry for <name>` for each new plugin. Exit code 0.

After both installers finish, tell the user to **restart Codex** so the new skills and plugins are picked up.

---

## Phase 5 — Third-party tools (optional, dual-runtime)

A handful of upstream tools ship their own multi-platform installers. Run this script if you want them — toggle individual sections via env vars (`INSTALL_GSD=0`, `INSTALL_CONTEXT_MODE=0`, `INSTALL_CLAUDE_MEM=0`).

```bash
./plugins/bootstrap-third-party.sh
```

Some entries here only print marketplace-install hints rather than executing them; that is by design (the upstream tools' own install flow is the source of truth). Read the output and follow any hints that apply to your runtime.

**Check:** the script's exit code is 0. Sections that needed user action are clearly logged.

---

## Phase 6 — Final verification

Verify only the runtime you set up (the other one, if it gets set up later, will run its own Phase 6).

**Universal checks (both runtimes):**

1. **Template remote is reachable.** `git ls-remote template HEAD` returns a hash.
2. **Downstream slot files are project-specific.** Re-run the Phase 2 checks.

**If you are Claude Code:**

- `ls .claude/skills/ | wc -l` ≥ 1 (skills auto-discovered).
- `[[ -d .claude/agents ]] && ls .claude/agents/*.md >/dev/null 2>&1` succeeds (native subagent definitions like `implementer.md` and `reviewer.md` are present and auto-loaded).
- `[[ -d .claude/hooks ]] && ls .claude/hooks/*.sh >/dev/null 2>&1` succeeds (PreToolUse hook scripts like `block-dangerous-bash.sh` and `block-dangerous-git.sh` are present). Also verify `.claude/settings.json` references them under `hooks.PreToolUse` — if either the scripts or the references are missing, the safety hooks are not active and the user should be told.
- `python3 -c 'import json; d=json.load(open("'"$HOME"'/.claude/settings.json")); print(list(d.get("enabledPlugins", {}).keys()))'` includes everything from `plugins/install-claude-plugins.sh`'s curated list.

**If you are Codex:**

- `ls ~/.codex/skills/` includes the skills shipped with this template (see `./README.md` § "Available skills" for the current set).
- `python3 -c 'import json; d=json.load(open("'"$HOME"'/.agents/plugins/marketplace.json")); print([p.get("name") for p in d.get("plugins", [])])'` includes everything vendored under `plugins/`.

Report a structured summary to the user. Pick the line for your runtime; leave the other one unsaid (it is not your concern):

```
Setup complete for <Claude Code | Codex>.

- Template remote: <hash>
- Project README replaced: yes/no
- Project AGENTS overrides set: yes/no
- Skills:    <N installed (or "auto-discovered" for Claude)>
- Plugins:   <N installed>
- Third-party (Phase 5): <"ran" OR "skipped">

Restart <Claude Code | Codex> to pick up the new configuration.
```

---

## When something fails

Stop at the failed step. Do **not** continue downstream phases.

Report what failed, what was tried, and what the user can do — for example:

- *"Phase 1 check failed: SSH access to `git@github.com:toderian/project_template.git` is missing. Either add an SSH key to GitHub or switch to HTTPS by running `git remote set-url template https://github.com/toderian/project_template.git`."*
- *"Phase 3b: the `claude` CLI exists but `~/.claude/settings.json` is malformed JSON — the installer refuses to overwrite. Inspect and repair the file, then re-run."*

Do not invent fix-it scripts. Hand control back to the user with the most useful next step.

---

## After setup — what to read next

- `_base/AGENTS.md` — the base operating contract every agent honors.
- `_base/README.md` — full documentation, including the skills catalog.
- `_base/CHANGELOG.md` — what changes when you pull updates from the template.
- `playbooks/skills/` — the authoritative workflow definitions for every shipped skill.

The skill catalog (regenerated automatically) lives in `_base/README.md` § "Available skills". To use any skill, invoke `/<skill-name>` from within Claude Code or Codex.
