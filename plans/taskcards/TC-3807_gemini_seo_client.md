---
id: TC-3807
title: "Gemini SEO Client (free-tier integration)"
status: In-Progress
priority: High
owner: agent
updated: "2026-03-07"
tags: [seo, gemini, client]
depends_on: [TC-3806]
allowed_paths:
  - plans/taskcards/TC-3807_gemini_seo_client.md
  - src/launcher/clients/gemini_client.py
  - tests/unit/clients/test_gemini_client.py
evidence_required:
  - tests/unit/clients/test_gemini_client.py
---

# Taskcard TC-3807 — Gemini SEO Client

## Objective

Create a lightweight Google Gemini client for SEO tasks: keyword analysis, slug refinement, and meta description generation. Uses free tier with rate limiting and caching.

## Required spec references

- `C:\Users\prora\.claude\plans\sparkling-discovering-walrus.md` (Stage 1: Gemini Integration)

## Scope

### In scope
- `GeminiSEOClient` class with 3 methods: `analyze_keywords`, `refine_slugs`, `generate_description`
- Rate limiting via `APIRateLimiter` (TC-3806)
- Caching via `SEOCache` (TC-3806)
- Graceful degradation when API key missing or API unavailable

### Out of scope
- Keyword research orchestration (TC-3808)
- Pipeline integration (TC-3809+)

## Inputs

- `APIRateLimiter` from TC-3806
- `SEOCache` from TC-3806

## Outputs

- `src/launcher/clients/gemini_client.py`
- `tests/unit/clients/test_gemini_client.py`

## Allowed paths

- plans/taskcards/TC-3807_gemini_seo_client.md
- src/launcher/clients/gemini_client.py
- tests/unit/clients/test_gemini_client.py

### Allowed paths rationale
New client module + tests. No existing files modified.

## Implementation steps

### Step 1: Create gemini_client.py
- Use `urllib.request` for HTTP calls (no google-genai dependency yet — keep minimal)
- Rate-limited via `create_gemini_limiter()`
- All responses cached via `SEOCache`
- Graceful degradation: no API key → log warning, return empty results

### Step 2: Write unit tests with mocked API responses

## Failure modes

### Failure mode 1: Missing API key
**Detection**: `GEMINI_API_KEY` env var empty or not set
**Resolution**: All methods return empty/passthrough, log warning once
**Gate**: No gate — graceful degradation

### Failure mode 2: Rate limit (429)
**Detection**: HTTP 429 response
**Resolution**: Exponential backoff via `APIRateLimiter.record_error(429)`, retry up to max_retries
**Gate**: No gate — transparent retry

### Failure mode 3: API returns invalid JSON
**Detection**: `json.JSONDecodeError` on response parsing
**Resolution**: Log warning, return empty result, do not cache invalid response
**Gate**: No gate — transparent fallback

## Task-specific review checklist

1. [ ] No API key → graceful no-op (not crash)
2. [ ] Rate limiter used for every API call
3. [ ] All successful responses cached
4. [ ] Invalid responses NOT cached
5. [ ] Retry logic uses exponential backoff
6. [ ] All tests pass with PYTHONHASHSEED=0

## Deliverables

1. `src/launcher/clients/gemini_client.py`
2. `tests/unit/clients/test_gemini_client.py`

## Acceptance checks

1. [ ] All new tests pass
2. [ ] No existing tests broken
3. [ ] Missing API key test passes (graceful degradation)

## Self-review

### Verification results
- [ ] Tests: X/X PASS

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/clients/test_gemini_client.py -v
```

## Integration boundary proven

**Upstream**: `SEOCache` + `APIRateLimiter` (TC-3806)
**Downstream**: `keyword_research.py` (TC-3808), `seo_metadata.py` (TC-3810)
**Contract**: `GeminiSEOClient.analyze_keywords() -> list[str]`, `.refine_slugs() -> list[str]`, `.generate_description() -> str`
