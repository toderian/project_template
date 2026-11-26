#!/usr/bin/env bash
#
# Atomically reserve an inbox idea or task filename.
#
# Usage:
#   at reserve inbox <slug>
#   at reserve task <PREFIX> <TYPE> <slug>
#
# The script creates the reserved file as an empty placeholder and prints its
# repo-relative path. Fill the placeholder immediately using the appropriate
# inbox/task template. If an agent is interrupted after reservation, strict
# ledger validation will catch the empty placeholder.

set -euo pipefail

# Root resolution: an explicit --root DIR wins; otherwise the git toplevel of
# the current directory; otherwise the current directory. (`at reserve` always
# passes --root explicitly; direct invocation falls back to git/cwd, matching
# sync_todo_ledgers.py's --root/default resolution.)
ROOT_OVERRIDE=""
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --root)
      [[ $# -ge 2 ]] || { echo "error: --root requires a directory argument" >&2; exit 2; }
      ROOT_OVERRIDE="$2"
      shift 2
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done
set -- "${ARGS[@]+"${ARGS[@]}"}"

if [[ -n "$ROOT_OVERRIDE" ]]; then
  REPO_ROOT="$(cd "$ROOT_OVERRIDE" && pwd)"
else
  REPO_ROOT="$(git -C . rev-parse --show-toplevel 2>/dev/null || pwd)"
fi

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
  at reserve inbox <slug>
  at reserve task <PREFIX> <TYPE> <slug>

Examples:
  at reserve inbox dark-mode-toggle
  at reserve task AUTH F login-session

The task manager must already be initialized. Run at init --with-tasks first if
docs/tasks_manager/ is missing.
EOF
}

rel_repo() {
  local path="$1"
  if [[ "$path" == "${REPO_ROOT}/"* ]]; then
    printf '%s' "${path#"${REPO_ROOT}"/}"
  else
    printf '%s' "$path"
  fi
}

die() {
  echo "error: $*" >&2
  exit 2
}

require_initialized() {
  [[ -d "${TM}" ]] || die "docs/tasks_manager/ is missing; run at init --with-tasks first"
  [[ -d "${TODOS}" ]] || die "$(rel_repo "${TODOS}") is missing; run at init --with-tasks first"
  [[ -d "${ARCHIVED}" ]] || die "$(rel_repo "${ARCHIVED}") is missing; run at init --with-tasks first"
  [[ -d "${INBOX}" ]] || die "$(rel_repo "${INBOX}") is missing; run at init --with-tasks first"
  [[ -d "${INBOX_ARCHIVED}" ]] || die "$(rel_repo "${INBOX_ARCHIVED}") is missing; run at init --with-tasks first"
  [[ -f "${AREAS_FILE}" ]] || die "$(rel_repo "${AREAS_FILE}") is missing; run at init --with-tasks first"
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

# Host-wide high-water mark, so two checkouts of one repo never reserve the same ID: the lock and
# one number file per prefix live under the state directory, keyed by the git common dir. If that
# directory cannot be made or written (or there is no absolute git common dir), HWM_BASE stays empty
# and only the per-checkout lock and scan apply.
HWM_BASE=""
HOST_LOCK=""
init_state() {
  local common key dir="${XDG_STATE_HOME:-${HOME:-/nonexistent}/.local/state}/agents-template/reserve"
  common="$(git -C "${REPO_ROOT}" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" || return 0
  [[ "$common" == /* ]] || return 0
  key="$(printf '%s' "$common" | cksum | cut -d' ' -f1)"
  mkdir -p "$dir" 2>/dev/null && [[ -w "$dir" ]] || return 0
  HOST_LOCK="${dir}/${key}.lock"
  HWM_BASE="${dir}/${key}"
}

# max(checkout scan, high-water mark) for a prefix ("I" for inbox)
with_hwm() {
  local scan="$1" prefix="$2" mark=0
  [[ -n "$HWM_BASE" && -r "${HWM_BASE}-${prefix}" ]] && mark="$(cat "${HWM_BASE}-${prefix}" 2>/dev/null)"
  [[ "$mark" =~ ^[0-9]+$ ]] || mark=0
  (( mark > scan )) && scan="$mark"
  printf '%s' "$scan"
}

save_hwm() {
  [[ -n "$HWM_BASE" ]] || return 0
  printf '%s' "$2" > "${HWM_BASE}-${1}.$$" 2>/dev/null && mv -f "${HWM_BASE}-${1}.$$" "${HWM_BASE}-${1}" 2>/dev/null \
    || rm -f "${HWM_BASE}-${1}.$$" 2>/dev/null || true
}

# One lock dir holding its owner's pid: a lock whose pid is dead is taken over (the mv is atomic, so
# one taker wins). A lock without a pid file is never taken over. simplicity: two takers can still
# race between the pid check and the mv; revisit when that shows up.
HELD_LOCKS=()
lock_dir() {
  local dir="$1" attempts=0 pid
  while ! mkdir "$dir" 2>/dev/null; do
    pid="$(cat "$dir/pid" 2>/dev/null || true)"
    if [[ "$pid" =~ ^[0-9]+$ ]] && ! kill -0 "$pid" 2>/dev/null; then
      mv "$dir" "$dir.stale.$$" 2>/dev/null && rm -rf "$dir.stale.$$"
      continue
    fi
    attempts=$((attempts + 1))
    (( attempts < 100 )) || die "could not acquire reservation lock at ${dir}; if no reservation is running, remove it with: rm -rf '${dir}'"
    sleep 0.1
  done
  printf '%s' "$$" > "$dir/pid" 2>/dev/null || true
  HELD_LOCKS+=("$dir")
}

release_locks() {
  local d
  for d in "${HELD_LOCKS[@]+"${HELD_LOCKS[@]}"}"; do
    rm -f "$d/pid" 2>/dev/null; rmdir "$d" 2>/dev/null || true
  done
}

# The per-checkout lock always; the host lock too when the state directory works, so a sandboxed
# process and a normal one in the same checkout still exclude each other.
acquire_lock() {
  trap release_locks EXIT
  lock_dir "${LOCK_DIR}"
  [[ -z "$HOST_LOCK" ]] || lock_dir "$HOST_LOCK"
}

# Reservation loops call this in a `while true` loop keyed on an incrementing
# numeric ID; a real filename collision (path already exists) means "try the
# next ID." Any other reservation failure (permissions, read-only filesystem,
# full disk, etc.) is not a collision and must not be treated as one — looping
# forever on it would hang the caller. Distinguish the two by checking whether
# the path exists after the noclobber write fails.
reserve_file() {
  local path="$1"
  if (set -o noclobber; : > "$path") 2>/dev/null; then
    printf '%s\n' "$(rel_repo "$path")"
    return 0
  fi
  if [[ -e "$path" ]]; then
    return 1
  fi
  die "cannot create $(rel_repo "$path") (permissions/disk full?)"
}

# Backstop against an unbounded loop if id_exists()/reserve_file() somehow
# keeps reporting collisions (e.g. a corrupted ledger) without ever hitting
# the die() above.
readonly MAX_RESERVE_ATTEMPTS=1000

reserve_inbox() {
  local slug="$1" n id path attempts=0
  validate_slug "$slug"
  n=$(($(with_hwm "$(highest_inbox_id)" I) + 1))
  while true; do
    attempts=$((attempts + 1))
    (( attempts <= MAX_RESERVE_ATTEMPTS )) || die "gave up after ${MAX_RESERVE_ATTEMPTS} attempts to reserve an inbox ID"
    id="I-$(pad_id "$n")"
    if id_exists "$id"; then
      n=$((n + 1))
      continue
    fi
    path="${INBOX}/${id}_${slug}.md"
    reserve_file "$path" && { save_hwm I "$n"; return 0; }
    n=$((n + 1))
  done
}

reserve_task() {
  local prefix="$1" type="$2" slug="$3" n id path attempts=0
  validate_prefix_registered "$prefix"
  [[ "$type" =~ ^[FDCR]$ ]] || die "type must be one of F, D, C, R"
  validate_slug "$slug"
  n=$(($(with_hwm "$(highest_task_id "$prefix")" "$prefix") + 1))
  while true; do
    attempts=$((attempts + 1))
    (( attempts <= MAX_RESERVE_ATTEMPTS )) || die "gave up after ${MAX_RESERVE_ATTEMPTS} attempts to reserve a task ID"
    id="${prefix}-$(pad_id "$n")"
    if id_exists "$id"; then
      n=$((n + 1))
      continue
    fi
    path="${TODOS}/${id}-${type}_${slug}.md"
    reserve_file "$path" && { save_hwm "$prefix" "$n"; return 0; }
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
    init_state
    acquire_lock
    reserve_inbox "$2"
    ;;
  task)
    [[ $# -eq 4 ]] || { usage >&2; exit 2; }
    require_initialized
    init_state
    acquire_lock
    reserve_task "$2" "$3" "$4"
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
