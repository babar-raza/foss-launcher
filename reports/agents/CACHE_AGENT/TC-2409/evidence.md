# TC-2409 Evidence: LLM Disk Cache

## Files Changed / Added

| File | Status | Description |
|------|--------|-------------|
| `src/launch/clients/llm_cache.py` | NEW | Cache module: `cache_enabled`, `cache_dir`, `make_cache_key`, `load`, `save` |
| `src/launch/clients/llm_provider.py` | MODIFIED | Import `llm_cache`; move `request_payload` before telemetry context; add cache check + save; add `_build_cache_context()` |
| `tests/unit/clients/test_llm_cache.py` | NEW | 30+ assertions covering: hit, miss, nondet bypass, ALLOW_NONDET, fallback bypass, CACHE_FALLBACK, corruption tolerance, default-off |
| `docs/reference/config.md` | MODIFIED | Added "LLM Disk Cache" section with env vars, directory, and key documentation |
| `plans/taskcards/TC-2409_llm_disk_cache_opt_in.md` | NEW | Taskcard |
| `plans/taskcards/INDEX.md` | MODIFIED | Registered TC-2409 |

## Integration Point

**Cache check location**: `LLMProviderClient._chat_completion_impl()` — BEFORE
`with LLMTelemetryContext(...)`. This avoids spurious `LLM_CALL_STARTED` events
for requests served from disk.

**Cache save location**: Inside the telemetry context, immediately before
`return result`, after `result` dict is fully assembled (including optional
`tool_calls`).

**Key composition**: `make_cache_key(request_payload)` where `request_payload`
is the fully assembled dict (`model`, `messages`, `temperature`, optional
`max_tokens`, `response_format`, `tools`). Any `output_schema` is injected into
`messages` before the payload is assembled, so it is automatically covered by
the key.

## Env Vars Supported

| Variable | Default | Effect |
|----------|---------|--------|
| `FOSS_LAUNCHER_LLM_CACHE` | `0` | Set to `1` to enable disk cache |
| `FOSS_LAUNCHER_LLM_CACHE_DIR` | (unset) | Override cache directory path |
| `FOSS_LAUNCHER_LLM_CACHE_ALLOW_NONDET` | `0` | Set to `1` to cache temperature > 0 responses |
| `FOSS_LAUNCHER_LLM_CACHE_FALLBACK` | `0` | Set to `1` to cache fallback-endpoint responses |

## Test Results

### New cache tests
```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/clients/test_llm_cache.py -v
```
**32 passed, 1 warning in 1.44s** ✅

### Full test suite (regression check)
```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ --tb=short
```
**4917 passed, 9 skipped, 3 xfailed, 9 xpassed, 1 warning in 119.90s** — 0 failures ✅

## Design Decisions

1. **Cache check before telemetry context**: Prevents spurious `LLM_CALL_STARTED`
   events in `events.ndjson` for requests served from disk. This is the cleanest
   separation of concerns.

2. **`request_payload` moved before `with` block**: Required prerequisite for (1).
   The payload dict is pure data construction with no side effects, so moving it
   is safe.

3. **Fallback bypass by default**: Fallback responses may come from a different
   model/server than the primary. Caching them by default could silently serve
   degraded fallback content on future primary calls. Opt-in via
   `FOSS_LAUNCHER_LLM_CACHE_FALLBACK=1`.

4. **SHA-256 full 64-char key, flat file layout**: Pipeline generates ~50–200 LLM
   calls per run. Flat layout is simpler and perfectly adequate at this scale.
   Full SHA-256 avoids any collision risk.

5. **No new third-party deps**: `llm_cache.py` uses only `hashlib`, `json`, `os`,
   `time`, `pathlib`, `typing` — all stdlib.

## Caveats

- **Streaming**: Not applicable — `LLMProviderClient` does not support streaming.
- **Tool calls**: Tool definitions are included in `request_payload["tools"]` and
  thus covered by the cache key. Tool-call results from the LLM response are
  stored in `result["tool_calls"]` and round-trip correctly via cache.
- **L1 retry loop**: Cache hit bypasses the L1 validation retry loop. The stored
  response already passed L1 validation on its first call.
- **Evidence files**: On a cache hit, no new evidence file is written. The
  `evidence_path` in the returned dict points to the original call's evidence
  file, which is informational only.
