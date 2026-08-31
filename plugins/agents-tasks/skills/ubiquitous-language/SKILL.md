---
name: ubiquitous-language
description: "Retrospectively harvest domain terms from the current conversation into docs/resources/CONTEXT.md, flagging ambiguities and proposing canonical terms. Use when the user wants to catch the glossary up after a discussion, define domain terms in bulk, harden terminology, or mentions \"domain model\" or \"DDD\"."
metadata:
  source:
    - "github.com/mattpocock/skills (original, since renamed/reworked upstream)"
    - playbooks/skills/engineering/ubiquitous-language.md
  pack: docs-knowledge
---

# Ubiquitous Language

## Purpose

Retrospectively harvest the domain terms from **this conversation** into the project glossary: scan
what was said, catch the places one word meant two things or two words meant one, and propose
canonical terms.

This is the batch move. `agents-extras:domain-modeling` is the inline one — it sharpens terms *as* a design session
crystallises them and writes each one down on the spot. Reach for this skill when the conversation has
already happened and the glossary needs catching up.

## Where it writes

The project glossary, never a separate file: `docs/resources/CONTEXT.md` (follow
`docs/resources/CONTEXT-MAP.md` to the right context if the repo has several; a root `CONTEXT.md` is
only a pointer or legacy fallback). If `CONTEXT_DOCS_DIR` is set in `project.env` at the repo root,
follow it silently, namespaced by source repo, exactly as `agents-extras:domain-modeling` does.

Use the layout and rules in the `agents-extras:domain-modeling` skill (references/CONTEXT-FORMAT.md): term
definitions with _Avoid_ aliases, Relationships, Example dialogue, Flagged ambiguities. Do not invent a
second format here.

Create the glossary lazily: if none exists, create it when the first term is resolved.

## Process

1. **Scan the conversation** for domain-relevant nouns, verbs, and concepts.
2. **Identify problems**: the same word used for different concepts (ambiguity), different words used
   for one concept (synonyms), and vague or overloaded terms.
3. **Read the existing glossary first.** Terms already defined there are the canon — extend or sharpen
   them rather than proposing a rival definition, and say explicitly when the conversation contradicts
   what the glossary says.
4. **Propose the additions and changes to the user** before writing: new terms, sharpened definitions,
   and each ambiguity with a recommended resolution. Be opinionated — pick the better word and list the
   others as aliases to avoid.
5. **Write the agreed terms into the glossary**, updating the Relationships, Example dialogue, and
   Flagged ambiguities sections so they still describe the whole context, not just this batch.
6. **Report** what was added, what was sharpened, and what remains ambiguous.

## Rules

- Only terms that carry meaning for a domain expert. Skip module and class names unless the domain
  uses them, and skip general programming concepts (array, endpoint, timeout) unless this project
  gives them a specific meaning.
- Definitions are one sentence: what the thing *is*, not what it does.
- Flag conflicts explicitly rather than silently picking a winner.
- A decision that is hard to reverse, surprising without context, and the result of a real trade-off
  belongs in an ADR, not the glossary. See the `agents-tasks:knowledge-base` skill (references/adr-convention.md).

## Quality bar

- The glossary is the only place the terms live; this skill created no second file.
- Every ambiguity found in the conversation is either resolved in the glossary or listed under
  Flagged ambiguities.
- Terms already in the glossary were extended, not duplicated with a rival definition.
