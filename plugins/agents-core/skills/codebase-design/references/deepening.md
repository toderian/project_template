# Deepening

How to deepen a cluster of shallow modules safely, given its dependencies. Assumes the vocabulary in
[SKILL.md](../SKILL.md): **module**, **interface**, **seam**, **adapter**, **depth**.

## Dependency categories

When assessing a candidate for deepening, classify its dependencies. The category decides how the
deepened module is tested across its seam.

### 1. In-process

Pure computation, in-memory state, no I/O. Always deepenable: merge the modules and test through the
new interface directly. No adapter needed.

### 2. Local-substitutable

Dependencies with local test stand-ins (PGLite for Postgres, an in-memory filesystem). Deepenable if
the stand-in exists. The deepened module is tested with the stand-in running in the test suite. The
seam is internal; no port at the module's external interface.

### 3. Remote but owned (ports and adapters)

Your own services across a network boundary — microservices, internal APIs. Define a **port** (the
interface) at the seam. The deep module owns the logic; the transport is injected as an **adapter**.
Tests use an in-memory adapter, production an HTTP/gRPC/queue one.

Recommendation shape: *"Define a port at the seam, implement an HTTP adapter for production and an
in-memory adapter for testing, so the logic sits in one deep module even though it is deployed across a
network."*

### 4. True external (mock)

Third-party services you don't control (payment, SMS, mail). The deepened module takes the external
dependency as an injected port; tests provide a mock adapter.

## Seam discipline

- **One adapter means a hypothetical seam; two means a real one.** Don't introduce a port unless at
  least two adapters are justified, typically production plus test. A single-adapter seam is
  indirection.
- **Internal seams are not external seams.** A deep module may have seams private to its
  implementation and used by its own tests; keep them out of the interface.

## Testing strategy: replace, don't layer

- Old unit tests on shallow modules become waste once tests at the deepened module's interface exist —
  delete them rather than keeping both layers.
- Write the new tests at the deepened module's interface. The interface is the test surface.
- Assert on observable outcomes through the interface, never on internal state.
- Tests should survive internal refactors, because they describe behaviour. If a test has to change
  when the implementation changes, it is testing past the interface.
