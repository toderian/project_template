# SciWrite

## Purpose

Review scientific or engineering manuscripts for writing clarity while preserving the author's
technical content. Use this skill to make claims easier to follow, not to change claims, data,
methods, results, statistical interpretation, or conclusions.

This playbook is adapted from
[`labarba/sciwrite`](https://github.com/labarba/sciwrite), copyright 2026 Lorena A. Barba,
licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). It has been modified for
this repository's shared-playbook plus thin-wrapper skill layout.

For requests specifically about "deslop", "de-AI", "make this sound human", or removing AI-style
prose patterns, use `deslop` as the style-cleanup pass and keep this playbook's scientific integrity
boundary in force.

## Non-negotiable boundary

Scientific claims and data are author-owned. Do not silently alter them.

- Preserve numerical values, units, sample sizes, p-values, citations, methods, results, and
  conclusions.
- If a claim, number, citation, or technical term looks wrong or inconsistent, flag it as a finding
  and ask the author to verify it.
- Suggested rewrites may improve grammar, emphasis, concision, and flow, but must not introduce new
  technical meaning.
- Respect disciplinary and journal conventions. Passive voice, acronyms, and formulaic Methods prose
  can be appropriate in some fields.

## Review modes

Choose the narrowest mode that matches the user's request.

| Mode | Use when | Work performed |
| --- | --- | --- |
| `full-review` | The user asks for a manuscript, chapter, or paper-wide review. | Run all five audit passes and return a structured report. |
| `section-review` | The user names one section such as Abstract, Introduction, Methods, Results, or Discussion. | Run all five audit passes on that section only. |
| `targeted` | The user asks for one issue such as passive voice, clutter, sentence flow, terminology, numbers, or citations. | Run only the relevant pass or passes. |
| `interactive` | The user asks to walk through revisions or learn from examples. | Work paragraph by paragraph with before/after suggestions and explanations; wait before moving on. |

Default to `full-review` when the scope is ambiguous and enough manuscript text is available. If the
manuscript is missing, ask for the file path, pasted section, or target text.

## The five audit passes

Run passes sequentially for `full-review` and `section-review`. For `targeted`, run only the pass or
passes that match the user's request.

### Pass 1: Clutter and concision

Find words that do not earn their place.

- Replace inflated phrases with direct ones, for example "due to the fact that" -> "because",
  "in order to" -> "to", "a majority of" -> "most", and "on the basis of" -> "based on".
- Delete throat-clearing phrases such as "it is important to note that" when the sentence works
  without them.
- Flag vague openings such as "in terms of" and recommend a more specific subject or verb.
- Remove redundant modifiers where the noun or verb already carries the meaning.
- Prefer precise technical language over decorative adjectives and generalized academic filler.

### Pass 2: Voice and verb vitality

Make agency and action clear.

- Identify passive constructions where the actor matters or accountability is hidden.
- Convert passive voice to active voice only when doing so preserves the technical meaning.
- Keep passive voice when the actor is unknown, irrelevant, conventional for the target venue, or the
  object of the action deserves emphasis.
- Replace nominalizations and "smothered verbs" with direct verbs where possible: "conducted an
  analysis" -> "analyzed", "provided a description" -> "described", "achieved a reduction" ->
  "reduced".
- Prefer subject-verb-object order when it clarifies who did what.

### Pass 3: Sentence architecture

Improve the reader's path through each paragraph.

- Flag buried predicates, especially when long subject phrases separate the grammatical subject from
  the main verb.
- Break sentences that carry too many logical steps.
- Combine choppy sentences only when the relationship between ideas is clear.
- Use punctuation as structure: colons for setup, semicolons for closely linked independent clauses,
  and dashes sparingly for emphasis or interruption.
- Check paragraph rhythm. A paragraph made entirely of same-length sentences often reads flat or
  mechanical.

### Pass 4: Terminology and keyword consistency

Scientific repetition is often clarity.

- Extract defined terms, group names, variable names, methods, model names, abbreviations, and units
  from the manuscript.
- Check that the same concept keeps the same name across Abstract, Methods, Results, Discussion,
  tables, and figure captions.
- Flag synonym drift where the author appears to rename a defined term for variety.
- Check that acronyms are useful, standard for the field, and defined where readers need them.
- Prefer exact repeated terminology over stylistic synonym swaps when a change could imply a new
  category, variable, or method.

### Pass 5: Numbers, units, and citation integrity

Audit internal consistency without deciding the science for the author.

- Compare numerical claims across Abstract, main text, tables, figures, and captions.
- Flag mismatched sample sizes, percentages, units, significant figures, thresholds, or model names.
- Check that reported percentages are plausible given raw counts when both appear.
- Flag citation patterns that need author verification, especially secondary-source citations for
  specific quantitative claims.
- Treat every suspected number, unit, or citation problem as a verification request, not as permission
  to correct the manuscript from memory.

## Severity tags

Tag every finding with one severity.

- `CRITICAL`: The issue can mislead the reader, such as an inconsistent value, term, unit, or citation
  that changes interpretation.
- `MAJOR`: The issue significantly impairs clarity, such as a buried predicate, dense clutter, unclear
  agency, or heavy nominalization in an important sentence.
- `MINOR`: The issue is worth fixing but does not block understanding, such as mild wordiness or an
  optional rhythm improvement.

## Report structure

For `full-review` and `section-review`, use this structure:

```markdown
## SciWrite Review: <document or section>

### Summary
<2-3 sentences on the dominant writing issues and the strongest revision opportunities.>

### Pass 1: Clutter and Concision
- <SEVERITY> <location>: <finding>
  Original: "<short excerpt>"
  Suggested revision: "<rewrite that preserves technical meaning>"
  Rationale: <why the revision helps>

### Pass 2: Voice and Verb Vitality
...

### Pass 3: Sentence Architecture
...

### Pass 4: Terminology and Keyword Consistency
...

### Pass 5: Numbers, Units, and Citation Integrity
...

### Top Priority Revisions
1. <highest-impact revision>
2. <next revision>
3. <next revision>
```

For `targeted` mode, report only the relevant pass or passes. For `interactive` mode, use this
per-paragraph structure:

```markdown
### Paragraph <n>

Original:
<paragraph>

Suggested revision:
<paragraph>

Why:
- <specific explanation>

Continue?
```

## Quality bar

- Every suggestion includes a location, original text, concrete revision, and rationale.
- The report distinguishes writing edits from technical verification notes.
- Rewrites preserve scientific meaning and do not invent evidence.
- Findings are specific enough for the author to apply without guessing.
- The final output respects the user's requested mode and scope.
