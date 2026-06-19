# Model Eval Routing Workbook

## Purpose

Run a small deterministic evaluator slice against sanitized public fixtures before using private
benchmarks.

## Depends on

None.

## Contents

- `scripts/run-small-eval.py` - executes the synthetic evaluation fixture.
- `samples/public-fixture.jsonl` - safe input examples.
- `outputs/README.md` - describes generated reports.

## How to run/use

```bash
PYTHONDONTWRITEBYTECODE=1 python3 workbooks/model-eval-routing/scripts/run-small-eval.py \
  --fixture workbooks/model-eval-routing/samples/public-fixture.jsonl \
  --output .local/workbooks/model-eval-routing/small-eval.json
```

```bash
PYTHONDONTWRITEBYTECODE=1 python3 workbooks/model-eval-routing/scripts/summarize-failures.py \
  --input .local/workbooks/model-eval-routing/small-eval.json
```

## Methodology

Use the smallest fixture first, summarize failures, then decide whether private benchmark access is
needed for the next slice.
