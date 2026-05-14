# Test Taxonomy Convention

## Purpose

A shared vocabulary for the layers of tests this template recognizes. Used by `playbooks/skills/tdd.md` (workflow) and any reviewer or test-writing role that needs to name what kind of test it is producing. On Claude Code, the `spec-validator` subagent (`.claude/agents/spec-validator.md`) is one such consumer — it writes the acceptance layer of this taxonomy. Codex sessions apply the taxonomy directly from the main thread when writing tests.

This is a **convention**, not a workflow. It names the layers; `tdd.md` names the loop that produces them. A team can run TDD without referencing this taxonomy, and can name layers without running TDD.

## The five layers

| Layer | What it asks | Determinism | Cost |
|---|---|---|---|
| Acceptance | Does the public behavior satisfy the spec? | medium (depends on input shape) | high |
| Contract | Does the implementation honor specific guarantees that the acceptance criteria imply? | high | medium |
| Property-based | Does an invariant hold across a wide input space? | high (under sampled inputs) | medium |
| Integration | Do real components work together end-to-end? | medium | medium-high |
| Unit | Does one function behave correctly in isolation? | high | very low |

### Acceptance

Spec-driven, public-interface, hardest to game because the assertions come from acceptance criteria, not implementation knowledge.

- assert against observable behavior, not internal state
- written from the criteria, not from the code that satisfies them
- one assertion per criterion (binary pass/fail per criterion)
- realistic inputs, not `test_input_123`

Example shape: "given a valid checkout request, the response contains an order id and the cart is cleared."

### Contract

Generated downward from acceptance criteria. Deterministic once written. Tests narrower, more mechanical guarantees that the acceptance criteria imply but do not assert directly.

- if the acceptance criterion says "errors must be actionable", a contract test asserts every error message contains a `what`, a `why`, and a `how to fix`
- if the acceptance criterion says "the response includes an order id", a contract test asserts the order id field type and uniqueness

Example shape: "every public error response object has fields `code`, `message`, and `recovery`."

### Property-based

Invariants that must hold across a wide input space. Use `hypothesis` (Python), `fast-check` (TS), or the equivalent for the language. Property tests catch more bugs than example-based tests for pure functions and serialization roundtrips.

- pick a property that the function must always satisfy
- let the framework generate inputs; the test asserts the property
- shrink failures to the minimal counterexample

Example shapes:
- "sorting preserves all elements" (`set(sorted(arr)) == set(arr) and len(sorted(arr)) == len(arr)`)
- "serialize then deserialize is identity" (`load(dump(x)) == x`)
- "any valid input produces a parseable output"

### Integration

Multiple real components working together. No mocks for the components being integrated. Mocks at the system boundary (network, time, randomness) are fine.

- exercise the seam between two or more units
- realistic data flowing through the seam
- assert the end-to-end behavior, not the internal handoff

Example shape: "POST to `/orders` with a valid payload writes a row to the orders table and returns the row id."

### Unit

One function or method, in isolation. Arrange-Act-Assert. Near-zero cost to write and run.

- single function under test
- collaborators stubbed if they would slow the test or introduce flakiness
- one logical assertion per test (Arrange-Act-Assert)

Example shape: "`format_currency(1234.5, 'USD')` returns `'$1,234.50'`."

## Decision matrix

Which layers are required for what kind of change. Use as a checklist before writing tests, not as a quota.

| Change | Unit | Integration | Acceptance | Property-based |
|---|---|---|---|---|
| Pure utility / helper | required | skip | skip | strong fit if the function has a clear invariant |
| Data model / schema | required | required | consider | consider (serialization roundtrip) |
| API / CLI endpoint | required | required | consider | consider (input shape) |
| Auth / security | required | required | **required** | consider |
| Multi-component workflow | required | required | required | skip |
| Bug fix | required (regression) | skip | skip | skip |
| UI component | required | required | consider | skip |
| Refactor (no behavior change) | existing tests must still pass | — | — | — |

"Consider" means: write the layer if the change has semantics worth checking at that layer; skip if it would just duplicate a lower layer.

## Failure modes to prevent

- **Skipping acceptance on auth or multi-component work.** These changes have implementation-spanning contracts that unit tests cannot catch.
- **Hardcoded counts and pinned versions in assertions.** `assert len(agents) == 16` breaks on every legitimate addition. Prefer structural checks (`assert "implementer.md" in names`) or thresholds (`>= 8`).
- **Mocking the system under test.** If the test mocks the function it claims to verify, it tests the mock, not the behavior.
- **Brittle integration mocks.** Integration tests that stub the seam being integrated test nothing useful. Stub at the system boundary, not at the seam.
- **Property tests with weak invariants.** `assert result is not None` is not a property — it is a smoke test in disguise. A property names something that must always be true.
- **Testing implementation, not behavior.** If renaming an internal function breaks the test, the test was coupled to the internals. Rewrite against the public interface.

## When this convention applies

Any time a test is being written, named, or reviewed. The convention does not require all five layers for every change — see the decision matrix. The convention does require that whichever layer is being written can be named, and that the right one is being written for the change in front of you.
