# Plugin + Thin-Seed Restructure — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure `project_template` into a plugin marketplace (4 plugins) + a thin downstream seed driven by an `at` CLI, then migrate all 9 downstream repos off the `_base/` git-merge model.

**Architecture:** Repo root = marketplace (`.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`) over `plugins/{agents-core,agents-tasks,agents-extras,agents-personal}`. Each plugin is a spec-shaped Claude+Codex plugin (`skills/`, `agents/`, `hooks/`, `bin/`, `seed/`). `scripts/build.py` generates every mirror (Codex hooks/agents, marketplace files) from the Claude-side sources and has a `--check` mode. `plugins/agents-core/bin/at` seeds/migrates/doctors downstream repos.

**Tech Stack:** bash (≥4) + python3 (stdlib only) + jq (hooks). Claude Code ≥ 2.1.213, Codex CLI ≥ 0.147.

**Spec:** `docs/specs/2026-08-18-plugin-restructure-design.md` — read it first; the plan argues from it.

## Global Constraints

- No new runtime dependencies: bash, python3 stdlib, jq only (as today).
- Every SKILL.md ≤ 500 lines; `name` = directory name, lowercase-hyphen; `description` ≤ 1,024 chars, harness-neutral ("Use when …", never "wants Codex to").
- Seed `AGENTS.md` ≤ 200 lines. `CLAUDE.md` = `@AGENTS.md`.
- Ledger path fixed: `docs/tasks_manager/`. On-disk task format unchanged; only validation relaxes.
- Plugin names: `agents-core`, `agents-tasks`, `agents-extras`, `agents-personal`; marketplace name `agents-template`; initial version `1.0.0` everywhere; git tag `v1.0.0`.
- Generated files are committed and must round-trip: `python3 scripts/build.py --check` exits 0.
- Never edit downstream repos except in Phase 2/3 tasks; never `git push` anywhere in this plan.
- Commit after each task in this repo (master, per repo convention). Use `git commit -n` while the legacy pre-commit hook still exists (Task 1 replaces it).

## File structure (end state)

```
.claude-plugin/marketplace.json                GENERATED (build.py) — Claude marketplace
.agents/plugins/marketplace.json               GENERATED (build.py) — Codex marketplace
plugins/agents-core/
  .claude-plugin/plugin.json                   hand-written source of version/description
  .codex-plugin/plugin.json                    GENERATED from the Claude manifest
  skills/<15 skills>/SKILL.md (+references/ assets/)
  agents/{implementer,reviewer,researcher,plan-critic,security-auditor,spec-validator}.md
  hooks/hooks.json                             Claude hooks (${CLAUDE_PLUGIN_ROOT})
  hooks/hooks.codex.json                       GENERATED (${PLUGIN_ROOT})
  hooks/{block-dangerous-git,block-dangerous-bash,block-write-sensitive,block-bad-todo-name,remind-archive-done-todo}.sh
  hooks/tests/test-hooks.sh
  codex/agents/*.toml                          GENERATED from agents/*.md
  bin/at                                       bash entry → lib/at.py
  lib/at.py                                    CLI implementation (init/migrate/doctor/bootstrap/ledger…)
  seed/AGENTS.md seed/CLAUDE.md seed/settings.json seed/gitignore.block seed/gitattributes.block
plugins/agents-tasks/
  .claude-plugin/plugin.json  .codex-plugin/plugin.json (GENERATED)
  skills/task-ledger/{SKILL.md,references/{todo-convention,inbox-convention,task-system-quickstart}.md,
                      scripts/{sync_todo_ledgers.py,mdtables.py,reserve_work_item.sh,check_repos_config.sh}}
  skills/<23 more skills>/
  seed/docs/tasks_manager/… seed/docs/areas/… seed/docs/resources/… seed/artifacts/README.md
  seed/workbooks/README.md seed/.config/repos.project.md
plugins/agents-extras/  (.claude-plugin, .codex-plugin GENERATED, skills/<17>)
plugins/agents-personal/(.claude-plugin, .codex-plugin GENERATED, skills/<7>)
scripts/build.py                               generator + --check
scripts/convert_playbook.py                    one-off migration helper (deleted in Task 12)
scripts/tests/run-all.sh                       runs everything below; installed as .git/hooks/pre-commit
scripts/tests/test_sync_todo_ledgers.py
scripts/tests/test-at.sh
scripts/tests/fixtures/ledger-{legacy,minimal}/…
docs/specs/…  docs/plans/…  docs/meta/{UPDATE_PLAN,RESEARCH_SNAPSHOT}.md  docs/migration.md
AGENTS.md CLAUDE.md README.md CHANGELOG.md LICENSE .gitignore .gitattributes
```

---

## Phase 1 — upstream restructure

### Task 1: Marketplace + plugin skeletons + build.py --check

**Files:**
- Create: `plugins/agents-core/.claude-plugin/plugin.json`, same for `agents-tasks`, `agents-extras`, `agents-personal`
- Create: `scripts/build.py`
- Generate: `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, `plugins/*/.codex-plugin/plugin.json`
- Create: `scripts/tests/run-all.sh`
- Modify: `.git/hooks/pre-commit` (local, untracked) → runs `scripts/tests/run-all.sh`

**Interfaces:**
- Produces: `scripts/build.py [--check]` — exit 0 when all generated files match; writes them otherwise. Functions: `load_plugins() -> list[dict]` (reads each `plugins/*/.claude-plugin/plugin.json`), `render_marketplace_claude(plugins)`, `render_marketplace_codex(plugins)`, `render_codex_plugin(manifest)`, `render_codex_hooks(claude_hooks_json)`, `render_codex_agents(agents_dir)`. Later tasks add hook/agent generation to the same file.
- Produces: `scripts/tests/run-all.sh` — sequential runner, exit non-zero on first failure; other tasks append their test commands to it.

- [ ] **Step 1: Write the four Claude manifests** (source of truth). Example for core; adjust `name`/`description`/`keywords` for the others (tasks: "Task ledger, knowledge base, workbooks, artifact registry and cross-repo workflows"; extras: "Architecture, GitHub triage, UI, database-migration and dev-tooling skills"; personal: "Writing, Obsidian, teaching and niche migration skills (personal)").

```json
{
  "name": "agents-core",
  "version": "1.0.0",
  "description": "Core operating skills for coding agents: plan execution, TDD, debugging, spec workflow, handoff, subagent protocol, security review, git discipline — plus safety hooks, subagent roles and the `at` CLI that seeds downstream repos.",
  "author": { "name": "Vitalii Toderian", "url": "https://github.com/toderian" },
  "repository": "https://github.com/toderian/project_template",
  "license": "Apache-2.0",
  "keywords": ["skills", "tdd", "planning", "hooks", "subagents", "codex", "claude-code"]
}
```

- [ ] **Step 2: Write `scripts/build.py`** with the marketplace/codex-manifest generators (hooks/agents generators are added in Tasks 3–4 but stub the functions now so `--check` runs):

```python
#!/usr/bin/env python3
"""Generate every mirrored/derived file in this repo from its Claude-side source.

Sources of truth:  plugins/*/.claude-plugin/plugin.json, plugins/*/hooks/hooks.json,
                   plugins/*/agents/*.md
Generated:         .claude-plugin/marketplace.json, .agents/plugins/marketplace.json,
                   plugins/*/.codex-plugin/plugin.json, plugins/*/hooks/hooks.codex.json,
                   plugins/*/codex/agents/*.toml
Usage: python3 scripts/build.py [--check]
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR = ROOT / "plugins"
MARKETPLACE_NAME = "agents-template"
OWNER = {"name": "Vitalii Toderian", "url": "https://github.com/toderian"}
GENERATED_BANNER = "GENERATED by scripts/build.py from {src}; do not edit by hand."

def load_plugins() -> list[dict]:
    out = []
    for manifest in sorted(PLUGINS_DIR.glob("*/.claude-plugin/plugin.json")):
        data = json.loads(manifest.read_text())
        data["_dir"] = manifest.parent.parent
        assert data["name"] == data["_dir"].name, f"{manifest}: name != dir"
        out.append(data)
    return out

def render_marketplace_claude(plugins: list[dict]) -> str:
    return json.dumps({
        "name": MARKETPLACE_NAME,
        "description": "Agents template: operating contract, skills, hooks and subagents for Claude Code and Codex.",
        "owner": OWNER,
        "plugins": [{
            "name": p["name"], "description": p["description"], "version": p["version"],
            "source": f"./plugins/{p['name']}",
        } for p in plugins],
    }, indent=2) + "\n"

def render_marketplace_codex(plugins: list[dict]) -> str:
    return json.dumps({
        "name": MARKETPLACE_NAME,
        "interface": {"displayName": "Agents Template"},
        "plugins": [{
            "name": p["name"], "description": p["description"], "version": p["version"],
            "source": {"source": "local", "path": f"./plugins/{p['name']}"},
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            "category": "Developer Tools",
        } for p in plugins],
    }, indent=2) + "\n"

def render_codex_plugin(p: dict) -> str:
    out = {
        "name": p["name"], "version": p["version"], "description": p["description"],
        "author": p.get("author", OWNER), "repository": p.get("repository"),
        "license": p.get("license"), "keywords": p.get("keywords", []),
        "skills": "./skills/",
        "interface": {"displayName": p["name"], "shortDescription": p["description"][:120],
                      "category": "Developer Tools"},
    }
    if (p["_dir"] / "hooks" / "hooks.json").exists():
        out["hooks"] = "./hooks/hooks.codex.json"
    return json.dumps({k: v for k, v in out.items() if v is not None}, indent=2) + "\n"

def render_codex_hooks(claude_hooks: dict) -> dict:      # filled in Task 3
    text = json.dumps(claude_hooks)
    text = text.replace("${CLAUDE_PLUGIN_ROOT}", "${PLUGIN_ROOT}").replace("MultiEdit|", "")
    return json.loads(text)

def render_codex_agent(md_path: Path) -> str:              # filled in Task 4
    raise NotImplementedError

def targets(plugins: list[dict]) -> dict[Path, str]:
    t = {
        ROOT / ".claude-plugin/marketplace.json": render_marketplace_claude(plugins),
        ROOT / ".agents/plugins/marketplace.json": render_marketplace_codex(plugins),
    }
    for p in plugins:
        t[p["_dir"] / ".codex-plugin/plugin.json"] = render_codex_plugin(p)
        hooks = p["_dir"] / "hooks/hooks.json"
        if hooks.exists():
            t[p["_dir"] / "hooks/hooks.codex.json"] = json.dumps(
                render_codex_hooks(json.loads(hooks.read_text())), indent=2) + "\n"
        for md in sorted((p["_dir"] / "agents").glob("*.md")) if (p["_dir"] / "agents").is_dir() else []:
            t[p["_dir"] / "codex/agents" / (md.stem + ".toml")] = render_codex_agent(md)
    return t

def main(argv: list[str]) -> int:
    check = "--check" in argv
    plugins = load_plugins()
    stale = []
    for path, content in targets(plugins).items():
        current = path.read_text() if path.exists() else None
        if current != content:
            stale.append(path)
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
                print(f"wrote {path.relative_to(ROOT)}")
    if check and stale:
        for p in stale: print(f"STALE {p.relative_to(ROOT)}", file=sys.stderr)
        return 1
    print("build: ok" if not stale else f"build: wrote {len(stale)} file(s)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```
(Until Task 4 lands, make `render_codex_agent` return a placeholder only if no `agents/` dir exists — i.e. do not create `plugins/agents-core/agents/` before Task 4.)

- [ ] **Step 3: Run `python3 scripts/build.py`** → writes both marketplace files + 4 codex manifests. Then `python3 scripts/build.py --check` → `build: ok`, exit 0.

- [ ] **Step 4: Validate with the harness**: `claude plugin validate .` (marketplace) and `claude plugin validate plugins/agents-core` (etc.) → all report valid. If `validate` complains about empty `skills/`, create `plugins/<p>/skills/.gitkeep` temporarily (removed when skills land).

- [ ] **Step 5: `scripts/tests/run-all.sh`**:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 scripts/build.py --check
for p in plugins/*/; do claude plugin validate "$p" >/dev/null; done
claude plugin validate . >/dev/null
# appended by later tasks:
# bash plugins/agents-core/hooks/tests/test-hooks.sh
# python3 scripts/tests/test_sync_todo_ledgers.py
# bash scripts/tests/test-at.sh
echo "run-all: ok"
```
`chmod +x`, run it → `run-all: ok`. Replace `.git/hooks/pre-commit` with a 3-line script that runs `scripts/tests/run-all.sh` (local file, not tracked).

- [ ] **Step 6: Commit** — `git commit -n -m "feat: scaffold agents-template marketplace and plugin manifests"` (body: what/why per repo convention).

### Task 2: Convert playbooks → plugin skills

**Files:**
- Create: `scripts/convert_playbook.py`
- Create: `plugins/<plugin>/skills/<name>/SKILL.md` for all 57 playbooks per the mapping in spec §5 (plus new hubs `git-discipline`, `task-ledger`, `knowledge-base`, `workbook`, `artifacts-registry`, `connectors-and-mcp`, `setup-project` created in Tasks 5–7)
- Move: sidecar dirs (`playbooks/skills/engineering/tdd/*.md` → `plugins/agents-core/skills/tdd/references/`, etc.), `playbooks/templates/*` → owning skill `assets/`, `playbooks/personalities/*` → `plugins/agents-core/skills/subagent-protocol/references/personalities/`

**Interfaces:**
- Consumes: playbook frontmatter (`name`, `description`, optional `argument-hint`).
- Produces: SKILL.md frontmatter `name`, `description`, optional `argument-hint`, `metadata: {source: <old path>, pack: <old pack>}`; body verbatim with link rewrites.

- [ ] **Step 1: Write `scripts/convert_playbook.py`**:

```python
#!/usr/bin/env python3
"""One-off: playbooks/skills/<bucket>/<name>.md -> plugins/<plugin>/skills/<name>/SKILL.md
Usage: convert_playbook.py <plugin> <name> [<name>...]     (reads MAPPING below for pack)
"""
import json, re, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
LIB = json.loads((ROOT / ".agents/skill-library.json").read_text())
PACK_OF = {s: pack for pack, v in LIB["packs"].items() for s in v["skills"]}
REWRITES = [   # (regex, replacement) applied to body text
    (r"`?playbooks/conventions/todo-convention\.md`?", "the `task-ledger` skill (references/todo-convention.md)"),
    (r"`?playbooks/conventions/inbox-convention\.md`?", "the `task-ledger` skill (references/inbox-convention.md)"),
    (r"`?playbooks/conventions/task-system-quickstart\.md`?", "the `task-ledger` skill"),
    (r"`?playbooks/conventions/knowledge-base-quickstart\.md`?", "the `knowledge-base` skill"),
    (r"`?playbooks/conventions/runbook-convention\.md`?", "the `knowledge-base` skill (references/runbook-convention.md)"),
    (r"`?playbooks/conventions/adr-convention\.md`?", "the `knowledge-base` skill (references/adr-convention.md)"),
    (r"`?playbooks/conventions/generated-artifacts\.md`?", "the `knowledge-base` skill (references/generated-artifacts.md)"),
    (r"`?playbooks/conventions/workbook-convention\.md`?", "the `workbook` skill"),
    (r"`?playbooks/conventions/autonomy-levels\.md`?", "the `git-discipline` skill (references/autonomy-levels.md)"),
    (r"`?playbooks/conventions/plan-critique\.md`?", "the `planning-workflow` skill (references/plan-critique.md)"),
    (r"`?playbooks/conventions/vertical-slicing\.md`?", "the `prd-to-plan` skill (references/vertical-slicing.md)"),
    (r"`?playbooks/conventions/test-taxonomy\.md`?", "the `tdd` skill (references/test-taxonomy.md)"),
    (r"`?playbooks/conventions/connectors-and-mcp\.md`?", "the `connectors-and-mcp` skill"),
    (r"`?playbooks/conventions/agent-loop-recipes\.md`?", "the `subagent-protocol` skill (references/agent-loop-recipes.md)"),
    (r"`?playbooks/conventions/prompt-orchestration\.md`?", "the `subagent-protocol` skill (references/prompt-orchestration.md)"),
    (r"`?playbooks/personalities/(\w+)\.md`?", r"the `\1` personality (subagent-protocol skill, references/personalities/\1.md)"),
    (r"`?_base/scripts/sync-todo-ledgers\.sh`?", "`at ledger`"),
    (r"`?_base/scripts/reserve-work-item\.sh`?", "`at reserve`"),
    (r"`?_base/scripts/check-repos-config\.sh`?", "`at repos-check`"),
    (r"`?_base/scripts/check-template-update\.sh`?", "`at doctor`"),
    (r"`?playbooks/skills/\w+/([\w-]+)\.md`?", r"the `\1` skill"),
    (r"`?playbooks/skills/\w+/([\w-]+)/([\w./-]+)`?", r"`\1` skill references/\2"),
    (r"`?playbooks/templates/([\w.-]+)`?", r"assets/\1"),
    (r"wants Codex to ", "wants to "), (r"Codex should ", "the agent should "),
]
def convert(plugin: str, name: str) -> None:
    src = next(ROOT.glob(f"playbooks/skills/*/{name}.md"))
    dst_dir = ROOT / "plugins" / plugin / "skills" / name
    dst_dir.mkdir(parents=True, exist_ok=True)
    text = src.read_text()
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    fm, body = m.group(1), m.group(2)
    for pat, rep in REWRITES:
        body = re.sub(pat, rep, body)
    fm = re.sub(r"wants Codex to ", "wants to ", fm)
    fm += f"\nmetadata:\n  source: {src.relative_to(ROOT)}\n  pack: {PACK_OF.get(name, 'core')}"
    (dst_dir / "SKILL.md").write_text(f"---\n{fm}\n---\n{body}")
    side = src.with_suffix("")
    if side.is_dir():
        ref = dst_dir / "references"; ref.mkdir(exist_ok=True)
        for f in side.iterdir(): shutil.copy2(f, ref / f.name)
    print(f"{src.relative_to(ROOT)} -> {dst_dir.relative_to(ROOT)}")
if __name__ == "__main__":
    plugin, *names = sys.argv[1:]
    for n in names: convert(plugin, n)
```

- [ ] **Step 2: Run the conversion per plugin** exactly:

```bash
python3 scripts/convert_playbook.py agents-core execute-plan tdd diagnose spec-workflow task-spec-workflow planning-workflow prototype performance-optimization handoff subagent-protocol security-review-owasp simplicity-review squash-workspace-commits init
python3 scripts/convert_playbook.py agents-tasks add-task capture-idea triage-inbox complete-task roadmap audit-todos align tidy-repo prd-to-todos prd-to-plan define-area describe-component distill-knowledge map-system refresh-context ubiquitous-language cross-repo-feature cross-repo-pr-review
python3 scripts/convert_playbook.py agents-extras design-an-interface doubt-driven-development grill-me grill-with-docs improve-codebase-architecture request-refactor-plan zoom-out github-triage prd-to-issues qa triage-issue write-a-prd frontend-design ui-design-review migration-safety setup-pre-commit write-a-skill
python3 scripts/convert_playbook.py agents-personal academic-humanizer deslop edit-article sciwrite obsidian-vault scaffold-exercises migrate-to-shoehorn
```
Then: `git mv plugins/agents-core/skills/init plugins/agents-core/skills/setup-project` and set `name: setup-project` (body rewritten in Task 7). Delete `git-guardrails-claude-code` (not converted). Move `playbooks/personalities/*.md` → `plugins/agents-core/skills/subagent-protocol/references/personalities/`; `playbooks/conventions/{agent-loop-recipes,prompt-orchestration}.md` → same skill's `references/`; `plan-critique.md` → `planning-workflow/references/`; `vertical-slicing.md` → `prd-to-plan/references/`; `test-taxonomy.md` → `tdd/references/`; `autonomy-levels.md` → `git-discipline/references/` (skill created in Task 6). Templates: `adr.template.md`, `runbook*.template.md`, `area-sources.template.md`, `resource-inbox-batch.template.md` → `knowledge-base/assets/`; `cross-repo-*.template.md` → `cross-repo-feature/assets/`; `AGENT_*.template.*` → `handoff/assets/`.

- [ ] **Step 3: Verify no dangling references**: `grep -rn "playbooks/\|_base/\|\.agents/skills\|skills/misc\|skills/engineering\|skills/productivity" plugins/` must return only `metadata.source` lines. Fix by hand any remaining. `grep -rn "Codex" plugins/*/skills/*/SKILL.md | grep -i "description:"` must be empty. Every SKILL.md ≤ 500 lines (`wc -l`); if `execute-plan` or `security-review-owasp` exceed, move sections to `references/`.

- [ ] **Step 4: `claude plugin validate plugins/agents-core`** (and the other three) → valid, no warnings about frontmatter. Fix any `name` mismatch (must equal dir name).

- [ ] **Step 5: Commit** — `git commit -n -m "feat: convert playbooks into plugin skills"` (do NOT delete `playbooks/` yet — Task 12).

### Task 3: Hooks → agents-core (Claude + generated Codex twin)

**Files:**
- Move: `.claude/hooks/*.sh` → `plugins/agents-core/hooks/`; `_base/scripts/tests/test-hooks.sh` → `plugins/agents-core/hooks/tests/test-hooks.sh`
- Create: `plugins/agents-core/hooks/hooks.json`
- Modify: `plugins/agents-core/hooks/block-write-sensitive.sh` (path-segment matching + apply_patch branch), `test-hooks.sh` (paths + new cases)
- Modify: `scripts/build.py` (`render_codex_hooks` already stubbed; ensure `hooks.codex.json` generated), `scripts/tests/run-all.sh` (append hook tests)

- [ ] **Step 1: Write `plugins/agents-core/hooks/hooks.json`**:

```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash", "hooks": [
        { "type": "command", "command": "\"${CLAUDE_PLUGIN_ROOT}\"/hooks/block-dangerous-git.sh" },
        { "type": "command", "command": "\"${CLAUDE_PLUGIN_ROOT}\"/hooks/block-dangerous-bash.sh" } ] },
      { "matcher": "Write|Edit|MultiEdit|apply_patch", "hooks": [
        { "type": "command", "command": "\"${CLAUDE_PLUGIN_ROOT}\"/hooks/block-write-sensitive.sh" },
        { "type": "command", "command": "\"${CLAUDE_PLUGIN_ROOT}\"/hooks/block-bad-todo-name.sh" } ] }
    ],
    "PostToolUse": [
      { "matcher": "Write|Edit|MultiEdit|apply_patch", "hooks": [
        { "type": "command", "command": "\"${CLAUDE_PLUGIN_ROOT}\"/hooks/remind-archive-done-todo.sh" } ] }
    ]
  }
}
```

- [ ] **Step 2: Add failing tests** to `test-hooks.sh` (follow its existing `expect_block`/`expect_allow` helpers): (a) `write: docs/secrets-rotation.md stays allowed`; (b) `write: docs/private-key-policy.md stays allowed`; (c) `write: config/credentials/prod.json blocks`; (d) `write: id_rsa blocks`; (e) `apply_patch: '*** Add File: .creds/token.txt' blocks` (payload `{"tool_name":"apply_patch","tool_input":{"command":"*** Begin Patch\n*** Add File: .creds/token.txt\n+x\n*** End Patch"}}`); (f) `apply_patch: '*** Update File: src/app.py' stays allowed`; (g) `todo-name via apply_patch: '*** Add File: docs/tasks_manager/_todos/bad name.md' blocks`. Run: `bash plugins/agents-core/hooks/tests/test-hooks.sh` → the new cases FAIL.

- [ ] **Step 3: Implement**: in `block-write-sensitive.sh` extract paths as: `file_path` from `.tool_input.file_path` when present; else, when `.tool_name == "apply_patch"`, every line of `.tool_input.command` matching `^\*\*\* (Add|Update|Delete|Move to) File: (.+)$` → capture group 2. Replace substring patterns with segment-anchored regex: `(^|/)(\.creds|\.env(\..*)?|secrets?|credentials?)(/|$)`, plus basenames `id_rsa|id_ed25519|.*\.pem|.*\.key|.*\.p12|.*\.agekey`; keep `.env.example`, `*.example`, `*.template` allowed. Same path-extraction helper in `block-bad-todo-name.sh` and `remind-archive-done-todo.sh` (source a shared `hooks/lib/paths.sh`). Run tests → all pass (43 old + 7 new).

- [ ] **Step 4: Generate Codex twin**: `python3 scripts/build.py` → `hooks/hooks.codex.json` (uses `${PLUGIN_ROOT}`, matcher without `MultiEdit`). `--check` ok. Append `bash plugins/agents-core/hooks/tests/test-hooks.sh` to `run-all.sh`.

- [ ] **Step 5: Commit** — `git commit -n -m "feat: ship safety hooks in agents-core for Claude and Codex"`.

### Task 4: Subagents → agents-core + generated Codex TOML

**Files:**
- Move: `.claude/agents/*.md` → `plugins/agents-core/agents/`
- Modify: each agent md — replace `playbooks/personalities/<x>.md` references with inline "Working style" bullets from that personality (copy the Responsibilities/Working style/Failure modes bullets, ≤ 15 lines) and replace `playbooks/conventions/plan-critique.md` / `playbooks/skills/engineering/security-review-owasp.md` / `test-taxonomy.md` with `${CLAUDE_PLUGIN_ROOT}/skills/planning-workflow/references/plan-critique.md`, `${CLAUDE_PLUGIN_ROOT}/skills/security-review-owasp/SKILL.md` (+`references/languages.md`), `${CLAUDE_PLUGIN_ROOT}/skills/tdd/references/test-taxonomy.md`. Replace "Do NOT read `AGENTS.md` / `_base/AGENTS.md`" with "Do NOT read `AGENTS.md`/`CLAUDE.md`".
- Modify: `scripts/build.py::render_codex_agent`

- [ ] **Step 1: Implement `render_codex_agent`**:

```python
def render_codex_agent(md_path: Path) -> str:
    text = md_path.read_text()
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    fm, body = m.group(1), m.group(2).strip()
    name = re.search(r"^name:\s*(.+)$", fm, re.M).group(1).strip()
    desc = re.search(r"^description:\s*(.+)$", fm, re.M).group(1).strip().strip('"')
    body = re.sub(r"\$\{CLAUDE_PLUGIN_ROOT\}/skills/([\w-]+)/SKILL\.md", r"the `\1` skill ($\1)", body)
    body = re.sub(r"\$\{CLAUDE_PLUGIN_ROOT\}/skills/([\w-]+)/references/([\w./-]+)", r"the `\1` skill's references/\2", body)
    body = body.replace('"""', "'''")
    return (f'# {GENERATED_BANNER.format(src=md_path.relative_to(ROOT))}\n'
            f'name = "{name}"\ndescription = "{desc}"\n'
            f'developer_instructions = """\n{body}\n"""\n')
```

- [ ] **Step 2: Run `python3 scripts/build.py`** → 6 TOMLs in `plugins/agents-core/codex/agents/`; `--check` ok; `python3 -c "import tomllib,glob;[tomllib.load(open(f,'rb')) for f in glob.glob('plugins/agents-core/codex/agents/*.toml')]"` parses. `claude plugin validate plugins/agents-core` ok.

- [ ] **Step 3: Commit** — `git commit -n -m "feat: move subagent roles into agents-core and generate Codex mirrors"`.

### Task 5: task-ledger skill + scripts (slimmed validation) with tests

**Files:**
- Create: `plugins/agents-tasks/skills/task-ledger/SKILL.md` (body = today's `task-system-quickstart.md`, trimmed to the golden path + "run `at ledger check` after edits"; frontmatter `paths: ["docs/tasks_manager/**"]`)
- Move: `playbooks/conventions/{todo-convention,inbox-convention,task-system-quickstart}.md` → `task-ledger/references/`; `_base/scripts/sync_todo_ledgers.py` + `lib/mdtables.py` → `task-ledger/scripts/`; `_base/scripts/reserve-work-item.sh` → `scripts/reserve_work_item.sh`; `_base/scripts/check-repos-config.sh` → `scripts/check_repos_config.sh` (fix its `_base/scripts/lib` import path to sibling `mdtables.py`)
- Modify: `sync_todo_ledgers.py` (root resolution, optional fields, harvest→warn, size warnings, `rotate-log`)
- Create: `scripts/tests/test_sync_todo_ledgers.py`, `scripts/tests/fixtures/ledger-legacy/`, `scripts/tests/fixtures/ledger-minimal/`

**Interfaces:**
- Produces: `sync_todo_ledgers.py [--check] [--root DIR] [rotate-log TASK_ID]`. Root default: `git -C . rev-parse --show-toplevel`, else cwd. `GENERATED_NOTE` text → "_Generated by `at ledger sync`. Do not edit this block by hand._" (keep old note accepted on read).

- [ ] **Step 1: Fixtures**. `ledger-legacy/`: copy the skeleton from `_base/docs/tasks_manager` + one task file with the full 18-row table (as in `todo-convention.md` §File format) with `Status: open`, and one archived task with harvest. `ledger-minimal/`: same skeleton + one task whose table has only `Task ID, Type, Area, Status, Priority, Created, Updated, Source`, and one task file with a `## Execution log` of 250 lines. Both need `_areas.md` with the area/prefix used, `_roadmap.md`, `docs/areas/`.

- [ ] **Step 2: Failing tests** (`unittest`, copies fixture to a tempdir, runs the script via `subprocess`, asserts):

```python
import subprocess, shutil, tempfile, unittest, pathlib
SCRIPT = pathlib.Path(__file__).resolve().parents[2] / "plugins/agents-tasks/skills/task-ledger/scripts/sync_todo_ledgers.py"
FIX = pathlib.Path(__file__).resolve().parent / "fixtures"
def run(fixture, *args):
    tmp = pathlib.Path(tempfile.mkdtemp()); shutil.copytree(FIX / fixture, tmp, dirs_exist_ok=True)
    p = subprocess.run(["python3", str(SCRIPT), "--root", str(tmp), *args], capture_output=True, text=True)
    return p, tmp
class Ledger(unittest.TestCase):
    def test_legacy_full_table_checks_clean(self):
        p, _ = run("ledger-legacy", "--check"); self.assertEqual(p.returncode, 0, p.stderr)
    def test_minimal_table_checks_clean(self):
        p, _ = run("ledger-minimal", "--check"); self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn("missing Owner", p.stderr); self.assertNotIn("missing Last executed", p.stderr)
    def test_oversized_log_warns(self):
        p, _ = run("ledger-minimal", "--check"); self.assertIn("execution log exceeds 200 lines", p.stderr)
    def test_rotate_log_moves_body_and_leaves_pointer(self):
        p, tmp = run("ledger-minimal", "rotate-log", "TST-002")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue((tmp / "docs/tasks_manager/_logs/TST-002.md").exists())
        task = next((tmp / "docs/tasks_manager/_todos").glob("TST-002-*.md")).read_text()
        self.assertIn("_logs/TST-002.md", task); self.assertLess(task.count("\n"), 120)
    def test_missing_harvest_is_warning_not_error(self):
        # ledger-legacy has a second archived task without harvest section
        p, _ = run("ledger-legacy", "--check"); self.assertEqual(p.returncode, 0); self.assertIn("Completion harvest", p.stderr)
    def test_sync_writes_ledgers(self):
        p, tmp = run("ledger-minimal"); self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("TST-001", (tmp / "docs/tasks_manager/_active.md").read_text())
if __name__ == "__main__": unittest.main()
```
Run → fails (no `--root`, missing-field errors).

- [ ] **Step 3: Implement** in `sync_todo_ledgers.py`: parse `--root DIR` and `rotate-log ID`; default root via `git rev-parse --show-toplevel`; in `validate_task_metadata` remove `Last executed`, `Owner`, `Blocked by`, `Source ref` from `required_missing` (still format-check when present); in archived-task checks change harvest `validate_or_warn` → `self.warn`; add `check_task_size(path)`: warn `task '<base>' exceeds 400 lines` and `task '<base>' execution log exceeds 200 lines (run: at ledger rotate-log <ID>)`; implement `rotate_log(taskid)`: find task file, split at `## Execution log`, write body to `_logs/<ID>.md` with header `# Execution log — <ID>` (append if exists), replace section body with `See [_logs/<ID>.md](../_logs/<ID>.md). New entries go there.`; ensure `_logs/` skeleton is created by `at init` (Task 7). Run tests → pass. Also run `--check` against a scratch copy of redmesh's ledger to confirm zero errors: `cp -r /home/vi/work/ratio1/projects/project_r1_redmesh/docs /tmp/…/redmesh-docs && python3 …/sync_todo_ledgers.py --check --root /tmp/…` (read-only copy).

- [ ] **Step 4: Update `reserve_work_item.sh` / `check_repos_config.sh`** to resolve repo root the same way (git toplevel or `--root`), and their usage text to `at reserve …` / `at repos-check`. Smoke: `bash reserve_work_item.sh --help`.

- [ ] **Step 5: Append `python3 scripts/tests/test_sync_todo_ledgers.py` to `run-all.sh`; run it. Commit** — `git commit -n -m "feat: task-ledger skill with slimmed validation and log rotation"`.

### Task 6: New hub skills (git-discipline, knowledge-base, workbook, artifacts-registry, connectors-and-mcp)

**Files:**
- Create: `plugins/agents-core/skills/git-discipline/SKILL.md` (+`references/autonomy-levels.md` moved in Task 2)
- Create: `plugins/agents-tasks/skills/knowledge-base/SKILL.md` (+`references/{knowledge-base-quickstart,runbook-convention,adr-convention,generated-artifacts}.md`, `assets/*.template.md`)
- Create: `plugins/agents-tasks/skills/workbook/SKILL.md` (body = `workbook-convention.md`)
- Create: `plugins/agents-tasks/skills/artifacts-registry/SKILL.md` (body = root `AGENTS.md` §Artifact registry + `artifacts/README.md` how-to)
- Create: `plugins/agents-tasks/skills/connectors-and-mcp/SKILL.md` (body = `connectors-and-mcp.md`)

- [ ] **Step 1: `git-discipline`** — frontmatter `description: "Branch, commit, squash and push rules plus the autonomy ladder (L0–L3). Use when deciding where to commit, whether to branch, how to write commit messages, when squashing task commits, or when a push/force/reset is being considered."`. Body = `_base/AGENTS.md` §9 (branch/commit/push discipline) rewritten to reference `.config/repos.project.md` and `references/autonomy-levels.md`; state plainly: "the `block-dangerous-git` hook refuses `git push`, `reset --hard`, `clean -f`, `branch -D`, forced add at every level; pushing is a human action." Include the commit-message format (`feat:`/`fix:`/`chore:` + `What changed / Why / Checks` body). ≤ 150 lines. Fold `squash-workspace-commits` reference (it stays its own skill).

- [ ] **Step 2: `knowledge-base`, `workbook`, `artifacts-registry`, `connectors-and-mcp`** — each: frontmatter (`name`, harness-neutral `description`), body from the source convention with paths rewritten (`docs/resources/...` unchanged; `_base/...` removed). Add `paths:` where natural: `workbook` → `["workbooks/**"]`, `artifacts-registry` → `["artifacts/**", ".gitattributes"]`, `knowledge-base` → `["docs/resources/**", "docs/areas/**"]`.

- [ ] **Step 3: `claude plugin validate`** both plugins; `wc -l` ≤ 500 each. **Commit** — `git commit -n -m "feat: add hub skills for git discipline, knowledge base, workbooks, artifacts, connectors"`.

### Task 7: Seed files + `at` CLI (init / doctor / bootstrap / ledger wrappers)

**Files:**
- Create: `plugins/agents-core/seed/AGENTS.md`, `seed/CLAUDE.md`, `seed/settings.json`, `seed/gitignore.block`, `seed/gitattributes.block`
- Create: `plugins/agents-tasks/seed/docs/tasks_manager/{_inbox,_todos,_todos_archived,_inbox_archived,_logs}/.gitkeep`, `_areas.md`, `_roadmap.md`, `seed/docs/areas/{_overview.md,global.md}`, `seed/docs/resources/{README.md,CONTEXT.md,global/summary.md,global/runbooks/README.md,_reports/README.md,_inbox/README.md}` (copied from `_base/docs/`, minus `_digests/`, `system-map.md`, `archive/`), `seed/artifacts/README.md`, `seed/workbooks/README.md`, `seed/.config/repos.project.md` (from `_base/repos.project.example.md`)
- Create: `plugins/agents-core/bin/at` (bash), `plugins/agents-core/lib/at.py`
- Create: `plugins/agents-tasks/bin/at-ledger`, `bin/at-reserve`, `bin/at-repos-check` (3-line wrappers exec-ing the scripts with `--root "$(git rev-parse --show-toplevel)"`)
- Modify: `plugins/agents-core/skills/setup-project/SKILL.md` (body: "run `at init …`, then fill the Project section of AGENTS.md; checklist")
- Create: `scripts/tests/test-at.sh`

**Interfaces:**
- Produces: `at init [--with-tasks] [--with-artifacts] [--with-workbooks] [--with-repos] [--all]`, `at doctor`, `at bootstrap [--local DIR] [--codex] [--claude] [--clean-global-skills]`, `at version`, `at ledger <sync|check|rotate-log ID>`, `at reserve …`, `at repos-check`. Exit codes: 0 ok, 1 errors, 2 usage.
- `lib/at.py` functions: `cmd_init(args)`, `cmd_doctor(args)`, `cmd_bootstrap(args)`, `cmd_migrate(args)` (Task 8), `write_seed_file(src, dst, overwrite: bool)`, `merge_managed_block(dst_path, block_text, begin, end)`, `merge_settings_json(dst_path, seed_json)` (deep-merge only keys `extraKnownMarketplaces`, `enabledPlugins`, `permissions.deny`, union lists), `find_tasks_root() -> Path|None`, `repo_root() -> Path`.

- [ ] **Step 1: Write `seed/AGENTS.md`** (≤ 200 lines). Sections, in order — write real text, no placeholders except the marked project slots:
  1. Title + 3-line preamble: "This file is yours (downstream-owned). Shared skills, hooks and subagents come from the `agents-template` plugins; this file routes to them." + `<!-- Claude Code loads this via CLAUDE.md (@AGENTS.md); Codex loads it directly. Keep under 200 lines. -->`
  2. **Operating loop** (5 bullets: first principles → smallest surgical change → narrowest checks first, inspect real output → critique the weakest assumption → review for clarity/adoption; loop when a pass finds a real problem).
  3. **Principles in one line each**: evidence before action; minimal & surgical diff (no drive-by refactors, remove what your change obsoletes); evaluation-driven (never weaken tests); context discipline (offload big outputs to files, keep head/tail); ratchet failures into durable rules; simplicity first, subagents only when the task splits cleanly.
  4. **Autonomy & git**: default L1 (local dev; commit allowed, no push); details in `git-discipline`; hooks block `git push`, `reset --hard`, `clean -f`, `branch -D`, forced add, writes into `.creds/`/secrets, dangerous shell; commit format `type: summary` + `What changed / Why / Checks` body; commit after each coherent slice.
  5. **Routing table** (task → skill): implement a tracked task → `execute-plan` (+`task-ledger` if `docs/tasks_manager/` exists); new feature/bug → `tdd`; unexpected behaviour → `diagnose`; unclear scope → `spec-workflow` / `task-spec-workflow`; before writing a plan → `planning-workflow`; security-sensitive → `security-review-owasp`; branch/commit/push question → `git-discipline`; delegating → `subagent-protocol` (agents: implementer, reviewer, researcher, plan-critic, security-auditor, spec-validator); pausing → `handoff`; capture idea / add task / triage / roadmap / complete → `capture-idea`, `add-task`, `triage-inbox`, `roadmap`, `complete-task`; durable notes/runbooks/ADRs → `knowledge-base`; repeatable workflow → `workbook`; large/generated/encrypted files → `artifacts-registry`; multi-repo → `cross-repo-feature` / `cross-repo-pr-review` + `.config/repos.project.md`; over-engineering check → `simplicity-review`; setting up a repo → `setup-project`.
  6. **Repository conventions** (2 lines each): `.creds/` local-only, never echo/commit values; `.no-commit/` local scratch; `.prompts/` committable prompts (review before commit); `.local/` machine bindings; `.inbox/` local drop-zone; `tools/python/` uv envs (`pyproject.toml`/`uv.lock` committed, `.venv` not); large data via `artifacts/README.md`.
  7. **Definition of done** (5 bullets) + **anti-patterns** (5 bullets).
  8. **Project** — slots with `<!-- TODO-FILL: … -->` comments: Summary; Commands (test/lint/build/run); Domain rules & invariants; Repos & areas; People/coordination. `at doctor` warns while any `TODO-FILL` remains.
  Count lines: must be ≤ 200 (`wc -l`).

- [ ] **Step 2: Other seed files.** `seed/CLAUDE.md` = `@AGENTS.md\n`. `seed/settings.json`:
```json
{
  "extraKnownMarketplaces": { "agents-template": { "source": { "source": "github", "repo": "toderian/project_template" } } },
  "enabledPlugins": { "agents-core@agents-template": true },
  "permissions": { "deny": [
    "Read(./.creds/**)", "Edit(./.creds/**)", "Write(./.creds/**)",
    "Bash(git push --force*)", "Bash(git push -f*)"
  ] }
}
```
`seed/gitignore.block` = today's root `.gitignore` content between markers `# BEGIN agents-template` / `# END agents-template` (add `.inbox/`, `.local/`, `.no-commit/`, `.creds/`, `.venv/`, `tools/python/.venv/`, `__pycache__/`, `*.pyc`, `.claude/settings.local.json*`, `.codex/*` + `!.codex/agents/` + `.codex/agents/*` + `!.codex/agents/*.toml`, `.worktrees/`, `worktrees/`, `.tmp/`, `tmp/`, `temp/`, `project.env`). `seed/gitattributes.block` = markers + `*.pdf *.docx *.xlsx *.pptx *.png *.jpg *.jpeg *.gif *.zip *.gz *.tar binary` (one per line, `binary` attribute).

- [ ] **Step 3: `bin/at`**:
```bash
#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
exec python3 "$HERE/../lib/at.py" "$@"
```
`lib/at.py`: argparse with subcommands. `repo_root()` = `git rev-parse --show-toplevel` (error if not a git repo). `core_root()` = `Path(__file__).parents[1]`. `tasks_root()` = `$AT_TASKS_ROOT` or `core_root().parent / "agents-tasks"` (dev/Codex layout) or newest `core_root().parents[1] / "agents-tasks" / *` (Claude cache layout) else None. `cmd_init`: copy `seed/AGENTS.md`→`AGENTS.md`, `seed/CLAUDE.md`→`CLAUDE.md` (create-only); `merge_settings_json(".claude/settings.json")`; `merge_managed_block(".gitignore", …)`, same for `.gitattributes`; write `.codex/agents/*.toml` from `core_root()/codex/agents/` (overwrite, generated); with `--with-tasks` copy `tasks_root()/seed/docs/**` (create-only) and add `agents-tasks@agents-template: true` to `enabledPlugins`; `--with-artifacts`/`--with-workbooks`/`--with-repos` copy the respective seed files (create-only). Print a per-file `created / kept / merged` report. `cmd_doctor`: checks per spec §7 → prints `OK`/`WARN`/`ERROR` lines, exit 1 on any ERROR. `cmd_bootstrap`: shell out to `claude plugin marketplace add <src>` (src = `--local DIR` or `toderian/project_template`), `claude plugin install agents-core@agents-template` (+ others requested), `codex plugin marketplace add <src>`, `codex plugin add agents-core@agents-template` …; write `~/.local/bin/at` resolver:
```bash
#!/usr/bin/env bash
# resolver written by `at bootstrap`
for c in "$HOME"/.claude/plugins/cache/agents-template/agents-core/*/bin/at \
         "$HOME"/.codex/.tmp/marketplaces/agents-template/plugins/agents-core/bin/at \
         "$AT_DEV_ROOT"/plugins/agents-core/bin/at; do
  [ -x "$c" ] && exec "$c" "$@"
done
echo "at: agents-core not installed (run: claude plugin install agents-core@agents-template)" >&2; exit 1
```
(sort candidates so the newest cache version wins). `--clean-global-skills`: list symlinks in `~/.claude/skills`, `~/.codex/skills`, `~/.agents/skills` whose target contains `/.claude/skills/` or `/skills/<bucket>/` inside a repo that has `_base/` or `playbooks/`; print them; remove only with `--yes`. `cmd_ledger/reserve/repos_check`: `subprocess.run([python3, tasks_root()/skills/task-ledger/scripts/sync_todo_ledgers.py, "--root", repo_root(), *rest])` etc.

- [ ] **Step 4: `scripts/tests/test-at.sh`** (integration): create tmp git repo; run `at init --all` from a PATH that includes `plugins/agents-core/bin` (and `AT_TASKS_ROOT=plugins/agents-tasks`); assert files exist: `AGENTS.md CLAUDE.md .claude/settings.json .codex/agents/implementer.toml docs/tasks_manager/_todos artifacts/README.md workbooks/README.md .config/repos.project.md`; assert `.gitignore` contains both markers; run `at init --all` again → output contains no `created` lines (idempotent); `at doctor` exits 0 with a `WARN … TODO-FILL` line; `wc -l AGENTS.md` ≤ 200; `at ledger check` exits 0. Run → pass. Append to `run-all.sh`.

- [ ] **Step 5: `setup-project/SKILL.md`** rewrite: purpose, "run `at init` with the flags for what the project needs", then walk the human through filling the Project slots, then `at doctor`. **Commit** — `git commit -n -m "feat: add at CLI, downstream seed and setup-project skill"`.

### Task 8: `at migrate` (legacy `_base/` downstream → plugin layout)

**Files:**
- Modify: `plugins/agents-core/lib/at.py` (`cmd_migrate`)
- Modify: `scripts/tests/test-at.sh` (migration case on scratch copies)
- Create: `docs/migration.md`

- [ ] **Step 1: Failing test**: in `test-at.sh`, build a scratch legacy repo: `git clone -q /home/vi/work/vitalii/repos/models_playground "$TMP/light"` (a real light downstream, cloned read-only from local path) and `git clone -q /home/vi/work/ratio1/projects/project_r1_redmesh "$TMP/heavy"`; run `at migrate --yes --commit` in each; assert: no `_base/ playbooks/ .agents/skill-library.json .claude/hooks .claude-plugin` left; `git remote | grep -c template` = 0; `.gitattributes` has no `template-keep`; `CLAUDE.md` exists; `AGENTS.md` ≤ 200 lines and contains the heavy repo's previous project rules (redmesh's 6 rules preserved under `## Project`); `at doctor` exit 0; heavy: `at ledger check` exit 0 and `docs/tasks_manager/_todos` count unchanged; a `backup/pre-plugin-migration-*` branch exists; `git status --porcelain` empty. Run → fails (`migrate` unknown).

- [ ] **Step 2: Implement `cmd_migrate`** (spec §7): preconditions (clean tree, on `master`/`main`, has `_base/` or `playbooks/`); `--dry-run` prints plan only; create backup branch; `git remote remove template` if present; delete dirs: `_base/`, `playbooks/`, `.agents/skills/`, `.agents/skill-library.json`, `.agents/skills.enabled.json`, `.claude/skills/`, `.claude/hooks/`, `.claude-plugin/`; `skills/`: delete only if every file under it is a `SKILL.md`/`README.md`/`.gitkeep` or the two known installer scripts — otherwise abort listing the foreign files (edge_node case; the plan step for edge_node handles its zombies first); `.claude/agents/*.md`: delete files whose `name:` is one of the six roles (they now come from the plugin), keep others; `.codex/agents/*.toml`: regenerate from plugin (overwrite); `CONTEXT.md` delete only if it matches the template stub (contains "template" and ≤ 15 lines); `.gitattributes`: remove the `# BEGIN agents-template merge rules … # END agents-template merge rules` block and lines matching `merge=template-keep-`; `git config --unset-all merge.template-keep-local.driver` etc. (ignore errors); `.claude/settings.json`: drop `hooks` entries whose command contains `.claude/hooks/`, then `merge_settings_json`; **AGENTS.md preservation**: extract the downstream's `## Project-specific overrides` section body minus the known template boilerplate paragraphs (the four seeded subsections `Implementation footprint`, `Local credentials`, `Saved prompts`, `Artifact registry`, `Python tooling environments`, and the "Downstream projects, replace or extend…" list) → keep whatever remains as `## Project` → write new seed AGENTS.md with that content substituted for the Summary/Domain-rules slots (mark unrecognised leftovers under `### Migrated notes`); save the old file as `.no-commit/AGENTS.md.pre-migration` (gitignored) for reference; **README.md**: if it starts with the template README (`# Agents Template` or "This `README.md` extends"), strip that leading block up to the first project H1 and drop the template skills table; then `cmd_init` with `--with-tasks` iff `docs/tasks_manager/_todos` exists, `--with-artifacts` iff `artifacts/` exists, `--with-workbooks` iff `workbooks/` exists, `--with-repos` iff `.config/repos.project.md` exists; run `cmd_doctor`; with `--commit`: `git add -A && git commit -m "chore: migrate to agents-template plugins"` with a body listing removed/added paths.

- [ ] **Step 3: Run `test-at.sh`** → pass. Also dry-run against a clone of edge_node to confirm the `skills/` foreign-file abort message names `skills/watch.py` and `skills/run_container_app.py`.

- [ ] **Step 4: `docs/migration.md`**: human steps: `at bootstrap`, `cd repo`, `at migrate --dry-run`, `at migrate --yes --commit`, fill AGENTS.md Project slots, `at doctor`, open Claude → `/context` shows AGENTS.md; open Codex → `$execute-plan` visible; hooks trust prompt. **Commit** — `git commit -n -m "feat: add at migrate for legacy _base downstreams"`.

### Task 9: Skill descriptions + budget pass

- [ ] **Step 1**: For every SKILL.md, rewrite `description` to ≤ 300 chars where possible, "Use when …" phrasing, no harness names. Add `disable-model-invocation: true` to `complete-task`, `squash-workspace-commits`, `tidy-repo`, `setup-project`.
- [ ] **Step 2**: `claude plugin details agents-core@agents-template` is only available after install; instead compute `sum(len(description))` per plugin with a one-liner and record it in the commit body (target: core ≤ 4k chars, tasks ≤ 6k). `claude plugin validate` all. **Commit** — `git commit -n -m "chore: tighten skill descriptions and mark side-effect skills manual-only"`.

### Task 10: Repo docs, cleanup of legacy trees, changelog, tag

**Files:**
- Delete: `_base/`, `playbooks/`, `skills/`, `.claude/skills/`, `.agents/skills/`, `.agents/skill-library.json`, `.agents/skills.enabled.json`, `.claude-plugin/plugin.json` (root), `.claude/hooks/`, `.claude/agents/`, `.codex/`, `artifacts/`, `docs/_plans/.gitkeep`, `scripts/convert_playbook.py`, root `.claude/settings.json` hooks block (keep the file with permissions only), `.claude/settings.local.json` entries referencing `_base`
- Move: `playbooks/meta/{UPDATE_PLAN,RESEARCH_SNAPSHOT}.md` → `docs/meta/` (before deleting playbooks); `_base/CHANGELOG.md` → `CHANGELOG.md` rewritten
- Rewrite: `README.md`, `AGENTS.md` (this repo's contributor rules), `CLAUDE.md` (`@AGENTS.md`), `.gitignore`, `.gitattributes`

- [ ] **Step 1**: `git rm -r` the legacy trees; ensure `grep -rn "_base/\|playbooks/" --include=*.md --include=*.py --include=*.sh --include=*.json . | grep -v "^./docs/specs\|^./docs/plans\|^./CHANGELOG.md\|^./docs/migration.md\|metadata:\|source: playbooks"` is empty.
- [ ] **Step 2: `README.md`** (≤ 120 lines): what this is; install for Claude (`/plugin marketplace add toderian/project_template`, `/plugin install agents-core@agents-template`) and Codex (`codex plugin marketplace add toderian/project_template`, `codex plugin add agents-core@agents-template`); `at bootstrap` / `at init` / `at migrate`; plugin table (4 rows: what's inside, when to enable); layout; developing (`scripts/build.py`, `scripts/tests/run-all.sh`, releasing with `claude plugin tag`); link to spec, migration doc, changelog.
- [ ] **Step 3: `AGENTS.md`** for this repo (≤ 60 lines): purpose; sources-of-truth vs generated files; run `scripts/tests/run-all.sh` before commit; skill authoring rules (spec-shaped, ≤ 500 lines, harness-neutral description); versioning (bump all four `plugin.json` together, `scripts/build.py`, tag `v<version>`); no vendored third-party code. `CLAUDE.md` = `@AGENTS.md`.
- [ ] **Step 4: `CHANGELOG.md`**: `## 1.0.0 — 2026-08-…` entry summarising the restructure (link spec) + a line "Earlier history: `_base/CHANGELOG.md` in git history before this commit". `.gitignore`: keep `.idea`, `.no-commit/`, `__pycache__/`, `*.pyc`, `.claude/settings.local.json*`, `.codex/*` (no exceptions needed now), `.local/`, `.creds/`. `.gitattributes`: only the binary rules block.
- [ ] **Step 5**: `bash scripts/tests/run-all.sh` → ok. **Commit** — `git commit -m "refactor: remove legacy _base/playbooks trees; document plugin layout"` (pre-commit now runs run-all.sh). Then `git tag -a v1.0.0 -m "agents-template 1.0.0: plugin marketplace + thin seed"`; also `claude plugin tag plugins/agents-core` if it validates cleanly (creates `agents-core--v1.0.0`) — optional, skip if it errors.

### Task 11: End-to-end verification with both harnesses (manual, this machine)

- [ ] **Step 1**: `at bootstrap --local /home/vi/work/vitalii/repos/project_template --claude --codex` (adds marketplace from local path, installs `agents-core`, `agents-tasks`, `agents-extras`; writes `~/.local/bin/at`).
- [ ] **Step 2**: `claude plugin list` shows the three; `claude plugin details agents-core@agents-template` → record projected token cost in `docs/meta/RESEARCH_SNAPSHOT.md` "Verification 2026-08" note. `codex plugin list` shows them installed/enabled.
- [ ] **Step 3**: In a scratch repo seeded by `at init --all`: start `claude -p "/context"` (or interactive) and confirm the memory list shows `CLAUDE.md` → `AGENTS.md`; `/agents-core:tdd` resolves; run `echo test` and `git push --force` through Bash → the latter is blocked by the hook. Codex: `codex exec "list your skills"` shows `$tdd`; first hook run prompts for trust once.
- [ ] **Step 4**: Record results in the commit body of a small `docs: record 1.0.0 verification` commit (or in CHANGELOG under 1.0.0).

---

## Phase 2 — migrate ratio1 hubs (in order: redmesh, edge_node, infra)

Each is one task; same steps. Repos work on `master`; commit there (no push).

### Task 12: Migrate `project_r1_redmesh`
- [ ] `cd /home/vi/work/ratio1/projects/project_r1_redmesh && git status --porcelain` must be empty (if not, stop and report).
- [ ] `at migrate --dry-run` → review list; `at migrate --yes` (no `--commit` yet).
- [ ] Edit `AGENTS.md` Project section: carry over the six RedMesh rules (glossary in `docs/resources/CONTEXT.md`, legacy archive, "run `at ledger check` after task changes" (was `_base/scripts/sync-todo-ledgers.sh --check`), sensitive runtime artifacts, legacy scripts workbook, archived `add-redmesh-vuln`, `tools/python/redmesh-model-training/`), fill Summary/Commands from `README.md`. Remove leftover `TODO-FILL` markers. `wc -l AGENTS.md` ≤ 200.
- [ ] `.claude/settings.json`: enable `agents-tasks` and `agents-extras` (redmesh used architecture/github/docs-knowledge/simplicity/cross-repo packs).
- [ ] `at doctor` → 0; `at ledger check` → 0 (warnings about oversized logs are expected: run `at ledger rotate-log <ID>` for every task file > 400 lines — list them from the warnings — then `at ledger sync`).
- [ ] `git add -A && git commit -m "chore: migrate to agents-template plugins"` (body: removed `_base/ playbooks/ skills/ .claude/skills .agents/skills`, added `CLAUDE.md`, rewrote `AGENTS.md`, rotated N logs).

### Task 13: Migrate `project_r1_edge_node`
- [ ] Clean tree check. First: `git rm skills/watch.py skills/run_container_app.py` (byte-identical to `ops/edge-nodes/scripts/*.py`; verify with `cmp` first) and `git rm docs/_plans/{autonomy-aware-loop-engineering,central-artifact-registry,dated-roadmap-milestones,safe-workspace-commit-squash-skill,task-native-specs-system-map,human-reusable-workflow-artifacts}.md` (verify each is identical to the upstream `playbooks/meta/template-plans/` version at `bc8ccd5` via `git -C /home/vi/work/vitalii/repos/project_template show bc8ccd5:playbooks/meta/template-plans/<name>.md | cmp - docs/_plans/<name>.md`); commit `chore: drop template-imported zombies`.
- [ ] `at migrate --dry-run`, then `at migrate --yes`. `AGENTS.md` Project section: write from `README.md` (line 101 onward: "Ratio1 Edge Node — Development Environment") and `.config/repos.project.md` (9 repos, roles, docs-hub mode: "this repo holds docs/tasks/plans for sibling repos; do not import sibling source"); Commands: e2e (`tests/e2e`, uv), `tools/edge-nodes/*`. `README.md`: remove the template README block (lines 1–100) so the project H1 is first.
- [ ] Enable `agents-tasks` (+`agents-extras` for cross-repo/github). `at doctor` → 0; `at ledger check` → 0 after rotating oversized logs (`DPLY-010`, `DPLY-015`, …). Commit.

### Task 14: Migrate `project_r1_infra`
- [ ] Clean tree check; `at migrate --dry-run`, `--yes` (no `docs/tasks_manager` → tasks plugin not enabled; the repo's own `docs/r1infra/_todos` layout is untouched). `AGENTS.md` Project: summary from the audit (operator notebook for r1infra/r1setup; observability workbook; sibling repo paths from `project.env`); Commands: workbook scripts. `README.md`: replace the template README with a 20-line project README (the file is byte-identical to the template today). Enable `agents-tasks` only if the user wants the ledger later (leave off). `at doctor` → 0. Commit.

## Phase 3 — light consumers

### Task 15: `bootstrap_work`, `models_playground`, `project_technical_writing`, `project_fl_godfather`
- [ ] For each: clean tree; `at migrate --dry-run`; `at migrate --yes --commit` (fl_godfather has no `template` remote — fine). Write a 5-line Project summary in each `AGENTS.md` from its README; commit `docs: fill AGENTS.md project section`. `at doctor` → 0.
- [ ] `project_technical_writing` additionally hosts the global skill symlink targets: run `at bootstrap --clean-global-skills` (lists, then `--yes`) so `~/.claude/skills`, `~/.codex/skills`, `~/.agents/skills` no longer point into it; the writing skills are now `agents-personal` — `claude plugin install agents-personal@agents-template` and `codex plugin add agents-personal@agents-template`.

### Task 16: `learning_project_vi`, `ubuntu-setup`
- [ ] Clean tree; `git remote remove template`; `at init` (no flags); for `learning_project_vi` merge its existing `CLAUDE.md` content into the new `AGENTS.md` Project section and make `CLAUDE.md` = `@AGENTS.md`; commit `chore: adopt agents-template plugins`.

### Task 17: Close-out
- [ ] Update `docs/meta/RESEARCH_SNAPSHOT.md` "Last aligned" date and add the 2026-08-18 audit link; `CHANGELOG.md` 1.0.0 entry lists migrated repos. Update memory notes. Report: what changed per repo, anything left (e.g. Codex per-repo plugin enablement is user-level).

---

## Self-review notes (done while writing)
- Spec §4 layout ↔ Tasks 1–10; §5 inventory ↔ Task 2/6/9; §6 seed ↔ Task 7; §7 CLI ↔ Tasks 7–8; §8 ledger ↔ Task 5; §10 rollout ↔ Tasks 12–17; §11 testing ↔ `run-all.sh` composition + Task 11.
- Names used consistently: `at init|migrate|doctor|bootstrap|ledger|reserve|repos-check`; `render_codex_hooks/agent`; `merge_managed_block`, `merge_settings_json`; plugin names; `hooks.codex.json`; `codex/agents/*.toml`.
