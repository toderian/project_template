"""`at addon` — optional tools a repository switches on for itself.

An add-on is an MCP server from its own upstream, pinned to a version and started with `npx`;
nothing of it is copied into the repo. `at addon enable <name>` records it in three places:

- `.mcp.json` (committed): the server for Claude Code, and the record of what the repo enabled;
- `.claude/settings.json` (committed): the `agents-extras` plugin, which holds the UI skills;
- `.codex/config.toml` (git-ignored, this checkout only): the same server for Codex, which loads a
  project config only in a project it trusts.

Python 3 stdlib only. Imported by lib/at.py; do not run directly.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

# name -> server name, npm package, pinned version, extra args, what it is, a file it needs.
ADDONS: dict[str, dict] = {
    "browser": {
        "server": "chrome-devtools", "package": "chrome-devtools-mcp", "version": "1.12.0",
        "args": ["--no-usage-statistics", "--no-performance-crux"],
        "about": "see the rendered page in a local Chrome: screenshots, console, accessibility "
                 "(ChromeDevTools/chrome-devtools-mcp)",
        "requires": None,
    },
    "shadcn": {
        "server": "shadcn", "package": "shadcn", "version": "4.23.0", "args": ["mcp"],
        "about": "search and add shadcn components; React + Tailwind repos only (shadcn-ui/ui)",
        "requires": "components.json",
    },
}
MCP_FILE = ".mcp.json"
CODEX_FILE = ".codex/config.toml"


def entry(name: str) -> dict:
    """The MCP server definition `at` writes for this add-on."""
    addon = ADDONS[name]
    return {"command": "npx", "args": ["-y", f"{addon['package']}@{addon['version']}", *addon["args"]]}


def _is_ours(name: str, found: object) -> bool:
    """Whether `found` is a server `at` wrote for this add-on, at this pin or an older one."""
    if not isinstance(found, dict) or found.get("command") != "npx":
        return False
    prefix = ADDONS[name]["package"] + "@"
    return any(isinstance(arg, str) and arg.startswith(prefix) for arg in found.get("args") or [])


def _load_mcp(repo: Path) -> dict:
    path = repo / MCP_FILE
    if not path.exists() or not path.read_text().strip():
        return {}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"at addon: {path}: invalid JSON ({exc}); fix it by hand, then re-run")
    if not isinstance(data, dict) or not isinstance(data.get("mcpServers", {}), dict):
        raise SystemExit(f"at addon: {path}: fix by hand: expected a JSON object with an `mcpServers` object")
    return data


def _save_mcp(repo: Path, data: dict) -> None:
    path = repo / MCP_FILE
    if not data.get("mcpServers"):
        data.pop("mcpServers", None)
    if data:
        path.write_text(json.dumps(data, indent=2) + "\n")
    elif path.exists():
        path.unlink()


def enabled(repo: Path) -> list[str]:
    """Add-ons this repo has switched on, read from `.mcp.json`."""
    servers = _load_mcp(repo).get("mcpServers", {})
    return [name for name, addon in ADDONS.items() if _is_ours(name, servers.get(addon["server"]))]


def _markers(name: str) -> tuple[str, str]:
    return f"# BEGIN agents-template addon {name}", f"# END agents-template addon {name}"


def _codex_block(name: str) -> str:
    begin, end = _markers(name)
    server = entry(name)
    return (f"{begin}\n[mcp_servers.{ADDONS[name]['server']}]\ncommand = {json.dumps(server['command'])}\n"
            f"args = {json.dumps(server['args'])}\n{end}\n")


def _codex_without(text: str, name: str) -> str:
    """`text` with this add-on's managed block removed."""
    begin, end = _markers(name)
    kept, inside = [], False
    for line in text.splitlines(keepends=True):
        if line.strip() == begin:
            inside = True
        elif line.strip() == end:
            inside = False
        elif not inside:
            kept.append(line)
    return "".join(kept)


def codex_registered(repo: Path, name: str) -> bool:
    path = repo / CODEX_FILE
    return path.exists() and f"[mcp_servers.{ADDONS[name]['server']}]" in path.read_text()


def _codex_enable(repo: Path, name: str) -> str:
    path = repo / CODEX_FILE
    text = path.read_text() if path.exists() else ""
    rest = _codex_without(text, name)
    if f"[mcp_servers.{ADDONS[name]['server']}]" in rest:
        return "kept (the file has its own definition)"
    new = rest + ("" if not rest or rest.endswith("\n\n") else "\n" if rest.endswith("\n") else "\n\n") \
        + _codex_block(name)
    if new == text:
        return "kept"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new)
    return "added" if _markers(name)[0] not in text else "updated"


def _codex_disable(repo: Path, name: str) -> None:
    path = repo / CODEX_FILE
    if not path.exists():
        return
    text = path.read_text()
    rest = _codex_without(text, name).rstrip("\n")
    if rest:
        if rest + "\n" != text:
            path.write_text(rest + "\n")
        return
    path.unlink()
    try:
        path.parent.rmdir()  # only when at created it and nothing else lives there
    except OSError:
        pass


def problems(repo: Path, name: str) -> list[str]:
    """What stops an enabled add-on from working in this checkout."""
    addon, found = ADDONS[name], []
    if not shutil.which("npx"):
        found.append("npx is not on PATH (install Node)")
    if addon["requires"] and not (repo / addon["requires"]).exists():
        found.append(f"the repo has no {addon['requires']}")
    if shutil.which("codex") and not codex_registered(repo, name):
        found.append(f"not registered for Codex in this checkout; run: at addon enable {name}")
    return found


def doctor_findings(repo: Path) -> list[tuple[str, str]]:
    """One line per add-on the repo enabled; nothing when it enabled none."""
    try:
        names = enabled(repo)
    except SystemExit as exc:
        return [("WARN", str(exc))]
    findings = []
    for name in names:
        found = problems(repo, name)
        findings.append(("WARN", f"addon {name}: enabled, but {'; '.join(found)}") if found else
                        ("OK", f"addon {name}: enabled"))
    return findings


def cmd_list(args: argparse.Namespace, repo: Path) -> int:
    on = enabled(repo)
    for name, addon in ADDONS.items():
        print(f"{name:<8} {'enabled ' if name in on else 'disabled'}  {addon['package']}@{addon['version']}  "
              f"{addon['about']}")
    return 0


def cmd_status(args: argparse.Namespace, repo: Path) -> int:
    findings = doctor_findings(repo)
    for level, text in findings:
        print(f"{level:<4} {text}")
    if not findings:
        print("no add-on is enabled in this repo; see: at addon list")
    return 0


def cmd_enable(args: argparse.Namespace, repo: Path, enable_extras: Callable[[Path], str]) -> int:
    data = _load_mcp(repo)
    servers = data.setdefault("mcpServers", {})
    for name in args.name:
        addon, wanted = ADDONS[name], entry(name)
        current = servers.get(addon["server"])
        if current is None or (_is_ours(name, current) and current != wanted):
            servers[addon["server"]] = wanted
            state = "added" if current is None else f"updated to {addon['package']}@{addon['version']}"
        elif current == wanted:
            state = "kept"
        else:
            print(f"at addon: {MCP_FILE} already defines a different `{addon['server']}` server; kept as is, "
                  f"{name} not enabled", file=sys.stderr)
            continue
        print(f"{name}: {MCP_FILE} {state}")
        if shutil.which("codex"):
            print(f"{name}: {CODEX_FILE} {_codex_enable(repo, name)} (this checkout only; Codex loads it "
                  f"in a trusted project)")
            ignored = subprocess.run(["git", "-C", str(repo), "check-ignore", "-q", CODEX_FILE], check=False)
            if ignored.returncode != 0:
                print(f"warning: {CODEX_FILE} is not git-ignored here; run `at init` or ignore it, do not "
                      f"commit it", file=sys.stderr)
        else:
            print(f"{name}: codex is not on PATH; Codex registration skipped")
        if addon["requires"] and not (repo / addon["requires"]).exists():
            print(f"warning: {name} needs {addon['requires']} in the repo and does nothing without it",
                  file=sys.stderr)
    _save_mcp(repo, data)
    print(f".claude/settings.json: agents-extras {enable_extras(repo)}")
    print(f"commit {MCP_FILE} and .claude/settings.json; restart the session and approve the new server")
    return 0


def cmd_disable(args: argparse.Namespace, repo: Path) -> int:
    data = _load_mcp(repo)
    servers = data.get("mcpServers", {})
    for name in args.name:
        server = ADDONS[name]["server"]
        if _is_ours(name, servers.get(server)):
            del servers[server]
            print(f"{name}: removed from {MCP_FILE}")
        elif server in servers:
            print(f"at addon: `{server}` in {MCP_FILE} was not written by at; kept", file=sys.stderr)
        else:
            print(f"{name}: not enabled")
        _codex_disable(repo, name)
    _save_mcp(repo, data)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="at addon", description="optional tools a repository switches on for itself")
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("list", help="every add-on and whether this repo enabled it")
    sub.add_parser("status", help="check the add-ons this repo enabled")
    for action, text in (("enable", "switch add-ons on in this repo"), ("disable", "switch add-ons off")):
        cmd = sub.add_parser(action, help=text)
        cmd.add_argument("name", nargs="+", choices=sorted(ADDONS), metavar="|".join(sorted(ADDONS)))
    return p


def main(argv: list[str], repo: Path, enable_extras: Callable[[Path], str]) -> int:
    args = build_parser().parse_args(argv)
    if args.action == "enable":
        return cmd_enable(args, repo, enable_extras)
    return {"list": cmd_list, "status": cmd_status, "disable": cmd_disable}[args.action](args, repo)
