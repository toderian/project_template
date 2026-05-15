#!/usr/bin/env bash
#
# Validate that skills, wrappers, and the skills table are in sync.
#
# Designed to be run by an agent in a loop:
#   1. Run the script.
#   2. Read each finding (one per line: SEVERITY  CHECK_ID  PATH  [details]).
#   3. Fix one or a batch.
#   4. Re-run. Watch the findings shrink. Stop when clean.
#
# Active skills are enumerated in `.claude-plugin/plugin.json`. Anything on
# disk that isn't in the manifest is flagged as orphan; anything in the
# manifest that isn't on disk is flagged as missing.
#
# Exits 0 if no BLOCKER or DRIFT findings (STYLE alone does not fail).

set -euo pipefail

readonly VERSION="0.2.0"

usage() {
  cat <<'EOF'
Usage: check-skills-sync.sh [OPTION]

Validate skill/wrapper/table consistency in the agents template.

With no option, run all checks and print findings to stdout.

Output format (one finding per line):
  SEVERITY<tab>CHECK_ID<tab>PATH<tab>[details]

Severities:
  BLOCKER  Missing or orphan files, broken references. Must fix.
  DRIFT    Out-of-sync metadata that can be mechanically corrected.
  STYLE    Thin-wrapper / convention violations. Advisory.

Exit codes:
  0  No BLOCKER or DRIFT findings (STYLE is allowed).
  1  At least one BLOCKER or DRIFT finding.
  2  Usage error or environment problem.

Options:
  --version    Print version and exit.
  --help       Show this message and exit.
EOF
}

case "${1:-}" in
  --version) printf 'check-skills-sync.sh %s\n' "$VERSION"; exit 0 ;;
  --help)    usage; exit 0 ;;
  "")        ;;
  *)         printf 'unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
esac

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MANIFEST="$REPO_ROOT/.claude-plugin/plugin.json"
PLAYBOOKS_DIR="$REPO_ROOT/playbooks/skills"
CODEX_SKILLS_DIR="$REPO_ROOT/skills"
CLAUDE_SKILLS_DIR="$REPO_ROOT/.claude/skills"
README="$REPO_ROOT/_base/README.md"
GEN_SCRIPT="$REPO_ROOT/_base/scripts/gen-skills-table.sh"

# Names that have wrappers in skills/ and .claude/skills/ but no playbook.
# These are agent definitions; their canonical role file lives in .claude/agents/.
AGENT_ONLY_NAMES=("implementer" "reviewer")

# Personalities live only in playbooks/personalities/ and must NOT be exposed
# as skill wrappers (they are role cards, not slash commands).
PERSONALITY_NAMES=("manager" "builder" "tester" "critic" "researcher")

# Recognised buckets. Any other top-level dir under skills/ etc. is an orphan.
BUCKETS=("engineering" "productivity" "misc" "personal")

# Wrappers should fit on a quick read; longer than this is a thinness smell.
WRAPPER_MAX_LINES=50

# Accumulator (TSV: severity\tcheck_id\tpath\tdetails)
FINDINGS=()

emit() {
  local severity="$1" check_id="$2" path="$3"
  shift 3
  local details="$*"
  FINDINGS+=("$(printf '%s\t%s\t%s\t%s' "$severity" "$check_id" "$path" "$details")")
}

in_array() {
  local needle="$1"; shift
  local hay
  for hay in "$@"; do [[ "$hay" == "$needle" ]] && return 0; done
  return 1
}

# Extract a frontmatter field from a wrapper SKILL.md.
fm_field() {
  local file="$1" field="$2"
  awk -v field="$field" '
    /^---[[:space:]]*$/ { if (in_fm) { exit } else { in_fm = 1; next } }
    in_fm {
      pat = "^" field ":[[:space:]]*"
      if ($0 ~ pat) {
        sub(pat, "")
        sub(/^"/, ""); sub(/"$/, "")
        sub(/^'\''/, ""); sub(/'\''$/, "")
        print
        exit
      }
    }
  ' "$file"
}

# Extract quoted trigger phrases from a description.
quoted_triggers() {
  local desc="$1"
  printf '%s\n' "$desc" \
    | { grep -oE '"[^"]+"' || true; } \
    | tr -d '"' \
    | tr '[:upper:]' '[:lower:]' \
    | sort -u
}

# ----------------------------------------------------------------------------
# Read the manifest
# ----------------------------------------------------------------------------

if [[ ! -f "$MANIFEST" ]]; then
  printf 'error: manifest not found at %s\n' "$MANIFEST" >&2
  exit 2
fi

declare -A NAME_TO_BUCKET
while IFS=$'\t' read -r name bucket; do
  NAME_TO_BUCKET["$name"]="$bucket"
done < <(python3 - "$MANIFEST" <<'PY'
import json, sys
with open(sys.argv[1]) as f:
    data = json.load(f)
for p in data["skills"]:
    parts = p.strip("./").split("/")
    if len(parts) != 3 or parts[0] != "skills":
        sys.exit(f"manifest entry malformed: {p}")
    print(f"{parts[2]}\t{parts[1]}")
PY
)

mapfile -t MANIFEST_NAMES < <(printf '%s\n' "${!NAME_TO_BUCKET[@]}" | sort)

# ----------------------------------------------------------------------------
# Check 1: every manifest entry has both wrappers (and a playbook unless agent-only)
# ----------------------------------------------------------------------------

for name in "${MANIFEST_NAMES[@]}"; do
  bucket="${NAME_TO_BUCKET[$name]}"

  codex_wrapper="$CODEX_SKILLS_DIR/$bucket/$name/SKILL.md"
  claude_wrapper="$CLAUDE_SKILLS_DIR/$bucket/$name/SKILL.md"

  if [[ ! -f "$codex_wrapper" ]]; then
    emit BLOCKER missing-codex-wrapper "skills/$bucket/$name/SKILL.md" "listed in manifest"
  fi
  if [[ ! -f "$claude_wrapper" ]]; then
    emit BLOCKER missing-claude-wrapper ".claude/skills/$bucket/$name/SKILL.md" "listed in manifest"
  fi

  if ! in_array "$name" "${AGENT_ONLY_NAMES[@]}"; then
    if [[ ! -f "$PLAYBOOKS_DIR/$bucket/$name.md" ]] && [[ ! -d "$PLAYBOOKS_DIR/$bucket/$name" ]]; then
      emit BLOCKER missing-playbook "playbooks/skills/$bucket/$name.md" "manifest entry has no playbook"
    fi
  fi

  if in_array "$name" "${PERSONALITY_NAMES[@]}"; then
    emit BLOCKER personality-in-manifest ".claude-plugin/plugin.json" \
      "$name is a personality and must not be exposed as a skill"
  fi
done

# ----------------------------------------------------------------------------
# Check 2: nothing on filesystem outside the manifest, and buckets are known
# ----------------------------------------------------------------------------

# Top-level under each skill tree must be a known bucket.
check_top_level() {
  local dir="$1" label="$2"
  [[ -d "$dir" ]] || return 0
  while IFS= read -r d; do
    [[ -z "$d" ]] && continue
    local bucket="$(basename "$d")"
    if ! in_array "$bucket" "${BUCKETS[@]}"; then
      emit BLOCKER unknown-bucket "$label/$bucket/" "expected one of: ${BUCKETS[*]}"
    fi
  done < <(find "$dir" -mindepth 1 -maxdepth 1 -type d 2>/dev/null)
}

check_top_level "$CODEX_SKILLS_DIR"  "skills"
check_top_level "$CLAUDE_SKILLS_DIR" ".claude/skills"
check_top_level "$PLAYBOOKS_DIR"     "playbooks/skills"

# Wrapper dirs (skills/<bucket>/<name>/, .claude/skills/<bucket>/<name>/)
scan_wrapper_dirs() {
  local dir="$1" label="$2"
  [[ -d "$dir" ]] || return 0
  while IFS= read -r d; do
    [[ -z "$d" ]] && continue
    local bucket="$(basename "$(dirname "$d")")"
    local name="$(basename "$d")"
    if [[ -z "${NAME_TO_BUCKET[$name]+x}" ]]; then
      emit BLOCKER orphan-on-disk "$label/$bucket/$name/" "not listed in manifest"
    elif [[ "${NAME_TO_BUCKET[$name]}" != "$bucket" ]]; then
      emit BLOCKER bucket-mismatch "$label/$bucket/$name/" \
        "manifest places it in ${NAME_TO_BUCKET[$name]}"
    fi
  done < <(find "$dir" -mindepth 2 -maxdepth 2 -type d 2>/dev/null)
}

scan_wrapper_dirs "$CODEX_SKILLS_DIR"  "skills"
scan_wrapper_dirs "$CLAUDE_SKILLS_DIR" ".claude/skills"

# Playbook files at the bucket level (playbooks/skills/<bucket>/<name>.md)
while IFS= read -r f; do
  [[ -z "$f" ]] && continue
  bucket="$(basename "$(dirname "$f")")"
  name="$(basename "$f" .md)"
  if [[ -z "${NAME_TO_BUCKET[$name]+x}" ]]; then
    emit BLOCKER orphan-on-disk "playbooks/skills/$bucket/$name.md" "not listed in manifest"
  elif [[ "${NAME_TO_BUCKET[$name]}" != "$bucket" ]]; then
    emit BLOCKER bucket-mismatch "playbooks/skills/$bucket/$name.md" \
      "manifest places it in ${NAME_TO_BUCKET[$name]}"
  fi
done < <(find "$PLAYBOOKS_DIR" -mindepth 2 -maxdepth 2 -type f -name '*.md' 2>/dev/null)

# Stray files at the top level of playbooks/skills/ (legacy flat layout)
while IFS= read -r f; do
  [[ -z "$f" ]] && continue
  rel="${f#$REPO_ROOT/}"
  emit BLOCKER unbucketed-playbook "$rel" \
    "playbooks must live under a bucket dir (${BUCKETS[*]})"
done < <(find "$PLAYBOOKS_DIR" -mindepth 1 -maxdepth 1 -type f -name '*.md' 2>/dev/null)

# ----------------------------------------------------------------------------
# Check 3: personality wrappers (still enforced, now bucket-aware)
# ----------------------------------------------------------------------------

for name in "${PERSONALITY_NAMES[@]}"; do
  for bucket in "${BUCKETS[@]}"; do
    if [[ -d "$CODEX_SKILLS_DIR/$bucket/$name" ]]; then
      emit BLOCKER personality-exposed-as-skill \
        "skills/$bucket/$name/" "personality cards must not be slash-invokable"
    fi
    if [[ -d "$CLAUDE_SKILLS_DIR/$bucket/$name" ]]; then
      emit BLOCKER personality-exposed-as-skill \
        ".claude/skills/$bucket/$name/" "personality cards must not be slash-invokable"
    fi
  done
done

# ----------------------------------------------------------------------------
# Check 4: per-wrapper validations
# ----------------------------------------------------------------------------

check_wrapper() {
  local runtime="$1" name="$2" bucket="$3" wrapper="$4" expect_disable_model="$5"
  local pretty
  if [[ "$runtime" == "codex" ]]; then
    pretty="skills/$bucket/$name/SKILL.md"
  else
    pretty=".claude/skills/$bucket/$name/SKILL.md"
  fi

  [[ -f "$wrapper" ]] || return 0

  local fm_name
  fm_name="$(fm_field "$wrapper" name || true)"
  if [[ -z "$fm_name" ]]; then
    emit BLOCKER missing-name "$pretty" "frontmatter has no name: field"
  elif [[ "$fm_name" != "$name" ]]; then
    emit DRIFT name-mismatch "$pretty" "expected=$name got=$fm_name"
  fi

  local fm_desc
  fm_desc="$(fm_field "$wrapper" description || true)"
  if [[ -z "$fm_desc" ]]; then
    emit BLOCKER missing-description "$pretty" "frontmatter has no description: field"
  fi

  if [[ "$expect_disable_model" == "yes" ]]; then
    if ! grep -q '^disable-model-invocation:[[:space:]]*true' "$wrapper"; then
      emit STYLE missing-disable-model-invocation "$pretty" \
        "Claude wrappers should set disable-model-invocation: true"
    fi
  fi

  local lines
  lines=$(wc -l < "$wrapper")
  if (( lines > WRAPPER_MAX_LINES )); then
    emit STYLE wrapper-too-long "$pretty" "lines=$lines max=$WRAPPER_MAX_LINES"
  fi

  # Reference check: wrapper should mention its playbook (skip for agent-only).
  if ! in_array "$name" "${AGENT_ONLY_NAMES[@]}"; then
    if ! grep -qE "playbooks/skills/$bucket/$name(\.md|/)" "$wrapper"; then
      emit DRIFT missing-playbook-reference "$pretty" \
        "wrapper does not reference playbooks/skills/$bucket/$name(.md|/)"
    fi
  fi
}

for name in "${MANIFEST_NAMES[@]}"; do
  bucket="${NAME_TO_BUCKET[$name]}"
  check_wrapper codex  "$name" "$bucket" "$CODEX_SKILLS_DIR/$bucket/$name/SKILL.md"   no
  check_wrapper claude "$name" "$bucket" "$CLAUDE_SKILLS_DIR/$bucket/$name/SKILL.md"  yes
done

# ----------------------------------------------------------------------------
# Check 5: description trigger-keyword drift between Codex and Claude wrappers
# ----------------------------------------------------------------------------

for name in "${MANIFEST_NAMES[@]}"; do
  bucket="${NAME_TO_BUCKET[$name]}"
  codex_wrapper="$CODEX_SKILLS_DIR/$bucket/$name/SKILL.md"
  claude_wrapper="$CLAUDE_SKILLS_DIR/$bucket/$name/SKILL.md"
  [[ -f "$codex_wrapper" && -f "$claude_wrapper" ]] || continue

  codex_desc="$(fm_field "$codex_wrapper" description || true)"
  claude_desc="$(fm_field "$claude_wrapper" description || true)"
  [[ -n "$codex_desc" && -n "$claude_desc" ]] || continue

  codex_trig="$(quoted_triggers "$codex_desc")"
  claude_trig="$(quoted_triggers "$claude_desc")"

  only_claude="$(comm -23 <(printf '%s\n' "$claude_trig") <(printf '%s\n' "$codex_trig") | paste -sd ',' -)"
  if [[ -n "$only_claude" ]]; then
    emit DRIFT trigger-only-in-claude \
      "skills/$bucket/$name/SKILL.md" \
      "Claude wrapper has trigger phrases not in Codex wrapper: [$only_claude]"
  fi

  only_codex="$(comm -13 <(printf '%s\n' "$claude_trig") <(printf '%s\n' "$codex_trig") | paste -sd ',' -)"
  if [[ -n "$only_codex" ]]; then
    emit DRIFT trigger-only-in-codex \
      ".claude/skills/$bucket/$name/SKILL.md" \
      "Codex wrapper has trigger phrases not in Claude wrapper: [$only_codex]"
  fi
done

# ----------------------------------------------------------------------------
# Check 6: skills table in _base/README.md is up-to-date
# ----------------------------------------------------------------------------

if [[ -x "$GEN_SCRIPT" ]]; then
  tmp_readme="$(mktemp)"
  trap 'rm -f "$tmp_readme"' EXIT
  cp "$README" "$tmp_readme"

  pre_hash="$(sha256sum "$README" | awk '{print $1}')"
  if "$GEN_SCRIPT" >/dev/null 2>&1; then
    post_hash="$(sha256sum "$README" | awk '{print $1}')"
    if [[ "$pre_hash" != "$post_hash" ]]; then
      emit DRIFT skills-table-out-of-date \
        "_base/README.md" \
        "_base/scripts/gen-skills-table.sh produced changes — run it and commit"
      cp "$tmp_readme" "$README"
    fi
  else
    emit BLOCKER skills-table-generator-failed \
      "_base/scripts/gen-skills-table.sh" \
      "generator exited non-zero"
  fi
fi

# ----------------------------------------------------------------------------
# Report
# ----------------------------------------------------------------------------

blocker_count=0; drift_count=0; style_count=0
for f in "${FINDINGS[@]}"; do
  case "${f%%	*}" in
    BLOCKER) blocker_count=$((blocker_count+1)) ;;
    DRIFT)   drift_count=$((drift_count+1)) ;;
    STYLE)   style_count=$((style_count+1)) ;;
  esac
done

if (( ${#FINDINGS[@]} > 0 )); then
  printf '%s\n' "${FINDINGS[@]}" | sort
  printf '\n'
fi

total=${#FINDINGS[@]}
if (( total == 0 )); then
  # Count per-bucket for the OK line
  declare -A BUCKET_COUNTS
  for n in "${MANIFEST_NAMES[@]}"; do
    b="${NAME_TO_BUCKET[$n]}"
    BUCKET_COUNTS[$b]=$((${BUCKET_COUNTS[$b]:-0}+1))
  done
  bucket_summary=""
  for b in "${BUCKETS[@]}"; do
    bucket_summary+="$b=${BUCKET_COUNTS[$b]:-0} "
  done
  printf 'OK  manifest has %d skills (%s)\n' \
    "${#MANIFEST_NAMES[@]}" "${bucket_summary% }"
  exit 0
fi

printf '%d findings  (%d BLOCKER, %d DRIFT, %d STYLE)\n' \
  "$total" "$blocker_count" "$drift_count" "$style_count"

if (( blocker_count + drift_count > 0 )); then
  exit 1
fi
exit 0
