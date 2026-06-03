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

Digests should name the source, distillation date, digest bucket, affected areas, related task or inbox
idea when known, key facts, decisions, domain terms, risks, suggested knowledge-base updates, and
follow-ups.

Durable facts from a digest should be promoted into the canonical knowledge files under
`docs/resources/` when they are stable enough for future agents to rely on.

When a source should remain traceable for future work, add or update a row in
`docs/resources/<area>/sources.md` linking the source, digest, related tasks, and canonical docs.

For operational material, promote stable procedure steps into
`docs/resources/<area>/runbooks/<scenario-slug>.md` and keep real environment values in
`.local/runbooks/<scenario-slug>.local.md`.
