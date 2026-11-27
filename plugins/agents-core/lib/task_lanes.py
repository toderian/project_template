"""Parallel lanes for `at task run --lanes N`: wave planning, lane worktrees, the wave transaction, recovery.

A wave is the ready phases (every `After:` met) whose `Files:` lines (the phase's scope fence: comma-separated
repo-relative paths under the phase heading, every such line counts) do not overlap; a phase without a valid
`Files:` line never shares a wave. Each phase of a wave runs the ordinary phase loop (`Runner.phase`) through its
own `Runner` on its own worktree and branch, one process tree per lane. A lane commits its reviewed tree only;
everything the driver decides stays in the integration checkout, under the run lock the integration `Runner`
holds: the lane's `state.md` is a private copy, never read back from disk.

A wave is one transaction on the integration branch. Before the first merge `Note: wave K: base <sha>, phases
...` is saved. Lanes merge lowest phase first, each by the full SHA its Runner committed (its tree must be the
one its reviews saw and its only parent the base), then the `--check` commands run; a refused or conflicting merge
(aborted, never resolved) or a red check puts the branch back where it was and parks that lane. One `Stage: both`
review of base..HEAD follows. FAIL, or anything dirty outside the driver's own files, undoes the whole wave (every
merged lane parked, worktrees kept). PASS ticks the task file, syncs the ledgers, sets the rows `committed`, notes
`Note: wave K: done` and makes one bookkeeping commit of the driver's own paths; merged lanes are then removed.

At the start of every run `open_wave` stops a rerun after a kill mid-wave (the base note without its closing
line), and `leftovers` removes a lane an earlier run left only when it is clean and holds no commit of its own;
any other leftover is reported, its row parked, nothing deleted.

Python 3 stdlib only. Imported by lib/task_run.py; do not run directly.
"""
from __future__ import annotations

import os
import re
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import task_run
from task_run import RunError, State, sh

FILES_RE = re.compile(r"^\s*Files:\s*(.+?)\s*$", re.M)
PATH_RE = re.compile(r"\w[\w.\-]*(?:/[\w.\-]+)*")  # relative, no glob; `..` is refused below
ENTRY_RE = re.compile(r"(?:([a-z][a-z0-9-]*):)?(" + PATH_RE.pattern + ")")  # `path` in the task's own checkout, or `slug:path` in a sibling repo
WAVE_RE = re.compile(r"^Note: wave (\d+): (?:base ([0-9a-f]{40})|(done|undone)\b)")


def split_entry(entry: str) -> tuple:
    """(slug or None, path) of a `Files:` entry; (None, None) when it is not one."""
    m = ENTRY_RE.fullmatch(entry)
    return (m[1], m[2]) if m else (None, None)


def entry_ok(entry: str) -> bool:
    path = split_entry(entry)[1]
    return path is not None and not {".", ".."} & set(path.split("/"))


def fence(task, n: int) -> list[str] | None:
    """Phase `n`'s `Files:` entries (every such line; `slug:path` is kept as written), or None when there is none or any entry is not a plain relative path."""
    items = [x.strip().strip("`").rstrip("/") for m in FILES_RE.findall("\n".join(task.phases[n - 1].body)) for x in m.split(",")]
    ok = items and all(entry_ok(i) for i in items)
    return items if ok else None


def inside(path: str, paths: list[str]) -> bool:
    return any(path == p or path.startswith(p + "/") for p in paths)


def overlap(a: list[str], b: list[str]) -> bool:
    return any(inside(x, b) or inside(y, a) for x in a for y in b)


def plan_wave(task, ready: list[int], lanes: int) -> list[int]:
    """`ready[0]` plus, while there is room, each later ready phase whose fence overlaps none already in."""
    wave, taken = [ready[0]], [fence(task, ready[0])]
    if taken[0] is None:
        return wave
    for n in ready[1:]:
        if len(wave) < lanes and (f := fence(task, n)) and not any(overlap(f, t) for t in taken):
            wave.append(n)
            taken.append(f)
    return wave


def planned_waves(r, state: State, todo: list[int]) -> list[str]:
    """--dry-run: the waves the run would plan if every phase committed."""
    done = {n for n in range(1, len(state.rows) + 1) if state.row(n)[1] in r.done_rows}
    pending, out, k = list(todo), [], next_wave(state)
    while ready := [n for n in pending if r.args.phase or set(task_run.phase_deps(r.task, n)) <= done]:
        wave = plan_wave(r.task, ready, r.lanes)
        out.append(f"wave {k}: phases {', '.join(map(str, wave))} in lanes" if len(wave) > 1 else f"phase {wave[0]}: serial")
        k += len(wave) > 1
        done |= set(wave)
        pending = [n for n in pending if n not in wave]
    return out


def lane_names(r, n: int) -> tuple[Path, str]:
    """Worktree beside the repository and branch, from the validated task id and the phase number only."""
    tid = r.task.taskid
    if not re.fullmatch(r"[A-Z][A-Z0-9]*-\d+", tid):
        raise RunError(f"{tid!r} is not a task id")
    return r.repo.parent / f"{r.repo.name}-lane-{tid}-p{n}", f"at-lane/{tid}-p{n}"


# ---- recovery at the start of every run -------------------------------------------------------

def waves(state: State) -> dict[int, list]:
    """K -> [base sha, closed] from the `Note: wave K:` lines."""
    out: dict[int, list] = {}
    for line in state.ledger:
        if m := WAVE_RE.match(line):
            w = out.setdefault(int(m.group(1)), ["", False])
            w[0], w[1] = m.group(2) or w[0], w[1] or bool(m.group(3))
    return out


def next_wave(state: State) -> int:
    return 1 + max((k for k, (_, closed) in waves(state).items() if closed), default=0)


def open_wave(r, state: State) -> str:
    """A wave whose base note has no closing line was cut short: the recovery is by hand, nothing runs ('' when none)."""
    for k, (base, closed) in waves(state).items():
        if base and not closed:
            head = r.git("rev-parse", "HEAD").stdout.strip()
            where = "HEAD is still at it" if head == base else f"HEAD {head[:12]} is past it"
            return (f"wave {k} of {r.task.taskid} did not finish (was the driver stopped?): its base is {base}, {where}. "
                    f"Nothing was dispatched or reset. Recover with `git reset --hard {base}` (it also drops the wave's "
                    f"uncommitted notes from state.md), then rerun: lanes left with work are reported, never re-implemented.")
    return ""


def leftovers(r, state: State, todo: list[int]) -> set[int]:
    """Lane worktrees and branches of this task an earlier run left. Clean and holding no commit of its own (its branch tip
    is on the integration branch's first-parent line; a merged lane commit is not): removed, the phase runs as usual.
    Anything else: kept and reported, its row parked; the phase is not run. (Anything else at a lane path makes
    `git worktree add` fail, which parks that lane.)"""
    tid = r.task.taskid
    r.git("worktree", "prune")
    trees = {os.path.realpath(l[9:]) for l in r.git("worktree", "list", "--porcelain").stdout.splitlines() if l.startswith("worktree ")}
    refs = r.git("for-each-ref", "--format=%(refname)", f"refs/heads/at-lane/{tid}-p*").stdout
    nums = {int(x) for x in re.findall(rf"^refs/heads/at-lane/{re.escape(tid)}-p(\d+)$", refs, re.M)}
    nums = {n for n in range(1, len(state.rows) + 1) if n in nums or os.path.realpath(lane_names(r, n)[0]) in trees}
    line = set(r.git("rev-list", "--first-parent", "HEAD").stdout.split()) if nums else set()
    held = set()
    for n in sorted(nums):
        path, branch = lane_names(r, n)
        registered = os.path.realpath(path) in trees
        tip = r.git("rev-parse", "-q", "--verify", f"refs/heads/{branch}").stdout.strip()
        merged = state.row(n)[1] == "committed" and r.git("merge-base", "--is-ancestor", tip, "HEAD").returncode == 0
        empty = not (registered and r.dirty(path)) and (not tip or tip in line or merged)  # merged: killed before its removal
        if empty and (not registered or r.git("worktree", "remove", "--force", str(path)).returncode == 0) \
                and (not tip or r.git("branch", "-D", branch).returncode == 0):
            r.say(f"phase {n}: removed an empty lane an earlier run left ({path})")
            continue
        held.add(n)
        r.say(f"phase {n}: an earlier lane holds work in {path} (branch {branch}); kept, the phase is not run")
        if n in todo:
            if state.row(n)[1] not in ("blocked", "parked"):
                state.set(n, status="parked")
            note = (f"Note: parked phase {n}: an earlier lane holds work in {path} (branch {branch}); merge or remove it "
                    f"by hand, then set the row to pending")
            if note not in state.ledger:
                state.note(note)
    state.save()
    return held


# ---- one wave ---------------------------------------------------------------------------------

last_line = task_run.last_output_line


def lane_job(lr, ls: State, n: int) -> bool:
    try:
        return lr.phase(ls, n)
    except Exception as exc:  # DispatchError, RunError or a bug: this lane fails, the others go on
        if ls.row(n)[1] != "blocked":
            ls.set(n, status="blocked")
        ls.note(f"Phase {n}: lane aborted — {str(exc)[:300]}")
        ls.save()
        return False


def untracked(r) -> set[str]:
    """Untracked, non-ignored paths outside the run directory."""
    return set(filter(None, r.git("ls-files", "-z", "--others", "--exclude-standard", "--", ".", f":(exclude){r.runs_rel}").stdout.split("\0")))


def undo(r, sha: str, before: set[str]) -> None:
    """Back to `sha` outside the run directory, which is the driver's own record (state.md is saved from memory
    after this; lane reports stay). Tracked files return to `sha`; untracked paths not in `before` (what the merges
    added, what a check created) are removed."""
    keep = f":(exclude){r.runs_rel}"
    r.git("reset", "-q", sha)
    r.git("checkout", "-q", sha, "--", ".", keep)
    for p in untracked(r) - before:
        f = r.repo / p.rstrip("/")              # a nested repository is listed as one directory entry
        shutil.rmtree(f) if f.is_dir() and not f.is_symlink() else f.unlink(missing_ok=True)
    if r.git("rev-parse", "HEAD").stdout.strip() != sha or r.git("diff", "--quiet", sha, "--", ".", keep).returncode:
        raise RunError(f"could not put the integration branch back to {sha}; inspect the repository")


def verify(r, lr, base: str) -> str:
    """Why the lane's commit must not be merged ('' when it may). Its tree must be the one the lane's last review saw
    and its only parent the base: a commit put in its place can then differ in its message only."""
    if not (sha := lr.commit_sha):
        return "did not finish"
    if r.git("rev-parse", f"{sha}^{{tree}}").stdout.strip() != lr.reviewed_tree:
        return f"the commit {sha[:12]} does not hold the tree its reviews saw"
    if r.git("rev-list", "--parents", "-n", "1", sha).stdout.split()[1:] != [base]:
        return f"the driver's commit {sha[:12]} does not sit directly on the wave base"
    return ""


def merge(r, n: int, sha: str) -> str:
    """Merge the lane's commit; '' when it landed and the checks are green, else why not (HEAD is back where it was)."""
    pre, before = r.git("rev-parse", "HEAD").stdout.strip(), untracked(r)
    title = r.tb.phase_title(r.task.phases[n - 1])
    proc = r.git("merge", "--no-ff", "-q", "-m", f"merge: {r.task.taskid} phase {n} lane — {title}", sha)
    if proc.returncode != 0:
        conflict = r.git("rev-parse", "-q", "--verify", "MERGE_HEAD").returncode == 0
        if conflict:
            r.git("merge", "--abort")  # the driver never resolves a conflict
        undo(r, pre, before)
        return "its merge conflicts (merge aborted)" if conflict else f"merge refused: {last_line(proc)}"
    for cmd in r.args.check:
        if sh(["bash", "-lc", cmd], r.repo).returncode != 0:
            undo(r, pre, before)
            return f"check failed after its merge (merge undone): {cmd}"
    return ""


def wave_prompt(r, k: int, phases: list[int], base: str, parked: list[int], outside: dict[int, list[str]]) -> str:
    runs = r.runs_rel
    briefs = ", ".join(f"{runs}/phase-{n}/brief.md" for n in phases)
    fences = "; ".join(f"phase {n}: Files: {', '.join(fence(r.task, n))}"
                       + (f" (changed outside it: {', '.join(outside[n][:10])})" if outside[n] else "") for n in phases)
    skipped = (f"Phases {', '.join(map(str, parked))} of the wave were not merged (parked, reported in state.md): "
               "they are outside this review and are not a finding.\n") if parked else ""
    return (f"Stage: both\nReview the integrated result of phases {', '.join(map(str, phases))}, which ran in parallel lanes "
            f"and were merged.\n{skipped}Briefs: {briefs} — judge each phase by its own checklist under '## This phase' "
            "(met / not met, one line each), then the quality of the whole diff, above all where the phases meet.\n"
            f"Scope fences: {fences}. A path a phase changed outside its fence is a finding unless its brief needs it.\n"
            f"Diff: {runs}/wave-{k}/diff.patch (BASE {base} → merged HEAD)\nScope fence: read-only; do not edit files.\n"
            f"Your reply is the report (saved to {runs}/wave-{k}/review.md): the ## Status / ## Verdict / ## Findings block "
            "first, each finding as a numbered line '[C|I|M] path:line — one line', then ## Evidence; at most 40 lines.")


def run_wave(r, state: State, wave: list[int]) -> bool:
    """Run `wave` in lanes and integrate it as one transaction. False only when the wave committed and the
    post-phase checks then failed (stop the run); every other outcome is in the rows."""
    r.require_clean_tree()
    r.commit_run_dir(f"chore: {r.task.taskid} run state")  # the base holds the state: `git reset --hard <base>` loses nothing earlier
    base = r.git("rev-parse", "HEAD").stdout.strip()
    k = next_wave(state)
    log_at = {}  # phase -> size of the lane's driver.log as checked out (the committed copy)
    lanes = []  # (n, path, branch, lane runner, lane state, notes already in its state)
    for n in wave:
        path, branch = lane_names(r, n)
        proc = r.git("worktree", "add", "-q", "-b", branch, str(path), base)
        if proc.returncode != 0:
            r.park(state, n, f"its lane could not be created at {path}: {last_line(proc)}")
            r.say(f"phase {n}: lane not created: {last_line(proc)}")
            continue
        state.set(n, status="implementing", commit="—")
        state.note(f"Note: lane phase {n}: worktree {path}, branch {branch}")
        state.save(current_phase=str(wave[0]))
        lr = type(r)(r.args, path, r.core_root, r.tasks_scripts)
        lr.lane, lr.mode = branch, r.mode
        shutil.copyfile(state.path, lr.runs / "state.md")
        ls = State(lr.runs / "state.md")
        log_at[n] = (lr.runs / "driver.log").stat().st_size if (lr.runs / "driver.log").exists() else 0
        lanes.append((n, path, branch, lr, ls, len(ls.ledger)))
    r.say(f"wave {k}: phases {', '.join(str(l[0]) for l in lanes) or 'none'} in lanes")
    done = []
    if lanes:
        with ThreadPoolExecutor(max_workers=len(lanes)) as pool:
            done = [f.result() for f in [pool.submit(lane_job, lr, ls, n) for n, _, _, lr, ls, _ in lanes]]
    opened, merged = f"Note: wave {k}: base {base}, phases {', '.join(map(str, wave))}", {}
    for (n, path, branch, lr, ls, seen), ok in zip(lanes, done):
        if (src := lr.runs / f"phase-{n}").exists():
            shutil.copytree(src, r.runs / f"phase-{n}", dirs_exist_ok=True, symlinks=True)  # a link an implementer planted stays a link
        if (log := lr.runs / "driver.log").exists():
            with r.harness.log.open("a", encoding="utf-8") as fh:
                fh.write(f"\n### lane phase {n}\n" + log.read_bytes()[log_at[n]:].decode("utf-8", "replace"))  # only what the lane added to the committed copy
        r.harness.cost_usd += lr.harness.cost_usd
        state.ledger += ls.ledger[seen:]
        state.rows[n - 1] = list(ls.row(n))
        why = verify(r, lr, base) if ok and ls.row(n)[1] == "committed" else "did not finish"
        if not why:
            if opened not in state.ledger:
                state.note(opened)
                state.save()
            why = merge(r, n, lr.commit_sha)
        if why:
            r.park(state, n, f"lane {why}; work kept in {path} (branch {branch})")
            state.set(n, commit="—")
            r.say(f"phase {n}: lane {why}; worktree kept")
            continue
        merged[n] = (r.git("rev-parse", "HEAD").stdout.strip(), path, branch, lr)
        state.set(n, status="reviewing", commit="—")  # committed only when the wave passes
        r.say(f"phase {n}: lane merged, wave review pending")
    if not merged:
        if opened in state.ledger:
            state.ledger.remove(opened)  # nothing merged: the wave number is not used
        state.save()
        return True
    state.save()
    why = review(r, state, k, base, wave, merged)
    if not why and (stray := [l[3:] for l in r.dirty()]):
        (r.runs / f"wave-{k}" / "stray.patch").write_text(r.git("diff", "HEAD", "--", *stray).stdout, encoding="utf-8")
        why = (f"paths changed in the integration checkout outside every lane: {', '.join(stray[:10])}; edits to tracked "
               f"files saved to {r.runs_rel}/wave-{k}/stray.patch, untracked files left in place, uncommitted")
    if why:
        undo(r, base, untracked(r))
        for n, (_, path, branch, _) in merged.items():
            r.park(state, n, f"wave {k} was undone ({why}); work kept in {path} (branch {branch})")
        state.note(f"Note: wave {k}: undone — {why}; nothing of it stays on the integration branch, its lanes are kept")
        state.save()
        r.say(f"wave {k}: undone ({why})")
        return True
    state.save()
    before = state.path.read_text(encoding="utf-8")
    for n, (_, _, _, lr) in merged.items():
        task_run.tick_phase(r.task.path, n, lr.lane_entry)
    r.sync_ledgers()
    for n, (sha, _, branch, _) in merged.items():
        state.set(n, status="committed", commit=sha[:7])
        state.note(f"Phase {n}: lane merged ({sha[:7]}, branch {branch})")
    state.note(f"Note: wave {k}: done")  # inside the bookkeeping commit: a kill before it leaves the wave open
    state.save()
    r.git("add", "--", *(paths := r.bookkeeping_paths()))
    proc = r.git("commit", "-q", "-m", f"chore: {r.task.taskid} wave {k} — phases {', '.join(map(str, wave))}\n\n"
                 f"Merged: {', '.join(map(str, merged))}. Bookkeeping of the wave: task file, ledgers, run state.")
    if proc.returncode != 0:  # the wave stays open: state.md as before the done lines, nothing left staged
        state.path.write_text(before, encoding="utf-8")
        state.__init__(state.path)
        r.git("reset", "-q", "--", *paths)
        raise RunError(f"commit `chore: {r.task.taskid} wave {k}` failed: {last_line(proc)}")
    for n, (_, path, branch, _) in merged.items():
        if r.git("worktree", "remove", "--force", str(path)).returncode or r.git("branch", "-d", branch).returncode:
            r.say(f"phase {n}: merged, but lane {path} (branch {branch}) could not be removed; the next run reports it")
    return r.post_phase_checks(state, min(merged))


def review(r, state: State, k: int, base: str, wave: list[int], merged: dict) -> str:
    """The one `Stage: both` review of base..HEAD; '' on PASS without a critical finding, else why the wave is undone."""
    d = r.runs / f"wave-{k}"
    d.mkdir(exist_ok=True)
    (d / "diff.patch").write_text(r.git("diff", base, "HEAD", "--", ".", f":(exclude){r.runs_rel}").stdout, encoding="utf-8")
    outside = {n: [p for p in r.git("diff", "--name-only", base, lr.commit_sha).stdout.split() if not inside(p, fence(r.task, n))]
               for n, (_, _, _, lr) in merged.items()}
    phases = list(merged)
    try:
        reply, _ = r.dispatch("reviewer", wave_prompt(r, k, phases, base, [n for n in wave if n not in merged], outside),
                              writable=False, strong=True, stage="both", phase=phases[0])
    except task_run.DispatchError as exc:
        reply = f"## Verdict: FAIL\n{exc}"
    (d / "review.md").write_text(reply, encoding="utf-8")
    verdict, crit = task_run.parse_verdict(reply), [f for f in task_run.findings(reply) if f[0] == "C"]
    state.note(f"Note: wave {k} review (phases {', '.join(map(str, phases))}): {verdict}, {len(crit)} critical; {r.runs_rel}/wave-{k}/review.md")
    return "" if verdict == "PASS" and not crit else f"its review did not pass, see {r.runs_rel}/wave-{k}/review.md"
