# Cross-Repo PR Review

## Purpose

Review multiple linked pull requests as one feature delivery, while still producing actionable
findings per PR. Use this when a feature spans repos, packages, services, clients, generated code,
or independently deployed components.

The skill exists because single-PR review misses integration failures: a core library can change a
contract, a backend can depend on it incorrectly, and a UI can assume rollout timing that production
does not guarantee.

## Review Principles

Keep the reviewer's judgment in charge. Use AI-assisted scanning to move faster, but do not outsource
the verdict. A finding is only useful when you can explain the code path, the cross-repo contract it
violates, and why the suggested fix is better.

Preserve context isolation. Inspect each PR in its own section or sub-agent context before mixing
details across repos. Cross-repo reviews need an integration synthesis, but the raw observations for
PR A should not pollute the evidence gathered for PR B.

Build understanding before judging. For each PR, reconstruct what changed, where the data or control
flow goes next, and what assumptions downstream code now depends on. If you cannot explain that flow,
ask questions or mark the gap instead of inventing confidence.

Separate surface scanning from deep pressure testing. First remove obvious issues and irrelevant
noise; then run a deeper review focused on production failure modes, compatibility, rollout order,
security, and meaningful tests.

Scale depth to risk. A small config-only follower PR may need a quick compatibility pass. A versioned
API, migration, auth, generated artifact, or shared library change needs a full deep review.

Classify output strictly. Separate must-fix blockers, should-fix risks, optional suggestions, and
discarded noise. Do not bury blockers in style commentary.

Support author-side self-review. If the user is preparing their own cross-repo PR set before asking
humans to review it, run the same phases and bias the output toward surgical file/line fixes the
author can make before peers spend time on it.

## Inputs

Accept any useful combination of:

- GitHub PR URLs, repo plus PR numbers, branch names, or local checkout paths.
- The intended feature name or existing cross-repo feature contract.
- Release constraints: version pins, deployment order, feature flags, migrations, package publishing,
  generated client updates, or backwards-compatibility promises.

If inputs are incomplete, discover what you can from GitHub metadata, local repos, task files,
contracts under `docs/resources/<area>/contracts/`, and `.config/repos.project.md`. Ask the user only
when the missing answer changes the review verdict.

## Process

### 1. Establish the review set

List every PR/repo in scope and its role in the feature: producer, consumer, shared type package,
backend, UI, CLI, infra, migration, docs, or tests. Record commit SHAs or branch heads so the review
is reproducible.

If a referenced PR is unavailable, continue with the others and mark the missing PR as a review
blocker or limitation depending on risk.

When the tool environment supports sub-agents and the PRs are independent enough to inspect in
parallel, assign one reviewer context per PR and keep one integration context for synthesis. Do not
delegate the final verdict; the main reviewer owns severity and tradeoff judgment.

### 2. Reconstruct the intended contract

Find an existing cross-repo feature contract first. If none exists, build a provisional contract in
the review notes:

- participant responsibilities
- APIs, schemas, events, messages, env/config, CLI/runtime, generated artifacts
- package versions, dependency pins, release tags, and publish order
- old/new compatibility combinations for independently deployed parts
- required tests, CI checks, migrations, and manual verification

The provisional contract is the standard you review against. Be explicit when it is inferred rather
than documented.

### 3. Inspect each PR in isolation

For each PR, create a separate inventory before drawing integration conclusions:

- stated intent from title, body, issue, task, or commit messages
- changed public surfaces and boundary files
- dependency or version changes
- tests added, removed, skipped, or weakened
- CI status and failing checks
- migrations, data backfills, feature flags, env vars, secrets, generated files, and docs

Do not decide that a cross-repo issue exists until you have compared isolated inventories against the
contract.

### 4. Build reviewer understanding

For each PR, answer:

- What new behavior does this PR introduce?
- Which upstream assumptions does it rely on?
- Which downstream components consume its output?
- What breaks if the new assumption is false, late, partially rolled out, or rolled back?
- Which tests prove behavior rather than merely proving that files, types, or mocks exist?

If these questions expose uncertainty, record it as an open question or missing evidence. Do not turn
uncertainty into a speculative finding unless the risk is concrete.

### 5. Run the surface pass

Find obvious local issues first: failed CI, compilation errors, inconsistent naming, missing imports,
dead code, stale generated artifacts, broken docs links, version mismatch, or tests that cannot run.

Dismiss irrelevant style-only suggestions unless they hide a real maintenance or correctness problem.
The goal is to clear noise before deeper review.

### 6. Run the deep pressure test

Review with two lenses:

- Senior programmer: correctness, error paths, data validation, concurrency, performance, test
  quality, and maintainability.
- Senior architect: contracts, ownership boundaries, compatibility, rollout order, observability,
  security, failure isolation, and reversibility.

Pressure test the implementation:

- Does every consumer use the exact contract the producer now exposes?
- Can old backend plus new UI, new backend plus old UI, old core plus new backend, and rollback states
  behave safely?
- Are package versions and generated clients pinned or published in the required order?
- Are migrations, schema changes, and API defaults safe for partial rollout?
- Are feature flags, env vars, auth/signing, and secrets treated as first-class boundaries?
- Are error states explicit enough for UI and operations to handle?
- Do tests validate real behavior at the integration boundary, not only mocks or type existence?
- Is there an e2e or contract test that would fail if any repo implemented the boundary differently?

### 7. Synthesize cross-repo findings

Compare the isolated PR inventories against the provisional or documented contract. Separate:

- Cross-repo blockers: issues that only appear when PRs are considered together.
- Per-PR blockers: local issues that block that PR regardless of the others.
- Follow-ups: useful work that should not block the current merge.
- Noise: AI-suggested or reviewer-considered items intentionally discarded.

When a finding spans repos, assign the primary fix location and mention every affected PR.

### 8. Verify

Prefer executable evidence:

- GitHub CI statuses and logs for each PR.
- Local tests for touched modules.
- Contract, integration, generated-client, migration, and e2e checks when available.
- Static checks for dependency pins, schema generation, and API client regeneration.

If checks cannot run, say exactly what was not run and how that affects confidence.

## Report Structure

Use this structure for the final review:

```md
## Overall Verdict
BLOCK | REQUEST_CHANGES | COMMENT_ONLY | APPROVE_WITH_NOTES | APPROVE

One-paragraph explanation.

## Review Set
| PR | Repo | Role | Head/SHA | CI | Notes |
|----|------|------|----------|----|-------|

## Merge/Rollout Order
1. ...

## Cross-Repo Findings
### [Severity] Title
- Affected PRs: ...
- Location: ...
- Issue: ...
- Why it matters: ...
- Suggested fix: ...
- Evidence: ...

## Per-PR Findings
### <repo>#<PR>
- [Severity] `path:line` - issue, impact, suggested fix.

## Test and Coverage Gaps
- ...

## Open Questions
- ...

## Checks Run
- ...

## Discarded Noise
- Optional; include only when it helps explain why common AI suggestions were not reported.
```

Severity guidance:

- `Blocker`: merge would likely break production, data, security, compatibility, or release order.
- `Major`: correctness or maintainability risk that should be fixed before merge.
- `Minor`: useful fix with limited blast radius.
- `Nit`: optional cleanup; include sparingly.

## Quality Bar

- The review identifies the intended cross-repo contract before judging implementation.
- Each PR is inspected in isolation before integration synthesis.
- Findings are grouped both by cross-repo impact and by owning PR.
- Merge order, rollout safety, and old/new compatibility are explicit.
- Tests are evaluated for behavioral coverage, not just volume.
- The final verdict is human-owned: evidence-backed, severity-classified, and free of unfiltered AI
  noise.
