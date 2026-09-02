#!/usr/bin/env bash
#
# Cut a release of agents-template: one version for all four plugins.
#
#   scripts/release.sh <X.Y.Z> [--dry-run]
#
# Sets "version" in every plugins/*/.claude-plugin/plugin.json, regenerates the
# derived files (codex manifests, both marketplaces), runs the test suite, then
# commits and creates the annotated tag v<X.Y.Z>. It never pushes.

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

VERSION=""
DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    -h|--help) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) echo "release: unknown option: $arg" >&2; exit 2 ;;
    *)
      if [[ -n "$VERSION" ]]; then echo "release: unexpected argument: $arg" >&2; exit 2; fi
      VERSION="$arg" ;;
  esac
done

if [[ -z "$VERSION" ]]; then
  echo "usage: scripts/release.sh <X.Y.Z> [--dry-run]" >&2
  exit 2
fi
if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "release: '$VERSION' is not a semver X.Y.Z version" >&2
  exit 2
fi

TAG="v$VERSION"
MANIFESTS=(plugins/*/.claude-plugin/plugin.json)
say() { if [[ "$DRY_RUN" == 1 ]]; then echo "would: $*"; else echo "==> $*"; fi }

if [[ -n "$(git status --porcelain)" ]]; then
  echo "release: working tree is not clean; commit or stash first" >&2
  exit 1
fi
if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
  echo "release: tag $TAG already exists" >&2
  exit 1
fi

CURRENT="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["version"])' "${MANIFESTS[0]}")"
echo "release: $CURRENT -> $VERSION (${#MANIFESTS[@]} plugins)"

# Between the version bump and the commit, a failure — build, tests, or the commit
# itself, which `git add -A` has already staged by then — would leave the bumped
# state behind. The tree was verified clean above, so restoring index and worktree
# from HEAD discards only our own edits. No untracked leftovers are possible:
# scripts/build.py writes a fixed set of targets (both marketplaces, and per plugin
# the .codex-plugin manifest, hooks.codex.json and codex/agents/*.toml), all of
# them already tracked, and a release edits nothing but the version key.
ROLLBACK=0
rollback_on_failure() {
  local rc=$?
  if [[ "$rc" != 0 && "$ROLLBACK" == 1 ]]; then
    echo "release: failed; restoring version $CURRENT" >&2
    git restore --source=HEAD --staged --worktree . || true
  fi
  return "$rc"
}
trap rollback_on_failure EXIT

say "set version to $VERSION in ${MANIFESTS[*]}"
if [[ "$DRY_RUN" == 0 ]]; then
  ROLLBACK=1
  python3 - "$VERSION" "${MANIFESTS[@]}" <<'PY'
import json, sys
version, paths = sys.argv[1], sys.argv[2:]
for path in paths:
    with open(path) as fh:
        data = json.load(fh)          # dicts preserve insertion order
    data["version"] = version
    with open(path, "w") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
PY
fi

say "python3 scripts/build.py"
if [[ "$DRY_RUN" == 0 ]]; then python3 scripts/build.py; fi

REQUIRE_CODEX_LIVE=1
EXPECT_CODEX_VERSION=0.152.1
if [[ -n "${AT_RELEASE_TEST:-}" ]]; then
  REQUIRE_CODEX_LIVE="${AT_REQUIRE_CODEX_LIVE:-0}"
  EXPECT_CODEX_VERSION="${AT_EXPECT_CODEX_VERSION:-}"
fi
say "AT_REQUIRE_CODEX_LIVE=$REQUIRE_CODEX_LIVE AT_EXPECT_CODEX_VERSION=${EXPECT_CODEX_VERSION:-none} bash scripts/tests/run-all.sh"
if [[ "$DRY_RUN" == 0 ]]; then
  AT_REQUIRE_CODEX_LIVE="$REQUIRE_CODEX_LIVE" \
    AT_EXPECT_CODEX_VERSION="$EXPECT_CODEX_VERSION" \
    bash scripts/tests/run-all.sh
fi

say "git commit -m 'chore: release $VERSION'"
if [[ "$DRY_RUN" == 0 ]]; then
  git add -A
  git commit -q -F - <<EOF
chore: release $VERSION

What changed: version $VERSION in all four plugin manifests, plus the generated
Codex manifests and both marketplace files.
Why: cut the $TAG release so downstream repos can pin and update to it.
Checks: python3 scripts/build.py; bash scripts/tests/run-all.sh.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
  ROLLBACK=0
fi

say "git tag -a $TAG -m 'agents-template $VERSION'"
if [[ "$DRY_RUN" == 0 ]]; then git tag -a "$TAG" -m "agents-template $VERSION"; fi

if [[ "$DRY_RUN" == 1 ]]; then
  echo "dry run: nothing changed"
else
  echo "released $VERSION; push with: git push && git push --tags"
fi
