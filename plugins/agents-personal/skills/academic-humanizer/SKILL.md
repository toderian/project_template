---
name: academic-humanizer
description: "Improve AI-assisted academic manuscripts and funding proposals while preserving scholarly voice, claims, numbers, citations, and disclosure integrity. Use when the user asks for \"academic-humanizer\", academic humanizing, or de-AI editing of papers, theses, abstracts, or grant proposals (NSF/NIH)."
metadata:
  source: playbooks/skills/personal/academic-humanizer.md
  pack: writing
---

# Academic Humanizer

## Purpose

Improve AI-assisted academic prose without turning it into casual, opinionated, or unsupported
writing. Use this skill for manuscripts, theses, rebuttals, abstracts, and funding proposals when
the user wants prose to sound less generic while staying precise, evidence-bound, and venue-appropriate.

This playbook adapts workflow ideas from
[`AIScientists-Dev/academic-humanizer`](https://github.com/AIScientists-Dev/academic-humanizer),
copyright 2026 AIScientists-Dev, licensed under MIT. The upstream project credits `blader/humanizer`
and `koaeraser/ARMS` as prior work.

For general non-academic prose, use `agents-personal:deslop`. For a manuscript-wide clarity and consistency audit,
use `agents-personal:sciwrite`. Use this skill when the request is specifically about academic humanizing, AI-assisted
academic prose, or grant-proposal text.

## Boundaries

- Do not help users evade required AI-use disclosure, authorship policies, or institutional rules.
- Preserve all numbers, units, equations, citations, figure/table references, methods, results, and
  conclusions unless the user explicitly asks for substantive scientific revision.
- Do not invent evidence, preliminary results, collaborators, citations, grants, letters, or claims.
- Treat neutral, precise, field-specific prose as a valid human voice. Do not overcorrect academic
  writing into blog prose.
- Keep evidence-tied hedging when the claim is uncertain. Do not strengthen "suggests", "is consistent
  with", or "may indicate" into unsupported certainty.

## Modes

Choose the narrowest mode that matches the request.

| Mode | Use when | Work performed |
| --- | --- | --- |
| `audit` | The user asks whether text sounds generic, AI-assisted, overclaimed, or proposal-weak. | List high-yield findings with locations and concrete fixes. |
| `rewrite` | The user asks to humanize, de-AI, polish, or revise the provided academic text. | Rewrite while preserving content, claims, and citation support, then report what changed. |
| `line-edit` | The user wants trackable paragraph-by-paragraph changes. | Show original, revision, and rationale per paragraph. |
| `proposal` | The text is NSF, NIH, fellowship, foundation, or grant text. | Apply the proposal-specific feasibility and first-pages checks before style edits. |
| `voice-match` | The user provides an author sample or venue target. | Match sentence rhythm, hedging level, terminology, and register without copying distinctive phrases. |

Default to `proposal` for Specific Aims, Project Summary, Project Description, Broader Impacts,
fellowship statements, and foundation proposals. Default to `rewrite` for academic text when the user
asks to humanize it and provides enough text.

## Process

### 1. Classify the document

Identify the document type, target venue or agency, audience, and whether the user supplied an author
sample. If the target venue or agency would materially change the edit and cannot be inferred, ask one
brief question before rewriting.

### 2. Protect content before style

See also `agents-personal:deslop`'s "Protect meaning before style" step for the general-prose variant of this same idea
— kept separate here because these two skills adapt different upstream projects with independent
wording.

Before editing, mark the content that cannot drift:

- numerical values, units, statistics, dates, thresholds, sample sizes, and reported effects
- equations, variables, model names, dataset names, methods, organisms, populations, or compounds
- citations, quoted material, figure/table references, reviewer comments, and response commitments
- uncertainty language that reflects real evidence limits

If support for a claim is missing, flag it or add a placeholder such as `[add evidence/citation]` only
when the user requested rewrite help. Do not fill the gap from memory.

### 3. Remove academic AI tells

Fix generic patterns only when they weaken the academic text:

- inflated significance: "pivotal", "groundbreaking", "paramount", "revolutionary"
- vague stakes: "has important implications" without the specific implication
- formulaic openings: "In recent years...", "With the rapid development of...", "Despite recent advances..."
- empty intensifiers: "extensive", "comprehensive", "wide range of" without enumerated scope
- overclaiming verbs: "prove", "establish", "demonstrate" when the evidence only supports "suggests",
  "shows in this setting", or "provides evidence"
- filler connectives: repeated "Moreover", "Furthermore", "Additionally", and "Importantly"
- contribution cliches: "novel method", "extensive experiments", "strong results" without specifics
- citation dumping: long citation lists that do not explain which source supports which point
- synonym drift: changing terms for variety when the same concept should keep the same name
- overlong clause-stacked sentences that hide the main claim

Keep legitimate academic conventions: passive voice in methods, first-person plural when the venue
allows it, technical definitions, formal notation, and precise repeated terminology.

### 4. Enforce claim-evidence discipline

For each empirical or technical claim, check whether the text supplies a number, figure, table,
citation, theorem, method, or stated rationale. Then calibrate the sentence:

- If a claim is unsupported, soften it or mark the missing evidence.
- If a verb is stronger than the evidence, downgrade it.
- If a magnitude is vague, use the supplied number or range and tie it to the metric, method, baseline,
  dataset, or population.
- If the text compares methods, prefer the strongest relevant comparator over a trivial baseline.

Treat suspected scientific issues as author verification notes, not permission to silently correct the
science.

### 5. Match voice and venue

If an author sample is supplied, match its register, sentence length, connective habits, hedging level,
notation style, and section openings. Do not copy signature phrases or introduce personal flourishes.

If no sample is supplied, default to clean, direct academic prose:

- lead with the claim, result, or gap
- use concrete nouns and verbs
- preserve field-specific terminology
- keep paragraph structure unless structural editing is requested
- avoid casual contractions, jokes, marketing language, and exaggerated personality

## Proposal Mode

Funding proposals need vision plus feasibility. Do not flatten all ambition: phrases such as
"long-term goal", "transformative", "foundation", or "pioneer" can be appropriate when the plan,
preliminary data, team, or theory supports them.

### First-pages check

Spend the most attention on the opening pages because reviewers form their score early.

- **NIH Specific Aims:** By the end of the page, the reader should know the problem, known facts, gap
  or critical need, long-term goal, central hypothesis, rationale, 2-3 aims, expected outcomes, and
  payoff.
- **NSF Project Summary:** Keep Overview, Intellectual Merit, and Broader Impacts self-contained and
  explicit.
- **NSF Project Description:** Open with long-term vision, proposal goal, gap, thrusts or aims, and
  payoff within the first 1-2 pages where possible.

If the hook, gap, central idea, aims, or payoff is missing or buried, fix that before polishing later
sections.

### Proposal-specific fixes

- Convert method-as-aim phrasing into question, outcome, or knowledge-gain phrasing.
- Make aims parallel and independently valuable when possible. If an aim depends on another, state the
  fallback or de-risking plan.
- Attach bold claims to feasibility evidence: preliminary data, prior publications, classical
  foundations, collaborators, letters, facilities, datasets, or staged milestones.
- Replace generic Broader Impacts with concrete programs, audiences, deliverables, courses, tools,
  timelines, or measures tied to the research.
- Keep central hypotheses falsifiable and committed. Move cautious interpretation hedges to the
  Approach when appropriate.
- Surface the real supplied team record early when it de-risks execution. Do not invent standing,
  funding, partnerships, or letters.

## Output

For `audit`, use:

```markdown
## Academic Humanizer Audit: <scope>

### Summary
<2-3 sentences on the dominant patterns and highest-value fixes.>

### Findings
- <SEVERITY> <location>: <finding>
  Original: "<short excerpt>"
  Suggested revision: "<specific rewrite or instruction>"
  Rationale: <why this improves the academic prose without changing meaning>

### Evidence And Integrity Notes
<claims, numbers, citations, feasibility gaps, or policy/disclosure issues to verify, or "None.">
```

For `rewrite`, `proposal`, and `voice-match`, use:

```markdown
## Revised Draft
<edited text>

## What Changed
- <specific, high-signal edit category>

## Evidence And Integrity Notes
<confirmation that numbers/equations/citations were preserved, plus any claims or feasibility gaps to verify.>
```

For `line-edit`, repeat:

```markdown
### Paragraph <n>

Original:
<paragraph>

Suggested revision:
<paragraph>

Why:
- <specific rationale>
```

## Quality bar

- The result reads as academic prose written by a careful scholar, not casualized general-purpose text.
- Claims, uncertainty, citations, numbers, and methods do not drift.
- Generic AI patterns are removed only when they weaken clarity, evidence discipline, or voice.
- Proposal revisions preserve justified ambition while making feasibility visible.
- The response states any evidence, citation, feasibility, or disclosure issues the author must verify.
