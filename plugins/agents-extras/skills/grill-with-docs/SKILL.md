---
name: grill-with-docs
description: "A relentless interview that also builds the project's domain model: glossary terms and ADRs written as decisions crystallise."
disable-model-invocation: true
metadata:
  source:
    - "github.com/mattpocock/skills@885e2ca skills/engineering/grill-with-docs/SKILL.md (adapted)"
    - playbooks/skills/engineering/grill-with-docs.md
  pack: architecture
---

Invoke two skills together: `agents-core:grilling` for the interview, and `agents-extras:domain-modeling` so terminology and
decisions are challenged and written down inline as the rounds resolve.

Use this instead of plain `agents-core:grill-me` when the project already has — or is starting to grow — a
domain glossary and an ADR log.

When the frontier is empty, summarise: **Decisions made**, **Glossary changes**
(`docs/resources/CONTEXT.md`), **ADRs created** (`docs/adr/`), **Open questions**, **Risks
identified**.
