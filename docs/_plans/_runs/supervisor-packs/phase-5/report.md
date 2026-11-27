# Phase 5: implementer's reply, condensed

## Test plan
- start-worker links, hub dir made for a `/` entry, missing file entry skipped and said, restart keeps links, real
  dir refuses and is named, link to elsewhere never followed, bad or unignored entry refuses:
  test_sup_workers.py test_start_worker_links_the_local_paths_and_refuses_what_is_in_the_way
- link goes at landing and hub content stays (real `git worktree remove`); a real file that replaced the link goes to
  `kept/<ID>`: test_sup_land.py test_a_linked_local_path_goes_with_the_worktree_and_a_real_file_in_its_place_is_kept
- init keeps `local`, refuses bad entries, a profile without the key loads as []: test_sup_tick.py
  test_init_keeps_local_and_refuses_a_bad_or_unignored_entry
- worker prompt sentence: existing prompt test.
Not tested: slash spelling of `git status --ignored`; the "outside the worktree" refusal of `_link_local`.

## Changes
- sup_state.py: `local_entries(entries, hub)` (the one validator, ValueError naming the entry), `profile_local(profile, hub)`.
- sup_tick.py: init validates and keeps `local`.
- sup_workers.py: `_link_local(profile, hub, cwd)` after `_write_map`; prompt: run the resource's script yourself
  once the lease is granted, then `at sup release <resource>`.
- sup.py: `kept_ignored(wt, linked=())` skips only a symlink whose realpath is a `local` hub path; land passes
  `linked`; close-pack passes none (pack worktrees get no links).
- supervise/SKILL.md +11 lines; assets/profile.json `"local": []`.

## Decision
git ignores `x/` only for directories, never for a symlink named `x`: the link showed as untracked and landing
refused. The validator checks the entry without its trailing `/`; the owner writes `shared`, not `shared/`, in
.gitignore. Refusal text and skill say so.

## Tests
workers 40 OK, land 48 OK, tick 24 OK, watch 37 OK, flow 4 OK, digest 18 OK, build.py --check ok.

## Open
A bad `local` list found at landing refuses after the commit is made ("rerun sup land"). Lib net 63 against 60.

## Status: DONE_WITH_CONCERNS

## Fix round 1 (from the implementer's reply)
1 guard (a): `_link_local` links only after `git -C <worktree> check-ignore -q` passes; guard (b): `cmd_land` reads
`local` (shape rules only) before the commit and refuses a branch that tracks a `local` entry (`git ls-tree -r`).
2 post-commit try/except removed. 3 retargeted link and dropped-entry link kept as links (test). 4 OSError ->
Refused. 5 outside-worktree refusal tested. 6 kept destination's real parent must be inside `kept/<ID>` (test).
7 validator refuses a leading `:` and a parent of another entry; git status other than 0/1 reported with git's
line. 8 malformed profile.json named. 9 skill sentence. 10 tick cases and prompt assertion. `rstrip("/")` removed
from `kept_ignored`.
Tests: workers 41 OK, land 51 OK, tick 24 OK, watch 37 OK, flow 4 OK, digest 18 OK, build.py --check ok.
Lib net 82 against 60.
