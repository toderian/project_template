#!/usr/bin/env bash
# End-to-end scenarios for unattended runs against the REAL Claude Code CLI.
#
#   bash scripts/tests/test-unattended-live.sh            # every scenario file
#   bash scripts/tests/test-unattended-live.sh E1 E3      # chosen scenarios
#
# Each scenario is scripts/tests/live/eN-<name>.sh and runs in its own scratch git repo with its own
# AGENTS_RUN_GUARD_DIR, on the cheapest model with a spend cap and a timeout (live/lib.sh). It
# spends tokens and needs the CLI, so it runs by hand only: not in run-all.sh, pre-commit or CI.
# A missing CLI is a failure, not a skip. A failing scenario keeps its scratch repo and prints it.
# Model runs are flaky: a failing scenario is tried again, LIVE_ATTEMPTS times in all (default 2),
# each attempt with its own scratch dir; a pass after a retry is reported as such. Ctrl-C or TERM
# stops the running session and the suite (exit 130).
# See docs/specs/2026-11-26-unattended-run-hardening-plan.md, "End-to-end tests".

set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
LIVE="${HERE}/live"

if [[ $# -eq 0 ]]; then
  set -- $(cd "${LIVE}" && ls e[0-9]*-*.sh 2>/dev/null | sed -E 's/^e([0-9]+)-.*/\1/' | sort -un | sed 's/^/E/')
fi
[[ $# -gt 0 ]] || { echo "FAIL: no scenario files in ${LIVE}" >&2; exit 1; }

command -v claude >/dev/null || { echo "FAIL: the claude CLI is not on PATH (a missing CLI is a failure)" >&2; exit 1; }
command -v jq >/dev/null || { echo "FAIL: jq is not on PATH" >&2; exit 1; }

ATTEMPTS="${LIVE_ATTEMPTS:-2}"
CHILD=""
trap '[[ -z "${CHILD}" ]] || kill -TERM "${CHILD}" 2>/dev/null; wait 2>/dev/null; echo "interrupted" >&2; exit 130' INT TERM

FAILED=()
for ID in "$@"; do
  N="${ID#[Ee]}"
  FILE=$(ls "${LIVE}"/e"${N}"-*.sh 2>/dev/null | head -1)
  if [[ -z "${FILE}" ]]; then
    echo "FAIL ${ID}: no scenario file live/e${N}-*.sh"
    FAILED+=("${ID}")
    continue
  fi
  echo "=== ${ID}: $(basename "${FILE}")"
  PASSED=""
  for ((A = 1; A <= ATTEMPTS; A++)); do
    rc=0
    bash "${FILE}" & CHILD=$!
    wait "${CHILD}" || rc=$?
    CHILD=""
    [[ ${rc} -ne 130 ]] || { echo "interrupted" >&2; exit 130; }
    if [[ ${rc} -eq 0 ]]; then PASSED=1; break; fi
    echo "attempt ${A} of ${ATTEMPTS} of ${ID} failed (exit ${rc})"
    [[ ${A} -ge ${ATTEMPTS} ]] || echo "retrying ${ID}: the model is not deterministic; the failed attempt's scratch dir is kept"
  done
  if [[ -n "${PASSED}" && ${A} -eq 1 ]]; then
    echo "PASS ${ID}"
  elif [[ -n "${PASSED}" ]]; then
    echo "PASS ${ID} (after a retry: attempt ${A} of ${ATTEMPTS}; see the failed attempt above)"
  else
    echo "FAIL ${ID}"
    FAILED+=("${ID}")
  fi
done

if [[ ${#FAILED[@]} -gt 0 ]]; then
  echo "test-unattended-live: FAILED: ${FAILED[*]}" >&2
  exit 1
fi
echo "test-unattended-live: ok ($*)"
