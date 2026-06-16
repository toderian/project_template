#!/usr/bin/env python3
"""Audit whether completed workspace commits can be squashed safely.

This helper is intentionally read-only. It shells out to Git for inspection and
never creates commits, refs, branches, rebases, resets, or worktree changes.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SHA_RE = re.compile(r"\b[0-9a-fA-F]{7,40}\b")


class GitError(RuntimeError):
    pass


@dataclass(frozen=True)
class Commit:
    sha: str
    short: str
    subject: str
    parents: list[str]
    paths: list[str]

    @property
    def is_merge(self) -> bool:
        return len(self.parents) > 1

    def summary(self) -> dict[str, Any]:
        return {
            "sha": self.sha,
            "short": self.short,
            "subject": self.subject,
            "parents": self.parents,
            "is_merge": self.is_merge,
            "paths": self.paths,
        }


def run_git(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and proc.returncode != 0:
        raise GitError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc


def git_stdout(args: list[str], *, check: bool = True) -> str:
    return run_git(args, check=check).stdout.strip()


def repo_root() -> Path:
    root = git_stdout(["rev-parse", "--show-toplevel"])
    return Path(root)


def resolve_ref(ref: str) -> str:
    return git_stdout(["rev-parse", "--verify", f"{ref}^{{commit}}"])


def short_sha(sha: str) -> str:
    return git_stdout(["rev-parse", "--short", sha])


def upstream_ref() -> str | None:
    proc = run_git(
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
        check=False,
    )
    if proc.returncode != 0:
        return None
    ref = proc.stdout.strip()
    return ref or None


def is_ancestor(base: str, head: str) -> bool:
    return run_git(["merge-base", "--is-ancestor", base, head], check=False).returncode == 0


def dirty_status() -> list[str]:
    output = git_stdout(["status", "--porcelain=v1"], check=True)
    return output.splitlines() if output else []


def rev_list(base: str, head: str) -> list[str]:
    output = git_stdout(["rev-list", "--reverse", f"{base}..{head}"])
    return output.splitlines() if output else []


def commit_subject(sha: str) -> str:
    return git_stdout(["show", "-s", "--format=%s", sha])


def commit_body(sha: str) -> str:
    return git_stdout(["show", "-s", "--format=%B", sha])


def commit_parents(sha: str) -> list[str]:
    line = git_stdout(["rev-list", "--parents", "-n", "1", sha])
    parts = line.split()
    return parts[1:]


def commit_paths(sha: str) -> list[str]:
    output = git_stdout(
        ["diff-tree", "--root", "--no-commit-id", "--name-status", "--find-renames", "-r", sha]
    )
    paths = []
    for line in output.splitlines():
        parts = line.split("\t")
        if not parts:
            continue
        status = parts[0]
        if status.startswith("R") or status.startswith("C"):
            paths.extend(parts[1:])
        elif len(parts) > 1:
            paths.append(parts[1])
    return sorted(set(paths))


def commit_info(sha: str) -> Commit:
    full = resolve_ref(sha)
    return Commit(
        sha=full,
        short=short_sha(full),
        subject=commit_subject(full),
        parents=commit_parents(full),
        paths=commit_paths(full),
    )


def remote_branches_containing(sha: str) -> list[str]:
    output = git_stdout(["branch", "-r", "--contains", sha], check=True)
    branches = []
    for line in output.splitlines():
        branch = line.strip().lstrip("*").strip()
        if not branch or " -> " in branch:
            continue
        branches.append(branch)
    return sorted(set(branches))


def find_task_file(root: Path, task_id: str | None) -> Path | None:
    if not task_id:
        return None

    candidate = Path(task_id)
    if candidate.exists() and candidate.is_file():
        return candidate.resolve()

    search_roots = [
        root / "docs" / "tasks_manager" / "_todos",
        root / "docs" / "tasks_manager" / "_todos_archived",
        root / "docs" / "_plans",
    ]
    matches: list[Path] = []
    needle = task_id.lower()
    for search_root in search_roots:
        if not search_root.exists():
            continue
        for path in search_root.rglob("*.md"):
            try:
                text = path.read_text(errors="replace")
            except OSError:
                continue
            if needle in path.name.lower() or needle in text.lower():
                matches.append(path)
    if len(matches) == 1:
        return matches[0]
    return None


def parse_task_file(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"path": None, "base": None, "shas": [], "ambiguous": False}

    text = path.read_text(errors="replace")
    base = None
    base_match = re.search(
        r"(?im)execution base revision:\s*`?([0-9a-f]{7,40})`?",
        text,
    )
    if base_match:
        base = base_match.group(1)

    shas = sorted(set(SHA_RE.findall(text)), key=text.find)
    return {"path": str(path), "base": base, "shas": shas, "ambiguous": False}


def choose_base(args: argparse.Namespace, task_meta: dict[str, Any]) -> tuple[str | None, str]:
    if args.base:
        return resolve_ref(args.base), "explicit-base"
    if task_meta.get("base"):
        return resolve_ref(task_meta["base"]), "task-execution-log"
    upstream = upstream_ref()
    if upstream:
        return resolve_ref(upstream), f"upstream:{upstream}"
    return None, "none"


def selected_from_inputs(
    args: argparse.Namespace,
    commits: list[Commit],
    task_meta: dict[str, Any],
) -> tuple[list[str], list[str], list[str]]:
    commit_by_sha = {commit.sha: commit for commit in commits}
    selected: set[str] = set()
    sources: list[str] = []
    missing: list[str] = []

    for ref in args.select:
        try:
            sha = resolve_ref(ref)
        except GitError:
            missing.append(ref)
            continue
        selected.add(sha)
        sources.append(f"select:{ref}")

    task_id = args.task_id
    if task_id:
        needle = task_id.lower()
        matched = [
            commit.sha
            for commit in commits
            if needle in commit.subject.lower() or needle in commit_body(commit.sha).lower()
        ]
        if matched:
            selected.update(matched)
            sources.append(f"task-id:{task_id}")

    task_shas = task_meta.get("shas") or []
    in_range_shas = []
    for ref in task_shas:
        try:
            sha = resolve_ref(ref)
        except GitError:
            continue
        if sha in commit_by_sha:
            in_range_shas.append(sha)
    if in_range_shas:
        selected.update(in_range_shas)
        sources.append("task-log-shas")

    ordered = [commit.sha for commit in commits if commit.sha in selected]
    out_of_range = sorted(selected - set(ordered))
    return ordered, sorted(set(sources)), missing + out_of_range


def selected_indices(commits: list[Commit], selected: list[str]) -> list[int]:
    selected_set = set(selected)
    return [index for index, commit in enumerate(commits) if commit.sha in selected_set]


def suffix_soft_reset_base(commits: list[Commit], indices: list[int], base: str) -> str | None:
    if not indices:
        return None
    first = min(indices)
    expected = list(range(first, len(commits)))
    if indices != expected:
        return None
    if first == 0:
        return base
    return commits[first - 1].sha


def overlap_report(selected_commits: list[Commit], unrelated_commits: list[Commit]) -> dict[str, Any]:
    selected_paths = sorted({path for commit in selected_commits for path in commit.paths})
    unrelated_paths = sorted({path for commit in unrelated_commits for path in commit.paths})
    overlap = sorted(set(selected_paths) & set(unrelated_paths))
    pairs = []
    for selected in selected_commits:
        selected_set = set(selected.paths)
        for unrelated in unrelated_commits:
            paths = sorted(selected_set & set(unrelated.paths))
            if paths:
                pairs.append(
                    {
                        "selected": selected.short,
                        "unrelated": unrelated.short,
                        "paths": paths,
                    }
                )
    return {
        "has_overlap": bool(overlap),
        "overlap_paths": overlap,
        "pairs": pairs,
        "selected_paths": selected_paths,
        "unrelated_paths": unrelated_paths,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    root = repo_root()
    head = resolve_ref(args.head)
    task_file = find_task_file(root, args.task_id)
    task_meta = parse_task_file(task_file)
    dirty = dirty_status()

    base, base_source = choose_base(args, task_meta)
    blockers: list[str] = []
    notes: list[str] = []
    commits: list[Commit] = []
    selected: list[str] = []
    selected_sources: list[str] = []
    missing_selected: list[str] = []

    if base is None:
        blockers.append("no reliable base or upstream; provide --base or explicit --select with a base")
    elif not is_ancestor(base, head):
        blockers.append("base is not an ancestor of head")
    else:
        commits = [commit_info(sha) for sha in rev_list(base, head)]
        selected, selected_sources, missing_selected = selected_from_inputs(args, commits, task_meta)

    if dirty:
        blockers.append("worktree or index is dirty")
    if base is not None and not commits:
        blockers.append("candidate range is empty")
    if not selected:
        blockers.append("no selected task commits; provide --task-id or --select")
    if missing_selected:
        blockers.append("one or more selected commits are missing or outside the candidate range")

    selected_set = set(selected)
    selected_commits = [commit for commit in commits if commit.sha in selected_set]
    unrelated_commits = [commit for commit in commits if commit.sha not in selected_set]

    pushed = []
    for commit in commits:
        branches = remote_branches_containing(commit.sha)
        if branches:
            pushed.append(
                {
                    "sha": commit.sha,
                    "short": commit.short,
                    "subject": commit.subject,
                    "remote_branches": branches,
                }
            )
    if pushed:
        blockers.append("candidate range contains commits already present on remote branches")

    merge_commits = [commit for commit in commits if commit.is_merge]
    if merge_commits:
        blockers.append("candidate range contains merge commits")

    overlap = overlap_report(selected_commits, unrelated_commits)

    method = None
    soft_base = None
    indices = selected_indices(commits, selected)
    if selected and commits:
        soft_base = suffix_soft_reset_base(commits, indices, base or "")
        if soft_base:
            method = "soft-reset"
        else:
            method = "mixed-rewrite"
            if overlap["has_overlap"]:
                blockers.append("selected and unrelated commits touch overlapping paths")

    allowed = not blockers and method in {"soft-reset", "mixed-rewrite"}
    if method == "mixed-rewrite":
        notes.append("create a local backup ref before replaying unrelated commits")
    if allowed:
        notes.append("rerun final validation checks after rewriting history")

    return {
        "repo": str(root),
        "head": {"input": args.head, "sha": head, "short": short_sha(head)},
        "task": {
            "task_id": args.task_id,
            "file": task_meta.get("path"),
            "execution_base": task_meta.get("base"),
        },
        "dirty": {"clean": not dirty, "status": dirty},
        "candidate_range": {
            "base": base,
            "base_short": short_sha(base) if base else None,
            "base_source": base_source,
            "head": head,
            "commit_count": len(commits),
            "commits": [commit.summary() for commit in commits],
        },
        "selection": {
            "sources": selected_sources,
            "selected_commits": [commit.summary() for commit in selected_commits],
            "unrelated_commits": [commit.summary() for commit in unrelated_commits],
            "missing_or_out_of_range": missing_selected,
        },
        "pushed_shared_commits": pushed,
        "merge_commits": [commit.summary() for commit in merge_commits],
        "path_overlap": overlap,
        "auto_squash": {
            "allowed": allowed,
            "method": method if allowed else None,
            "proposed_method": method,
            "soft_reset_base": soft_base if method == "soft-reset" else None,
            "blockers": sorted(set(blockers)),
            "notes": notes,
        },
    }


def print_human(report: dict[str, Any]) -> None:
    auto = report["auto_squash"]
    candidate = report["candidate_range"]
    selection = report["selection"]
    dirty = report["dirty"]

    status = "ALLOWED" if auto["allowed"] else "BLOCKED"
    method = auto["method"] or auto["proposed_method"] or "none"
    print(f"Auto-squash: {status} ({method})")
    print(f"Repo: {report['repo']}")
    print(
        "Range: "
        f"{candidate['base_short'] or 'none'}..{report['head']['short']} "
        f"({candidate['base_source']}, {candidate['commit_count']} commits)"
    )
    print(f"Dirty: {'no' if dirty['clean'] else 'yes'}")
    if not dirty["clean"]:
        for line in dirty["status"]:
            print(f"  {line}")

    print("\nSelected commits:")
    if selection["selected_commits"]:
        for commit in selection["selected_commits"]:
            print(f"  {commit['short']} {commit['subject']}")
    else:
        print("  none")

    print("\nUnrelated commits:")
    if selection["unrelated_commits"]:
        for commit in selection["unrelated_commits"]:
            print(f"  {commit['short']} {commit['subject']}")
    else:
        print("  none")

    if report["pushed_shared_commits"]:
        print("\nPushed/shared commits:")
        for commit in report["pushed_shared_commits"]:
            branches = ", ".join(commit["remote_branches"])
            print(f"  {commit['short']} {commit['subject']} [{branches}]")

    if report["merge_commits"]:
        print("\nMerge commits:")
        for commit in report["merge_commits"]:
            print(f"  {commit['short']} {commit['subject']}")

    overlap = report["path_overlap"]
    print("\nPath overlap:")
    if overlap["has_overlap"]:
        for path in overlap["overlap_paths"]:
            print(f"  {path}")
    else:
        print("  none")

    if auto["soft_reset_base"]:
        print(f"\nSoft reset base: {short_sha(auto['soft_reset_base'])}")

    if auto["blockers"]:
        print("\nBlockers:")
        for blocker in auto["blockers"]:
            print(f"  - {blocker}")

    if auto["notes"]:
        print("\nNotes:")
        for note in auto["notes"]:
            print(f"  - {note}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", help="Task ID or task/plan file path used to identify commits")
    parser.add_argument("--base", help="Base ref before the candidate rewrite range")
    parser.add_argument("--head", default="HEAD", help="Head ref for the candidate rewrite range")
    parser.add_argument(
        "--select",
        action="append",
        default=[],
        metavar="SHA",
        help="Explicit commit to squash; may be repeated",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        report = build_report(args)
    except GitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        print_human(report)
    return 0 if report["auto_squash"]["allowed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
