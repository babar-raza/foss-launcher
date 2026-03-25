# TC-3696 Evidence Report

## Changes Made

### New gate `gate_minimum_content_density.py` (order 55)
- Roles: workflow_page/how_to/getting_started=250, reference_object_page=150, blog_announcement=300
- Strips frontmatter + code fences before counting prose words
- ERROR severity, error_code G_MIN_CONTENT_DENSITY
- Registered in gates_registry.yaml

### Extended `gate_4_frontmatter_required_fields.py`
- Added `_check_placeholder_fields()`:
  - G4-PH-001: description in {"Template-driven docs page"} or starts with "Quick Start - "
  - G4-PH-002: claim_ids if present must be list of 64-char hex strings (null also rejected)
- Fixed: uses `"claim_ids" in frontmatter` to detect null values properly

### Validation engine tests updated
- Gate count: 54 → 55 in both test files
- `gate_minimum_content_density` added to expected_ids and _REGISTRY_ONLY_GATES

## Test Results

```
tests/unit/workers/w9/gates/test_tc3696_content_density_frontmatter.py  15 passed
```

Full suite:
```
8749 passed, 13 skipped, 3 xfailed, 47 warnings in 170.91s
```
(+15 tests from 8734 baseline)
