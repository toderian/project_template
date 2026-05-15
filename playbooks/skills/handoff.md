# Handoff

## Purpose

Compact the current conversation into a handoff document so a fresh agent (in a later session) can continue the work without replaying the whole transcript.

## Process

### 1. Choose a destination

Generate a tempfile path with `mktemp -t handoff-XXXXXX.md`. Read that path before writing to it (the file is created empty by `mktemp`; reading it confirms the path and avoids silent overwrite if a tool requires read-before-write).

### 2. Summarise the conversation

The doc should let a fresh agent continue without having to re-read the transcript. Include:

- **Goal**: one paragraph — what the user is trying to accomplish.
- **State**: where the work is right now — what's been decided, what's been built, what's still pending.
- **Key context**: durable facts the next agent needs (file paths, branch name, services touched, environments).
- **Next step**: the single next action the receiving agent should take.
- **Open questions / blockers**: anything currently waiting on the user or on an external party.

### 3. Reference, don't duplicate

Do **not** copy content that already lives in another durable artifact — PRDs, plans, ADRs, GitHub issues, commits, diffs, design docs. Reference them by path or URL instead. The handoff is a pointer, not a clone.

If a relevant artifact does not yet exist but should, surface that gap in the "Open questions" section rather than inlining its content.

### 4. Suggest the right skills

End with a short "Suggested skills" section naming the playbooks the next session is likely to invoke (`planning-workflow`, `spec-workflow`, `tdd`, `triage-issue`, etc.). Use the names; the next agent will pick them up via the standard skill loader.

### 5. Tailor to the user-supplied argument

If the user invoked the skill with a free-text argument (the `argument-hint:` prompt asks "What will the next session be used for?"), treat that argument as the lens for the handoff. A handoff aimed at "finish the migration" leans heavier on State + Next step; one aimed at "onboard a teammate" leans heavier on Goal + Key context.

If no argument is given, write the handoff as a general-purpose continuation note.

## Quality bar

A good handoff:

- Fits on a single screen.
- Stands alone — the receiving agent does not need the prior transcript to act.
- Points to the next concrete step, not a vague "continue the work".
- Cites artifacts by path/URL rather than inlining their bodies.
