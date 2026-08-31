---
name: improve-codebase-architecture
description: "Explore a codebase for architectural improvement, focusing on testability by deepening shallow modules. Use when the user wants to improve architecture, find refactoring opportunities, consolidate tightly-coupled modules, or make a codebase more AI-navigable."
metadata:
  source:
    - "github.com/mattpocock/skills (original, since renamed/reworked upstream)"
    - playbooks/skills/engineering/improve-codebase-architecture.md
  pack: architecture
---

# Improve Codebase Architecture

## Purpose

Explore a codebase like an AI would, surface architectural friction, discover opportunities for improving testability, and propose module-deepening refactors as GitHub issue RFCs.

A **deep module** has a small interface hiding a large implementation: more testable, more AI-navigable, and testable at the seam instead of inside. The `agents-core:codebase-design` skill defines depth, seams, leverage and locality; use its words here.

## Process

### 1. Explore the codebase

Navigate the codebase naturally (using whatever exploration mechanism the host runtime offers — Claude Code's Explore subagent, a Codex MultiAgentV2 worker, or direct `rg`/`grep`). Do NOT follow rigid heuristics — explore organically and note where you experience friction:

- Where does understanding one concept require bouncing between many small files?
- Where are modules so shallow that the interface is nearly as complex as the implementation?
- Where have pure functions been extracted just for testability, but the real bugs hide in how they're called?
- Where do tightly-coupled modules create integration risk in the seams between them?
- Which parts of the codebase are untested, or hard to test?

The friction you encounter IS the signal.

**Scope the search before you widen it.** If the user named a direction, take it. Otherwise walk back a
good stretch of `git log --oneline` and concentrate on the codebase's hot spots — a deepening
opportunity in code nobody touches is a refactor you will never cash in. Only if the changes are
scattered with no clear hot spot should you widen the net across the repo.

**Apply the deletion test** to anything you suspect is shallow: imagine deleting it — would complexity
vanish (a pass-through) or reappear across N callers (it was earning its keep)? A "reappears" is the
signal you want. The `agents-core:codebase-design` skill defines the test and the rest of the vocabulary.

### 2. Present candidates

Present a numbered list of deepening opportunities. For each candidate, show:

- **Cluster**: Which modules/concepts are involved
- **Why they're coupled**: Shared types, call patterns, co-ownership of a concept
- **Dependency category**: See the `agents-core:codebase-design` skill (references/deepening.md) for the four categories
- **Test impact**: What existing tests would be replaced by boundary tests

Do NOT propose interfaces yet. Ask the user: "Which of these would you like to explore?"

### 3. User picks a candidate

### 4. Frame the problem space

Before spawning sub-agents, write a user-facing explanation of the problem space for the chosen candidate:

- The constraints any new interface would need to satisfy
- The dependencies it would need to rely on
- A rough illustrative code sketch to make the constraints concrete — this is not a proposal, just a way to ground the constraints

Show this to the user, then immediately proceed to Step 5. The user reads and thinks about the problem while the sub-agents work in parallel.

### 5. Design multiple interfaces

Spawn 3+ parallel design explorations — one per constraint. Use whatever parallel-dispatch mechanism the host runtime offers (Claude Code's `Agent` tool, Codex's MultiAgentV2 workers, or sequentially as a fallback if neither is available). Each must produce a **radically different** interface for the deepened module.

Prompt each exploration with a separate technical brief (file paths, coupling details, dependency category, what's being hidden). This brief is independent of the user-facing explanation in Step 4. Start from the same constraint set `design-an-interface` uses (the `design-an-interface` skill step 2 — minimize the interface, maximize flexibility, optimize for the common case), and add this architecture-specific constraint when applicable:

- Exploration 4 (if applicable): "Design around the ports & adapters pattern for cross-boundary dependencies"

Each exploration outputs:

1. Interface signature (types, methods, params)
2. Usage example showing how callers use it
3. What complexity it hides internally
4. Dependency strategy (how deps are handled — see the `agents-core:codebase-design` skill, references/deepening.md)
5. Trade-offs

Present designs sequentially, then compare them in prose.

After comparing, give your own recommendation: which design you think is strongest and why. If elements from different designs would combine well, propose a hybrid. Be opinionated — the user wants a strong read, not just a menu.

### 6. User picks an interface (or accepts recommendation)

### 7. Create GitHub issue

Create a refactor RFC as a GitHub issue using `gh issue create`. Use the template in `improve-codebase-architecture` skill references/REFERENCE.md. Do NOT ask the user to review before creating — just create it and share the URL.
