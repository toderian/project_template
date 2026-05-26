# Knowledge Digests

Curated Markdown summaries of raw source material live here.

Keep digests segregated by area:

```text
_digests/
├── global/          # default, cross-cutting, or infrastructure knowledge
├── <area>/          # digests owned by a registered area
├── _cross-area/     # sources that materially affect several areas
└── _uncategorized/  # sources whose ownership is not known yet
```

Use one digest per source or small source batch:

```text
docs/resources/_digests/<area-or-bucket>/YYYY-MM-DD-<source-slug>.md
```

Digests should name the source, distillation date, digest bucket, affected areas, key facts,
decisions, domain terms, risks, suggested knowledge-base updates, and follow-ups.

Durable facts from a digest should be promoted into the canonical knowledge files under
`docs/resources/` when they are stable enough for future agents to rely on.
