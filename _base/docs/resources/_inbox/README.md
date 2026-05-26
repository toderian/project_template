# Raw Knowledge Inbox

Drop raw source material here when it needs to be distilled into the project knowledge base.

This folder is staging, not authoritative context. Run `/distill-knowledge` to turn raw files into
Markdown digests under `docs/resources/_digests/<area-or-bucket>/` and durable updates under
`docs/resources/`.

By default, non-Markdown files in this folder are ignored so large, binary, proprietary, or sensitive
sources are not committed by accident. If a project intentionally versions raw source files, adjust this
folder's `.gitignore` in that downstream repo.
