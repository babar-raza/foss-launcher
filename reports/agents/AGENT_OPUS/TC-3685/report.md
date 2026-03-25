# TC-3685 Report — G6 Permalink Uniqueness Scoping

## Summary
Fixed 9 false-positive G6 permalink collision issues by scoping collision
detection to within the same Hugo section (subdomain), matching W4 TC-969.

## Root Cause
G6 gate built `permalink_map` keyed only by normalized permalink value.
W4 uses `(section, url_path)` tuples. Cross-section files (docs vs kb vs
reference) sharing the same permalink were flagged as collisions.

## Changes
- `gate_permalink_uniqueness.py`: Added `_infer_section(md_file, site_dir)`
  extracting subdomain from `content/<subdomain>/...` path. Changed
  `permalink_map` key from `str` to `Tuple[str, str]` (section, permalink).
  Doubled segment detection remains global.

## Tests
- 13 new tests in `tests/unit/workers/w9/test_g6_permalink_scoping.py`
  - `TestInferSection` (5): docs, kb, blog, not-in-content, outside-site
  - `TestCrossSectionAllowed` (2): 2-section and 4-section same permalink
  - `TestSameSectionCollision` (2): same-section fails, case-insensitive
  - `TestDoubledSegmentsAlwaysError` (1)
  - `TestEdgeCases` (3): global fallback, no permalink, mixed collision

## Verification
- Full suite: 8617 passed, 0 failed (PYTHONHASHSEED=0)
