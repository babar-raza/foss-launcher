# TC-1001 Evidence: Make cross_links Absolute URLs in W4

## Summary

Modified the `add_cross_links()` function in W4 IAPlanner to generate absolute URLs (https://...) instead of relative url_path values for cross-subdomain navigation.

## Changes Made

### 1. Import Added (worker.py line ~51)
```python
from ...resolvers.public_urls import build_absolute_public_url
```

### 2. Function Signature Updated (worker.py line ~1536)
```python
def add_cross_links(
    pages: List[Dict[str, Any]],
    product_slug: str = "3d",
    platform: str = "python",
) -> None:
```

### 3. Cross-link Generation Updated
Changed from:
```python
page["cross_links"] = [p["url_path"] for p in by_section["reference"][:2]]
```

To:
```python
page["cross_links"] = [
    build_absolute_public_url(
        section=p["section"],
        family=product_slug,
        locale="en",
        platform=platform,
        slug=p["slug"],
    )
    for p in by_section["reference"][:2]
]
```

Same pattern applied to:
- docs -> reference (line ~1571)
- kb -> docs (line ~1583)
- blog -> products (line ~1595)

### 4. Call Site Updated (worker.py line ~2877)
```python
add_cross_links(all_pages, product_slug=product_slug, platform=platform)
```

### 5. Test Updated (test_tc_430_ia_planner.py)
- Added `slug` field to test page dicts
- Updated assertions to verify absolute URLs with correct subdomain

## Test Results

```
============================= test session starts =============================
collected 33 items

tests\unit\workers\test_tc_430_ia_planner.py ........................... [ 81%]
......                                                                   [100%]

======================== 33 passed, 1 warning in 0.74s ========================
```

## Verification

Cross-links now generate absolute URLs:
- docs pages -> `https://reference.aspose.org/<family>/<platform>/<slug>/`
- kb pages -> `https://docs.aspose.org/<family>/<platform>/<slug>/`
- blog pages -> `https://products.aspose.org/<family>/<platform>/<slug>/`

## Files Modified

1. `src/launch/workers/w4_ia_planner/worker.py`
   - Added import for `build_absolute_public_url`
   - Modified `add_cross_links()` signature to accept `product_slug` and `platform`
   - Updated cross-link generation to use `build_absolute_public_url()`
   - Updated call site at line ~2877

2. `tests/unit/workers/test_tc_430_ia_planner.py`
   - Updated `test_add_cross_links()` to include `slug` in page dicts
   - Updated function call with `product_slug` and `platform` args
   - Added assertions verifying absolute URL format

## Spec Compliance

- specs/33_public_url_mapping.md: Uses `build_absolute_public_url()` for correct subdomain mapping
- specs/06_page_planning.md: Cross-linking rules unchanged (docs->reference, kb->docs, blog->products)
