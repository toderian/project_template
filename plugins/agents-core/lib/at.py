#!/usr/bin/env python3
"""`at` — the agents-template CLI.

Subcommands:
  init         write the downstream seed into this repo (idempotent, never clobbers)
  doctor       check that this repo still matches the contract
  bootstrap    install the plugins into this machine's harnesses, write ~/.local/bin/at
  migrate      convert a legacy `_base/`/`playbooks/` downstream to the plugin layout
  ledger       wrapper: `sync` | `check` | `rotate-log <TASK_ID>`
  reserve      wrapper: reserve an inbox idea or task filename
  repos-check  wrapper: validate `.config/repos.project.md`
  version      print the agents-core plugin version

Exit codes: 0 ok, 1 errors, 2 usage. Python 3 stdlib only, no third-party imports.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

MARKETPLACE = "agents-template"
DEFAULT_SOURCE = "toderian/project_template"
BEGIN_MARKER = "# BEGIN agents-template"
END_MARKER = "# END agents-template"
MAX_AGENTS_MD_LINES = 200
# The project-slot form in the seed AGENTS.md. Only this exact opener counts as an
# unfilled slot, so prose that merely mentions the token does not keep doctor warning.
TODO_SLOT_MARKER = "<!-- TODO-FILL"

RESOLVER = r"""#!/usr/bin/env bash
# Resolver written by `at bootstrap` (agents-template). Safe to re-run.
# Prefers the newest installed Claude plugin cache version, then the Codex
# marketplace checkout, then $AT_DEV_ROOT for a local development checkout.
set -u

newest_claude_cache() {
  local base="$HOME/.claude/plugins/cache/agents-template/agents-core" version
  [ -d "$base" ] || return 1
  version="$(cd "$base" && ls -1d -- */ 2>/dev/null | tr -d / \
    | sort -t. -k1,1n -k2,2n -k3,3n | tail -n 1)"
  [ -n "$version" ] || return 1
  printf '%s\n' "$base/$version/bin/at"
}

candidates=()
cached="$(newest_claude_cache)" && candidates+=("$cached")
candidates+=("$HOME/.codex/.tmp/marketplaces/agents-template/plugins/agents-core/bin/at")
[ -n "${AT_DEV_ROOT:-}" ] && candidates+=("$AT_DEV_ROOT/plugins/agents-core/bin/at")

for candidate in "${candidates[@]}"; do
  [ -x "$candidate" ] && exec "$candidate" "$@"
done

echo "at: agents-core not installed (run: claude plugin install agents-core@agents-template)" >&2
exit 1
"""


# --------------------------------------------------------------------------- #
# paths and small helpers
# --------------------------------------------------------------------------- #

def die(message: str, code: int = 1) -> None:
    print(f"at: {message}", file=sys.stderr)
    raise SystemExit(code)


def core_root() -> Path:
    """The agents-core plugin root (the parent of this file's lib/ dir)."""
    return Path(__file__).resolve().parents[1]


def repo_root() -> Path:
    """The git toplevel of the current directory."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=False,
        )
    except FileNotFoundError:
        die("git is not on PATH")
    if out.returncode != 0:
        die("not inside a git repository (run `git init` first)")
    return Path(out.stdout.strip()).resolve()


def version() -> str:
    manifest = core_root() / ".claude-plugin" / "plugin.json"
    return json.loads(manifest.read_text())["version"]


def _version_key(name: str) -> tuple:
    """Sort key for a plugin cache directory name, numeric part by part."""
    parts = re.findall(r"\d+", name)
    return tuple(int(p) for p in parts) or (0,)


def find_tasks_root() -> Path | None:
    """Locate the installed agents-tasks plugin root, or None.

    Order: $AT_TASKS_ROOT; the sibling plugin dir (dev checkout and Codex
    marketplace layout `plugins/<name>/`); the newest version dir in the Claude
    cache layout `<marketplace>/<plugin>/<version>/`.
    """
    env = os.environ.get("AT_TASKS_ROOT")
    if env:
        path = Path(env).expanduser()
        return path if (path / "skills").is_dir() else None
    sibling = core_root().parent / "agents-tasks"
    if (sibling / "skills").is_dir():
        return sibling
    cached = core_root().parents[1] / "agents-tasks"
    if cached.is_dir():
        versions = [d for d in cached.iterdir() if (d / "skills").is_dir()]
        if versions:
            return max(versions, key=lambda d: _version_key(d.name))
    return None


def tasks_root() -> Path:
    """Like find_tasks_root(), but exits with an actionable message."""
    found = find_tasks_root()
    if found is None:
        die("agents-tasks is not installed "
            "(run: claude plugin install agents-tasks@agents-template, "
            "or set AT_TASKS_ROOT)")
    return found


# --------------------------------------------------------------------------- #
# seed writers
# --------------------------------------------------------------------------- #

def write_seed_file(src: Path, dst: Path, overwrite: bool) -> str:
    """Copy `src` to `dst`, preserving its mode bits. Returns 'created', 'updated' or 'kept'."""
    data = src.read_bytes()
    if dst.exists():
        if not overwrite or dst.read_bytes() == data:
            return "kept"
        dst.write_bytes(data)
        shutil.copymode(src, dst)
        return "updated"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data)
    shutil.copymode(src, dst)
    return "created"


def merge_managed_block(dst_path: Path, block_text: str,
                        begin: str = BEGIN_MARKER, end: str = END_MARKER) -> str:
    """Replace the `begin`..`end` block in `dst_path`, or append one.

    Markers must be whole lines, so a differently-worded legacy block (e.g.
    `# BEGIN agents-template merge rules`) is left alone for `at migrate`.
    Everything outside the markers is preserved byte for byte.
    Returns 'created', 'merged' or 'kept'.
    """
    existed = dst_path.exists()
    text = dst_path.read_text() if existed else ""
    block = f"{begin}\n{block_text.strip(chr(10))}\n{end}"
    lines = text.splitlines(keepends=True)
    start = stop = None
    for index, line in enumerate(lines):
        if start is None:
            if line.strip() == begin:
                start = index
        elif line.strip() == end:
            stop = index
            break
    if start is not None and stop is None:
        die(f"{dst_path}: found `{begin}` at line {start + 1} without a matching `{end}`; "
            "repair or remove the block by hand, then re-run `at init`")
    if start is not None and stop is not None:
        new_text = "".join(lines[:start]) + block + "\n" + "".join(lines[stop + 1:])
    else:
        prefix = text
        if prefix and not prefix.endswith("\n"):
            prefix += "\n"
        if prefix and not prefix.endswith("\n\n"):
            prefix += "\n"
        new_text = prefix + block + "\n"
    if existed and new_text == text:
        return "kept"
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    dst_path.write_text(new_text)
    return "merged" if existed else "created"


RETIRED_DENY_RULES = frozenset({
    # Claude's permission engine only matches `Edit(path)` for write tools, so
    # a `Write(...)` deny entry is a silent no-op that just prints a warning.
    # `Edit(./.creds/**)` already covers the intent; drop this if an
    # already-seeded repo still carries it.
    "Write(./.creds/**)",
})


def merge_settings_json(dst_path: Path, seed_json: dict) -> str:
    """Deep-merge only the keys this template manages; never drop user keys.

    Managed: `extraKnownMarketplaces` and `enabledPlugins` (missing keys added),
    `permissions.deny` (union, existing order kept, retired rules dropped),
    `statusLine` (set only if the repo has none — never replaces a custom one).
    Returns 'created', 'merged' or 'kept'.
    """
    existed = dst_path.exists()
    data: dict = {}
    if existed:
        raw = dst_path.read_text()
        if raw.strip():
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                die(f"{dst_path}: invalid JSON ({exc}); fix it by hand, then re-run `at init`")
        if not isinstance(data, dict):
            die(f"{dst_path}: expected a JSON object at the top level")
    before = json.dumps(data, sort_keys=True)

    for key in ("extraKnownMarketplaces", "enabledPlugins"):
        wanted = seed_json.get(key) or {}
        if not wanted:
            continue
        bucket = data.setdefault(key, {})
        if not isinstance(bucket, dict):
            die(f"{dst_path}: fix by hand: `{key}` must be a JSON object")
        for name, value in wanted.items():
            bucket.setdefault(name, value)

    deny = (seed_json.get("permissions") or {}).get("deny") or []
    if deny:
        permissions = data.setdefault("permissions", {})
        if not isinstance(permissions, dict):
            die(f"{dst_path}: fix by hand: `permissions` must be a JSON object")
        current = permissions.setdefault("deny", [])
        if not isinstance(current, list):
            die(f"{dst_path}: fix by hand: `permissions.deny` must be a list")
        for rule in deny:
            if rule not in current:
                current.append(rule)

    existing_permissions = data.get("permissions")
    if isinstance(existing_permissions, dict) and isinstance(existing_permissions.get("deny"), list):
        existing_permissions["deny"] = [
            rule for rule in existing_permissions["deny"] if rule not in RETIRED_DENY_RULES
        ]

    if "statusLine" in seed_json and "statusLine" not in data:
        data["statusLine"] = seed_json["statusLine"]

    if existed and json.dumps(data, sort_keys=True) == before:
        return "kept"
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    dst_path.write_text(json.dumps(data, indent=2) + "\n")
    return "merged" if existed else "created"


# --------------------------------------------------------------------------- #
# at init
# --------------------------------------------------------------------------- #

def _copy_tree(src: Path, dst_root: Path, report: list, repo: Path) -> None:
    for path in sorted(src.rglob("*")):
        if path.is_dir():
            continue
        target = dst_root / path.relative_to(src)
        report.append((str(target.relative_to(repo)), write_seed_file(path, target, overwrite=False)))


def seed_repo(repo: Path, with_tasks: bool = False, with_artifacts: bool = False,
              with_workbooks: bool = False, with_repos: bool = False) -> list[tuple[str, str]]:
    """Write the downstream seed into `repo`. Returns a (path, status) report."""
    seed = core_root() / "seed"
    report: list[tuple[str, str]] = []

    for name in ("AGENTS.md", "CLAUDE.md"):
        report.append((name, write_seed_file(seed / name, repo / name, overwrite=False)))

    report.append((".claude/statusline.sh", write_seed_file(
        seed / "statusline.sh", repo / ".claude" / "statusline.sh", overwrite=False)))

    settings = json.loads((seed / "settings.json").read_text())
    if with_tasks:
        settings["enabledPlugins"][f"agents-tasks@{MARKETPLACE}"] = True
    report.append((".claude/settings.json",
                   merge_settings_json(repo / ".claude" / "settings.json", settings)))

    report.append((".gitignore", merge_managed_block(
        repo / ".gitignore", (seed / "gitignore.block").read_text())))
    report.append((".gitattributes", merge_managed_block(
        repo / ".gitattributes", (seed / "gitattributes.block").read_text())))

    # generated role mirrors for Codex — always refreshed from the plugin
    for toml in sorted((core_root() / "codex" / "agents").glob("*.toml")):
        dst = repo / ".codex" / "agents" / toml.name
        report.append((f".codex/agents/{toml.name}", write_seed_file(toml, dst, overwrite=True)))

    # plan scratchpad — several skills write their working plans here
    plans_keep = repo / "docs" / "_plans" / ".gitkeep"
    if plans_keep.exists():
        report.append(("docs/_plans/.gitkeep", "kept"))
    else:
        plans_keep.parent.mkdir(parents=True, exist_ok=True)
        plans_keep.write_text("")
        report.append(("docs/_plans/.gitkeep", "created"))

    if with_tasks or with_artifacts or with_workbooks or with_repos:
        tseed = tasks_root() / "seed"
        if with_tasks:
            _copy_tree(tseed / "docs", repo / "docs", report, repo)
        if with_artifacts:
            report.append(("artifacts/README.md", write_seed_file(
                tseed / "artifacts" / "README.md", repo / "artifacts" / "README.md", overwrite=False)))
        if with_workbooks:
            report.append(("workbooks/README.md", write_seed_file(
                tseed / "workbooks" / "README.md", repo / "workbooks" / "README.md", overwrite=False)))
        if with_repos:
            report.append((".config/repos.project.md", write_seed_file(
                tseed / ".config" / "repos.project.md",
                repo / ".config" / "repos.project.md", overwrite=False)))
    return report


def cmd_init(args: argparse.Namespace) -> int:
    report = seed_repo(repo_root(), with_tasks=args.with_tasks, with_artifacts=args.with_artifacts,
                       with_workbooks=args.with_workbooks, with_repos=args.with_repos)
    for rel, status in report:
        print(f"{status:>7}  {rel}")
    print("at init: done — fill the Project section of AGENTS.md, then run `at doctor`.")
    return 0


# --------------------------------------------------------------------------- #
# at doctor
# --------------------------------------------------------------------------- #

def _ledger_findings(repo: Path, findings: list) -> None:
    script = None
    found = find_tasks_root()
    if found is not None:
        script = found / "skills" / "task-ledger" / "scripts" / "sync_todo_ledgers.py"
    if script is None or not script.exists():
        findings.append(("WARN", "docs/tasks_manager/ exists but agents-tasks is not installed; "
                                 "skipped the ledger check"))
        return
    proc = subprocess.run([sys.executable, str(script), "--check", "--root", str(repo)],
                          capture_output=True, text=True, check=False)
    messages = [line for line in (proc.stderr + proc.stdout).splitlines() if line.strip()]
    warnings = [line for line in messages if line.startswith("WARNING:")]
    for line in warnings:
        findings.append(("WARN", f"ledger: {line[len('WARNING:'):].strip()}"))
    if proc.returncode != 0:
        problems = [line for line in messages if not line.startswith("WARNING:")]
        for line in problems:
            findings.append(("ERROR", f"ledger: {line}"))
        if not problems:
            findings.append(("ERROR", "ledger: `at ledger check` failed"))
    elif not warnings:
        findings.append(("OK", "task ledgers are valid"))


def cmd_doctor(args: argparse.Namespace) -> int:
    repo = repo_root()
    findings: list[tuple[str, str]] = []

    claude_md = repo / "CLAUDE.md"
    if not claude_md.exists():
        findings.append(("ERROR", "CLAUDE.md is missing (run `at init`)"))
    else:
        lines = [line.strip() for line in claude_md.read_text().splitlines() if line.strip()]
        if lines and lines[0] == "@AGENTS.md":
            findings.append(("OK", "CLAUDE.md imports AGENTS.md"))
        else:
            findings.append(("ERROR", "CLAUDE.md must start with `@AGENTS.md`"))

    agents_md = repo / "AGENTS.md"
    if not agents_md.exists():
        findings.append(("ERROR", "AGENTS.md is missing (run `at init`)"))
    else:
        text = agents_md.read_text()
        count = len(text.splitlines())
        if count <= MAX_AGENTS_MD_LINES:
            findings.append(("OK", f"AGENTS.md is {count} lines"))
        else:
            findings.append(("WARN", f"AGENTS.md is {count} lines "
                                     f"(> {MAX_AGENTS_MD_LINES}); move detail into skills or docs"))
        slots = text.count(TODO_SLOT_MARKER)
        if slots:
            findings.append(("WARN", f"AGENTS.md still has {slots} TODO-FILL project slot(s) to fill "
                                     "(see the `setup-project` skill)"))
        else:
            findings.append(("OK", "AGENTS.md project slots are filled"))

    legacy = [name for name in ("_base", "playbooks") if (repo / name).is_dir()]
    if legacy:
        findings.append(("ERROR", f"legacy template layout: {', '.join(name + '/' for name in legacy)} "
                                  "still present — run `at migrate`"))
    else:
        findings.append(("OK", "no legacy `_base/` or `playbooks/` tree"))

    settings_path = repo / ".claude" / "settings.json"
    key = f"agents-core@{MARKETPLACE}"
    if not settings_path.exists():
        findings.append(("WARN", ".claude/settings.json is missing; plugins will not auto-install "
                                 "(run `at init`)"))
    else:
        try:
            settings = json.loads(settings_path.read_text() or "{}")
        except json.JSONDecodeError as exc:
            settings = None
            findings.append(("ERROR", f".claude/settings.json is not valid JSON ({exc})"))
        if settings is not None:
            if (settings.get("enabledPlugins") or {}).get(key) is True:
                findings.append(("OK", f"{key} is enabled in .claude/settings.json"))
            else:
                findings.append(("WARN", f"{key} is not enabled in .claude/settings.json "
                                         "(run `at init`)"))

    if (repo / "docs" / "tasks_manager").is_dir():
        _ledger_findings(repo, findings)

    for level, message in findings:
        print(f"{level:<5} {message}")
    errors = sum(1 for level, _ in findings if level == "ERROR")
    warns = sum(1 for level, _ in findings if level == "WARN")
    print(f"at doctor: {len(findings) - errors - warns} ok, {warns} warning(s), {errors} problem(s)")
    return 1 if errors else 0


# --------------------------------------------------------------------------- #
# at bootstrap
# --------------------------------------------------------------------------- #

def write_resolver(home: Path) -> Path:
    """Write the `at` resolver shim into <home>/.local/bin/at."""
    dst = home / ".local" / "bin" / "at"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(RESOLVER)
    dst.chmod(0o755)
    return dst


def _is_legacy_template_repo(path: Path) -> bool:
    """True if any ancestor of `path` looks like a pre-plugin template checkout."""
    for parent in [path, *path.parents]:
        if (parent / "_base").is_dir() or (parent / "playbooks").is_dir():
            return True
        if (parent / ".git").exists():
            break
    return False


def stale_skill_symlinks(home: Path) -> list[Path]:
    """Global skill symlinks that are dangling, or point into a legacy template skill tree.

    Two independent reasons a global skill symlink is stale:
      (a) its target no longer exists on disk at all -- e.g. the downstream
          repo it pointed into has already been `at migrate`d, which deletes
          its `_base/`/`playbooks/`/`skills/` dirs. Any dangling global skill
          symlink is worth reporting, regardless of what path it used to
          point to.
      (b) its target still exists but resolves into a repo that still has
          `_base/`/`playbooks/` -- the pre-migration case: a symlink into a
          legacy-layout repo that hasn't been migrated yet.
    """
    found: list[Path] = []
    for rel in (".claude/skills", ".codex/skills", ".agents/skills"):
        base = home / rel
        if not base.is_dir():
            continue
        for entry in sorted(base.iterdir()):
            if not entry.is_symlink():
                continue
            target = Path(os.path.realpath(entry))
            if not target.exists():
                found.append(entry)
                continue
            text = str(target)
            if "/.claude/skills/" not in text and not re.search(r"/skills/[^/]+/", text):
                continue
            if _is_legacy_template_repo(target.parent):
                found.append(entry)
    return found


def _run(cmd: list[str]) -> bool:
    print("$ " + " ".join(cmd))
    try:
        proc = subprocess.run(cmd, check=False)
    except FileNotFoundError:
        print(f"at: {cmd[0]} is not on PATH — skipped", file=sys.stderr)
        return False
    if proc.returncode != 0:
        print(f"at: command failed (exit {proc.returncode}) — continuing", file=sys.stderr)
        return False
    return True


def cmd_bootstrap(args: argparse.Namespace) -> int:
    source = str(Path(args.local).expanduser().resolve()) if args.local else DEFAULT_SOURCE
    want_claude, want_codex = args.claude, args.codex
    if not want_claude and not want_codex:
        want_claude = want_codex = True

    names = ["agents-core"]
    for flag, name in ((args.tasks, "agents-tasks"), (args.extras, "agents-extras"),
                       (args.personal, "agents-personal")):
        if flag:
            names.append(name)

    failures = 0
    if want_claude:
        failures += not _run(["claude", "plugin", "marketplace", "add", source])
        for name in names:
            failures += not _run(["claude", "plugin", "install", f"{name}@{MARKETPLACE}"])
    if want_codex:
        failures += not _run(["codex", "plugin", "marketplace", "add", source])
        for name in names:
            failures += not _run(["codex", "plugin", "add", f"{name}@{MARKETPLACE}"])

    resolver = write_resolver(Path.home())
    print(f"wrote {resolver} (make sure ~/.local/bin is on PATH)")

    if args.clean_global_skills:
        candidates = stale_skill_symlinks(Path.home())
        if not candidates:
            print("no stale global skill symlinks found")
        else:
            print("stale global skill symlinks (dangling, or resolving into a legacy template tree):")
            for link in candidates:
                print(f"  {link} -> {os.path.realpath(link)}")
            if args.yes:
                for link in candidates:
                    link.unlink()
                print(f"removed {len(candidates)} symlink(s)")
            else:
                print("re-run with --yes to remove them")

    print("\nThird-party plugins are installed from their own marketplaces, e.g.:")
    print("  claude plugin marketplace add obra/superpowers-marketplace")
    print("  claude plugin install superpowers@superpowers-marketplace")
    return 1 if failures else 0


# --------------------------------------------------------------------------- #
# at migrate
# --------------------------------------------------------------------------- #

BACKUP_PREFIX = "backup/pre-plugin-migration-"
DEFAULT_BRANCHES = ("master", "main")
# Subagents that now ship with the plugin: a legacy copy of one of these is deleted,
# any other `.claude/agents/*.md` is the downstream's own and stays.
TEMPLATE_ROLE_AGENTS = frozenset({
    "implementer", "reviewer", "researcher", "plan-critic", "security-auditor", "spec-validator",
})
# A legacy skill tree is only ever deleted when every file under it is one of these
# or belongs to a skill the template itself shipped (KNOWN_LEGACY_SKILL_NAMES).
TEMPLATE_SKILL_FILES = frozenset({
    "SKILL.md", "README.md", ".gitkeep", "install-codex-skills.sh", "link-skills.sh",
})
LEGACY_SKILL_TREES = ("skills", ".claude/skills", ".agents/skills")

# Frozen: every skill the pre-plugin template ever shipped (57 playbook skills plus the
# two generated role wrappers). The legacy set can no longer grow, so this list is final;
# a skill directory or playbook whose name is missing here is the downstream's own.
KNOWN_LEGACY_SKILL_NAMES = frozenset({
    "academic-humanizer", "add-task", "align", "audit-todos", "capture-idea", "complete-task",
    "cross-repo-feature", "cross-repo-pr-review", "define-area", "describe-component",
    "design-an-interface", "deslop", "diagnose", "distill-knowledge", "doubt-driven-development",
    "edit-article", "execute-plan", "frontend-design", "git-guardrails-claude-code",
    "github-triage", "grill-me", "grill-with-docs", "handoff", "implementer",
    "improve-codebase-architecture", "init", "map-system", "migrate-to-shoehorn",
    "migration-safety", "obsidian-vault", "performance-optimization", "planning-workflow",
    "prd-to-issues", "prd-to-plan", "prd-to-todos", "prototype", "qa", "refresh-context",
    "request-refactor-plan", "reviewer", "roadmap", "scaffold-exercises", "sciwrite",
    "security-review-owasp", "setup-pre-commit", "simplicity-review", "spec-workflow",
    "squash-workspace-commits", "subagent-protocol", "task-spec-workflow", "tdd", "tidy-repo",
    "triage-inbox", "triage-issue", "ubiquitous-language", "ui-design-review", "write-a-prd",
    "write-a-skill", "zoom-out"
})

# Frozen: `playbooks/conventions/`, `playbooks/personalities/` and `playbooks/templates/`.
KNOWN_LEGACY_CONVENTIONS = frozenset({
    "adr-convention.md", "agent-loop-recipes.md", "autonomy-levels.md", "connectors-and-mcp.md",
    "generated-artifacts.md", "inbox-convention.md", "knowledge-base-quickstart.md",
    "plan-critique.md", "prompt-orchestration.md", "runbook-convention.md",
    "task-system-quickstart.md", "test-taxonomy.md", "todo-convention.md", "vertical-slicing.md",
    "workbook-convention.md"
})


KNOWN_LEGACY_PERSONALITIES = frozenset({
    "builder.md", "critic.md", "manager.md", "researcher.md", "reviewer.md", "tester.md"
})


KNOWN_LEGACY_TEMPLATES = frozenset({
    "AGENT_DECISIONS.template.md", "AGENT_PROGRESS.template.md", "AGENT_TASKS.template.json",
    "adr.template.md", "area-sources.template.md", "cross-repo-area-summary.template.md",
    "cross-repo-dependency-graph.template.md", "cross-repo-feature-contract.template.md",
    "resource-inbox-batch.template.md", "runbook.local.template.md", "runbook.template.md"
})
LEGACY_TREES = ("_base", "playbooks", "skills", ".claude/skills", ".claude/hooks",
                ".claude-plugin", ".agents/skills", ".agents/skill-library.json",
                ".agents/skills.enabled.json")
LEGACY_MERGE_BEGIN = "# BEGIN agents-template merge rules"
LEGACY_MERGE_END = "# END agents-template merge rules"
MERGE_DRIVER_MARK = "merge=template-keep-"
MERGE_DRIVER_KEYS = ("merge.template-keep-local.driver", "merge.template-keep-local.name",
                     "merge.template-keep-upstream.driver", "merge.template-keep-upstream.name")
HOOK_DIR_MARK = ".claude/hooks/"
TEMPLATE_REMOTE_NAMES = ("template", "templates")
TEMPLATE_REMOTE_URL_SUFFIXES = ("toderian/project_template.git", "/project_template")
TEMPLATE_README_H1 = "# Agents Template"
TEMPLATE_README_MARK = "This `README.md` extends"
TEMPLATE_README_EMPTY = "_None for the base template itself._"
DOMAIN_SLOT_HEADING = "### Domain rules and invariants"
CONTEXT_STUB_MAX_LINES = 15
PRE_MIGRATION_DIR = ".no-commit"
README_STUB = ("# {name}\n\n<!-- TODO-FILL: one paragraph on what this project is -->\n\n"
               "Agent contract: see AGENTS.md (agents-template plugins).\n")
COMMIT_SUBJECT = "chore: migrate to agents-template plugins"
COMMIT_TRAILER = "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
# Legacy rules that survive migration may still point at deleted `_base/` scripts.
LEGACY_PATH_REWRITES = (
    ("_base/scripts/sync-todo-ledgers.sh --check", "at ledger check"),
    ("_base/scripts/sync-todo-ledgers.sh", "at ledger sync"),
    ("[`_base/AGENTS.md`](./_base/AGENTS.md)", "`AGENTS.md`"),
    ("`_base/AGENTS.md`", "`AGENTS.md`"),
)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, check=False)


def _git_out(repo: Path, *args: str) -> str:
    proc = _git(repo, *args)
    return proc.stdout.strip() if proc.returncode == 0 else ""


# --- markdown block splitting ---------------------------------------------- #

_BULLET = re.compile(r"^\s*([-*+]|\d+\.)\s+")
_FENCE = re.compile(r"^(```+|~~~+)")


def md_units(text: str) -> list[tuple[str, str]]:
    """Split markdown into ('heading'|'block', raw text) units.

    A unit is one heading, one fenced code block, one top-level list item with its
    continuation lines, or one paragraph. `at migrate` compares units, so a legacy
    file that appended project rules to a template list keeps only its own items.
    """
    lines = text.splitlines()
    units: list[tuple[str, str]] = []
    buf: list[str] = []
    fence: str | None = None

    def flush() -> None:
        if buf:
            units.append(("block", "\n".join(buf).rstrip()))
            buf.clear()

    index = 0
    while index < len(lines):
        line = lines[index]
        if fence is not None:
            buf.append(line)
            if line.strip().startswith(fence):
                fence = None
                flush()
            index += 1
            continue
        opening = _FENCE.match(line.strip())
        if opening:
            flush()
            fence = opening.group(1)
            buf.append(line)
            index += 1
            continue
        if not line.strip():
            flush()
            index += 1
            continue
        if line.startswith("#"):
            flush()
            units.append(("heading", line.rstrip()))
            index += 1
            continue
        if _BULLET.match(line):
            flush()
            buf.append(line)
            index += 1
            while index < len(lines):
                nxt = lines[index]
                if (not nxt.strip() or nxt.startswith("#") or _BULLET.match(nxt)
                        or _FENCE.match(nxt.strip())):
                    break
                buf.append(nxt)
                index += 1
            flush()
            continue
        buf.append(line)
        index += 1
    flush()
    return units


def _norm_unit(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def legacy_units() -> frozenset[str]:
    """Normalised blocks of every legacy template AGENTS.md (shipped data file)."""
    path = core_root() / "lib" / "legacy-agents-md.txt"
    if not path.exists():
        die(f"{path} is missing from the installed agents-core plugin")
    return frozenset(line.strip() for line in path.read_text().splitlines()
                     if line.strip() and not line.startswith(";;"))


_OVERRIDES_HEADING = re.compile(r"^##\s+Project-specific overrides\s*$", re.M | re.I)
_PER_DIR_HEADING = re.compile(r"^#{2,4}\s+Per-directory overrides", re.I)
_PREAMBLE_QUOTE = re.compile(r"^>\s*\**\s*Auto-loaded entrypoint", re.I)


def _drop_template_prose(units: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Drop the template preamble blockquote and any per-directory-overrides section.

    Both are template scaffolding in every legacy AGENTS.md, and both are worded
    freely enough downstream that block matching alone does not catch them.
    """
    out: list[tuple[str, str]] = []
    skipping: int | None = None
    for kind, raw in units:
        if kind == "heading":
            level = len(raw) - len(raw.lstrip("#"))
            if skipping is not None and level <= skipping:
                skipping = None
            if _PER_DIR_HEADING.match(raw):
                skipping = level
                continue
        if skipping is not None:
            continue
        if _PREAMBLE_QUOTE.match(raw.strip()):
            continue
        out.append((kind, raw))
    return out


def preserved_project_rules(text: str) -> tuple[str, list[str]]:
    """The downstream's own rules from a legacy AGENTS.md, template blocks removed.

    Returns the rules and any warnings to show the human. Without a
    `## Project-specific overrides` heading (any case) there is no reliable way to
    tell contract from boilerplate, so nothing is carried over and the human is
    pointed at the saved copy instead of getting a mangled contract.
    """
    match = _OVERRIDES_HEADING.search(text)
    if not match:
        return "", [f"the old AGENTS.md has no `## Project-specific overrides` heading, so no "
                    f"project rules were carried over — hand-merge from "
                    f"`{PRE_MIGRATION_DIR}/AGENTS.md.pre-migration`"]
    rest = text[match.end():]
    following = re.search(r"^## ", rest, re.M)
    body = rest[:following.start()] if following else rest
    known = legacy_units()
    kept = [(kind, raw) for kind, raw in _drop_template_prose(md_units(body))
            if _norm_unit(raw) not in known]
    out: list[str] = []
    for index, (kind, raw) in enumerate(kept):
        if kind == "heading":
            following_kind = kept[index + 1][0] if index + 1 < len(kept) else "heading"
            if following_kind == "heading":
                continue  # a heading whose whole body was template boilerplate
        if out and _BULLET.match(raw) and _BULLET.match(out[-1]):
            out[-1] += "\n" + raw  # keep a list a list
            continue
        out.append(raw)
    return "\n\n".join(out).strip(), []


def rewrite_legacy_paths(text: str) -> tuple[str, list[str]]:
    """Repoint `_base/` references that survive in preserved rules; report leftovers."""
    for old, new in LEGACY_PATH_REWRITES:
        text = text.replace(old, new)
    leftovers = [line.strip() for line in text.splitlines() if "_base/" in line]
    return text, leftovers


def fill_domain_slot(seed_text: str, rules: str) -> str:
    """Replace the Domain-rules TODO-FILL marker with the preserved project rules."""
    pattern = re.compile(r"(^" + re.escape(DOMAIN_SLOT_HEADING) + r"\s*\n\n)(<!--.*?-->)",
                         re.M | re.S)
    match = pattern.search(seed_text)
    if not match:
        die("the seed AGENTS.md no longer has the "
            f"`{DOMAIN_SLOT_HEADING}` slot; migration cannot place the project rules")
    return seed_text[:match.start(2)] + rules.strip() + seed_text[match.end(2):]


# --- file-level rewrites ---------------------------------------------------- #

def _collapse_blank_lines(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text).lstrip("\n")
    return text if text.endswith("\n") or not text else text + "\n"


def clean_gitattributes(text: str, path: Path) -> str:
    """Drop the legacy merge-rules block and every `merge=template-keep-*` line."""
    lines = text.splitlines(keepends=True)
    begin = end = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if begin is None:
            if stripped == LEGACY_MERGE_BEGIN:
                begin = index
        elif stripped == LEGACY_MERGE_END:
            end = index
            break
    if begin is not None and end is None:
        die(f"{path}: found `{LEGACY_MERGE_BEGIN}` at line {begin + 1} without a matching "
            f"`{LEGACY_MERGE_END}`; repair it by hand, then re-run `at migrate`")
    if begin is not None:
        lines = lines[:begin] + lines[end + 1:]
    return _collapse_blank_lines("".join(l for l in lines if MERGE_DRIVER_MARK not in l))


def strip_local_hooks(data: dict) -> bool:
    """Drop settings.json hook entries that run scripts from `.claude/hooks/`."""
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return False
    changed = False
    for event in list(hooks):
        groups = hooks[event]
        if not isinstance(groups, list):
            continue
        surviving = []
        for group in groups:
            if isinstance(group, dict) and isinstance(group.get("hooks"), list):
                entries = [e for e in group["hooks"] if HOOK_DIR_MARK not in json.dumps(e)]
                if len(entries) != len(group["hooks"]):
                    changed = True
                    group = dict(group, hooks=entries)
                if not entries:
                    continue
            surviving.append(group)
        if surviving:
            hooks[event] = surviving
        else:
            del hooks[event]
            changed = True
    if not hooks:
        del data["hooks"]
        changed = True
    return changed


def _first_project_h1(lines: list[str]) -> int | None:
    """Index of the first H1 that is not the template's, ignoring fenced examples."""
    fence: str | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if fence is not None:
            if stripped.startswith(fence):
                fence = None
            continue
        opening = _FENCE.match(stripped)
        if opening:
            fence = opening.group(1)
            continue
        if index and stripped.startswith("# ") and stripped != TEMPLATE_README_H1:
            return index
    return None


def _drop_template_tables(text: str) -> str:
    """Remove `### …` sections whose body is the template's empty-catalog placeholder."""
    if TEMPLATE_README_EMPTY not in text:
        return text
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    index = 0
    while index < len(lines):
        if lines[index].startswith("### "):
            stop = index + 1
            while stop < len(lines) and not re.match(r"^#{1,3} ", lines[stop]):
                stop += 1
            if TEMPLATE_README_EMPTY not in "".join(lines[index:stop]):
                out.extend(lines[index:stop])
            index = stop
            continue
        out.append(lines[index])
        index += 1
    return _collapse_blank_lines("".join(out))


def migrate_readme(text: str, project: str) -> str | None:
    """New README body, or None when this README is the project's own."""
    lines = text.splitlines()
    head = lines[:5]
    is_template = ((lines and lines[0].strip() == TEMPLATE_README_H1)
                   or any(TEMPLATE_README_MARK in line for line in head))
    if not is_template:
        return None
    start = _first_project_h1(lines)
    if start is None:
        return README_STUB.format(name=project)
    return _drop_template_tables(_collapse_blank_lines("\n".join(lines[start:]) + "\n"))


def _agent_role(path: Path) -> str | None:
    """The frontmatter `name:` of a markdown subagent file."""
    match = re.match(r"---\s*\n(.*?)\n---", path.read_text(errors="replace"), re.S)
    if not match:
        return None
    name = re.search(r"^name:\s*(.+)$", match.group(1), re.M)
    return name.group(1).strip() if name else None


def _walk_files(root: Path):
    """(path, parts-relative-to-root) for every file under `root`, symlinks not followed."""
    for parent, _dirs, names in os.walk(root, followlinks=False):
        for name in sorted(names):
            path = Path(parent) / name
            yield path, path.relative_to(root).parts


def _skill_tree_foreign(repo: Path, root: Path) -> list[str]:
    """Files in a generated skill tree that belong to no template skill."""
    if not root.is_dir():
        return []
    foreign = []
    for path, parts in _walk_files(root):
        name = parts[-1]
        if len(parts) == 1:                     # installer scripts / README at the tree root
            known = name in TEMPLATE_SKILL_FILES
        elif len(parts) == 2:                   # <bucket>/<file>
            known = name in TEMPLATE_SKILL_FILES or (
                name.endswith(".md") and name[:-3] in KNOWN_LEGACY_SKILL_NAMES)
        else:                                   # <bucket>/<skill>/… sidecars
            known = parts[1] in KNOWN_LEGACY_SKILL_NAMES
        if not known:
            foreign.append(str(path.relative_to(repo)))
    return foreign


def _playbooks_foreign(repo: Path, root: Path) -> list[str]:
    """Files under `playbooks/` that no version of the template ever shipped."""
    if not root.is_dir():
        return []
    foreign = []
    for path, parts in _walk_files(root):
        name, top = parts[-1], parts[0]
        if len(parts) == 1:
            known = name in ("README.md", ".gitkeep")
        elif top == "meta":
            known = True
        elif top == "skills":
            rest = parts[1:]
            if len(rest) == 1:                  # skills/<file>
                known = name in ("README.md", ".gitkeep")
            elif len(rest) == 2:                # skills/<bucket>/<skill>.md
                known = name in ("README.md", ".gitkeep") or (
                    name.endswith(".md") and name[:-3] in KNOWN_LEGACY_SKILL_NAMES)
            else:                               # skills/<bucket>/<skill>/… sidecars
                known = rest[1] in KNOWN_LEGACY_SKILL_NAMES
        elif top == "conventions":
            known = len(parts) == 2 and name in KNOWN_LEGACY_CONVENTIONS
        elif top == "personalities":
            known = len(parts) == 2 and name in KNOWN_LEGACY_PERSONALITIES
        elif top == "templates":
            known = len(parts) == 2 and name in KNOWN_LEGACY_TEMPLATES
        else:
            known = False
        if not known:
            foreign.append(str(path.relative_to(repo)))
    return foreign


def foreign_template_files(repo: Path) -> list[str]:
    """Downstream-authored files inside the trees `at migrate` would delete.

    Migration deletes whole trees, so anything in them that the template never
    shipped has to be moved out first — this is what makes the deletion safe.
    """
    foreign: list[str] = []
    for tree in LEGACY_SKILL_TREES:
        foreign += _skill_tree_foreign(repo, repo / tree)
    foreign += _playbooks_foreign(repo, repo / "playbooks")
    return sorted(set(foreign))


def template_remotes(repo: Path) -> list[str]:
    """Remotes that point at the template: by conventional name or by fetch URL."""
    found = []
    for line in _git_out(repo, "remote", "-v").splitlines():
        parts = line.split()
        if len(parts) < 3 or parts[2] != "(fetch)":
            continue
        name, url = parts[0], parts[1].rstrip("/")
        if name in TEMPLATE_REMOTE_NAMES or url.endswith(TEMPLATE_REMOTE_URL_SUFFIXES):
            found.append(name)
    return sorted(set(found))


def _is_template_context(path: Path) -> bool:
    text = path.read_text(errors="replace")
    return len(text.splitlines()) <= CONTEXT_STUB_MAX_LINES and "template" in text.lower()


def migration_removals(repo: Path) -> list[Path]:
    """Everything `at migrate` recognises as template-owned, in deletion order."""
    removals = [repo / rel for rel in LEGACY_TREES
                if (repo / rel).exists() or (repo / rel).is_symlink()]
    agents_dir = repo / ".claude" / "agents"
    if agents_dir.is_dir():
        removals += [md for md in sorted(agents_dir.glob("*.md"))
                     if _agent_role(md) in TEMPLATE_ROLE_AGENTS]
    context = repo / "CONTEXT.md"
    if context.is_file() and _is_template_context(context):
        removals.append(context)
    return removals


def _remove(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def _save_pre_migration(repo: Path, name: str, text: str) -> str:
    dst = repo / PRE_MIGRATION_DIR / f"{name}.pre-migration"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text)
    return str(dst.relative_to(repo))


def _label(repo: Path, path: Path) -> str:
    rel = str(path.relative_to(repo))
    return rel + "/" if path.is_dir() else rel


def _norm_dir(path: str) -> str:
    """Strip a trailing slash — git's porcelain marker for a directory
    collapsed to one entry because everything under it shares one status."""
    return path[:-1] if path.endswith("/") else path


def _path_matches_any(path: str, entries: list[str]) -> bool:
    """True if `path` equals, or is nested inside, any entry in `entries`.

    Used both ways: is an untracked path inside a tree migrate deletes, and
    is a staged path (from `git diff --name-only`) one that was untracked
    before migrate started. A directory entry (trailing slash — git's
    porcelain marker for a directory collapsed because everything under it
    shares one status) matches both itself and anything nested under it.
    """
    norm_path = _norm_dir(path)
    for entry in entries:
        norm_entry = _norm_dir(entry)
        if norm_path == norm_entry or norm_path.startswith(norm_entry + "/"):
            return True
    return False


def _paths_overlap(a: str, b: str) -> bool:
    """True if `a` and `b` are the same path, or either is nested inside the
    other.

    `_path_matches_any` alone is one-directional (is `a` inside `b`); that
    misses the case where git collapses a wholly-untracked *ancestor* to one
    entry (`?? .claude/`) that is a strict parent of a path we care about
    (`.claude/hooks/`) — `a` inside `b` is false, but `b` inside `a` is true.
    Checking both directions catches it either way.
    """
    return _path_matches_any(a, [b]) or _path_matches_any(b, [a])


def _leaked_untracked_paths(staged: list[str], own_paths: set[str],
                            untracked_before: list[str]) -> list[str]:
    """Staged paths that were untracked before `at migrate` started and are
    not among the paths migrate itself created, merged or rewrote (`own_paths`).

    A last-resort safety net right before `--commit` commits anything: without
    the `own_paths` exclusion, a pre-existing untracked path that migrate
    deliberately overwrites or creates itself (e.g. an untracked `.codex/`
    directory before migrate seeds `.codex/agents/*.toml` into it) would
    false-positive here, aborting after the whole tree has already been
    rewritten.
    """
    return sorted(path for path in staged
                  if path not in own_paths and _path_matches_any(path, untracked_before))


def cmd_migrate(args: argparse.Namespace) -> int:
    repo = repo_root()
    if args.keep_tasks and args.no_tasks:
        die("--keep-tasks and --no-tasks are mutually exclusive", code=2)

    # --- preconditions (nothing is touched before all of them pass) ---------
    if not any((repo / name).is_dir() for name in ("_base", "playbooks")):
        die("no legacy `_base/` or `playbooks/` tree here — nothing to migrate "
            "(run `at init` to seed the plugin contract instead)")
    branch = _git_out(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if branch not in DEFAULT_BRANCHES:
        die(f"on branch `{branch}` — migrate from the default branch "
            f"({' or '.join('`' + b + '`' for b in DEFAULT_BRANCHES)})")
    # `-z`: NUL-delimited, so an untracked path is never C-quoted/escaped —
    # no unescaping needed to recover the real path.
    status_out = _git(repo, "status", "--porcelain", "-z").stdout
    status_entries = [entry for entry in status_out.split("\0") if entry]
    tracked_dirty = [entry for entry in status_entries if not entry.startswith("??")]
    # Pre-migration untracked (`??`) set, computed once, right after the
    # precondition that reads it: `--allow-untracked` lets these survive
    # alongside a dirty-tree refusal, but they must never be staged, removed,
    # or otherwise touched by anything migrate does below.
    untracked_before = [entry[3:] for entry in status_entries if entry.startswith("??")]
    if tracked_dirty or (untracked_before and not args.allow_untracked):
        die(f"the working tree is not clean ({len(tracked_dirty)} tracked change(s), "
            f"{len(untracked_before)} untracked path(s)); commit or stash first — migration "
            "rewrites tracked files")
    foreign = foreign_template_files(repo)
    if foreign:
        die("these files live in trees this migration deletes, but no version of the template "
            "ever shipped them:\n"
            + "\n".join(f"  {path}" for path in foreign)
            + "\nmove or delete these first (or adopt them into a plugin), "
              "then re-run `at migrate`")

    removals = migration_removals(repo)
    if untracked_before:
        # An untracked file inside a tree migrate deletes would otherwise be
        # silently destroyed by `_remove()`/`shutil.rmtree` below — refuse
        # instead, the same way `foreign_template_files` refuses on a
        # downstream-authored file inside skills/playbooks trees. Bidirectional
        # (`_paths_overlap`, not `_path_matches_any`): git may collapse a
        # wholly-untracked *ancestor* to one entry (`?? .claude/`) that is a
        # strict parent of a removal target (`.claude/hooks/`) — checking only
        # "is the untracked entry inside a removal" misses that shape.
        removal_labels = [_label(repo, path) for path in removals]
        blocked = sorted({entry for entry in untracked_before
                          if any(_paths_overlap(entry, label) for label in removal_labels)})
        if blocked:
            die("these untracked path(s) live inside (or contain) a tree `at migrate` deletes; "
                "move them out first — migrate will not delete untracked files:\n"
                + "\n".join(f"  {path}" for path in blocked))

    # --- adoption: a pre-existing untracked file at a path migrate manages --
    # is "adopted" — merged or overwritten with generated content, then
    # committed — rather than left alone. Detected read-only so the dry-run
    # plan and the real apply agree on the same list; only the apply phase
    # actually performs the .codex/agents/*.toml backup-before-overwrite.
    # `.claude/settings.json`/`.gitignore`/`.gitattributes` are safe without a
    # backup: they are always merged (existing content kept, managed keys/
    # block added), never wholesale replaced.
    codex_toml_targets = [str((repo / ".codex" / "agents" / toml.name).relative_to(repo))
                          for toml in sorted((core_root() / "codex" / "agents").glob("*.toml"))]
    adopted_overwrite = sorted({rel for rel in codex_toml_targets
                                if (repo / rel).is_file()
                                and any(_paths_overlap(rel, entry) for entry in untracked_before)})
    adopted_merge = sorted({rel for rel in (".claude/settings.json", ".gitignore", ".gitattributes")
                            if (repo / rel).is_file()
                            and any(_paths_overlap(rel, entry) for entry in untracked_before)})

    with_tasks = (repo / "docs" / "tasks_manager" / "_todos").is_dir()
    if args.keep_tasks:
        with_tasks = True
    if args.no_tasks:
        with_tasks = False
    with_artifacts = (repo / "artifacts").is_dir()
    with_workbooks = (repo / "workbooks").is_dir()
    with_repos = (repo / ".config" / "repos.project.md").is_file()
    if (with_tasks or with_artifacts or with_workbooks or with_repos) and find_tasks_root() is None:
        die("this repo needs the agents-tasks seed (task ledger, artifacts, workbooks or repo "
            "registry) but agents-tasks is not installed "
            "(run: claude plugin install agents-tasks@agents-template, or set AT_TASKS_ROOT)")

    remotes = template_remotes(repo)
    old_agents = (repo / "AGENTS.md").read_text() if (repo / "AGENTS.md").exists() else ""
    old_readme = (repo / "README.md").read_text() if (repo / "README.md").exists() else ""
    new_readme = migrate_readme(old_readme, repo.name) if old_readme else None
    rules, warnings = preserved_project_rules(old_agents) if old_agents else ("", [])
    leftovers: list[str] = []
    if rules:
        rules, leftovers = rewrite_legacy_paths(rules)
    seed_agents = (core_root() / "seed" / "AGENTS.md").read_text()
    new_agents = fill_domain_slot(seed_agents, rules) if rules else seed_agents

    attributes = repo / ".gitattributes"
    old_attributes = attributes.read_text() if attributes.exists() else None
    new_attributes = (clean_gitattributes(old_attributes, attributes)
                      if old_attributes is not None else None)

    settings_path = repo / ".claude" / "settings.json"
    settings: dict | None = None
    if settings_path.exists():
        raw = settings_path.read_text()
        try:
            parsed = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError as exc:
            die(f"{settings_path}: invalid JSON ({exc}); fix it by hand, then re-run `at migrate`")
        if isinstance(parsed, dict) and strip_local_hooks(parsed):
            settings = parsed

    kept = [_label(repo, path) for path in sorted((repo / ".claude" / "agents").glob("*.md"))
            if path not in removals]
    kept += [_label(repo, path) for path in sorted((repo / ".agents").glob("*"))
             if path not in removals] if (repo / ".agents").is_dir() else []
    if (repo / "CONTEXT.md").is_file() and (repo / "CONTEXT.md") not in removals:
        kept.append("CONTEXT.md")
    if old_readme and new_readme is None:
        kept.append("README.md (project-owned)")

    seed_flags = [name for name, on in (("--with-tasks", with_tasks),
                                        ("--with-artifacts", with_artifacts),
                                        ("--with-workbooks", with_workbooks),
                                        ("--with-repos", with_repos)) if on]

    print(f"at migrate: {repo}")
    if untracked_before:
        print(f"  ignore   {len(untracked_before)} untracked path(s) (--allow-untracked): "
              "never staged, committed or deleted, unless adopted below")
    for entry in adopted_overwrite:
        print(f"  adopt    {entry} (was untracked; saved to {PRE_MIGRATION_DIR}/pre-migration/{entry})")
    for entry in adopted_merge:
        print(f"  adopt    {entry} (was untracked; merged, now managed)")
    for path in removals:
        print(f"  remove   {_label(repo, path)}")
    for remote in remotes:
        print(f"  remove   git remote `{remote}`")
    if new_attributes is not None and new_attributes != old_attributes:
        print("  rewrite  .gitattributes (drop the legacy merge rules)")
    if settings is not None:
        print("  rewrite  .claude/settings.json (drop hooks that run from .claude/hooks/)")
    print(f"  rewrite  AGENTS.md (plugin seed{'' if not rules else ' + preserved project rules'})")
    if new_readme is not None:
        print("  rewrite  README.md (drop the template README)")
    for entry in kept:
        print(f"  keep     {entry}")
    print(f"  seed     at init {' '.join(seed_flags)}".rstrip()
          + "  (CLAUDE.md, the managed .gitignore/.gitattributes blocks, "
            ".claude/settings.json, .codex/agents/, docs/_plans/)")
    for warning in warnings:
        print(f"  WARN     {warning}")

    if args.dry_run or not args.yes:
        print("at migrate: dry run — nothing changed. Re-run with `--yes` to apply.")
        return 0

    # --- apply --------------------------------------------------------------
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = f"{BACKUP_PREFIX}{stamp}"
    if _git(repo, "branch", backup).returncode != 0:
        die(f"could not create the backup branch `{backup}`")
    print(f"\ncreated backup branch {backup}")

    removed = [_label(repo, path) for path in removals]
    for path in removals:
        _remove(path)
    for rel in (".claude/agents", ".agents"):
        path = repo / rel
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()
    for remote in remotes:
        _git(repo, "remote", "remove", remote)
        removed.append(f"git remote `{remote}`")
    for key in MERGE_DRIVER_KEYS:
        _git(repo, "config", "--unset-all", key)

    rewritten: list[tuple[str, str]] = []  # (path, what changed)
    if new_attributes is not None and new_attributes != old_attributes:
        attributes.write_text(new_attributes)
        rewritten.append((".gitattributes", "dropped the legacy merge rules"))
    if settings is not None:
        settings_path.write_text(json.dumps(settings, indent=2) + "\n")
        rewritten.append((".claude/settings.json", "dropped hooks run from .claude/hooks/"))

    saved: list[str] = []
    if old_agents:
        saved.append(_save_pre_migration(repo, "AGENTS.md", old_agents))
    (repo / "AGENTS.md").write_text(new_agents)
    rewritten.append(("AGENTS.md", "plugin seed"
                      + (" + preserved project rules" if rules else "")))
    if new_readme is not None:
        saved.append(_save_pre_migration(repo, "README.md", old_readme))
        (repo / "README.md").write_text(new_readme)
        rewritten.append(("README.md", "dropped the template README"))

    # Adopted `.codex/agents/*.toml`: back up the pre-existing (untracked)
    # content before `seed_repo()` below overwrites it with generated content.
    # `.claude/settings.json`/`.gitignore`/`.gitattributes` need no backup
    # here — they are merged, not overwritten, by `seed_repo()`.
    for rel in adopted_overwrite:
        backup_path = repo / PRE_MIGRATION_DIR / "pre-migration" / rel
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path.write_bytes((repo / rel).read_bytes())

    print()
    report = seed_repo(repo, with_tasks=with_tasks, with_artifacts=with_artifacts,
                       with_workbooks=with_workbooks, with_repos=with_repos)
    for rel, status in report:
        print(f"{status:>7}  {rel}")

    print()
    doctor_rc = cmd_doctor(args)

    print("\nat migrate: summary")
    for entry in removed:
        print(f"  removed  {entry}")
    for entry, note in rewritten:
        print(f"  rewrote  {entry} ({note})")
    for entry in kept:
        print(f"  kept     {entry}")
    for entry in saved:
        print(f"  saved    {entry} (local only, gitignored)")
    if rules:
        print(f"  moved    {len(rules.splitlines())} line(s) of project rules into "
              f"AGENTS.md → {DOMAIN_SLOT_HEADING}")
    for line in leftovers:
        print(f"  review   preserved rule still mentions `_base/`: {line}")
    # WARN lines already printed once in the plan block above; the summary
    # does not repeat them.

    if args.commit:
        added = sorted({rel for rel, status in report if status != "kept"}
                       | {rel for rel, _ in rewritten})
        body = "\n".join([
            COMMIT_SUBJECT, "",
            "What changed: dropped the vendored template trees and re-seeded the",
            "downstream-owned contract from the agents-template plugins.",
            "Why: skills, hooks and subagents now install as Claude Code / Codex",
            "plugins instead of being copied into every repository.",
            "Checks: at doctor", "",
            "Removed:", *[f"- {entry}" for entry in removed], "",
            "Added or updated:", *[f"- {entry}" for entry in added], "",
            COMMIT_TRAILER, "",
        ])
        # Never `git add -A`: that would sweep up untracked paths the caller
        # explicitly asked to leave alone (--allow-untracked). Stage tracked
        # changes only, plus the exact paths migrate itself created or merged
        # — force-added (`-f`), since a downstream's own `.gitignore` may
        # ignore a path migrate manages regardless of that local rule (e.g.
        # a `.claude/` or `.codex/` line added outside the managed block).
        if _git(repo, "add", "-u").returncode != 0:
            _git(repo, "reset", "-q")
            die("`git add -u` failed; commit by hand")
        for rel in added:
            if _git(repo, "add", "-f", "--", rel).returncode != 0:
                _git(repo, "reset", "-q")
                die(f"`git add -f -- {rel}` failed; commit by hand")

        # `-z`: NUL-delimited, matching the `-z` porcelain parse above — a
        # staged path is never C-quoted/escaped, so no unescaping is needed.
        staged_out = _git(repo, "diff", "--cached", "--name-only", "-z").stdout
        staged = [entry for entry in staged_out.split("\0") if entry]
        leaked = _leaked_untracked_paths(staged, set(added), untracked_before)
        if leaked:
            _git(repo, "reset", "-q")
            die("refusing to commit: these path(s) were untracked before `at migrate` ran and "
                "must not be swept into the migration commit (unstaged, nothing committed):\n"
                + "\n".join(f"  {path}" for path in leaked))

        commit = subprocess.run(["git", "-C", str(repo), "commit", "-n", "-F", "-"],
                                input=body, text=True, capture_output=True, check=False)
        if commit.returncode != 0:
            die(f"`git commit` failed: {commit.stderr.strip() or commit.stdout.strip()}")
        print(f"\ncommitted {_git_out(repo, 'rev-parse', '--short', 'HEAD')} {COMMIT_SUBJECT}")
    else:
        print("\nnothing committed (re-run with `--commit`, or review and commit by hand)")

    print(f"fill the Project section of AGENTS.md, then re-run `at doctor`. "
          f"Undo with: git reset --hard {backup}")
    if doctor_rc:
        print("at migrate: `at doctor` reported problems above — fix them before pushing",
              file=sys.stderr)
    return 1 if doctor_rc else 0


# --------------------------------------------------------------------------- #
# agents-tasks script wrappers
# --------------------------------------------------------------------------- #

def _run_tasks_script(name: str, extra: list[str]) -> int:
    script = tasks_root() / "skills" / "task-ledger" / "scripts" / name
    if not script.exists():
        die(f"{script} is missing from the installed agents-tasks plugin")
    runner = [sys.executable] if name.endswith(".py") else ["bash"]
    cmd = runner + [str(script), "--root", str(repo_root())] + extra
    return subprocess.run(cmd, check=False).returncode


def cmd_ledger(args: argparse.Namespace) -> int:
    if args.action == "sync":
        extra: list[str] = []
    elif args.action == "check":
        extra = ["--check"]
    else:  # rotate-log
        if not args.task_id:
            die("usage: at ledger rotate-log <TASK_ID>", code=2)
        extra = ["rotate-log", args.task_id]
    return _run_tasks_script("sync_todo_ledgers.py", extra)


def cmd_reserve(args: argparse.Namespace) -> int:
    if not args.rest:
        die("usage: at reserve inbox <slug> | at reserve task <PREFIX> <TYPE> <slug>", code=2)
    return _run_tasks_script("reserve_work_item.sh", list(args.rest))


def cmd_repos_check(args: argparse.Namespace) -> int:
    return _run_tasks_script("check_repos_config.sh", list(args.rest))


def cmd_version(args: argparse.Namespace) -> int:
    print(version())
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="at", description="agents-template CLI: seed, check and install the agent contract.")
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init", help="write the downstream seed into this repo")
    p_init.add_argument("--with-tasks", action="store_true",
                        help="seed docs/tasks_manager, docs/areas and docs/resources")
    p_init.add_argument("--with-artifacts", action="store_true", help="seed artifacts/README.md")
    p_init.add_argument("--with-workbooks", action="store_true", help="seed workbooks/README.md")
    p_init.add_argument("--with-repos", action="store_true", help="seed .config/repos.project.md")
    p_init.add_argument("--all", action="store_true", help="all of the above")
    p_init.set_defaults(func=cmd_init)

    p_doctor = sub.add_parser("doctor", help="check this repo against the contract")
    p_doctor.set_defaults(func=cmd_doctor)

    p_boot = sub.add_parser("bootstrap", help="install the plugins for this machine")
    p_boot.add_argument("--local", metavar="DIR", help="use a local marketplace checkout as source")
    p_boot.add_argument("--claude", action="store_true", help="only set up Claude Code")
    p_boot.add_argument("--codex", action="store_true", help="only set up Codex")
    p_boot.add_argument("--tasks", action="store_true", help="also install agents-tasks")
    p_boot.add_argument("--extras", action="store_true", help="also install agents-extras")
    p_boot.add_argument("--personal", action="store_true", help="also install agents-personal")
    p_boot.add_argument("--clean-global-skills", action="store_true",
                        help="list stale global skill symlinks from the legacy layout")
    p_boot.add_argument("--yes", action="store_true", help="actually remove them")
    p_boot.set_defaults(func=cmd_bootstrap)

    p_migrate = sub.add_parser(
        "migrate", help="convert a legacy `_base/`/`playbooks/` downstream to the plugin layout")
    p_migrate.add_argument("--dry-run", action="store_true",
                           help="print the plan and change nothing (the default)")
    p_migrate.add_argument("--yes", action="store_true", help="actually apply the plan")
    p_migrate.add_argument("--commit", action="store_true",
                           help="commit the migration when it succeeds")
    p_migrate.add_argument("--keep-tasks", action="store_true",
                           help="seed the task ledger even without docs/tasks_manager/_todos")
    p_migrate.add_argument("--no-tasks", action="store_true", help="never seed the task ledger")
    p_migrate.add_argument("--allow-untracked", action="store_true",
                           help="allow a working tree with untracked-only dirtiness (git status "
                                "--porcelain has only `??` entries); --commit never `git add -A`s "
                                "them, it stages only tracked changes and paths migrate itself "
                                "created or merged")
    p_migrate.set_defaults(func=cmd_migrate)

    p_ledger = sub.add_parser("ledger", help="sync | check | rotate-log <TASK_ID>")
    p_ledger.add_argument("action", choices=("sync", "check", "rotate-log"))
    p_ledger.add_argument("task_id", nargs="?")
    p_ledger.set_defaults(func=cmd_ledger)

    p_reserve = sub.add_parser("reserve", help="reserve an inbox idea or task filename")
    p_reserve.add_argument("rest", nargs=argparse.REMAINDER)
    p_reserve.set_defaults(func=cmd_reserve)

    p_repos = sub.add_parser("repos-check", help="validate .config/repos.project.md")
    p_repos.add_argument("rest", nargs=argparse.REMAINDER)
    p_repos.set_defaults(func=cmd_repos_check)

    p_version = sub.add_parser("version", help="print the agents-core plugin version")
    p_version.set_defaults(func=cmd_version)
    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help(sys.stderr)
        return 2
    if args.command == "init" and args.all:
        args.with_tasks = args.with_artifacts = args.with_workbooks = args.with_repos = True
    return args.func(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        raise SystemExit(130)
