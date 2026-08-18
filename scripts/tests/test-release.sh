#!/usr/bin/env bash
#
# Test for scripts/release.sh.
#
# Copies the current working tree (tracked files only) into a throwaway git repo
# and releases there, so nothing in this checkout is touched. The copy uses the
# working tree rather than `git clone` on purpose: the pre-commit hook runs this
# suite before the commit exists, so HEAD would not yet contain the change.
#
# `--dry-run` must leave the copy untouched; the real run must bump all four
# plugin manifests, both generated marketplaces, tag v<version> and end clean.
# Set AT_RELEASE_TEST_FULL=0 to check only the dry run.
#
# Run from any cwd: bash scripts/tests/test-release.sh

set -uo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
NEW_VERSION="1.0.1"
FULL="${AT_RELEASE_TEST_FULL:-1}"

PASS_COUNT=0
FAIL_COUNT=0
pass() { PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { FAIL_COUNT=$((FAIL_COUNT + 1)); echo "FAIL: $*" >&2; }
assert_eq() { # assert_eq <actual> <expected> <desc>
  if [[ "$1" == "$2" ]]; then pass; else fail "$3 (got '$1', want '$2')"; fi
}

WORKDIR="$(mktemp -d)"
trap 'rm -rf "${WORKDIR}"' EXIT
COPY="$WORKDIR/r"
mkdir -p "$COPY"

# tracked + not-yet-tracked files, from the working tree, into a fresh single-commit repo
( cd "$REPO" && git ls-files -z -co --exclude-standard | tar --null -T - -cf - ) | ( cd "$COPY" && tar -xf - )
git -C "$COPY" init -q
git -C "$COPY" config user.email "test@example.com"
git -C "$COPY" config user.name "release test"
git -C "$COPY" add -A
git -C "$COPY" commit -qm "snapshot"

cd "$COPY" || exit 1
OLD_VERSION="$(python3 -c 'import json;print(json.load(open("plugins/agents-core/.claude-plugin/plugin.json"))["version"])')"

versions() { # every version string that must move together
  python3 - <<'PY'
import glob, json
out = []
for path in sorted(glob.glob("plugins/*/.claude-plugin/plugin.json")):
    out.append(json.load(open(path))["version"])
for path in (".claude-plugin/marketplace.json", ".agents/plugins/marketplace.json"):
    out += [p["version"] for p in json.load(open(path))["plugins"]]
print(" ".join(out))
PY
}

EXPECT_OLD="$(python3 -c "print(' '.join(['$OLD_VERSION'] * 12))")"
EXPECT_NEW="$(python3 -c "print(' '.join(['$NEW_VERSION'] * 12))")"
assert_eq "$(versions)" "$EXPECT_OLD" "the copy starts at $OLD_VERSION everywhere"

# --- guards -----------------------------------------------------------------
OUT="$(bash scripts/release.sh 1.0 --dry-run 2>&1)"; RC=$?
assert_eq "$RC" "2" "release rejects a non-semver version"
OUT="$(bash scripts/release.sh 2>&1)"; RC=$?
assert_eq "$RC" "2" "release without a version prints usage"
echo scratch > dirty.txt
OUT="$(bash scripts/release.sh "$NEW_VERSION" 2>&1)"; RC=$?
assert_eq "$RC" "1" "release refuses a dirty working tree"
rm -f dirty.txt

# --- dry run changes nothing ------------------------------------------------
DRY_OUT="$(AT_RELEASE_TEST=1 bash scripts/release.sh "$NEW_VERSION" --dry-run 2>&1)"; DRY_RC=$?
assert_eq "$DRY_RC" "0" "release --dry-run exits 0: $DRY_OUT"
if grep -q "would: set version to $NEW_VERSION" <<<"$DRY_OUT"; then pass; else fail "dry run names the version bump"; fi
if grep -q "dry run: nothing changed" <<<"$DRY_OUT"; then pass; else fail "dry run says it changed nothing"; fi
assert_eq "$(versions)" "$EXPECT_OLD" "dry run leaves every version at $OLD_VERSION"
assert_eq "$(git status --porcelain | wc -l | tr -d ' ')" "0" "dry run leaves the tree clean"
assert_eq "$(git tag -l | wc -l | tr -d ' ')" "0" "dry run creates no tag"

# --- the real thing ---------------------------------------------------------
if [[ "$FULL" != "0" ]]; then
  REAL_OUT="$(AT_RELEASE_TEST=1 bash scripts/release.sh "$NEW_VERSION" 2>&1)"; REAL_RC=$?
  assert_eq "$REAL_RC" "0" "release exits 0: $REAL_OUT"
  assert_eq "$(versions)" "$EXPECT_NEW" "all four manifests and both marketplaces show $NEW_VERSION"
  assert_eq "$(git tag -l "v$NEW_VERSION")" "v$NEW_VERSION" "the annotated tag exists"
  assert_eq "$(git cat-file -t "v$NEW_VERSION")" "tag" "the tag is annotated"
  assert_eq "$(git log -1 --format=%s)" "chore: release $NEW_VERSION" "the release commit is on top"
  assert_eq "$(git status --porcelain | wc -l | tr -d ' ')" "0" "the release leaves a clean tree"
  if grep -q "git push && git push --tags" <<<"$REAL_OUT"; then pass; else fail "release prints the push hint"; fi
  OUT="$(AT_RELEASE_TEST=1 bash scripts/release.sh "$NEW_VERSION" 2>&1)"; RC=$?
  assert_eq "$RC" "1" "release refuses an existing tag"

  # a failing suite must not leave a half-applied version bump behind
  sed -i '2i exit 1  # sabotage' scripts/tests/run-all.sh
  git commit -qam "sabotage the suite"
  OUT="$(AT_RELEASE_TEST=1 bash scripts/release.sh 1.0.2 2>&1)"; RC=$?
  assert_eq "$RC" "1" "release fails when the suite fails"
  assert_eq "$(versions)" "$EXPECT_NEW" "a failed release restores the manifests"
  assert_eq "$(git status --porcelain | wc -l | tr -d ' ')" "0" "a failed release leaves a clean tree"
  assert_eq "$(git tag -l v1.0.2)" "" "a failed release creates no tag"
else
  echo "SKIP: real release run (AT_RELEASE_TEST_FULL=0)"
fi

echo "test-release: $PASS_COUNT passed, $FAIL_COUNT failed"
[[ "$FAIL_COUNT" -eq 0 ]]
