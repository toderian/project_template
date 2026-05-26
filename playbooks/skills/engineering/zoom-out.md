# Zoom Out

## Purpose

Step up a layer of abstraction and produce a map of the relevant modules and callers, using the project's domain glossary. Use when starting work in an unfamiliar part of the codebase, or when a narrow trace has lost the bigger picture.

## Process

### 1. Identify the area

State the area of code under inspection — typically a file, a module, or a feature surface that the user has named or that the current task touches.

### 2. Read the glossary first

Before reading code, read `docs/resources/CONTEXT.md` (or the relevant glossary from
`docs/resources/CONTEXT-MAP.md` if the repo has multiple contexts). If only root `CONTEXT.md` exists,
treat it as a pointer or legacy fallback. The glossary fixes the canonical names — using them keeps the
map legible.

### 3. Produce the map

Output a structured summary, not a tour:

- **Purpose** — what this area is for, one sentence, in domain terms.
- **Inputs** — what callers reach into this area, and what shape the calls take. Cite specific files where the call sites live.
- **Outputs** — what this area produces; what downstream code consumes it.
- **Internal shape** — the 3–7 modules / files / classes that matter, each with a one-line role description. Skip uninteresting plumbing.
- **Edges and seams** — boundaries with adjacent contexts (database, UI, other services), with one line about how the boundary is shaped.
- **Open questions** — anything you couldn't resolve from the code alone.

### 4. Use the glossary in the map

Every term that appears in `docs/resources/CONTEXT.md` should appear in **bold** the first time it's
used in the map. If the code uses a different word than the glossary canonicalises, note the alias
(e.g. "`Account` in code = **Customer** in the glossary").

### 5. Stop at the map

This skill produces a map. It does not propose changes, write code, or critique the design. If the map surfaces a real architectural problem, mention it under "Open questions" and let the user decide whether to follow up with `improve-codebase-architecture` or `diagnose`.

## Quality bar

A good zoom-out:

- Fits on one screen.
- Reads in the project's domain language, not generic CS terms.
- Names specific files for the non-obvious claims.
- Surfaces edges and seams clearly enough that someone could pick the right next file to read.
