---
name: google-docs-refine
description: "Refines text through a reusable Google Docs workstation using connector staging, visible browser automation, and human-assisted Gemini actions. Use when the user asks to formalize, rephrase, polish, shorten, or otherwise refine text in Google Docs."
argument-hint: "[text or file] [Google Doc URL] [refinement instruction]"
disable-model-invocation: true
metadata:
  source: project_technical_writing/playbooks/skills/personal/google-docs-refine.md
  pack: personal
---

# Google Docs Refine

## Purpose

Use Google Docs as a reusable text-refinement workstation: stage source text in a
Google Doc, let the user run Google Docs Gemini writing tools such as formalize,
rephrase, polish, shorten, or a custom prompt in the visible browser, then read
the resulting text back for the agent.

This skill deliberately separates three jobs:

1. Reliable staging and extraction through Google Docs API/MCP when available.
2. Visible-browser automation for the Google Docs web UI.
3. Human confirmation for the built-in Gemini rewrite UI, because public Docs
   API and common connector surfaces expose document editing, not the product's
   internal AI rewrite action.

## Inputs

Accept any of these:

- Plain text in the prompt.
- A local file path containing the text to refine.
- A Google Doc URL to use as the workbench document.
- A refinement instruction, for example "formalize", "make academic", "shorten",
  or a custom prompt.

If the user does not provide a workbench Google Doc URL, create or ask for one.
Prefer an existing disposable workbench doc for repeated use so the same browser
tab and login session can be reused.

## Route Selection

Use this order:

1. **Connector-assisted route**: When a Google Drive/Docs connector is available,
   use it for creating a workbench doc, clearing/replacing document text, and
   reading the final text. This is safest for indexes and extraction.
2. **Browser workstation route**: Use `scripts/google-docs-refine.sh` when the
   user wants the visible Google Docs UI, when connector writes are unavailable,
   or when the workflow depends on Docs Gemini UI controls.
3. **Manual fallback**: If browser automation cannot focus Docs or read the
   clipboard, keep the browser open, put the source text or prompt on the
   clipboard, and ask the user to paste or copy once.

Do not claim that MCP or the Docs API can invoke "Help me write", "Formalize",
"Rephrase", or Gemini-in-Docs unless the current tool surface explicitly exposes
such an action. Standard Docs API `batchUpdate` can insert, delete, and style
document content; it is not the same as invoking Google Docs' built-in rewrite UI.

## Browser Workstation

Use the bundled script:

```bash
scripts/google-docs-refine.sh \
  --url "https://docs.google.com/document/d/..." \
  --input source.txt \
  --prompt "Formalize this for an academic paper while preserving citations." \
  --auto-refine more-formal \
  --output refined.txt
```

For text from stdin:

```bash
printf '%s\n' "$TEXT" | scripts/google-docs-refine.sh \
  --url "https://docs.google.com/document/d/..." \
  --input - \
  --prompt "Rephrase in a more formal style." \
  --auto-refine more-formal \
  --output refined.txt
```

The script opens a persistent visible Chrome profile under
`~/.cache/google-docs-refine-suite/chrome-profile`. It installs Playwright into
`~/.cache/google-docs-refine-suite/npm` on first use, not into the repo. The user
signs in to Google in that profile once; do not store or request Google
credentials in repo files. It launches Chrome with sandboxing enabled by default;
use `--no-chromium-sandbox` only when Chrome cannot start in the local
environment.

The script stages text into the document and copies the refinement prompt to the
clipboard if one is provided. With `--auto-refine`, it drives the visible Google
Docs Gemini refine UI, accepts the result, and copies the final document text
back to the requested output file. Supported automatic modes are `more-formal`,
`rephrase`, `shorten`, `elaborate`, `bulletise`/`bulletize`, and
`summarise`/`summarize`.

Without `--auto-refine`, the script pauses. The user should run the Google Docs
Gemini rewrite UI in the browser and press Enter in the terminal when the final
text is in the document. It restores the original clipboard by default after
extraction; pass `--leave-clipboard` when the final text should remain on the
clipboard.

To attach to a reusable Chrome window instead of launching the managed profile,
start Chrome yourself with a non-default user data directory and a localhost
debugging port, then pass `--cdp-endpoint`:

```bash
google-chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/.cache/google-docs-refine-suite/cdp-profile"

scripts/google-docs-refine.sh \
  --cdp-endpoint http://127.0.0.1:9222 \
  --url "https://docs.google.com/document/d/..." \
  --input source.txt \
  --prompt "Make this more formal." \
  --output refined.txt
```

Keep the debugging port bound to localhost. Do not expose it on a network
interface.

## Connector-Assisted Workflow

When the Google Drive connector is available:

1. Resolve the exact workbench Google Doc URL or document id.
2. Read the doc before writing when indexes matter.
3. Replace the body text with the source text through connector-supported Docs
   operations, or use the browser script for staging if the connector write
   permission is unavailable.
4. Open the same doc in the browser script with `--no-stage` and the prompt so
   the user can run the built-in Docs Gemini UI.
5. After the user confirms the rewrite is inserted, read the final text through
   the connector when possible. Use browser clipboard extraction only as a
   fallback.

If connector readback and browser clipboard output differ, trust the connector
for final text unless the user points out visible UI content that has not synced.

## Quality Bar

- Never expose, store, or summarize Google credentials. Use the browser session
  profile or the already-authenticated connector only.
- Use a disposable or explicitly selected workbench document, because staging
  replaces the document body.
- Preserve citation markers and technical symbols in the prompt when relevant.
- Return the refined text from the output file or connector readback, not a
  paraphrase reconstructed from memory.
- State clearly when the final rewrite step was human-confirmed in the browser
  rather than invoked through an API.
