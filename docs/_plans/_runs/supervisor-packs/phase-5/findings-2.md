# Phase 5, fix round 2 (orchestrator): from re-review-1-quality.md

F1, F2. Guard (b) replaced by a rule that needs no profile: before any commit `cmd_land` takes the paths the
   branch adds against the default branch (`git diff --diff-filter=A default...branch`) and refuses when the hub
   holds, untracked, something at that path, or a non-directory (or a link) at one of its parents. git overwrites
   what it ignores; this is the case that replaced a `local` directory. Tests: the committed link is refused with
   and without `--profile`; a branch that adds file `lab` where the hub has ignored `lab/results/` is refused;
   a branch that committed and then removed its link lands.
F3. The kept destination is refused when it is itself a symlink. Test added.
F4. `_link_local` reports a `check-ignore` status above 1 with git's line.
Merges: `current_profile` read once in `cmd_land`; `_link_local` reads the list with `check=False`.
