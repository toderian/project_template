# Spec lifecycle

Specs can describe either planned intent or implemented system behavior. Agents must distinguish those
states before using a spec as evidence.

Use these statuses for durable specs under `docs/resources/`, including `system-map.md`, area
summaries when they describe explicit contracts, dependency graphs, component contexts, and feature
contracts:

| Status | Meaning |
|--------|---------|
| `draft` | Proposal or rough design. Do not treat it as approved or implemented. |
| `accepted` | Approved target behavior. Use it as implementation intent, not current-state evidence. |
| `partially-implemented` | Some evidence exists. Separate the live behavior from the remaining planned work. |
| `implemented` | Verified current behavior, backed by code, tests, task history, or other evidence. |
| `superseded` | Obsolete. Link the replacement or state why it no longer applies. |

Task-local `### Specification` and `### Design` sections are planned intent until the task is completed
and its linked durable specs are reconciled. A completed task proves only its acceptance criteria and
recorded changes; it does not automatically make every linked durable spec `implemented`.

## Resolving spec sources before implementation

Resolve in this order and record the result in the execution log (one line per source is enough):

1. Task-local `### Specification` and `### Design` when present.
2. Optional `Spec refs` metadata, including `self`, PRDs, plans, `docs/resources/system-map.md`, area
   summaries, dependency graphs, component contexts, and feature contracts.
3. Task acceptance criteria and related tests.
4. Relevant durable docs discovered during the current-state review.
5. User-provided context from the current request.

For each resolved source, note whether it is planned intent (`draft` or `accepted`) or current-state
evidence (`implemented` or evidence-backed `partially-implemented`). If a source is `superseded`,
follow the replacement if one is named; otherwise ignore it and record the uncertainty.

## At completion

If the task implements, partially implements, supersedes, or invalidates a referenced durable spec,
update that spec's status and evidence, or record an explicit follow-up when the update is outside the
closeout scope (`agents-tasks:complete-task` step 3).
