# Writing Skills

## Purpose

Create new agent skills with proper structure, progressive disclosure, and bundled resources. Skills are reusable agent capabilities invoked by name and shared across Claude Code and Codex.

This playbook combines the dual-tool layout convention used by this template with the practical authoring wisdom from Anthropic's [`skill-creator`](https://github.com/anthropics/skills/tree/main/skills/skill-creator). The eval/benchmark/optimization machinery from skill-creator is intentionally omitted — it depends on Claude-specific subagent infrastructure not available here.

## Process

1. **Capture intent** — understand what the skill should enable, when it should trigger, and what the expected output is.
2. **Interview and research** — ask about edge cases, input/output formats, example files, success criteria, and dependencies. Pull context from the conversation history first; only ask the user to fill the gaps.
3. **Draft** — write the playbook (authoritative) and the two thin wrappers.
4. **Try it on 2–3 realistic prompts** — the kind of thing a real user would actually say. Refine based on what works and what doesn't.
5. **Review with user** — confirm coverage, clarity, and the right level of detail.

## Skill Structure

Every skill has three parts: a shared playbook and two thin wrappers. Skills are grouped into buckets (`engineering`, `productivity`, `misc`, `personal`) and enumerated in `.claude-plugin/plugin.json`.

```
playbooks/skills/<bucket>/<name>.md             # Shared workflow logic (authoritative)
skills/<bucket>/<name>/SKILL.md                 # Codex wrapper (thin)
.claude/skills/<bucket>/<name>/SKILL.md         # Claude Code wrapper (thin)
.claude-plugin/plugin.json                      # active-skill manifest (single source of truth)
```

The active set is enumerated in `.claude-plugin/plugin.json` (one `./skills/<bucket>/<name>` entry per skill). The sync and install scripts read that manifest — skills on disk but not in the manifest are treated as inactive. **The playbook is the single source of truth.** Wrappers just point to it. When changing a workflow, update the playbook first.

Optional additions in the playbook directory (when SKILL.md exceeds 500 lines or covers multiple distinct domains):

```
playbooks/skills/<bucket>/<name>/REFERENCE.md   # Detailed docs read on demand
playbooks/skills/<bucket>/<name>/EXAMPLES.md    # Usage examples
playbooks/skills/<bucket>/<name>/<domain>.md    # Per-domain reference (e.g., aws.md, gcp.md)
```

Optional additions in skill directories (when the skill needs deterministic helpers):

```
skills/<bucket>/<name>/scripts/helper.sh        # Codex utility scripts
.claude/skills/<bucket>/<name>/scripts/helper.sh # Claude utility scripts
```

## Anatomy of a skill

Borrowed from skill-creator:

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description required)
│   └── Markdown instructions
└── Bundled resources (optional, in the playbook directory)
    ├── scripts/    — Executable code for deterministic/repetitive tasks
    ├── references/ — Docs loaded into context as needed
    └── assets/     — Files used in output (templates, icons, fonts)
```

In this template, the bundled resources live next to the **playbook** (under `playbooks/skills/<bucket>/<name>/`), not next to the wrappers — both runtimes read them through the same path.

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
playbooks/skills/engineering/cloud-deploy.md   # Workflow + selection logic
playbooks/skills/engineering/cloud-deploy/aws.md
playbooks/skills/engineering/cloud-deploy/gcp.md
playbooks/skills/engineering/cloud-deploy/azure.md
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

## Wrapper templates

### Codex wrapper

```md
---
name: skill-name
description: Brief description of capability. Use when [specific triggers].
# argument-hint: "Free-text prompt for the user — only if the skill takes an argument"
---

# Skill Name

Read and follow:

- `playbooks/skills/<bucket>/<name>.md`

Keep this skill thin. The playbook is the shared workflow and should be updated first when the process changes.
```

### Claude Code wrapper

```md
---
name: skill-name
description: Brief description of capability. Use when [specific triggers].
# argument-hint: "Free-text prompt for the user — only if the skill takes an argument"
disable-model-invocation: true
---

Read and follow:

- `playbooks/skills/<bucket>/<name>.md`

Keep this skill thin. The playbook is the shared workflow and should be updated first when the process changes.
```

### Frontmatter fields

- `name:` — required; must match the directory name. Validated by `_base/scripts/check-skills-sync.sh`.
- `description:` — required; one-line summary surfaced to the user when picking skills. Include `"quoted trigger phrases"` for natural-language invocation; the sync script checks the same quoted set lives on both wrappers (Codex and Claude must not drift).
- `argument-hint:` — optional. Set when the skill expects free-text arguments from the user (e.g. a path, a topic, or a description). The value is the prompt the runtime shows to collect that argument — phrase it as a short question. Keep it identical on both wrappers. Use sparingly: most skills don't need it, and adding it to a skill that doesn't actually consume an argument creates noise.
- `disable-model-invocation: true` — Claude-only. Tells Claude to follow the playbook rather than improvising from the description. Always set on Claude wrappers; Codex wrappers don't need it.

### Keeping descriptions consistent across runtimes

The `check-skills-sync.sh` drift check extracts `"..."` substrings from each description and compares the sets. The two wrappers can phrase their descriptions differently, but the quoted-trigger set must match. Easiest approach: keep the descriptions identical on both wrappers; vary only the body if needed.

### Playbook template

```md
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

- [ ] Bucket chosen (`engineering`, `productivity`, `misc`, or `personal`)
- [ ] Playbook created in `playbooks/skills/<bucket>/<name>.md` (or `<bucket>/<name>/` directory if multi-file)
- [ ] Codex wrapper created in `skills/<bucket>/<name>/SKILL.md`
- [ ] Claude wrapper created in `.claude/skills/<bucket>/<name>/SKILL.md` with `disable-model-invocation: true`
- [ ] Skill added to `.claude-plugin/plugin.json` `skills` array (alphabetical within the bucket)
- [ ] Both wrappers point to the same playbook
- [ ] Description includes triggers ("Use when…") and is a little pushy about when to fire
- [ ] Quoted `"..."` trigger phrases in the description are identical between Codex and Claude wrappers (the sync script enforces this)
- [ ] If the skill takes user arguments, `argument-hint:` is set on both wrappers with the same prompt
- [ ] Wrapper SKILL.md under 50 lines (logic lives in playbook)
- [ ] Playbook body under 500 lines (split if longer)
- [ ] No time-sensitive info embedded in the skill body
- [ ] Consistent terminology throughout
- [ ] Concrete examples included where they clarify intent
- [ ] References go one level deep — clear pointers to bundled files, not three nested layers
- [ ] The "why" is explained for any non-obvious instruction
- [ ] `_base/scripts/check-skills-sync.sh` exits 0 and `_base/scripts/gen-skills-table.sh` has been run to update the skill table
