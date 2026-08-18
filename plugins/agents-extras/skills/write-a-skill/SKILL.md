---
name: write-a-skill
description: "Create new agent skills with proper structure, progressive disclosure, and bundled resources. Use when the user wants to create, write, or build a new skill."
metadata:
  source: playbooks/skills/productivity/write-a-skill.md
  pack: dev-tooling
---

# Writing Skills

## Purpose

Create new agent skills with proper structure, progressive disclosure, and bundled resources. Skills are reusable agent capabilities invoked by name and shared across Claude Code and Codex.

This skill combines the plugin-skill layout used by this template's marketplace with the practical authoring wisdom from Anthropic's [`skill-creator`](https://github.com/anthropics/skills/tree/main/skills/skill-creator). The eval/benchmark/optimization machinery from skill-creator is intentionally omitted — it depends on Claude-specific subagent infrastructure not available here.

## Process

1. **Capture intent** — understand what the skill should enable, when it should trigger, and what the expected output is.
2. **Interview and research** — ask about edge cases, input/output formats, example files, success criteria, and dependencies. Pull context from the conversation history first; only ask the user to fill the gaps.
3. **Draft** — write the skill directly in its plugin.
4. **Try it on 2–3 realistic prompts** — the kind of thing a real user would actually say. Refine based on what works and what doesn't.
5. **Review with user** — confirm coverage, clarity, and the right level of detail.

## Skill Structure

Every skill is a single `SKILL.md` file (plus optional bundled resources) living directly under one of
the four plugins in this marketplace — `agents-core`, `agents-tasks`, `agents-extras`, `agents-personal`
— chosen by what the skill is for (core coding workflow, task/knowledge management, situational extras,
or personal writing/teaching workflows). Both Claude Code and Codex discover skills the same way: each
plugin manifest points at its `skills/` directory, and every subdirectory with a `SKILL.md` is a skill.
There is no separate authoring file and no generated wrapper — the frontmatter and body you write are
what both runtimes load.

```
plugins/<plugin>/skills/<name>/SKILL.md   # The skill: frontmatter + workflow body (authoritative, only copy)
plugins/<plugin>/skills/<name>/references/  # Optional: docs loaded into context as needed
plugins/<plugin>/skills/<name>/assets/      # Optional: templates and files used in output
plugins/<plugin>/skills/<name>/scripts/     # Optional: helper scripts
```

The skill's own frontmatter (`name`, `description`, optional `argument-hint`) is the single source of
its metadata — there is no separate pack/selection file to keep in sync. `name` must equal the skill's
directory name. Users opt into a whole plugin (`agents-core`, `agents-tasks`, `agents-extras`,
`agents-personal`) rather than selecting individual skills.

Optional additions in the skill directory (when SKILL.md exceeds 500 lines or covers multiple distinct domains):

```
plugins/<plugin>/skills/<name>/references/REFERENCE.md   # Detailed docs read on demand
plugins/<plugin>/skills/<name>/references/EXAMPLES.md    # Usage examples
plugins/<plugin>/skills/<name>/references/<domain>.md    # Per-domain reference (e.g., aws.md, gcp.md)
```

## Anatomy of a skill

Borrowed from skill-creator:

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description required)
│   └── Markdown instructions
└── Bundled resources (optional, alongside SKILL.md)
    ├── scripts/    — Executable code for deterministic/repetitive tasks
    ├── references/ — Docs loaded into context as needed
    └── assets/     — Files used in output (templates, icons, fonts)
```

In this template, bundled resources live next to `SKILL.md` inside the skill's own directory — both
Claude Code and Codex read them through the same path, since there is only one copy of the skill.

## Progressive disclosure

Skills load in three levels. Design with this hierarchy in mind:

1. **Metadata** (name + description) — always in context. ~100 words.
2. **SKILL.md / playbook body** — loaded when the skill triggers. Aim for under 500 lines.
3. **Bundled resources** — loaded only when needed. Unlimited; scripts can run without their source being read.

Patterns:

- Keep the playbook body under 500 lines. If approaching the limit, add a layer of hierarchy with clear pointers about where to read next.
- Reference files clearly from the playbook with guidance on **when** to read them.
- For large reference files (>300 lines), include a table of contents.

**Domain organization** — when a skill supports multiple domains/frameworks, organize by variant so the agent reads only the relevant file:

```
cloud-deploy/SKILL.md              # Workflow + selection logic
cloud-deploy/references/aws.md
cloud-deploy/references/gcp.md
cloud-deploy/references/azure.md
```

## Description requirements

The description is **the only thing the agent sees** when deciding which skill to load. It's surfaced in the system prompt alongside every other installed skill.

**Goal:** give the agent just enough info to know:

1. What capability this skill provides
2. When/why to trigger it (specific keywords, contexts, file types)

**Format:**

- Max 1024 chars
- Third person
- First sentence: what it does
- Second sentence: "Use when [specific triggers]"

**Be a little pushy.** Agents tend to *under*trigger skills — they default to handling things directly even when a skill would help. Counter this by naming concrete contexts the skill should fire in, including ones the user might not phrase explicitly.

**Good example:**

```
Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when user mentions PDFs, forms, or document extraction — even if they don't explicitly ask to "use a skill".
```

**Bad example:**

```
Helps with documents.
```

The bad example gives the agent no way to distinguish this from any other document skill.

## Writing style

Try to explain the **why** behind every instruction. Modern LLMs have good theory of mind — when given the reasoning, they go beyond rote instructions and actually solve the problem. When you find yourself writing `ALWAYS` or `NEVER` in all caps, or building rigid step-by-step structures, that's a yellow flag. Reframe and explain why the thing matters; the agent will handle edge cases better.

Other tips:

- Prefer the imperative form for instructions.
- Make the skill *general*, not narrowly tied to one example. Use examples to illustrate, not to define the boundary.
- Write a draft, then come back with fresh eyes and improve it.

### Writing patterns

**Defining output formats:**

```markdown
## Report structure
ALWAYS use this exact template:
# [Title]
## Executive summary
## Key findings
## Recommendations
```

**Examples:**

```markdown
## Commit message format
**Example 1:**
Input: Added user authentication with JWT tokens
Output: feat(auth): implement JWT-based authentication
```

## SKILL.md frontmatter

There is nothing to generate or regenerate — edit the skill's own frontmatter directly, in place. Both
Claude Code and Codex read the same `plugins/<plugin>/skills/<name>/SKILL.md`, so there is no
cross-runtime drift to manage.

- `name:` — required; must match the skill's directory name exactly.
- `description:` — required; a one-line (max 1,024 char) summary surfaced to the agent when picking
  skills. Include concrete trigger phrases. Keep it harness-neutral — write "the agent" or "the user
  wants to", not "Codex" or "Claude" by name, since the same file loads in both runtimes.
- `argument-hint:` — optional; set when the skill expects free-text arguments from the user, such as a
  path, topic, or description.
- `metadata:` — optional structured key/values (this template uses it for provenance, e.g. `source:`,
  `pack:`); not surfaced to the agent.

### Skill template

```md
---
name: skill-name
description: "Brief description of capability. Use when [specific triggers]."
# argument-hint: "Free-text prompt for the user — only if the skill takes an argument"
---

# Skill Name

## Purpose

[What this skill does and when to use it]

## Process

[Step-by-step workflow — explain the why for non-obvious steps]

## Quality bar

[What good looks like; review checklist]
```

## When to add scripts

Add utility scripts when:

- The operation is deterministic (validation, formatting, packaging)
- The same code would be generated repeatedly across invocations
- Errors need explicit handling

Scripts save tokens and improve reliability vs. generated code. **Strong signal:** if you've watched the skill run on a few real tasks and the agent independently writes the same helper each time, bundle that helper as a script and tell the skill to call it.

## When to split files

Split into separate files when:

- The playbook body exceeds ~500 lines
- The content has distinct domains (finance vs. sales schemas; aws vs. gcp deploys)
- Advanced features are rarely needed and can live one click deeper

## Iteration philosophy

When improving an existing skill based on real-world use:

1. **Generalize from the feedback.** A skill is meant to be invoked across many different prompts. If a stubborn issue keeps appearing, don't bolt on overfitted MUSTs — try a different metaphor or a different working pattern. Cheap to try, sometimes lands on something great.
2. **Keep the prompt lean.** Remove instructions that aren't pulling their weight. If transcripts show the agent wasting time on something unproductive, look for the part of the skill that's pushing it there and cut.
3. **Explain the why.** Terse rules produce brittle behavior. Reasoning produces robust behavior.
4. **Look for repeated work across runs.** If multiple invocations all independently write the same helper script or follow the same multi-step setup, lift that into a bundled script.

## Principle of Lack of Surprise

A skill's content must not surprise the user given its description. No malware, no exploit code, nothing that could compromise system security or facilitate unauthorized access. "Roleplay as X" skills are fine — deceptive or covert capability skills are not.

## Review checklist

After drafting, verify:

- [ ] Plugin chosen (`agents-core`, `agents-tasks`, `agents-extras`, or `agents-personal`)
- [ ] Skill created at `plugins/<plugin>/skills/<name>/SKILL.md` (with `references/`, `assets/`, or `scripts/` alongside it if needed)
- [ ] SKILL.md opens with `---` frontmatter setting `name` (matching the directory name) and `description` (and `argument-hint` if it takes arguments)
- [ ] Description includes triggers ("Use when…"), is a little pushy about when to fire, and is harness-neutral (no "Codex"/"Claude" by name)
- [ ] `claude plugin validate plugins/<plugin>` reports no warnings for the new skill
- [ ] SKILL.md body under 500 lines (split into `references/` if longer)
- [ ] No time-sensitive info embedded in the skill body
- [ ] Consistent terminology throughout
- [ ] Concrete examples included where they clarify intent
- [ ] References go one level deep — clear pointers to bundled files, not three nested layers
- [ ] The "why" is explained for any non-obvious instruction
