"""`at migrate` — move a repository from the pre-1.0 copied template to the plugins.

One-off conversion code: it removes the template's copied skills, agents, hooks and merge rules,
keeps what the project added, and seeds the plugin layout. Everything it shares with the rest of the
CLI (repo and plugin roots, seeding, the doctor checks) comes in as `core`, the `at` module itself.

Python 3 stdlib only. Imported by lib/at.py; do not run directly.
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


def die(message: str, code: int = 1) -> None:
    print(f"at: {message}", file=sys.stderr)
    raise SystemExit(code)

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
    path = Path(__file__).resolve().parent / "legacy-agents-md.txt"
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


def cmd_migrate(args: argparse.Namespace, core) -> int:
    repo = core.repo_root()
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
                          for toml in sorted((core.core_root() / "codex" / "agents").glob("*.toml"))]
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
    if (with_tasks or with_artifacts or with_workbooks or with_repos) and core.find_tasks_root() is None:
        die("this repo needs the agents-tasks seed (task ledger, artifacts, workbooks or repo "
            "registry) but agents-tasks is not installed "
            "(Claude: claude plugin install agents-tasks@agents-template; "
            "Codex: codex plugin add agents-tasks@agents-template; or set AT_TASKS_ROOT)")

    remotes = template_remotes(repo)
    old_agents = (repo / "AGENTS.md").read_text() if (repo / "AGENTS.md").exists() else ""
    old_readme = (repo / "README.md").read_text() if (repo / "README.md").exists() else ""
    new_readme = migrate_readme(old_readme, repo.name) if old_readme else None
    rules, warnings = preserved_project_rules(old_agents) if old_agents else ("", [])
    leftovers: list[str] = []
    if rules:
        rules, leftovers = rewrite_legacy_paths(rules)
    seed_agents = (core.core_root() / "seed" / "AGENTS.md").read_text()
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
            ".claude/settings.json, .codex/agents/, docs/_plans/, a local .caveman.json)")
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
    # content before `core.seed_repo()` below overwrites it with generated content.
    # `.claude/settings.json`/`.gitignore`/`.gitattributes` need no backup
    # here — they are merged, not overwritten, by `core.seed_repo()`.
    for rel in adopted_overwrite:
        backup_path = repo / PRE_MIGRATION_DIR / "pre-migration" / rel
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path.write_bytes((repo / rel).read_bytes())

    print()
    report = core.seed_repo(repo, with_tasks=with_tasks, with_artifacts=with_artifacts,
                       with_workbooks=with_workbooks, with_repos=with_repos)
    for rel, status in report:
        print(f"{status:>7}  {rel}")

    print()
    doctor_rc = core._print_doctor_findings(core._repo_doctor_findings(repo))

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
        added = sorted({rel for rel, status in report
                        if status != "kept" and rel not in core.LOCAL_ONLY_SEED_PATHS}
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
