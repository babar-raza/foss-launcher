# Healing Plan — TC-3777 Evaluate Worker Content-Review Alignment

**Date:** 2026-03-07
**Source:** Self-review of TC-3777 implementation
**Scope:** All gaps/blockers from the evaluate worker content-review alignment self-review

---

## Gap Table

| Gap ID | Severity | Description | Taskcard | Status |
|--------|----------|-------------|----------|--------|
| G-EV-01 | **BLOCKER** | RunConfig has no `product_name`/`display_name` field — check_product_names silently disabled for every page | EV-01 | Not Started |
| G-EV-02 | **BLOCKER** | `_run_llm_review` passes `product_name=""`, `page_title=""`, `canonical_import=""`, `platform=""` — LLM review criteria 8+9 have no context | EV-01 | Not Started |
| G-EV-03 | HIGH | Duplicate `_strip_frontmatter` + `_strip_code_blocks` in repetition.py and product_names.py — violates DRY; shared helpers exist in `launcher.shared.jaccard` | EV-02 | Not Started |
| G-EV-04 | LOW | `from collections import Counter` inside function body in artifacts.py — code smell | EV-02 | Not Started |
| G-EV-05 | HIGH | O(n²) sentence comparison in check_repetition with no cap — 200 sentences = 19,900 pairs | EV-03 | Not Started |
| G-EV-06 | HIGH | Sentence splitting on `\.\s` breaks on abbreviations ("e.g. something"), decimals ("3.14 GB"), URLs | EV-03 | Not Started |
| G-EV-07 | MEDIUM | Missing doubled path segment detection (`/python/python/`) in permalink check — plan P0 item dropped | EV-04 | Not Started |
| G-EV-08 | MEDIUM | Keyword stuffing regex `\b[A-Z][a-z]+\.[A-Z][A-Za-z]+\b` matches any PascalCase.PascalCase, not actual product name — false positives | EV-04 | Not Started |
| G-EV-09 | HIGH | Missing tests: keyword stuffing, wrong-case detection, medium-severity repetition path, product_name threading through worker | EV-05 | Not Started |
| G-EV-10 | LOW | No logging in any of 3 new check functions | EV-06 | Not Started |
| G-EV-11 | LOW | Worker docstring says "8 deterministic checks" — now 11 | EV-06 | Not Started |

---

## Summary

| Severity | Count |
|----------|-------|
| BLOCKER | 2 |
| HIGH | 4 |
| MEDIUM | 2 |
| LOW | 3 |
| **TOTAL** | **11** |

---

## Taskcard File Inventory

| Taskcard | File | Gaps Covered |
|----------|------|--------------|
| EV-01 | `plans/healing/EV-01-product-name-threading.md` | G-EV-01, G-EV-02 |
| EV-02 | `plans/healing/EV-02-dry-cleanup.md` | G-EV-03, G-EV-04 |
| EV-03 | `plans/healing/EV-03-repetition-robustness.md` | G-EV-05, G-EV-06 |
| EV-04 | `plans/healing/EV-04-permalink-keyword-precision.md` | G-EV-07, G-EV-08 |
| EV-05 | `plans/healing/EV-05-missing-test-coverage.md` | G-EV-09 |
| EV-06 | `plans/healing/EV-06-observability-docstrings.md` | G-EV-10, G-EV-11 |
