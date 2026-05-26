#!/usr/bin/env bash
#
# Regenerate task ledgers and generated area status blocks from task files.
#
# Default mode is permissive: it regenerates generated files and prints
# warnings for recoverable task-system drift.
#
# --check mode is strict and read-only: it validates metadata, references,
# lifecycle placement, completion fields, and generated output freshness.
#
# Sources of truth:
#   docs/tasks_manager/_areas.md
#   docs/tasks_manager/_roadmap.md
#   docs/tasks_manager/_todos/*.md
#   docs/tasks_manager/_todos_archived/*.md
#
# Generated outputs:
#   docs/tasks_manager/_active.md
#   docs/tasks_manager/_done.md
#   docs/areas/_overview.md
#   marker-delimited blocks in docs/areas/<slug>.md
#
# Portable prerequisites: bash, awk, sort, grep, cmp, python3.

set -euo pipefail

CHECK_MODE=0

usage() {
  cat <<'EOF'
Usage: sync-todo-ledgers.sh [--check]

Regenerate task ledgers and generated area status blocks.

Options:
  --check   Validate strictly without writing files.
  --help    Show this message.
EOF
}

case "${1:-}" in
  "") ;;
  --check) CHECK_MODE=1 ;;
  --help) usage; exit 0 ;;
  *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOCS="${REPO_ROOT}/docs"
TM="${DOCS}/tasks_manager"
TODOS="${TM}/_todos"
ARCHIVED="${TM}/_todos_archived"
INBOX="${TM}/_inbox"
INBOX_ARCHIVED="${TM}/_inbox_archived"
AREAS_FILE="${TM}/_areas.md"
ROADMAP="${TM}/_roadmap.md"
ACTIVE_LEDGER="${TM}/_active.md"
DONE_LEDGER="${TM}/_done.md"
AREAS_DIR="${DOCS}/areas"
AREAS_OVERVIEW="${AREAS_DIR}/_overview.md"

if [[ ! -d "${TM}" ]]; then
  if [[ "${CHECK_MODE}" -eq 1 ]]; then
    echo "No docs/tasks_manager/ directory at ${TM} - nothing to check. Run /init first." >&2
  else
    echo "No docs/tasks_manager/ directory at ${TM} - nothing to sync. Run /init first." >&2
  fi
  exit 0
fi

TMP_FILES=()
CHECK_ERRORS=0

cleanup() {
  if [[ ${#TMP_FILES[@]} -gt 0 ]]; then
    rm -f "${TMP_FILES[@]}"
  fi
}
trap cleanup EXIT

new_tmp() {
  local tmp
  tmp="$(mktemp)"
  TMP_FILES+=("$tmp")
  printf '%s' "$tmp"
}

rel_repo() {
  local path="$1"
  if [[ "$path" == "${REPO_ROOT}/"* ]]; then
    printf '%s' "${path#${REPO_ROOT}/}"
  else
    printf '%s' "$path"
  fi
}

warn() {
  echo "WARNING: $*" >&2
}

error() {
  echo "ERROR: $*" >&2
  CHECK_ERRORS=$((CHECK_ERRORS + 1))
}

validate_or_warn() {
  if [[ "${CHECK_MODE}" -eq 1 ]]; then
    error "$@"
  else
    warn "$@"
  fi
}

check_only_error() {
  if [[ "${CHECK_MODE}" -eq 1 ]]; then
    error "$@"
  fi
}

trim() {
  local s="$1"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s' "$s"
}

md_escape() {
  local s="$1"
  s="${s//|/\\|}"
  printf '%s' "$s"
}

path_abs() {
  python3 - "$1" <<'PY'
from pathlib import Path
import sys

print(Path(sys.argv[1]).expanduser().resolve(strict=False))
PY
}

path_rel() {
  python3 - "$1" "$2" <<'PY'
from pathlib import Path
import os
import sys

target = Path(sys.argv[1]).expanduser().resolve(strict=False)
start = Path(sys.argv[2]).expanduser().resolve(strict=False)
print(os.path.relpath(target, start))
PY
}

page_abs_for() {
  local page="$1"
  if [[ "$page" = /* ]]; then
    path_abs "$page"
  else
    path_abs "${TM}/${page}"
  fi
}

page_rel_from_areas() {
  local page_abs="$1"
  path_rel "$page_abs" "${AREAS_DIR}"
}

ensure_check_structure() {
  [[ -d "${TODOS}" ]] || check_only_error "missing task directory $(rel_repo "${TODOS}")"
  [[ -d "${ARCHIVED}" ]] || check_only_error "missing archived task directory $(rel_repo "${ARCHIVED}")"
  [[ -d "${INBOX}" ]] || check_only_error "missing inbox directory $(rel_repo "${INBOX}")"
  [[ -d "${INBOX_ARCHIVED}" ]] || check_only_error "missing archived inbox directory $(rel_repo "${INBOX_ARCHIVED}")"
  [[ -d "${AREAS_DIR}" ]] || check_only_error "missing areas directory $(rel_repo "${AREAS_DIR}")"
  [[ -f "${AREAS_FILE}" ]] || check_only_error "missing area registry $(rel_repo "${AREAS_FILE}")"
  [[ -f "${ROADMAP}" ]] || check_only_error "missing roadmap $(rel_repo "${ROADMAP}")"
  [[ -f "${ACTIVE_LEDGER}" ]] || check_only_error "missing active ledger $(rel_repo "${ACTIVE_LEDGER}")"
  [[ -f "${DONE_LEDGER}" ]] || check_only_error "missing done ledger $(rel_repo "${DONE_LEDGER}")"
  [[ -f "${AREAS_OVERVIEW}" ]] || check_only_error "missing area overview $(rel_repo "${AREAS_OVERVIEW}")"
}

if [[ "${CHECK_MODE}" -eq 1 ]]; then
  ensure_check_structure
else
  mkdir -p "${TODOS}" "${ARCHIVED}" "${INBOX}" "${INBOX_ARCHIVED}" "${AREAS_DIR}"
fi

declare -A AREA_PREFIX AREA_DESC AREA_PAGE PREFIX_AREA AREA_ORDER
declare -a AREAS=()

read_areas() {
  if [[ -f "${AREAS_FILE}" ]]; then
    while IFS=$'\t' read -r area prefix desc page; do
      [[ -n "$area" ]] || continue
      [[ "$area" == "Area" ]] && continue
      [[ "$area" == "---" ]] && continue
      if [[ -z "$prefix" || -z "$page" ]]; then
        validate_or_warn "area row '${area}' is missing Prefix or Page in $(rel_repo "${AREAS_FILE}")"
        continue
      fi
      if [[ ! "$area" =~ ^[a-z][a-z0-9-]*$ ]]; then
        validate_or_warn "area row '${area}' has malformed Area slug in $(rel_repo "${AREAS_FILE}")"
      fi
      if [[ ! "$prefix" =~ ^[A-Z][A-Z0-9]*$ ]]; then
        validate_or_warn "area row '${area}' has malformed Prefix '${prefix}'"
      fi
      if [[ -n "${AREA_PREFIX[$area]+x}" ]]; then
        validate_or_warn "duplicate area '${area}' in $(rel_repo "${AREAS_FILE}")"
        continue
      fi
      if [[ -n "${PREFIX_AREA[$prefix]+x}" ]]; then
        validate_or_warn "duplicate prefix '${prefix}' for areas '${PREFIX_AREA[$prefix]}' and '${area}'"
        continue
      fi
      if [[ "$prefix" == "T" && "$area" != "global" ]]; then
        validate_or_warn "prefix 'T' is reserved for area 'global' but is assigned to '${area}'"
      fi
      AREA_PREFIX["$area"]="$prefix"
      AREA_DESC["$area"]="$desc"
      AREA_PAGE["$area"]="$page"
      PREFIX_AREA["$prefix"]="$area"
      AREA_ORDER["$area"]="${#AREAS[@]}"
      AREAS+=("$area")
    done < <(awk '
      function trim(s) { gsub(/^[[:space:]]+|[[:space:]]+$/, "", s); return s }
      BEGIN { FS="|" }
      /^\|/ {
        a = trim($2); b = trim($3); c = trim($4); d = trim($5)
        if (a == "" || a ~ /^-+$/ || a == "Area") next
        printf "%s\t%s\t%s\t%s\n", a, b, c, d
      }
    ' "${AREAS_FILE}")
  fi

  if [[ ${#AREAS[@]} -eq 0 ]]; then
    if [[ "${CHECK_MODE}" -eq 1 && -f "${AREAS_FILE}" ]]; then
      error "area registry $(rel_repo "${AREAS_FILE}") contains no valid areas"
    fi
    AREA_PREFIX["global"]="T"
    AREA_DESC["global"]="Default, cross-area, and uncategorized work."
    AREA_PAGE["global"]="../areas/global.md"
    PREFIX_AREA["T"]="global"
    AREA_ORDER["global"]=0
    AREAS+=("global")
  fi
}

# Extract one task's fields as a unit-separated line:
# taskid type area created updated last_executed status priority owner blocked_by source source_ref title phase_done phase_total
extract_task() {
  awk '
    function trim(s) { gsub(/^[[:space:]]+|[[:space:]]+$/, "", s); return s }
    BEGIN { FS="|"; OFS = sprintf("%c", 28) }
    /^\|/ {
      key = tolower(trim($2)); val = trim($3)
      if (key == "task id")       taskid = val
      if (key == "type")          type = val
      if (key == "area")          area = val
      if (key == "created")       created = val
      if (key == "updated")       updated = val
      if (key == "last executed") last_executed = val
      if (key == "status")        status = val
      if (key == "priority")      priority = val
      if (key == "owner")         owner = val
      if (key == "blocked by")    blocked_by = val
      if (key == "source")        source = val
      if (key == "source ref")    source_ref = val
      next
    }
    /^## / && title == "" { title = trim(substr($0, 4)) }
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
      printf "%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%d%s%d\n",
        taskid, OFS, type, OFS, area, OFS, created, OFS, updated, OFS, last_executed, OFS,
        status, OFS, priority, OFS, owner, OFS, blocked_by, OFS, source, OFS, source_ref, OFS,
        title, OFS, done, OFS, total
    }
  ' "$1"
}

task_has_nonempty_section() {
  local file="$1" heading="$2"
  awk -v heading="$heading" '
    $0 ~ "^##[[:space:]]+" heading "[[:space:]]*$" { in_section=1; next }
    in_section && /^##[[:space:]]+/ { exit }
    in_section && NF { found=1 }
    END { exit found ? 0 : 1 }
  ' "$file"
}

validate_completion_archive() {
  local file="$1" taskid="$2" rel
  rel="$(rel_repo "$file")"

  if ! grep -qE '^##[[:space:]]+Completion harvest[[:space:]]*$' "$file"; then
    validate_or_warn "archived task '${taskid}' in ${rel} is missing a Completion harvest section"
    return
  fi
  if ! grep -qiE '^\|[[:space:]]*Resource updates[[:space:]]*\|[[:space:]]*(None|N/A|docs/resources/[^|]+)[[:space:]]*\|' "$file"; then
    validate_or_warn "archived task '${taskid}' in ${rel} is missing explicit Completion harvest Resource updates"
  fi
  if ! grep -qiE '^\|[[:space:]]*Area updates[[:space:]]*\|[[:space:]]*(None|N/A|docs/areas/[^|]+)[[:space:]]*\|' "$file"; then
    validate_or_warn "archived task '${taskid}' in ${rel} is missing explicit Completion harvest Area updates"
  fi
  if ! grep -qiE '^\|[[:space:]]*Follow-ups[[:space:]]*\|[[:space:]]*(None|N/A|I-[0-9]{3,}[^|]*)[[:space:]]*\|' "$file"; then
    validate_or_warn "archived task '${taskid}' in ${rel} is missing explicit Completion harvest Follow-ups"
  fi
  if ! grep -qiE '^\|[[:space:]]*Notable decisions/deviations[[:space:]]*\|[[:space:]]*(None|N/A|[^|]*[[:alnum:]][^|]*)[[:space:]]*\|' "$file"; then
    validate_or_warn "archived task '${taskid}' in ${rel} is missing explicit Completion harvest Notable decisions/deviations"
  fi
  if ! grep -qE '^##[[:space:]]+Completion summary[[:space:]]*$' "$file"; then
    validate_or_warn "archived task '${taskid}' in ${rel} is missing a Completion summary section"
  elif ! task_has_nonempty_section "$file" "Completion summary"; then
    validate_or_warn "archived task '${taskid}' in ${rel} has an empty Completion summary section"
  fi
}

validate_task_metadata() {
  local file="$1" base="$2" taskid="$3" type="$4" area="$5" created="$6" updated="$7" last_executed="$8"
  local status="$9" priority="${10}" owner="${11}" blocked_by="${12}" source="${13}" source_ref="${14}" title="${15}"
  local required_missing=0 rel
  rel="$(rel_repo "$file")"

  if [[ -z "$taskid" ]]; then
    validate_or_warn "task '${base}' is missing Task ID"
    required_missing=1
  fi
  if [[ -z "$type" ]]; then
    validate_or_warn "task '${base}' is missing Type"
    required_missing=1
  fi
  if [[ -z "$area" ]]; then
    validate_or_warn "task '${base}' is missing Area"
    required_missing=1
  fi
  if [[ -z "$created" ]]; then
    validate_or_warn "task '${base}' is missing Created"
    required_missing=1
  fi
  if [[ -z "$updated" || "$updated" == "N/A" ]]; then
    validate_or_warn "task '${base}' is missing Updated"
    required_missing=1
  fi
  if [[ -z "$last_executed" ]]; then
    validate_or_warn "task '${base}' is missing Last executed"
    required_missing=1
  fi
  if [[ -z "$status" ]]; then
    validate_or_warn "task '${base}' is missing Status"
    required_missing=1
  fi
  if [[ -z "$priority" ]]; then
    validate_or_warn "task '${base}' is missing Priority"
    required_missing=1
  fi
  if [[ -z "$owner" ]]; then
    validate_or_warn "task '${base}' is missing Owner"
    required_missing=1
  fi
  if [[ -z "$blocked_by" ]]; then
    validate_or_warn "task '${base}' is missing Blocked by"
    required_missing=1
  fi
  if [[ -z "$source" ]]; then
    validate_or_warn "task '${base}' is missing Source"
    required_missing=1
  fi
  if [[ -z "$source_ref" ]]; then
    validate_or_warn "task '${base}' is missing Source ref"
    required_missing=1
  fi
  if [[ -z "$title" ]]; then
    validate_or_warn "task '${base}' in ${rel} is missing a title heading"
  fi

  [[ "$type" =~ ^[FDCR]$ || -z "$type" ]] || validate_or_warn "task '${base}' has malformed Type '${type}'"
  [[ "$status" =~ ^(open|in_progress|done|cancelled)$ || -z "$status" ]] || validate_or_warn "task '${base}' has malformed Status '${status}'"
  [[ "$priority" =~ ^(high|medium|low)$ || -z "$priority" ]] || validate_or_warn "task '${base}' has malformed Priority '${priority}'"
  [[ "$created" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(:[0-9]{2})? || -z "$created" ]] || validate_or_warn "task '${base}' has malformed Created '${created}'"
  [[ "$updated" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(:[0-9]{2})? || -z "$updated" ]] || validate_or_warn "task '${base}' has malformed Updated '${updated}'"
  [[ "$last_executed" == "N/A" || "$last_executed" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(:[0-9]{2})? || -z "$last_executed" ]] || validate_or_warn "task '${base}' has malformed Last executed '${last_executed}'"

  if [[ "$required_missing" -eq 0 && -n "$taskid" && -n "$type" ]]; then
    if [[ ! "$base" =~ ^${taskid}-${type}_[a-z0-9]([a-z0-9-]*[a-z0-9])?\.md$ ]]; then
      validate_or_warn "task '${base}' filename does not match metadata Task ID '${taskid}' and Type '${type}'"
    fi
  fi
}

declare -A TASK_COUNT TASK_FILE TASK_BASE TASK_DIR TASK_TYPE TASK_AREA TASK_STATUS TASK_PRIORITY TASK_UPDATED TASK_TITLE TASK_PHASE
declare -A AREA_OPEN AREA_INPROGRESS AREA_DONE AREA_NOW AREA_NEXT AREA_LATER
declare -a TASK_IDS=()

record_task() {
  local file="$1" dir_label="$2"
  local taskid type area created updated last_executed status priority owner blocked_by source source_ref title done total base prefix expected_area
  base="$(basename "$file")"

  IFS=$'\034' read -r taskid type area created updated last_executed status priority owner blocked_by source source_ref title done total < <(extract_task "$file")

  validate_task_metadata "$file" "$base" "$taskid" "$type" "$area" "$created" "$updated" "$last_executed" "$status" "$priority" "$owner" "$blocked_by" "$source" "$source_ref" "$title"

  if [[ -z "$taskid" ]]; then
    return 0
  fi

  [[ -n "$area" ]] || area="global"
  [[ -n "$status" ]] || status="open"
  [[ -n "$priority" ]] || priority="medium"
  [[ -n "$updated" ]] || updated="N/A"

  TASK_COUNT["$taskid"]=$(( ${TASK_COUNT["$taskid"]:-0} + 1 ))
  if [[ ${TASK_COUNT["$taskid"]} -eq 1 ]]; then
    TASK_IDS+=("$taskid")
  else
    validate_or_warn "ambiguous task id '${taskid}' appears in multiple task files"
  fi

  TASK_FILE["$taskid"]="$file"
  TASK_BASE["$taskid"]="$base"
  TASK_DIR["$taskid"]="$dir_label"
  TASK_TYPE["$taskid"]="$type"
  TASK_AREA["$taskid"]="$area"
  TASK_STATUS["$taskid"]="$status"
  TASK_PRIORITY["$taskid"]="$priority"
  TASK_UPDATED["$taskid"]="$updated"
  TASK_TITLE["$taskid"]="$title"
  TASK_PHASE["$taskid"]="${done}/${total}"

  prefix="${taskid%-*}"
  if [[ "$prefix" == "$taskid" || ! "$taskid" =~ ^[A-Z][A-Z0-9]*-[0-9]{3,}$ ]]; then
    validate_or_warn "task '${base}' has malformed Task ID '${taskid}'"
  elif [[ -n "${PREFIX_AREA[$prefix]+x}" ]]; then
    expected_area="${PREFIX_AREA[$prefix]}"
    if [[ "$area" != "$expected_area" ]]; then
      validate_or_warn "task '${taskid}' prefix '${prefix}' maps to area '${expected_area}' but metadata says '${area}'"
    fi
  else
    validate_or_warn "task '${taskid}' uses unregistered prefix '${prefix}'"
  fi

  if [[ -z "${AREA_PREFIX[$area]+x}" ]]; then
    validate_or_warn "task '${taskid}' uses unregistered area '${area}'"
  fi

  case "$dir_label:$status" in
    _todos:open|_todos:in_progress|_todos_archived:done|_todos_archived:cancelled) ;;
    _todos:done|_todos:cancelled)
      validate_or_warn "terminal task '${taskid}' has Status '${status}' but is still in docs/tasks_manager/_todos/"
      ;;
    _todos_archived:open|_todos_archived:in_progress)
      validate_or_warn "active task '${taskid}' has Status '${status}' but is in docs/tasks_manager/_todos_archived/"
      ;;
  esac

  if [[ "$dir_label" == "_todos_archived" ]]; then
    validate_completion_archive "$file" "$taskid"
  fi

  case "$status" in
    open) AREA_OPEN["$area"]=$(( ${AREA_OPEN["$area"]:-0} + 1 )) ;;
    in_progress) AREA_INPROGRESS["$area"]=$(( ${AREA_INPROGRESS["$area"]:-0} + 1 )) ;;
    done|cancelled) AREA_DONE["$area"]=$(( ${AREA_DONE["$area"]:-0} + 1 )) ;;
  esac
}

read_areas

for f in "${TODOS}"/*.md; do
  [[ -e "$f" ]] || continue
  record_task "$f" "_todos"
done

for f in "${ARCHIVED}"/*.md; do
  [[ -e "$f" ]] || continue
  record_task "$f" "_todos_archived"
done

write_or_check() {
  local target="$1" source="$2" label="$3"
  if [[ "${CHECK_MODE}" -eq 1 ]]; then
    if [[ ! -f "$target" ]]; then
      error "${label} is missing at $(rel_repo "$target")"
      return
    fi
    if ! cmp -s "$source" "$target"; then
      error "${label} is stale at $(rel_repo "$target"); run scripts/sync-todo-ledgers.sh"
    fi
  else
    cp "$source" "$target"
  fi
}

# ---- Render _active.md ----
active_tmp="$(new_tmp)"
active_header='# Active tasks

Ledger of every `open` and `in_progress` task - the backlog view. Sorted in_progress first, then by
priority, then Task ID. Rows are maintained as tasks change status; rebuild any time with
`scripts/sync-todo-ledgers.sh`. The task files in `docs/tasks_manager/_todos/` remain the source of truth.

| Task ID | Type | Title | Area | Status | Priority | Phase | Updated | File |
|---------|------|-------|------|--------|----------|-------|---------|------|'

active_rows=""
for taskid in "${TASK_IDS[@]}"; do
  [[ "${TASK_COUNT[$taskid]}" -eq 1 ]] || continue
  [[ "${TASK_DIR[$taskid]}" == "_todos" ]] || continue
  status="${TASK_STATUS[$taskid]}"
  case "$status" in open|in_progress) ;; *) continue ;; esac
  skstatus=1; [[ "$status" == "in_progress" ]] && skstatus=0
  case "${TASK_PRIORITY[$taskid]}" in high) skprio=0 ;; medium) skprio=1 ;; low) skprio=2 ;; *) skprio=3 ;; esac
  row="| ${taskid} | ${TASK_TYPE[$taskid]} | $(md_escape "${TASK_TITLE[$taskid]}") | ${TASK_AREA[$taskid]} | ${status} | ${TASK_PRIORITY[$taskid]} | ${TASK_PHASE[$taskid]} | ${TASK_UPDATED[$taskid]} | [${TASK_BASE[$taskid]}](_todos/${TASK_BASE[$taskid]}) |"
  active_rows+="${skstatus}\t${skprio}\t${taskid}\t${row}"$'\n'
done

{
  printf '%s\n' "$active_header"
  if [[ -n "$active_rows" ]]; then
    printf '%b' "$active_rows" | sort -t$'\t' -k1,1n -k2,2n -k3,3 | cut -f4-
  fi
} > "${active_tmp}"
write_or_check "${ACTIVE_LEDGER}" "${active_tmp}" "active ledger"

# ---- Render _done.md ----
done_tmp="$(new_tmp)"
done_header='# Done tasks

Ledger of completed and cancelled tasks. Newest row at the top. Rebuild any time with
`scripts/sync-todo-ledgers.sh`.

| Task ID | Type | Title | Area | Completed | Commit | File |
|---------|------|-------|------|-----------|--------|------|'

done_rows=""
for taskid in "${TASK_IDS[@]}"; do
  [[ "${TASK_COUNT[$taskid]}" -eq 1 ]] || continue
  [[ "${TASK_DIR[$taskid]}" == "_todos_archived" ]] || continue
  status="${TASK_STATUS[$taskid]}"
  case "$status" in done|cancelled) ;; *) continue ;; esac
  row="| ${taskid} | ${TASK_TYPE[$taskid]} | $(md_escape "${TASK_TITLE[$taskid]}") | ${TASK_AREA[$taskid]} | ${TASK_UPDATED[$taskid]} | - | [${TASK_BASE[$taskid]}](_todos_archived/${TASK_BASE[$taskid]}) |"
  done_rows+="${TASK_UPDATED[$taskid]}\t${taskid}\t${row}"$'\n'
done

{
  printf '%s\n' "$done_header"
  if [[ -n "$done_rows" ]]; then
    printf '%b' "$done_rows" | sort -t$'\t' -k1,1r -k2,2r | cut -f3-
  fi
} > "${done_tmp}"
write_or_check "${DONE_LEDGER}" "${done_tmp}" "done ledger"

# ---- Roadmap diagnostics and horizon assignment ----
declare -A ROADMAP_TASK_COUNT ROADMAP_TASK_HORIZON ROADMAP_INBOX_COUNT
declare -a ROADMAP_TASK_IDS ROADMAP_INBOX_IDS

if [[ -f "${ROADMAP}" ]]; then
  horizon=""
  while IFS= read -r line; do
    case "$line" in
      "## Now"*) horizon="Now"; continue ;;
      "## Next"*) horizon="Next"; continue ;;
      "## Later"*) horizon="Later"; continue ;;
      "## "*) horizon="__invalid__"; continue ;;
    esac

    if [[ "$horizon" == "__invalid__" ]]; then
      while IFS= read -r id; do
        [[ -n "$id" ]] || continue
        validate_or_warn "roadmap reference '${id}' appears outside a Now/Next/Later horizon"
      done < <(printf '%s\n' "$line" | grep -Eo '([A-Z][A-Z0-9]*|I)-[0-9]{3,}' | sort -u || true)
      continue
    fi

    [[ -n "$horizon" ]] || continue

    while IFS= read -r id; do
      [[ -n "$id" ]] || continue
      [[ "$id" =~ ^I-[0-9]{3,}$ ]] && continue
      if [[ -z "${ROADMAP_TASK_COUNT[$id]+x}" ]]; then
        ROADMAP_TASK_IDS+=("$id")
      fi
      ROADMAP_TASK_COUNT["$id"]=$(( ${ROADMAP_TASK_COUNT["$id"]:-0} + 1 ))
      ROADMAP_TASK_HORIZON["$id"]="${ROADMAP_TASK_HORIZON[$id]:-$horizon}"
    done < <(printf '%s\n' "$line" | grep -Eo '[A-Z][A-Z0-9]*-[0-9]{3,}' | sort -u || true)

    while IFS= read -r id; do
      [[ -n "$id" ]] || continue
      if [[ -z "${ROADMAP_INBOX_COUNT[$id]+x}" ]]; then
        ROADMAP_INBOX_IDS+=("$id")
      fi
      ROADMAP_INBOX_COUNT["$id"]=$(( ${ROADMAP_INBOX_COUNT["$id"]:-0} + 1 ))
    done < <(printf '%s\n' "$line" | grep -Eo 'I-[0-9]{3,}' | sort -u || true)
  done < "${ROADMAP}"
fi

for id in "${ROADMAP_TASK_IDS[@]}"; do
  if [[ ${ROADMAP_TASK_COUNT[$id]} -gt 1 ]]; then
    validate_or_warn "ambiguous roadmap task reference '${id}' appears ${ROADMAP_TASK_COUNT[$id]} times"
    continue
  fi
  if [[ -z "${TASK_COUNT[$id]+x}" ]]; then
    validate_or_warn "missing roadmap task reference '${id}'"
    continue
  fi
  if [[ ${TASK_COUNT[$id]} -gt 1 ]]; then
    validate_or_warn "ambiguous roadmap task reference '${id}' matches multiple files"
    continue
  fi
  area="${TASK_AREA[$id]}"
  case "${ROADMAP_TASK_HORIZON[$id]}" in
    Now) AREA_NOW["$area"]=$(( ${AREA_NOW["$area"]:-0} + 1 )) ;;
    Next) AREA_NEXT["$area"]=$(( ${AREA_NEXT["$area"]:-0} + 1 )) ;;
    Later) AREA_LATER["$area"]=$(( ${AREA_LATER["$area"]:-0} + 1 )) ;;
  esac
done

for id in "${ROADMAP_INBOX_IDS[@]}"; do
  if [[ ${ROADMAP_INBOX_COUNT[$id]} -gt 1 ]]; then
    validate_or_warn "ambiguous roadmap inbox reference '${id}' appears ${ROADMAP_INBOX_COUNT[$id]} times"
    continue
  fi
  if ! compgen -G "${INBOX}/${id}_"'*.md' >/dev/null && ! compgen -G "${INBOX_ARCHIVED}/${id}_"'*.md' >/dev/null; then
    validate_or_warn "missing roadmap inbox reference '${id}'"
  fi
done

task_link_from_area() {
  local taskid="$1"
  local target="../tasks_manager/${TASK_DIR[$taskid]}/${TASK_BASE[$taskid]}"
  printf '[%s](%s)' "$taskid" "$target"
}

task_bullet() {
  local taskid="$1"
  printf -- '- %s (%s) %s - %s, %s, phase %s\n' \
    "$(task_link_from_area "$taskid")" \
    "${TASK_TYPE[$taskid]}" \
    "$(md_escape "${TASK_TITLE[$taskid]}")" \
    "${TASK_STATUS[$taskid]}" \
    "${TASK_PRIORITY[$taskid]}" \
    "${TASK_PHASE[$taskid]}"
}

section_for_area_horizon() {
  local area="$1" horizon="$2"
  local found=0 taskid
  for taskid in "${ROADMAP_TASK_IDS[@]}"; do
    [[ "${ROADMAP_TASK_COUNT[$taskid]}" -eq 1 ]] || continue
    [[ "${TASK_COUNT[$taskid]:-0}" -eq 1 ]] || continue
    [[ "${TASK_AREA[$taskid]}" == "$area" ]] || continue
    [[ "${ROADMAP_TASK_HORIZON[$taskid]}" == "$horizon" ]] || continue
    case "${TASK_STATUS[$taskid]}" in done|cancelled) continue ;; esac
    task_bullet "$taskid"
    found=1
  done
  [[ $found -eq 1 ]] || printf '_No tasks._\n'
}

section_for_area_unscheduled() {
  local area="$1"
  local found=0 taskid scheduled
  for taskid in "${TASK_IDS[@]}"; do
    [[ "${TASK_COUNT[$taskid]}" -eq 1 ]] || continue
    [[ "${TASK_AREA[$taskid]}" == "$area" ]] || continue
    case "${TASK_STATUS[$taskid]}" in open|in_progress) ;; *) continue ;; esac
    scheduled=0
    if [[ -n "${ROADMAP_TASK_COUNT[$taskid]+x}" && "${ROADMAP_TASK_COUNT[$taskid]}" -eq 1 ]]; then
      scheduled=1
    fi
    [[ $scheduled -eq 0 ]] || continue
    task_bullet "$taskid"
    found=1
  done
  [[ $found -eq 1 ]] || printf '_No tasks._\n'
}

replace_block() {
  local file="$1" begin="$2" end="$3" block_file="$4" tmp
  tmp="$(new_tmp)"
  awk -v begin="$begin" -v end="$end" -v block_file="$block_file" '
    BEGIN {
      while ((getline line < block_file) > 0) block = block line ORS
      close(block_file)
    }
    index($0, begin) {
      print begin
      printf "%s", block
      in_block = 1
      seen = 1
      next
    }
    index($0, end) {
      print end
      in_block = 0
      next
    }
    !in_block { print }
    END {
      if (!seen) {
        print ""
        print begin
        printf "%s", block
        print end
      }
    }
  ' "$file" > "$tmp"
  mv "$tmp" "$file"
}

ensure_area_page() {
  local area="$1" page_abs="$2" title
  if [[ -f "$page_abs" ]]; then
    return 0
  fi
  mkdir -p "$(dirname "$page_abs")"
  title="${area//-/ }"
  {
    printf '# %s\n\n' "$title"
    printf '%s\n\n' "${AREA_DESC[$area]}"
    printf '<!-- BEGIN generated-area-status -->\n'
    printf '_Generated by `scripts/sync-todo-ledgers.sh`. Do not edit this block by hand._\n\n'
    printf '## Now\n\n_No tasks._\n\n'
    printf '## Next\n\n_No tasks._\n\n'
    printf '## Later\n\n_No tasks._\n\n'
    printf '## Unscheduled\n\n_No tasks._\n'
    printf '<!-- END generated-area-status -->\n'
  } > "$page_abs"
  echo "created area page: $(rel_repo "$page_abs")"
}

# ---- Generate/check area pages ----
for area in "${AREAS[@]}"; do
  page_abs="$(page_abs_for "${AREA_PAGE[$area]}")"
  block="$(new_tmp)"
  {
    printf '_Generated by `scripts/sync-todo-ledgers.sh`. Do not edit this block by hand._\n\n'
    printf '## Now\n\n'
    section_for_area_horizon "$area" "Now"
    printf '\n## Next\n\n'
    section_for_area_horizon "$area" "Next"
    printf '\n## Later\n\n'
    section_for_area_horizon "$area" "Later"
    printf '\n## Unscheduled\n\n'
    section_for_area_unscheduled "$area"
  } > "$block"

  if [[ "${CHECK_MODE}" -eq 1 ]]; then
    if [[ ! -f "$page_abs" ]]; then
      error "area page for '${area}' is missing at $(rel_repo "$page_abs")"
      continue
    fi
    expected_page="$(new_tmp)"
    cp "$page_abs" "$expected_page"
    replace_block "$expected_page" '<!-- BEGIN generated-area-status -->' '<!-- END generated-area-status -->' "$block"
    write_or_check "$page_abs" "$expected_page" "generated area status block for '${area}'"
  else
    ensure_area_page "$area" "$page_abs"
    replace_block "$page_abs" '<!-- BEGIN generated-area-status -->' '<!-- END generated-area-status -->' "$block"
  fi
done

# ---- Generate/check area overview ----
overview_block="$(new_tmp)"
{
  printf '_Generated by `scripts/sync-todo-ledgers.sh`. Do not edit this block by hand._\n\n'
  printf '| Area | Prefix | Description | Now | Next | Later | Open | In Progress | Done | Page |\n'
  printf '|------|--------|-------------|-----|------|-------|------|-------------|------|------|\n'
  for area in "${AREAS[@]}"; do
    page_abs="$(page_abs_for "${AREA_PAGE[$area]}")"
    rel="$(page_rel_from_areas "$page_abs")"
    printf '| %s | %s | %s | %s | %s | %s | %s | %s | %s | [%s](%s) |\n' \
      "$area" \
      "${AREA_PREFIX[$area]}" \
      "$(md_escape "${AREA_DESC[$area]}")" \
      "${AREA_NOW[$area]:-0}" \
      "${AREA_NEXT[$area]:-0}" \
      "${AREA_LATER[$area]:-0}" \
      "${AREA_OPEN[$area]:-0}" \
      "${AREA_INPROGRESS[$area]:-0}" \
      "${AREA_DONE[$area]:-0}" \
      "$(basename "$rel")" \
      "$rel"
  done
} > "$overview_block"

if [[ "${CHECK_MODE}" -eq 1 ]]; then
  if [[ ! -f "${AREAS_OVERVIEW}" ]]; then
    error "area overview is missing at $(rel_repo "${AREAS_OVERVIEW}")"
  else
    expected_overview="$(new_tmp)"
    cp "${AREAS_OVERVIEW}" "$expected_overview"
    replace_block "$expected_overview" '<!-- BEGIN generated-area-overview -->' '<!-- END generated-area-overview -->' "$overview_block"
    write_or_check "${AREAS_OVERVIEW}" "$expected_overview" "generated area overview block"
  fi
else
  if [[ ! -f "${AREAS_OVERVIEW}" ]]; then
    printf '# Areas Overview\n' > "${AREAS_OVERVIEW}"
  fi
  replace_block "${AREAS_OVERVIEW}" '<!-- BEGIN generated-area-overview -->' '<!-- END generated-area-overview -->' "$overview_block"
fi

if [[ "${CHECK_MODE}" -eq 1 ]]; then
  if (( CHECK_ERRORS > 0 )); then
    echo "Task ledger validation failed: ${CHECK_ERRORS} issue(s)." >&2
    exit 1
  fi
  echo "OK task ledgers valid"
else
  echo "Ledgers synced: $(rel_repo "${ACTIVE_LEDGER}"), $(rel_repo "${DONE_LEDGER}"), $(rel_repo "${AREAS_OVERVIEW}")"
fi
