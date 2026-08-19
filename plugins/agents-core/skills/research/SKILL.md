---
name: research
description: "Investigate a question against primary sources and capture the findings as one cited Markdown file in the repo. Use when the user wants a topic researched, docs or API facts gathered, or reading legwork delegated while other work continues."
metadata:
  source: "github.com/mattpocock/skills@885e2ca skills/engineering/research/SKILL.md (adapted)"
  pack: core
---

# Research

Dispatch the work to a background `researcher` subagent so the main thread keeps moving. Without
subagents, run the same job inline under the researcher personality (`subagent-protocol` skill,
references/personalities/researcher.md).

Its job:

1. Investigate the question against **primary sources** — official docs, source code, specs,
   first-party APIs — not a secondary write-up of them. Follow every claim back to the source that
   owns it, and say so when a claim has no primary source behind it.
2. Write the findings to a single Markdown file, citing each claim's source with a link.
3. Save it where this repo keeps such notes: `docs/resources/_reports/research/<YYYY-MM-DDTHHMMSS+ZZZZ>_<slug>.md`
   when `docs/resources/` exists (never overwrite an older report — see its `_reports/README.md`),
   otherwise match whatever convention the repo already has, and say where it went.

Report the path and the short answer to the question. Durable conclusions worth keeping graduate
into `docs/resources/` through the `distill-knowledge` skill; the report itself is a snapshot.
