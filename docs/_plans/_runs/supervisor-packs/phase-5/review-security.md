## Status: DONE
## Verdict: PASS (the phase diff adds no critical or important issue; finding 1 is older code)
## Findings: 4 (C: 0, I: 1, M: 3)
1. [I] plugins/agents-core/lib/sup.py:285-288 (`cmd_land` move loop, unchanged since 71bf02b) — a symlink left in `kept/<ID>` by a failed landing lets a second landing write through it: worker makes ignored link `a -> <owner dir>`, locks the worktree, landing moves the link and fails; worker replaces `a` with a real directory; the rerun moves its files into the owner directory. Needs a live worker between two landings; workers run as the owner (D20). Fix: require `realpath(dest.parent)` inside `kept`.
2. [M] sup.py:284-288 (older) — race between `ls-files` and `shutil.move`: a swapped parent directory makes landing move an outside file into `kept/<ID>`. Not reproduced.
3. [M] plugins/agents-core/lib/sup_state.py:171 — `git check-ignore -- body` reads pathspec magic (`:(top)shared`), the code uses the entry literally. Owner input, availability only. Fix: refuse a leading `:` or `--literal-pathspecs`.
4. [M] sup.py:279-283 with sup_state.py:171 — `local` is validated again at landing, after the commit: a landed `.gitignore` change stops every later landing at "rerun" until the owner repairs it. Fail closed, no loss.

Correctly handled (probed): traversal, absolute, backslash, control characters, `.local`, `.git`, option-like entries
after `--`, symlinked hub parent, symlinked worktree parent (refused), existing link elsewhere (refused, not followed),
landing moves links as links, `git worktree remove` unlinks without following, static prompt sentence.
