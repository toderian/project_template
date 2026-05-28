#!/usr/bin/env bash
#
# Custom merge driver used by setup-template-merge-rules.sh.
#
# For merges/cherry-picks from the `template` remote, apply the template
# ownership rule requested by .gitattributes. For ordinary project branch
# merges, fall back to Git's normal three-way file merge behavior.

set -uo pipefail

usage() {
  cat <<'EOF'
Usage: template-merge-driver.sh keep-local|keep-upstream <ancestor> <current> <other> [path]

This script is intended to be called by Git as a custom merge driver.
EOF
}

if [[ $# -lt 4 ]]; then
  usage >&2
  exit 2
fi

MODE="$1"
ANCESTOR="$2"
CURRENT="$3"
OTHER="$4"
PATHNAME="${5:-}"

case "${MODE}" in
  keep-local|keep-upstream) ;;
  *)
    printf 'unknown merge mode: %s\n' "${MODE}" >&2
    usage >&2
    exit 2
    ;;
esac

merge_heads() {
  local git_dir file

  git_dir="$(git rev-parse --git-dir 2>/dev/null)" || return 0
  for file in "${git_dir}/MERGE_HEAD" "${git_dir}/CHERRY_PICK_HEAD"; do
    [[ -f "${file}" ]] || continue
    while IFS= read -r head; do
      [[ -n "${head}" ]] && printf '%s\n' "${head}"
    done < "${file}"
  done
}

is_template_head() {
  local head="$1"
  local ref

  while IFS= read -r ref; do
    [[ -n "${ref}" ]] || continue
    if git merge-base --is-ancestor "${head}" "${ref}" 2>/dev/null; then
      return 0
    fi
  done < <(git for-each-ref --format='%(refname)' refs/remotes/template 2>/dev/null)

  return 1
}

is_template_env() {
  local name value action

  while IFS='=' read -r name value; do
    [[ "${name}" == GITHEAD_* ]] || continue
    case "${value}" in
      refs/remotes/template/*)
        return 0
        ;;
    esac
  done < <(env)

  action="${GIT_REFLOG_ACTION:-}"
  case "${action}" in
    *" refs/remotes/template/"*)
      return 0
      ;;
  esac

  return 1
}

is_template_merge() {
  local head

  if is_template_env; then
    return 0
  fi

  while IFS= read -r head; do
    if is_template_head "${head}"; then
      return 0
    fi
  done < <(merge_heads)

  return 1
}

if is_template_merge; then
  case "${MODE}" in
    keep-local)
      exit 0
      ;;
    keep-upstream)
      cp "${OTHER}" "${CURRENT}"
      exit $?
      ;;
  esac
fi

if [[ -n "${PATHNAME}" ]]; then
  git merge-file -L "current:${PATHNAME}" -L "base:${PATHNAME}" -L "other:${PATHNAME}" \
    "${CURRENT}" "${ANCESTOR}" "${OTHER}"
else
  git merge-file "${CURRENT}" "${ANCESTOR}" "${OTHER}"
fi
