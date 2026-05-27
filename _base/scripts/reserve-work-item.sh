#!/usr/bin/env bash
#
# Atomically reserve an inbox idea or task filename.
#
# Usage:
#   _base/scripts/reserve-work-item.sh inbox <slug>
#   _base/scripts/reserve-work-item.sh task <PREFIX> <TYPE> <slug>
#
# The script creates the reserved file as an empty placeholder and prints its
# repo-relative path. Fill the placeholder immediately using the appropriate
# inbox/task template. If an agent is interrupted after reservation, strict
# ledger validation will catch the empty placeholder.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TM="${REPO_ROOT}/docs/tasks_manager"
TODOS="${TM}/_todos"
ARCHIVED="${TM}/_todos_archived"
INBOX="${TM}/_inbox"
INBOX_ARCHIVED="${TM}/_inbox_archived"
AREAS_FILE="${TM}/_areas.md"
LOCK_DIR="${TM}/.reserve-work-item.lock"

usage() {
  cat <<'EOF'
Usage:
  _base/scripts/reserve-work-item.sh inbox <slug>
  _base/scripts/reserve-work-item.sh task <PREFIX> <TYPE> <slug>

Examples:
  _base/scripts/reserve-work-item.sh inbox dark-mode-toggle
  _base/scripts/reserve-work-item.sh task AUTH F login-session

The task manager must already be initialized. Run /init first if
docs/tasks_manager/ is missing.
EOF
}

rel_repo() {
  local path="$1"
  if [[ "$path" == "${REPO_ROOT}/"* ]]; then
    printf '%s' "${path#${REPO_ROOT}/}"
  else
    printf '%s' "$path"
  fi
}

die() {
  echo "error: $*" >&2
  exit 2
}

require_initialized() {
  [[ -d "${TM}" ]] || die "docs/tasks_manager/ is missing; run /init first"
  [[ -d "${TODOS}" ]] || die "$(rel_repo "${TODOS}") is missing; run /init first"
  [[ -d "${ARCHIVED}" ]] || die "$(rel_repo "${ARCHIVED}") is missing; run /init first"
  [[ -d "${INBOX}" ]] || die "$(rel_repo "${INBOX}") is missing; run /init first"
  [[ -d "${INBOX_ARCHIVED}" ]] || die "$(rel_repo "${INBOX_ARCHIVED}") is missing; run /init first"
  [[ -f "${AREAS_FILE}" ]] || die "$(rel_repo "${AREAS_FILE}") is missing; run /init first"
}

validate_slug() {
  local slug="$1"
  [[ "$slug" =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ ]] || die "slug must be lowercase hyphenated text"
  ((${#slug} < 50)) || die "slug must be under 50 characters"
}

validate_prefix_registered() {
  local prefix="$1"
  [[ "$prefix" =~ ^[A-Z][A-Z0-9]*$ ]] || die "prefix must be uppercase alphanumeric and start with a letter"
  [[ "$prefix" != "I" ]] || die "prefix I is reserved for inbox IDs"
  awk -v want="$prefix" '
    function trim(s) { gsub(/^[[:space:]]+|[[:space:]]+$/, "", s); return s }
    BEGIN { FS="|" }
    /^\|/ {
      prefix = trim($3)
      if (prefix == want) found = 1
    }
    END { exit found ? 0 : 1 }
  ' "${AREAS_FILE}" || die "prefix ${prefix} is not registered in $(rel_repo "${AREAS_FILE}")"
}

pad_id() {
  local n="$1"
  if (( n < 1000 )); then
    printf '%03d' "$n"
  else
    printf '%d' "$n"
  fi
}

highest_inbox_id() {
  local high=0 base n
  for path in "${INBOX}"/I-*_*.md "${INBOX_ARCHIVED}"/I-*_*.md; do
    [[ -e "$path" ]] || continue
    base="$(basename "$path")"
    [[ "$base" =~ ^I-([0-9]+)_ ]] || continue
    n=$((10#${BASH_REMATCH[1]}))
    (( n > high )) && high="$n"
  done
  printf '%s' "$high"
}

highest_task_id() {
  local prefix="$1" high=0 base n
  for path in "${TODOS}/${prefix}"-*-*_*.md "${ARCHIVED}/${prefix}"-*-*_*.md; do
    [[ -e "$path" ]] || continue
    base="$(basename "$path")"
    [[ "$base" =~ ^${prefix}-([0-9]+)-[FDCR]_ ]] || continue
    n=$((10#${BASH_REMATCH[1]}))
    (( n > high )) && high="$n"
  done
  printf '%s' "$high"
}

id_exists() {
  local id="$1"
  compgen -G "${TODOS}/${id}-"'*.md' >/dev/null && return 0
  compgen -G "${ARCHIVED}/${id}-"'*.md' >/dev/null && return 0
  compgen -G "${INBOX}/${id}_"'*.md' >/dev/null && return 0
  compgen -G "${INBOX_ARCHIVED}/${id}_"'*.md' >/dev/null && return 0
  return 1
}

acquire_lock() {
  local attempts=0
  while ! mkdir "${LOCK_DIR}" 2>/dev/null; do
    attempts=$((attempts + 1))
    if (( attempts >= 100 )); then
      die "could not acquire reservation lock at $(rel_repo "${LOCK_DIR}")"
    fi
    sleep 0.1
  done
  trap 'rmdir "${LOCK_DIR}" 2>/dev/null || true' EXIT
}

reserve_file() {
  local path="$1"
  if (set -o noclobber; : > "$path") 2>/dev/null; then
    printf '%s\n' "$(rel_repo "$path")"
    return 0
  fi
  return 1
}

reserve_inbox() {
  local slug="$1" n id path
  validate_slug "$slug"
  n=$(($(highest_inbox_id) + 1))
  while true; do
    id="I-$(pad_id "$n")"
    if id_exists "$id"; then
      n=$((n + 1))
      continue
    fi
    path="${INBOX}/${id}_${slug}.md"
    reserve_file "$path" && return 0
    n=$((n + 1))
  done
}

reserve_task() {
  local prefix="$1" type="$2" slug="$3" n id path
  validate_prefix_registered "$prefix"
  [[ "$type" =~ ^[FDCR]$ ]] || die "type must be one of F, D, C, R"
  validate_slug "$slug"
  n=$(($(highest_task_id "$prefix") + 1))
  while true; do
    id="${prefix}-$(pad_id "$n")"
    if id_exists "$id"; then
      n=$((n + 1))
      continue
    fi
    path="${TODOS}/${id}-${type}_${slug}.md"
    reserve_file "$path" && return 0
    n=$((n + 1))
  done
}

case "${1:-}" in
  --help|-h)
    usage
    exit 0
    ;;
  inbox)
    [[ $# -eq 2 ]] || { usage >&2; exit 2; }
    require_initialized
    acquire_lock
    reserve_inbox "$2"
    ;;
  task)
    [[ $# -eq 4 ]] || { usage >&2; exit 2; }
    require_initialized
    acquire_lock
    reserve_task "$2" "$3" "$4"
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
