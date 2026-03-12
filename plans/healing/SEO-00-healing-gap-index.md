# SEO Module Healing — Gap Index

## Context

The v2 SEO module (TC-3806 through TC-3812) implemented a 3-stage SEO pipeline:
keyword research → keyword-aware prompts → post-gen metadata optimization → validation.

Initial self-review identified 14 gaps (G-01 through G-14). A subsequent
self-review after fixing Gemini model deprecation, PyTrends empty results,
and canonical URL bugs identified 7 additional gaps (G-SR1 through G-SR7).

These taskcards bring the SEO module from "functional draft" to "production grade".

## Gap Table — Original (G-01 through G-14)

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|----------|----------|
| G-01 | No exception safety in Phase 1.5 — one bad page crashes entire run | Critical | SEO-01 |
| G-02 | Gemini call in `_generate_description` has no exception handling | Critical | SEO-01 |
| G-03 | Keyword density/body-presence check missing from Evaluate (plan spec) | High | SEO-02 |
| G-04 | `_strip_html_entities` imported as private cross-module — fragile coupling | Medium | SEO-03 |
| G-05 | `Any` typing for `keyword_bundle` and `gemini_client` — no contract safety | Medium | SEO-03 |
| G-06 | `_entity_re` compiled inside function body on every call — perf waste | Low | SEO-04 |
| G-07 | Duplicate stop-word lists in `seo_metadata.py` and `plan.py` | Low | SEO-04 |
| G-08 | No structured event emission for Phase 1.5 — breaks observability pattern | Medium | SEO-05 |
| G-09 | No debug logging for description priority chain selection | Medium | SEO-05 |
| G-10 | Missing tests: keyword_bundle integration, canonical variants, description==seoTitle, Phase 1.5 worker integration | High | SEO-06 |
| G-11 | `_enforce_metadata_quality` mutates dict in-place AND returns it — unclear contract | Low | SEO-04 |
| G-12 | Hardcoded `_SUBDOMAIN_MAP` — not configurable for non-Aspose products | Medium | SEO-07 |
| G-13 | Missing `seo:` run config section from plan spec | Medium | SEO-07 |
| G-14 | Gemini slug refinement in `_refine_page_slugs()` not implemented (plan spec) | Medium | SEO-08 |

## Gap Table — Self-Review Round 2 (G-SR1 through G-SR7)

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|----------|----------|
| G-SR1 | No tests for Gemini 2.5 thinking-part filtering in `_call_api` | High | SEO-09 |
| G-SR2 | No tests for `_FAMILY_TREND_TERMS` mapping or unknown-family fallback | High | SEO-10 |
| G-SR3 | `_FAMILY_TREND_TERMS` defined inside function body, should be module-level | Low | SEO-11 |
| G-SR4 | Plan spec still references `gemini-2.0-flash` (code uses `gemini-2.5-flash`) | Medium | SEO-12 |
| G-SR5 | `TrendReq` instantiated per-query in loop (3 sessions instead of 1) | Low | SEO-13 |
| G-SR6 | No Gemini model deprecation fallback chain (silent degradation on quota=0) | High | SEO-14 |
| G-SR7 | `maxOutputTokens: 2048` is unvalidated guess; no per-method sizing | Medium | SEO-15 |

## Taskcard Summary

| Taskcard | Title | Gaps Fixed | Priority | Status |
|----------|-------|------------|----------|--------|
| SEO-01 | Exception safety for Phase 1.5 + Gemini calls | G-01, G-02 | P0 — Critical | Done |
| SEO-02 | Keyword density body-presence check in Evaluate | G-03 | P1 — High | Done |
| SEO-03 | Type safety — Protocol types + public entity stripper | G-04, G-05 | P1 — High | Done |
| SEO-04 | Code hygiene — regex hoisting, stop-word dedup, contract clarity | G-06, G-07, G-11 | P2 — Medium | Done |
| SEO-05 | Observability — event emission + description chain logging | G-08, G-09 | P2 — Medium | Done |
| SEO-06 | Test coverage expansion | G-10 | P1 — High | Done |
| SEO-07 | Configuration — subdomain map + `seo:` run config section | G-12, G-13 | P2 — Medium | Done |
| SEO-08 | Gemini slug refinement wiring | G-14 | P3 — Low | Done |
| SEO-09 | Gemini 2.5 thinking-part parsing tests | G-SR1 | P1 — High | Done |
| SEO-10 | Family-specific Trends query tests | G-SR2 | P1 — High | Done |
| SEO-11 | Hoist `_FAMILY_TREND_TERMS` to module level | G-SR3 | P2 — Medium | Done |
| SEO-12 | Update plan spec Gemini model reference | G-SR4 | P2 — Medium | Done |
| SEO-13 | Reuse TrendReq instance across queries | G-SR5 | P3 — Low | Done |
| SEO-14 | Gemini model deprecation fallback chain | G-SR6 | P1 — High | Done |
| SEO-15 | Gemini maxOutputTokens right-sizing | G-SR7 | P2 — Medium | Done |
