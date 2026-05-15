# Grill Me

## Purpose

Interview the user relentlessly about every aspect of a plan, design, or decision until reaching shared understanding. Surface hidden assumptions, missing constraints, and unresolved dependencies.

## Workflow

### 1. Set scope

Ask the user what they want to be grilled on — a plan, a design, a feature, a decision.

### 2. Walk the design tree

Move through the following categories one question at a time. For each question, provide your recommended answer so the user can accept, modify, or reject it.

**Categories** (adapt order to what matters most for the topic):

- **Scope**: what is included, what is explicitly excluded, what is the MVP
- **Constraints**: time, budget, compatibility, policy, performance, security
- **Dependencies**: what must exist before this can work, what breaks if this changes
- **Edge cases**: unusual inputs, failure modes, concurrency, empty states, scale limits
- **Rollback**: what happens if this fails in production, how do you undo it
- **Prior art**: has this been tried before, what can be reused, what failed last time
- **Users**: who uses this, how do they discover it, what do they expect

### 3. Resolve dependencies between decisions

If a later answer contradicts or depends on an earlier one, flag it and resolve before moving on.

### 4. Explore the codebase when possible

If a question can be answered by reading existing code, tests, or docs — explore the codebase instead of asking the user. Reserve questions for decisions only the user can make.

### 5. Converge

Stop grilling when:

- all categories above have been covered for the topic
- no question generates new information or changes a prior answer
- the user says they are satisfied

### 6. Summarize

After the session, produce a brief summary:

- **Decisions made**: concrete answers that were locked in
- **Open questions**: anything that was deferred or unresolved
- **Risks identified**: concerns that surfaced during grilling
