# SR-04 Changes

## File: src/launch/workers/w6_seo_optimizer/worker.py

### Change 1: Add `_injection_stats` mutable counter dict

Added after `max_parallel` initialization, before closure definition:

```python
# Observability counters (mutable container shared by closure)
_injection_stats = {"desc_injected": 0, "canonical_updated": 0}
```

### Change 2: Track injection events inside `_optimize_one_page()` closure

Added after quality enforcement (`enforce_seo_metadata_quality`), before `changed = ...`:

```python
# Track injection events for observability (SR-04)
import re as _re
_desc_before = bool(_re.search(r'^description:', original_content, _re.MULTILINE))
_desc_after = bool(_re.search(r'^description:', content, _re.MULTILINE))
_canon_before = _get_seo_field(original_content, "canonical")
_canon_after = _get_seo_field(content, "canonical")
if not _desc_before and _desc_after:
    _injection_stats["desc_injected"] += 1
    logger.info("[W6] w6_description_injected slug=%s", slug)
if _canon_before != _canon_after and _canon_after:
    _injection_stats["canonical_updated"] += 1
    logger.info("[W6] w6_canonical_updated slug=%s", slug)
```

### Change 3: Publish counts to `seo_report.json`

Added after `report["keyword_stats"]` assignment:

```python
report["description_injected_count"] = _injection_stats["desc_injected"]
report["canonical_updated_count"] = _injection_stats["canonical_updated"]
```

---

## File: tests/unit/workers/test_w6_seo_hardening.py

### Change 4: Add `test_seo_report_includes_injection_counts` to `TestSeoFieldInjection`

Test uses a page with NO description and STALE canonical to exercise both injection
paths. Asserts both `description_injected_count >= 1` and `canonical_updated_count >= 1`
in the written `seo_report.json`.
