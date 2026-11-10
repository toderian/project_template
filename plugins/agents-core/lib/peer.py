"""`at peer` — a read-only second opinion from the other agent CLI.

A session running in Claude Code can ask Codex to review, and the reverse, when this checkout has
opted in: `git config agents.peers "<cli>[:<model>[:<effort>]] ..."` (local git config, so per repo and never
committed — the peer's provider receives the brief and every file the peer reads). The peer never
edits: Codex runs in its read-only sandbox, Claude without the edit tools and with read-only git
commands only. The dispatch itself is `task_run.Harness`, the same code `at task run` uses.

Exit codes of `at peer run` / `at peer status`: 0 a reply was saved (whatever its verdict) or a peer
is available; 3 no peer available, with one reason line; 2 usage error. A caller treats 3 as "go on
without the peer", never as a failed review.

Python 3 stdlib only. Imported by lib/at.py; do not run directly.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import task_run  # lib/task_run.py, next to this file

CLIS = ("claude", "codex")
ROLES = ("reviewer", "plan-critic", "security-auditor")
CONFIG_KEY = "agents.peers"
DEPTH_ENV = "AT_PEER_DEPTH"  # set on the peer process; a peer never starts a peer of its own
UNAVAILABLE = 3
# The only shell commands a Claude peer may run; Codex is fenced by its read-only sandbox instead.
READ_ONLY_GIT = ["git show:*", "git diff:*", "git log:*", "git status:*"]
# `## Verdict: PASS`, `## Plan verdict: REVISE`, `## Architecture verdict: PROCEED` ...
ANY_VERDICT_RE = re.compile(r"^\s*(?:#+\s*)?(?:\w+ )?[Vv]erdict:\s*([A-Z_]+)\b", re.M)


def _git_config(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), "config", *args], capture_output=True, text=True, check=False)


def parse_entries(value: str) -> tuple[list[tuple[str, str | None, str | None]], list[str]]:
    """`"codex:gpt-x:high claude"` -> ([("codex", "gpt-x", "high"), ("claude", None, None)], unknown).

    Model and effort are the defaults for that peer; `codex::high` sets an effort and no model.
    """
    entries, unknown = [], []
    for word in value.replace(",", " ").split():
        cli, model, effort = (word.split(":", 2) + ["", ""])[:3]
        if cli in CLIS:
            entries.append((cli, model or None, effort or None))
        else:
            unknown.append(word)
    return entries, unknown


def configured(repo: Path) -> list[tuple[str, str | None, str | None]]:
    proc = _git_config(repo, "--get", CONFIG_KEY)
    return parse_entries(proc.stdout)[0] if proc.returncode == 0 else []


def caller(from_arg: str | None) -> str | None:
    """Which CLI is asking: the flag, else Claude Code's own marker in the environment."""
    return from_arg or ("claude" if os.environ.get("CLAUDECODE") else None)


def pick(repo: Path, from_arg: str | None) -> tuple[tuple[str, str | None, str | None] | None, str]:
    """((cli, model, effort), "") for the peer to use, or (None, reason)."""
    if os.environ.get(DEPTH_ENV):
        return None, "this session is itself a peer check"
    entries = configured(repo)
    if not entries:
        return None, f"not enabled for this checkout; run: at peer enable <{'|'.join(CLIS)}>"
    who = caller(from_arg)
    others = [e for e in entries if e[0] != who]
    if not others:
        return None, f"{CONFIG_KEY} lists only {who}, the calling CLI"
    if not shutil.which(others[0][0]):
        return None, f"{others[0][0]} is not on PATH"
    return others[0], ""


def describe(model: str | None, effort: str | None) -> str:
    return f"model {model or 'default'}, effort {effort or 'default'}"


def doctor_findings(repo: Path) -> list[tuple[str, str]]:
    """One line per CLI this checkout lists as a peer; nothing when the feature is off."""
    return [("OK", f"peer check: {cli} is on PATH") if shutil.which(cli) else
            ("WARN", f"peer check: {CONFIG_KEY} lists {cli}, which is not on PATH; "
                     f"install it or run `at peer disable`")
            for cli, _, _ in configured(repo)]


def _unavailable(reason: str) -> int:
    print(f"peer: unavailable ({' '.join(reason.split())})")
    return UNAVAILABLE


def cmd_enable(args: argparse.Namespace, repo: Path) -> int:
    entries, unknown = parse_entries(" ".join(args.cli))
    if unknown or not entries:
        print(f"at peer enable: expected {' or '.join(CLIS)}, optionally as <cli>:<model>:<effort>; got "
              f"{' '.join(unknown) or 'nothing'}", file=sys.stderr)
        return 2
    missing = [cli for cli, _, _ in entries if not shutil.which(cli)]
    if missing:
        print(f"at peer enable: not on PATH: {', '.join(missing)}", file=sys.stderr)
        return 1
    value = " ".join(":".join([cli, model or "", effort or ""]).rstrip(":") for cli, model, effort in entries)
    proc = _git_config(repo, CONFIG_KEY, value)
    if proc.returncode != 0:
        print(f"at peer enable: git config failed: {proc.stderr.strip()}", file=sys.stderr)
        return 1
    names = ", ".join(cli for cli, _, _ in entries)
    print(f"peer checks enabled for this checkout only: {value}")
    print(f"note: a peer check sends the brief and the files the peer reads to the provider of {names}")
    return 0


def cmd_disable(args: argparse.Namespace, repo: Path) -> int:
    _git_config(repo, "--unset-all", CONFIG_KEY)
    print("peer checks disabled for this checkout")
    return 0


def cmd_status(args: argparse.Namespace, repo: Path) -> int:
    peer, reason = pick(repo, args.from_cli)
    if not peer:
        return _unavailable(reason)
    print(f"peer: {peer[0]} ({describe(peer[1], peer[2])})")
    return 0


def cmd_run(args: argparse.Namespace, repo: Path, core_root: Path) -> int:
    if not caller(args.from_cli) and not os.environ.get(DEPTH_ENV):
        print("at peer run: cannot tell which CLI is calling; pass --from claude|codex", file=sys.stderr)
        return 2
    try:
        brief = Path(args.brief).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"at peer run: cannot read --brief: {exc}", file=sys.stderr)
        return 2
    peer, reason = pick(repo, args.from_cli)
    if not peer:
        return _unavailable(reason)
    cli, model, effort = peer[0], args.model or peer[1], args.effort or peer[2]
    env = {DEPTH_ENV: "1"}
    with tempfile.TemporaryDirectory() as tmp:
        harness = task_run.Harness(cli, repo, core_root, model, None, None, Path(tmp) / "peer.log",
                                   args.timeout, None, checks=READ_ONLY_GIT, effort=effort)
        try:
            message, session = harness.run(args.role, brief, writable=False, env=env)
            if message.strip() and task_run.parse_status(message) == "MISSING":
                again, _ = harness.run(args.role, task_run.STATUS_REMINDER + brief, writable=False,
                                       session=session, env=env)
                if task_run.parse_status(again) != "MISSING":
                    message = again
        except task_run.RunError as exc:
            return _unavailable(str(exc))
    if not message.strip():
        return _unavailable(f"{cli} returned an empty reply")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f"Peer: {cli} ({describe(model, effort)}), role {args.role}, {task_run.now_iso()}\n\n"
                   f"{message.rstrip()}\n", encoding="utf-8")
    verdicts = ANY_VERDICT_RE.findall(message)
    found = list(dict.fromkeys(task_run.findings(message)))  # a reply may list a finding twice
    critical = sum(1 for severity, _ in found if severity == "C")
    status = "" if task_run.parse_status(message) != "MISSING" else ", no status line"
    print(f"peer {cli} ({args.role}): {verdicts[-1] if verdicts else 'no verdict'}, {len(found)} finding(s), "
          f"{critical} critical{status} -> {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="at peer", description="read-only second opinion from the other agent CLI")
    sub = p.add_subparsers(dest="action", required=True)
    enable = sub.add_parser("enable", help="allow these CLIs as peers in this checkout")
    enable.add_argument("cli", nargs="+", metavar="<cli>[:<model>[:<effort>]]")
    sub.add_parser("disable", help="turn peer checks off in this checkout")
    for name, text in (("status", "say which peer a call would use"), ("run", "run one peer check")):
        cmd = sub.add_parser(name, help=text)
        cmd.add_argument("--from", dest="from_cli", choices=CLIS,
                         help="the CLI this session runs in (detected for Claude Code)")
    run = sub.choices["run"]
    run.add_argument("--role", required=True, choices=ROLES)
    run.add_argument("--brief", required=True, help="file with the dispatch brief")
    run.add_argument("--out", required=True, help="file the peer's reply is saved to")
    run.add_argument("--model", help="model for this call; default is the one in agents.peers, else the CLI's own")
    run.add_argument("--effort", help="reasoning effort for this call, as the peer CLI names it (e.g. low, medium, "
                                      "high); default is the one in agents.peers, else the CLI's own")
    run.add_argument("--timeout", type=int, default=900, help="seconds before the peer is killed (default 900)")
    return p


def main(argv: list[str], repo: Path, core_root: Path) -> int:
    args = build_parser().parse_args(argv)
    if args.action == "run":
        return cmd_run(args, repo, core_root)
    return {"enable": cmd_enable, "disable": cmd_disable, "status": cmd_status}[args.action](args, repo)
