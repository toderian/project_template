#!/usr/bin/env bash
#
# Regenerate task ledgers and generated area status blocks from task files.
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
# Tool-agnostic: bash + awk + coreutils.

set -euo pipefail

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
  echo "No docs/tasks_manager/ directory at ${TM} - nothing to sync. Run /init first." >&2
  exit 0
fi

mkdir -p "${TODOS}" "${ARCHIVED}" "${AREAS_DIR}"

declare -A AREA_PREFIX AREA_DESC AREA_PAGE PREFIX_AREA AREA_ORDER
declare -a AREAS=()

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

page_abs_for() {
  local page="$1"
  if [[ "$page" = /* ]]; then
    realpath -m "$page"
  else
    realpath -m "${TM}/${page}"
  fi
}

page_rel_from_areas() {
  local page_abs="$1"
  realpath --relative-to="${AREAS_DIR}" "$page_abs"
}

read_areas() {
  if [[ -f "${AREAS_FILE}" ]]; then
    while IFS=$'\t' read -r area prefix desc page; do
      [[ -n "$area" ]] || continue
      [[ "$area" == "Area" ]] && continue
      [[ "$area" == "---" ]] && continue
      if [[ -z "$prefix" || -z "$page" ]]; then
        echo "WARNING: area row '${area}' is missing Prefix or Page in ${AREAS_FILE#${REPO_ROOT}/}" >&2
        continue
      fi
      if [[ -n "${AREA_PREFIX[$area]+x}" ]]; then
        echo "WARNING: duplicate area '${area}' in ${AREAS_FILE#${REPO_ROOT}/}" >&2
        continue
      fi
      if [[ -n "${PREFIX_AREA[$prefix]+x}" ]]; then
        echo "WARNING: duplicate prefix '${prefix}' for areas '${PREFIX_AREA[$prefix]}' and '${area}'" >&2
        continue
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
    AREA_PREFIX["global"]="T"
    AREA_DESC["global"]="Default, cross-area, and uncategorized work."
    AREA_PAGE["global"]="../areas/global.md"
    PREFIX_AREA["T"]="global"
    AREA_ORDER["global"]=0
    AREAS+=("global")
  fi
}

# Extract one task's fields as a unit-separated line:
#   taskid type area status priority updated title phase_done phase_total
extract_task() {
  awk '
    function trim(s) { gsub(/^[[:space:]]+|[[:space:]]+$/, "", s); return s }
    BEGIN { FS="|"; OFS = sprintf("%c", 28) }
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
      if (area == "")     area = "global"
      if (status == "")   status = "open"
      if (priority == "") priority = "medium"
      if (updated == "")  updated = "N/A"
      printf "%s%s%s%s%s%s%s%s%s%s%s%s%s%s%d%s%d\n",
        taskid, OFS, type, OFS, area, OFS, status, OFS, priority, OFS, updated, OFS, title, OFS, done, OFS, total
    }
  ' "$1"
}

declare -A TASK_COUNT TASK_FILE TASK_BASE TASK_DIR TASK_TYPE TASK_AREA TASK_STATUS TASK_PRIORITY TASK_UPDATED TASK_TITLE TASK_PHASE
declare -A AREA_OPEN AREA_INPROGRESS AREA_DONE AREA_NOW AREA_NEXT AREA_LATER
declare -a TASK_IDS=()

record_task() {
  local file="$1" dir_label="$2"
  local taskid type area status priority updated title done total base prefix expected_area
  base="$(basename "$file")"
  IFS=$'\034' read -r taskid type area status priority updated title done total < <(extract_task "$file")
  if [[ -z "$taskid" ]]; then
    echo "WARNING: task '${base}' is missing Task ID; skipped" >&2
    return 0
  fi

  TASK_COUNT["$taskid"]=$(( ${TASK_COUNT["$taskid"]:-0} + 1 ))
  if [[ ${TASK_COUNT["$taskid"]} -eq 1 ]]; then
    TASK_IDS+=("$taskid")
  else
    echo "WARNING: ambiguous task id '${taskid}' appears in multiple task files" >&2
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
    echo "WARNING: task '${base}' has malformed Task ID '${taskid}'" >&2
  elif [[ -n "${PREFIX_AREA[$prefix]+x}" ]]; then
    expected_area="${PREFIX_AREA[$prefix]}"
    if [[ "$area" != "$expected_area" ]]; then
      echo "WARNING: task '${taskid}' prefix '${prefix}' maps to area '${expected_area}' but metadata says '${area}'" >&2
    fi
  else
    echo "WARNING: task '${taskid}' uses unregistered prefix '${prefix}'" >&2
  fi

  if [[ -z "${AREA_PREFIX[$area]+x}" ]]; then
    echo "WARNING: task '${taskid}' uses unregistered area '${area}'" >&2
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

# ---- Rebuild _active.md ----
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
} > "${ACTIVE_LEDGER}"

# ---- Rebuild _done.md ----
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
} > "${DONE_LEDGER}"

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
    esac
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
    echo "WARNING: ambiguous roadmap task reference '${id}' appears ${ROADMAP_TASK_COUNT[$id]} times" >&2
    continue
  fi
  if [[ -z "${TASK_COUNT[$id]+x}" ]]; then
    echo "WARNING: missing roadmap task reference '${id}'" >&2
    continue
  fi
  if [[ ${TASK_COUNT[$id]} -gt 1 ]]; then
    echo "WARNING: ambiguous roadmap task reference '${id}' matches multiple files" >&2
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
    echo "WARNING: ambiguous roadmap inbox reference '${id}' appears ${ROADMAP_INBOX_COUNT[$id]} times" >&2
    continue
  fi
  if ! compgen -G "${INBOX}/${id}_"'*.md' >/dev/null && ! compgen -G "${INBOX_ARCHIVED}/${id}_"'*.md' >/dev/null; then
    echo "WARNING: missing roadmap inbox reference '${id}'" >&2
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
  tmp="$(mktemp)"
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
  echo "created area page: ${page_abs#${REPO_ROOT}/}"
}

# ---- Generate area pages ----
for area in "${AREAS[@]}"; do
  page_abs="$(page_abs_for "${AREA_PAGE[$area]}")"
  ensure_area_page "$area" "$page_abs"
  block="$(mktemp)"
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
  replace_block "$page_abs" '<!-- BEGIN generated-area-status -->' '<!-- END generated-area-status -->' "$block"
  rm -f "$block"
done

# ---- Generate area overview ----
if [[ ! -f "${AREAS_OVERVIEW}" ]]; then
  printf '# Areas Overview\n' > "${AREAS_OVERVIEW}"
fi

overview_block="$(mktemp)"
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

replace_block "${AREAS_OVERVIEW}" '<!-- BEGIN generated-area-overview -->' '<!-- END generated-area-overview -->' "$overview_block"
rm -f "$overview_block"

echo "Ledgers synced: ${ACTIVE_LEDGER#${REPO_ROOT}/}, ${DONE_LEDGER#${REPO_ROOT}/}, ${AREAS_OVERVIEW#${REPO_ROOT}/}"
