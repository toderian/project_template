"""`at task size <TASK-ID> (--phase N [--fix R] | --final) [--base REV]` — measure a run's diff.

Writes a size table next to the diff it describes so every review point in the
`agents-core:execute-plan` loop sees how much code the phase, the fix round or the whole run added:

  --phase N          BASE of phase N (from state.md) → working tree   → phase-N/size.md
  --phase N --fix R  what fix round R changed since the previous size file → phase-N/size-fix-R.md
                     (or --base REV → working tree when the pre-fix state was committed)
  --final            base_rev (state.md frontmatter) → working tree   → size.md

Lines per file before and after, code vs test split, and a `Flagged:` line for growth a reviewer
must see a reason for. Flags are prompts for judgement, not failures: the command exits 0 whenever
it could measure, 2 on a usage or base error. Python 3 stdlib only. Imported by lib/at.py.
"""
from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

RUNS_DIR = "docs/tasks_manager/_runs"
TEST_RE = re.compile(r"(^|/)(tests?|spec|specs|__tests__|fixtures?)(/|$)|(^|/)(test[-_.]|[-_.]test\.|.*\.spec\.)")
GROW_MIN_LINES, GROW_MIN_PCT, NEW_FILE_MAX, PHASE_NET_MAX = 40, 25, 120, 300


@dataclass
class FileSize:
    path: str
    before: int | None  # None = binary
    after: int | None
    added: int
    deleted: int

    @property
    def kind(self) -> str:
        if self.before is None or self.after is None:
            return "binary"
        return "test" if TEST_RE.search(self.path) else "code"

    @property
    def net(self) -> int:
        return (self.after or 0) - (self.before or 0)

    @property
    def is_new(self) -> bool:
        return self.before == 0

    @property
    def flag(self) -> str | None:
        if self.kind != "code":
            return None
        if self.is_new:
            return f"new, {self.after}" if (self.after or 0) >= NEW_FILE_MAX else None
        if self.before and self.net >= GROW_MIN_LINES and self.net * 100 >= self.before * GROW_MIN_PCT:
            return f"+{self.net * 100 // self.before} %, +{self.net}"
        return None


@dataclass
class Report:
    base: str
    files: list[FileSize]

    def by_kind(self, kind: str) -> list[FileSize]:
        return [f for f in self.files if f.kind == kind]

    def net(self, kind: str) -> int:
        return sum(f.net for f in self.by_kind(kind))

    @property
    def added(self) -> int:
        return sum(f.added for f in self.files)

    @property
    def deleted(self) -> int:
        return sum(f.deleted for f in self.files)

    def code_growth(self) -> dict[str, int]:
        """Code files whose line count grew, path → net. Empty when the diff only shrank or moved code."""
        return {f.path: f.net for f in self.by_kind("code") if f.net > 0}

    def flagged(self) -> list[str]:
        out = [f"{Path(f.path).name} ({f.flag})" for f in self.files if f.flag]
        if self.net("code") >= PHASE_NET_MAX:
            out.append(f"code net +{self.net('code')} ≥ {PHASE_NET_MAX}")
        return out


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


def _count_lines(text: bytes | str | None) -> int:
    if not text:
        return 0
    if isinstance(text, bytes):
        return text.count(b"\n") + (0 if text.endswith(b"\n") else 1)
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def _lines_at(repo: Path, rev: str, path: str) -> int:
    proc = subprocess.run(["git", "-C", str(repo), "show", f"{rev}:{path}"], capture_output=True)
    return _count_lines(proc.stdout) if proc.returncode == 0 else 0


def _lines_now(repo: Path, path: str) -> int:
    p = repo / path
    return _count_lines(p.read_bytes()) if p.is_file() else 0


def measure(repo: Path, base: str, exclude: str = RUNS_DIR) -> Report:
    """Diff `base` → working tree (tracked changes plus untracked files), excluding the run directory."""
    if _git(repo, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}").returncode != 0:
        raise ValueError(f"base revision not found: {base}")
    pathspec = [".", f":(exclude){exclude}"]
    files: list[FileSize] = []
    numstat = _git(repo, "diff", "--numstat", base, "--", *pathspec).stdout
    for line in numstat.splitlines():
        added, deleted, path = line.split("\t", 2)
        if added == "-":  # binary
            files.append(FileSize(path, None, None, 0, 0))
            continue
        files.append(FileSize(path, _lines_at(repo, base, path), _lines_now(repo, path), int(added), int(deleted)))
    untracked = _git(repo, "ls-files", "--others", "--exclude-standard", "--", *pathspec).stdout
    for path in untracked.splitlines():
        if not path or any(f.path == path for f in files):
            continue
        try:
            (repo / path).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            files.append(FileSize(path, None, None, 0, 0))
            continue
        n = _lines_now(repo, path)
        files.append(FileSize(path, 0, n, n, 0))
    files.sort(key=lambda f: (-abs(f.net), f.path))
    return Report(base, files)


def render(report: Report, title: str, shape: list[str] | None = None, fix_round: int | None = None) -> str:
    out = [f"# Size — {title} · BASE {report.base} → working tree", ""]
    for line in shape or []:
        out.append(f"Shape: {line}")
    if shape:
        out.append("")
    if not report.files:
        out.append("No changes.")
        return "\n".join(out) + "\n"
    out += ["| File | Before | After | Net | Kind |", "|---|---|---|---|---|"]
    for f in report.files:
        if f.kind == "binary":
            out.append(f"| {f.path} | – | – | binary | binary |")
            continue
        net = f"{f.net:+d}" + (" (new)" if f.is_new else " (deleted)" if f.after == 0 else "")
        out.append(f"| {f.path} | {f.before} | {f.after} | {net} | {f.kind} |")
    code, test = report.by_kind("code"), report.by_kind("test")
    out += ["", f"Total: +{report.added} / −{report.deleted}, {len(report.files)} files. "
                f"Code net {report.net('code'):+d} ({len(code)} files). Test net {report.net('test'):+d} ({len(test)} files)."]
    flagged = report.flagged()
    out.append("Flagged: " + (", ".join(flagged) if flagged else "none"))
    if fix_round is not None:
        growth = report.code_growth()
        grown = ", ".join(f"{Path(p).name} {n:+d}" for p, n in growth.items()) or "none"
        out.append(f"Fix round {fix_round}: code net {report.net('code'):+d} in {grown}")
    return "\n".join(out) + "\n"


def parse_after(size_file: Path) -> dict[str, int]:
    """After-column per path from a size file this module wrote (the previous review point)."""
    out: dict[str, int] = {}
    if not size_file.is_file():
        return out
    for line in size_file.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 5 and cells[1].isdigit() and cells[2].isdigit():
            out[cells[0]] = int(cells[2])
    return out


def delta(prev_after: dict[str, int], current: Report) -> Report:
    """What one fix round changed: line counts at the previous review point → now, same base."""
    files = []
    for f in current.files:
        if f.kind == "binary":
            continue
        before = prev_after.get(f.path, 0 if f.is_new else f.before)
        net = (f.after or 0) - before
        if net:
            files.append(FileSize(f.path, before, f.after, max(net, 0), max(-net, 0)))
    for path, before in prev_after.items():  # touched last round, back to base now
        if not any(f.path == path for f in current.files):
            files.append(FileSize(path, before, before, 0, 0))
    files.sort(key=lambda f: (-abs(f.net), f.path))
    return Report(current.base, files)


def phase_shape(task_file: Path, n: int) -> list[str]:
    """`Shape:` lines written under `#### Phase N:` in the task file, if any."""
    if not task_file.is_file():
        return []
    text = task_file.read_text(encoding="utf-8")
    m = re.search(rf"^#### Phase {n}\b[^\n]*\n(.*?)(?=^#### |^### |\Z)", text, re.M | re.S)
    if not m:
        return []
    return [l.strip()[6:].strip() for l in m.group(1).splitlines() if l.strip().startswith("Shape:")]


def _state(runs: Path) -> tuple[dict[str, str], list[str]]:
    state = runs / "state.md"
    if not state.is_file():
        raise ValueError(f"no run state at {state}; run `at task run-state init` first or pass --base")
    lines = state.read_text(encoding="utf-8").split("\n")
    end = lines.index("---", 1)
    front = {k.strip(): v.strip() for k, _, v in (l.partition(":") for l in lines[1:end])}
    return front, lines[end + 1:]


def phase_base(ledger: list[str], n: int) -> str | None:
    rev = None
    for line in ledger:
        m = re.match(rf"^Phase {n}: BASE (\S+)", line)
        if m:
            rev = m.group(1).rstrip(";")
    return rev


def write_phase(repo: Path, runs: Path, task_file: Path, task_id: str, n: int, base: str,
                fix_round: int | None = None, fix_base: str | None = None) -> tuple[Path, Report]:
    """Phase size from BASE; with `fix_round`, only what that round changed since the previous size
    file (`size.md` for round 1, `size-fix-<R-1>.md` after), or since `fix_base` when given."""
    pdir = runs / f"phase-{n}"
    pdir.mkdir(parents=True, exist_ok=True)
    report = measure(repo, fix_base or base)
    if fix_round and not fix_base:
        prev = pdir / ("size.md" if fix_round == 1 else f"size-fix-{fix_round - 1}.md")
        if not prev.is_file():
            raise ValueError(f"no previous size file {prev.name} to diff fix round {fix_round} against; pass --base")
        report = delta(parse_after(prev), report)
    name = f"size-fix-{fix_round}.md" if fix_round else "size.md"
    title = f"{task_id} phase {n}" + (f" fix round {fix_round}" if fix_round else "")
    out = pdir / name
    out.write_text(render(report, title, phase_shape(task_file, n), fix_round), encoding="utf-8")
    return out, report


def write_final(repo: Path, runs: Path, task_id: str, base: str) -> tuple[Path, Report]:
    report = measure(repo, base)
    out = runs / "size.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(report, f"{task_id} whole run"), encoding="utf-8")
    return out, report


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="at task size", description=__doc__.split("\n\n")[0])
    p.add_argument("task_id")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--phase", type=int, metavar="N", help="measure phase N from its BASE line in state.md")
    g.add_argument("--final", action="store_true", help="measure the whole run from base_rev")
    p.add_argument("--fix", type=int, metavar="R", help="with --phase: measure what fix round R changed since the previous size file")
    p.add_argument("--base", metavar="REV", help="override the base revision")
    return p


def main(argv: list[str], repo: Path) -> int:
    args = build_parser().parse_args(argv)
    runs = repo / RUNS_DIR / args.task_id
    try:
        if args.fix and not args.phase:
            raise ValueError("--fix needs --phase")
        front, ledger = _state(runs) if (args.phase or not args.base) else ({}, [])
        task_file = repo / front.get("task_file", "")
        if args.final:
            base = args.base or front.get("base_rev")
            if not base:
                raise ValueError("state.md has no base_rev; pass --base")
            out, report = write_final(repo, runs, args.task_id, base)
        else:
            base = phase_base(ledger, args.phase) if args.fix else (args.base or phase_base(ledger, args.phase))
            if not base:
                raise ValueError(f"no `Phase {args.phase}: BASE <rev>` line in state.md; pass --base")
            out, report = write_phase(repo, runs, task_file, args.task_id, args.phase, base, args.fix,
                                      fix_base=args.base if args.fix else None)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2
    print(out.read_text(encoding="utf-8"), end="")
    print(f"-> {out.relative_to(repo)}")
    return 0
