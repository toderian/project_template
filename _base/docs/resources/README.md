# Resources

Durable project documentation lives here: the primary domain glossary (`CONTEXT.md`), area summaries
and dependency graphs under `<area>/`, feature contracts under `<area>/contracts/`, component contexts
under `<area>/components/<component-slug>/CONTEXT.md`, decisions, runbooks, research notes, and other
material that explains how the system works.

Raw source material waiting to be processed belongs in `_inbox/`. Curated Markdown summaries of those
sources belong in `_digests/`. Use `/distill-knowledge` to extract the important information and
promote stable facts into the canonical knowledge files.

Rerunnable agent reports, audits, inventories, and migration proposals belong in `_reports/` with
timestamped filenames, one file per run. Stable project docs do not belong there.

Queued work belongs in `../tasks_manager/`. Area status belongs in `../areas/`. Frozen or obsolete
docs/resources belong in `../archive/`.

This folder is seeded by `/init`; add structure as the project grows.
