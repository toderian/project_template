# Spec and design sections on a task

Task files own executable work; durable docs under `docs/resources/` own system knowledge and
cross-repo contracts. A task-local spec is planned intent until closeout reconciles the durable specs
it names (`agents-tasks:task-ledger` references/spec-lifecycle.md).

## When to add them

| Add | When |
|-----|------|
| `### Specification` | acceptance criteria alone would lose the intent: non-goals, constraints, open questions, a behavior with edge cases worth naming |
| `### Design` | the approach needs agreement before code edits: touched components, interface or data changes, test strategy, rollout/reversibility |
| `Spec refs` row | either section exists (`self`), or the task must satisfy a PRD, plan, `docs/resources/system-map.md`, area summary, dependency graph, component context, or feature contract |

Both sections stay concise; a spec longer than the brief plus the criteria is a sign the task should
be split, not that the spec should grow. Do not add them to routine tasks.

## Making an existing task implementation-ready

1. Read the task and every source it names; classify each durable spec by lifecycle status and never
   use a `draft` or `accepted` spec as current-state evidence.
2. Add or update `Spec refs`, `### Specification`, `### Design`; refine phases into committable
   steps; make every acceptance criterion observable; list related tests or `N/A - <reason>`.
3. Append one execution-log line naming the spec sources and their statuses.
4. Stop before code edits. Summarize: task path, spec sources and statuses, non-goals and open
   questions, phases, criteria and tests. Resolve questions that change behavior or architecture with
   the user (`agents-core:grilling` when there is more than one); record non-blocking ones under the
   task and report that `agents-core:execute-plan` can proceed.
5. `at ledger sync && at ledger check` (`at repos-check` when `Repos` / `Autonomy` changed).
