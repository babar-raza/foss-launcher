# HG-09 — Safe Truncation in `_build_evidence_context()`

**Status**: Done
**Gap linkage**: G9 (evidence context truncates at char boundary, may split markdown table rows)
**Role**: Senior engineer. Drop-in, production-ready.
**Priority**: Medium

## Context

`_build_evidence_context()` in `extract/_entry.py` ends with:

```python
return result[:max_chars]
```

This truncates the string at an arbitrary character position. If truncation lands
inside a markdown table row (e.g., `| FBX | Yes | No |` gets cut to `| FBX | Yes | N`),
the LLM receives a malformed table that may confuse its parsing.

The evidence context is structured markdown with:
1. A header section (`## SOURCE-VERIFIED FACTS`)
2. A format matrix table (`| Format | Import | Export |`)
3. A limitations list
4. An API summary line
5. An install command

Truncation should occur at a newline boundary, preserving complete lines.
An incomplete table row is worse than a complete table with fewer rows.

## Scope

### Fix

1. Replace hard character truncation with newline-boundary truncation in `_entry.py`
2. Add a unit test verifying the fix

### Allowed paths

```
src/launcher/workers/understand/extract/_entry.py
tests/unit/workers/test_understand.py
plans/taskcards/TC-4015_safe_evidence_truncation.md
```

### Forbidden

All other paths.

## Implementation

Replace in `_build_evidence_context()`:

```python
# BEFORE
return result[:max_chars]

# AFTER
if len(result) > max_chars:
    # Find the last newline before the budget limit
    cutoff = result.rfind("\n", 0, max_chars)
    if cutoff > 0:
        result = result[:cutoff]
    else:
        # No newline found — hard truncate (very short budget)
        result = result[:max_chars]
return result
```

## Acceptance checks

### CLI
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -k "truncat" -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=no -q
```

### Tests
- `test_evidence_context_truncation_at_newline_boundary`:
  - Construct a long evidence context (many format rows) with max_chars=150
  - Verify the result ends at a newline (no mid-row cut)
  - Verify the result contains complete table rows only
- `test_evidence_context_truncation_no_newline_fallback`:
  - Construct a context with no newline in first 50 chars, max_chars=50
  - Verify hard truncation happens without crash

### Config respected end-to-end
- max_chars parameter still respected (result ≤ max_chars in all cases)

### No mock data in production paths
- Test uses real `_build_evidence_context()` call with FormatRecord instances

## Deliverables

1. 2-line fix in `_entry.py`
2. 2 unit tests
3. `plans/taskcards/TC-4015_safe_evidence_truncation.md`

## Hard rules

- Result must always be ≤ max_chars (safety invariant preserved)
- Empty result still returns "" (no change to empty path)
- `VERIFIED EVIDENCE takes precedence...` instruction is appended BEFORE truncation,
  so it may be truncated — this is acceptable (it's a soft instruction, not hard data)

## Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Robustness | No mid-row table cuts in any realistic scenario |
| Correctness | Budget respected; result ≤ max_chars always |
| Minimality | 2-line change; 2 tests |
| Testability | Both truncation paths independently tested |
| Correctness | LLM receives only complete lines |

## Now (runbook)

```
1. Read src/launcher/workers/understand/extract/_entry.py (end of _build_evidence_context)
2. Replace result[:max_chars] with rfind("\n") logic
3. Write 2 unit tests:
   - Short max_chars with multi-row table → verify ends at "\n"
   - Very short max_chars with no newline → verify hard truncate
4. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -k "truncat" -v
5. Run full suite
```
