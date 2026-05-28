# Distill Knowledge

## Purpose

Turn raw source material into durable project knowledge. Use this when the user drops documents, notes,
exports, screenshots with text, meeting notes, specifications, research, or other raw context and wants
the important parts summarized, extracted, and integrated into the Markdown knowledge base.

Raw material is not authoritative. The output of this skill is:

- a source-backed digest in `docs/resources/_digests/`
- optional updates to the durable knowledge base under `docs/resources/`
- optional follow-up tasks or inbox ideas for work discovered during distillation

## Knowledge lanes

Use these locations consistently:

- `docs/resources/_inbox/` - raw knowledge drop zone. Files here are waiting to be distilled.
- `docs/resources/_digests/<area>/` - curated Markdown summaries of one source or one small source
  batch, segregated by owning area.
- `docs/resources/_digests/_cross-area/` - digests that materially affect multiple areas.
- `docs/resources/_digests/_uncategorized/` - digests whose area is not known yet.
- `docs/resources/CONTEXT.md` - canonical domain glossary.
- `docs/resources/<area>/summary.md` - durable area architecture knowledge.
- `docs/resources/<area>/dependency-graph.md` - cross-repo/package dependencies.
- `docs/resources/<area>/contracts/<feature-slug>.md` - concrete feature contracts.
- `docs/resources/<area>/runbooks/<scenario-slug>.md` - sanitized reusable operational procedures.
- `docs/resources/<area>/attachments/` - durable committed source documents and binaries with nearby
  Markdown metadata or an attachment index.
- `docs/resources/<area>/components/<component-slug>/CONTEXT.md` - component context.

The raw inbox is a staging area, not a place future agents should rely on for context. Preserve
important facts by writing a digest and promoting durable facts into the appropriate knowledge file.

## Process

### 1. Locate the source material

Accept any of:

- files already in `docs/resources/_inbox/`
- paths supplied by the user
- pasted text in the conversation
- external local paths when the project should not commit raw source files

If the source may be sensitive, proprietary, license-restricted, or too large to commit, keep the raw
file outside the repo or leave it ignored in `_inbox/`. The digest should summarize only what the
project is allowed to retain.

For binary formats, use available local extraction tools when they exist (`pdftotext`, office document
converters, OCR utilities). If extraction is not available, report the blocker or ask the user for a
text export. Do not pretend to have read a file that could not be extracted.

If the user wants a binary or source document committed for long-term reference instead of merely
distilled, place it under `docs/resources/<area>/attachments/` with Markdown metadata documenting
purpose, provenance, area or owner, and update guidance. Do not leave authoritative binaries in
`docs/resources/_inbox/`.

### 2. Classify and scope

For each source, identify:

- source type: spec, meeting notes, research, vendor docs, design notes, audit/report, runbook, other
- project area(s) affected
- whether it contains domain terms, architecture facts, decisions, dependencies, risks, or tasks
- whether the digest should cover one file or a batch of related files

Keep batches small. If unrelated files were dropped together, create separate digests so future agents
can cite the right source without reading irrelevant material.

### 3. Write the digest

Create a digest at:

```text
docs/resources/_digests/<area-or-bucket>/YYYY-MM-DD-<source-slug>.md
```

Use the registered area slug when one area clearly owns the material. Use `global` for cross-cutting
default/infrastructure knowledge, `_cross-area` for sources that materially affect several areas, and
`_uncategorized` when ownership is still unclear. Do not create a new area directory unless the area is
registered or the user has approved the new area. Create the target digest directory if it does not
exist.

Use this shape:

```markdown
# <Source title> - Digest

| Field | Value |
| --- | --- |
| Source | <path, URL, or "pasted conversation"> |
| Distilled | <YYYY-MM-DD> |
| Digest bucket | <area-or-bucket> |
| Areas | <area slugs or N/A> |
| Status | raw-distilled |

## Executive summary

3-7 bullets with the most important takeaways.

## Key facts

- Fact with source anchor or section/page when available.

## Decisions and constraints

- Decision/constraint, or `None found`.

## Domain terms

- Term - meaning, or `None found`.

## Architecture notes

- Durable system knowledge, or `None found`.

## Risks and open questions

- Risk/question and why it matters, or `None found`.

## Suggested knowledge-base updates

- Target file - update to make, or `None`.

## Suggested follow-ups

- Task/inbox idea candidate, or `None`.
```

Use short excerpts only when needed for traceability. Prefer paraphrase. If a source has page numbers,
headings, URLs, timestamps, or filenames, record those anchors beside important facts.

### 4. Promote durable facts

After writing the digest, update durable knowledge files only when the source gives enough evidence:

- add or clarify terms in `docs/resources/CONTEXT.md`
- update area responsibilities, flows, decisions, or open questions in
  `docs/resources/<area>/summary.md`
- update dependency graphs, feature contracts, runbooks, or component contexts when the source
  describes those concrete boundaries or repeatable procedures
- move long-lived committed source documents or binaries to `docs/resources/<area>/attachments/` with
  nearby Markdown metadata or an attachment index

For SSH, setup, debugging, service inspection, and similar operational sources, promote only stable
procedure steps into `docs/resources/<area>/runbooks/`. Keep real hostnames, account names, paths, and
local reusable values in `.local/runbooks/`; never commit secrets.

Do not dump the digest wholesale into the knowledge base. Promote only durable facts that future
agents need during implementation or review. If a fact is interesting but not yet stable, keep it in
the digest and list it as an open question.

When the source implies actionable work, use the task system:

- capture vague follow-ups with `/capture-idea`
- create clear committed tasks with `/add-task`
- avoid silently changing roadmap order

### 5. Clean up or retain raw sources intentionally

At the end, report which raw files were processed. If the raw file is committed Markdown and still
useful, it can remain in `_inbox/` with a link to the digest. If it is ignored, large, binary, or
sensitive, leave it in place locally or ask the user before deleting/moving it. Never delete raw
source material without explicit user approval.

### 6. Report

End with:

- digest files created
- durable knowledge files updated
- raw sources processed and still pending
- follow-ups captured or recommended
- blockers, especially unreadable formats or sensitivity concerns

Use the shared status vocabulary:

```md
## Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
## Summary: ...
## Concerns: ...
## Files changed: ...
```

## Quality bar

- Every digest names its source and distillation date.
- Summaries preserve the most important information without becoming a duplicate of the source.
- Durable knowledge-base updates are source-backed and placed in the correct canonical file.
- Raw inbox material is treated as staging, not long-term context.
- Sensitive or license-restricted raw material is not committed by accident.
