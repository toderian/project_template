---
name: write-a-skill
description: "Create or edit a skill in this plugin marketplace: pick the plugin, write SKILL.md and its bundled resources, validate. Use when the user wants to create, write, or build a new skill, or restructure an existing one."
metadata:
  source:
    - "github.com/mattpocock/skills (original, since renamed/reworked upstream)"
    - playbooks/skills/productivity/write-a-skill.md
    - https://github.com/anthropics/skills/tree/main/skills/skill-creator
  pack: dev-tooling
---

# Write a Skill

## Purpose

Create a reusable agent skill in this marketplace — invoked by name and shared across Claude Code and
Codex — with the right structure, the right plugin, and a description that actually fires.

This skill covers the **mechanics**: layout, frontmatter, bundled resources, validation. The
**writing** is `agents-extras:writing-for-agents`: context pointers, the two loads, progressive disclosure,
completion criteria, leading words, pruning. Read it first; everything below assumes it.

## Process

0. **Read `agents-extras:writing-for-agents`** (and its references/skill-mechanics.md for the invocation choice).
1. **Capture intent** — what the skill should enable, when it should trigger, what the output is.
2. **Interview and research** — edge cases, input/output formats, example files, success criteria,
   dependencies. Pull from the conversation first; ask the user only for the gaps. Run `agents-core:grilling`
   when the gaps are several and interdependent.
3. **Draft** — write the skill directly in its plugin.
4. **Try it on 2–3 realistic prompts** — the kind of thing a real user would actually say. Refine on
   what works and what does not.
5. **Review with the user** — coverage, clarity, and whether the detail level earns its load.

## Where a skill lives

Every skill is a single `SKILL.md` (plus optional bundled resources) under one of the four plugins,
chosen by audience:

| Plugin | Take it when the skill is |
|---|---|
| `agents-core` | core coding workflow — always enabled downstream, so the bar is highest |
| `agents-tasks` | task ledger, knowledge base, workbooks, cross-repo work |
| `agents-extras` | situational review/GitHub/UI/authoring toolkit |
| `agents-personal` | personal writing, teaching, niche migrations |

```
plugins/<plugin>/skills/<name>/SKILL.md     # the skill: frontmatter + body (only copy)
plugins/<plugin>/skills/<name>/references/  # docs loaded on demand
plugins/<plugin>/skills/<name>/assets/      # templates and files used in output
plugins/<plugin>/skills/<name>/scripts/     # helper scripts
```

Both harnesses discover skills the same way: each plugin manifest points at its `skills/` directory,
and every subdirectory with a `SKILL.md` is a skill. There is no authoring file, no generated
wrapper, and no pack/selection file to keep in sync — `scripts/build.py` does not touch skills at all.
Users opt into a whole plugin, never an individual skill.

## Frontmatter

Edit the skill's own frontmatter in place; it is the single source of its metadata.

- `name:` — required; must equal the directory name exactly.
- `description:` — required; ≤ 1,024 characters, harness-neutral, carrying the trigger branches. It is
  the only thing the agent sees when picking skills. Write it under the context-pointer rules in
  `agents-extras:writing-for-agents`.
- `disable-model-invocation: true` — only for side-effect-heavy skills a human should start, or a
  router. The description then becomes human-facing.
- `argument-hint:` — optional; set when the skill expects free-text arguments (a path, topic, slug).
- `metadata:` — optional; this repo uses it for provenance (`source:`, `pack:`). Keep `source` when
  moving or adapting an existing skill, and name the upstream commit when the skill is adapted from
  one.
- `paths:` — optional glob list scoping the skill to part of the repo (see `agents-tasks:task-ledger`).

### Template

```md
---
name: skill-name
description: "What it does. Use when <specific triggers>."
---

# Skill Name

## Purpose

[what this does and when to use it]

## Process

[the ordered steps, each ending on a checkable completion criterion]

## Quality bar

[what good looks like]
```

## When to add scripts

Bundle a script when the operation is deterministic (validation, formatting, packaging), when the same
code would otherwise be generated on every invocation, or when errors need explicit handling. Scripts
save tokens and improve reliability. **Strong signal:** if you have watched the skill run a few times
and the agent independently writes the same helper each time, bundle that helper and have the skill
call it. Constraints: bash, `python3` (stdlib only), and `jq` — no new runtime dependencies.

## Principle of Lack of Surprise

A skill's content must not surprise the user given its description. No malware, no exploit code,
nothing that could compromise system security or facilitate unauthorized access. "Roleplay as X"
skills are fine; deceptive or covert capability skills are not.

## Quality bar

- [ ] Plugin chosen by audience; `agents-core` stays small because it is always enabled
- [ ] `plugins/<plugin>/skills/<name>/SKILL.md` exists, `name` matches the directory
- [ ] Description carries triggers, is harness-neutral, ≤ 1,024 chars, and passes the context-pointer
      rules in `agents-extras:writing-for-agents`
- [ ] Body under 500 lines; on-demand material disclosed to `references/`
- [ ] Every step ends on a completion criterion the agent can check
- [ ] No no-op lines, no duplicated meaning, no restatement of what the environment already says
- [ ] The "why" is explained for any non-obvious instruction
- [ ] `claude plugin validate plugins/<plugin>` reports no warnings
- [ ] `bash scripts/tests/run-all.sh` passes
- [ ] `README.md` skill counts and the seeded `AGENTS.md` routing table updated if the skill is
      user-facing
