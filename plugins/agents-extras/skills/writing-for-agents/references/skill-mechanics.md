# Skill mechanics

The skill-specific branch of [`agents-extras:writing-for-agents`](../SKILL.md): what changes when the document is a
skill. Everything else about writing it is the universal reference in `SKILL.md`.

## Invocation

Two choices, trading the two loads:

- A **model-invoked** skill keeps a `description`, so the agent can fire it autonomously and other
  skills can reach it. You can still type its name — model-invocation always _includes_ user reach; a
  description only ever adds agent discovery. That description is the skill's top-level context
  pointer, loaded at all times: permanent context load in exchange for discoverability. A
  model-invoked skill whose content is all reference is also the one home for shared reference,
  because another skill can invoke it. Mechanics: omit `disable-model-invocation`, and write a
  model-facing description carrying the trigger branches (the pointer rules in `SKILL.md` apply in
  full).
- A **user-invoked** skill strips the description from the agent's reach: only a human typing its
  name can invoke it, and no other skill can. Zero context load, but it spends cognitive load — you
  are the index that must remember it exists. Mechanics: set `disable-model-invocation: true`; the
  `description` becomes human-facing, a one-line summary with the trigger list stripped.

Pick model-invocation only when the agent must reach the skill on its own, or another skill must. If
it only ever fires by hand, make it user-invoked and pay no context load. This repo's own rule is
narrower: `disable-model-invocation: true` for side-effect-heavy skills a human should start.

Shared reference that two user-invoked skills both need can live in neither: with no descriptions,
neither can fire the other. Push it to a plain file both point at.

## Splitting by invocation

Split off a model-invoked skill when you have a distinct leading word that should trigger it on its
own (a trigger word you actually use in your prompts), or another skill must reach it. You pay
context load for the new always-loaded description, so that independent reach has to be worth it.
`agents-core:grilling` and `agents-extras:domain-modeling` are this repo's worked examples: primitives split out of
user-invoked routers (`agents-core:grill-me`, `agents-extras:grill-with-docs`) precisely so other skills could reach
them.

## Router skills

When user-invoked skills multiply past what you can remember, that piled-up cognitive load is cured by
a **router skill**: one user-invoked skill that names the others and when to reach for each, so the
human has one skill to remember instead of many. It can only hint, never fire them — user-invoked
skills have no description, so nothing but the human can reach them. The seeded `AGENTS.md` routing
table plays this role for downstream repos.

## Marketplace constraints

- Both harnesses load the same `plugins/<plugin>/skills/<name>/SKILL.md`, so keep every description
  harness-neutral: write "the agent" and "the user", never a product name or a product's UI.
- `name` must equal the directory name. Body ≤ 500 lines; longer material goes to `references/`,
  templates to `assets/`, executables to `scripts/`.
- Codex reads `disable-model-invocation: true` as its own no-implicit-invocation setting; there is no
  separate file to keep in sync.
- Name every skill by its full `plugin:skill` id (`agents-tasks:add-task`), never bare — including a
  skill in the same plugin as the one you are writing. Claude Code invokes skills by that id, so a
  bare name leaves the reader guessing a prefix, and the wrong guess is an "Unknown skill" error
  mid-task. Exempting same-plugin names does not work: a bare name among prefixed ones reads as an
  elision of *their* prefix. Codex users drop the prefix (`$add-task`).
