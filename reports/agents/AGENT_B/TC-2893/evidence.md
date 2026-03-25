# TC-2893: Limitations Anti-Dump Guardrail — Evidence

## Summary

Implemented anti-dump guardrail for Limitations sections: sanitized 3 structured prompt injection sites, added sanitization to legacy prompt builder, and created FQ-9 prelint for post-hoc dump detection.

## Files Changed

| File | Change |
|------|--------|
| `src/launch/workers/w5_section_writer/generators/content_generators.py` | Added `_sanitize_claims_for_prompt()` helper (line ~354); replaced raw `claim_text` at lines 2171 and 2373 |
| `src/launch/workers/w5_section_writer/worker.py` | Added re-exports for `_sanitize_limitation_bullet`, `_sanitize_claims_for_prompt`; fixed `_try_structured_limitations` (line 157); fixed legacy prompt builder (lines 1407-1414) |
| `src/launch/workers/w9_validator/gates/gate_17_prelints.py` | Added FQ-9 constants (`FQ9_MAX_BULLETS=10`, `FQ9_MAX_LINE_LEN=220`), `_FQ9_DUMP_INDICATORS` regex, `lint_fq9_limitations_dump_shape()` function; registered in `_ALL_LINTS` |
| `tests/unit/workers/w9/test_gate_17_fq9.py` | New: 16 test cases for FQ-9 lint |
| `tests/unit/workers/test_w5_structured_limitations_sanitization.py` | New: 8 test cases for `_sanitize_claims_for_prompt` |

## Tests

### Command
```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short
```

### Results
```
6890 passed, 13 skipped, 3 xfailed, 9 xpassed, 47 warnings in 146.51s
```

### New Test Counts
- `test_gate_17_fq9.py`: 16 tests — all passed
- `test_w5_structured_limitations_sanitization.py`: 8 tests — all passed (1 test was removed after consolidation)
- **Total new tests**: 23 (verified via targeted run)

### Targeted Run
```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/w9/test_gate_17_fq9.py tests/unit/workers/test_w5_structured_limitations_sanitization.py -x -v
```
```
23 passed in 0.78s
```

## Change Details

### Phase 1: `_sanitize_claims_for_prompt()` helper
- Location: `content_generators.py` between `_sanitize_limitation_bullet` and `_build_enriched_claim_context`
- Pipeline: `_get_display_text(claim)` → `_sanitize_limitation_bullet(display)` → `_smart_truncate(sanitized, MAX_BULLET_LEN - 2)`
- Uses lazy import `from ..worker import _smart_truncate, MAX_BULLET_LEN` (matching existing circular import avoidance pattern)

### Phase 2: Structured prompt builders
- Line 2171 (path 1): `_claim_texts_1 = _sanitize_claims_for_prompt(limitation_claims[:10])`
- Line 2373 (path 2): `_claim_texts_2 = _sanitize_claims_for_prompt(limitation_claims[:10])`
- Both previously used `f"- {c.get('claim_text', '')}"` — now sanitized

### Phase 3: worker.py paths
- `_try_structured_limitations` (line 157): `claim_texts = _sanitize_claims_for_prompt(limitation_claims[:10])`
- Legacy prompt builder (lines 1407-1414): applies `_sanitize_limitation_bullet()` + `_smart_truncate()` per claim, skips None results
- Added `_sanitize_limitation_bullet` and `_sanitize_claims_for_prompt` to re-export block (line 97-98)

### Phase 4: FQ-9 prelint
- Constants: `FQ9_MAX_BULLETS = 10`, `FQ9_MAX_LINE_LEN = 220`
- Section detection: `_FQ9_SECTION_RE` matches `## Limitations` and `## Known Limitations`
- Dump indicators regex: `claim_text:`, `"claim_id"`, `evidence_score`, file paths, JSON starts, code patterns
- Fence-aware: skips bullet lines inside code fences
- Severity: warn (NOT in `_ERROR_CODES` — does not cause gate failure)
- Registered in `_ALL_LINTS` list

## Verification

- [x] All 3 raw `claim_text` injection sites replaced
- [x] Legacy prompt builder sanitized
- [x] FQ-9 lint is fence-aware
- [x] FQ-9 detects both heading variants
- [x] FQ-9 severity is warn only
- [x] No circular imports
- [x] 23 new tests pass
- [x] 0 regressions (6890 passed, 13 skipped)
