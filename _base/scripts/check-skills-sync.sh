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
# Exits 0 if no BLOCKER or DRIFT findings (STYLE alone does not fail).

set -euo pipefail

readonly VERSION="0.1.0"

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
PLAYBOOKS_DIR="$REPO_ROOT/playbooks/skills"
CODEX_SKILLS_DIR="$REPO_ROOT/skills"
CLAUDE_SKILLS_DIR="$REPO_ROOT/.claude/skills"
PERSONALITIES_DIR="$REPO_ROOT/playbooks/personalities"
README="$REPO_ROOT/_base/README.md"
GEN_SCRIPT="$REPO_ROOT/_base/scripts/gen-skills-table.sh"

# Names that have wrappers in skills/ and .claude/skills/ but no playbook.
# These are agent definitions; their canonical role file lives in .claude/agents/.
AGENT_ONLY_NAMES=("implementer" "reviewer")

# Personalities live only in playbooks/personalities/ and must NOT be exposed
# as skill wrappers (they are role cards, not slash commands).
PERSONALITY_NAMES=("manager" "builder" "tester" "critic" "researcher")
# Note: "reviewer" is intentionally both an agent and a personality card; it's
# allowed in wrappers because of the agent role. We do not flag it here.

# Wrappers should fit on a quick read; longer than this is a thinness smell.
WRAPPER_MAX_LINES=50

# Accumulator (TSV: severity\tcheck_id\tpath\tdetails)
FINDINGS=()

emit() {
  # emit SEVERITY CHECK_ID PATH [details]
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
# Usage: fm_field <path> <field-name>
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
# Returns lowercase phrases, one per line, deduplicated.
quoted_triggers() {
  local desc="$1"
  # grep -oE exits 1 when there are no matches; suppress so pipefail doesn't kill us.
  printf '%s\n' "$desc" \
    | { grep -oE '"[^"]+"' || true; } \
    | tr -d '"' \
    | tr '[:upper:]' '[:lower:]' \
    | sort -u
}

# ----------------------------------------------------------------------------
# Discovery
# ----------------------------------------------------------------------------

mapfile -t PLAYBOOK_NAMES < <(
  find "$PLAYBOOKS_DIR" -maxdepth 1 -type f -name '*.md' -printf '%f\n' \
    | sed 's/\.md$//' \
    | sort
)

mapfile -t CODEX_NAMES < <(
  find "$CODEX_SKILLS_DIR" -maxdepth 1 -mindepth 1 -type d -printf '%f\n' \
    | sort
)

mapfile -t CLAUDE_NAMES < <(
  find "$CLAUDE_SKILLS_DIR" -maxdepth 1 -mindepth 1 -type d -printf '%f\n' \
    | sort
)

# ----------------------------------------------------------------------------
# Check 1: pairing — every playbook has both wrappers
# ----------------------------------------------------------------------------

for name in "${PLAYBOOK_NAMES[@]}"; do
  if [[ ! -f "$CODEX_SKILLS_DIR/$name/SKILL.md" ]]; then
    emit BLOCKER missing-codex-wrapper \
      "skills/$name/SKILL.md" \
      "playbook exists at playbooks/skills/$name.md"
  fi
  if [[ ! -f "$CLAUDE_SKILLS_DIR/$name/SKILL.md" ]]; then
    emit BLOCKER missing-claude-wrapper \
      ".claude/skills/$name/SKILL.md" \
      "playbook exists at playbooks/skills/$name.md"
  fi
done

# ----------------------------------------------------------------------------
# Check 2: orphans — every wrapper has a playbook (or is a known agent-only name)
# ----------------------------------------------------------------------------

for name in "${CODEX_NAMES[@]}"; do
  if [[ ! -f "$PLAYBOOKS_DIR/$name.md" ]] && ! in_array "$name" "${AGENT_ONLY_NAMES[@]}"; then
    emit BLOCKER orphan-codex-wrapper \
      "skills/$name/SKILL.md" \
      "no matching playbooks/skills/$name.md"
  fi
done

for name in "${CLAUDE_NAMES[@]}"; do
  if [[ ! -f "$PLAYBOOKS_DIR/$name.md" ]] && ! in_array "$name" "${AGENT_ONLY_NAMES[@]}"; then
    emit BLOCKER orphan-claude-wrapper \
      ".claude/skills/$name/SKILL.md" \
      "no matching playbooks/skills/$name.md"
  fi
done

# ----------------------------------------------------------------------------
# Check 3: personalities not exposed as skill wrappers
# ----------------------------------------------------------------------------

for name in "${PERSONALITY_NAMES[@]}"; do
  if [[ -d "$CODEX_SKILLS_DIR/$name" ]]; then
    emit BLOCKER personality-exposed-as-skill \
      "skills/$name/" \
      "personality cards must not be slash-invokable"
  fi
  if [[ -d "$CLAUDE_SKILLS_DIR/$name" ]]; then
    emit BLOCKER personality-exposed-as-skill \
      ".claude/skills/$name/" \
      "personality cards must not be slash-invokable"
  fi
done

# ----------------------------------------------------------------------------
# Check 4: per-wrapper validations (name, description, references, thinness,
#          claude-only fields)
# ----------------------------------------------------------------------------

check_wrapper() {
  local runtime="$1" name="$2" wrapper="$3" expect_disable_model="$4"
  local pretty
  if [[ "$runtime" == "codex" ]]; then
    pretty="skills/$name/SKILL.md"
  else
    pretty=".claude/skills/$name/SKILL.md"
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

  # Reference check: wrapper should mention its playbook (skip for agent-only names).
  if ! in_array "$name" "${AGENT_ONLY_NAMES[@]}"; then
    if ! grep -qE "playbooks/skills/$name(\.md|/)" "$wrapper"; then
      emit DRIFT missing-playbook-reference "$pretty" \
        "wrapper does not reference playbooks/skills/$name(.md|/)"
    fi
  fi
}

for name in "${CODEX_NAMES[@]}"; do
  check_wrapper codex "$name" "$CODEX_SKILLS_DIR/$name/SKILL.md" no
done

for name in "${CLAUDE_NAMES[@]}"; do
  check_wrapper claude "$name" "$CLAUDE_SKILLS_DIR/$name/SKILL.md" yes
done

# ----------------------------------------------------------------------------
# Check 5: description trigger-keyword drift between Codex and Claude wrappers
# ----------------------------------------------------------------------------
# Heuristic: extract quoted "..." phrases from each side, lowercase, compare
# as sets. Any phrase present on one side but not the other is drift.

for name in "${PLAYBOOK_NAMES[@]}"; do
  codex_wrapper="$CODEX_SKILLS_DIR/$name/SKILL.md"
  claude_wrapper="$CLAUDE_SKILLS_DIR/$name/SKILL.md"
  [[ -f "$codex_wrapper" && -f "$claude_wrapper" ]] || continue

  codex_desc="$(fm_field "$codex_wrapper" description || true)"
  claude_desc="$(fm_field "$claude_wrapper" description || true)"
  [[ -n "$codex_desc" && -n "$claude_desc" ]] || continue

  codex_trig="$(quoted_triggers "$codex_desc")"
  claude_trig="$(quoted_triggers "$claude_desc")"

  # Phrases only in Claude
  only_claude="$(comm -23 <(printf '%s\n' "$claude_trig") <(printf '%s\n' "$codex_trig") | paste -sd ',' -)"
  if [[ -n "$only_claude" ]]; then
    emit DRIFT trigger-only-in-claude \
      "skills/$name/SKILL.md" \
      "Claude wrapper has trigger phrases not in Codex wrapper: [$only_claude]"
  fi

  # Phrases only in Codex
  only_codex="$(comm -13 <(printf '%s\n' "$claude_trig") <(printf '%s\n' "$codex_trig") | paste -sd ',' -)"
  if [[ -n "$only_codex" ]]; then
    emit DRIFT trigger-only-in-codex \
      ".claude/skills/$name/SKILL.md" \
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

  # Run the generator against a temp copy without modifying the real README.
  # We do that by swapping the README path via a subshell trick: copy real → tmp,
  # run generator with README pointed at tmp by sandboxing through a temp repo
  # symlink is overkill. Instead: run the generator (it edits the real README
  # in place), capture diff, then revert if dirty.
  pre_hash="$(sha256sum "$README" | awk '{print $1}')"
  if "$GEN_SCRIPT" >/dev/null 2>&1; then
    post_hash="$(sha256sum "$README" | awk '{print $1}')"
    if [[ "$pre_hash" != "$post_hash" ]]; then
      emit DRIFT skills-table-out-of-date \
        "_base/README.md" \
        "_base/scripts/gen-skills-table.sh produced changes — run it and commit"
      # Restore so this check is non-destructive.
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
  # Sort by severity (BLOCKER < DRIFT < STYLE alphabetically — perfect), then by check_id.
  printf '%s\n' "${FINDINGS[@]}" | sort
  printf '\n'
fi

total=${#FINDINGS[@]}
if (( total == 0 )); then
  printf 'OK  skills/wrappers/table fully in sync (%d playbooks, %d codex, %d claude wrappers)\n' \
    "${#PLAYBOOK_NAMES[@]}" "${#CODEX_NAMES[@]}" "${#CLAUDE_NAMES[@]}"
  exit 0
fi

printf '%d findings  (%d BLOCKER, %d DRIFT, %d STYLE)\n' \
  "$total" "$blocker_count" "$drift_count" "$style_count"

if (( blocker_count + drift_count > 0 )); then
  exit 1
fi
exit 0
