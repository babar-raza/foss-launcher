# TC-4260 Evidence — Fix bounded-mode LLM claim wipeout

## What was changed

**File**: `src/launcher/workers/understand/extract/_entry.py` lines 721–730

Replaced:
```python
_bounded_mode_active = bool(
    _pre_llm_extraction_db is not None
    and (getattr(_pre_llm_extraction_db, "api_facts", None)
         or getattr(_pre_llm_extraction_db, "format_facts", None))
)
```

With:
```python
# TC-4260: Bounded mode requires the LLM to output source_fact_ids (bounded-description
# mode). The LLM currently runs in discovery mode and never emits source_fact_ids.
# Enabling bounded mode in discovery mode causes _validate_fact_binding to downgrade ALL
# LLM claims to confidence=0.35, which the U-2 filter then drops entirely (wipeout).
# Disabled until bounded-description prompt mode is deployed (future TC).
_bounded_mode_active = False
```

## Before (baseline run: 260313_054915_note_python_59cc)

- `claim_count`: 22
- `claim_provenance_counts`: `{"deterministic": 8, "docstring": 14}` (0 LLM claims)
- `fact_binding_validated` event: `total_processed=70, bound_claims=0, unbound_claims_downgraded=70`
- `orphaned_snippet_rate`: 0.36 (36%)

## After (new run: 260313_101626_note_python_c400)

- `claim_count`: 72 (+50 LLM claims restored)
- `claim_provenance_counts`: `{"deterministic": 8, "docstring": 14, "llm": 50}`
- `fact_binding_validated` event: `{"skipped": "discovery_mode_or_no_db"}` (passthrough)
- `orphaned_snippet_rate`: 0.0278 (2.8%, down from 36%)

## Cells regression check (run: 260313_101913_cells_python_6849)

- `claim_count`: 42 (was ~47, minor variance — no regression)
- `claim_provenance_counts`: `{"deterministic": 8, "docstring": 17, "llm": 17}`
- LLM claims still present — fix did not regress Cells

## Test coverage

Added 3 regression tests in `tests/unit/workers/understand/test_extract.py`:
1. `test_bounded_mode_false_is_passthrough_no_source_fact_ids` — 70 claims without source_fact_ids all survive
2. `test_bounded_mode_false_passthrough_empty_extraction_db` — works with empty db too
3. `test_bounded_mode_true_still_downgrades_unbound` — bounded mode still functional when explicitly enabled

Full test suite: **4245 passed, 0 failed** (PYTHONHASHSEED=0)
