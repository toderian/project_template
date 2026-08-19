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
assert_symlink_gone() { # assert_symlink_gone <path> <desc>
  # `-e` alone is not enough here: it follows the symlink, so a *dangling*
  # symlink already reads as "missing" whether or not the link itself was
  # ever removed. `-L` checks the link entry directly.
  if [[ ! -e "$1" && ! -L "$1" ]]; then pass; else fail "$2 (unexpected: $1)"; fi
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
         docs/_plans/.gitkeep artifacts/README.md workbooks/README.md .config/repos.project.md; do
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

# a retired no-op deny rule from an already-seeded repo self-heals on re-init
python3 -c 'import json,pathlib
p = pathlib.Path(".claude/settings.json")
d = json.loads(p.read_text())
d["permissions"]["deny"].append("Write(./.creds/**)")
p.write_text(json.dumps(d, indent=2) + "\n")'
at init --all >/dev/null 2>&1
RETIRED_GONE="$(python3 -c 'import json;d=json.load(open(".claude/settings.json"));print("Write(./.creds/**)" in d["permissions"]["deny"])')"
assert_eq "$RETIRED_GONE" "False" "at init drops the retired Write(./.creds/**) deny rule"

# --- at doctor --------------------------------------------------------------
DOCTOR_OUT="$(at doctor 2>&1)"
DOCTOR_RC=$?
assert_eq "$DOCTOR_RC" "0" "at doctor exits 0 on a fresh seed: $DOCTOR_OUT"
assert_stdout_contains "$DOCTOR_OUT" "TODO-FILL" "at doctor warns about unfilled project slots"
if printf '%s\n' "$DOCTOR_OUT" | grep -q '^WARN .*TODO-FILL'; then pass; else fail "TODO-FILL finding is a WARN"; fi
assert_stdout_lacks "$DOCTOR_OUT" "ERROR" "at doctor reports no errors on a fresh seed"

# the warning counts slot markers, not every mention of the token
MARKERS="$(grep -c '<!-- TODO-FILL' AGENTS.md)"
assert_stdout_contains "$DOCTOR_OUT" "still has $MARKERS TODO-FILL project slot(s)" \
  "doctor counts exactly the project slot markers"
assert_eq "$(grep -c 'TODO-FILL' AGENTS.md)" "$MARKERS" \
  "the seed mentions TODO-FILL only in slot markers"

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

# filling every slot clears the warning
sed -i 's|^<!-- TODO-FILL.*|Filled in by the test.|' AGENTS.md
DOCTOR_FILLED="$(at doctor 2>&1)"
DOCTOR_FILLED_RC=$?
assert_eq "$DOCTOR_FILLED_RC" "0" "at doctor exits 0 once the project slots are filled"
if printf '%s\n' "$DOCTOR_FILLED" | grep -qE '^OK +AGENTS\.md project slots are filled'; then
  pass
else
  fail "filled project slots report OK: $DOCTOR_FILLED"
fi
assert_stdout_lacks "$DOCTOR_FILLED" "TODO-FILL" "no TODO-FILL warning once the slots are filled"

# prose that merely mentions the token is not an unfilled slot
printf '\nGuidance: doctor warns while any TODO-FILL slot marker remains.\n' >> AGENTS.md
DOCTOR_PROSE="$(at doctor 2>&1)"
DOCTOR_PROSE_RC=$?
assert_eq "$DOCTOR_PROSE_RC" "0" "at doctor exits 0 when only prose mentions the token"
assert_stdout_lacks "$DOCTOR_PROSE" "still has" "a prose mention does not count as a slot"
sed -i '/Guidance: doctor warns while any/d' AGENTS.md

# --- ledger wrappers --------------------------------------------------------
at ledger check >/dev/null 2>&1
assert_eq "$?" "0" "at ledger check exits 0 on the seeded ledger"
at ledger sync >/dev/null 2>&1
assert_eq "$?" "0" "at ledger sync exits 0 on the seeded ledger"
at repos-check >/dev/null 2>&1
assert_eq "$?" "0" "at repos-check exits 0 on the seeded registry"

# a failing ledger check still labels WARNING lines WARN, not ERROR
cp "$REPO/scripts/tests/fixtures/ledger-minimal/docs/tasks_manager/_todos/TST-002-C_oversized-execution-log.md" \
   docs/tasks_manager/_todos/
DOCTOR_LEDGER="$(at doctor 2>&1)"
DOCTOR_LEDGER_RC=$?
assert_eq "$DOCTOR_LEDGER_RC" "1" "at doctor exits 1 when the ledger check fails"
if printf '%s\n' "$DOCTOR_LEDGER" | grep -qE '^WARN +ledger: .*execution log exceeds 200 lines'; then
  pass
else
  fail "ledger warnings stay WARN on a failing check: $DOCTOR_LEDGER"
fi
if printf '%s\n' "$DOCTOR_LEDGER" | grep -qE '^ERROR +ledger: '; then pass; else fail "ledger errors are ERROR"; fi
rm docs/tasks_manager/_todos/TST-002-C_oversized-execution-log.md

# --- at version -------------------------------------------------------------
EXPECTED_VERSION="$(python3 -c "import json;print(json.load(open('$REPO/plugins/agents-core/.claude-plugin/plugin.json'))['version'])")"
assert_eq "$(at version 2>&1)" "$EXPECTED_VERSION" "at version prints the plugin version"
if [[ "$EXPECTED_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then pass;
else fail "plugin version '$EXPECTED_VERSION' is not semver X.Y.Z"; fi

# --- usage errors -----------------------------------------------------------
at frobnicate >/dev/null 2>&1
assert_eq "$?" "2" "unknown subcommand exits 2"
MIGRATE_NOLEGACY="$(at migrate --yes 2>&1)"
MIGRATE_NOLEGACY_RC=$?
assert_eq "$MIGRATE_NOLEGACY_RC" "1" "at migrate refuses a repo with no legacy layout"
assert_stdout_contains "$MIGRATE_NOLEGACY" "at init" "the refusal points at at init"
at migrate --keep-tasks --no-tasks >/dev/null 2>&1
assert_eq "$?" "2" "at migrate rejects --keep-tasks with --no-tasks"

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

# --- broken managed files are a repair job, not a silent rewrite ---------------
PROJECT3="$WORKDIR/project3"
mkdir -p "$PROJECT3"
cd "$PROJECT3" || exit 1
git init -q .
git config user.email "test@example.com"
git config user.name "at test"
git commit -q --allow-empty -m init

printf 'node_modules/\n# BEGIN agents-template\nstale-body/\n' > .gitignore
BROKEN_BLOCK="$(at init 2>&1)"
BROKEN_BLOCK_RC=$?
assert_eq "$BROKEN_BLOCK_RC" "1" "at init refuses an unterminated managed block"
assert_stdout_contains "$BROKEN_BLOCK" "without a matching" "the error names the missing END marker"
assert_contains .gitignore "stale-body/" "at init leaves the broken file untouched"
printf 'node_modules/\n' > .gitignore

printf '{"permissions": {"deny": "nope"}}\n' > .claude/settings.json
BAD_DENY="$(at init 2>&1)"
BAD_DENY_RC=$?
assert_eq "$BAD_DENY_RC" "1" "at init refuses a non-list permissions.deny"
assert_stdout_contains "$BAD_DENY" 'permissions.deny` must be a list' "the error says how to fix it"

printf '{"enabledPlugins": []}\n' > .claude/settings.json
BAD_PLUGINS="$(at init 2>&1)"
BAD_PLUGINS_RC=$?
assert_eq "$BAD_PLUGINS_RC" "1" "at init refuses a non-object enabledPlugins"
assert_stdout_contains "$BAD_PLUGINS" 'enabledPlugins` must be a JSON object' "the error names the key"

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

# Dangling case: once a downstream repo has been `at migrate`d, its
# _base/playbooks/skills dirs are deleted -- so a leftover global symlink
# into its old skill path no longer resolves into anything at all. It must
# still be flagged as stale even though _is_legacy_template_repo() can no
# longer find a _base/playbooks ancestor (there's nothing left to find).
# This exact shape was reproduced live on this machine: after
# ~/repos/project_technical_writing was migrated, 26 symlinks in
# ~/.claude/skills and 26 in ~/.codex/skills pointed into its now-deleted
# .claude/skills/<name> paths, and `at bootstrap --clean-global-skills`
# silently reported "no stale global skill symlinks found".
ln -sfn "$WORKDIR/does-not-exist-anymore/.claude/skills/old-skill" "$FAKEHOME/.claude/skills/dangling-example"

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
assert_stdout_contains "$CANDIDATES" "$FAKEHOME/.claude/skills/dangling-example" "a symlink whose target no longer exists at all (post-migrate) is a candidate"
assert_stdout_lacks "$CANDIDATES" "keep-me" "symlink into a non-template repo is not a candidate"
assert_stdout_lacks "$CANDIDATES" "hand-written" "a real directory is not a candidate"

# Same bug, exercised through the actual `at bootstrap --clean-global-skills`
# CLI path (not just the pure stale_skill_symlinks() function). `_run` shells
# out to the real `claude`/`codex` CLIs to add/install plugins -- stub it to
# a no-op so this stays hermetic (this file's own contract: "nothing touches
# the real machine config"), while still driving the real cmd_bootstrap()
# code, including the --yes removal path and the os.path.realpath() print
# line for a target that no longer exists.
BOOT_DRY="$(HOME="$FAKEHOME" python3 - "$AT_PY" "$FAKEHOME" "$REPO" <<'PY'
import argparse, importlib.util, sys
spec = importlib.util.spec_from_file_location("at", sys.argv[1])
at = importlib.util.module_from_spec(spec)
spec.loader.exec_module(at)
at._run = lambda cmd: True  # never shell out to the real claude/codex CLIs
args = argparse.Namespace(local=sys.argv[3], claude=False, codex=False, tasks=False,
                           extras=False, personal=False, clean_global_skills=True, yes=False)
at.cmd_bootstrap(args)
PY
)"
assert_stdout_contains "$BOOT_DRY" "$FAKEHOME/.claude/skills/dangling-example" \
  "at bootstrap --clean-global-skills lists the dangling symlink"
assert_stdout_lacks "$BOOT_DRY" "no stale global skill symlinks found" \
  "at bootstrap --clean-global-skills does not claim a clean bill of health"

BOOT_YES="$(HOME="$FAKEHOME" python3 - "$AT_PY" "$FAKEHOME" "$REPO" <<'PY'
import argparse, importlib.util, sys
spec = importlib.util.spec_from_file_location("at", sys.argv[1])
at = importlib.util.module_from_spec(spec)
spec.loader.exec_module(at)
at._run = lambda cmd: True
args = argparse.Namespace(local=sys.argv[3], claude=False, codex=False, tasks=False,
                           extras=False, personal=False, clean_global_skills=True, yes=True)
at.cmd_bootstrap(args)
PY
)"
CANDIDATE_COUNT="$(printf '%s\n' "$CANDIDATES" | grep -c .)"
assert_stdout_contains "$BOOT_YES" "removed $CANDIDATE_COUNT symlink(s)" \
  "at bootstrap --yes removes every stale candidate, including the dangling one"
assert_symlink_gone "$FAKEHOME/.claude/skills/dangling-example" "the dangling symlink is gone after --yes"

# _leaked_untracked_paths: the last-resort safety check `at migrate --commit`
# runs right before it commits. Exercise the pure function directly with a
# synthetic staged list — this legitimately drives its die-branch logic
# (a genuinely leaked path) alongside the exclusion that stops it from
# false-positiving on migrate's own managed paths (see IMPORTANT 3 below).
LEAK_CHECK="$(python3 - "$AT_PY" <<'PY'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("at", sys.argv[1])
at = importlib.util.module_from_spec(spec)
spec.loader.exec_module(at)

staged = ["CLAUDE.md", "wip.txt", "data/blob.bin", ".codex/agents/plan-critic.toml"]
own_paths = {"CLAUDE.md", ".codex/agents/plan-critic.toml"}
untracked_before = ["wip.txt", "data/", ".codex/"]
for path in at._leaked_untracked_paths(staged, own_paths, untracked_before):
    print(path)
PY
)"
assert_eq "$LEAK_CHECK" "$(printf 'data/blob.bin\nwip.txt')" \
  "_leaked_untracked_paths flags genuinely leaked paths and excludes migrate's own managed path"

# --- at migrate: real legacy downstreams (read-only clones) ------------------
# Sources are only ever `git clone`d; the originals are never touched. Each case
# is skipped with a SKIP line when its source is not present on this machine.
LIGHT_SRC="${AT_TEST_LIGHT_SRC:-/home/vi/work/vitalii/repos/models_playground}"
HEAVY_SRC="${AT_TEST_HEAVY_SRC:-/home/vi/work/ratio1/projects/project_r1_redmesh}"
FOREIGN_SRC="${AT_TEST_FOREIGN_SRC:-/home/vi/work/ratio1/projects/project_r1_edge_node}"
WRITING_SRC="${AT_TEST_WRITING_SRC:-/home/vi/work/vitalii/repos/project_technical_writing}"
LEDGER_SCRIPT="$REPO/plugins/agents-tasks/skills/task-ledger/scripts/sync_todo_ledgers.py"

clone_legacy() { # clone_legacy <src> <dst>
  GIT_LFS_SKIP_SMUDGE=1 git clone -q "$1" "$2" || return 1
  git -C "$2" config user.email "test@example.com"
  git -C "$2" config user.name "at test"
  # a clone has no `template` remote of its own; the real downstreams do
  git -C "$2" remote add template git@github.com:toderian/project_template.git
  git -C "$2" config merge.template-keep-local.driver "true"
}

# --- light downstream (no task ledger) --------------------------------------
if [[ -d "$LIGHT_SRC/.git" ]]; then
  LIGHT="$WORKDIR/light"
  clone_legacy "$LIGHT_SRC" "$LIGHT"
  cd "$LIGHT" || exit 1

  DRY_OUT="$(at migrate 2>&1)"; DRY_RC=$?
  assert_eq "$DRY_RC" "0" "at migrate is a dry run by default: $DRY_OUT"
  assert_stdout_contains "$DRY_OUT" "dry run" "the default run says nothing changed"
  assert_stdout_contains "$DRY_OUT" "_base/" "the plan names the legacy trees it would remove"
  assert_eq "$(git status --porcelain | wc -l | tr -d ' ')" "0" "a dry run leaves the tree clean"
  assert_exists "$LIGHT/_base" "a dry run keeps _base/"
  assert_eq "$(git branch --list 'backup/pre-plugin-migration-*' | wc -l | tr -d ' ')" "0" \
    "a dry run creates no backup branch"
  assert_eq "$(git remote | grep -c '^template$')" "1" "a dry run keeps the template remote"
  assert_eq "$(git config --get merge.template-keep-local.driver)" "true" \
    "a dry run keeps the template merge drivers"

  printf 'scratch\n' > dirty.txt
  DIRTY_OUT="$(at migrate --yes 2>&1)"; DIRTY_RC=$?
  assert_eq "$DIRTY_RC" "1" "at migrate refuses a dirty working tree"
  assert_stdout_contains "$DIRTY_OUT" "working tree" "the refusal names the dirty working tree"
  assert_exists "$LIGHT/_base" "the refused run changed nothing"
  rm dirty.txt

  # a downstream's own subagent, its own .agents/ entry, and a template CONTEXT.md stub
  mkdir -p .claude/agents .agents/plugins
  printf -- '---\nname: custom-role\ndescription: a local subagent\n---\n\nBody.\n' \
    > .claude/agents/custom-role.md
  printf '{"name": "local-marketplace"}\n' > .agents/plugins/marketplace.json
  printf '# Context\n\nSeeded from the template; replace with real domain terms.\n' > CONTEXT.md
  git remote add templates https://github.com/toderian/project_template.git
  git remote add upstream-tpl git@github.com:toderian/project_template.git
  git add -A >/dev/null 2>&1
  git commit -qm "local additions"

  MIG_OUT="$(at migrate --yes --commit 2>&1)"; MIG_RC=$?
  assert_eq "$MIG_RC" "0" "at migrate --yes --commit exits 0 on a light downstream: $MIG_OUT"
  for p in _base playbooks skills .claude/hooks .claude/skills .claude-plugin \
           .agents/skills .agents/skill-library.json .agents/skills.enabled.json \
           .claude/agents/implementer.md; do
    assert_missing "$LIGHT/$p" "migrate removes $p"
  done
  assert_eq "$(git remote | grep -c '^template$')" "0" "migrate drops the template remote"
  assert_eq "$(git remote | grep -c '^templates$')" "0" "migrate drops a templates-named remote"
  assert_eq "$(git remote | grep -c '^upstream-tpl$')" "0" "migrate drops a remote by its template URL"
  assert_eq "$(git remote | grep -c '^origin$')" "1" "migrate keeps the project's own remote"
  assert_eq "$(git config --get merge.template-keep-local.driver)" "" \
    "migrate unsets the template merge drivers"
  assert_eq "$(grep -c 'template-keep' .gitattributes)" "0" "migrate strips the merge-driver rules"
  assert_contains .gitattributes "*.pdf binary" "migrate applies the managed .gitattributes block"
  assert_contains .gitignore "# BEGIN agents-template" "migrate applies the managed .gitignore block"
  assert_eq "$(head -n 1 CLAUDE.md)" "@AGENTS.md" "migrate writes CLAUDE.md"
  LIGHT_LINES="$(wc -l < AGENTS.md | tr -d ' ')"
  if [[ "$LIGHT_LINES" -le 200 ]]; then pass; else fail "migrated AGENTS.md is $LIGHT_LINES lines (> 200)"; fi
  assert_eq "$(head -n 1 README.md)" "# light" "an all-template README is replaced by a project stub"
  assert_exists "$LIGHT/.no-commit/AGENTS.md.pre-migration" "migrate keeps the old AGENTS.md"
  assert_exists "$LIGHT/.no-commit/README.md.pre-migration" "migrate keeps the old README.md"
  assert_eq "$(git ls-files .no-commit | wc -l | tr -d ' ')" "0" "the pre-migration copies stay untracked"
  assert_exists "$LIGHT/docs/_plans/.gitkeep" "migrate seeds docs/_plans/"
  assert_exists "$LIGHT/.claude/agents/custom-role.md" "migrate keeps a downstream's own subagent"
  assert_exists "$LIGHT/.agents/plugins/marketplace.json" "migrate keeps other .agents/ entries"
  assert_missing "$LIGHT/CONTEXT.md" "migrate removes a template CONTEXT.md stub"
  assert_eq "$(grep -c '.claude/hooks/' .claude/settings.json)" "0" \
    "migrate drops settings.json hooks that point at .claude/hooks/"
  LIGHT_PLUGINS="$(python3 -c 'import json;d=json.load(open(".claude/settings.json"))["enabledPlugins"];print(d.get("agents-core@agents-template"), "agents-tasks@agents-template" in d)')"
  assert_eq "$LIGHT_PLUGINS" "True False" "migrate enables agents-core only (no task ledger here)"
  if diff -q .codex/agents/implementer.toml "$REPO/plugins/agents-core/codex/agents/implementer.toml" >/dev/null; then
    pass
  else
    fail "migrate regenerates .codex/agents/*.toml from the plugin"
  fi
  assert_eq "$(git branch --list 'backup/pre-plugin-migration-*' | wc -l | tr -d ' ')" "1" \
    "migrate creates one backup branch"
  assert_eq "$(git status --porcelain | wc -l | tr -d ' ')" "0" "migrate --commit leaves a clean tree"
  assert_eq "$(git log -1 --format=%s)" "chore: migrate to agents-template plugins" \
    "migrate --commit uses the documented subject"
  assert_stdout_contains "$(git log -1 --format=%B)" "Co-Authored-By" "the migration commit carries the trailer"
  at doctor >/dev/null 2>&1
  assert_eq "$?" "0" "at doctor exits 0 on the migrated light downstream"
else
  echo "SKIP: light downstream migration (no clone source at $LIGHT_SRC)"
fi

# --- at migrate --commit on a downstream that locally gitignores .claude/ ---
# A downstream's own `.gitignore` may ignore a path migrate itself manages
# (its own local convention, unrelated to the managed block) — `--commit`
# must still stage and commit that path; it is force-added on purpose.
if [[ -d "$LIGHT_SRC/.git" ]]; then
  GITIGNORED="$WORKDIR/light-gitignored-claude"
  clone_legacy "$LIGHT_SRC" "$GITIGNORED"
  cd "$GITIGNORED" || exit 1
  printf '\n.claude/\n' >> .gitignore
  git add .gitignore
  git commit -qm "locally ignore .claude/ (simulates a downstream's own rule)"
  GI_OUT="$(at migrate --yes --commit 2>&1)"; GI_RC=$?
  assert_eq "$GI_RC" "0" \
    "migrate succeeds when the downstream's own .gitignore ignores .claude/: $GI_OUT"
  assert_stdout_contains "$(git show --name-only HEAD)" ".claude/settings.json" \
    "the migration commit includes .claude/settings.json even though it is locally gitignored"
else
  echo "SKIP: migrate with a locally gitignored .claude/ (no clone source at $LIGHT_SRC)"
fi

# --- at migrate --allow-untracked: untracked-only dirtiness -----------------
# Real targets carry untracked paths that must never be committed or removed
# (a multi-GB untracked attachments tree, a WIP task file mid-draft). `at
# migrate` must be usable there without stashing or committing them first.
if [[ -d "$LIGHT_SRC/.git" ]]; then
  UNTRACKED="$WORKDIR/light-untracked"
  clone_legacy "$LIGHT_SRC" "$UNTRACKED"
  cd "$UNTRACKED" || exit 1

  printf 'scratch\n' > wip.txt
  mkdir -p data
  printf '\x00\x01' > data/blob.bin

  NOFLAG_OUT="$(at migrate --yes 2>&1)"; NOFLAG_RC=$?
  assert_eq "$NOFLAG_RC" "1" "untracked-only dirtiness still refuses without --allow-untracked"
  assert_stdout_contains "$NOFLAG_OUT" "working tree" \
    "the refusal without --allow-untracked names the dirty working tree"
  assert_exists "$UNTRACKED/_base" "the refused run changed nothing"
  assert_exists "$UNTRACKED/wip.txt" "the refused run left the untracked file alone"

  ALLOW_OUT="$(at migrate --allow-untracked --yes --commit 2>&1)"; ALLOW_RC=$?
  assert_eq "$ALLOW_RC" "0" \
    "--allow-untracked --yes --commit succeeds with untracked-only dirtiness: $ALLOW_OUT"
  assert_stdout_contains "$ALLOW_OUT" "2 untracked path(s)" \
    "migrate prints the count of untracked paths it is leaving alone"
  assert_exists "$UNTRACKED/wip.txt" "wip.txt is still on disk after migrate"
  assert_exists "$UNTRACKED/data/blob.bin" "data/blob.bin is still on disk after migrate"
  assert_eq "$(git ls-files wip.txt data | wc -l | tr -d ' ')" "0" \
    "wip.txt and data/ are still untracked after migrate"
  LEAKED_IN_COMMIT="$(git show --name-only HEAD | grep -cE '^(wip\.txt|data/)' || true)"
  assert_eq "$LEAKED_IN_COMMIT" "0" "the migration commit does not contain wip.txt or data/"
  UNTRACKED_STATUS="$(git status --porcelain)"
  assert_eq "$UNTRACKED_STATUS" "$(printf '?? data/\n?? wip.txt')" \
    "after migrate, git status --porcelain shows exactly the pre-existing untracked paths"
  assert_eq "$(git ls-files .no-commit | wc -l | tr -d ' ')" "0" \
    "the pre-migration copies stay untracked even with --allow-untracked"
  assert_contains .gitignore ".no-commit/" \
    "the managed .gitignore block still ignores .no-commit/ (pre-migration copies stay ignored)"
  assert_eq "$(git log -1 --format=%s)" "chore: migrate to agents-template plugins" \
    "the --allow-untracked migration still commits under the documented subject"
else
  echo "SKIP: at migrate --allow-untracked (no clone source at $LIGHT_SRC)"
fi

# a tracked modification alongside --allow-untracked still refuses (only
# untracked-only dirtiness is exempt from the clean-tree precondition)
if [[ -d "$LIGHT_SRC/.git" ]]; then
  TRACKEDDIRTY="$WORKDIR/light-tracked-dirty"
  clone_legacy "$LIGHT_SRC" "$TRACKEDDIRTY"
  cd "$TRACKEDDIRTY" || exit 1

  printf '\nlocal edit\n' >> README.md
  TRACKED_OUT="$(at migrate --allow-untracked --yes 2>&1)"; TRACKED_RC=$?
  assert_eq "$TRACKED_RC" "1" \
    "a tracked modification still refuses even with --allow-untracked"
  assert_stdout_contains "$TRACKED_OUT" "working tree" \
    "the refusal with a tracked modification names the dirty working tree"
  assert_exists "$TRACKEDDIRTY/_base" "the refused run changed nothing"
else
  echo "SKIP: at migrate --allow-untracked tracked-dirty refusal (no clone source at $LIGHT_SRC)"
fi

# --- heavy downstream (task ledger, LFS, project rules) ---------------------
if [[ -d "$HEAVY_SRC/.git" ]]; then
  HEAVY="$WORKDIR/heavy"
  clone_legacy "$HEAVY_SRC" "$HEAVY"
  cd "$HEAVY" || exit 1

  LFS_BEFORE="$(grep -c 'filter=lfs' .gitattributes)"
  TODOS_BEFORE="$(find docs/tasks_manager/_todos -type f | wc -l | tr -d ' ')"
  LEDGER_ERR_BEFORE="$(python3 "$LEDGER_SCRIPT" --check --root "$HEAVY" 2>&1 | grep -c 'ERROR' || true)"

  HEAVY_OUT="$(at migrate --yes --commit 2>&1)"; HEAVY_RC=$?
  assert_eq "$HEAVY_RC" "0" "at migrate --yes --commit exits 0 on a heavy downstream: $HEAVY_OUT"
  for p in _base playbooks skills .claude/hooks .claude/skills .claude-plugin \
           .agents/skills .agents/skill-library.json .agents/skills.enabled.json; do
    assert_missing "$HEAVY/$p" "heavy migrate removes $p"
  done
  assert_eq "$(git remote | grep -c '^template$')" "0" "heavy migrate drops the template remote"
  assert_eq "$(grep -c 'template-keep' .gitattributes)" "0" "heavy migrate strips the merge-driver rules"
  assert_eq "$(grep -c 'filter=lfs' .gitattributes)" "$LFS_BEFORE" \
    "heavy migrate keeps every project Git LFS rule"
  assert_eq "$(grep -c '.claude/hooks/' .claude/settings.json)" "0" \
    "heavy migrate drops settings.json hooks that point at .claude/hooks/"
  assert_contains AGENTS.md "docs/resources/CONTEXT.md" "heavy migrate preserves the project rules"
  assert_contains AGENTS.md "at ledger check" "a preserved rule is repointed at the at CLI"
  assert_eq "$(grep -c '_base/' AGENTS.md)" "0" "no preserved rule still points into _base/"
  HEAVY_LINES="$(wc -l < AGENTS.md | tr -d ' ')"
  if [[ "$HEAVY_LINES" -le 200 ]]; then pass; else fail "migrated AGENTS.md is $HEAVY_LINES lines (> 200)"; fi
  assert_exists "$HEAVY/.no-commit/AGENTS.md.pre-migration" "heavy migrate keeps the old AGENTS.md"
  assert_eq "$(find docs/tasks_manager/_todos -type f | wc -l | tr -d ' ')" "$TODOS_BEFORE" \
    "heavy migrate leaves the task ledger alone"
  HEAVY_PLUGINS="$(python3 -c 'import json;d=json.load(open(".claude/settings.json"))["enabledPlugins"];print(d.get("agents-core@agents-template"), d.get("agents-tasks@agents-template"))')"
  assert_eq "$HEAVY_PLUGINS" "True True" "heavy migrate enables agents-core and agents-tasks"
  assert_exists "$HEAVY/CONTEXT.md" "heavy migrate keeps a CONTEXT.md that is not the template stub"
  assert_exists "$HEAVY/.config/repos.project.md" "heavy migrate keeps the repo registry"
  assert_exists "$HEAVY/workbooks/README.md" "heavy migrate keeps the workbooks registry"
  assert_eq "$(git branch --list 'backup/pre-plugin-migration-*' | wc -l | tr -d ' ')" "1" \
    "heavy migrate creates one backup branch"
  assert_eq "$(git status --porcelain | wc -l | tr -d ' ')" "0" "heavy migrate --commit leaves a clean tree"
  LEDGER_ERR_AFTER="$(at ledger check 2>&1 | grep -c 'ERROR' || true)"
  assert_eq "$LEDGER_ERR_AFTER" "$LEDGER_ERR_BEFORE" "heavy migrate adds no ledger errors"
  at doctor >/dev/null 2>&1
  assert_eq "$?" "0" "at doctor exits 0 on the migrated heavy downstream"
else
  echo "SKIP: heavy downstream migration (no clone source at $HEAVY_SRC)"
fi

# --- downstream with foreign files under skills/ ----------------------------
if [[ -d "$FOREIGN_SRC/.git" ]]; then
  FOREIGN="$WORKDIR/foreign"
  clone_legacy "$FOREIGN_SRC" "$FOREIGN"
  cd "$FOREIGN" || exit 1

  FOREIGN_OUT="$(at migrate --yes 2>&1)"; FOREIGN_RC=$?
  assert_eq "$FOREIGN_RC" "1" "at migrate aborts on foreign files under skills/"
  assert_stdout_contains "$FOREIGN_OUT" "skills/watch.py" "the abort names the first foreign file"
  assert_stdout_contains "$FOREIGN_OUT" "skills/run_container_app.py" "the abort names the second foreign file"
  assert_exists "$FOREIGN/_base" "the aborted run changed nothing"
  assert_eq "$(git status --porcelain | wc -l | tr -d ' ')" "0" "the aborted run leaves the tree clean"
  assert_eq "$(git branch --list 'backup/pre-plugin-migration-*' | wc -l | tr -d ' ')" "0" \
    "the aborted run creates no backup branch"
else
  echo "SKIP: foreign-file migration abort (no clone source at $FOREIGN_SRC)"
fi

# --- at migrate: synthetic legacy repos --------------------------------------
SEED_AGENTS="$REPO/plugins/agents-core/seed/AGENTS.md"
SEED_H2="$(grep -c '^## ' "$SEED_AGENTS")"

make_legacy_repo() { # make_legacy_repo <dir>
  mkdir -p "$1/_base" "$1/playbooks"
  printf '# base contract\n' > "$1/_base/AGENTS.md"
  printf '# Playbooks\n' > "$1/playbooks/README.md"
  git -C "$1" init -q .
  git -C "$1" config user.email "test@example.com"
  git -C "$1" config user.name "at test"
}

# a legacy AGENTS.md with title-case headings (bootstrap_work's shape)
TITLECASE="$WORKDIR/legacy-titlecase"
make_legacy_repo "$TITLECASE"
cat > "$TITLECASE/AGENTS.md" <<'LEGACY'
# AGENTS.md

> Auto-loaded entrypoint for the agent operating contract. Both Claude Code and
> Codex load this file automatically at session start.
>
> Before acting, also read [`_base/AGENTS.md`](./_base/AGENTS.md).

## Project-Specific Overrides

### Repository Purpose

- Bootstrap rule: `workspace.yml` defines the workspace manifest.

## Per-Directory Overrides

For monorepos, place an `AGENTS.md` in any subdirectory to override the root contract.
LEGACY
git -C "$TITLECASE" add -A >/dev/null 2>&1
git -C "$TITLECASE" commit -qm init
cd "$TITLECASE" || exit 1
TITLE_OUT="$(at migrate --yes 2>&1)"; TITLE_RC=$?
assert_eq "$TITLE_RC" "0" "at migrate handles a title-case overrides heading: $TITLE_OUT"
assert_contains AGENTS.md "workspace.yml" "a project rule under a title-case heading survives"
assert_eq "$(grep -c 'Auto-loaded entrypoint' AGENTS.md)" "0" "the template preamble blockquote is dropped"
assert_eq "$(grep -ci 'per-directory overrides' AGENTS.md)" "0" "the per-directory section is dropped"
assert_contains AGENTS.md "### People and coordination" "the seed's later project slots survive"
assert_eq "$(grep -c '^## ' AGENTS.md)" "$SEED_H2" "no extra H2 is injected into the seed"
TITLE_LINES="$(wc -l < AGENTS.md | tr -d ' ')"
if [[ "$TITLE_LINES" -le 200 ]]; then pass; else fail "migrated AGENTS.md is $TITLE_LINES lines (> 200)"; fi

# a legacy AGENTS.md with no overrides heading at all
NOHEADING="$WORKDIR/legacy-noheading"
make_legacy_repo "$NOHEADING"
cat > "$NOHEADING/AGENTS.md" <<'LEGACY'
# AGENTS.md

> Auto-loaded entrypoint for the agent operating contract.

## House rules

- Never rewrite the published vault history.
LEGACY
git -C "$NOHEADING" add -A >/dev/null 2>&1
git -C "$NOHEADING" commit -qm init
cd "$NOHEADING" || exit 1
NOHEAD_OUT="$(at migrate --yes 2>&1)"; NOHEAD_RC=$?
assert_eq "$NOHEAD_RC" "0" "at migrate survives an AGENTS.md with no overrides heading: $NOHEAD_OUT"
assert_stdout_contains "$NOHEAD_OUT" "WARN" "migrate warns when it can not tell rules from boilerplate"
# `  WARN` (2 leading spaces) is migrate's own warning line; unindented `WARN`
# further down is unrelated output from the `at doctor` run migrate triggers.
assert_eq "$(printf '%s\n' "$NOHEAD_OUT" | grep -c '^  WARN')" "1" \
  "the migrate WARN line is printed exactly once, not once in the plan and again in the summary"
assert_stdout_contains "$NOHEAD_OUT" ".no-commit/AGENTS.md.pre-migration" \
  "the warning points at the saved copy to hand-merge"
assert_eq "$(grep -c 'published vault history' AGENTS.md)" "0" \
  "nothing is preserved when the overrides heading is missing"
if diff -q AGENTS.md "$SEED_AGENTS" >/dev/null; then pass; else fail "AGENTS.md is the untouched seed"; fi
assert_exists "$NOHEADING/.no-commit/AGENTS.md.pre-migration" "the old AGENTS.md is still saved"

# downstream-authored content inside playbooks/ aborts the migration
FOREIGNPB="$WORKDIR/legacy-foreign-playbook"
make_legacy_repo "$FOREIGNPB"
mkdir -p "$FOREIGNPB/playbooks/skills/personal/my-thing/scripts" \
         "$FOREIGNPB/playbooks/skills/engineering" "$FOREIGNPB/playbooks/conventions"
printf '# My Thing\n' > "$FOREIGNPB/playbooks/skills/personal/my-thing.md"
printf 'echo hi\n' > "$FOREIGNPB/playbooks/skills/personal/my-thing/scripts/run.sh"
printf '# tdd\n' > "$FOREIGNPB/playbooks/skills/engineering/tdd.md"
printf '# todo\n' > "$FOREIGNPB/playbooks/conventions/todo-convention.md"
git -C "$FOREIGNPB" add -A >/dev/null 2>&1
git -C "$FOREIGNPB" commit -qm init
cd "$FOREIGNPB" || exit 1
PB_OUT="$(at migrate --yes 2>&1)"; PB_RC=$?
assert_eq "$PB_RC" "1" "at migrate aborts on downstream-authored playbooks"
assert_stdout_contains "$PB_OUT" "playbooks/skills/personal/my-thing.md" "the abort names the foreign playbook"
assert_stdout_contains "$PB_OUT" "playbooks/skills/personal/my-thing/scripts/run.sh" \
  "the abort names the foreign playbook's sidecar"
assert_stdout_lacks "$PB_OUT" "playbooks/skills/engineering/tdd.md" "a template playbook is not flagged"
assert_stdout_lacks "$PB_OUT" "conventions/todo-convention.md" "a template convention is not flagged"
assert_exists "$FOREIGNPB/_base" "the aborted playbook run changed nothing"
assert_eq "$(git branch --list 'backup/pre-plugin-migration-*' | wc -l | tr -d ' ')" "0" \
  "the aborted playbook run creates no backup branch"

# an untracked file living inside a tree migrate deletes must refuse instead
# of being silently destroyed by `_remove()`/`shutil.rmtree`
UNTRACKEDINSIDE="$WORKDIR/legacy-untracked-inside-removal"
make_legacy_repo "$UNTRACKEDINSIDE"
mkdir -p "$UNTRACKEDINSIDE/.claude/hooks"
printf '#!/bin/bash\necho legacy\n' > "$UNTRACKEDINSIDE/.claude/hooks/legacy-hook.sh"
git -C "$UNTRACKEDINSIDE" add -A >/dev/null 2>&1
git -C "$UNTRACKEDINSIDE" commit -qm init
cd "$UNTRACKEDINSIDE" || exit 1
printf 'private notes\n' > _base/local-notes.md
printf '#!/bin/bash\necho mine\n' > .claude/hooks/my-own-hook.sh
GUARD_OUT="$(at migrate --allow-untracked --yes 2>&1)"; GUARD_RC=$?
assert_eq "$GUARD_RC" "1" \
  "migrate refuses when an untracked file lives inside a tree it deletes"
assert_stdout_contains "$GUARD_OUT" "_base/local-notes.md" \
  "the refusal names the untracked file under _base/"
assert_stdout_contains "$GUARD_OUT" ".claude/hooks/my-own-hook.sh" \
  "the refusal names the untracked file under .claude/hooks/"
assert_exists "$UNTRACKEDINSIDE/_base/local-notes.md" \
  "the untracked file under _base/ was not deleted"
assert_exists "$UNTRACKEDINSIDE/.claude/hooks/my-own-hook.sh" \
  "the untracked file under .claude/hooks/ was not deleted"
assert_exists "$UNTRACKEDINSIDE/_base" "the refused run left _base/ in place"
assert_eq "$(git branch --list 'backup/pre-plugin-migration-*' | wc -l | tr -d ' ')" "0" \
  "no backup branch is created when migrate refuses on an untracked file inside a removed tree"

# bidirectional containment: when a wholly-untracked ANCESTOR collapses to one
# entry (`?? .claude/`) that is a strict PARENT of a removal target
# (`.claude/hooks/`), the guard must still fire — checking only "untracked
# entry inside a removal" misses this shape (the removal is inside the
# untracked entry, not the other way around).
UNTRACKEDANCESTOR="$WORKDIR/legacy-untracked-ancestor"
make_legacy_repo "$UNTRACKEDANCESTOR"
git -C "$UNTRACKEDANCESTOR" add -A >/dev/null 2>&1
git -C "$UNTRACKEDANCESTOR" commit -qm init
cd "$UNTRACKEDANCESTOR" || exit 1
mkdir -p .claude/hooks
printf '#!/bin/bash\necho legacy\n' > .claude/hooks/legacy-hook.sh
printf '#!/bin/bash\necho mine\n' > .claude/hooks/my-own-hook.sh
if [[ "$(git status --porcelain)" == "?? .claude/" ]]; then
  pass
else
  fail ".claude/ collapses to one wholly-untracked entry (fixture assumption)"
fi
ANCESTOR_OUT="$(at migrate --allow-untracked --yes 2>&1)"; ANCESTOR_RC=$?
assert_eq "$ANCESTOR_RC" "1" \
  "migrate refuses when a wholly-untracked ancestor contains a removal target"
assert_stdout_contains "$ANCESTOR_OUT" ".claude/" \
  "the refusal names the untracked ancestor directory"
assert_exists "$UNTRACKEDANCESTOR/.claude/hooks/my-own-hook.sh" \
  "the untracked file under the collapsed ancestor was not deleted"
assert_exists "$UNTRACKEDANCESTOR/.claude/hooks/legacy-hook.sh" \
  "the template hook file under the collapsed ancestor was not deleted"
assert_eq "$(git branch --list 'backup/pre-plugin-migration-*' | wc -l | tr -d ' ')" "0" \
  "no backup branch is created when migrate refuses on a collapsed untracked ancestor"

# the .agents/ analogue: `?? .agents/` containing skill-library.json
UNTRACKEDAGENTS="$WORKDIR/legacy-untracked-agents-ancestor"
make_legacy_repo "$UNTRACKEDAGENTS"
git -C "$UNTRACKEDAGENTS" add -A >/dev/null 2>&1
git -C "$UNTRACKEDAGENTS" commit -qm init
cd "$UNTRACKEDAGENTS" || exit 1
mkdir -p .agents
printf '{"skills": []}\n' > .agents/skill-library.json
if [[ "$(git status --porcelain)" == "?? .agents/" ]]; then
  pass
else
  fail ".agents/ collapses to one wholly-untracked entry (fixture assumption)"
fi
AGENTSANCESTOR_OUT="$(at migrate --allow-untracked --yes 2>&1)"; AGENTSANCESTOR_RC=$?
assert_eq "$AGENTSANCESTOR_RC" "1" \
  "migrate refuses when a wholly-untracked .agents/ ancestor contains a removal target"
assert_stdout_contains "$AGENTSANCESTOR_OUT" ".agents/" \
  "the refusal names the untracked .agents/ ancestor directory"
assert_exists "$UNTRACKEDAGENTS/.agents/skill-library.json" \
  "skill-library.json under the collapsed ancestor was not deleted"

# a foreign untracked file sharing a not-yet-tracked .codex/ directory with
# the six .codex/agents/*.toml migrate itself seeds must not false-positive
# the leak check (IMPORTANT 3): migrate created those paths itself.
LEAKCODEX="$WORKDIR/legacy-leak-codex"
make_legacy_repo "$LEAKCODEX"
git -C "$LEAKCODEX" add -A >/dev/null 2>&1
git -C "$LEAKCODEX" commit -qm init
cd "$LEAKCODEX" || exit 1
mkdir -p .codex/agents
printf 'not a template file\n' > .codex/agents/README.txt
if [[ "$(git status --porcelain)" == "?? .codex/" ]]; then
  pass
else
  fail ".codex/ collapses to one untracked entry before migrate runs (fixture assumption)"
fi
LEAKCODEX_OUT="$(at migrate --allow-untracked --yes --commit 2>&1)"; LEAKCODEX_RC=$?
assert_eq "$LEAKCODEX_RC" "0" \
  "migrate succeeds when a foreign untracked file shares a collapsed dir with paths it seeds: $LEAKCODEX_OUT"
LEAKCODEX_COMMIT="$(git show --name-only HEAD)"
assert_stdout_contains "$LEAKCODEX_COMMIT" ".codex/agents/plan-critic.toml" \
  "the six generated .codex/agents/*.toml are in the commit"
assert_stdout_lacks "$LEAKCODEX_COMMIT" ".codex/agents/README.txt" \
  "the foreign untracked file is not in the commit"
assert_eq "$(git ls-files .codex/agents/README.txt | wc -l | tr -d ' ')" "0" \
  ".codex/agents/README.txt is still untracked after migrate"
assert_exists "$LEAKCODEX/.codex/agents/README.txt" \
  ".codex/agents/README.txt still exists on disk"

# an untracked WIP task file sharing a not-yet-tracked docs/tasks_manager/
# tree with the ledger files migrate seeds must survive untouched — proves
# the leak-check exclusion holds across a whole freshly-seeded tree, not
# just a single directory. The process exit code is not asserted here:
# `at doctor`'s embedded ledger check correctly flags the freshly-added,
# never-synced task as stale (run `at ledger sync`) — an orthogonal, correct
# signal unrelated to the leak check. "Succeeds" here means the migration
# commit happens and the leak check does not false-positive on its own
# seeded files.
LEAKWIP="$WORKDIR/legacy-leak-wip-task"
make_legacy_repo "$LEAKWIP"
git -C "$LEAKWIP" add -A >/dev/null 2>&1
git -C "$LEAKWIP" commit -qm init
cd "$LEAKWIP" || exit 1
mkdir -p docs/tasks_manager/_todos
printf '# scratch WIP notes, not a real task file\n' > docs/tasks_manager/_todos/WIP-999-F_wip.md
LEAKWIP_OUT="$(at migrate --allow-untracked --yes --commit 2>&1)"
assert_stdout_contains "$LEAKWIP_OUT" "committed" \
  "migrate commits despite an untracked WIP file sharing the freshly-seeded docs/tasks_manager/ tree"
assert_stdout_lacks "$LEAKWIP_OUT" "refusing to commit" \
  "the leak check does not false-positive on migrate's own freshly-seeded ledger files"
LEAKWIP_COMMIT="$(git show --name-only HEAD)"
assert_stdout_lacks "$LEAKWIP_COMMIT" "WIP-999-F_wip.md" \
  "the untracked WIP task file is not in the commit"
assert_eq "$(git ls-files docs/tasks_manager/_todos/WIP-999-F_wip.md | wc -l | tr -d ' ')" "0" \
  "the WIP task file is still untracked after migrate"
assert_exists "$LEAKWIP/docs/tasks_manager/_todos/WIP-999-F_wip.md" \
  "the WIP task file still exists on disk"

# adoption (overwrite category): an untracked, hand-edited .codex/agents/*.toml
# at a path migrate itself regenerates must be backed up before being
# overwritten, not silently discarded.
ADOPTOVERWRITE="$WORKDIR/legacy-adopt-overwrite"
make_legacy_repo "$ADOPTOVERWRITE"
git -C "$ADOPTOVERWRITE" add -A >/dev/null 2>&1
git -C "$ADOPTOVERWRITE" commit -qm init
cd "$ADOPTOVERWRITE" || exit 1
mkdir -p .codex/agents
printf 'hand edited content, not the plugin template\n' > .codex/agents/implementer.toml
DRY_ADOPT_OUT="$(at migrate --allow-untracked 2>&1)"
assert_eq "$(printf '%s\n' "$DRY_ADOPT_OUT" | grep -c '^  adopt    .codex/agents/implementer.toml')" "1" \
  "the dry-run plan prints the adopt line for the hand-edited toml exactly once"
ADOPT_OUT="$(at migrate --allow-untracked --yes --commit 2>&1)"; ADOPT_RC=$?
assert_eq "$ADOPT_RC" "0" "migrate succeeds adopting an untracked hand-edited .codex/agents/*.toml: $ADOPT_OUT"
assert_eq "$(printf '%s\n' "$ADOPT_OUT" | grep -c '^  adopt    .codex/agents/implementer.toml')" "1" \
  "the adopt line for the hand-edited toml is printed exactly once"
assert_contains .no-commit/pre-migration/.codex/agents/implementer.toml \
  "hand edited content, not the plugin template" \
  "the pre-existing untracked content is saved under .no-commit/pre-migration/ before being overwritten"
if diff -q .codex/agents/implementer.toml \
     "$REPO/plugins/agents-core/codex/agents/implementer.toml" >/dev/null; then
  pass
else
  fail "the committed toml equals the plugin's generated version"
fi
assert_stdout_contains "$(git show --name-only HEAD)" ".codex/agents/implementer.toml" \
  "the adopted toml is in the migration commit"
assert_eq "$(git ls-files .no-commit | wc -l | tr -d ' ')" "0" \
  "the pre-migration backup stays untracked"

# adoption (merge category): an untracked .claude/settings.json with a user
# key must be merged (managed keys added) and committed, not silently
# discarded — the user's own key must survive in the committed file.
ADOPTMERGE="$WORKDIR/legacy-adopt-merge"
make_legacy_repo "$ADOPTMERGE"
git -C "$ADOPTMERGE" add -A >/dev/null 2>&1
git -C "$ADOPTMERGE" commit -qm init
cd "$ADOPTMERGE" || exit 1
mkdir -p .claude
printf '{"model": "opus"}\n' > .claude/settings.json
ADOPTMERGE_OUT="$(at migrate --allow-untracked --yes --commit 2>&1)"; ADOPTMERGE_RC=$?
assert_eq "$ADOPTMERGE_RC" "0" "migrate succeeds adopting an untracked .claude/settings.json: $ADOPTMERGE_OUT"
assert_eq "$(printf '%s\n' "$ADOPTMERGE_OUT" | grep -c '^  adopt    .claude/settings.json')" "1" \
  "the adopt line for .claude/settings.json is printed exactly once"
ADOPTMERGE_MODEL="$(python3 -c 'import json;print(json.load(open(".claude/settings.json")).get("model"))')"
assert_eq "$ADOPTMERGE_MODEL" "opus" \
  "the user's own settings.json key survives the merge"
assert_stdout_contains "$(git show --name-only HEAD)" ".claude/settings.json" \
  "the adopted settings.json is in the migration commit"

# --- downstream with its own playbook skill (real repo) ---------------------
if [[ -d "$WRITING_SRC/.git" ]]; then
  WRITING="$WORKDIR/writing"
  clone_legacy "$WRITING_SRC" "$WRITING"
  cd "$WRITING" || exit 1
  WRITING_OUT="$(at migrate --dry-run 2>&1)"; WRITING_RC=$?
  assert_eq "$WRITING_RC" "1" "at migrate aborts on a downstream that authored its own playbook"
  assert_stdout_contains "$WRITING_OUT" "google-docs-refine" "the abort names the downstream's own skill"
  assert_eq "$(git status --porcelain | wc -l | tr -d ' ')" "0" "the aborted dry run leaves the tree clean"
else
  echo "SKIP: downstream-authored playbook abort (no clone source at $WRITING_SRC)"
fi

# --- summary ----------------------------------------------------------------
cd "$REPO" || exit 1
echo "test-at: ${PASS_COUNT} passed, ${FAIL_COUNT} failed"
[[ "$FAIL_COUNT" -eq 0 ]]
