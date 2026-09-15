---
name: codebase-design
description: "Shared vocabulary and principles for designing deep modules: a lot of behaviour behind a small interface, placed at a clean seam, testable through that interface. Use when designing or reviewing a module's interface, deciding where a seam goes, hunting for deepening opportunities, making code more testable, or when another skill needs the module/interface/seam/depth terms."
metadata:
  source:
    - "github.com/mattpocock/skills@885e2ca skills/engineering/codebase-design/SKILL.md (adapted)"
    - playbooks/skills/engineering/tdd.md (references/deep-modules.md, references/interface-design.md)
  pack: architecture
---

# Codebase Design

Design **deep modules**: a lot of behaviour behind a small interface, placed at a clean seam, testable
through that interface. This is the vocabulary layer — the design, testing and review skills all
use these words, and this is where
they are defined. It is a reference to consult, not a session to run.

## Glossary

Use these terms exactly. Consistent language is the point, so don't substitute "component", "service",
"API", or "boundary".

**Module** — anything with an interface and an implementation. Deliberately scale-agnostic: a function,
a class, a package, or a tier-spanning slice. _Avoid_: unit, component, service.

**Interface** — everything a caller must know to use the module correctly: the type signature, but also
invariants, ordering constraints, error modes, required configuration, and performance characteristics.
_Avoid_: API, signature — both are too narrow, naming only the type-level surface.

**Implementation** — what is inside a module. Distinct from **adapter**: a thing can be a small adapter
with a large implementation (a Postgres repository) or a large adapter with a small implementation (an
in-memory fake). Say "adapter" when the seam is the topic, "implementation" otherwise.

**Adapter** — a concrete thing that satisfies an interface at a seam. Describes the *role* it fills,
not what is inside it.

**Depth** — leverage at the interface: how much behaviour a caller or a test can exercise per unit of
interface it has to learn. A module is **deep** when a large amount of behaviour sits behind a small
interface, **shallow** when the interface is nearly as complex as the implementation.

**Seam** (Michael Feathers) — a place where you can alter behaviour without editing in that place; the
*location* at which a module's interface lives. Where to put the seam is its own decision, separate
from what goes behind it. _Avoid_: boundary, which is overloaded with domain-driven design's bounded
context.

**Leverage** — what callers get from depth: more capability per unit of interface learned. One
implementation pays back across N call sites and M tests.

**Locality** — what maintainers get from depth: change, bugs, knowledge and verification concentrate in
one place instead of spreading across callers. Fix once, fixed everywhere.

## Deep vs shallow

**Deep module** = small interface + lots of implementation:

```
┌─────────────────────┐
│   Small Interface   │  ← Few methods, simple params
├─────────────────────┤
│                     │
│  Deep Implementation│  ← Complex logic hidden
│                     │
└─────────────────────┘
```

**Shallow module** = large interface + little implementation (avoid):

```
┌─────────────────────────────────┐
│       Large Interface           │  ← Many methods, complex params
├─────────────────────────────────┤
│  Thin Implementation            │  ← Just passes through
└─────────────────────────────────┘
```

When designing an interface, ask: can I reduce the number of methods? Can I simplify the parameters?
Can I hide more complexity inside?

## Principles

- **Depth is a property of the interface, not the implementation.** A deep module can be internally
  composed of small, mockable, swappable parts; they just are not part of its interface. A module can
  have **internal seams** (private to its implementation, used by its own tests) as well as the
  **external seam** at its interface — don't expose an internal seam through the interface merely
  because a test uses it.
- **The deletion test.** Imagine deleting the module. If complexity vanishes, it was a pass-through. If
  complexity reappears across N callers, it was earning its keep. This is the screening question for
  anything you suspect is shallow.
- **The interface is the test surface.** Callers and tests cross the same seam. If you want to test
  *past* the interface, the module is probably the wrong shape.
- **One adapter means a hypothetical seam; two adapters means a real one.** Don't introduce a seam
  unless something actually varies across it — typically production plus test. A single-adapter seam is
  indirection, which the `agents-core:simplicity-review` skill flags as `yagni`; that skill owns the review side of
  this rule.

## The two senses of "seam"

Both are live in this repo and they are not the same thing. Say which one you mean:

- **Design seam** (this skill) — where a module's interface lives, chosen so behaviour can be altered
  without editing in place.
- **Test seam** (`agents-core:tdd` skill, references/test-taxonomy.md) — the level a test observes behaviour at.
  Note its inverse rule: stub at the system boundary, *not* at the seam being integrated.
- **Regression seam** (`agents-core:diagnose` skill, Phase 5) — a seam where a test exercises the real bug pattern
  as it occurs at the call site. When none exists, that absence is itself the finding.

## Designing for testability

Good interfaces make testing natural.

1. **Accept dependencies, don't create them.**

   ```typescript
   // Testable
   function processOrder(order, paymentGateway) {}

   // Hard to test
   function processOrder(order) {
     const gateway = new StripeGateway();
   }
   ```

2. **Return results, don't produce side effects.**

   ```typescript
   // Testable
   function calculateDiscount(cart): Discount {}

   // Hard to test
   function applyDiscount(cart): void {
     cart.total -= discount;
   }
   ```

3. **Small surface area.** Fewer methods means fewer tests; fewer parameters means simpler setup.

## Rejected framings

- **Depth as the ratio of implementation lines to interface lines** (Ousterhout's own metric): it
  rewards padding the implementation. Use depth-as-leverage instead.
- **"Interface" as a language keyword or a class's public methods**: too narrow — an interface includes
  every fact a caller must know.
- **"Boundary"**: overloaded with domain-driven design. Say **seam** or **interface**.

## Going deeper

- Deepening a cluster given its dependencies — dependency categories and the replace-don't-layer
  testing rule: [references/deepening.md](references/deepening.md).
- Exploring several radically different interfaces for one module: the `agents-extras:design-an-interface` skill.
- Finding deepening candidates across a codebase: the `agents-extras:improve-codebase-architecture` skill.
