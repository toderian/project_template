# Writing Skills

## Purpose

Create new agent skills with proper structure, progressive disclosure, and bundled resources.

## Process

1. **Gather requirements** - ask user about:
   - What task/domain does the skill cover?
   - What specific use cases should it handle?
   - Does it need executable scripts or just instructions?
   - Any reference materials to include?

2. **Draft the skill** - create:
   - SKILL.md with concise instructions
   - Additional reference files if content exceeds 500 lines
   - Utility scripts if deterministic operations needed

3. **Review with user** - present draft and ask:
   - Does this cover your use cases?
   - Anything missing or unclear?
   - Should any section be more/less detailed?

## Skill Structure

Every skill has three parts: a shared playbook and two thin wrappers.

```
playbooks/<name>.md                    # Shared workflow logic (authoritative)
skills/<name>/SKILL.md                 # Codex wrapper (thin)
.claude/skills/<name>/SKILL.md         # Claude Code wrapper (thin)
```

The playbook is the single source of truth. Wrappers just point to it.

Optional additions in the playbook directory:

```
playbooks/<name>/REFERENCE.md          # Detailed docs
playbooks/<name>/EXAMPLES.md           # Usage examples
```

Optional additions in skill directories (when needed):

```
skills/<name>/scripts/helper.sh        # Codex utility scripts
.claude/skills/<name>/scripts/helper.sh # Claude utility scripts
```

## Codex Wrapper Template

```md
---
name: skill-name
description: Brief description of capability. Use when [specific triggers].
---

# Skill Name

Read and follow:

- `playbooks/<name>.md`

Keep this skill thin. The playbook is the shared workflow and should be updated first when the process changes.
```

## Claude Code Wrapper Template

```md
---
name: skill-name
description: Brief description of capability. Use when [specific triggers].
disable-model-invocation: true
---

Read and follow:

- `playbooks/<name>.md`

Keep this skill thin. The playbook is the shared workflow and should be updated first when the process changes.
```

The `disable-model-invocation: true` flag tells Claude to follow the playbook rather than generating its own approach.

## Playbook Template

```md
# Skill Name

## Purpose

[What this skill does and when to use it]

## Process

[Step-by-step workflow]

## Quality bar

[What good looks like, review checklist]
```

## Description Requirements

The description is **the only thing your agent sees** when deciding which skill to load. It's surfaced in the system prompt alongside all other installed skills. Your agent reads these descriptions and picks the relevant skill based on the user's request.

**Goal**: Give your agent just enough info to know:

1. What capability this skill provides
2. When/why to trigger it (specific keywords, contexts, file types)

**Format**:

- Max 1024 chars
- Write in third person
- First sentence: what it does
- Second sentence: "Use when [specific triggers]"

**Good example**:

```
Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when user mentions PDFs, forms, or document extraction.
```

**Bad example**:

```
Helps with documents.
```

The bad example gives your agent no way to distinguish this from other document skills.

## When to Add Scripts

Add utility scripts when:

- Operation is deterministic (validation, formatting)
- Same code would be generated repeatedly
- Errors need explicit handling

Scripts save tokens and improve reliability vs generated code.

## When to Split Files

Split into separate files when:

- SKILL.md exceeds 100 lines
- Content has distinct domains (finance vs sales schemas)
- Advanced features are rarely needed

## Review Checklist

After drafting, verify:

- [ ] Playbook created in `playbooks/`
- [ ] Codex wrapper created in `skills/<name>/SKILL.md`
- [ ] Claude wrapper created in `.claude/skills/<name>/SKILL.md`
- [ ] Both wrappers point to the same playbook
- [ ] Description includes triggers ("Use when...")
- [ ] Wrapper SKILL.md under 100 lines (logic lives in playbook)
- [ ] No time-sensitive info
- [ ] Consistent terminology
- [ ] Concrete examples included
- [ ] References one level deep
