# Evidence — TC-UND-106 (Agent B)

Date: 2026-03-14

## Changes Made

### `src/launcher/workers/understand/extract/_llm.py`

| Addition | Lines | Description |
|----------|-------|-------------|
| `_CHUNK_THRESHOLD_CHARS = 60_000` | after 162 | Activate chunking above this total |
| `_CHUNK_SIZE_CHARS = 50_000` | after 162 | Max content chars per chunk window |
| `_split_doc_contexts()` | 172-204 | Greedy window splitter; single oversized doc stays alone |
| `_salvage_partial_json()` | 445-500 | Char-scan state machine; recovers complete objects from truncated array |
| Modified `_parse_claims_json` | ~542-552 | Calls `_salvage_partial_json` as recovery after double JSONDecodeError |
| Modified `_extract_claims_llm` | 224-302 | Chunked path when `total_chars > 60K`; single-call path unchanged below threshold |

### `tests/unit/workers/understand/test_extract.py`

New class `TestLLMJsonSalvageAndChunking` (12 tests appended at EOF).

## Test Results

### Targeted tests (new class only)
```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -v -k "Salvage or Chunk or split or chunked" -q

12 passed, 157 deselected in 1.87s
```

### Full understand worker suite
```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -q

380 passed, 2 xpassed in 4.86s
```

### Full test suite
```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q

4381 passed, 65 skipped, 3 xfailed, 2 xpassed in 99.65s
```

Baseline was 4369. Delta: **+12** (the 12 new TC-UND-106 tests).

## Root Cause Confirmed

- `_parse_claims_json` used `rfind("]")` which finds inner `]` from claim object
  properties when the outer array `]` is missing due to truncation → `json.loads`
  fails → `_repair_json` cannot fix structural truncation → returns `[]`
- All 3 retries receive identical input/budget → all fail identically
- Fallback: 62 deterministic claims (claim_source="llm_fallback")

## Fix Verification

- `test_salvage_recovers_complete_objects_from_truncated_array`: 4/5 objects
  recovered from array truncated mid-5th object ✓
- `test_split_large_input_produces_multiple_bounded_chunks`: 4×20K → 2 chunks ✓
- `test_extract_uses_chunked_path_for_large_input`: `_call_llm_extract` called >1
  time for 80K input ✓
- `test_extract_uses_single_call_below_threshold`: single call for 10K input ✓
- `test_extract_partial_chunk_success_returns_successful_chunk_claims`: partial
  chunk success correctly returns claims without falling to deterministic ✓
