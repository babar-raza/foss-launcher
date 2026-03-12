---
id: TC-3806
title: "SEO Cache + API Rate Limiter (foundational infra)"
status: Done
priority: High
owner: agent
updated: "2026-03-07"
tags: [seo, infra, cache]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3806_seo_cache_and_rate_limiter.md
  - src/launcher/shared/seo_cache.py
  - src/launcher/shared/api_rate_limiter.py
  - tests/unit/shared/test_seo_cache.py
  - tests/unit/shared/test_api_rate_limiter.py
evidence_required:
  - tests/unit/shared/test_seo_cache.py
  - tests/unit/shared/test_api_rate_limiter.py
---

# Taskcard TC-3806 — SEO Cache + API Rate Limiter

## Objective

Create the foundational infrastructure for the v2 SEO module: a cross-run, per-family/platform disk cache with TTL management, and a token-bucket rate limiter with exponential backoff for external API calls. These are dependencies for all subsequent SEO taskcards.

## Required spec references

- `C:\Users\prora\.claude\plans\sparkling-discovering-walrus.md` (Stage 1: Cache Strategy + Rate Limiting sections)

## Scope

### In scope
- `seo_cache.py`: Disk-backed cache with per-entry TTL, cross-run persistence, corruption recovery
- `api_rate_limiter.py`: Token-bucket rate limiter with exponential backoff on 429/5xx
- Unit tests for both modules

### Out of scope
- Gemini client (TC-3807)
- Keyword research engine (TC-3808)
- Integration into pipeline workers (TC-3809+)

## Inputs

- Plan file: `C:\Users\prora\.claude\plans\sparkling-discovering-walrus.md`
- Existing cache pattern: `src/launcher/clients/llm_cache.py` (reference, not modified)

## Outputs

- `src/launcher/shared/seo_cache.py` — SEO cache module
- `src/launcher/shared/api_rate_limiter.py` — Rate limiter module
- `tests/unit/shared/test_seo_cache.py` — Cache tests
- `tests/unit/shared/test_api_rate_limiter.py` — Rate limiter tests

## Allowed paths

- plans/taskcards/TC-3806_seo_cache_and_rate_limiter.md
- src/launcher/shared/seo_cache.py
- src/launcher/shared/api_rate_limiter.py
- tests/unit/shared/test_seo_cache.py
- tests/unit/shared/test_api_rate_limiter.py

### Allowed paths rationale
- Two new shared modules + their tests. No existing files modified.

## Implementation steps

### Step 1: Create seo_cache.py

Disk-backed cache with:
- Per-entry TTL (configurable, default 7 days for external APIs, 24h for local)
- Cache dir: `<project_root>/.seo_cache/<family>/<platform>/`
- SHA-256 keys from `{family}:{platform}:{source}:{content_hash}`
- Atomic writes (temp file + os.replace)
- Corruption recovery (invalid JSON → cache miss, log warning)
- Expired entry pruning on load
- Cache version field for future migration

### Step 2: Create api_rate_limiter.py

Token-bucket rate limiter with:
- Configurable RPM, min interval, max retries
- `acquire()` blocks until slot available
- `record_error(status_code)` → exponential backoff (2s base, 60s cap)
- `record_success()` → reset backoff counter
- Thread-safe (threading.Lock)
- Per-API defaults: Trends 10 RPM/1.5s, Suggest 30 RPM/0.5s, Gemini 15 RPM/1.0s

### Step 3: Write unit tests

Cache tests: TTL expiry, cross-run persistence, key determinism, corruption recovery, version field.
Rate limiter tests: bucket fill, acquire blocking, backoff escalation, success reset, concurrent safety.

## Failure modes

### Failure mode 1: Cache directory not writable

**Detection**: `OSError` / `PermissionError` on `mkdir()` or `os.replace()`
**Resolution**: Catch at cache init, log warning, degrade to no-cache mode (all gets return None)
**Gate**: No gate — this is infra

### Failure mode 2: Corrupt cache file on disk

**Detection**: `json.JSONDecodeError` on load
**Resolution**: Log warning, delete corrupt file, return cache miss. Next write recreates clean file.
**Gate**: No gate — transparent recovery

### Failure mode 3: Race condition on concurrent cache writes

**Detection**: Partial JSON on disk (interrupted `os.replace`)
**Resolution**: Atomic write via temp file + `os.replace()` is atomic on all platforms. If temp file lingers, it's cleaned up on next cache operation.
**Gate**: No gate — atomic ops prevent this

## Task-specific review checklist

1. [ ] Cache uses atomic writes (temp file + os.replace)
2. [ ] TTL is per-entry, not global
3. [ ] Expired entries pruned on load
4. [ ] Corrupt JSON recovers gracefully (no crash)
5. [ ] Rate limiter uses threading.Lock for concurrency
6. [ ] Exponential backoff caps at max_backoff_seconds
7. [ ] All tests pass with PYTHONHASHSEED=0

## Deliverables

1. `src/launcher/shared/seo_cache.py`
2. `src/launcher/shared/api_rate_limiter.py`
3. `tests/unit/shared/test_seo_cache.py`
4. `tests/unit/shared/test_api_rate_limiter.py`

## Acceptance checks

1. [ ] All new tests pass: `.venv/Scripts/python.exe -m pytest tests/unit/shared/test_seo_cache.py tests/unit/shared/test_api_rate_limiter.py -v`
2. [ ] No existing tests broken: `.venv/Scripts/python.exe -m pytest tests/ -x --timeout=60`
3. [ ] Cache survives round-trip: write → read → verify value matches
4. [ ] TTL expiry works: write with TTL=0 → read returns None
5. [ ] Rate limiter blocks correctly: acquire N+1 times at RPM=N within 1 minute → blocks

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: test output

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_seo_cache.py tests/unit/shared/test_api_rate_limiter.py -v
```

**Expected results**:
- All tests PASS
- No warnings about missing modules

## Integration boundary proven

**Upstream**: None (foundational)
**Downstream**: `gemini_client.py` (TC-3807), `keyword_research.py` (TC-3808)
**Contract**: `SEOCache.get(key) -> Any | None`, `SEOCache.set(key, value, ttl)`, `APIRateLimiter.acquire()`, `APIRateLimiter.record_error(status) -> float`, `APIRateLimiter.record_success()`
