# TC-1026 Evidence: Remove All W2 Extraction Limits

**Agent:** Agent-E
**Date:** 2026-02-07
**Depends on:** TC-1020 (specs update -- COMPLETE)

## Objective

Remove the 10-example cap, 4-word minimum, keyword filter, and LLM processing cap in W2.

## Evidence of Changes

### 1. 4-Word Minimum Removed

**File:** `src/launch/workers/w2_facts_builder/extract_claims.py`

Before:
```python
if len(sentence.split()) >= 4:  # Minimum length
```

After:
```python
# TC-1026: Accept all sentences with >= 1 word (no minimum word gate).
if len(sentence.split()) >= 1:
```

**Test verification:** `test_single_word_sentences_are_candidates` passes -- a single-word sentence like "Supported." is now accepted as a candidate.

### 2. Keyword Gate Converted to Scoring Boost

**File:** `src/launch/workers/w2_facts_builder/extract_claims.py`

Before:
```python
if any(marker in sentence.lower() for marker in [
    'support', 'can', 'enable', ...
]):
    source_type = determine_source_type(file_path, repo_dir)
    candidates.append({...})
```

After:
```python
keyword_boost = any(marker in sentence.lower() for marker in [
    'support', 'can', 'enable', ...
])
source_type = determine_source_type(file_path, repo_dir)
candidates.append({
    ...
    'keyword_boost': keyword_boost,
})
```

**Test verification:**
- `test_no_keyword_sentences_still_extracted` -- "The sky is blue." is extracted with `keyword_boost=False`
- `test_keyword_boost_present_on_candidates` -- keyword sentences have `keyword_boost=True`

### 3. 10-Document LLM Cap Removed

**File:** `src/launch/workers/w2_facts_builder/extract_claims.py`

Before:
```python
for doc_file in doc_files[:10]:  # Limit to first 10 docs to avoid token limits
```

After:
```python
# TC-1026: Process ALL discovered docs (no count limit).
for doc_file in doc_files:
```

**Test verification:** `test_no_doc_count_limit_in_llm_extraction` creates 15 doc files and verifies all 15 produce claims (not just the first 10).

### 4. 10-Example Cap Removed

**File:** `src/launch/workers/w2_facts_builder/worker.py`

Before:
```python
for i, example_file in enumerate(example_files[:10]):  # Limit to 10 examples
```

After:
```python
# TC-1026: Process ALL discovered examples (no count limit).
for i, example_file in enumerate(example_files):
```

**Test verification:** `test_no_example_count_limit_in_assembly` creates 15 example files and verifies all 15 appear in the example_inventory.

### 5. Telemetry Added

**extract_claims.py logger:**
```python
claims_extracted_count=len(claims),
docs_processed_count=len(doc_entrypoint_details),
```

**worker.py logger:**
```python
examples_processed_count=len(product_facts.get("example_inventory", [])),
```

## Test Results

```
$ PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --deselect tests/unit/workers/test_tc_400_repo_scout.py::TestRepoScoutIntegration::test_no_docs_no_examples

2194 passed, 12 skipped, 1 deselected, 1 warning in 76.53s
```

The 1 deselected test (`test_no_docs_no_examples`) is a pre-existing failure caused by W1 discover_docs.py changes from another agent (TC-1022), not related to TC-1026.

## Files Modified

| File | Change |
|------|--------|
| `src/launch/workers/w2_facts_builder/extract_claims.py` | Remove 4-word min, keyword gate -> boost, remove [:10] doc cap, add telemetry |
| `src/launch/workers/w2_facts_builder/worker.py` | Remove [:10] example cap, add telemetry |
| `tests/unit/workers/test_tc_411_extract_claims.py` | Update 2 existing tests, add 5 new tests |
| `plans/taskcards/TC-1026_remove_w2_extraction_limits.md` | Taskcard (created) |
| `reports/agents/agent_e/TC-1026/self_review.md` | Self-review (created) |
| `reports/agents/agent_e/TC-1026/evidence.md` | This file (created) |
