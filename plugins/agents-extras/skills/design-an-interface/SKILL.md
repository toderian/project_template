---
name: design-an-interface
description: "Generate multiple radically different interface designs for a module using parallel sub-agents when available. Use when the user wants to design an API, explore interface options, compare module shapes, or mentions \"design it twice\"."
metadata:
  source:
    - "github.com/mattpocock/skills (original, since renamed/reworked upstream)"
    - playbooks/skills/misc/design-an-interface.md
  pack: architecture
---

# Design an Interface

## Purpose

Generate multiple radically different interface designs for a module, then compare. Based on "Design It Twice" from "A Philosophy of Software Design": your first idea is unlikely to be the best.

## Workflow

### 1. Gather Requirements

Before designing, understand:

- [ ] What problem does this module solve?
- [ ] Who are the callers? (other modules, external users, tests)
- [ ] What are the key operations?
- [ ] Any constraints? (performance, compatibility, existing patterns)
- [ ] What should be hidden inside vs exposed?

Ask: "What does this module need to do? Who will use it?"

### 2. Generate Designs (Parallel Sub-Agents Where Available)

Generate 3+ independent designs. Use the runtime's parallel subagent mechanism when available
(`Task` tool on Claude Code, Codex multi-agent tools when present). If no subagent runtime is available,
run three isolated main-thread passes and keep each pass blind to the others until comparison. Each pass
must produce a **radically different** approach.

```
Prompt template for each sub-agent:

Design an interface for: [module description]

Requirements: [gathered requirements]

Constraints for this design: [assign a different constraint to each agent]
- Agent 1: "Minimize method count - aim for 1-3 methods max"
- Agent 2: "Maximize flexibility - support many use cases"
- Agent 3: "Optimize for the most common case"
- Agent 4: "Take inspiration from [specific paradigm/library]"

Output format:
1. Interface signature (types/methods)
2. Usage example (how caller uses it)
3. What this design hides internally
4. Trade-offs of this approach
```

### 3. Present Designs

Show each design with:

1. **Interface signature** - types, methods, params
2. **Usage examples** - how callers actually use it in practice
3. **What it hides** - complexity kept internal

Present designs sequentially so user can absorb each approach before comparison.

### 4. Compare Designs

After showing all designs, compare them on the three axes that decide module shape (the
`codebase-design` skill defines all three):

- **Depth** — leverage at the interface: how much behaviour a caller exercises per unit of interface
  it must learn.
- **Locality** — where change, bugs and verification concentrate once this design ships.
- **Seam placement** — is the interface in the right place, and does anything actually vary across it?

Then the practical pair: **ease of correct use** vs **ease of misuse**, plus whether the shape allows
an efficient implementation or forces awkward internals.

Discuss trade-offs in prose, not tables. Highlight where designs diverge most, and end with your own
recommendation — the user wants a strong read, not a menu. If elements of different designs combine
well, propose the hybrid.

### 5. Synthesize

Often the best design combines insights from multiple options. Ask:

- "Which design best fits your primary use case?"
- "Any elements from other designs worth incorporating?"

## Anti-Patterns

- Don't let sub-agents produce similar designs - enforce radical difference
- Don't skip comparison - the value is in contrast
- Don't implement - this is purely about interface shape
- Don't evaluate based on implementation effort
