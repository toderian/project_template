---
name: grill-with-docs
description: Grilling session that challenges a plan against the existing domain model, sharpens terminology, and updates docs/resources/CONTEXT.md plus ADRs inline as decisions crystallise. Use when the user wants to stress-test a plan against the project's language and documented decisions, when a CONTEXT.md or ADR log exists, or when starting one.
---

# Grill With Docs

Use this skill when stress-testing a plan should also leave the project's domain glossary and ADR log sharper than it found them. Plain `grill-me` runs the interview without doc side-effects; this version writes them inline.

Read and follow:

- `playbooks/skills/engineering/grill-with-docs.md`
- `playbooks/skills/engineering/grill-with-docs/CONTEXT-FORMAT.md` (the glossary file format)
- `playbooks/skills/engineering/grill-with-docs/ADR-FORMAT.md` (the ADR file format)

Keep this skill thin. The playbook is the shared workflow and should be updated first when the process changes.
