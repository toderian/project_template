#!/usr/bin/env python3
"""`at` — the agents-template CLI.

Subcommands:
  init         write the downstream seed into this repo (idempotent, never clobbers)
  doctor       check that this repo still matches the contract
  bootstrap    install the plugins into this machine's harnesses, write ~/.local/bin/at
  migrate      convert a legacy `_base/`/`playbooks/` downstream (Task 8)
  ledger       wrapper: `sync` | `check` | `rotate-log <TASK_ID>`
  reserve      wrapper: reserve an inbox idea or task filename
  repos-check  wrapper: validate `.config/repos.project.md`
  version      print the agents-core plugin version

Exit codes: 0 ok, 1 errors, 2 usage. Python 3 stdlib only, no third-party imports.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

MARKETPLACE = "agents-template"
DEFAULT_SOURCE = "toderian/project_template"
BEGIN_MARKER = "# BEGIN agents-template"
END_MARKER = "# END agents-template"
MAX_AGENTS_MD_LINES = 200

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
    """Copy `src` to `dst`. Returns 'created', 'updated' or 'kept'."""
    data = src.read_bytes()
    if dst.exists():
        if not overwrite or dst.read_bytes() == data:
            return "kept"
        dst.write_bytes(data)
        return "updated"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data)
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


def merge_settings_json(dst_path: Path, seed_json: dict) -> str:
    """Deep-merge only the keys this template manages; never drop user keys.

    Managed: `extraKnownMarketplaces` and `enabledPlugins` (missing keys added),
    `permissions.deny` (union, existing order kept). Returns 'created',
    'merged' or 'kept'.
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
        for name, value in wanted.items():
            bucket.setdefault(name, value)

    deny = (seed_json.get("permissions") or {}).get("deny") or []
    if deny:
        current = data.setdefault("permissions", {}).setdefault("deny", [])
        for rule in deny:
            if rule not in current:
                current.append(rule)

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


def cmd_init(args: argparse.Namespace) -> int:
    repo = repo_root()
    seed = core_root() / "seed"
    report: list[tuple[str, str]] = []

    for name in ("AGENTS.md", "CLAUDE.md"):
        report.append((name, write_seed_file(seed / name, repo / name, overwrite=False)))

    settings = json.loads((seed / "settings.json").read_text())
    if args.with_tasks:
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

    if args.with_tasks or args.with_artifacts or args.with_workbooks or args.with_repos:
        tseed = tasks_root() / "seed"
        if args.with_tasks:
            _copy_tree(tseed / "docs", repo / "docs", report, repo)
        if args.with_artifacts:
            report.append(("artifacts/README.md", write_seed_file(
                tseed / "artifacts" / "README.md", repo / "artifacts" / "README.md", overwrite=False)))
        if args.with_workbooks:
            report.append(("workbooks/README.md", write_seed_file(
                tseed / "workbooks" / "README.md", repo / "workbooks" / "README.md", overwrite=False)))
        if args.with_repos:
            report.append((".config/repos.project.md", write_seed_file(
                tseed / ".config" / "repos.project.md",
                repo / ".config" / "repos.project.md", overwrite=False)))

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
    if proc.returncode != 0:
        for line in messages:
            findings.append(("ERROR", f"ledger: {line}"))
        if not messages:
            findings.append(("ERROR", "ledger: `at ledger check` failed"))
        return
    warnings = [line for line in messages if line.startswith("WARNING:")]
    for line in warnings:
        findings.append(("WARN", f"ledger: {line[len('WARNING:'):].strip()}"))
    if not warnings:
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
        slots = text.count("TODO-FILL")
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
    """Global skill symlinks that point into a legacy template skill tree."""
    found: list[Path] = []
    for rel in (".claude/skills", ".codex/skills", ".agents/skills"):
        base = home / rel
        if not base.is_dir():
            continue
        for entry in sorted(base.iterdir()):
            if not entry.is_symlink():
                continue
            target = Path(os.path.realpath(entry))
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
            print("stale global skill symlinks (they resolve into a legacy template tree):")
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
# at migrate (Task 8)
# --------------------------------------------------------------------------- #

def cmd_migrate(args: argparse.Namespace) -> int:
    print("at migrate: not implemented yet (Task 8)", file=sys.stderr)
    return 2


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

    p_migrate = sub.add_parser("migrate", help="convert a legacy downstream (Task 8)")
    p_migrate.add_argument("--dry-run", action="store_true")
    p_migrate.add_argument("--keep-tasks", action="store_true")
    p_migrate.add_argument("--no-tasks", action="store_true")
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
