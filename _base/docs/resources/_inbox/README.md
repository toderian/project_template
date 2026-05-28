# Raw Knowledge Inbox

Drop raw source material here when it needs to be distilled into the project knowledge base.

This folder is staging, not authoritative context. Run `/distill-knowledge` to turn raw files into
Markdown digests under `docs/resources/_digests/<area-or-bucket>/` and durable updates under
`docs/resources/`.

Raw transcripts, pasted debugging logs, and one-off operational notes belong here before they are
distilled. Do not turn them directly into `docs/resources/<area>/runbooks/` files; promote only stable,
repeatable procedure steps after distillation.

By default, non-Markdown files in this folder are ignored so large, binary, proprietary, or sensitive
sources are not committed by accident. If a project intentionally versions raw source files, adjust this
folder's `.gitignore` in that downstream repo.

If a `.docx`, PDF, spreadsheet, diagram, or similar source document must be committed as a long-lived
project resource, move it to `docs/resources/<area>/attachments/` and add nearby Markdown metadata or
an attachment index documenting purpose, provenance, area or owner, and update guidance.
