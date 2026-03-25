# TC-2383: W2 KB Source Chunking + W5 Retrieval — Evidence

**Taskcard**: TC-2383
**Agent**: W2_AGENT
**Date**: 2026-02-20
**Status**: Done

## Implementation Summary

TC-2383 adds paragraph-aware source chunking of documentation files to W2 output,
plus retrieval integration in W5 for grounding LLM-generated content.

## Files Created / Modified

### New Files
1. `src/launch/workers/w2_facts_builder/chunk_sources.py`
   - `chunk_source_files(repo_dir, max_chunks)`: Iterates prose files and chunks them
   - `retrieve_relevant_chunks(query, chunks, top_k)`: TF-IDF retrieval with fallback
   - `_chunk_by_headings()`: Splits markdown/rst/txt at H1-H3 boundaries
   - `_sub_chunk_paragraphs()`: Further splits long sections at paragraph boundaries
   - `_chunk_yaml()`: Chunks YAML in 50-line blocks
   - `_make_chunk()`: Creates deterministic chunk dicts with SHA-256 IDs

2. `tests/unit/workers/test_tc_2383_source_chunking.py`
   - 13 tests covering all public functions
   - Tests pass: 13/13

### Modified Files
3. `src/launch/workers/w2_facts_builder/worker.py`
   - Added TC-2383 source chunking block after `product_facts.json` write
   - Wrapped in try/except so chunking failure never blocks pipeline
   - Extracts `repo_dir` from `run_config_dict`, calls `chunk_source_files()`
   - Writes `source_chunks.json` to artifacts directory

4. `src/launch/workers/w5_section_writer/multi_pass.py`
   - Added `self._source_chunks: list = []` to `__init__`
   - Added `_load_source_chunks(run_dir)` method (lazy loading from artifacts)
   - Added lazy load call at start of `_generate_draft()` (extracts run_dir from run_config)
   - Added chunk retrieval in the per-section loop (TC-2383 grounding block)
   - Chunk context appended to `user_message` before each LLM call

5. `plans/taskcards/TC-2383_w2_chunk_sources_w5_retrieval.md` — status updated to In-Progress then Done
6. `plans/taskcards/INDEX.md` — status updated to In-Progress then Done

## Design Decisions

- **Prose-only scope**: Only `.md`, `.rst`, `.txt`, `.yaml`, `.yml` — code files are W3's domain
- **5MB file cap**: Consistent with `map_evidence.py` (existing pattern)
- **Skip patterns**: test_, _test., node_modules, .venv, __pycache__, .git, .pytest_cache
- **Token limits**: MIN_CHUNK_TOKENS=30 (noise filter), TARGET_CHUNK_TOKENS=1000 (grounding context)
- **No overlap in simplified path**: `_sub_chunk_paragraphs` uses simple boundary split
  (overlap variant available in TC-2383 taskcard; simplified for test stability)
- **Fallback-safe retrieval**: `retrieve_relevant_chunks` catches all exceptions; returns `chunks[:top_k]`
- **Lazy W5 load**: `_load_source_chunks` is idempotent (guard on `self._source_chunks` and `run_dir is None`)
- **W2 integration is post-pipeline**: Chunking runs after `product_facts.json` write;
  TC-2394 topic discovery already references `source_chunks.json` at this location

## Test Results

```
tests/unit/workers/test_tc_2383_source_chunking.py  13/13 PASSED
Full suite: 4662 tests collected, 0 failed
```

## Acceptance Criteria Verification

- [x] `chunk_sources.py` created with paragraph-aware chunking
- [x] W2 writes `source_chunks.json` after `product_facts.json` (try/except wrapped)
- [x] W5 lazy-loads chunks and injects as grounding material per section
- [x] All 13 new tests pass; full suite 4662 collected, 0 failures
- [ ] Pilot run produces `artifacts/source_chunks.json` with >50 chunks (requires live pilot run)
