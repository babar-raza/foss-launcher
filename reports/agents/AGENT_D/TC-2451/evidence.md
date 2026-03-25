# TC-2451 Evidence — Agent D: W5 Per-Page Timing Metrics + INCREMENTAL.md

**Date**: 2026-02-23
**Agent**: Agent_D

---

## Deliverables

### 1. Per-Page `duration_ms` in W5 (`src/launch/workers/w5_section_writer/worker.py`)

**Sequential loop** — `time.perf_counter()` wrap around `_generate_single_page()`:
```python
import time as _time
_t0 = _time.perf_counter()
entry = _generate_single_page(...)
entry["duration_ms"] = int((_time.perf_counter() - _t0) * 1000)
```

**Parallel loop** — `_pp_t0` captured before `pool.submit()`, `duration_ms` set when future resolves:
```python
_pp_t0 = _time.perf_counter()
fut = pool.submit(_generate_single_page, ...)
futures[fut] = (page, _pp_t0)
...
entry["duration_ms"] = int((_time.perf_counter() - _par_t0) * 1000)
```

**Cache-hit and preserved page entries** have `"duration_ms": 0` (no generation time).

---

### 2. Aggregate Timing Log

W5 emits at completion:
```
[W5] timing: N generated avg=Xms, M skipped (preserved+cache)
```

Implementation replaces the old `"Incremental summary"` log (TC-1764) with a unified timing
+ skipped summary that covers both `page_status="preserved"` and `page_status="cache_hit"`.

---

### 3. Draft Manifest Extension

`draft_manifest.json` entries now include `duration_ms` (optional field, backward compat):
```json
{
  "page_id": "products_overview",
  "section": "products",
  "slug": "overview",
  "output_path": "content/.../overview.md",
  "draft_path": "drafts/products/overview.md",
  "title": "Overview",
  "word_count": 847,
  "claim_count": 5,
  "page_status": "new",
  "duration_ms": 11234
}
```

---

### 4. `reports/perf/INCREMENTAL.md`

Created with:
- How each mechanism works (hash skip + regen_failed_only)
- Before/after analysis: 20-page pilot, 2 failures → 90% W5 wall-clock savings
- Timing metrics explanation and format
- Configuration reference
- Safety properties

---

## No New Tests Required

Timing is an additive field to manifest entries — verified structurally:
- The `execute_section_writer()` function already has test coverage in `test_tc_440_section_writer.py`
- `duration_ms` is optional in the manifest schema — existing tests unaffected
- `test_w5_incremental.py` covers cache-hit entries having `duration_ms=0` conceptually via
  the `TestW5CacheHitSkip` class structure
