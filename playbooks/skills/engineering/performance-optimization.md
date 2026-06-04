# Performance Optimization

## Purpose

Make code faster by measuring first, not guessing. Most "obvious" optimizations target code that
isn't the bottleneck; this skill enforces the discipline of finding the real hot path with a profiler
before changing anything, and proving each change moved the metric before keeping it.

Use this when the user wants to optimize performance, reduce latency, cut memory, or asks "why is this
slow?" and the goal is *improvement against a baseline*. This is distinct from `diagnose`, which is the
loop for a performance *regression* (something that got slower and you need to find what changed).
Reach for `diagnose` to localize a regression; reach for this skill to optimize a known, measured hot
path.

## The discipline

Optimize in a measured loop. Never skip step 2.

1. **Reproduce a representative workload.** Optimizing against a toy input that doesn't match
   production traffic optimizes the wrong thing. Pin down a workload that reflects real usage — input
   size, distribution, concurrency, cache state.
2. **Measure to find the real hot path.** Profile (CPU, allocations, I/O wait, query time — whichever
   dimension the metric lives in). Record a **baseline number** before touching anything. The profiler
   tells you where the time actually goes; intuition routinely points at the wrong place.
3. **Hypothesize.** State, in one sentence, what is slow and why, grounded in the profile — not "this
   loop looks expensive" but "the profile shows 70% of wall time in N+1 queries from this loop."
4. **Change one thing.** Make the smallest change that tests the hypothesis. One variable at a time, or
   you can't attribute the result.
5. **Re-measure against the baseline.** Same workload, same measurement. Compare to the recorded
   baseline. If the change didn't move the metric meaningfully, **revert it** — a change that doesn't
   help is complexity with no payoff.
6. **Repeat or stop.** Re-profile: the hot path has likely moved. Continue until the metric meets its
   target or the remaining hot paths aren't worth the complexity. Stop when you hit diminishing
   returns, not when you run out of ideas.

## Rules

- **No speculative optimization.** A change without a profile justifying it and a measurement
  confirming it does not get committed. "It should be faster" is a hypothesis, not a result.
- **Guard correctness.** A faster wrong answer is worthless. Keep the existing tests green; add one
  for any behavior the optimization could plausibly change (boundary conditions, concurrency, caching
  staleness).
- **Record the numbers.** Note baseline and post-change figures (and the workload) in the
  commit/PR/task so the win is verifiable and the next person doesn't re-litigate it. For rerunnable
  benchmark output, follow `playbooks/conventions/generated-artifacts.md`
  (`docs/resources/_reports/<workflow>/...`).
- **Prefer the cheap win.** Algorithmic and I/O-shape fixes (N+1 queries, missing index, redundant
  serialization, unbounded allocation) usually dwarf micro-optimizations. Exhaust those before
  hand-tuning inner loops.
- **Consider an ADR** when an optimization makes the code meaningfully harder to read or locks in a
  trade-off (e.g. caching with staleness risk) — see `playbooks/conventions/adr-convention.md`.

---
*Adapted from [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) (MIT License).*
