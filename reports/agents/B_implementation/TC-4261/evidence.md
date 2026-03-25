# TC-4261 Evidence — Fix howto_article sufficiency + LLM-failure self-review gate

## Fix 1: howto_article api_verified exclusion

**File**: `src/launcher/workers/understand/worker.py`

Added `non_docstring_api_verified` after `non_docstring_verified` definition (~line 232):
```python
non_docstring_api_verified = [
    c for c in api_verified
    if getattr(c, "claim_source", "docstring") != "docstring"
]
```

Changed `howto_article` `evidence_sufficient` from:
```python
evidence_sufficient=has_op_snippets and (len(non_docstring_verified) >= 2 or len(api_verified) >= 2),
```
To:
```python
evidence_sufficient=has_op_snippets and (len(non_docstring_verified) >= 2 or len(non_docstring_api_verified) >= 2),
```

Also aligned the `_missing` check from `len(api_verified) < 2` to `len(non_docstring_api_verified) < 2`.

## Fix 2: LLM-failure self-review gate

**File**: `src/launcher/workers/understand/worker.py` (after `low_claim_count` check in `self_review`)

Added HIGH-severity finding `llm_failure_claim_wipeout` that fires when:
- `_public_class_count >= 2` (non-trivial API surface — LLM would have been called)
- `_llm_claim_count == 0` (no LLM claims survived)
- `_other_claim_count > 0` (docstring/deterministic claims exist, proving pipeline ran)

Uses `claim_mix["llm_count"]` and `claim_mix["counts"]` which are always available from the bundle. No dependency on external files.

## Pilot verification (Note run: 260313_101626_note_python_c400, after TC-4260)

- `claim_provenance_counts`: `{"llm": 50, "docstring": 14, "deterministic": 8}`
- `howto_article.evidence_sufficient`: `True` (now backed by 50 LLM claims + op snippets)
- `howto_article.verified_claim_count`: 21 (was 0 before TC-4260)
- LLM-failure gate would NOT fire (50 LLM claims present)

## Before state (baseline run: 260313_054915_note_python_59cc)

Without TC-4260, Note had:
- `claim_provenance_counts`: `{"deterministic": 8, "docstring": 14}` (0 LLM claims)
- `howto_article.evidence_sufficient`: `True` (false positive — driven by docstring api claims)
- If the LLM-failure gate existed, it would have fired: 0 LLM claims + 3 public classes >= 2

## Test coverage

Added to `tests/unit/workers/test_understand.py`:

**TestHowtoArticleSufficiencyDocstringExclusion** (3 tests):
1. `test_howto_insufficient_when_all_api_claims_are_docstring` — verifies the fix (was True before)
2. `test_howto_sufficient_with_real_llm_api_claims` — LLM claims + op snippets = sufficient
3. `test_howto_insufficient_mixed_docstring_and_no_op_snippets` — no op snippets = insufficient

**TestSelfReviewLLMFailureGate** (3 tests):
1. `test_llm_failure_gate_fires_when_no_llm_claims` — HIGH finding when 0 LLM + 2+ classes
2. `test_llm_failure_gate_does_not_fire_when_llm_claims_present` — no false positive
3. `test_llm_failure_gate_does_not_fire_for_small_api_surface` — quiet for tiny repos

Full test suite: **4245 passed, 0 failed** (PYTHONHASHSEED=0)
