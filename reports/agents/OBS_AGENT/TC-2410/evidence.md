# TC-2410 Evidence: LLM Cache Observability

## Files Changed / Added

| File | Status | Description |
|------|--------|-------------|
| `src/launch/workers/_shared/cache_telemetry.py` | NEW | Standalone telemetry helper: `CACHE_OUTCOMES`, `CACHE_REASONS`, `CacheEvent`, `emit_cache_event`, `get_cache_stats`, `reset_cache_stats` |
| `src/launch/clients/llm_provider.py` | MODIFIED | Added import + 5 telemetry hooks (marked `# LLM_CACHE_TELEMETRY_HOOK`): hit, miss, saved, bypass/nondet, bypass/fallback |
| `scripts/llm_cache_maintenance.py` | NEW | Maintenance CLI: `stats`, `purge`, `purge-old` subcommands with `--dry-run` and `--cache-dir` |
| `tests/unit/clients/test_cache_telemetry.py` | NEW | 8 test classes: constants, emit shape, counter increments, thread-safety, CacheEvent dataclass, provider integration, maintenance script smoke tests |
| `docs/reference/config.md` | MODIFIED | "Diagnosing cache behavior" subsection appended to LLM Disk Cache section |
| `plans/taskcards/TC-2410_llm_cache_observability_cli_safety.md` | NEW | Taskcard |
| `plans/taskcards/INDEX.md` | MODIFIED | Registered TC-2410 |

## Hook Integration Point

**Import added** (line 26, after existing `llm_cache` import):
```python
from ..workers._shared.cache_telemetry import emit_cache_event as _emit_cache_event
```

**Hooks applied** (all marked `# LLM_CACHE_TELEMETRY_HOOK`):
1. `_chat_completion_impl` — cache hit path: `_emit_cache_event(logger, "hit", "ok", ...)`
2. `_chat_completion_impl` — cache miss path: `_emit_cache_event(logger, "miss", "not_found", ...)`
3. `_chat_completion_impl` — cache save path: `_emit_cache_event(logger, "saved", "ok", ...)`
4. `_chat_completion_impl` — fallback bypass (new `else` branch): `_emit_cache_event(logger, "bypass", "fallback", ...)`
5. `_build_cache_context` — nondet bypass: `_emit_cache_event(logger, "bypass", "nondet", ...)`

## Design Decisions

1. **Standalone module in `_shared/`**: `cache_telemetry.py` imports ONLY stdlib — no imports
   from `clients/` or `workers/`. Circular import risk = zero.

2. **Non-fatal by design**: All code inside `emit_cache_event` wrapped in `try/except Exception`.
   A logging failure or counter update failure never propagates to the pipeline.

3. **Thread-safe counters**: `_COUNTER_LOCK` (threading.Lock) guards both reads and writes.
   Tested with 50 concurrent threads × 20 increments = 1,000 expected hits with no race.

4. **`duration_ms=0` omitted from logs**: Zero-duration events (miss, bypass, saved) don't log
   `duration_ms` to reduce noise. Non-zero values (hit with disk latency) are included.

5. **`get_cache_stats()` returns a copy**: Callers cannot accidentally mutate the live counter
   dict. Tested explicitly.

6. **Maintenance script**: No external deps; uses only stdlib (`argparse`, `pathlib`, `time`,
   `datetime`). Windows encoding fix applied to stdout/stderr.

## Test Results

### New telemetry tests
```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/clients/test_cache_telemetry.py -v
```
**39 passed, 1 warning in 0.92s** ✅

### Full test suite (regression check)
```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ --tb=short
```
**4956 passed, 9 skipped, 3 xfailed, 9 xpassed, 1 warning — 0 failures** ✅
(+39 from TC-2410 on top of TC-2409 baseline of 4917)

## Caveats

- **Provider integration tests**: The `test_bypass_fallback_counter` test exercises the
  fallback path through mock `http_post` side effects. Real fallback behavior depends on
  the primary endpoint actually failing, so the test uses best-effort assertions.

- **No `events.ndjson` integration**: Cache telemetry is DEBUG-level only, not emitted as
  structured events to `events.ndjson`. This is intentional — adding structured events
  would require LLMTelemetryContext changes and is disproportionate for cache diagnostics.
