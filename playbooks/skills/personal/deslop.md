# Deslop

## Purpose

Remove generic AI-prose patterns from scientific, technical, and article drafts while preserving the
author's voice, evidence, and meaning. Use this skill when the user asks to "deslop", "de-AI", make a
draft sound human, remove AI patterns, or clean up prose that feels formulaic, padded, or synthetic.

This playbook adapts workflow ideas from
[`stephenturner/skill-deslop`](https://github.com/stephenturner/skill-deslop), copyright 2026 Stephen
D. Turner, licensed under MIT. The upstream project credits `stop-slop` and `tropes.fyi` as prior art;
this repo uses original wording and does not vendor their reference files.

## Working contract

Treat "AI-ish" as a reader-facing style problem, not as proof about how the text was produced.

- Preserve claims, numbers, units, citations, methods, results, and conclusions unless the user asks
  for a substantive rewrite.
- Keep technical terms, acronyms, and field-specific phrasing when they carry precise meaning.
- Do not apply blanket bans. Passive voice, adverbs, symmetrical structure, and formal transitions can
  be appropriate in scientific prose.
- Prefer specific edits with rationale over a wholesale rewrite that flattens the author's voice.
- Flag technical uncertainty instead of inventing missing evidence, citations, mechanisms, or caveats.

For scientific or engineering manuscripts, combine this style pass with `sciwrite` when the user also
needs claim, terminology, number, unit, or citation integrity checks.

## Modes

Choose the narrowest mode that matches the request.

| Mode | Use when | Work performed |
| --- | --- | --- |
| `audit` | The user asks whether prose sounds AI-generated or asks for a review only. | Identify patterns, quote short excerpts, and suggest fixes without rewriting the whole piece. |
| `rewrite` | The user asks to clean up, deslop, de-AI, or humanize the text. | Rewrite the target text while preserving meaning, then list the most important edits. |
| `line-edit` | The user wants trackable, paragraph-by-paragraph edits. | Show original text, suggested revision, and rationale for each edited paragraph. |
| `scientific` | The text is a manuscript, abstract, grant narrative, cover letter, response to reviewers, or technical paper. | Run `rewrite` or `line-edit` with the scientific safety pass enabled. |

Default to `scientific` for manuscript-like prose. Default to `rewrite` for general prose when the user
asks for direct cleanup.

## Process

### 1. Identify the voice to preserve

Infer the target audience, venue, and author stance from the text. Keep discipline-specific formality,
first-person conventions, and the author's level of confidence. Ask a clarifying question only when
the target venue or audience would materially change the edit.

### 2. Protect meaning before style

Before rewriting, mark the claims that cannot drift:

- numerical values, units, thresholds, sample sizes, dates, and statistical results
- named methods, datasets, models, compounds, organisms, populations, or systems
- citations, quoted material, figure/table references, and reviewer comments
- hedges that reflect real uncertainty, such as "may", "suggests", or "consistent with"

If a sentence is vague because evidence is missing, flag the gap rather than filling it from memory.

### 3. Detect high-yield AI-prose patterns

Look for patterns that make prose feel generic or machine-shaped:

- empty signposting: sentences that announce importance without adding information
- throat clearing: openings that delay the claim
- vague stakes: broad claims about complexity, importance, transformation, or nuance
- generic attribution: unnamed "studies", "researchers", "experts", or "the literature" where a
  specific source or finding is needed
- formulaic contrast: repeated "not only X but also Y", "while X, Y", or "rather than X, Y" scaffolds
- self-posed questions that the paragraph immediately answers
- list rhythm in prose: three-part sequences, matched clauses, and repeated sentence lengths
- synthetic transitions: "moreover", "furthermore", "in conclusion", and similar joins used only as
  glue
- false agency: abstractions that "highlight", "underscore", "delve into", or "serve as" without a
  concrete actor or action
- decorative modifiers that make the sentence sound confident without making it more precise

Do not mark a pattern as a problem when it is doing useful work for the field, journal, or reader.

### 4. Rewrite toward specificity and cadence

Apply the smallest edit that fixes the problem.

- Put the claim, actor, or result near the start of the sentence.
- Replace vague evaluation with observable detail.
- Prefer concrete verbs over noun-heavy constructions when the actor matters.
- Use passive voice when the actor is irrelevant, unknown, or conventionally omitted in Methods prose.
- Break repeated sentence patterns. Mix short direct sentences with longer explanatory ones.
- Remove transitions that only announce the relationship; keep transitions that clarify logic.
- Replace broad claims with the exact result, mechanism, limitation, or citation-backed statement.
- Keep one strong point instead of diluting it with a hedged companion point.

### 5. Run the scientific safety pass

For scientific text, verify that the revision did not silently change:

- quantitative claims or statistical interpretation
- causal strength, uncertainty, or scope
- terminology for variables, groups, models, or methods
- citation placement and what each citation appears to support
- journal-appropriate formality
- reviewer-response politeness and accountability

When a passive sentence in Methods or Results is clearer than an active version, keep it. When "we"
would clarify agency in a paper, use it only if it fits the target venue and author preference.

### 6. Score the result when useful

For longer edits, score the final prose from 1 to 5 on:

- `Specificity`: concrete claims replace vague stakes.
- `Voice preservation`: the text still sounds like the author or field.
- `Cadence`: sentence rhythm varies naturally.
- `Evidence discipline`: claims stay tied to data, citations, or stated limits.
- `Compression`: words carry information instead of atmosphere.

If any score is below 3, revise again before returning the result.

## Output structure

For `audit`, use:

```markdown
## Deslop Audit: <scope>

### Summary
<2-3 sentences on the dominant prose patterns and the highest-value fixes.>

### Findings
- <SEVERITY> <location>: <pattern>
  Original: "<short excerpt>"
  Suggested revision: "<specific rewrite or instruction>"
  Rationale: <why this improves the prose without changing meaning>

### Scientific Integrity Notes
<claims, numbers, citations, or terms the author should verify, or "None.">
```

For `rewrite` and `scientific`, use:

```markdown
## Revised Draft
<cleaned-up text>

## What Changed
- <specific, high-signal edit category>

## Scientific Integrity Notes
<claims, numbers, citations, or terms the author should verify, or "None.">
```

For `line-edit`, repeat this block per paragraph:

```markdown
### Paragraph <n>

Original:
<paragraph>

Suggested revision:
<paragraph>

Why:
- <specific explanation>
```

## Quality bar

- The revision sounds specific and author-owned, not merely less formal.
- Scientific meaning, uncertainty, citations, and quantitative details are preserved.
- The output explains non-obvious edits without lecturing about generic writing rules.
- The skill does not overcorrect legitimate scientific conventions into blog prose.
- The final prose has fewer filler phrases, fewer formulaic structures, and better sentence rhythm.
