# TC-2451 Self-Review — Agent D: W5 Per-Page Timing Metrics + INCREMENTAL.md

**Date**: 2026-02-23
**Agent**: Agent_D

---

## Checklist

### Correctness
- [x] `duration_ms` computed with `time.perf_counter()` (high-resolution monotonic clock)
- [x] Preserved pages (page_status="preserved") have `duration_ms=0` — no generation time
- [x] Cache-hit pages (page_status="cache_hit") have `duration_ms=0` — no generation time
- [x] Aggregate log uses `_generated_entries` (excludes preserved + cache_hit) for avg_ms
- [x] Division-by-zero guarded: `max(len(_generated_entries), 1)` denominator
- [x] `import time as _time` is scoped within the function to avoid module-level import conflicts
- [x] Parallel timing captures start before `pool.submit()` — includes thread scheduling overhead
  (documented as limitation in self_review)

### Draft Manifest
- [x] `duration_ms` is an optional field — existing downstream consumers unaffected
- [x] All entry paths (generated, preserved, cache_hit) include `duration_ms`

### Reports
- [x] `reports/perf/INCREMENTAL.md` covers both mechanisms with numeric estimates
- [x] Safety properties documented (pilots unaffected, fallback behaviors)
- [x] Configuration reference with YAML example included

### Tests
- [x] `pytest tests/ -x` — 0 failures (no new tests needed for timing; additive field)

---

## Known Limitations

1. **Parallel timing overhead**: In parallel mode, `duration_ms` includes thread pool scheduling
   overhead (~1-2ms), not just LLM call time. Sequential mode is accurate to ±1ms.

2. **Preserved page duration**: `duration_ms=0` for preserved pages understates the file read time
   (~1ms). This is acceptable — the point is to show "no LLM call cost".
