#!/usr/bin/env bash
#
# Seed docs/ and workbooks/ from _base/ without overwriting downstream-owned files.
# This is a portable replacement for GNU-specific recursive no-clobber copy snippets.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

python3 - "${REPO_ROOT}" <<'PY'
from pathlib import Path
import shutil
import sys

root = Path(sys.argv[1])

def seed_tree(src_root, dst_root):
    if not src_root.is_dir():
        raise SystemExit(f"error: {src_root} does not exist")

    dst_root.mkdir(parents=True, exist_ok=True)

    created = 0
    skipped = 0

    for src in sorted(src_root.rglob("*")):
        rel = src.relative_to(src_root)
        dst = dst_root / rel

        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            continue

        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            skipped += 1
            print(f"= {dst.relative_to(root)}")
            continue

        shutil.copy2(src, dst)
        created += 1
        print(f"+ {dst.relative_to(root)}")

    return created, skipped

docs_src_root = root / "_base" / "docs"
docs_dst_root = root / "docs"
created, skipped = seed_tree(docs_src_root, docs_dst_root)

primary_context = docs_dst_root / "resources" / "CONTEXT.md"
root_context = root / "CONTEXT.md"
root_context_template = root / "_base" / "CONTEXT.md.template"
if primary_context.exists():
    if root_context.exists():
        skipped += 1
        print(f"= {root_context.relative_to(root)}")
    else:
        shutil.copy2(root_context_template, root_context)
        created += 1
        print(f"+ {root_context.relative_to(root)}")

print(f"Seeded docs: created {created}, skipped {skipped}.")

workbooks_src_root = root / "_base" / "workbooks"
workbooks_dst_root = root / "workbooks"
created, skipped = seed_tree(workbooks_src_root, workbooks_dst_root)
print(f"Seeded workbooks: created {created}, skipped {skipped}.")
PY
