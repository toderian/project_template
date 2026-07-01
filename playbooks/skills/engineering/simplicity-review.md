# Simplicity Review

## Purpose

Review proposed or existing code for avoidable complexity: unnecessary code, speculative
abstractions, hand-rolled standard library behavior, avoidable dependencies, wrappers around native
platform features, and verbose implementations that can be made smaller without weakening behavior.

This playbook adapts workflow ideas from
[`DietrichGebert/ponytail`](https://github.com/DietrichGebert/ponytail), copyright 2026
DietrichGebert, licensed under MIT. It keeps this repo's neutral engineering tone and does not import
Ponytail's lifecycle hooks, mode persistence, statusline behavior, benchmark scoreboard, or persona.

## Boundary

Simplicity review is about over-engineering, not correctness review.

- Do not use this as a substitute for security review, spec compliance review, accessibility review,
  performance profiling, or regression testing.
- Do not recommend removing trust-boundary validation, authorization checks, data-loss prevention,
  accessibility basics, observability required for operation, or user-requested behavior.
- Do not collapse code merely because fewer lines are possible. The smaller version must preserve
  behavior, edge-case correctness, readability, and the repo's established patterns.
- Prefer "do not build this yet" only for speculative requirements. If the user explicitly asks for
  the full version after the tradeoff is named, build it.

## Modes

Choose the narrowest mode that matches the request.

| Mode | Use when | Work performed |
| --- | --- | --- |
| `prebuild` | Before implementing a feature, fix, refactor, dependency, or interface. | Apply the minimal-correct-change ladder and recommend the smallest implementation path. |
| `diff-review` | Reviewing current changes or a PR for bloat. | Inspect the diff and list removable complexity without applying fixes. |
| `repo-audit` | The user asks what can be deleted or simplified in a repo. | Scan the codebase and rank simplification candidates by expected cut and risk. |
| `debt-ledger` | The user asks what deliberate simplifications were deferred. | Collect `simplicity:` comments and flag missing revisit triggers. |

## Minimal-Correct-Change Ladder

Run this ladder after you understand the task and the code it touches. The first rung that safely
holds is the preferred implementation.

1. **Does this need to exist now?** If the need is speculative, defer it and name the trigger that
   would make it real.
2. **Does this repo already have it?** Reuse local helpers, patterns, components, data access paths,
   test harnesses, and conventions before inventing new ones.
3. **Does the standard library solve it?** Use built-in language/runtime behavior when it is correct
   enough for the real requirement.
4. **Does the native platform solve it?** Prefer browser, database, OS, framework, or host-platform
   features over custom code or new packages when they satisfy the requirement.
5. **Does an installed dependency already solve it?** Reuse an existing dependency before adding one.
6. **Can the implementation be a clear small expression?** Use the compact form when it remains
   readable and edge-case correct.
7. **Only then write new code.** Keep the diff scoped to the current requirement and leave a small
   runnable check for non-trivial logic.

When two small options are available, choose the one that is more correct at the edge cases and more
consistent with the surrounding code. Minimal does not mean fragile.

## Review Tags

Use these tags for findings.

- `delete`: dead code, unused flexibility, speculative feature, or duplicate branch. Replacement:
  nothing.
- `stdlib`: hand-rolled behavior that the language/runtime already provides. Name the standard API.
- `native`: code or dependency replacing a browser, database, OS, framework, or platform feature.
  Name the feature.
- `yagni`: abstraction, configuration, interface, factory, adapter, or extension point with no
  current second use.
- `shrink`: same behavior can be expressed more directly with less code and no loss of clarity.
- `reuse`: local helper, component, pattern, or dependency already exists and should be used instead
  of new code.

## Process

### Prebuild

1. Identify the concrete requirement and the smallest code path it touches.
2. Inspect local patterns first. Search for existing helpers, components, utilities, APIs, tests, and
   dependency usage before suggesting new code.
3. Apply the ladder and stop at the first viable rung.
4. State the proposed implementation in one short paragraph:
   - what to build or delete
   - what local/stdlib/native path to reuse
   - what is intentionally deferred
   - what check will prove the behavior
5. If the user asked for a broader version, name the simpler alternative once, then proceed with the
   user's choice.

### Diff Review

1. Review only the changed lines and the immediate surrounding code needed to judge complexity.
2. Look for new files, abstractions, dependencies, options, wrappers, generic helpers, and tests that
   outsize the requirement.
3. Separate simplification findings from correctness/security findings. If you notice a real bug,
   note that it belongs in a normal review pass.
4. Rank findings by expected value: largest safe deletion first, then dependency removals, then local
   shrinks.

Output:

```markdown
## Simplicity Review

- <file>:L<line>: <tag>: <what to cut or replace>. <replacement or deferral trigger>.

net: -<N> lines possible, -<M> dependencies possible.
```

If there is nothing worth cutting:

```markdown
Lean already. Ship.
```

### Repo Audit

1. Start with dependency manifests, route/component registries, shared utilities, config files, and
   top-level source directories.
2. Search for common bloat signals:
   - interfaces, factories, adapters, or strategy maps with one implementation
   - wrappers that only delegate
   - config flags nobody sets
   - helper functions with one caller
   - custom implementations of language/runtime/platform APIs
   - dependencies used for one tiny feature
   - duplicated local patterns
3. Sample enough call sites to avoid false positives. A one-use abstraction may still be valid when
   it protects a hard boundary or matches a framework convention.
4. Return a ranked report. Do not apply fixes during an audit unless the user explicitly asks.

Output:

```markdown
## Simplicity Audit

1. <tag>: <what to cut or replace>. <replacement>. <paths>. Risk: <low|medium|high>.
2. ...

net: -<N> lines possible, -<M> dependencies possible.
```

### Debt Ledger

Deliberate simplifications can be documented with a `simplicity:` comment when the shortcut has a
known ceiling and a clear revisit trigger.

Format:

```text
simplicity: <known ceiling>; revisit when <trigger>
```

Examples:

```python
# simplicity: global lock is enough for one worker; revisit when workers run concurrently.
```

```ts
// simplicity: native date input covers current browsers; revisit if design requires custom ranges.
```

For `debt-ledger`, search tracked source files for comment markers such as `# simplicity:` and
`// simplicity:` while skipping dependency, build, generated, and VCS directories. Report each marker
with file, line, ceiling, trigger, and `no-trigger` when the revisit trigger is missing.

Output:

```markdown
## Simplicity Debt

- <file>:L<line>: <ceiling>. revisit: <trigger>.

<N> markers, <M> missing revisit triggers.
```

## Quality Bar

- Every finding is actionable and names a replacement, deletion, or revisit trigger.
- The report does not recommend removing required validation, security, accessibility, or
  user-requested behavior.
- Findings are grounded in observed code, not taste.
- The smallest path still includes a credible check for non-trivial logic.
- The output stays narrow: complexity findings here, broader correctness findings in the appropriate
  review workflow.
