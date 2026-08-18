"""Escape-aware Markdown table parsing helpers (stdlib only).

The single source of truth for splitting a Markdown table row into cells,
shared by `check_repos_config.sh`'s embedded validator and
`sync_todo_ledgers.py`. Unlike a naive `split("|")`/awk `FS="|"`, this
understands backslash-escaped pipes (`\\|`) so a cell may legitimately contain
a literal pipe, and both tools agree on the parse.

Keep this dependency-free (Python stdlib only): it is imported by scripts that
must run before any third-party package is guaranteed present.
"""

from __future__ import annotations

import re


def is_escaped_pipe(text: str, index: int) -> bool:
    """Return True if the `|` at ``text[index]`` is escaped by a backslash.

    A pipe is escaped when it is preceded by an odd number of backslashes.
    """
    backslashes = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == "\\":
        backslashes += 1
        cursor -= 1
    return backslashes % 2 == 1


def split_table_row(line: str) -> list[str]:
    """Split a Markdown table row into stripped, unescaped cell values.

    Leading/trailing empty cells (produced by the row's outer pipes) are
    dropped, each remaining cell is whitespace-stripped, and escaped pipes
    (`\\|`) are unescaped to a literal `|`.
    """
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
    """Return True if every cell is a Markdown table separator (`---`, `:-:`)."""
    return all(re.fullmatch(r":?-{3,}:?", cell.strip() or "") for cell in cells)


def metadata_pairs(lines: list[str]) -> list[tuple[str, str]]:
    """Yield (key, value) for every line that starts with a table pipe.

    Mirrors the ledger generator's metadata scan: any line beginning with `|`
    is treated as a `| Key | Value |` row, the first cell is the key and the
    second cell (if any) is the value. Lines are scanned wherever they appear
    (there is no fenced-code awareness, matching the historical awk behavior).
    """
    pairs: list[tuple[str, str]] = []
    for raw in lines:
        if not raw.startswith("|"):
            continue
        cells = split_table_row(raw)
        if not cells:
            continue
        key = cells[0]
        value = cells[1] if len(cells) > 1 else ""
        pairs.append((key, value))
    return pairs
