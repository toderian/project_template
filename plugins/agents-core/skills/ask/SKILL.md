---
name: ask
description: "Put a decision to the user so it can be answered without scrolling back: context, the question, options with consequences, what each affects, a recommendation, and what happens with no answer; as an interactive choice menu where the harness has one. Use when you are about to ask the user a question or need a decision, when a run parks questions for the owner, or when the user says a question lacks context, asks \"what does this affect\", \"what do you recommend\", or asks you to re-ask."
argument-hint: "Which open question should I re-ask? (default: every question still open in this conversation)"
metadata:
  pack: core
---

# Ask

## Purpose

A question the user cannot answer from the question alone costs a round trip: they ask for context,
you answer, they decide. Write every question so that a reader who has not seen the rest of the
conversation can decide from it.

Invoked by the user with no argument, re-ask **every** question still open in this conversation in
the format below, the ones you asked badly included.

## Process

### 1. Decide whether to ask at all

- A fact you can find (code, tests, docs, a command, the web): find it, do not ask.
- A choice that is cheap to undo and has a conventional answer: take it, say so in one line.
- A decision already made in this conversation, the task file or a `Ruling:` / `Decision:` line: use it.
- What is left is the user's: a trade-off between things they own (scope, risk, money, time, other
  people), an action that is hard to undo, or an authorisation.

Done when every remaining question passes the last test.

### 2. Batch

Ask every question you can ask now in one message, numbered. A question whose answer depends on
another open question waits for the next round. Order by what unblocks the most work.

### 3. Write each question

```markdown
### Q1: <the decision, ≤ 10 words>

**Context:** <what you were doing, what you found, why the repo cannot decide it. 2–4 sentences.
Full names for files, tasks, hosts and jobs; nothing that needs earlier chat to resolve.>

**Question:** <one sentence ending in a question mark>

**Options:**
- **A: <label> (recommended)** — <what happens next; what it costs>
- **B: <label>** — <what happens next; what it costs>

**Affects:** <files, behaviour, tasks, other people; reversible or not>

**Recommendation:** A, because <one clause>. Cost if wrong: <one clause>.

**If you don't answer:** <what I do meanwhile, and what waits>
```

- Two to four options, mutually exclusive, the recommended one first. "Do nothing" is an option
  when it is a real choice.
- An option states its consequence, not its mechanism: "the scan restarts from zero, about 20
  minutes", not "pass `--force`".
- No recommendation is allowed only when you can say what you would need to know to have one.
- One decision per question. Split "A, and should I also B?".

### 4. Deliver

- **The harness has a structured question tool** (an interactive menu): use it. One menu question per
  decision, up to the tool's limit per call, further questions in a second call. The user may see
  only the dialog, so the question text itself carries the Context and the question, each option's
  description carries its consequence, and the recommended option is first and labelled. Put
  `Affects` and `If you don't answer` into the question text when they change the choice.
- **No such tool:** the Markdown block above, then one line that says how to answer
  (`Reply e.g. "1A 2B"`).

After the answers: restate each decision in one line, record it where the work keeps decisions (the
task file, or a `Decision:` line in the run state), and continue.

## Quality bar

- Each question can be answered by someone who reads only that question.
- Every option names what happens and what it costs; exactly one is recommended.
- Nothing asked that a lookup, a convention or an earlier answer already settles.
