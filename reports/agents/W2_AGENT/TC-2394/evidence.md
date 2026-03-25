# TC-2394 Evidence: Topic Discovery

**Agent**: W2_AGENT
**Taskcard**: TC-2394
**Date**: 2026-02-20
**Status**: Done

## Implementation Summary

TC-2394 adds LLM-powered topic discovery to the W2 FactsBuilder, enabling the pipeline to
identify article topics from FOSS repo documentation that are not already covered by
existing claim_groups. Discovered topics become optional pages in W4.

## Files Created

### `src/launch/workers/w2_facts_builder/topic_discovery.py`
- New module implementing topic discovery logic
- `discover_topics_from_docs(doc_chunks, existing_claim_groups, llm_client, max_topics=10)` — main entry point
- `_dedup_topics(topics, existing_titles, threshold)` — TF-IDF cosine similarity dedup gate at threshold 0.7
- `_parse_topics_json(raw)` — robust JSON parser handling fenced and unfenced LLM responses
- LLM prompt instructs model to avoid topics already covered by claim_group keys
- All errors caught and logged; never raises to caller

### `tests/unit/workers/test_tc_2394_topic_discovery.py`
- 11 unit tests covering all public and private functions
- Tests: happy path, dedup filtering, dedup keep unique, JSON fence parsing, invalid JSON, empty chunks, max_topics cap, dict-wrapped JSON, LLM failure graceful degradation

## Files Modified

### `src/launch/workers/w2_facts_builder/worker.py`
- After writing `product_facts.json` (line ~2947), added TC-2394 topic discovery block
- Checks for `source_chunks.json` (from TC-2383) and `llm_client is not None`
- Writes `topic_manifest.json` to `artifacts_dir` with structure:
  ```json
  {
    "discovered_topics": [...],
    "dedup_threshold": 0.7,
    "source_doc_count": N
  }
  ```
- Entire block wrapped in `try/except` — never blocks pipeline

### `src/launch/workers/w4_ia_planner/worker.py`
- After the section optional-pages loop (before TC-1813 slug dedup), added TC-2394 block
- Reads `topic_manifest.json` from `run_layout.artifacts_dir`
- Converts each discovered topic to a full page spec using existing W4 helpers:
  - `_derive_semantic_slug()` for slug generation
  - `build_content_strategy()` for content_strategy field
  - `compute_output_path()` and `compute_url_path()` for path fields
  - `_default_headings_for_role()` for required_headings
- Assigns topics to the `docs` section with `source: "topic_discovery"` marker
- Slug-deduplication against existing pages prevents collisions
- Entire block wrapped in `try/except` — never blocks pipeline

## Test Results

```
tests/unit/workers/test_tc_2394_topic_discovery.py  11 passed
Full suite: 4653 passed, 9 skipped, 0 failed
```

## Acceptance Checks

- [x] `topic_discovery.py` created with `discover_topics_from_docs()`, `_dedup_topics()`, `_parse_topics_json()`
- [x] W2 writes `topic_manifest.json` when `source_chunks.json` and `llm_client` are available
- [x] W4 reads `topic_manifest.json` and adds discovered topics as optional pages in `docs` section
- [x] Dedup threshold 0.7 prevents near-duplicates via TF-IDF cosine similarity
- [x] 11 TC-2394-specific tests pass; full suite 0 regressions (4653 passed)
- [x] All integrations guarded with `try/except` — pipeline cannot be blocked by topic discovery
