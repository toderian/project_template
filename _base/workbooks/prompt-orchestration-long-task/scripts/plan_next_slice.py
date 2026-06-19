#!/usr/bin/env python3
"""Print a deterministic next-slice brief for a long-running task.

This helper is intentionally read-only and standard-library-only. It parses enough Markdown structure
to orient a human or agent before implementation, but it does not execute commands or call providers.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


CHECKBOX_RE = re.compile(r"^(?P<indent>\s*)[-*]\s+\[(?P<mark>[ xX])\]\s+(?P<text>.+?)\s*$")
HEADING_RE = re.compile(r"^(?P<marks>#{1,6})\s+(?P<title>.+?)\s*$")
FENCE_RE = re.compile(r"^```(?P<lang>[A-Za-z0-9_-]*)\s*$")


@dataclass(frozen=True)
class Checkbox:
    line: int
    checked: bool
    text: str


@dataclass(frozen=True)
class CommandBlock:
    line: int
    language: str
    commands: tuple[str, ...]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text()


def title_from_markdown(text: str, fallback: str) -> str:
    for line in text.splitlines():
        match = HEADING_RE.match(line)
        if match:
            return match.group("title").strip()
    return fallback


def parse_checkboxes(text: str) -> list[Checkbox]:
    boxes: list[Checkbox] = []
    for index, line in enumerate(text.splitlines(), start=1):
        match = CHECKBOX_RE.match(line)
        if not match:
            continue
        boxes.append(
            Checkbox(
                line=index,
                checked=match.group("mark").lower() == "x",
                text=match.group("text").strip(),
            )
        )
    return boxes


def section_lines(text: str, section_names: Iterable[str]) -> list[str]:
    wanted = {name.casefold() for name in section_names}
    lines = text.splitlines()
    capture = False
    level = 0
    result: list[str] = []

    for line in lines:
        heading = HEADING_RE.match(line)
        if heading:
            title = heading.group("title").strip().casefold()
            current_level = len(heading.group("marks"))
            if capture and current_level <= level:
                break
            if title in wanted:
                capture = True
                level = current_level
                continue
        if capture:
            result.append(line)

    return result


def bulletish(lines: Iterable[str], limit: int | None = None) -> list[str]:
    items: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("-", "*")):
            stripped = stripped[1:].strip()
        elif re.match(r"^\d+\.\s+", stripped):
            stripped = re.sub(r"^\d+\.\s+", "", stripped)
        else:
            continue
        if stripped:
            items.append(stripped)
        if limit is not None and len(items) >= limit:
            break
    return items


def parse_command_blocks(text: str) -> list[CommandBlock]:
    blocks: list[CommandBlock] = []
    in_fence = False
    language = ""
    start_line = 0
    body: list[str] = []

    for index, line in enumerate(text.splitlines(), start=1):
        fence = FENCE_RE.match(line)
        if fence and not in_fence:
            in_fence = True
            language = fence.group("lang").lower()
            start_line = index
            body = []
            continue
        if fence and in_fence:
            if language in {"bash", "sh", "shell", "zsh", "text", ""}:
                commands = tuple(
                    entry.rstrip()
                    for entry in body
                    if entry.strip() and not entry.lstrip().startswith("#")
                )
                if commands:
                    blocks.append(CommandBlock(start_line, language or "text", commands))
            in_fence = False
            continue
        if in_fence:
            body.append(line)

    return blocks


def classify_task(task_path: Path) -> tuple[str, str]:
    stem = task_path.stem
    prefix = stem.split("-", 1)[0].upper() if "-" in stem else stem.upper()
    if prefix in {"F", "FEATURE"}:
        return "feature/product slice", "Use acceptance criteria, tests, rollout notes, and related workbook commands."
    if prefix in {"D", "BUG", "DEFECT"}:
        return "defect/diagnosis", "Use reproduction evidence, minimal fix hypothesis, and regression verification."
    if prefix in {"C", "CHORE"}:
        return "chore/convention/infrastructure", "Use compatibility, migration risk, and downstream impact checks."
    if prefix in {"R", "RESEARCH"}:
        return "research/report/resource", "Use source inventory, provenance, synthesis target, and follow-up criteria."
    if prefix == "T":
        return "global template/cross-area", "Use template conventions, setup checks, and downstream impact notes."
    if re.fullmatch(r"[A-Z]{2,5}", prefix):
        return f"area-scoped task ({prefix})", "Read area docs, repo registry rows, contracts, runbooks, and workbook state."
    return "uncategorized task", "Classify manually from task purpose, acceptance criteria, and current phase."


def select_next_phase(boxes: list[Checkbox]) -> Checkbox | None:
    phase_words = ("phase", "slice", "step", "milestone")
    for box in boxes:
        if not box.checked and any(word in box.text.casefold() for word in phase_words):
            return box
    for box in boxes:
        if not box.checked:
            return box
    return None


def print_list(title: str, items: list[str], empty: str) -> None:
    print(f"## {title}")
    if not items:
        print(f"- {empty}")
        return
    for item in items:
        print(f"- {item}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True, type=Path, help="Markdown task file to inspect")
    parser.add_argument("--workbook", type=Path, help="Related workbook README.md to inspect")
    parser.add_argument(
        "--max-log-lines",
        type=int,
        default=5,
        help="Maximum execution-log bullets to include (default: 5)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    task_text = read_text(args.task)
    task_title = title_from_markdown(task_text, args.task.stem)
    boxes = parse_checkboxes(task_text)
    next_phase = select_next_phase(boxes)
    task_kind, task_guidance = classify_task(args.task)

    workbook_text = ""
    workbook_title = "None"
    command_blocks: list[CommandBlock] = []
    if args.workbook:
        workbook_text = read_text(args.workbook)
        workbook_title = title_from_markdown(workbook_text, args.workbook.name)
        command_blocks = parse_command_blocks(workbook_text)

    acceptance = bulletish(section_lines(task_text, ["Acceptance Criteria", "Acceptance criteria"]), limit=8)
    blockers = bulletish(section_lines(task_text, ["Blockers", "Known Blockers", "Risks"]), limit=8)
    log_items = bulletish(section_lines(task_text, ["Execution log", "Execution Log"]), limit=args.max_log_lines)

    print("# Long-Task Next Slice Brief")
    print()
    print("## Intake")
    print(f"- Task: {task_title}")
    print(f"- Task path: {args.task.as_posix()}")
    print(f"- Workbook: {workbook_title}")
    if args.workbook:
        print(f"- Workbook path: {args.workbook.as_posix()}")
    print()

    print("## Current-State Review")
    print(f"- Completed checkboxes: {sum(1 for box in boxes if box.checked)}")
    print(f"- Open checkboxes: {sum(1 for box in boxes if not box.checked)}")
    if log_items:
        print("- Recent execution log:")
        for item in log_items:
            print(f"  - {item}")
    else:
        print("- Recent execution log: none found")
    print()

    print("## Classify Task")
    print(f"- Classification: {task_kind}")
    print(f"- Routing note: {task_guidance}")
    print()

    print("## Select Next Phase")
    if next_phase:
        print(f"- Next phase: line {next_phase.line}: {next_phase.text}")
    else:
        print("- Next phase: no open checkbox found; review task for closeout or missing phase markers")
    print()

    print("## Gather Workbook Commands")
    if not command_blocks:
        print("- No workbook command blocks found")
    else:
        for block in command_blocks[:4]:
            print(f"- Command block from line {block.line} ({block.language}):")
            for command in block.commands[:6]:
                print(f"  - `{command}`")
    print()

    print_list("Acceptance Criteria", acceptance, "No acceptance criteria section found")
    print()
    print_list("Blockers And Risks", blockers, "No blockers or risks section found")
    print()

    print("## Plan Next Slice")
    if next_phase:
        print(f"- Objective: complete `{next_phase.text}` without pulling later phases forward")
    else:
        print("- Objective: determine whether the task is ready for `/complete-task` or needs phase markers")
    print("- Inputs: task file, related area docs, repo registry, workbook README, artifact registry if outputs are generated")
    print("- Stop point: task state updated, checks recorded, and the smallest reviewable slice complete")
    print()

    print("## Verify")
    print("- Run the narrowest deterministic checks named by the task or workbook")
    print("- Confirm generated, large, encrypted, external, or reproducible outputs are registered in artifacts/README.md when applicable")
    print("- Confirm `.creds/`, `.no-commit/`, raw private outputs, and absolute local paths are not copied into tracked artifacts")
    print()

    print("## Critique")
    print("- Challenge whether the selected phase is too broad, missing a baseline check, or depends on an unresolved blocker")
    print("- Escalate to a LangGraph-style workflow only if durable branching, retry, checkpoint/resume, or parallel lanes are now required")
    print()

    print("## Checkpoint")
    print("- Append an execution-log entry with actions, decisions, checks, and remaining work")
    print("- Commit only after the slice satisfies its acceptance criteria and required checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
