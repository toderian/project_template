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

for f in AGENTS.md CLAUDE.md .claude/settings.json .claude/statusline.sh .codex/agents/implementer.toml \
         docs/tasks_manager/_todos docs/tasks_manager/_areas.md docs/tasks_manager/_roadmap.md \
         docs/tasks_manager/_logs docs/tasks_manager/_runs docs/areas/_overview.md docs/resources/CONTEXT.md \
         docs/_plans/.gitkeep artifacts/README.md workbooks/README.md .config/repos.project.md \
         .caveman.json; do
  assert_exists "$PROJECT/$f" "at init --all creates $f"
done

if [[ -x .claude/statusline.sh ]]; then pass; else fail ".claude/statusline.sh is executable"; fi
STATUSLINE_FALLBACK="$(echo '{"model":{"display_name":"Sonnet 5"},"workspace":{"current_dir":"/x/y/z"}}' | HOME=/tmp/at-test-no-gsd-$$ .claude/statusline.sh)"
assert_stdout_contains "$STATUSLINE_FALLBACK" "Sonnet 5" "statusline.sh fallback shows the model name"
assert_stdout_contains "$STATUSLINE_FALLBACK" "z" "statusline.sh fallback shows the directory"

assert_contains .gitignore "# BEGIN agents-template" ".gitignore has BEGIN marker"
assert_contains .gitignore "# END agents-template" ".gitignore has END marker"
assert_contains .gitignore "node_modules/" ".gitignore keeps pre-existing content"
assert_contains .gitignore ".no-commit/" ".gitignore managed block ignores local-only dirs"
assert_contains .gitignore ".caveman.json" ".gitignore managed block keeps the local caveman switch uncommitted"
assert_contains .gitignore "docs/tasks_manager/_runs/**/diff.patch" ".gitignore managed block ignores execute-plan review packages"
assert_contains .gitignore "docs/tasks_manager/_runs/*/lock" ".gitignore managed block ignores the execute-plan run lock"
assert_eq "$(python3 -c 'import json;d=json.load(open(".caveman.json"));print("defaultMode" in d, d["defaultMode"])')" "True None" \
  "the seeded .caveman.json carries a null defaultMode so caveman falls through to the user config (on by default)"
assert_eq "$(git check-ignore .caveman.json)" ".caveman.json" "the seeded .caveman.json is ignored by git"
printf '{"defaultMode": "off"}\n' > .caveman.json
at init >/dev/null 2>&1
assert_eq "$(python3 -c 'import json;print(json.load(open(".caveman.json"))["defaultMode"])')" "off" \
  "re-running at init keeps a locally edited .caveman.json"
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
SETTINGS_CAVEMAN="$(python3 -c 'import json;d=json.load(open(".claude/settings.json"));print(d["enabledPlugins"].get("caveman@caveman"), d["extraKnownMarketplaces"]["caveman"]["source"]["repo"])')"
assert_eq "$SETTINGS_CAVEMAN" "True JuliusBrussee/caveman" "settings.json enables the caveman companion from its own marketplace"
SETTINGS_DENY="$(python3 -c 'import json;print("\n".join(json.load(open(".claude/settings.json"))["permissions"]["deny"]))')"
assert_stdout_contains "$SETTINGS_DENY" "Read(./.creds/**)" "settings.json denies reads of the local credential dir"
SETTINGS_ASK="$(python3 -c 'import json;print("\n".join(json.load(open(".claude/settings.json"))["permissions"]["ask"]))')"
assert_stdout_contains "$SETTINGS_ASK" "agents.allowProtectedPush" "settings.json asks before a confirmed protected push"
assert_stdout_contains "$SETTINGS_ASK" "gh pr merge" "settings.json asks before a PR merge"

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

# a custom statusLine survives re-init (never replaced once set)
python3 -c 'import json, pathlib
p = pathlib.Path(".claude/settings.json")
d = json.loads(p.read_text())
d["statusLine"] = {"type": "command", "command": "echo custom"}
p.write_text(json.dumps(d, indent=2) + "\n")'
at init --all >/dev/null 2>&1
STATUSLINE_CMD="$(python3 -c 'import json;print(json.load(open(".claude/settings.json"))["statusLine"]["command"])')"
assert_eq "$STATUSLINE_CMD" "echo custom" "at init never replaces a custom statusLine"

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
assert_stdout_contains "$DOCTOR_OUT" "caveman@caveman is enabled in .claude/settings.json" \
  "at doctor checks every plugin the seed enables"

# a settings.json from before the companion existed is reported as behind
python3 - <<'PY'
import json, pathlib
p = pathlib.Path(".claude/settings.json")
d = json.loads(p.read_text())
d["enabledPlugins"].pop("caveman@caveman")
p.write_text(json.dumps(d, indent=2) + "\n")
PY
DOCTOR_NOCAVE="$(at doctor 2>&1)"
if printf '%s\n' "$DOCTOR_NOCAVE" | grep -qE '^WARN +caveman@caveman is not enabled'; then
  pass
else
  fail "doctor warns when the companion is not enabled: $DOCTOR_NOCAVE"
fi
INIT_CAVE="$(at init --with-tasks 2>&1)"
assert_stdout_contains "$INIT_CAVE" " merged  .claude/settings.json" "re-running at init merges the companion back in"

# a settings.json seeded before the `ask` rules existed is reported, then repaired by `at init`
assert_stdout_contains "$DOCTOR_OUT" ".claude/settings.json carries the seed permission rules" \
  "at doctor confirms the seed permission rules on a fresh seed"
python3 - <<'PY'
import json, pathlib
p = pathlib.Path(".claude/settings.json")
d = json.loads(p.read_text())
d["permissions"].pop("ask")
d["permissions"]["deny"].remove("Read(./.creds/**)")
p.write_text(json.dumps(d, indent=2) + "\n")
PY
DOCTOR_NOASK="$(at doctor 2>&1)"
if printf '%s\n' "$DOCTOR_NOASK" | grep -qE '^WARN +\.claude/settings\.json is missing 3 seed permission rule'; then
  pass
else
  fail "doctor warns about missing seed permission rules: $DOCTOR_NOASK"
fi
assert_stdout_contains "$DOCTOR_NOASK" "ask: Bash(gh pr merge*)" "doctor names the missing ask rule"
assert_stdout_contains "$DOCTOR_NOASK" "deny: Read(./.creds/**)" "doctor names the missing deny rule"
python3 - <<'PY'
import json, pathlib
p = pathlib.Path(".claude/settings.json")
d = json.loads(p.read_text())
d["permissions"]["ask"] = ["Bash(terraform apply*)"]
p.write_text(json.dumps(d, indent=2) + "\n")
PY
at init --with-tasks >/dev/null 2>&1
ASK_MERGED="$(python3 -c 'import json;print(json.load(open(".claude/settings.json"))["permissions"]["ask"])')"
assert_eq "$ASK_MERGED" "['Bash(terraform apply*)', 'Bash(git *agents.allowProtectedPush*)', 'Bash(gh pr merge*)']" \
  "at init unions the seed ask rules after the repo's own"
assert_stdout_contains "$(at doctor 2>&1)" ".claude/settings.json carries the seed permission rules" \
  "doctor is clean once at init merged the rules"

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

# Strict harness checks are separate from the repository checks used by migrate.
python3 - "$AT_PY" "$PROJECT" "$WORKDIR" <<'PYDOCTOR'
import importlib.util, pathlib, sys
spec = importlib.util.spec_from_file_location("at", sys.argv[1])
at = importlib.util.module_from_spec(spec)
spec.loader.exec_module(at)
repo = pathlib.Path(sys.argv[2])
cache = pathlib.Path(sys.argv[3]) / "codex-core"
for rel in (
    ".codex-plugin/plugin.json", "skills/marker", "hooks/hooks.codex.json",
    "bin/at", "lib/at.py", "seed/AGENTS.md", "codex/agents/marker",
):
    path = cache / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("ok\n")
(cache / "bin/at").chmod(0o755)
at.shutil.which = lambda name: f"/fake/{name}"
at.cli_plugin_inventory = lambda harness: {
    "agents-core": {"enabled": True, "installed": True, "version": "1.2.0"}
}
at._run_json = lambda cmd: {"marketplaces": [{"name": "agents-template"}]}
at._plugin_root_from_record = lambda harness, plugin, record: cache
strict = at._runtime_findings(repo, "codex", strict=True)
assert not [item for item in strict if item[0] == "ERROR"], strict
(cache / "lib/at.py").unlink()
broken = at._runtime_findings(repo, "codex", strict=True)
assert any(level == "ERROR" and "lib/at.py" in message for level, message in broken)
repo_only = at._repo_doctor_findings(repo)
assert not any("Codex role files" in message for _, message in repo_only)
at.repo_root = lambda: repo
at._repo_doctor_findings = lambda candidate: [("OK", "repository only")]
at._runtime_findings = lambda *args, **kwargs: (_ for _ in ()).throw(
    AssertionError("plain doctor must not inspect a harness runtime")
)
plain = type("Args", (), {"all_harnesses": False, "claude": False, "codex": False})()
assert at.cmd_doctor(plain) == 0
parser = at.build_parser()
assert parser.parse_args(["doctor", "--codex"]).codex is True
try:
    parser.parse_args(["doctor", "--codex", "--claude"])
except SystemExit as exc:
    assert exc.code == 2
else:
    raise AssertionError("doctor harness selectors must be mutually exclusive")
PYDOCTOR
assert_eq "$?" "0" "strict doctor checks are isolated and detect incomplete Codex payloads"

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

# doctor collapses a ledger warning repeated across many tasks into one line
GROUPED="$(python3 - "$AT_PY" <<'GROUPING'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("at", sys.argv[1])
at = importlib.util.module_from_spec(spec)
spec.loader.exec_module(at)
lines = [f"task 'AB-00{n}-F_x.md' exceeds 400 lines" for n in range(1, 6)]
lines.insert(2, "archived task 'AB-009' in docs/tasks_manager/_todos_archived/AB-009-F_y.md is missing a Completion harvest section")
lines += [f"task 'AB-01{n}-F_z.md' execution log exceeds 200 lines (run: at ledger rotate-log AB-01{n}, or --all)" for n in range(3)]
print("\n".join(at._group_ledger_warnings(lines)))
GROUPING
)"
assert_eq "$(printf '%s\n' "$GROUPED" | wc -l | tr -d ' ')" "5" "doctor groups five same-kind ledger warnings into one line: $GROUPED"
assert_eq "$(printf '%s\n' "$GROUPED" | sed -n 1p)" \
  "5 × task '…' exceeds 400 lines (e.g. AB-001-F_x.md, AB-002-F_x.md, AB-003-F_x.md)" \
  "the grouped line carries the count and three examples"
assert_stdout_contains "$GROUPED" "archived task 'AB-009' in docs/tasks_manager/_todos_archived/AB-009-F_y.md" \
  "a one-off ledger warning prints unchanged"
assert_stdout_contains "$GROUPED" "task 'AB-012-F_z.md' execution log exceeds 200 lines (run: at ledger rotate-log AB-012, or --all)" \
  "a kind seen fewer than four times is not grouped"

# --- task wrappers (brief + run-state) ---------------------------------------
cp "$REPO/scripts/tests/fixtures/task-brief/docs/tasks_manager/_todos/TST-003-F_brief-source.md" docs/tasks_manager/_todos/
at task brief TST-003 --phase 2 >/dev/null 2>&1
assert_eq "$?" "0" "at task brief exits 0"
assert_exists docs/tasks_manager/_runs/TST-003/phase-2/brief.md "at task brief writes the phase brief"
assert_contains docs/tasks_manager/_runs/TST-003/phase-2/brief.md "#### Phase 2: Implementation" "brief carries the requested phase"
at task run-state init TST-003 --runtime claude >/dev/null 2>&1
assert_eq "$?" "0" "at task run-state init exits 0"
at task run-state check TST-003 >/dev/null 2>&1
assert_eq "$?" "0" "at task run-state check exits 0 on a fresh state"
at task >/dev/null 2>&1
assert_eq "$?" "2" "bare at task exits 2"
TASK_RUN_DRY="$(at task run TST-003 --harness claude --dry-run 2>&1)"
assert_eq "$?" "0" "at task run --dry-run exits 0: $TASK_RUN_DRY"
if printf '%s\n' "$TASK_RUN_DRY" | grep -q '\[dry-run\] phase 3'; then pass; else fail "at task run --dry-run lists every phase: $TASK_RUN_DRY"; fi
rm -rf docs/tasks_manager/_runs/TST-003 docs/tasks_manager/_todos/TST-003-F_brief-source.md
at ledger sync >/dev/null 2>&1

# --- at update --------------------------------------------------------------
FAKEHOME="$WORKDIR/fakehome"
mkdir -p "$FAKEHOME"
UPDATE_EMPTY="$(HOME="$FAKEHOME" at update --check 2>&1)"; UPDATE_EMPTY_RC=$?
assert_eq "$UPDATE_EMPTY_RC" "1" "at update --check exits 1 when nothing is installed"
assert_stdout_contains "$UPDATE_EMPTY" "at bootstrap" \
  "the no-plugins message points at at bootstrap"

mkdir -p "$FAKEHOME/.claude/plugins/cache/agents-template/agents-core/1.0.1"
mkdir -p "$FAKEHOME/.claude/plugins/cache/agents-template/agents-core/1.1.0"
mkdir -p "$FAKEHOME/.claude/plugins/cache/agents-template/agents-tasks/1.1.0"
UPDATE_CHECK="$(HOME="$FAKEHOME" at update --check 2>&1)"; UPDATE_CHECK_RC=$?
assert_eq "$UPDATE_CHECK_RC" "1" "a valid empty live inventory overrides stale cache entries"
assert_stdout_contains "$UPDATE_CHECK" "no agents-template plugins" \
  "stale caches are not reported as configured plugins"
assert_stdout_lacks "$UPDATE_CHECK" "$ claude" "--check runs no harness commands"

# Cache inventories stay separate and sort semantic versions numerically.
mkdir -p "$FAKEHOME/.codex/plugins/cache/agents-template/agents-core/1.9.0"
mkdir -p "$FAKEHOME/.codex/plugins/cache/agents-template/agents-core/1.10.0"
python3 - "$AT_PY" "$FAKEHOME" <<'PYUPDATE'
import importlib.util, pathlib, sys
spec = importlib.util.spec_from_file_location("at", sys.argv[1])
at = importlib.util.module_from_spec(spec)
spec.loader.exec_module(at)
inventory = at.installed_plugins(pathlib.Path(sys.argv[2]))
assert set(inventory) == {"claude", "codex"}
assert inventory["claude"]["agents-core"] == ["1.0.1", "1.1.0"]
assert inventory["codex"]["agents-core"] == ["1.9.0", "1.10.0"]
PYUPDATE
assert_eq "$?" "0" "installed plugin inventories stay separate and sort semantically"

# Live inventory distinguishes a valid empty result from a failed query, and
# an inventory record selects its own installed version instead of a newer stale cache.
python3 - "$AT_PY" "$FAKEHOME" <<'PYINVENTORY'
import importlib.util, pathlib, sys
spec = importlib.util.spec_from_file_location("at", sys.argv[1])
at = importlib.util.module_from_spec(spec)
spec.loader.exec_module(at)
home = pathlib.Path(sys.argv[2])
at._run_json = lambda cmd: [] if cmd[0] == "claude" else {"installed": []}
assert at.cli_plugin_inventory("claude") == {}
assert at.cli_plugin_inventory("codex") == {}
at._run_json = lambda cmd: None
assert at.cli_plugin_inventory("claude") is None
assert at.cli_plugin_inventory("codex") is None
active = home / ".codex/plugins/cache/agents-template/agents-core/1.2.0"
stale = home / ".codex/plugins/cache/agents-template/agents-core/9.9.0"
active.mkdir(parents=True, exist_ok=True)
stale.mkdir(parents=True, exist_ok=True)
root = at._plugin_root_from_record(
    "codex", "agents-core", {"version": "1.2.0"}, home,
)
assert root == active, (root, active)

# The selected core harness does not constrain where task wrappers are found.
cross_home = home / "cross-harness"
claude_core = cross_home / ".claude/plugins/cache/agents-template/agents-core/1.2.0"
codex_tasks = cross_home / ".codex/plugins/cache/agents-template/agents-tasks/1.2.0"
(claude_core / "skills").mkdir(parents=True)
(codex_tasks / "skills").mkdir(parents=True)
at.os.environ.pop("AT_TASKS_ROOT", None)
at.os.environ["HOME"] = str(cross_home)
at.core_root = lambda: claude_core
assert at.find_tasks_root() == codex_tasks
claude_tasks = cross_home / ".claude/plugins/cache/agents-template/agents-tasks/1.2.0"
(claude_tasks / "skills").mkdir(parents=True)
assert at.find_tasks_root() == claude_tasks

# A cache outside $HOME (CLAUDE_CONFIG_DIR / CODEX_HOME) is found next to the running core plugin.
elsewhere = home / "elsewhere" / "plugins" / "cache" / "agents-template"
moved_core = elsewhere / "agents-core" / "1.2.0"
(moved_core / "skills").mkdir(parents=True)
for version in ("1.2.0", "1.10.0"):
    (elsewhere / "agents-tasks" / version / "skills").mkdir(parents=True)
at.os.environ["HOME"] = str(home / "empty-home")
at.core_root = lambda: moved_core
assert at.find_tasks_root() == elsewhere / "agents-tasks" / "1.10.0"
PYINVENTORY
assert_eq "$?" "0" "live inventory and cross-harness task cache resolution are deterministic"

# Codex command planning is source- and capability-aware and never emits plugin update.
python3 - "$AT_PY" <<'PYCODEXPLAN'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("at", sys.argv[1])
at = importlib.util.module_from_spec(spec)
spec.loader.exec_module(at)
names = ["agents-core", "agents-tasks"]
local = at.codex_update_commands(names, "local", supports=lambda cmd: False)
assert local == [
    ["codex", "plugin", "add", "agents-core@agents-template"],
    ["codex", "plugin", "add", "agents-tasks@agents-template"],
]
modern = at.codex_update_commands(
    names, "git", supports=lambda cmd: cmd[-1] == "upgrade",
)
assert modern[0] == ["codex", "plugin", "marketplace", "upgrade", "agents-template"]
legacy = at.codex_update_commands(
    names, "git", supports=lambda cmd: cmd[-1] == "update",
)
assert legacy[0] == ["codex", "plugin", "marketplace", "update", "agents-template"]
assert all(command[2] != "update" for command in modern[1:])
try:
    at.codex_update_commands(names, "git", supports=lambda cmd: False)
except ValueError:
    pass
else:
    raise AssertionError("unsupported Codex command set must fail")
PYCODEXPLAN
assert_eq "$?" "0" "Codex update command plans cover local, modern Git and legacy Git"

python3 - "$AT_PY" <<'PYUPDATEFLOW'
import argparse, contextlib, importlib.util, io, sys
spec = importlib.util.spec_from_file_location("at", sys.argv[1])
at = importlib.util.module_from_spec(spec)
spec.loader.exec_module(at)

CAVEMAN_INSTALL = [
    ["claude", "plugin", "marketplace", "add", "JuliusBrussee/caveman"],
    ["claude", "plugin", "install", "caveman@caveman"],
]
CAVEMAN_REFRESH = [
    ["claude", "plugin", "marketplace", "update", "caveman"],
    ["claude", "plugin", "update", "caveman@caveman"],
]
CAVEMAN_CODEX = [["npx", "--yes", "skills@1", "add", "JuliusBrussee/caveman", "--skill", "caveman",
                  "-g", "-a", "codex", "-y"]]
assert at.companion_commands("claude") == CAVEMAN_INSTALL
assert at.companion_commands("claude", installed=True) == CAVEMAN_REFRESH
assert at.companion_commands("codex") == at.companion_commands("codex", installed=True) == CAVEMAN_CODEX

# claude_plugin_installed reads the live plugin list: user-scope rows count, project-scope rows do not.
at._run_json = lambda cmd: [{"id": "caveman@caveman", "scope": "user"}]
assert at.claude_plugin_installed("caveman@caveman") is True
at._run_json = lambda cmd: [{"id": "caveman@caveman"}]
assert at.claude_plugin_installed("caveman@caveman") is True
at._run_json = lambda cmd: [{"id": "caveman@caveman", "scope": "project", "projectPath": "/elsewhere"}]
assert at.claude_plugin_installed("caveman@caveman") is False
at._run_json = lambda cmd: []
assert at.claude_plugin_installed("caveman@caveman") is False
at._run_json = lambda cmd: None
assert at.claude_plugin_installed("caveman@caveman") is False

# A companion failure or missing npx is reported, never counted as a bootstrap/update failure.
at.shutil.which = lambda name: None if name == "npx" else f"/fake/{name}"
skipped_cmds = []
at._run = lambda command: skipped_cmds.append(command) or True
assert at._install_companions("codex") == "skipped" and skipped_cmds == []
at.shutil.which = lambda name: f"/fake/{name}"
at._run = lambda command: False
at.claude_plugin_installed = lambda plugin_id: False
assert at._install_companions("claude") == "failed"

def run_case(cached, reported, args, source_type=None, caveman_installed=False):
    commands = []
    at.installed_plugins = lambda: cached
    at.cli_plugin_inventory = lambda harness: reported.get(harness, {})
    at.shutil.which = lambda harness: f"/fake/{harness}"
    at._run = lambda command: commands.append(command) or True
    at._verify_codex_cache = lambda names: []
    at._command_supported = lambda command: command[-1] == "upgrade"
    at.codex_marketplace_source_type = lambda: source_type
    at.claude_plugin_installed = lambda plugin_id: caveman_installed
    rc = at.cmd_update(args)
    assert rc == 0
    return commands

# A failed live query falls back to cache state; a valid empty result does not.
at.installed_plugins = lambda: {
    "claude": {"agents-core": ["1.1.0"]}, "codex": {},
}
at.cli_plugin_inventory = lambda harness: None
at.shutil.which = lambda harness: f"/fake/{harness}"
assert at.cmd_update(argparse.Namespace(check=True, claude=False, codex=False)) == 0

# A successful live query is authoritative even when a newer stale cache exists.
at.installed_plugins = lambda: {
    "claude": {}, "codex": {"agents-core": ["1.2.0", "9.9.0"]},
}
at.cli_plugin_inventory = lambda harness: (
    {"agents-core": {"version": "1.2.0", "enabled": True}}
    if harness == "codex" else {}
)
display = io.StringIO()
with contextlib.redirect_stdout(display):
    display_rc = at.cmd_update(argparse.Namespace(check=True, claude=False, codex=False))
assert display_rc == 0
assert "agents-core      1.2.0  (also cached: 9.9.0)" in display.getvalue()

claude = run_case(
    {"claude": {"agents-core": ["1.2.0"]}, "codex": {}},
    {"claude": {"agents-core": {"version": "1.2.0", "enabled": True}}, "codex": {}},
    argparse.Namespace(check=False, claude=False, codex=False),
)
assert claude == [
    ["claude", "plugin", "marketplace", "update", "agents-template"],
    ["claude", "plugin", "update", "agents-core@agents-template"],
    *CAVEMAN_INSTALL,
]

# A machine bootstrapped before the companion existed gets it installed; one that has it gets a refresh.
claude_refresh = run_case(
    {"claude": {"agents-core": ["1.2.0"]}, "codex": {}},
    {"claude": {"agents-core": {"version": "1.2.0", "enabled": True}}, "codex": {}},
    argparse.Namespace(check=False, claude=False, codex=False),
    caveman_installed=True,
)
assert claude_refresh[2:] == CAVEMAN_REFRESH

codex = run_case(
    {"claude": {}, "codex": {"agents-core": ["1.2.0"]}},
    {"claude": {}, "codex": {"agents-core": {
        "version": "1.2.0", "enabled": True, "installed": True, "source_type": "local",
    }}},
    argparse.Namespace(check=False, claude=False, codex=False),
)
assert codex == [["codex", "plugin", "add", "agents-core@agents-template"], *CAVEMAN_CODEX]

mixed = run_case(
    {
        "claude": {"agents-core": ["1.2.0"]},
        "codex": {"agents-core": ["1.2.0"]},
    },
    {
        "claude": {"agents-core": {"version": "1.2.0", "enabled": True}},
        "codex": {"agents-core": {
            "version": "1.2.0", "enabled": True, "installed": True, "source_type": "local",
        }},
    },
    argparse.Namespace(check=False, claude=False, codex=False),
)
assert mixed == [
    ["claude", "plugin", "marketplace", "update", "agents-template"],
    ["claude", "plugin", "update", "agents-core@agents-template"],
    *CAVEMAN_INSTALL,
    ["codex", "plugin", "add", "agents-core@agents-template"],
    *CAVEMAN_CODEX,
]

# A successful empty live inventory suppresses stale cache fallback.
at.installed_plugins = lambda: {
    "claude": {}, "codex": {"agents-core": ["0.9.0"]},
}
at.cli_plugin_inventory = lambda harness: {}
at.shutil.which = lambda harness: f"/fake/{harness}"
commands = []
at._run = lambda command: commands.append(command) or True
empty_rc = at.cmd_update(argparse.Namespace(check=False, claude=False, codex=False))
assert empty_rc == 1
assert commands == []

# An explicitly requested unavailable harness fails without touching the other one.
at.installed_plugins = lambda: {
    "claude": {"agents-core": ["1.2.0"]}, "codex": {"agents-core": ["1.2.0"]},
}
at.shutil.which = lambda harness: "/fake/claude" if harness == "claude" else None
at.cli_plugin_inventory = lambda harness: {
    "agents-core": {"version": "1.2.0", "enabled": True}
}
commands = []
explicit_rc = at.cmd_update(argparse.Namespace(check=False, claude=False, codex=True))
assert explicit_rc == 1
assert commands == []
PYUPDATEFLOW
assert_eq "$?" "0" "update isolates harnesses, ignores stale caches, and preserves Claude commands"

# --- at doctor: routing-table drift -----------------------------------------
cp AGENTS.md "$WORKDIR/AGENTS.md.pre-drift"
DOCTOR_CURRENT="$(at doctor 2>&1)"
assert_stdout_contains "$DOCTOR_CURRENT" "routing table matches the plugin seed" \
  "at doctor confirms a freshly seeded routing table"
python3 - "$PROJECT/AGENTS.md" <<'PYDROP'
import sys, pathlib
p = pathlib.Path(sys.argv[1])
lines = p.read_text().splitlines(keepends=True)
seen = 0
out = []
for line in lines:
    if line.startswith("| Pausing or handing off"):
        seen += 1
        continue
    out.append(line)
assert seen == 1, f"expected one row to drop, dropped {seen}"
p.write_text("".join(out))
PYDROP
DOCTOR_DRIFT="$(at doctor 2>&1)"; DOCTOR_DRIFT_RC=$?
assert_eq "$DOCTOR_DRIFT_RC" "0" "routing drift is a warning, not a problem"
assert_stdout_contains "$DOCTOR_DRIFT" "routing table is 1 row(s) behind" \
  "at doctor counts the missing routing row"
assert_stdout_contains "$DOCTOR_DRIFT" "Pausing or handing off" \
  "at doctor names the missing routing row"
assert_stdout_contains "$DOCTOR_DRIFT" "setup-project" "the drift warning points at setup-project"
cp "$WORKDIR/AGENTS.md.pre-drift" AGENTS.md

# --- at doctor: removed skill ids -------------------------------------------
printf '| Stress-test with the user | `agents-core:grill-me` |\n' >> AGENTS.md
DOCTOR_REMOVED="$(at doctor 2>&1)"; DOCTOR_REMOVED_RC=$?
assert_eq "$DOCTOR_REMOVED_RC" "0" "a removed skill id is a warning, not a problem"
assert_stdout_contains "$DOCTOR_REMOVED" "routes to a removed skill: agents-core:grill-me" \
  "at doctor names the removed skill id"
assert_stdout_contains "$DOCTOR_REMOVED" "Removed skill ids" "the warning points at adopting-updates"
cp "$WORKDIR/AGENTS.md.pre-drift" AGENTS.md
assert_stdout_contains "$(at doctor 2>&1)" "routing table matches the plugin seed" \
  "a seeded AGENTS.md names no removed skill"

# --- verify-task: the criteria-drift recipe sees a changed criterion --------
DRIFT_TASK="docs/tasks_manager/_todos/T-900-F_drift-fixture.md"
mkdir -p "$(dirname "$DRIFT_TASK")"
printf '### Acceptance criteria\n\n- [ ] returns 200 on success\n' > "$DRIFT_TASK"
git add "$DRIFT_TASK" && git -c user.name=t -c user.email=t@t commit -q -m "T-900 criteria v1"
printf '### Acceptance criteria\n\n- [ ] returns 201 on success\n' > "$DRIFT_TASK"
git add "$DRIFT_TASK" && git -c user.name=t -c user.email=t@t commit -q -m "T-900 criteria v2"
printf '### Acceptance criteria\n\n- [x] returns 201 on success\n' > "$DRIFT_TASK"
git add "$DRIFT_TASK" && git -c user.name=t -c user.email=t@t commit -q -m "T-900 ticked"
DRIFT="$(for c in $(git log --follow --format=%h -- "$DRIFT_TASK"); do
  echo "== $c $(git log -1 --format=%s "$c")"
  git show "$c" -- "$DRIFT_TASK" | grep -E '^[-+]- \[[ x]\] ' | sed -E 's/^[-+]- \[[ x]\] //' | sort | uniq -u
done)"
assert_stdout_contains "$DRIFT" "returns 200 on success" "the drift recipe shows the removed criterion"
assert_stdout_contains "$DRIFT" "returns 201 on success" "the drift recipe shows the added criterion"
assert_stdout_contains "$DRIFT" "T-900 criteria v2" "the drift recipe names the commit that changed it"
TICK_BLOCK="$(printf '%s\n' "$DRIFT" | sed -n '/T-900 ticked/,/^== /p' | grep -v '^== ')"
assert_eq "$TICK_BLOCK" "" "a tick-only commit prints no drift"
git rm -q "$DRIFT_TASK" && git -c user.name=t -c user.email=t@t commit -q -m "T-900 fixture removed"

# --- at peer: read-only second opinion from the other CLI --------------------
# Fake `claude` / `codex` binaries on a PATH that hides the real ones; CLAUDECODE is set per call,
# so the result does not depend on whether this suite itself runs inside Claude Code.
PEER_REPO="$WORKDIR/peer-repo"; PEER_BIN="$WORKDIR/peer-bin"; PEER_CALLS="$WORKDIR/peer-calls.txt"
mkdir -p "$PEER_REPO" "$PEER_BIN"
git -C "$PEER_REPO" init -q .
for cli in claude codex; do
  cp "$REPO/scripts/tests/fixtures/fake-peer.py" "$PEER_BIN/$cli"; chmod +x "$PEER_BIN/$cli"
done
printf 'Stage: both. Review HEAD.\n' > "$WORKDIR/peer-brief.md"
PEER_PATH="$PEER_BIN:$REPO/plugins/agents-core/bin:/usr/bin:/bin"
peer() { # peer <CLAUDECODE value or ""> <scenario> <at peer args...>
  local marker="$1" scenario="$2"; shift 2
  ( cd "$PEER_REPO" && env -u CLAUDECODE -u AT_PEER_DEPTH ${marker:+CLAUDECODE=$marker} PATH="$PEER_PATH" \
      FAKE_PEER="$scenario" FAKE_PEER_CALLS="$PEER_CALLS" at peer "$@" 2>&1 )
}
PEER_OUT="$(peer 1 ok status)"; PEER_RC=$?
assert_eq "$PEER_RC" "3" "at peer status exits 3 before the checkout opts in"
assert_stdout_contains "$PEER_OUT" "not enabled for this checkout" "the reason says how to enable"
PEER_OUT="$(peer 1 ok run --role reviewer --brief "$WORKDIR/peer-brief.md" --out "$WORKDIR/peer-out/r.md")"; PEER_RC=$?
assert_eq "$PEER_RC" "3" "at peer run exits 3 when not enabled"
assert_missing "$PEER_CALLS" "no CLI is started when peer checks are off"
peer 1 ok enable gemini >/dev/null; assert_eq "$?" "2" "at peer enable rejects an unknown CLI"
PEER_OUT="$(peer 1 ok enable codex:gpt-test claude)"
assert_stdout_contains "$PEER_OUT" "sends the brief and the files the peer reads" "enable warns that code leaves to the provider"
assert_eq "$(git -C "$PEER_REPO" config --get agents.peers)" "codex:gpt-test claude" "enable writes local git config"
assert_eq "$(peer 1 ok status)" "peer: codex (model gpt-test, effort default)" "from Claude Code the peer is codex"
assert_eq "$(peer "" ok status --from codex)" "peer: claude (model default, effort default)" "from codex the peer is claude"
peer "" ok run --role reviewer --brief "$WORKDIR/peer-brief.md" --out "$WORKDIR/peer-out/r.md" >/dev/null
assert_eq "$?" "2" "at peer run needs --from when the caller is unknown"

PEER_OUT="$(peer 1 ok run --role reviewer --brief "$WORKDIR/peer-brief.md" --out "$WORKDIR/peer-out/r.md")"; PEER_RC=$?
assert_eq "$PEER_RC" "0" "a peer review that FAILs the code still exits 0: $PEER_OUT"
assert_stdout_contains "$PEER_OUT" "peer codex (reviewer): FAIL, 2 finding(s), 1 critical -> $WORKDIR/peer-out/r.md" \
  "the summary line counts each finding once"
assert_contains "$WORKDIR/peer-out/r.md" "Peer: codex (model gpt-test, effort default), role reviewer" "the saved reply names the peer and model"
assert_contains "$WORKDIR/peer-out/r.md" "## Verdict: FAIL" "the saved reply holds the peer's text"
assert_contains "$PEER_CALLS" "codex|depth=1|exec -C $PEER_REPO -s read-only" "codex runs in its read-only sandbox, marked as a peer"
assert_contains "$PEER_CALLS" "-m gpt-test" "the model from agents.peers is passed on"

: > "$PEER_CALLS"
PEER_OUT="$(peer "" critic run --from codex --role plan-critic --brief "$WORKDIR/peer-brief.md" --out "$WORKDIR/peer-out/c.md")"
assert_stdout_contains "$PEER_OUT" "peer claude (plan-critic): REVISE, 1 finding(s), 0 critical" "a plan verdict is reported as given"
assert_contains "$PEER_CALLS" "--disallowedTools Edit,Write,MultiEdit,NotebookEdit" "a claude peer has no edit tools"
assert_contains "$PEER_CALLS" "--allowedTools Bash(git show:*),Bash(git diff:*),Bash(git log:*),Bash(git status:*)" \
  "a claude peer may run read-only git only"

# The caller picks model and effort per call; agents.peers holds the defaults (<cli>:<model>:<effort>).
: > "$PEER_CALLS"
peer 1 ok run --model gpt-big --effort high --role reviewer --brief "$WORKDIR/peer-brief.md" --out "$WORKDIR/peer-out/m.md" >/dev/null
assert_contains "$PEER_CALLS" '-m gpt-big -c model_reasoning_effort="high"' "--model and --effort reach codex and outrank the setting"
assert_contains "$WORKDIR/peer-out/m.md" "Peer: codex (model gpt-big, effort high)" "the saved reply records the model and effort used"
peer "" ok run --from codex --model opus --effort xhigh --role reviewer --brief "$WORKDIR/peer-brief.md" --out "$WORKDIR/peer-out/m.md" >/dev/null
assert_contains "$PEER_CALLS" "--model opus --effort xhigh" "--model and --effort reach claude"
peer 1 ok enable codex::low claude:sonnet:medium >/dev/null
assert_eq "$(git -C "$PEER_REPO" config --get agents.peers)" "codex::low claude:sonnet:medium" "enable stores default model and effort per CLI"
assert_eq "$(peer 1 ok status)" "peer: codex (model default, effort low)" "an effort can be set without a model"
: > "$PEER_CALLS"
peer "" ok run --from codex --role reviewer --brief "$WORKDIR/peer-brief.md" --out "$WORKDIR/peer-out/m.md" >/dev/null
assert_contains "$PEER_CALLS" "--model sonnet --effort medium" "the stored defaults are used when the call names none"
peer 1 ok enable codex:gpt-test claude >/dev/null

: > "$PEER_CALLS"
PEER_OUT="$(peer 1 no-status run --role reviewer --brief "$WORKDIR/peer-brief.md" --out "$WORKDIR/peer-out/n.md")"
assert_eq "$(wc -l < "$PEER_CALLS" | tr -d ' ')" "2" "a reply without a status line is asked for once more"
assert_stdout_contains "$PEER_OUT" "FAIL, 2 finding(s)" "the reminded reply is the one reported"

PEER_OUT="$(peer 1 error run --role reviewer --brief "$WORKDIR/peer-brief.md" --out "$WORKDIR/peer-out/e.md")"; PEER_RC=$?
assert_eq "$PEER_RC" "3" "a CLI that exits non-zero is 'unavailable', not a failed review"
assert_stdout_contains "$PEER_OUT" "peer: unavailable (reviewer: codex exited 1: error: not logged in run the login command first)" \
  "the reason is one line and carries the CLI's own error"
assert_missing "$WORKDIR/peer-out/e.md" "no reply file is written for an unavailable peer"
peer 1 empty run --role reviewer --brief "$WORKDIR/peer-brief.md" --out "$WORKDIR/peer-out/e.md" >/dev/null
assert_eq "$?" "3" "an empty reply is 'unavailable'"
PEER_OUT="$(peer 1 hang run --timeout 1 --role reviewer --brief "$WORKDIR/peer-brief.md" --out "$WORKDIR/peer-out/e.md")"; PEER_RC=$?
assert_eq "$PEER_RC" "3" "a peer that does not answer in time is 'unavailable'"
assert_stdout_contains "$PEER_OUT" "no reply within 1s" "the timeout is named"

: > "$PEER_CALLS"
PEER_OUT="$(cd "$PEER_REPO" && AT_PEER_DEPTH=1 CLAUDECODE=1 PATH="$PEER_PATH" FAKE_PEER_CALLS="$PEER_CALLS" \
  at peer run --role reviewer --brief "$WORKDIR/peer-brief.md" --out "$WORKDIR/peer-out/d.md" 2>&1)"; PEER_RC=$?
assert_eq "$PEER_RC" "3" "a peer session cannot start a peer of its own"
assert_eq "$(wc -l < "$PEER_CALLS" | tr -d ' ')" "0" "and starts no CLI"

peer_doctor() { ( cd "$PEER_REPO" && PATH="$PEER_PATH" at doctor 2>&1 ); }
assert_stdout_contains "$(peer_doctor)" "peer check: codex is on PATH" "at doctor confirms a listed peer CLI"
rm "$PEER_BIN/codex"
PEER_DOCTOR="$(peer_doctor)"
if printf '%s\n' "$PEER_DOCTOR" | grep -qE '^WARN +peer check: agents\.peers lists codex, which is not on PATH'; then pass
else fail "at doctor warns about a listed peer CLI that is not installed: $PEER_DOCTOR"; fi
assert_stdout_contains "$(peer_doctor)" "peer check: claude is on PATH" "the other listed CLI is still reported ok"
PEER_OUT="$(peer 1 ok status)"; PEER_RC=$?
assert_eq "$PEER_RC" "3" "a listed CLI that is not installed is 'unavailable'"
assert_stdout_contains "$PEER_OUT" "codex is not on PATH" "the reason names the missing CLI"
peer 1 ok disable >/dev/null
assert_eq "$(git -C "$PEER_REPO" config --get agents.peers)" "" "disable removes the setting"
assert_stdout_lacks "$(peer_doctor)" "peer check" "at doctor says nothing about peers when the feature is off"
assert_eq "$(git -C "$PEER_REPO" status --porcelain | wc -l | tr -d ' ')" "0" "peer commands leave the working tree untouched"

# --- at addon: optional tools a repo switches on for itself -------------------
# Only files are written; `npx` and `codex` are empty stand-ins on a PATH that hides the real ones.
ADDON_REPO="$WORKDIR/addon-repo"; ADDON_BIN="$WORKDIR/addon-bin"
mkdir -p "$ADDON_REPO" "$ADDON_BIN"
git -C "$ADDON_REPO" init -q .
printf '#!/bin/sh\nexit 0\n' > "$ADDON_BIN/npx"; chmod +x "$ADDON_BIN/npx"
ADDON_PATH="$ADDON_BIN:$REPO/plugins/agents-core/bin:/usr/bin:/bin"
addon() { ( cd "$ADDON_REPO" && PATH="$ADDON_PATH" at addon "$@" 2>&1 ); }
addon_doctor() { ( cd "$ADDON_REPO" && PATH="$ADDON_PATH" at doctor 2>&1 ); }
mcp_args() { python3 -c "import json,sys;print(' '.join(json.load(open('$ADDON_REPO/.mcp.json'))['mcpServers'][sys.argv[1]]['args']))" "$1"; }

assert_stdout_contains "$(addon status)" "no add-on is enabled" "at addon status says so when nothing is enabled"
assert_stdout_lacks "$(addon_doctor)" "addon " "at doctor says nothing about add-ons when none is enabled"
addon enable figma >/dev/null; assert_eq "$?" "2" "at addon enable rejects an unknown add-on"
assert_missing "$ADDON_REPO/.mcp.json" "a rejected add-on writes nothing"

ADDON_OUT="$(addon enable browser)"; ADDON_RC=$?
assert_eq "$ADDON_RC" "0" "at addon enable browser succeeds: $ADDON_OUT"
case "$(mcp_args chrome-devtools)" in
  "-y chrome-devtools-mcp@"*" --no-usage-statistics --no-performance-crux") pass ;;
  *) fail "the browser server is pinned and has its statistics off (got '$(mcp_args chrome-devtools)')" ;;
esac
assert_contains "$ADDON_REPO/.claude/settings.json" '"agents-extras@agents-template": true' "enable switches on the UI skills plugin"
assert_stdout_contains "$ADDON_OUT" "codex is not on PATH; Codex registration skipped" "without codex the Codex step is skipped and said"
assert_missing "$ADDON_REPO/.codex/config.toml" "and no Codex config is written"
assert_stdout_contains "$(addon_doctor)" "addon browser: enabled" "at doctor reports an enabled add-on"
assert_stdout_contains "$(addon list)" "browser  enabled " "at addon list marks it enabled"
assert_stdout_contains "$(addon list)" "shadcn   disabled" "and the other one disabled"
ADDON_BEFORE="$(cat "$ADDON_REPO/.mcp.json" "$ADDON_REPO/.claude/settings.json")"
assert_stdout_contains "$(addon enable browser)" "browser: .mcp.json kept" "a second enable changes nothing"
assert_eq "$(cat "$ADDON_REPO/.mcp.json" "$ADDON_REPO/.claude/settings.json")" "$ADDON_BEFORE" "and leaves both files byte-identical"

# With Codex installed the same server goes into the checkout's git-ignored Codex config.
printf '#!/bin/sh\nexit 0\n' > "$ADDON_BIN/codex"; chmod +x "$ADDON_BIN/codex"
ADDON_DOCTOR="$(addon_doctor)"  # captured first: `grep -q` on a pipe trips pipefail
if printf '%s\n' "$ADDON_DOCTOR" | grep -qE '^WARN +addon browser: enabled, but not registered for Codex in this checkout; run: at addon enable browser'; then pass
else fail "at doctor tells a Codex user to register an add-on the repo enabled: $ADDON_DOCTOR"; fi
printf '[features]\nfoo = true\n' > "$ADDON_REPO/.codex-own"; mkdir -p "$ADDON_REPO/.codex"; mv "$ADDON_REPO/.codex-own" "$ADDON_REPO/.codex/config.toml"
assert_stdout_contains "$(addon enable browser)" ".codex/config.toml is not git-ignored here" "an unignored Codex config is flagged"
assert_contains "$ADDON_REPO/.codex/config.toml" "[mcp_servers.chrome-devtools]" "enable registers the server for Codex"
printf '.codex/*\n' > "$ADDON_REPO/.gitignore"
assert_stdout_lacks "$(addon enable browser)" "not git-ignored" "and not flagged once the repo ignores it"
assert_contains "$ADDON_REPO/.codex/config.toml" "foo = true" "and keeps what the Codex config already held"
assert_eq "$(python3 -c "import tomllib;d=tomllib.load(open('$ADDON_REPO/.codex/config.toml','rb'));print(d['mcp_servers']['chrome-devtools']['command'], d['features']['foo'])")" \
  "npx True" "the Codex config is still valid TOML"
addon enable browser >/dev/null
assert_eq "$(grep -c 'mcp_servers.chrome-devtools' "$ADDON_REPO/.codex/config.toml")" "1" "a repeated enable does not duplicate the Codex block"
ADDON_DOCTOR="$(addon_doctor)"
if printf '%s\n' "$ADDON_DOCTOR" | grep -qE '^OK +addon browser: enabled$'; then pass
else fail "at doctor is satisfied once Codex is registered: $ADDON_DOCTOR"; fi

ADDON_OUT="$(addon enable shadcn)"
assert_stdout_contains "$ADDON_OUT" "shadcn needs components.json" "shadcn warns when the repo has no components.json"
assert_stdout_contains "$(addon status)" "addon shadcn: enabled, but the repo has no components.json" "and status keeps saying so"
: > "$ADDON_REPO/components.json"
assert_stdout_contains "$(addon status)" "OK   addon shadcn: enabled" "with components.json shadcn is fine"

# An older pin of ours is moved to the current one; a server someone else defined is never touched.
python3 - "$ADDON_REPO/.mcp.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
data["mcpServers"]["shadcn"]["args"][1] = "shadcn@0.0.1"
data["mcpServers"]["other"] = {"command": "other-server"}
json.dump(data, open(sys.argv[1], "w"))
PY
assert_stdout_contains "$(addon enable shadcn)" "shadcn: .mcp.json updated to shadcn@" "an older pin is updated"
addon disable shadcn browser >/dev/null
assert_eq "$(python3 -c "import json;print(sorted(json.load(open('$ADDON_REPO/.mcp.json'))['mcpServers']))")" "['other']" \
  "disable removes our servers and keeps a foreign one"
assert_contains "$ADDON_REPO/.codex/config.toml" "foo = true" "disable keeps the rest of the Codex config"
assert_eq "$(grep -c 'mcp_servers' "$ADDON_REPO/.codex/config.toml")" "0" "and removes our Codex blocks"
python3 -c "import json;json.dump({'mcpServers': {'chrome-devtools': {'command': 'mine'}}}, open('$ADDON_REPO/.mcp.json','w'))"
ADDON_OUT="$(addon enable browser)"
assert_stdout_contains "$ADDON_OUT" "already defines a different \`chrome-devtools\` server" "a foreign server of the same name is reported"
assert_eq "$(python3 -c "import json;print(json.load(open('$ADDON_REPO/.mcp.json'))['mcpServers']['chrome-devtools']['command'])")" "mine" "and kept"
assert_stdout_contains "$(addon disable browser)" "was not written by at; kept" "disable does not remove it either"
rm "$ADDON_REPO/.mcp.json" "$ADDON_REPO/.codex/config.toml"
addon enable browser >/dev/null; addon disable browser >/dev/null
assert_missing "$ADDON_REPO/.mcp.json" "disabling the last add-on removes the .mcp.json at created"
assert_missing "$ADDON_REPO/.codex" "and the Codex config it created"
printf '{broken' > "$ADDON_REPO/.mcp.json"
ADDON_OUT="$(addon enable browser)"; ADDON_RC=$?
assert_eq "$ADDON_RC" "1" "an invalid .mcp.json stops enable"
assert_stdout_contains "$ADDON_OUT" "invalid JSON" "with a fix-by-hand message"
assert_eq "$(cat "$ADDON_REPO/.mcp.json")" "{broken" "and is left as it was"

# --- at version -------------------------------------------------------------
EXPECTED_VERSION="$(python3 -c "import json;print(json.load(open('$REPO/plugins/agents-core/.claude-plugin/plugin.json'))['version'])")"
assert_eq "$(at version 2>&1)" "$EXPECTED_VERSION" "at version prints the plugin version"
assert_eq "$(at seed-path 2>&1)" "$REPO/plugins/agents-core/seed/AGENTS.md" \
  "at seed-path prints the active agents-core seed"
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

# A newer Codex cache wins across harnesses; Claude wins an exact-version tie.
CODEX_AT="$FAKEHOME/.codex/plugins/cache/agents-template/agents-core/1.11.0/bin"
mkdir -p "$CODEX_AT"
printf '#!/usr/bin/env bash\necho "codex cache 1.11.0"\n' > "$CODEX_AT/at"
chmod +x "$CODEX_AT/at"
RESOLVED_CODEX="$(HOME="$FAKEHOME" AT_DEV_ROOT="" bash "$FAKEHOME/.local/bin/at" 2>&1)"
assert_eq "$RESOLVED_CODEX" "codex cache 1.11.0" "resolver considers the versioned Codex cache"
CLAUDE_TIE="$FAKEHOME/.claude/plugins/cache/agents-template/agents-core/1.11.0/bin"
mkdir -p "$CLAUDE_TIE"
printf '#!/usr/bin/env bash\necho "claude cache 1.11.0"\n' > "$CLAUDE_TIE/at"
chmod +x "$CLAUDE_TIE/at"
RESOLVED_TIE="$(HOME="$FAKEHOME" AT_DEV_ROOT="" bash "$FAKEHOME/.local/bin/at" 2>&1)"
assert_eq "$RESOLVED_TIE" "claude cache 1.11.0" "resolver keeps Claude as the equal-version tie-breaker"

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

# bootstrap installs the caveman companion for exactly the harnesses it sets up
BOOT_CMDS="$(HOME="$FAKEHOME" python3 - "$AT_PY" "$FAKEHOME" "$REPO" <<'PY'
import argparse, importlib.util, sys
spec = importlib.util.spec_from_file_location("at", sys.argv[1])
at = importlib.util.module_from_spec(spec)
spec.loader.exec_module(at)
at.claude_plugin_installed = lambda plugin_id: False
at.shutil.which = lambda name: f"/fake/{name}"
CODEX_CMD = "npx --yes skills@1 add JuliusBrussee/caveman --skill caveman -g -a codex -y"
def case(run=None, **flags):
    commands = []
    at._run = run or (lambda cmd: commands.append(" ".join(cmd)) or True)
    args = argparse.Namespace(local=sys.argv[3], tasks=False, extras=False, personal=False,
                              clean_global_skills=False, yes=False, **flags)
    rc = at.cmd_bootstrap(args)
    return rc, commands
rc, both = case(claude=False, codex=False)
assert rc == 0
assert "claude plugin marketplace add JuliusBrussee/caveman" in both
assert "claude plugin install caveman@caveman" in both
assert CODEX_CMD in both
assert both.index("claude plugin install caveman@caveman") > both.index("claude plugin install agents-core@agents-template")
rc, only_claude = case(claude=True, codex=False)
assert rc == 0 and "claude plugin install caveman@caveman" in only_claude
assert not any(cmd.startswith("npx") or cmd.startswith("codex") for cmd in only_claude)
rc, only_codex = case(claude=False, codex=True)
assert rc == 0 and CODEX_CMD in only_codex
assert not any(cmd.startswith("claude") for cmd in only_codex)
# a failing companion command does not fail bootstrap; a failing marketplace command still does
rc, _ = case(run=lambda cmd: "caveman" not in " ".join(cmd), claude=False, codex=False)
assert rc == 0, "companion failure must not fail bootstrap"
rc, _ = case(run=lambda cmd: "agents-core" not in " ".join(cmd), claude=True, codex=False)
assert rc == 1, "a failed agents-core install still fails bootstrap"
print("bootstrap-companions-ok")
PY
)"
assert_stdout_contains "$BOOT_CMDS" "bootstrap-companions-ok" \
  "at bootstrap installs the caveman companion per selected harness: $BOOT_CMDS"

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
#
# All four downstreams have since been migrated for real, so their default
# branch no longer has the legacy `_base/`/`playbooks/` tree. Each call site
# below pins `clone_legacy` to a specific historical commit/branch that still
# has the pre-migration shape this test needs. Those pinned refs are matched
# to these specific *_SRC paths — if you override an AT_TEST_*_SRC env var to
# point at a different repo, you'll need a different pinned ref too.
LIGHT_SRC="${AT_TEST_LIGHT_SRC:-/home/vi/work/vitalii/repos/models_playground}"
HEAVY_SRC="${AT_TEST_HEAVY_SRC:-/home/vi/work/ratio1/projects/project_r1_redmesh}"
FOREIGN_SRC="${AT_TEST_FOREIGN_SRC:-/home/vi/work/ratio1/projects/project_r1_edge_node}"
WRITING_SRC="${AT_TEST_WRITING_SRC:-/home/vi/work/vitalii/repos/project_technical_writing}"
LEDGER_SCRIPT="$REPO/plugins/agents-tasks/skills/task-ledger/scripts/sync_todo_ledgers.py"

# Pinned refs, resolved to full 40-char SHAs. LIGHT_REF and HEAVY_REF were
# originally pinned to backup branch names -- those backup branches are
# local-only (never pushed) and could be silently deleted by a routine
# `git branch -D`, so the branch name is kept only as a comment and the
# pin itself is the commit it resolved to.
LIGHT_REF="9249ccecc2a671d3d1c4aa259c228d59c373823e"     # was branch backup/pre-plugin-migration-20260819-134111
HEAVY_REF="c32011c672c4f7599d6fe08ec8a1a326ec62c6ab"     # was branch backup/pre-plugin-migration-20260818-230258
FOREIGN_REF="a3462ddab7bb58aa071bcdb077a6cb34f81e0ad0"
WRITING_REF="82039a9044f8e9e80604884425aa5310f701cef6"

clone_legacy() { # clone_legacy <src> <dst> [<ref>]
  GIT_LFS_SKIP_SMUDGE=1 git clone -q "$1" "$2" || return 1
  # Set up identity/remote/merge-driver before the optional checkout below,
  # so a failed pin (fatal, see below) never leaves behind a half-configured
  # clone that a later step could pick up and run against with the real
  # developer's global git identity instead of test@example.com.
  git -C "$2" config user.email "test@example.com"
  git -C "$2" config user.name "at test"
  # a clone has no `template` remote of its own; the real downstreams do
  git -C "$2" remote add template git@github.com:toderian/project_template.git
  git -C "$2" config merge.template-keep-local.driver "true"
  if [[ -n "${3:-}" ]]; then
    # `at migrate` refuses to run unless the current branch is a default
    # branch (master/main) — a plain `checkout <ref>` would either switch
    # onto a differently-named branch or leave a detached HEAD (branch name
    # "HEAD"), and either way migrate would abort on the branch precondition
    # before ever reaching the legacy-tree logic this test wants to exercise.
    # Reset the clone's own default branch (whatever `git clone` checked
    # out, matching the source's HEAD) to point at the pinned ref instead,
    # so the working tree ends up on the historical content while still
    # sitting on a branch migrate accepts.
    default_branch="$(git -C "$2" symbolic-ref --short HEAD)" || return 1
    # A plain `checkout <ref>` also DWIMs an unqualified branch name (with
    # no matching local branch) onto the matching `origin/<ref>` remote-
    # tracking branch; `checkout -B <name> <start-point>` does not apply
    # that same DWIM to its start-point, so resolve it explicitly — first
    # as given (a raw SHA already resolves), falling back to `origin/<ref>`
    # (a bare branch name, which `git clone` only fetched as a remote-
    # tracking branch, not a local one).
    start_point="$(git -C "$2" rev-parse -q --verify "$3^{commit}" 2>/dev/null \
      || git -C "$2" rev-parse -q --verify "origin/$3^{commit}" 2>/dev/null)" || {
      echo "FATAL: pinned ref '$3' not found in $1 — the fixture is stale, update the pin in test-at.sh" >&2
      return 1
    }
    GIT_LFS_SKIP_SMUDGE=1 git -C "$2" checkout -q -B "$default_branch" "$start_point" || {
      echo "FATAL: pinned ref '$3' not found in $1 — the fixture is stale, update the pin in test-at.sh" >&2
      return 1
    }
  fi
}

# --- light downstream (no task ledger) --------------------------------------
LIGHT="$WORKDIR/light"
if [[ -d "$LIGHT_SRC/.git" ]] && clone_legacy "$LIGHT_SRC" "$LIGHT" "$LIGHT_REF"; then
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
  assert_exists "$LIGHT/.caveman.json" "migrate seeds the local .caveman.json"
  assert_eq "$(git ls-files .caveman.json | wc -l | tr -d ' ')" "0" \
    "migrate --commit never stages the local .caveman.json"
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
  echo "SKIP: light downstream migration (no clone source, or pinned ref unavailable, at $LIGHT_SRC)"
fi

# --- at migrate --commit on a downstream that locally gitignores .claude/ ---
# A downstream's own `.gitignore` may ignore a path migrate itself manages
# (its own local convention, unrelated to the managed block) — `--commit`
# must still stage and commit that path; it is force-added on purpose.
GITIGNORED="$WORKDIR/light-gitignored-claude"
if [[ -d "$LIGHT_SRC/.git" ]] && clone_legacy "$LIGHT_SRC" "$GITIGNORED" "$LIGHT_REF"; then
  cd "$GITIGNORED" || exit 1
  printf '\n.claude/\n' >> .gitignore
  git add .gitignore
  git commit -qm "locally ignore .claude/ (simulates a downstream's own rule)"
  GI_OUT="$(at migrate --yes --commit 2>&1)"; GI_RC=$?
  assert_eq "$GI_RC" "0" \
    "migrate succeeds when the downstream's own .gitignore ignores .claude/: $GI_OUT"
  assert_stdout_contains "$(git show --name-only HEAD)" ".claude/settings.json" \
    "the migration commit includes .claude/settings.json even though it is locally gitignored
--- migrate output:
$GI_OUT
--- git show --stat HEAD:
$(git show --stat --format='%H %s' HEAD | head -20)
--- git status --porcelain:
$(git status --porcelain)"
else
  echo "SKIP: migrate with a locally gitignored .claude/ (no clone source, or pinned ref unavailable, at $LIGHT_SRC)"
fi

# --- at migrate --allow-untracked: untracked-only dirtiness -----------------
# Real targets carry untracked paths that must never be committed or removed
# (a multi-GB untracked attachments tree, a WIP task file mid-draft). `at
# migrate` must be usable there without stashing or committing them first.
UNTRACKED="$WORKDIR/light-untracked"
if [[ -d "$LIGHT_SRC/.git" ]] && clone_legacy "$LIGHT_SRC" "$UNTRACKED" "$LIGHT_REF"; then
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
  echo "SKIP: at migrate --allow-untracked (no clone source, or pinned ref unavailable, at $LIGHT_SRC)"
fi

# a tracked modification alongside --allow-untracked still refuses (only
# untracked-only dirtiness is exempt from the clean-tree precondition)
TRACKEDDIRTY="$WORKDIR/light-tracked-dirty"
if [[ -d "$LIGHT_SRC/.git" ]] && clone_legacy "$LIGHT_SRC" "$TRACKEDDIRTY" "$LIGHT_REF"; then
  cd "$TRACKEDDIRTY" || exit 1

  printf '\nlocal edit\n' >> README.md
  TRACKED_OUT="$(at migrate --allow-untracked --yes 2>&1)"; TRACKED_RC=$?
  assert_eq "$TRACKED_RC" "1" \
    "a tracked modification still refuses even with --allow-untracked"
  assert_stdout_contains "$TRACKED_OUT" "working tree" \
    "the refusal with a tracked modification names the dirty working tree"
  assert_exists "$TRACKEDDIRTY/_base" "the refused run changed nothing"
else
  echo "SKIP: at migrate --allow-untracked tracked-dirty refusal (no clone source, or pinned ref unavailable, at $LIGHT_SRC)"
fi

# --- heavy downstream (task ledger, LFS, project rules) ---------------------
HEAVY="$WORKDIR/heavy"
if [[ -d "$HEAVY_SRC/.git" ]] && clone_legacy "$HEAVY_SRC" "$HEAVY" "$HEAVY_REF"; then
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
  echo "SKIP: heavy downstream migration (no clone source, or pinned ref unavailable, at $HEAVY_SRC)"
fi

# --- downstream with foreign files under skills/ ----------------------------
FOREIGN="$WORKDIR/foreign"
if [[ -d "$FOREIGN_SRC/.git" ]] && clone_legacy "$FOREIGN_SRC" "$FOREIGN" "$FOREIGN_REF"; then
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
  echo "SKIP: foreign-file migration abort (no clone source, or pinned ref unavailable, at $FOREIGN_SRC)"
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
WRITING="$WORKDIR/writing"
if [[ -d "$WRITING_SRC/.git" ]] && clone_legacy "$WRITING_SRC" "$WRITING" "$WRITING_REF"; then
  cd "$WRITING" || exit 1
  WRITING_OUT="$(at migrate --dry-run 2>&1)"; WRITING_RC=$?
  assert_eq "$WRITING_RC" "1" "at migrate aborts on a downstream that authored its own playbook"
  assert_stdout_contains "$WRITING_OUT" "google-docs-refine" "the abort names the downstream's own skill"
  assert_eq "$(git status --porcelain | wc -l | tr -d ' ')" "0" "the aborted dry run leaves the tree clean"
else
  echo "SKIP: downstream-authored playbook abort (no clone source, or pinned ref unavailable, at $WRITING_SRC)"
fi

# --- summary ----------------------------------------------------------------
cd "$REPO" || exit 1
echo "test-at: ${PASS_COUNT} passed, ${FAIL_COUNT} failed"
[[ "$FAIL_COUNT" -eq 0 ]]
