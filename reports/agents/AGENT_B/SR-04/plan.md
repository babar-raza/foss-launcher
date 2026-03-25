# SR-04 Plan

Add observability counters to track how many pages had `description` injected and
`canonical` updated during a W6 run.

Approach:
- Add mutable dict `_injection_stats = {"desc_injected": 0, "canonical_updated": 0}`
  in `execute_seo_optimizer()`, accessible from the `_optimize_one_page()` closure.
- After all content transformations, compare `original_content` vs `content` for:
  - description field presence (regex on `^description:`)
  - canonical value change (`_get_seo_field()` before/after)
- Write counts to `seo_report.json` as `description_injected_count` and
  `canonical_updated_count`.
- Add test `test_seo_report_includes_injection_counts` in `TestSeoFieldInjection`
  verifying both fields are present and >=1 when a page has missing description
  and stale canonical.

Addresses: GAP-08.
