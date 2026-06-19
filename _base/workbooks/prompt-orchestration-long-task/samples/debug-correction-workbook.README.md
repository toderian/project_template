# Debug Correction Workbook

## Purpose

Reproduce a parser mismatch, apply one correction rule, and verify the sanitized regression case.

## Depends on

None.

## Contents

- `scripts/reproduce-mismatch.py` - runs the sanitized failing fixture.
- `scripts/verify-correction.py` - checks the corrected output.

## How to run/use

```bash
PYTHONDONTWRITEBYTECODE=1 python3 workbooks/debug-correction/scripts/reproduce-mismatch.py \
  --fixture workbooks/debug-correction/samples/sanitized-log.txt
```

```bash
PYTHONDONTWRITEBYTECODE=1 python3 workbooks/debug-correction/scripts/verify-correction.py \
  --fixture workbooks/debug-correction/samples/sanitized-log.txt
```

## Methodology

Keep the correction rule narrow, prove it with a regression fixture, and document remaining formats
that need separate tasks.
