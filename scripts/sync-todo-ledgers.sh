#!/usr/bin/env bash
#
# Regenerate the todo ledgers from the todo files on disk.
#
#   docs/_active.md  <- fully rebuilt from docs/_todos/*.md  (open + in_progress)
#   docs/_done.md    <- reconciled from docs/_todos_archived/*.md (missing rows appended)
#
# The todo files are the source of truth; the ledgers are a derived index. Run this
# any time you suspect drift, after bulk edits, or from a Codex session (which has no
# hooks). Idempotent: re-running with no file changes produces no changes.
#
# Tool-agnostic: pure bash + awk, no dependencies beyond coreutils.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOCS="${REPO_ROOT}/docs"
TODOS="${DOCS}/_todos"
ARCHIVED="${DOCS}/_todos_archived"
ACTIVE_LEDGER="${DOCS}/_active.md"
DONE_LEDGER="${DOCS}/_done.md"

if [[ ! -d "${DOCS}" ]]; then
  echo "No docs/ directory at ${DOCS} — nothing to sync." >&2
  exit 0
fi

# Extract one todo's fields from a file as a single tab-separated line:
#   taskid  type  area  status  priority  updated  title  phasedone  phasetotal
extract() {
  awk '
    function trim(s) { gsub(/^[[:space:]]+|[[:space:]]+$/, "", s); return s }
    BEGIN { FS="|" }
    # metadata table rows: | Field | Value |
    /^\|/ {
      key = tolower(trim($2)); val = trim($3)
      if (key == "task id")  taskid = val
      if (key == "type")     type = val
      if (key == "area")     area = val
      if (key == "status")   status = val
      if (key == "priority") priority = val
      if (key == "updated")  updated = val
      next
    }
    # first H2 after the table is the title
    /^## / && title == "" { title = trim(substr($0, 4)) }
    # phase tracking: each "#### " starts a phase block; a phase is done when it has
    # at least one checkbox and all of them are checked.
    /^#### / {
      finalize()
      total++; inphase=1; hasitem=0; allchecked=1; next
    }
    /^(### |---|## )/ { finalize(); inphase=0 }
    inphase && /^[[:space:]]*-[[:space:]]*\[[ xX]\]/ {
      hasitem=1
      if ($0 ~ /\[[ ]\]/) allchecked=0
    }
    function finalize() {
      if (inphase && hasitem && allchecked) done++
      inphase=0
    }
    END {
      finalize()
      if (area == "")     area = "—"
      if (status == "")   status = "open"
      if (priority == "") priority = "—"
      if (updated == "")  updated = "—"
      printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%d\t%d\n",
        taskid, type, area, status, priority, updated, title, done, total
    }
  ' "$1"
}

# ---- Rebuild _active.md (open + in_progress) ----
active_header='# Active todos

Ledger of every `open` and `in_progress` todo — the backlog view. Sorted in_progress first, then by
priority, then Task ID. Rows are maintained as todos change status; rebuild any time with
`scripts/sync-todo-ledgers.sh`. The todo files in `docs/_todos/` remain the source of truth.

| Task ID | Type | Title | Area | Status | Priority | Phase | Updated | File |
|---------|------|-------|------|--------|----------|-------|---------|------|'

active_rows=""
if [[ -d "${TODOS}" ]]; then
  for f in "${TODOS}"/*.md; do
    [[ -e "$f" ]] || continue
    base="$(basename "$f")"
    IFS=$'\t' read -r taskid type area status priority updated title done total < <(extract "$f")
    [[ -z "$taskid" ]] && continue
    case "$status" in open|in_progress) ;; *) continue ;; esac
    # sort key: in_progress(0)/open(1), then priority high(0)/med(1)/low(2), then taskid
    skstatus=1; [[ "$status" == "in_progress" ]] && skstatus=0
    case "$priority" in high) skprio=0 ;; medium) skprio=1 ;; low) skprio=2 ;; *) skprio=3 ;; esac
    row="| ${taskid} | ${type} | ${title} | ${area} | ${status} | ${priority} | ${done}/${total} | ${updated} | [${base}](_todos/${base}) |"
    active_rows+="${skstatus}\t${skprio}\t${taskid}\t${row}"$'\n'
  done
fi

{
  printf '%s\n' "$active_header"
  if [[ -n "$active_rows" ]]; then
    printf '%b' "$active_rows" | sort -t$'\t' -k1,1n -k2,2n -k3,3 | cut -f4-
  fi
} > "${ACTIVE_LEDGER}"

# ---- Reconcile _done.md (append rows for archived files not already listed) ----
if [[ ! -f "${DONE_LEDGER}" ]]; then
  printf '%s\n' '# Done todos' '' \
    'Ledger of completed and cancelled todos. Newest row at the top.' '' \
    '| Task ID | Type | Title | Area | Completed | Commit | File |' \
    '|---------|------|-------|------|-----------|--------|------|' > "${DONE_LEDGER}"
fi

if [[ -d "${ARCHIVED}" ]]; then
  for f in "${ARCHIVED}"/*.md; do
    [[ -e "$f" ]] || continue
    base="$(basename "$f")"
    IFS=$'\t' read -r taskid type area status priority updated title done total < <(extract "$f")
    [[ -z "$taskid" ]] && continue
    # skip if this Task ID already has a row in the ledger
    if grep -qE "^\|[[:space:]]*${taskid}[[:space:]]*\|" "${DONE_LEDGER}"; then
      continue
    fi
    echo "| ${taskid} | ${type} | ${title} | ${area} | ${updated} | — | [${base}](_todos_archived/${base}) |" >> "${DONE_LEDGER}"
    echo "reconciled _done.md: added ${taskid} (${base})"
  done
fi

echo "Ledgers synced: ${ACTIVE_LEDGER#${REPO_ROOT}/}, ${DONE_LEDGER#${REPO_ROOT}/}"
