---
name: exploratory-test
description: "Test a running product end to end against its design tree, one checkable statement per scenario: drive the real interface, replay each mismatch, have an independent refuter try to explain it away, and file what survives as an inbox idea with a fingerprint. Use when the user says \"exploratory testing\", \"e2e loop\", \"bug hunt\", \"dogfood the product\", \"test it like a user\", wants agents to find bugs continuously, or wants a design tree checked against the running product."
argument-hint: "Which product or module, and how many cells?"
metadata:
  pack: quality
---

# Exploratory Test

## Purpose

Find where a running product and its design tree disagree, without a person steering each test. The
expected result of every scenario comes from a design leaf (`docs/resources/<area>/design/`). What the
product does is never the source of an expected value, and the model's own opinion never files a bug:
an agent exploring freely reports mostly false findings.

Each confirmed mismatch means the product is wrong or the leaf is wrong. Both are worth filing.

## Before the first run

The repo owns a small harness; this skill does not ship one. It needs the four things in
[references/harness.md](references/harness.md): a command that starts the product locally with test
data, a scenario helper that captures evidence, a rule that keeps runs from disturbing each other, and
a limit, enforced outside the model, on what the product under test can reach. Stop and build the
harness with the user if one is missing. Do not point the loop at a shared or production deployment.

Build the coverage ledger: `at explore build`. A cell is one checkable statement. Rules in design
leaves with a Check line and `Holds: Yes` become cells by themselves; a rule that holds partly or is a
target is a known gap and is left out. Other statements (a permission matrix, a list of refusals) go
into `cells.tsv` beside the ledger, written by a script the repo owns.

## One iteration

1. **Pick.** `at explore next N` prints the cells run least recently, with the leaf and the expected
   result of each.
2. **Charter.** Read the leaf. Write the scenario with the expectation and its leaf stated before any
   action. Code may be read to find the screen or route that exercises the statement, never to decide
   what the result should be.
3. **Drive** the real interface through the harness. One verdict per cell:
   - `pass`: the observed result is the expected one.
   - `mismatch`: the state under test was reached and the result differs.
   - `blocked`: the state was not reached (no data, a control not found, a timeout). Blocked is
     neither a pass nor a bug; say what was missing.
4. **Control.** A cell that expects a refusal also shows that a role holding the permission gets
   through on the same route. Skip the control when the operation destroys shared data.
5. **Replay** a mismatch once from a fresh sign-in with the same steps. A different second result
   makes the verdict `blocked`, with both results noted.
6. **Write the finding**: steps a person can repeat, the expected result with the quoted leaf
   statement, the actual result, the route, what was ruled out. State the narrowest true mismatch.
   The explorer never calls a finding confirmed.
7. **Refute.** Hand the finding and the leaf, and nothing else, to a fresh agent with the brief in
   [references/refuter-brief.md](references/refuter-brief.md). Its verdict is `confirmed`, `refuted`
   or `harness`.
8. **File** a confirmed finding: `at explore fingerprint CELL ROUTE "<short error phrase>"`, then
   `at explore known <fingerprint>`. If it is new, capture it with `agents-tasks:capture-idea` and end
   the idea with the line `Fingerprint: <value>`. At most five per run; list the rest in the run
   summary.
9. **Record** every cell, blocked ones included: `at explore record CELL VERDICT [FINGERPRINT]`. A
   cell the harness cannot exercise at all is `untestable` and is skipped from then on.

Run cells in parallel only when the harness says scenarios cannot disturb each other.

## Leads

An explorer reports what it noticed outside its cell as a side observation, not as a finding. When
several explorers report the same one, test it as a cell of its own through the real control, with a
leaf statement as the oracle. A lead with no leaf statement goes to the user as a question.

## Stop

Stop after the planned cells, after five filed findings, or when three cells in a row are blocked for
the same reason: then the harness is the problem, not the product.

## After the run

- Give the user the counts (pass, blocked, untestable, filed), the findings with their evidence
  folders, and the harness faults met.
- The user classifies each finding as bug, expected or harness fault. Write an expected or harness
  verdict into `decisions.tsv` (fingerprint, decision, date, note) so it is not filed again. The share
  the user rejects is the loop's false-positive rate; report it, never your own estimate.
- An accepted bug becomes a plain regression test with no model in it, whose expected value comes from
  the leaf. Never freeze what the product did.

## Quality bar

- Every scenario names the leaf statement it tests before it acts.
- Every filed finding has a replay and a refuter verdict in its evidence folder, and a fingerprint in
  its text.
- No finding is filed twice, and none is filed from a console message or a model judgement alone.
- Raw evidence (traces, screenshots, logs) stays out of git; the filed text is sanitized.
- A wrong leaf is filed like a wrong product.
