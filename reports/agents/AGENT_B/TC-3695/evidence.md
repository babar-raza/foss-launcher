# TC-3695 Evidence Report

## Changes Made

### `gate_spec_leakage.py` — 3 new patterns
- `\brgUINT(?:32)?\b` — catches `rgUINT32` and `rgUINT`
- `JCID\.[A-Za-z]+` — catches JCID dot-notation (JCID.IsFileData, JCID.IsReadOnly)
- `\bxdr:[a-z]+\b` (IGNORECASE) — catches xdr:sp, xdr:Row, etc.

### `extract_claims.py` `_is_spec_fragment()` — 3 new patterns (TC-3695 block)
- Same 3 patterns as gate, so W2 classifier marks these claims as `visibility: internal`

## Test Results

```
tests/unit/workers/w9/gates/test_tc3695_spec_leakage_extended.py  10 passed
```

Full suite:
```
8734 passed, 13 skipped, 3 xfailed, 47 warnings in 149.17s
```
(+10 tests from 8724 baseline)
