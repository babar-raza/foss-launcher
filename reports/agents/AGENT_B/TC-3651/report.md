# TC-3651 Evidence Report — LLM-Powered Slug Quality Cleanup

## Summary

Added batch LLM-powered slug refinement to `execute_ia_planner()` that removes
filler words from page slugs. When LLM is unavailable, an algorithmic stop-word
stripping fallback provides baseline protection. A `SLUG_FILLER_PREFIX` gate
safety net catches any slugs that slip through.

## Files Changed

| File | Change |
|------|--------|
| `src/launch/workers/_shared/slug_constants.py` | `SLUG_LEADING_STOP_WORDS` frozenset + `strip_leading_stop_words()` |
| `src/launch/workers/w4_ia_planner/worker.py` | `_refine_slugs()` + `_VALID_REFINED_SLUG_RE` + call in `execute_ia_planner()` + `per_feature_blog` fixes |
| `src/launch/workers/w9_validator/gates/gate_slug_safety.py` | `SLUG_FILLER_PREFIX` check in `_check_slug()` |
| `specs/45_seo_slug_strategy.md` | New section: LLM-Powered Slug Refinement (TC-3651) |
| `tests/unit/workers/test_slug_refinement.py` | 31 tests (9 stop-word + 5 LLM + 2 no-LLM + 2 blog + 4 sanitization + 2 length + 3 logging + 4 integration) |
| `tests/unit/workers/w9/test_gate_slug_filler.py` | 5 tests for SLUG_FILLER_PREFIX detection |

## Healing Plan

`plans/healing/22_tc3651_slug_refinement_healing.md` — 5 taskcards:

| Taskcard | Status | Description |
|----------|--------|-------------|
| SR-01 | Done | LLM slug sanitization guard (CRITICAL) |
| SR-02 | Done | per_feature_blog slug length cap (HIGH) |
| SR-03 | Done | Slug refinement observability (MEDIUM) |
| SR-04 | Done | Integration + edge-case tests (MEDIUM) |
| TM-01 | Done | Governance cleanup (MEDIUM/LOW) |

## Test Evidence

### Before TC-3651
- Tests: 8080 passed, 13 skipped, 3 xfailed, 0 failed

### After TC-3651 (base implementation)
```
pytest tests/unit/workers/test_slug_refinement.py -v  # 13 passed
pytest tests/unit/workers/w9/test_gate_slug_filler.py -v  # 5 passed
pytest tests/ -x  # 8103 passed, 0 failed
```

### After SR-01/02/03 (healing round 1)
```
pytest tests/unit/workers/test_slug_refinement.py -v  # 27 passed
pytest tests/ -x  # 8152 passed, 0 failed
```

### After SR-04 + TM-01 (healing round 2)
```
pytest tests/unit/workers/test_slug_refinement.py -v  # 31 passed
pytest tests/ -x  # (run pending)
```

## Key Design Decisions

1. **LLM batch over per-slug calls**: Single LLM call for all slugs (cost/latency).
2. **Algorithmic fallback**: `strip_leading_stop_words()` with `min_remaining=2` guard.
3. **SR-01 sanitization pipeline**: spaces->hyphens, lowercase, strip non-slug, collapse hyphens, regex validate.
4. **SR-02 length cap**: `_derive_semantic_slug(claim_text, max_length=25)` keeps total blog slug under ~55 chars.
5. **Gate safety net**: `SLUG_FILLER_PREFIX` fires on 2+ consecutive leading filler words (detection, not prevention).

## Spec Impact

- `specs/45_seo_slug_strategy.md` gained section "LLM-Powered Slug Refinement (TC-3651)" documenting:
  - Primary: LLM batch cleanup
  - Secondary: Algorithmic stop-word stripping
  - Safety net: Gate detection
  - Implementation paths and test files

## ID Renumbering Note

Originally created as TC-3641 but renumbered to TC-3651 due to ID conflict with
existing TC-3641 (AG-011 validator unit tests). All source comments, spec references,
test docstrings, and taskcard references updated accordingly.
