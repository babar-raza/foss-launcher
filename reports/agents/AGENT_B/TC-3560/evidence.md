# TC-3560 Evidence — W6 _index.md Description Placeholder Normalization

## Summary

Added deterministic placeholder detection and replacement for `_index.md`
description fields in `src/launch/workers/w6_seo_optimizer/seo_metadata.py`.

## Root Cause

Products `_index.md` files often have placeholder descriptions like "TODO: fill
description", "TBD", or "Template-driven products page". These fail
`gate_4_frontmatter_required_fields` (G4-SEO-001 — empty/generic description).
The existing TC-3400 injection always injects `seo_description` when absent, but
doesn't detect placeholder strings in existing description fields.

## Changes Made

### `src/launch/workers/w6_seo_optimizer/seo_metadata.py`
- Added module-level constant `_INDEX_DESC_PLACEHOLDER_RE` (regex: `TODO|TBD|fill desc|placeholder|template-driven`, case-insensitive)
- Added TC-3560 block at end of `optimize_seo_metadata()`, after the existing
  generic/short description update (TC-3400):
  - Only fires when `is_section_index=True`
  - Checks if existing description is empty OR matches placeholder regex
  - If so: generates deterministic template `"{product_label} for {platform} — documentation, code examples, and developer resources."` (≤160 chars)
  - Updates frontmatter with the deterministic description
  - No LLM dependency — purely deterministic

### `tests/unit/workers/test_w6_seo_hardening.py`
- Added `TestIndexDescriptionNormalization` class (7 tests):
  - `test_index_missing_description_gets_template`
  - `test_index_todo_placeholder_replaced`
  - `test_index_tbd_placeholder_replaced`
  - `test_index_template_driven_placeholder_replaced`
  - `test_non_index_page_description_not_overridden_by_tc3560`
  - `test_index_good_description_preserved`
  - `test_index_description_max_160_chars`

## Test Results

```
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w6_seo_hardening.py::TestIndexDescriptionNormalization -v
7 passed in 0.20s
```

Full suite: **7734 passed, 13 skipped, 3 xfailed, 0 failed** (was 7713).

## Non-LLM Guarantee

The template is computed from `product_name` + `platform` fields (already
available from `run_config`/`page_plan`). No API call is made. Result is
capped at 160 chars. Existing good descriptions are preserved (placeholder
regex uses `.match()` — start-of-string only).
