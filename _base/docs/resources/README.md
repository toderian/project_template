# Resources

Durable project documentation lives here: the primary domain glossary (`CONTEXT.md`), area summaries
and dependency graphs under `<area>/`, feature contracts under `<area>/contracts/`, component contexts
under `<area>/components/<component-slug>/CONTEXT.md`, decisions, runbooks, research notes, and other
material that explains how the system works.

Repeated operational procedures belong in `docs/resources/<area>/runbooks/<scenario-slug>.md`; use
`global` for cross-cutting workflows. Committed runbooks are sanitized and use placeholders such as
`<HOST>`, `<USER>`, `<SERVICE>`, `<REMOTE_PATH>`, and `<CONFIG_PROFILE>`. Real values belong in
ignored local binding files under `.local/runbooks/<scenario-slug>.local.md`.

Raw source material waiting to be processed belongs in `_inbox/`. Curated Markdown summaries of those
sources belong in `_digests/`. Use `/distill-knowledge` to extract the important information and
promote stable facts into the canonical knowledge files.

Long-lived committed source documents and binaries, such as `.docx`, PDFs, spreadsheets, diagrams, or
similar durable project resources, belong under `<area>/attachments/`. Keep a nearby Markdown companion
file or attachment index that documents purpose, provenance, area or owner, update guidance, and links
to related digests or canonical docs.

Rerunnable agent reports, audits, inventories, and migration proposals belong in `_reports/` with
timestamped filenames, one file per run. Stable project docs do not belong there.

Raw transcripts, pasted debugging logs, and one-off terminal output should not be pasted directly into
runbooks. Keep raw material in `_inbox/`, distilled reusable facts in `_digests/`, and rerunnable
outputs in `_reports/`; promote only stable procedures into runbooks.

For cross-repo docs, use repo slugs from the committed `.config/repos.project.md` registry when that project has one.
Reference source paths as `<repo-slug>:<repo-relative-path>`. Do not commit absolute local checkout
paths from `.local/repos.map`.

Queued work belongs in `../tasks_manager/`. Area status belongs in `../areas/`. Frozen or obsolete
docs/resources belong in `../archive/`. Workbook bundles belong in root `workbooks/`.

This folder is seeded by `/init`; add structure as the project grows.
