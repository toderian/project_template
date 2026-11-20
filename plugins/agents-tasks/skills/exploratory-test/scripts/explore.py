#!/usr/bin/env python3
"""Coverage ledger and finding fingerprints for the exploratory test loop.

  explore.py --root REPO [--dir DIR] build                      refresh cells, keep run state
  explore.py --root REPO [--dir DIR] next [N]                   the N cells run least recently (default 5)
  explore.py --root REPO [--dir DIR] record CELL VERDICT [FP]   pass | mismatch | blocked | filed | untestable
  explore.py --root REPO [--dir DIR] fingerprint CELL ROUTE ERROR
  explore.py --root REPO [--dir DIR] known FINGERPRINT          exit 0 and the file if known, exit 1 if new

DIR (default tests/e2e-explore) holds ledger.tsv, an optional cells.tsv (cell, leaf, expected: cells
the repo derives itself, such as a permission matrix) and an optional decisions.tsv (fingerprints the
owner classified as expected or as a harness fault). Cells built here: every design-leaf rule with a
Check line whose Holds line is Yes. A rule that holds partly or is a target is a known gap, not a cell.
"""
import argparse, csv, hashlib, re, sys
from datetime import datetime, timezone
from pathlib import Path

FIELDS = ["cell", "leaf", "expected", "last_run", "verdict", "runs", "finding"]
VERDICTS = ("pass", "mismatch", "blocked", "filed", "untestable")


def read_tsv(path):
    if not path.exists():
        return []
    with path.open() as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def cells(root, folder):
    for path in sorted((root / "docs/resources").glob("*/design/**/*.md")):
        for block in re.split(r"^### ", path.read_text(), flags=re.M)[1:]:
            rule = re.match(r"([A-Z][A-Z0-9]*-\d+)\b", block)
            holds = re.search(r"\*\*Holds\.\*\*\s*(\w+)", block)
            check = re.search(r"\*\*Check\.\*\*\s*(.+)", block)
            if rule and check and holds and holds.group(1).lower() == "yes":
                yield rule.group(1), str(path.relative_to(root)), check.group(1).strip()
    for row in read_tsv(folder / "cells.tsv"):
        yield row["cell"], row["leaf"], row["expected"]


def save(folder, rows):
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "ledger.tsv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows[key] for key in sorted(rows))


def fingerprint(cell, route, error):
    # Built from the oracle, the route and the error with numbers and identifiers removed, never from
    # prose: a reworded report of the same mismatch is the same finding.
    strip = lambda text: re.sub(r"\s+", " ", re.sub(r"[0-9a-f]{8,}|\d+", "N", text.lower())).strip()
    return hashlib.sha1(f"{cell}|{strip(route.split('?')[0])}|{strip(error)}".encode()).hexdigest()[:12]


def known(root, folder, value):
    files = [folder / "decisions.tsv"]
    for name in ("_inbox", "_inbox_archived", "_todos", "_todos_archived"):
        files += sorted((root / "docs/tasks_manager" / name).glob("*.md"))
    for path in files:
        if path.exists() and re.search(rf"^(Fingerprint: )?{value}\b", path.read_text(), flags=re.M):
            return path
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", required=True)
    parser.add_argument("--dir", default="tests/e2e-explore")
    parser.add_argument("command", choices=("build", "next", "record", "fingerprint", "known"))
    parser.add_argument("args", nargs="*")
    opts = parser.parse_args()
    root = Path(opts.root)
    folder = root / opts.dir
    rows = {row["cell"]: row for row in read_tsv(folder / "ledger.tsv")}
    args = opts.args
    if opts.command == "build" and not args:
        fresh = {}
        for cell, leaf, expected in cells(root, folder):
            old = rows.get(cell, {})
            fresh[cell] = {"cell": cell, "leaf": leaf, "expected": expected, "runs": old.get("runs", "0"),
                           **{key: old.get(key, "") for key in ("last_run", "verdict", "finding")}}
        save(folder, fresh)
        print(f"{len(fresh)} cells")
    elif opts.command == "next" and len(args) <= 1:
        # Never-run cells first, then the oldest; ties in a fixed scattered order so a batch spans leaves.
        order = sorted((row for row in rows.values() if row["verdict"] != "untestable"),
                       key=lambda row: (row["last_run"], hashlib.sha1(row["cell"].encode()).hexdigest()))
        for row in order[:int(args[0]) if args else 5]:
            print(f'{row["cell"]}\t{row["leaf"]}\t{row["expected"]}')
    elif opts.command == "record" and len(args) in (2, 3) and args[0] in rows and args[1] in VERDICTS:
        row = rows[args[0]]
        row.update(last_run=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), verdict=args[1],
                   runs=str(int(row["runs"]) + 1), finding=args[2] if len(args) == 3 else row["finding"])
        save(folder, rows)
    elif opts.command == "fingerprint" and len(args) == 3:
        print(fingerprint(*args))
    elif opts.command == "known" and len(args) == 1:
        found = known(root, folder, args[0])
        print(found.relative_to(root) if found else "new")
        return 0 if found else 1
    else:
        parser.error(f"wrong arguments for `{opts.command}`; see --help")
    return 0


if __name__ == "__main__":
    sys.exit(main())
