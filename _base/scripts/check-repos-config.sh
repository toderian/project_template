#!/usr/bin/env bash
#
# Validate the committed repo registry and, optionally, the local checkout map.
#
# Default mode validates:
#   repos.project when present
#   task Repos metadata values when docs/tasks_manager/ exists
#
# --local additionally validates:
#   .local/repos.map
#   required repo mappings
#   absolute mapped paths
#   path existence and directory-ness
#
# Portable prerequisites: bash, python3.

set -euo pipefail

LOCAL_MODE=0

usage() {
  cat <<'EOF'
Usage: _base/scripts/check-repos-config.sh [--local]

Validate repo registry configuration.

Options:
  --local   Also validate .local/repos.map and required checkout paths.
  --help    Show this message.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --local) LOCAL_MODE=1; shift ;;
    --help) usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

python3 - "${REPO_ROOT}" "${LOCAL_MODE}" <<'PY'
from __future__ import annotations

from pathlib import Path
import os
import re
import sys


ROOT = Path(sys.argv[1])
LOCAL_MODE = sys.argv[2] == "1"

REGISTRY_HEADER = [
    "Repo",
    "Required",
    "Role",
    "Default branch",
    "Integration branch",
    "Work mode",
    "Areas",
    "Notes",
]
TASK_META_HEADER = ["Field", "Value"]
SLUG_RE = re.compile(r"^[a-z][a-z0-9-]*$")
AREA_RE = re.compile(r"^[a-z][a-z0-9-]*$")
WORK_MODES = {"default-branch", "task-branch", "same-branch", "read-only", "ask"}

errors: list[str] = []


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def report(path: Path, line: int | None, message: str) -> None:
    loc = rel(path)
    if line is not None:
        loc = f"{loc}:{line}"
    errors.append(f"ERROR: {loc}: {message}")


def is_escaped_pipe(text: str, index: int) -> bool:
    backslashes = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == "\\":
        backslashes += 1
        cursor -= 1
    return backslashes % 2 == 1


def split_table_row(line: str) -> list[str]:
    raw = line.rstrip("\n")
    cells: list[str] = []
    current: list[str] = []

    for index, char in enumerate(raw):
        if char == "|" and not is_escaped_pipe(raw, index):
            cells.append("".join(current))
            current = []
        else:
            current.append(char)

    cells.append("".join(current))

    if cells and cells[0].strip() == "":
        cells = cells[1:]
    if cells and cells[-1].strip() == "":
        cells = cells[:-1]

    return [cell.strip().replace(r"\|", "|") for cell in cells]


def is_separator(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-{3,}:?", cell.strip() or "") for cell in cells)


def parse_required_table(path: Path, expected_header: list[str], table_name: str) -> list[tuple[int, dict[str, str]]]:
    if not path.exists():
        report(path, None, f"missing required {table_name}")
        return []

    lines = path.read_text(encoding="utf-8").splitlines()
    header_matches: list[int] = []

    for index, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue
        cells = split_table_row(line)
        if cells == expected_header:
            header_matches.append(index)

    if not header_matches:
        report(path, None, f"missing required {table_name} table with header: {' | '.join(expected_header)}")
        return []
    if len(header_matches) > 1:
        for index in header_matches[1:]:
            report(path, index + 1, f"duplicate {table_name} table header")

    header_index = header_matches[0]
    separator_index = header_index + 1
    if separator_index >= len(lines) or not lines[separator_index].lstrip().startswith("|"):
        report(path, header_index + 1, f"{table_name} header is missing a separator row")
        return []

    separator_cells = split_table_row(lines[separator_index])
    if len(separator_cells) != len(expected_header) or not is_separator(separator_cells):
        report(path, separator_index + 1, f"{table_name} separator row is malformed")
        return []

    rows: list[tuple[int, dict[str, str]]] = []
    for index in range(separator_index + 1, len(lines)):
        line = lines[index]
        if not line.lstrip().startswith("|"):
            break
        cells = split_table_row(line)
        if len(cells) != len(expected_header):
            report(
                path,
                index + 1,
                f"malformed {table_name} row: expected {len(expected_header)} columns, found {len(cells)}",
            )
            continue
        if is_separator(cells):
            report(path, index + 1, f"unexpected separator row inside {table_name} table")
            continue
        rows.append((index + 1, dict(zip(expected_header, cells))))

    if not rows:
        report(path, header_index + 1, f"{table_name} table has no repo rows")

    return rows


def valid_branch(value: str) -> bool:
    if value in {"N/A", "unknown"}:
        return True
    if not value or any(char.isspace() for char in value):
        return False
    if value.startswith("/") or value.endswith("/") or value.endswith("."):
        return False
    if value.endswith(".lock"):
        return False
    if ".." in value or "//" in value or "@{" in value:
        return False
    invalid_chars = set(" ~^:?*[\\")
    return not any(char in invalid_chars or ord(char) < 32 or ord(char) == 127 for char in value)


def validate_area_list(path: Path, line: int, value: str, label: str) -> None:
    if value == "N/A":
        return
    if not value:
        report(path, line, f"{label} must be comma-separated area slugs or N/A")
        return
    parts = [part.strip() for part in value.split(",")]
    if any(not part for part in parts):
        report(path, line, f"{label} contains an empty area slug")
        return
    for part in parts:
        if not AREA_RE.fullmatch(part):
            report(path, line, f"{label} contains malformed area slug '{part}'")


def load_registry() -> tuple[dict[str, dict[str, str]], bool]:
    path = ROOT / "repos.project"
    if not path.exists():
        if LOCAL_MODE:
            report(path, None, "missing repo registry; copy _base/repos.project.example to repos.project")
        return {}, False

    rows = parse_required_table(path, REGISTRY_HEADER, "repo registry")
    registry: dict[str, dict[str, str]] = {}
    seen: dict[str, int] = {}

    for line, row in rows:
        repo = row["Repo"]
        required = row["Required"]
        role = row["Role"]
        default_branch = row["Default branch"]
        integration_branch = row["Integration branch"]
        work_mode = row["Work mode"]
        areas = row["Areas"]

        if not SLUG_RE.fullmatch(repo):
            report(path, line, f"repo slug '{repo}' must match ^[a-z][a-z0-9-]*$")
        if repo in seen:
            report(path, line, f"duplicate repo slug '{repo}' also appears on line {seen[repo]}")
        else:
            seen[repo] = line
            registry[repo] = row

        if required not in {"yes", "no"}:
            report(path, line, f"Required for '{repo}' must be yes or no")
        if not role:
            report(path, line, f"Role for '{repo}' must not be empty")
        if not valid_branch(default_branch):
            report(path, line, f"Default branch for '{repo}' must be a branch name, N/A, or unknown")
        if not valid_branch(integration_branch):
            report(path, line, f"Integration branch for '{repo}' must be a branch name, N/A, or unknown")
        if work_mode not in WORK_MODES:
            report(path, line, f"Work mode for '{repo}' must be one of: {', '.join(sorted(WORK_MODES))}")
        validate_area_list(path, line, areas, f"Areas for '{repo}'")

    return registry, True


def parse_task_metadata(path: Path) -> list[tuple[int, str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    rows: list[tuple[int, str, str]] = []

    start = 0
    while start < len(lines) and not lines[start].strip():
        start += 1
    if start >= len(lines) or not lines[start].lstrip().startswith("|"):
        return rows

    header = split_table_row(lines[start])
    if header != TASK_META_HEADER:
        return rows

    if start + 1 >= len(lines):
        report(path, start + 1, "task metadata table is missing a separator row")
        return rows

    separator = split_table_row(lines[start + 1])
    if len(separator) != len(TASK_META_HEADER) or not is_separator(separator):
        report(path, start + 2, "task metadata separator row is malformed")
        return rows

    for index in range(start + 2, len(lines)):
        line = lines[index]
        if not line.lstrip().startswith("|"):
            break
        cells = split_table_row(line)
        if len(cells) != len(TASK_META_HEADER):
            report(path, index + 1, f"malformed task metadata row: expected 2 columns, found {len(cells)}")
            continue
        if is_separator(cells):
            report(path, index + 1, "unexpected separator row inside task metadata table")
            continue
        rows.append((index + 1, cells[0], cells[1]))

    return rows


def validate_repo_list(
    path: Path,
    line: int,
    value: str,
    registry: dict[str, dict[str, str]],
    registry_present: bool,
) -> None:
    if value == "N/A":
        return
    if not value:
        report(path, line, "Repos must be comma-separated repo slugs or N/A")
        return
    if not registry_present:
        report(path, line, "Repos metadata requires a committed repos.project registry")
        return

    parts = [part.strip() for part in value.split(",")]
    if any(not part for part in parts):
        report(path, line, "Repos contains an empty repo slug")
        return

    seen: set[str] = set()
    for part in parts:
        if not SLUG_RE.fullmatch(part):
            report(path, line, f"Repos contains malformed repo slug '{part}'")
            continue
        if part in seen:
            report(path, line, f"Repos contains duplicate repo slug '{part}'")
        seen.add(part)
        if part not in registry:
            report(path, line, f"Repos references unknown repo slug '{part}'")


def validate_task_repos(registry: dict[str, dict[str, str]], registry_present: bool) -> None:
    task_root = ROOT / "docs" / "tasks_manager"
    if not task_root.exists():
        return

    for directory_name in ["_todos", "_todos_archived"]:
        directory = task_root / directory_name
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.md")):
            for line, key, value in parse_task_metadata(path):
                if key.strip().lower() == "repos":
                    validate_repo_list(path, line, value, registry, registry_present)


def load_local_map(registry: dict[str, dict[str, str]]) -> dict[str, str]:
    path = ROOT / ".local" / "repos.map"
    mappings: dict[str, str] = {}
    seen: dict[str, int] = {}

    if not path.exists():
        report(path, None, "missing local repo map; copy _base/repos.map.example to .local/repos.map")
        return mappings

    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in line:
            report(path, index, "map entry must contain ':' and use '<repo-slug>: <absolute-path>'")
            continue
        slug, raw_path = [part.strip() for part in line.split(":", 1)]
        if not SLUG_RE.fullmatch(slug):
            report(path, index, f"repo slug '{slug}' must match ^[a-z][a-z0-9-]*$")
            continue
        if slug in seen:
            report(path, index, f"duplicate repo slug '{slug}' also appears on line {seen[slug]}")
            continue
        seen[slug] = index
        mappings[slug] = raw_path

        if slug not in registry:
            report(path, index, f"map references unknown repo slug '{slug}'")
        if not raw_path:
            report(path, index, f"path for '{slug}' must not be empty")
            continue
        if not os.path.isabs(raw_path):
            report(path, index, f"path for '{slug}' must be absolute")
            continue
        mapped_path = Path(raw_path)
        if not mapped_path.exists():
            report(path, index, f"path for '{slug}' does not exist: {raw_path}")
        elif not mapped_path.is_dir():
            report(path, index, f"path for '{slug}' must be a directory: {raw_path}")

    for slug, row in registry.items():
        if row["Required"] == "yes" and slug not in mappings:
            report(path, None, f"required repo '{slug}' is missing from local repo map")

    return mappings


def main() -> int:
    registry, registry_present = load_registry()
    validate_task_repos(registry, registry_present)
    if LOCAL_MODE:
        load_local_map(registry)

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    if LOCAL_MODE:
        print("OK  repos config valid, including local checkout map")
    else:
        print("OK  repos config valid")
    return 0


raise SystemExit(main())
PY
