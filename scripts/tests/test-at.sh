#!/usr/bin/env bash
#
# Integration test for the `at` CLI (plugins/agents-core/bin/at -> lib/at.py).
#
# Creates a throwaway git repo, seeds it with `at init --all` and asserts the
# seed shape, idempotence, `at doctor`, `at ledger check` and `at version`.
# The pure parts of `at bootstrap` (resolver text, stale-symlink candidates)
# are exercised against a temp HOME; nothing touches the real machine config.
#
# Run from any cwd: bash scripts/tests/test-at.sh

set -uo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
AT_PY="$REPO/plugins/agents-core/lib/at.py"

PASS_COUNT=0
FAIL_COUNT=0

pass() { PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { FAIL_COUNT=$((FAIL_COUNT + 1)); echo "FAIL: $*" >&2; }

assert_exists() { # assert_exists <path> <desc>
  if [[ -e "$1" ]]; then pass; else fail "$2 (missing: $1)"; fi
}
assert_missing() { # assert_missing <path> <desc>
  if [[ ! -e "$1" ]]; then pass; else fail "$2 (unexpected: $1)"; fi
}
assert_contains() { # assert_contains <file> <needle> <desc>
  if grep -qF -- "$2" "$1" 2>/dev/null; then pass; else fail "$3"; fi
}
assert_stdout_contains() { # assert_stdout_contains <text> <needle> <desc>
  if printf '%s\n' "$1" | grep -qF -- "$2"; then pass; else fail "$3"; fi
}
assert_stdout_lacks() { # assert_stdout_lacks <text> <needle> <desc>
  if printf '%s\n' "$1" | grep -qF -- "$2"; then fail "$3"; else pass; fi
}
assert_eq() { # assert_eq <actual> <expected> <desc>
  if [[ "$1" == "$2" ]]; then pass; else fail "$3 (got '$1', want '$2')"; fi
}

WORKDIR="$(mktemp -d)"
trap 'rm -rf "${WORKDIR}"' EXIT

# --- fixture repo -----------------------------------------------------------
PROJECT="$WORKDIR/project"
mkdir -p "$PROJECT"
cd "$PROJECT" || exit 1
git init -q .
git config user.email "test@example.com"
git config user.name "at test"
printf '# scratch project\n' > README.md
printf 'node_modules/\n' > .gitignore
git add -A
git commit -qm "init"

export PATH="$REPO/plugins/agents-core/bin:$PATH"
export AT_TASKS_ROOT="$REPO/plugins/agents-tasks"

# --- at init --all ----------------------------------------------------------
INIT_OUT="$(at init --all 2>&1)"
INIT_RC=$?
assert_eq "$INIT_RC" "0" "at init --all exits 0: $INIT_OUT"

for f in AGENTS.md CLAUDE.md .claude/settings.json .codex/agents/implementer.toml \
         docs/tasks_manager/_todos docs/tasks_manager/_areas.md docs/tasks_manager/_roadmap.md \
         docs/tasks_manager/_logs docs/areas/_overview.md docs/resources/CONTEXT.md \
         artifacts/README.md workbooks/README.md .config/repos.project.md; do
  assert_exists "$PROJECT/$f" "at init --all creates $f"
done

assert_contains .gitignore "# BEGIN agents-template" ".gitignore has BEGIN marker"
assert_contains .gitignore "# END agents-template" ".gitignore has END marker"
assert_contains .gitignore "node_modules/" ".gitignore keeps pre-existing content"
assert_contains .gitignore ".no-commit/" ".gitignore managed block ignores local-only dirs"
assert_contains .gitattributes "# BEGIN agents-template" ".gitattributes has BEGIN marker"
assert_contains .gitattributes "# END agents-template" ".gitattributes has END marker"

assert_eq "$(head -n 1 CLAUDE.md)" "@AGENTS.md" "CLAUDE.md imports AGENTS.md"
assert_contains .gitattributes "*.pdf binary" ".gitattributes managed block sets binary rules"
assert_contains AGENTS.md "TODO-FILL" "seed AGENTS.md carries TODO-FILL project slots"

LINES="$(wc -l < AGENTS.md | tr -d ' ')"
if [[ "$LINES" -le 200 ]]; then pass; else fail "AGENTS.md is $LINES lines (> 200)"; fi

SETTINGS_CORE="$(python3 -c 'import json;print(json.load(open(".claude/settings.json"))["enabledPlugins"].get("agents-core@agents-template"))')"
assert_eq "$SETTINGS_CORE" "True" "settings.json enables agents-core"
SETTINGS_TASKS="$(python3 -c 'import json;print(json.load(open(".claude/settings.json"))["enabledPlugins"].get("agents-tasks@agents-template"))')"
assert_eq "$SETTINGS_TASKS" "True" "settings.json enables agents-tasks with --with-tasks"
SETTINGS_DENY="$(python3 -c 'import json;print("\n".join(json.load(open(".claude/settings.json"))["permissions"]["deny"]))')"
assert_stdout_contains "$SETTINGS_DENY" "Read(./.creds/**)" "settings.json denies reads of the local credential dir"

# --- idempotence ------------------------------------------------------------
INIT_OUT2="$(at init --all 2>&1)"
INIT_RC2=$?
assert_eq "$INIT_RC2" "0" "second at init --all exits 0"
assert_stdout_lacks "$INIT_OUT2" "created" "second at init --all creates nothing"

# a user edit to a seeded file survives re-init
printf '\n<!-- local note -->\n' >> AGENTS.md
at init --all >/dev/null 2>&1
assert_contains AGENTS.md "<!-- local note -->" "at init never clobbers AGENTS.md"
sed -i '/<!-- local note -->/d' AGENTS.md

# unmanaged keys in settings.json survive re-init
python3 - <<'PY'
import json, pathlib
p = pathlib.Path(".claude/settings.json")
data = json.loads(p.read_text())
data["model"] = "opus"
data["permissions"]["deny"].append("Bash(rm -rf /*)")
p.write_text(json.dumps(data, indent=2) + "\n")
PY
at init --all >/dev/null 2>&1
KEPT="$(python3 -c 'import json;d=json.load(open(".claude/settings.json"));print(d.get("model"), "Bash(rm -rf /*)" in d["permissions"]["deny"])')"
assert_eq "$KEPT" "opus True" "at init keeps unmanaged settings.json keys"

# --- at doctor --------------------------------------------------------------
DOCTOR_OUT="$(at doctor 2>&1)"
DOCTOR_RC=$?
assert_eq "$DOCTOR_RC" "0" "at doctor exits 0 on a fresh seed: $DOCTOR_OUT"
assert_stdout_contains "$DOCTOR_OUT" "TODO-FILL" "at doctor warns about unfilled project slots"
if printf '%s\n' "$DOCTOR_OUT" | grep -q '^WARN .*TODO-FILL'; then pass; else fail "TODO-FILL finding is a WARN"; fi
assert_stdout_lacks "$DOCTOR_OUT" "ERROR" "at doctor reports no errors on a fresh seed"

# doctor fails on a legacy layout and on a broken CLAUDE.md
mkdir -p _base
DOCTOR_LEGACY="$(at doctor 2>&1)"
DOCTOR_LEGACY_RC=$?
assert_eq "$DOCTOR_LEGACY_RC" "1" "at doctor exits 1 when _base/ is present"
assert_stdout_contains "$DOCTOR_LEGACY" "at migrate" "legacy-layout error points at at migrate"
rmdir _base

printf 'no import here\n' > CLAUDE.md
DOCTOR_BAD="$(at doctor 2>&1)"
DOCTOR_BAD_RC=$?
assert_eq "$DOCTOR_BAD_RC" "1" "at doctor exits 1 when CLAUDE.md lacks the AGENTS.md import"
printf '@AGENTS.md\n' > CLAUDE.md

# --- ledger wrappers --------------------------------------------------------
at ledger check >/dev/null 2>&1
assert_eq "$?" "0" "at ledger check exits 0 on the seeded ledger"
at ledger sync >/dev/null 2>&1
assert_eq "$?" "0" "at ledger sync exits 0 on the seeded ledger"
at repos-check >/dev/null 2>&1
assert_eq "$?" "0" "at repos-check exits 0 on the seeded registry"

# --- at version -------------------------------------------------------------
EXPECTED_VERSION="$(python3 -c "import json;print(json.load(open('$REPO/plugins/agents-core/.claude-plugin/plugin.json'))['version'])")"
assert_eq "$(at version 2>&1)" "$EXPECTED_VERSION" "at version prints the plugin version"
assert_eq "$EXPECTED_VERSION" "1.0.0" "plugin version is 1.0.0"

# --- usage errors -----------------------------------------------------------
at frobnicate >/dev/null 2>&1
assert_eq "$?" "2" "unknown subcommand exits 2"
at migrate >/dev/null 2>&1
assert_eq "$?" "2" "at migrate is a Task 8 stub (exit 2)"

# --- at init without opt-in flags ------------------------------------------
PROJECT2="$WORKDIR/project2"
mkdir -p "$PROJECT2"
cd "$PROJECT2" || exit 1
git init -q .
git config user.email "test@example.com"
git config user.name "at test"
git commit -q --allow-empty -m init
cat > .gitattributes <<'LEGACY'
# BEGIN agents-template merge rules
AGENTS.md merge=template-keep-local
# END agents-template merge rules
LEGACY
at init >/dev/null 2>&1
assert_contains .gitattributes "# BEGIN agents-template merge rules" "a legacy merge-rules block is left for at migrate"
assert_contains .gitattributes "*.pdf binary" "the new managed block is appended alongside it"
assert_exists "$PROJECT2/AGENTS.md" "bare at init writes AGENTS.md"
assert_missing "$PROJECT2/docs/tasks_manager" "bare at init skips the tasks seed"
assert_missing "$PROJECT2/artifacts/README.md" "bare at init skips the artifacts seed"
BARE_TASKS="$(python3 -c 'import json;print("agents-tasks@agents-template" in json.load(open(".claude/settings.json"))["enabledPlugins"])')"
assert_eq "$BARE_TASKS" "False" "bare at init does not enable agents-tasks"

# --- bootstrap: pure parts only (temp HOME, no real config touched) ---------
FAKEHOME="$WORKDIR/home"
mkdir -p "$FAKEHOME"

python3 - "$AT_PY" "$FAKEHOME" <<'PY'
import importlib.util, pathlib, sys
spec = importlib.util.spec_from_file_location("at", sys.argv[1])
at = importlib.util.module_from_spec(spec)
spec.loader.exec_module(at)
at.write_resolver(pathlib.Path(sys.argv[2]))
PY
assert_exists "$FAKEHOME/.local/bin/at" "write_resolver writes ~/.local/bin/at"
if [[ -x "$FAKEHOME/.local/bin/at" ]]; then pass; else fail "resolver is executable"; fi

# newest cached version wins, numerically (1.10.0 > 1.9.0 > 1.2.0)
for v in 1.2.0 1.9.0 1.10.0; do
  d="$FAKEHOME/.claude/plugins/cache/agents-template/agents-core/$v/bin"
  mkdir -p "$d"
  printf '#!/usr/bin/env bash\necho "cache %s"\n' "$v" > "$d/at"
  chmod +x "$d/at"
done
RESOLVED="$(HOME="$FAKEHOME" AT_DEV_ROOT="" bash "$FAKEHOME/.local/bin/at" 2>&1)"
assert_eq "$RESOLVED" "cache 1.10.0" "resolver picks the newest cached version"

# stale global skill symlinks: only those pointing into a legacy template repo
LEGACY="$WORKDIR/legacy-repo"
mkdir -p "$LEGACY/_base" "$LEGACY/.claude/skills/old-skill" "$LEGACY/playbooks"
printf '# old\n' > "$LEGACY/.claude/skills/old-skill/SKILL.md"
LEGACY2="$WORKDIR/legacy-repo-2"
mkdir -p "$LEGACY2/playbooks" "$LEGACY2/skills/misc/legacy-wrapper"
printf '# old\n' > "$LEGACY2/skills/misc/legacy-wrapper/SKILL.md"
PLAIN="$WORKDIR/plain-repo"
mkdir -p "$PLAIN/skills/misc/keep-me"
printf '# keep\n' > "$PLAIN/skills/misc/keep-me/SKILL.md"
mkdir -p "$FAKEHOME/.claude/skills" "$FAKEHOME/.agents/skills" "$FAKEHOME/.codex/skills"
ln -sfn "$LEGACY/.claude/skills/old-skill" "$FAKEHOME/.claude/skills/old-skill"
ln -sfn "$LEGACY2/skills/misc/legacy-wrapper" "$FAKEHOME/.agents/skills/legacy-wrapper"
ln -sfn "$PLAIN/skills/misc/keep-me" "$FAKEHOME/.codex/skills/keep-me"
mkdir -p "$FAKEHOME/.claude/skills/hand-written"

CANDIDATES="$(python3 - "$AT_PY" "$FAKEHOME" <<'PY'
import importlib.util, pathlib, sys
spec = importlib.util.spec_from_file_location("at", sys.argv[1])
at = importlib.util.module_from_spec(spec)
spec.loader.exec_module(at)
for link in at.stale_skill_symlinks(pathlib.Path(sys.argv[2])):
    print(link)
PY
)"
assert_stdout_contains "$CANDIDATES" "$FAKEHOME/.claude/skills/old-skill" "symlink into a legacy .claude/skills tree is a candidate"
assert_stdout_contains "$CANDIDATES" "$FAKEHOME/.agents/skills/legacy-wrapper" "symlink into a legacy skills/<bucket>/ tree is a candidate"
assert_stdout_lacks "$CANDIDATES" "keep-me" "symlink into a non-template repo is not a candidate"
assert_stdout_lacks "$CANDIDATES" "hand-written" "a real directory is not a candidate"

# --- summary ----------------------------------------------------------------
cd "$REPO" || exit 1
echo "test-at: ${PASS_COUNT} passed, ${FAIL_COUNT} failed"
[[ "$FAIL_COUNT" -eq 0 ]]
