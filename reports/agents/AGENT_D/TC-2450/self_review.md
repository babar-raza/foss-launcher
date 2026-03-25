# TC-2450 Self-Review — Agent D: W5 Page Hash Cache + regen_failed_only

**Date**: 2026-02-23
**Agent**: Agent_D

---

## Checklist

### Correctness
- [x] `_compute_page_input_hash()` is pure — no I/O, no LLM, no side effects
- [x] Hash uses only fields that affect generated content (slug, section, page_role, title, purpose, headings, template_variant, resolved claims, resolved snippets)
- [x] Unrelated claims (not in `required_claim_ids`) excluded from hash
- [x] Sorted inputs throughout — `sorted(required_claim_ids)`, sorted claim/snippet dicts
- [x] `_find_failed_page_slugs()` catches file-not-found and corrupt JSON (returns `frozenset()`)
- [x] `_worker_cache.enabled=False` → all cache paths are no-ops (disabled by default)
- [x] Cache hit requires BOTH hash match AND file exists at `run_layout.run_dir / cached_rel`
- [x] `record_page()` called after generation (not before) — never stores a failed page
- [x] `regen_failed_only` block runs BEFORE the generation loop — page_status set before iteration
- [x] Parallel loop: hashes pre-computed for all `to_generate` pages before thread dispatch

### API Backward Compatibility
- [x] `is_page_hit(page_key)` (no hash arg) → empty string → hash check skipped → old behavior preserved
- [x] `record_page(page_key, draft_path)` (no hash arg) → stores `input_hash: ""` → old callers work
- [x] Pages with stored `input_hash: ""` → `is_page_hit(..., "any_hash")` returns hit (empty stored hash → skip validation)
- [x] Existing `test_worker_cache.py` TestPageCache tests pass unchanged

### Tests
- [x] `test_worker_cache.py` — 15+ tests, 0 failures
- [x] `test_w5_incremental.py` — 35+ tests, 0 failures
- [x] Full suite — 0 failures

### Pilots
- [x] `pilot-aspose-3d-foss-python`: no `caching.enabled`, no `regen_failed_only` — zero change
- [x] `pilot-aspose-note-foss-python`: same
- [x] `pilot-aspose-cells-foss-python`: same

---

## Known Limitations

1. **Cross-run caching**: The cache is stored in `run_dir/artifacts/run_cache.json`. For a
   fresh run_dir, the cache is empty → all pages regenerate. Hash-based skip only works within
   the same run_dir (e.g., resume scenarios). True cross-run persistence would require a
   configurable `cache_dir` — deferred to a future TC.

2. **`regen_failed_only` requires incremental mode**: For preserved pages to be reused,
   `incremental.enabled=true` + `previous_run_path` must be set alongside `regen_failed_only`.
   Without them, preserved pages have no source → fall through to regenerate (safe, not silent).

3. **Parallel loop timing**: `duration_ms` in parallel mode measures wall-clock from `pool.submit()`
   to future completion, not pure LLM time (includes thread scheduling overhead). For sequential mode
   it's accurate per-page wall clock.
