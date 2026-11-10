#!/usr/bin/env python3
"""`at` — the agents-template CLI.

Subcommands:
  init         write the downstream seed into this repo (idempotent, never clobbers)
  doctor       check that this repo still matches the contract
  bootstrap    install the plugins into this machine's harnesses, write ~/.local/bin/at
  migrate      convert a legacy `_base/`/`playbooks/` downstream to the plugin layout
  ledger       wrapper: `sync` | `check` | `rotate-log <TASK_ID>|--all`
  task         `brief <TASK_ID> --phase N` | `run-state init|check <TASK_ID>` | `run <TASK_ID>` (scripted execute-plan) | `size <TASK_ID> --phase N|--final`
  addon        `list` | `status` | `enable <name>...` | `disable <name>...`: optional tools per repo
  reserve      wrapper: reserve an inbox idea or task filename
  repos-check  wrapper: validate `.config/repos.project.md`
  seed-path    print the active agents-core seed AGENTS.md path
  version      print the agents-core plugin version

Exit codes: 0 ok, 1 errors, 2 usage. Python 3 stdlib only, no third-party imports.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Sibling modules (task_run, task_size, peer, addons, migrate) are imported lazily by name. Running
# this file puts lib/ on sys.path already; loading it another way (the tests use importlib) does not.
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

MARKETPLACE = "agents-template"
DEFAULT_SOURCE = "toderian/project_template"
# Companion plugin: installed next to the marketplace on every bootstrap/update and enabled by
# the seed settings, never vendored. Claude installs it as a plugin from its own marketplace;
# Codex has no marketplace for it, so the skill goes in through the `skills` CLI (needs npx).
CAVEMAN_REPO = "JuliusBrussee/caveman"
CAVEMAN_MARKETPLACE = "caveman"
CAVEMAN_PLUGIN = f"caveman@{CAVEMAN_MARKETPLACE}"
CAVEMAN_SKILL = "caveman"
# The `skills` CLI (npm) that installs SKILL.md bundles for Codex. Pinned to a major so `npx`
# neither prompts to install it (`--yes`) nor silently picks up a breaking release.
SKILLS_CLI = "skills@1"
# Seed files that stay local: written by `at init` for the developer to edit, ignored by the
# managed .gitignore block, and never staged by `at migrate --commit`.
LOCAL_ONLY_SEED_PATHS = frozenset({".caveman.json"})
BEGIN_MARKER = "# BEGIN agents-template"
END_MARKER = "# END agents-template"
MAX_AGENTS_MD_LINES = 200
# The project-slot form in the seed AGENTS.md. Only this exact opener counts as an
# unfilled slot, so prose that merely mentions the token does not keep doctor warning.
TODO_SLOT_MARKER = "<!-- TODO-FILL"

RESOLVER = r"""#!/usr/bin/env bash
# Resolver written by `at bootstrap` (agents-template). Safe to re-run.
# Prefers the newest installed plugin cache version across Claude and Codex,
# then the Codex marketplace checkout, then $AT_DEV_ROOT for development.
set -u

newest_plugin_cache() {
  python3 - "$HOME" <<'PY'
import pathlib, re, sys
home = pathlib.Path(sys.argv[1])
candidates = []
for harness, priority in ((".codex", 0), (".claude", 1)):
    base = home / harness / "plugins" / "cache" / "agents-template" / "agents-core"
    if not base.is_dir():
        continue
    for version in base.iterdir():
        executable = version / "bin" / "at"
        if version.is_dir() and executable.is_file():
            key = tuple(int(part) for part in re.findall(r"\d+", version.name)) or (0,)
            candidates.append((key, priority, str(executable)))
if candidates:
    print(max(candidates)[2])
PY
}

candidates=()
cached="$(newest_plugin_cache)" && [ -n "$cached" ] && candidates+=("$cached")
candidates+=("$HOME/.codex/.tmp/marketplaces/agents-template/plugins/agents-core/bin/at")
[ -n "${AT_DEV_ROOT:-}" ] && candidates+=("$AT_DEV_ROOT/plugins/agents-core/bin/at")

for candidate in "${candidates[@]}"; do
  [ -x "$candidate" ] && exec "$candidate" "$@"
done

echo "at: agents-core not installed (Claude: claude plugin install agents-core@agents-template; Codex: codex plugin add agents-core@agents-template)" >&2
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


def _run_capture(cmd: list[str], timeout: int = 15) -> subprocess.CompletedProcess | None:
    """Run a read-only harness query and return None when it cannot be executed."""
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True, check=False, timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def _run_json(cmd: list[str]) -> object | None:
    proc = _run_capture(cmd)
    if proc is None or proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def cached_plugins_for_harness(harness: str, home: Path | None = None) -> dict[str, list[str]]:
    """Return versioned agents-template cache entries for one harness."""
    if harness not in {"claude", "codex"}:
        raise ValueError(f"unknown harness: {harness}")
    home = home or Path.home()
    cache = home / f".{harness}" / "plugins" / "cache" / MARKETPLACE
    found: dict[str, list[str]] = {}
    if not cache.is_dir():
        return found
    for plugin in sorted(path for path in cache.iterdir() if path.is_dir()):
        versions = sorted(
            (version.name for version in plugin.iterdir() if version.is_dir()),
            key=_version_key,
        )
        if versions:
            found[plugin.name] = versions
    return found


def cli_plugin_inventory(harness: str) -> dict[str, dict] | None:
    """Installed plugins reported by a harness, or None when the query failed."""
    if harness == "claude":
        data = _run_json(["claude", "plugin", "list", "--json"])
        if not isinstance(data, list):
            return None
        records = data
        out = {}
        for record in records:
            if not isinstance(record, dict):
                continue
            plugin_id = str(record.get("id", ""))
            if not plugin_id.endswith(f"@{MARKETPLACE}"):
                continue
            name = plugin_id.rsplit("@", 1)[0]
            current = out.get(name)
            version_name = str(record.get("version", ""))
            if current is None or _version_key(version_name) > _version_key(str(current.get("version", ""))):
                out[name] = {
                    "version": version_name,
                    "enabled": record.get("enabled") is True,
                    "install_path": record.get("installPath"),
                }
        return out
    if harness == "codex":
        data = _run_json(["codex", "plugin", "list", "--json"])
        if not isinstance(data, dict) or not isinstance(data.get("installed"), list):
            return None
        records = data["installed"]
        out = {}
        for record in records:
            if not isinstance(record, dict) or record.get("marketplaceName") != MARKETPLACE:
                continue
            name = str(record.get("name", ""))
            if not name:
                continue
            marketplace_source = record.get("marketplaceSource")
            out[name] = {
                "version": str(record.get("version", "")),
                "enabled": record.get("enabled") is True,
                "installed": record.get("installed") is True,
                "source_type": (
                    marketplace_source.get("sourceType")
                    if isinstance(marketplace_source, dict) else None
                ),
            }
        return out
    raise ValueError(f"unknown harness: {harness}")


def find_tasks_root() -> Path | None:
    """Locate the installed agents-tasks plugin root, or None.

    Order: $AT_TASKS_ROOT; a sibling plugin dir in a source checkout; then the
    newest semantic version across both harness caches (Claude wins a version tie);
    finally the cache sibling resolved relative to this file, which keeps working
    when the harness cache does not live under $HOME (CLAUDE_CONFIG_DIR, CODEX_HOME).
    """
    env = os.environ.get("AT_TASKS_ROOT")
    if env:
        path = Path(env).expanduser()
        return path if (path / "skills").is_dir() else None
    sibling = core_root().parent / "agents-tasks"
    if (sibling / "skills").is_dir():
        return sibling
    home = Path.home()
    candidates = []
    for harness in ("codex", "claude"):
        versions = cached_plugins_for_harness(harness, home).get("agents-tasks", [])
        for installed_version in versions:
            candidate = (
                home / f".{harness}" / "plugins" / "cache" / MARKETPLACE
                / "agents-tasks" / installed_version
            )
            if (candidate / "skills").is_dir():
                candidates.append((
                    _version_key(installed_version), harness == "claude", candidate,
                ))
    if candidates:
        return max(candidates, key=lambda item: (item[0], item[1]))[2]
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
            "(Claude: claude plugin install agents-tasks@agents-template; "
            "Codex: codex plugin add agents-tasks@agents-template; "
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


# `permissions` lists `at init` unions the seed's rules into, and `at doctor` checks.
MANAGED_PERMISSION_LISTS = ("deny", "ask")


def missing_permission_rules(settings: dict, seed_json: dict) -> list[str]:
    """Seed `permissions.deny` / `.ask` rules the repo's settings do not carry, as `kind: rule`."""
    have = settings.get("permissions")
    have = have if isinstance(have, dict) else {}
    missing = []
    for kind in MANAGED_PERMISSION_LISTS:
        current = have.get(kind)
        current = current if isinstance(current, list) else []
        for rule in (seed_json.get("permissions") or {}).get(kind) or []:
            if rule not in current:
                missing.append(f"{kind}: {rule}")
    return missing


def merge_settings_json(dst_path: Path, seed_json: dict) -> str:
    """Deep-merge only the keys this template manages; never drop user keys.

    Managed: `extraKnownMarketplaces` and `enabledPlugins` (missing keys added),
    `permissions.deny` and `permissions.ask` (union, existing order kept; retired
    deny rules dropped),
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

    for kind in MANAGED_PERMISSION_LISTS:
        wanted_rules = (seed_json.get("permissions") or {}).get(kind) or []
        if not wanted_rules:
            continue
        permissions = data.setdefault("permissions", {})
        if not isinstance(permissions, dict):
            die(f"{dst_path}: fix by hand: `permissions` must be a JSON object")
        current = permissions.setdefault(kind, [])
        if not isinstance(current, list):
            die(f"{dst_path}: fix by hand: `permissions.{kind}` must be a list")
        for rule in wanted_rules:
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

    # local caveman switch: gitignored, edited (never committed) to turn terse mode off. Seeded
    # with a null mode so it inherits the user-level config (caveman's own default is "full")
    # instead of overriding a machine-wide opt-out.
    report.append((".caveman.json", write_seed_file(
        seed / "caveman.json", repo / ".caveman.json", overwrite=False)))

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

# Skill ids deleted from the plugins; `at doctor` warns while a downstream AGENTS.md still routes
# to one. Append, never remove (the successor is documented in adopting-updates.md §"Removed skill ids").
REMOVED_SKILL_IDS = (
    "agents-core:grill-me", "agents-extras:grill-with-docs", "agents-core:research",
    "agents-core:task-spec-workflow", "agents-tasks:prd-to-plan",
)

# A ledger warning repeated for at least this many tasks prints as one doctor line.
LEDGER_GROUP_MIN = 4


def _group_ledger_warnings(warnings: list[str]) -> list[str]:
    """Collapse warnings that differ only in the task they name.

    `at ledger check` prints one line per task; a repo with a hundred oversized
    tasks would bury every other finding. Lines are keyed by their text with
    quoted names, task ids and task-file paths masked; a key seen
    LEDGER_GROUP_MIN times or more becomes one line with a count and three
    examples, placed where its first member was. Everything else is unchanged.
    """
    def key_of(line: str) -> str:
        key = re.sub(r"'[^']*'", "'…'", line)
        key = re.sub(r"docs/tasks_manager/\S+", "<file>", key)
        return re.sub(r"\b[A-Z][A-Z0-9]*-[0-9]{3,}\b", "<ID>", key)

    groups: dict[str, list[str]] = {}
    for line in warnings:
        groups.setdefault(key_of(line), []).append(line)
    out, done = [], set()
    for line in warnings:
        key = key_of(line)
        members = groups[key]
        if len(members) < LEDGER_GROUP_MIN:
            out.append(line)
        elif key not in done:
            done.add(key)
            names = [m.group(1) for m in (re.search(r"'([^']*)'", member) for member in members) if m]
            examples = f" (e.g. {', '.join(names[:3])})" if names else ""
            out.append(f"{len(members)} × {key}{examples}")
    return out


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
    for text in _group_ledger_warnings([line[len("WARNING:"):].strip() for line in warnings]):
        findings.append(("WARN", f"ledger: {text}"))
    if proc.returncode != 0:
        problems = [line for line in messages if not line.startswith("WARNING:")]
        for line in problems:
            findings.append(("ERROR", f"ledger: {line}"))
        if not problems:
            findings.append(("ERROR", "ledger: `at ledger check` failed"))
    elif not warnings:
        findings.append(("OK", "task ledgers are valid"))


def routing_rows(text: str) -> list[str]:
    """The `## Routing table` body rows of an AGENTS.md, in order (header rows included)."""
    rows, inside = [], False
    for line in text.splitlines():
        if line.startswith("## Routing table"):
            inside = True
            continue
        if inside and line.startswith("## "):
            break
        if inside and line.startswith("|"):
            rows.append(line.strip())
    return rows


def routing_keys(rows: list[str]) -> list[str]:
    """The first cell of each routing row: the 'Your task' key. Separators dropped."""
    keys = []
    for row in rows:
        cells = [c.strip() for c in row.strip("|").split("|")]
        if not cells or not cells[0] or set(cells[0]) <= set("-: "):
            continue
        keys.append(cells[0])
    return keys


def seed_drift(repo_agents_md: str) -> tuple[str, list[str]]:
    """Compare a repo's routing table against the plugin seed's.

    Returns (status, detail) where status is one of:
      "current"  — the repo routes every row the seed does
      "behind"   — detail lists the seed row keys the repo is missing
      "none"     — the repo has no routing table at all
      "unknown"  — the plugin ships no seed to compare against
    """
    seed = core_root() / "seed" / "AGENTS.md"
    if not seed.is_file():
        return ("unknown", [])
    wanted = routing_keys(routing_rows(seed.read_text()))
    if not wanted:
        return ("unknown", [])
    have = set(routing_keys(routing_rows(repo_agents_md)))
    if not have:
        return ("none", [])
    missing = [key for key in wanted if key not in have]
    return ("behind", missing) if missing else ("current", [])


def _repo_doctor_findings(repo: Path) -> list[tuple[str, str]]:
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
                                     "(see the `agents-core:setup-project` skill)"))
        else:
            findings.append(("OK", "AGENTS.md project slots are filled"))
        status, missing = seed_drift(text)
        if status == "behind":
            findings.append(("WARN", f"AGENTS.md routing table is {len(missing)} row(s) behind the "
                                     f"plugin seed: {'; '.join(missing)} "
                                     "(run the agents-core:setup-project skill to adopt them)"))
        elif status == "current":
            findings.append(("OK", "AGENTS.md routing table matches the plugin seed"))
        removed = [sid for sid in REMOVED_SKILL_IDS if f"`{sid}`" in text or f"/{sid}" in text or f"${sid}" in text]
        if removed:
            findings.append(("WARN", f"AGENTS.md routes to a removed skill: {', '.join(removed)} "
                                     "(successors: agents-core:setup-project references/adopting-updates.md "
                                     "§\"Removed skill ids\")"))

    legacy = [name for name in ("_base", "playbooks") if (repo / name).is_dir()]
    if legacy:
        findings.append(("ERROR", f"legacy template layout: {', '.join(name + '/' for name in legacy)} "
                                  "still present — run `at migrate`"))
    else:
        findings.append(("OK", "no legacy `_base/` or `playbooks/` tree"))

    settings_path = repo / ".claude" / "settings.json"
    try:
        seed_settings = json.loads((core_root() / "seed" / "settings.json").read_text())
    except (OSError, ValueError):
        seed_settings = {}  # incomplete plugin cache: fall back to the one plugin that must exist
    wanted_plugins = sorted(seed_settings.get("enabledPlugins") or {f"agents-core@{MARKETPLACE}": True})
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
            enabled = settings.get("enabledPlugins") or {}
            for key in wanted_plugins:
                if enabled.get(key) is True:
                    findings.append(("OK", f"{key} is enabled in .claude/settings.json"))
                else:
                    findings.append(("WARN", f"{key} is not enabled in .claude/settings.json "
                                             "(run `at init`)"))
            missing_rules = missing_permission_rules(settings, seed_settings)
            if missing_rules:
                findings.append(("WARN", f".claude/settings.json is missing {len(missing_rules)} seed "
                                         f"permission rule(s): {'; '.join(missing_rules)} "
                                         "(run `at init`)"))
            elif seed_settings.get("permissions"):
                findings.append(("OK", ".claude/settings.json carries the seed permission rules"))

    import peer  # lib/peer.py, next to this file
    findings.extend(peer.doctor_findings(repo))  # nothing unless this checkout enabled peer checks
    import addons  # lib/addons.py, next to this file
    findings.extend(addons.doctor_findings(repo))  # nothing unless the repo enabled an add-on

    if (repo / "docs" / "tasks_manager").is_dir():
        _ledger_findings(repo, findings)

    return findings


def _active_cached_plugin_root(harness: str, plugin: str, home: Path | None = None) -> Path | None:
    home = home or Path.home()
    versions = cached_plugins_for_harness(harness, home).get(plugin, [])
    if not versions:
        return None
    return home / f".{harness}" / "plugins" / "cache" / MARKETPLACE / plugin / versions[-1]


def _plugin_root_from_record(
    harness: str, plugin: str, record: dict, home: Path | None = None,
) -> Path | None:
    """Resolve the cache payload that corresponds to a harness inventory record."""
    home = home or Path.home()
    install_path = record.get("install_path")
    if install_path:
        return Path(str(install_path))
    installed_version = str(record.get("version", ""))
    if installed_version:
        return (
            home / f".{harness}" / "plugins" / "cache" / MARKETPLACE
            / plugin / installed_version
        )
    return _active_cached_plugin_root(harness, plugin, home)


def _cache_payload_missing(root: Path | None, harness: str, plugin: str) -> list[str]:
    """Return missing or unusable files from one installed plugin payload."""
    manifest = ".claude-plugin/plugin.json" if harness == "claude" else ".codex-plugin/plugin.json"
    required_files = [manifest]
    required_dirs = ["skills"]
    if plugin == "agents-core":
        required_files.extend(["bin/at", "lib/at.py", "seed/AGENTS.md"])
        required_files.append(
            "hooks/hooks.json" if harness == "claude" else "hooks/hooks.codex.json"
        )
        if harness == "codex":
            required_dirs.append("codex/agents")
    missing = [rel for rel in required_files if root is None or not (root / rel).is_file()]
    missing.extend(rel for rel in required_dirs if root is None or not (root / rel).is_dir())
    if root is not None and (root / "bin/at").is_file() and not os.access(root / "bin/at", os.X_OK):
        missing.append("bin/at (not executable)")
    return missing


def _runtime_findings(repo: Path, harness: str, strict: bool) -> list[tuple[str, str]]:
    """Machine/runtime checks. Advisory mode returns only actionable warnings."""
    findings: list[tuple[str, str]] = []
    issue = "ERROR" if strict else "WARN"
    if shutil.which(harness) is None:
        findings.append((issue, f"{harness} CLI is not on PATH"))
        return findings
    if strict:
        findings.append(("OK", f"{harness} CLI is on PATH"))

    inventory = cli_plugin_inventory(harness)
    if inventory is None:
        findings.append((issue, f"could not query the {harness} plugin inventory"))
        return findings
    core = inventory.get("agents-core")
    if core is None:
        findings.append((issue, f"agents-core@{MARKETPLACE} is not installed in {harness}"))
        return findings
    if not core.get("enabled"):
        findings.append((issue, f"agents-core@{MARKETPLACE} is disabled in {harness}"))
    elif strict:
        findings.append(("OK", f"agents-core@{MARKETPLACE} is installed and enabled in {harness}"))

    if harness == "codex":
        marketplaces = _run_json(["codex", "plugin", "marketplace", "list", "--json"])
        records = marketplaces.get("marketplaces", []) if isinstance(marketplaces, dict) else []
        configured = any(
            isinstance(record, dict) and record.get("name") == MARKETPLACE for record in records
        )
        if not configured:
            findings.append((issue, f"{MARKETPLACE} marketplace is not configured in Codex"))
        elif strict:
            findings.append(("OK", f"{MARKETPLACE} marketplace is configured in Codex"))

    cache_root = _plugin_root_from_record(harness, "agents-core", core)
    missing = _cache_payload_missing(cache_root, harness, "agents-core")
    if missing:
        findings.append((issue, f"{harness} agents-core cache is incomplete: {', '.join(missing)}"))
    elif strict:
        findings.append(("OK", f"{harness} agents-core cache payload is complete"))

    if shutil.which("jq") is None:
        findings.append((issue, f"jq is required by the {harness} agents-core hooks"))
    elif strict:
        findings.append(("OK", "jq is available for plugin hooks"))

    if harness == "claude":
        if shutil.which("node") is None:
            findings.append(("WARN", f"node is required by the {CAVEMAN_PLUGIN} hooks"))
        elif strict:
            findings.append(("OK", f"node is available for the {CAVEMAN_PLUGIN} hooks"))

    if harness == "codex":
        codex_skill = Path.home() / ".codex" / "skills" / CAVEMAN_SKILL / "SKILL.md"
        if codex_skill.is_file():
            if strict:
                findings.append(("OK", f"the {CAVEMAN_SKILL} companion skill is installed for Codex"))
        elif shutil.which("npx") is None:
            findings.append(("WARN", f"npx is required to install the {CAVEMAN_SKILL} companion skill "
                                     "for Codex (install Node, then `at update --codex`)"))
        else:
            findings.append(("WARN", f"the {CAVEMAN_SKILL} companion skill is not installed for Codex "
                                     f"({codex_skill}; run `at update --codex`)"))

        expected_agents = sorted(path.name for path in (core_root() / "codex/agents").glob("*.toml"))
        agent_root = (
            core_root() / "codex/agents"
            if repo == core_root().parents[1]
            else repo / ".codex/agents"
        )
        missing_agents = [name for name in expected_agents if not (agent_root / name).is_file()]
        if not expected_agents:
            findings.append((issue, "Codex role source list is empty in agents-core"))
        elif missing_agents:
            findings.append((issue, f"Codex role files are missing: {', '.join(missing_agents)}"))
        elif strict:
            findings.append(("OK", f"all {len(expected_agents)} Codex role files are present"))
    return findings


def _print_doctor_findings(findings: list[tuple[str, str]]) -> int:

    for level, message in findings:
        print(f"{level:<5} {message}")
    errors = sum(1 for level, _ in findings if level == "ERROR")
    warns = sum(1 for level, _ in findings if level == "WARN")
    print(f"at doctor: {len(findings) - errors - warns} ok, {warns} warning(s), {errors} problem(s)")
    return 1 if errors else 0


def drift_items(repo: Path) -> list[str]:
    """What a seeded repo lacks compared with the installed plugin seed, as short phrases.

    The fast subset of `at doctor` behind `--drift`: no ledger check and no
    runtime check, so a session-start hook can afford it. Empty for a repo that
    is current, and for one that was never seeded (no routing table to compare).
    """
    agents_md = repo / "AGENTS.md"
    if not agents_md.is_file():
        return []
    text = agents_md.read_text()
    status, missing = seed_drift(text)
    if status in ("none", "unknown"):
        return []
    items = []
    if status == "behind":
        items.append(f"{len(missing)} routing row(s)")
    removed = [sid for sid in REMOVED_SKILL_IDS if f"`{sid}`" in text or f"/{sid}" in text or f"${sid}" in text]
    if removed:
        items.append(f"{len(removed)} removed skill id(s)")
    legacy = [name + "/" for name in ("_base", "playbooks") if (repo / name).is_dir()]
    if legacy:
        items.append(f"legacy {', '.join(legacy)}")
    try:
        seed_settings = json.loads((core_root() / "seed" / "settings.json").read_text())
        settings = json.loads((repo / ".claude" / "settings.json").read_text() or "{}")
    except (OSError, ValueError):
        return items
    if not isinstance(settings, dict):
        return items
    enabled = settings.get("enabledPlugins") or {}
    plugins = [key for key in sorted(seed_settings.get("enabledPlugins") or {}) if enabled.get(key) is not True]
    if plugins:
        items.append(f"{len(plugins)} seed plugin(s) not enabled")
    rules = missing_permission_rules(settings, seed_settings)
    if rules:
        items.append(f"{len(rules)} permission rule(s)")
    return items


def cmd_doctor_drift() -> int:
    """`at doctor --drift`: one line when the repo is behind the seed, nothing otherwise. Always 0."""
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, check=False)
        if out.returncode != 0 or not out.stdout.strip():
            return 0
        items = drift_items(Path(out.stdout.strip()).resolve())
    except (OSError, ValueError):
        return 0
    if items:
        print(f"agents-template: this repo is behind the plugin seed ({'; '.join(items)}). "
              "Run `at doctor` for the detail and the agents-core:setup-project skill to adopt it.")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    if getattr(args, "drift", False):
        return cmd_doctor_drift()
    repo = repo_root()
    findings = _repo_doctor_findings(repo)
    strict_harnesses = []
    if getattr(args, "all_harnesses", False):
        strict_harnesses = ["claude", "codex"]
    elif getattr(args, "claude", False):
        strict_harnesses = ["claude"]
    elif getattr(args, "codex", False):
        strict_harnesses = ["codex"]
    if strict_harnesses:
        for harness in strict_harnesses:
            findings.extend(_runtime_findings(repo, harness, strict=True))
    return _print_doctor_findings(findings)


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


def claude_plugin_installed(plugin_id: str) -> bool:
    """Whether `claude plugin list` reports `plugin_id` installed at user scope.

    Project-scoped rows (a `.claude/settings.json` elsewhere) do not count: the
    machine-level install is what bootstrap/update maintain.
    """
    data = _run_json(["claude", "plugin", "list", "--json"])
    if not isinstance(data, list):
        return False
    return any(
        isinstance(r, dict) and str(r.get("id", "")) == plugin_id
        and r.get("scope") in (None, "user")
        for r in data
    )


def companion_commands(harness: str, installed: bool = False) -> list[list[str]]:
    """Commands that install (or, when `installed`, refresh) the caveman companion."""
    if harness == "claude":
        if installed:
            return [["claude", "plugin", "marketplace", "update", CAVEMAN_MARKETPLACE],
                    ["claude", "plugin", "update", CAVEMAN_PLUGIN]]
        return [["claude", "plugin", "marketplace", "add", CAVEMAN_REPO],
                ["claude", "plugin", "install", CAVEMAN_PLUGIN]]
    if harness == "codex":
        # idempotent: re-adding refreshes the copy under ~/.codex/skills. `--yes` answers
        # npx's own "install skills?" prompt; the trailing `-y` is the skills CLI's.
        return [["npx", "--yes", SKILLS_CLI, "add", CAVEMAN_REPO, "--skill", CAVEMAN_SKILL,
                 "-g", "-a", "codex", "-y"]]
    raise ValueError(f"unknown harness: {harness}")


def _install_companions(harness: str) -> str:
    """Install or refresh the companion for `harness`.

    Returns 'installed', 'skipped' (tooling missing) or 'failed'. The companion is optional,
    so its outcome is reported but never fails bootstrap/update.
    """
    if harness == "codex" and shutil.which("npx") is None:
        print(f"at: npx is not on PATH — the {CAVEMAN_SKILL} skill for Codex was skipped "
              "(install Node, then re-run `at update --codex`)", file=sys.stderr)
        return "skipped"
    installed = harness == "claude" and claude_plugin_installed(CAVEMAN_PLUGIN)
    for command in companion_commands(harness, installed):
        if not _run(command):
            return "failed"
    return "installed"


def _print_companion_report(outcomes: dict[str, str]) -> None:
    for harness, status in outcomes.items():
        print(f"companion {CAVEMAN_PLUGIN} ({CAVEMAN_REPO}) for {harness}: {status}")


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
    companions: dict[str, str] = {}
    if want_claude:
        failures += not _run(["claude", "plugin", "marketplace", "add", source])
        for name in names:
            failures += not _run(["claude", "plugin", "install", f"{name}@{MARKETPLACE}"])
        companions["claude"] = _install_companions("claude")
    if want_codex:
        failures += not _run(["codex", "plugin", "marketplace", "add", source])
        for name in names:
            failures += not _run(["codex", "plugin", "add", f"{name}@{MARKETPLACE}"])
        companions["codex"] = _install_companions("codex")

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

    print()
    _print_companion_report(companions)
    print("Other third-party plugins are installed from their own marketplaces the same way, e.g.:")
    print("  claude plugin marketplace add obra/superpowers-marketplace")
    print("  claude plugin install superpowers@superpowers-marketplace")
    return 1 if failures else 0


# --------------------------------------------------------------------------- #
# at update
# --------------------------------------------------------------------------- #

def installed_plugins(home: Path | None = None) -> dict[str, dict[str, list[str]]]:
    """Cached agents-template plugins, kept separate by harness."""
    return {
        harness: cached_plugins_for_harness(harness, home)
        for harness in ("claude", "codex")
    }


def _command_supported(cmd: list[str]) -> bool:
    proc = _run_capture([*cmd, "--help"])
    return proc is not None and proc.returncode == 0


def codex_update_commands(
    plugin_names: list[str], source_type: str,
    supports=None,
) -> list[list[str]]:
    """Build the supported Codex refresh/reinstall command sequence."""
    supports = supports or _command_supported
    commands: list[list[str]] = []
    if source_type == "git":
        upgrade = ["codex", "plugin", "marketplace", "upgrade", MARKETPLACE]
        legacy_update = ["codex", "plugin", "marketplace", "update", MARKETPLACE]
        if supports(upgrade[:-1]):
            commands.append(upgrade)
        elif supports(legacy_update[:-1]):
            commands.append(legacy_update)
        else:
            raise ValueError("Codex supports neither marketplace upgrade nor marketplace update")
    elif source_type != "local":
        raise ValueError(f"unsupported Codex marketplace source type: {source_type or 'unknown'}")
    commands.extend(
        ["codex", "plugin", "add", f"{name}@{MARKETPLACE}"] for name in plugin_names
    )
    return commands


def codex_marketplace_source_type() -> str | None:
    data = _run_json(["codex", "plugin", "marketplace", "list", "--json"])
    records = data.get("marketplaces", []) if isinstance(data, dict) else []
    for record in records:
        if not isinstance(record, dict) or record.get("name") != MARKETPLACE:
            continue
        source = record.get("marketplaceSource")
        if isinstance(source, dict):
            source_type = source.get("sourceType")
            return str(source_type) if source_type else None
    return None


def _verify_codex_cache(plugin_names: list[str]) -> list[str]:
    """Return verification problems after a Codex reinstall."""
    problems = []
    inventory = cli_plugin_inventory("codex")
    if inventory is None:
        return ["could not query the Codex plugin inventory"]
    for name in plugin_names:
        record = inventory.get(name)
        if record is None or not record.get("installed") or not record.get("enabled"):
            problems.append(f"{name}: Codex does not report it installed and enabled")
            continue
        root = _plugin_root_from_record("codex", name, record)
        missing = _cache_payload_missing(root, "codex", name)
        if missing:
            problems.append(f"{name}: cache missing {', '.join(missing)}")
    return problems


def cmd_update(args: argparse.Namespace) -> int:
    """Refresh the marketplace and update every installed plugin from it."""
    cached = installed_plugins()
    reported = {
        harness: cli_plugin_inventory(harness) if shutil.which(harness) else None
        for harness in ("claude", "codex")
    }
    names = {
        harness: sorted(
            reported[harness] if reported[harness] is not None else cached[harness]
        )
        for harness in ("claude", "codex")
    }
    if not any(names.values()):
        print(f"at update: no {MARKETPLACE} plugins are installed on this machine.")
        print("Install them first: at bootstrap")
        return 1

    running = version()
    print(f"agents-core shipping this `at`: {running}")
    for harness in ("claude", "codex"):
        if not names[harness]:
            continue
        print(f"  {harness}:")
        for name in names[harness]:
            versions = cached[harness].get(name, [])
            live_inventory = reported[harness] or {}
            reported_version = str(live_inventory.get(name, {}).get("version", ""))
            display_version = reported_version or (versions[-1] if versions else "?")
            other_versions = [item for item in versions if item != display_version]
            extra = (
                f"  (also cached: {', '.join(other_versions)})"
                if other_versions else ""
            )
            print(f"    {name:<16} {display_version}{extra}")

    if args.check:
        print("\nat update --check: read-only. Run `at update` to refresh the marketplace and "
              "update these plugins, then restart the CLI to load them.")
        print("For the repo side: `at doctor` reports routing-table drift; "
              "agents-core:setup-project adopts it.")
        return 0

    want_claude, want_codex = args.claude, args.codex
    if not want_claude and not want_codex:
        want_claude = bool(names["claude"] and shutil.which("claude"))
        want_codex = bool(names["codex"] and shutil.which("codex"))
    selected = [
        harness for harness, wanted in (("claude", want_claude), ("codex", want_codex)) if wanted
    ]
    if not selected:
        print("at update: cached plugins exist, but no configured harness CLI is available.", file=sys.stderr)
        return 1

    failures = 0
    companions: dict[str, str] = {}
    if want_claude:
        if shutil.which("claude") is None or not names["claude"]:
            print("at update: --claude requested, but no Claude agents-template installation was found.",
                  file=sys.stderr)
            failures += 1
        else:
            failures += not _run(["claude", "plugin", "marketplace", "update", MARKETPLACE])
            for name in names["claude"]:
                failures += not _run(["claude", "plugin", "update", f"{name}@{MARKETPLACE}"])
            companions["claude"] = _install_companions("claude")
    if want_codex:
        if shutil.which("codex") is None or not names["codex"]:
            print("at update: --codex requested, but no Codex agents-template installation was found.",
                  file=sys.stderr)
            failures += 1
        else:
            source_types = {
                str(record.get("source_type")) for record in (reported["codex"] or {}).values()
                if record.get("source_type")
            }
            if not source_types:
                fallback_source_type = codex_marketplace_source_type()
                if fallback_source_type:
                    source_types.add(fallback_source_type)
            if len(source_types) != 1:
                print("at update: could not determine one Codex marketplace source type.", file=sys.stderr)
                failures += 1
            else:
                try:
                    commands = codex_update_commands(names["codex"], source_types.pop())
                except ValueError as exc:
                    print(f"at update: {exc}", file=sys.stderr)
                    failures += 1
                else:
                    codex_failed = False
                    for command in commands:
                        if not _run(command):
                            failures += 1
                            codex_failed = True
                            break
                    if not codex_failed:
                        problems = _verify_codex_cache(names["codex"])
                        for problem in problems:
                            print(f"at update: Codex verification failed: {problem}", file=sys.stderr)
                        failures += len(problems)
                        companions["codex"] = _install_companions("codex")

    print()
    _print_companion_report(companions)
    print("Restart the CLI to load the updated plugins — a running session keeps the old ones.")
    print("Then, in each downstream repo: `at doctor` reports routing-table drift, and "
          "agents-core:setup-project adopts it.")
    return 1 if failures else 0


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
    if args.action != "rotate-log" and args.all:
        die("usage: `--all` belongs to `at ledger rotate-log`", code=2)
    if args.action == "sync":
        extra: list[str] = []
    elif args.action == "check":
        extra = ["--check"]
    else:  # rotate-log
        if bool(args.task_id) == bool(args.all):
            die("usage: at ledger rotate-log <TASK_ID> | at ledger rotate-log --all", code=2)
        extra = ["rotate-log", args.task_id or "--all"]
    return _run_tasks_script("sync_todo_ledgers.py", extra)


def cmd_reserve(args: argparse.Namespace) -> int:
    if not args.rest:
        die("usage: at reserve inbox <slug> | at reserve task <PREFIX> <TYPE> <slug>", code=2)
    return _run_tasks_script("reserve_work_item.sh", list(args.rest))


def cmd_task(args: argparse.Namespace) -> int:
    if not args.rest:
        die("usage: at task brief <TASK_ID> --phase N | at task run-state init|check <TASK_ID> | at task run <TASK_ID> | at task size <TASK_ID> --phase N|--final", code=2)
    if args.rest[0] == "run":
        import task_run  # lib/task_run.py, next to this file
        scripts = tasks_root() / "skills" / "task-ledger" / "scripts"
        return task_run.main(list(args.rest[1:]), repo_root(), core_root(), scripts)
    if args.rest[0] == "size":
        import task_size  # lib/task_size.py, next to this file
        return task_size.main(list(args.rest[1:]), repo_root())
    return _run_tasks_script("task_brief.py", list(args.rest))


def cmd_migrate(args: argparse.Namespace) -> int:
    import migrate  # lib/migrate.py
    return migrate.cmd_migrate(args, sys.modules[__name__])


def cmd_peer(args: argparse.Namespace) -> int:
    import peer  # lib/peer.py, next to this file
    return peer.main(list(args.rest), repo_root(), core_root())


def _enable_extras(repo: Path) -> str:
    """Enable the agents-extras plugin in the repo's settings; 'created', 'merged' or 'kept'."""
    seed = json.loads((core_root() / "seed" / "settings.json").read_text())
    return merge_settings_json(repo / ".claude" / "settings.json", {
        "extraKnownMarketplaces": {MARKETPLACE: seed["extraKnownMarketplaces"][MARKETPLACE]},
        "enabledPlugins": {f"agents-extras@{MARKETPLACE}": True},
    })


def cmd_addon(args: argparse.Namespace) -> int:
    import addons  # lib/addons.py, next to this file
    return addons.main(list(args.rest), repo_root(), _enable_extras)


def cmd_repos_check(args: argparse.Namespace) -> int:
    return _run_tasks_script("check_repos_config.sh", list(args.rest))


def cmd_version(args: argparse.Namespace) -> int:
    print(version())
    return 0


def cmd_seed_path(args: argparse.Namespace) -> int:
    seed = core_root() / "seed" / "AGENTS.md"
    if not seed.is_file():
        die(f"agents-core seed is missing: {seed}")
    print(seed)
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
    doctor_harness = p_doctor.add_mutually_exclusive_group()
    doctor_harness.add_argument("--claude", action="store_true",
                                help="also require Claude runtime readiness")
    doctor_harness.add_argument("--codex", action="store_true",
                                help="also require Codex runtime readiness")
    doctor_harness.add_argument("--all", dest="all_harnesses", action="store_true",
                                help="require both Claude and Codex runtime readiness")
    p_doctor.add_argument("--drift", action="store_true",
                          help="print one line if the repo is behind the plugin seed, else nothing; "
                               "always exits 0 (used by the session-start hook)")
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

    p_update = sub.add_parser("update", help="refresh this machine's plugins from the marketplace")
    p_update.add_argument("--check", action="store_true",
                          help="report what is installed without changing anything")
    p_update.add_argument("--claude", action="store_true", help="only update Claude Code")
    p_update.add_argument("--codex", action="store_true", help="only update Codex")
    p_update.set_defaults(func=cmd_update)

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

    p_ledger = sub.add_parser("ledger", help="sync | check | rotate-log <TASK_ID>|--all")
    p_ledger.add_argument("action", choices=("sync", "check", "rotate-log"))
    p_ledger.add_argument("task_id", nargs="?")
    p_ledger.add_argument("--all", action="store_true",
                          help="rotate-log: every task whose execution log is over the limit")
    p_ledger.set_defaults(func=cmd_ledger)

    p_reserve = sub.add_parser("reserve", help="reserve an inbox idea or task filename")
    p_reserve.add_argument("rest", nargs=argparse.REMAINDER)
    p_reserve.set_defaults(func=cmd_reserve)

    p_task = sub.add_parser("task", help="brief <TASK_ID> --phase N | run-state init|check <TASK_ID> | run <TASK_ID> | size <TASK_ID> --phase N|--final")
    p_task.add_argument("rest", nargs=argparse.REMAINDER)
    p_task.set_defaults(func=cmd_task)

    p_peer = sub.add_parser("peer", help="enable <cli>[:<model>]... | disable | status | run --role R --brief F --out F: "
                                         "read-only second opinion from the other agent CLI")
    p_peer.add_argument("rest", nargs=argparse.REMAINDER)
    p_peer.set_defaults(func=cmd_peer)

    p_addon = sub.add_parser("addon", help="list | status | enable <name>... | disable <name>...: optional "
                                           "tools (browser, shadcn) a repository switches on for itself")
    p_addon.add_argument("rest", nargs=argparse.REMAINDER)
    p_addon.set_defaults(func=cmd_addon)

    p_repos = sub.add_parser("repos-check", help="validate .config/repos.project.md")
    p_repos.add_argument("rest", nargs=argparse.REMAINDER)
    p_repos.set_defaults(func=cmd_repos_check)

    p_seed_path = sub.add_parser("seed-path", help="print the active seed AGENTS.md path")
    p_seed_path.set_defaults(func=cmd_seed_path)

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
