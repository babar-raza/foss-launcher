# AQ-02 — Implement Claim Distribution Wrap-Around

**Status**: Done
**Gap linkage**: GAP-02 (Critical — sections still get 0 claims causing hallucination)
**Role**: Senior engineer. Drop-in, production-ready.

## Context

The plan (Change C) explicitly requires `_distribute_claims()` to wrap around when `len(claims) < total_sections`, so every section gets at least one claim. Only the fallback text was changed — the distribution logic remains unchanged. Pages with 2 claims and 4 sections still produce 2 sections with 0 claims, triggering the constrained fallback text. While the fallback is better than before, the root fix is ensuring every section receives at least one claim.

Current code at `section_prompt.py:537-542`:
```python
def _distribute_claims(claims, section_idx, total_sections):
    if not claims or total_sections <= 0:
        return []
    return [c for i, c in enumerate(claims) if i % total_sections == section_idx]
```

When `len(claims) == 2` and `total_sections == 4`:
- Section 0 → claim 0 (2%4==0 ✓)
- Section 1 → claim 1 (1%4==1? No, 1%4==1 ✓)
- Section 2 → nothing (no i where i%4==2, since max i=1)
- Section 3 → nothing

## Scope

### Fix

When `len(claims) < total_sections`, use modular wrap-around: `claims[section_idx % len(claims)]`. When `len(claims) >= total_sections`, keep current round-robin.

### Allowed paths
- `src/launcher/workers/generate/section_prompt.py`
- `tests/unit/workers/generate/test_section_prompt.py`
- `tests/unit/workers/test_generate.py`

### Forbidden
- Any other file/path

## Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ tests/unit/workers/test_generate.py -q --tb=short` — all pass
- **Tests**: Test with 2 claims, 4 sections → every section gets exactly 1 claim
- **Tests**: Test with 6 claims, 3 sections → sections get 2 claims each (existing behavior preserved)
- **Tests**: Test with 0 claims → returns empty list (edge case preserved)
- **No mock data in production paths**: Uses real Claim objects

## Deliverables

1. Modified `_distribute_claims()` in `section_prompt.py` with wrap-around logic
2. New tests in `test_section_prompt.py`:
   - `test_distribute_claims_wraps_when_fewer_than_sections`
   - `test_distribute_claims_round_robin_when_enough`
   - `test_distribute_claims_empty`
3. Verify existing tests still pass

## Hard rules

- Keep public signatures unless justified; update all call sites
- No network in offline tests
- Deterministic runs (seed/stable ordering) where needed — important for wrap-around to be predictable
- No new deps without explicit justification
- Keep code/docs/tests in sync

## Review dimensions — what 5/5 means

| Dimension | 5/5 target |
|-----------|-----------|
| Correctness & spec alignment | Matches plan: "wrap around so every section gets at least one claim via claims[section_idx % n]" |
| Robustness | 0 claims → [], 1 claim + 5 sections → every section gets that 1 claim |
| Testability | All three distribution modes tested: fewer, equal, more claims than sections |
| Minimality | ~3 lines changed in one function + tests |
| Consistency | Round-robin order is stable and deterministic |

## Now (runbook)

```bash
# 1. Edit _distribute_claims in section_prompt.py
#    Replace the function body with:
#    if not claims or total_sections <= 0:
#        return []
#    if len(claims) < total_sections:
#        return [claims[section_idx % len(claims)]]
#    return [c for i, c in enumerate(claims) if i % total_sections == section_idx]

# 2. Add tests to test_section_prompt.py

# 3. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/test_section_prompt.py -v --tb=short

# 4. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short
```
