#!/bin/bash

command -v jq >/dev/null || { echo "hook requires jq; install jq" >&2; exit 2; }

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command')
CWD=$(echo "$INPUT" | jq -r '.cwd // empty')
CWD=${CWD:-$PWD}

GIT_COMMAND_PREFIX='(^|[;&|[:space:]])["'"'"']?([^[:space:]"'"'"']*/)?git["'"'"']?([[:space:]]+(-C[[:space:]]+[^[:space:]]+|-c[[:space:]]+[^[:space:]]+|--git-dir(=|[[:space:]])[^[:space:]]+|--work-tree(=|[[:space:]])[^[:space:]]+|--[[:alnum:]-]+(=[^[:space:]]+)?))*[[:space:]]+'
CREDS_PATH_PATTERN='(^|[[:space:]"'"'"'])([^[:space:]"'"'"']*/)?\.creds([/\\]|[[:space:]"'"'"']|$)'
VENV_PATH_PATTERN='(^|[[:space:]"'"'"'])([^[:space:]"'"'"']*/)?\.venv([/\\]|[[:space:]"'"'"']|$)'
FORCE_ADD_PATTERN='(^|[[:space:]])(--force|-[^[:space:]]*f[^[:space:]]*)([[:space:]]|$)'
BROAD_ADD_PATTERN='(^|[[:space:]])(--[[:space:]]+)?(-A|--all|\.|\.\/|:\/)([[:space:]]|$)'
LOCAL_ONLY_STAGED_PATTERN='(^|/)(\.creds|\.venv)(/|$)'

if echo "$COMMAND" | grep -qE "${GIT_COMMAND_PREFIX}add([[:space:]]|$)"; then
  if echo "$COMMAND" | grep -qE "$CREDS_PATH_PATTERN"; then
    echo "BLOCKED: refused to stage .creds/ paths. Credentials must remain uncommitted." >&2
    exit 2
  fi
  if echo "$COMMAND" | grep -qE "$VENV_PATH_PATTERN"; then
    echo "BLOCKED: refused to stage .venv/ paths. Virtual environments must remain uncommitted." >&2
    exit 2
  fi
  if echo "$COMMAND" | grep -qE "$FORCE_ADD_PATTERN"; then
    echo "BLOCKED: refused to run forced git add. Forced staging can bypass .gitignore and commit local-only files." >&2
    exit 2
  fi
  if echo "$COMMAND" | grep -qE "$BROAD_ADD_PATTERN" && git ls-files | grep -qE "$LOCAL_ONLY_STAGED_PATTERN"; then
    echo "BLOCKED: refused broad git add while local-only .creds/ or .venv/ paths are tracked. Remove tracked local-only paths first." >&2
    exit 2
  fi
fi

# Reuse the boundary-anchored GIT_COMMAND_PREFIX (defined above, already used
# for the add/commit guards) instead of bare substrings, so quoted text (e.g.
# a commit message mentioning "git push") and dotfile arguments (e.g.
# `git checkout .gitignore`) don't false-positive on these patterns.
DANGEROUS_PATTERNS=(
  "${GIT_COMMAND_PREFIX}reset[[:space:]]+[^;&|]*--hard([[:space:]]|$)"
  "${GIT_COMMAND_PREFIX}clean[[:space:]]+-[a-zA-Z]*f[a-zA-Z]*([[:space:]]|$)"
  "${GIT_COMMAND_PREFIX}branch[[:space:]]+[^;&|]*-D([[:space:]]|$)"
  "${GIT_COMMAND_PREFIX}checkout([[:space:]]+--)?[[:space:]]+\.([[:space:]]|$)"
  "${GIT_COMMAND_PREFIX}restore([[:space:]]+--)?[[:space:]]+\.([[:space:]]|$)"
)

# Strip quoted spans before matching DANGEROUS_PATTERNS so free text inside
# quotes (e.g. a commit message like "Reminder to git push before EOD") can't
# false-positive. Tradeoff: a dangerous command hidden inside quotes (e.g.
# passed to `bash -c "..."`) is not caught — acceptable for an accident
# guardrail; this hook is not a security boundary. Only this matching uses the
# stripped text; the add/commit guards above/below inspect the full command.
STRIPPED_COMMAND=$(printf '%s' "$COMMAND" | sed -e 's/"[^"]*"//g' -e "s/'[^']*'//g")

# Push guard. A push to a feature branch is allowed. A force push is always
# refused. A push that reaches a protected branch (default main, master,
# develop; override with `git config agents.protectedBranches "main release/*"`)
# or whose target cannot be resolved is refused unless the command carries
# `-c agents.allowProtectedPush=<branch>`. The agent adds that marker only after
# the user confirms in chat (ask 1); the seed settings.json `ask` rule on the
# marker then forces a harness prompt, even in auto mode (ask 2).
PROTECTED_BRANCHES=$(git -C "$CWD" config --get agents.protectedBranches 2>/dev/null || echo "main master develop")
CONFIRM_KEY='agents.allowProtectedPush'

deny_push() {
  echo "BLOCKED: '$COMMAND': $1" >&2
  exit 2
}

is_protected() {
  local branch
  for branch in $PROTECTED_BRANCHES; do
    # shellcheck disable=SC2254 # unquoted on purpose: entries may be globs such as release/*
    case "$1" in $branch) return 0 ;; esac
  done
  return 1
}

require_confirmed() {
  local target="$1" confirmed="$2"
  is_protected "$target" || return 0
  [ "$confirmed" = "$target" ] && return 0
  deny_push "push to protected branch '$target'. Ask the user in chat first. Only after an explicit yes, rerun as 'git -c ${CONFIRM_KEY}=${target} push <remote> ${target}'; the user then confirms a second time in the permission prompt."
}

check_push_segment() {
  local -a tok
  read -ra tok <<< "$1"
  local n=${#tok[@]} i=0 dir="$CWD" confirmed="" tags_only="" arg dst
  local -a positional=()

  while [ "$i" -lt "$n" ]; do
    case "${tok[i]}" in git|*/git) break ;; esac
    i=$((i + 1))
  done
  i=$((i + 1))
  while [ "$i" -lt "$n" ] && [ "${tok[i]}" != push ]; do
    case "${tok[i]}" in
      -C) i=$((i + 1)); case "${tok[i]}" in /*) dir="${tok[i]}" ;; *) dir="$dir/${tok[i]}" ;; esac ;;
      -c) i=$((i + 1)); case "${tok[i]}" in "$CONFIRM_KEY"=*) confirmed="${tok[i]#*=}" ;; esac ;;
      --git-dir|--work-tree|--namespace) i=$((i + 1)) ;;
    esac
    i=$((i + 1))
  done
  [ "$i" -lt "$n" ] || return 0
  i=$((i + 1))

  while [ "$i" -lt "$n" ]; do
    arg="${tok[i]}"
    case "$arg" in
      --force*|+*) deny_push "force push is never allowed." ;;
      --all|--mirror|--branches) deny_push "'$arg' may reach a protected branch; push one named branch at a time." ;;
      --tags) tags_only=1 ;;
      -o|--push-option|--repo|--receive-pack|--exec) i=$((i + 1)) ;;
      --) ;;
      --*) ;;
      -*) case "$arg" in *f*) deny_push "force push is never allowed." ;; esac ;;
      *) positional+=("$arg") ;;
    esac
    i=$((i + 1))
  done

  if [ "${#positional[@]}" -le 1 ]; then
    [ -n "$tags_only" ] && return 0
    # No refspec: git picks the target from HEAD, upstream and push config.
    if echo "$COMMAND" | grep -qE '(^|[;&|[:space:]])(cd|pushd)[[:space:]]'; then
      deny_push "cannot resolve the push target after 'cd'; name it: 'git push <remote> <branch>'."
    fi
    local current upstream push_default
    current=$(git -C "$dir" symbolic-ref --quiet --short HEAD 2>/dev/null) \
      || deny_push "cannot resolve the current branch; name it: 'git push <remote> <branch>'."
    push_default=$(git -C "$dir" config --get push.default 2>/dev/null)
    if [ "$push_default" = matching ] || git -C "$dir" config --get-regexp '^remote\..*\.push$' >/dev/null 2>&1; then
      deny_push "push config may push several branches; name it: 'git push <remote> <branch>'."
    fi
    require_confirmed "$current" "$confirmed"
    upstream=$(git -C "$dir" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null) || upstream=""
    [ -n "$upstream" ] && require_confirmed "${upstream#*/}" "$confirmed"
    return 0
  fi

  for arg in "${positional[@]:1}"; do
    dst="${arg##*:}"
    [ -n "$dst" ] || deny_push "cannot resolve the destination of refspec '$arg'."
    if [ "$dst" = HEAD ]; then
      echo "$COMMAND" | grep -qE '(^|[;&|[:space:]])(cd|pushd)[[:space:]]' \
        && deny_push "cannot resolve HEAD after 'cd'; name the branch."
      dst=$(git -C "$dir" symbolic-ref --quiet --short HEAD 2>/dev/null) \
        || deny_push "cannot resolve HEAD; name the branch."
    fi
    case "$dst" in refs/tags/*) continue ;; esac
    dst="${dst#refs/heads/}"
    require_confirmed "$dst" "$confirmed"
  done
}

if echo "$STRIPPED_COMMAND" | grep -qE "${GIT_COMMAND_PREFIX}push([[:space:]]|$)"; then
  # Quote characters are dropped, not quoted spans, so `git push origin "main"`
  # still resolves to main.
  while IFS= read -r segment; do
    echo "$segment" | grep -qE "${GIT_COMMAND_PREFIX}push([[:space:]]|$)" || continue
    check_push_segment "$segment"
  done < <(printf '%s\n' "$COMMAND" | tr -d "\"'" | tr ';&|' '\n')
fi

for pattern in "${DANGEROUS_PATTERNS[@]}"; do
  if echo "$STRIPPED_COMMAND" | grep -qE "$pattern"; then
    echo "BLOCKED: '$COMMAND' matches dangerous pattern '$pattern'. The user has prevented you from doing this." >&2
    exit 2
  fi
done

if echo "$COMMAND" | grep -qE "${GIT_COMMAND_PREFIX}commit([[:space:]]|$)"; then
  if git diff --cached --name-only --diff-filter=ACMR | grep -qE "$LOCAL_ONLY_STAGED_PATTERN"; then
    echo "BLOCKED: refused to commit staged .creds/ or .venv/ paths. Local-only files must remain uncommitted." >&2
    exit 2
  fi
fi

exit 0
