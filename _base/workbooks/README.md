# Workbooks

This root folder is the canonical home for workbook bundles.

Each workbook lives in its own folder and contains everything needed for that workbook: `README.md`,
scripts, data, assets, templates, examples, outputs, or support files. Workbooks may be nested into
collections when that makes ownership or navigation clearer.

Every workbook `README.md` should include:

## Purpose

What the workbook is for and what outcome it produces.

## Depends on

List repo-relative paths to other workbook folders this workbook reuses, or `None`.

## Contents

List the important files and folders and what each one is for.

## How to run/use

Document commands, prerequisites, expected inputs, expected outputs, and cleanup notes.

Raw knowledge uploads awaiting distillation belong in `docs/resources/_inbox/`, not here. Long-lived
committed source documents and binaries belong under `docs/resources/<area>/attachments/` with nearby
Markdown metadata or an index documenting purpose, provenance, area or owner, and update guidance.

See `playbooks/conventions/workbook-convention.md` for the full convention.
