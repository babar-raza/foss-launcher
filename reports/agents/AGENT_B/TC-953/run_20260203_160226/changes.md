# TC-953: Page Inventory Contract and Quotas - Changes Documentation

## Summary of Changes

### 1. Ruleset Quota Updates
**File**: `specs/rulesets/ruleset.v1.yaml`

Changed section max_pages quotas to pilot-friendly values:

```yaml
# Before (production quotas)
sections:
  products:
    max_pages: 10
  docs:
    max_pages: 50
  reference:
    max_pages: 100
  kb:
    max_pages: 30
  blog:
    max_pages: 20

# After (pilot quotas)
sections:
  products:
    max_pages: 6      # ← Changed: 10 → 6
  docs:
    max_pages: 10     # ← Changed: 50 → 10
  reference:
    max_pages: 6      # ← Changed: 100 → 6
  kb:
    max_pages: 10     # ← Changed: 30 → 10
  blog:
    max_pages: 3      # ← Changed: 20 → 3
```

All min_pages values remain unchanged:
- products: min_pages=1
- docs: min_pages=2
- reference: min_pages=1
- kb: min_pages=3
- blog: min_pages=1

### 2. W4 IAPlanner Changes
**File**: `src/launch/workers/w4_ia_planner/worker.py`

#### Added Import
```python
# Line 48: Added YAML loading utility
from ...io.yamlio import load_yaml
```

#### New Function: load_ruleset_quotas
```python
def load_ruleset_quotas(repo_root: Path = None) -> Dict[str, Dict[str, int]]:
    """Load page quotas from ruleset.v1.yaml.

    Per specs/01_system_contract.md and specs/rulesets/, the ruleset defines
    per-section page quotas (min_pages, max_pages) that guide page planning.

    Args:
        repo_root: Path to repository root (auto-detected from worker location if None)

    Returns:
        Dictionary mapping section names to quota dictionaries with min_pages/max_pages keys

    Raises:
        IAPlannerError: If ruleset is missing or invalid
    """
    if repo_root is None:
        # Auto-detect repo root from this file's location
        repo_root = Path(__file__).parent.parent.parent.parent

    ruleset_path = repo_root / "specs" / "rulesets" / "ruleset.v1.yaml"
    if not ruleset_path.exists():
        raise IAPlannerError(f"Missing ruleset: {ruleset_path}")

    try:
        ruleset = load_yaml(ruleset_path)
        sections_config = ruleset.get("sections", {})

        # Extract quotas for each section
        quotas = {}
        for section, config in sections_config.items():
            quotas[section] = {
                "min_pages": config.get("min_pages", 1),
                "max_pages": config.get("max_pages", 10),
            }

        logger.info(f"[W4 IAPlanner] Loaded section quotas from ruleset: {quotas}")
        return quotas

    except Exception as e:
        raise IAPlannerError(f"Failed to load ruleset: {e}")
```

#### Modified execute_ia_planner Function
```python
# After loading input artifacts (line ~1086):
# Load section quotas from ruleset (TC-953)
repo_root = Path(__file__).parent.parent.parent.parent
section_quotas = load_ruleset_quotas(repo_root)

# Before (line ~1164):
# Apply quota (default: mandatory + up to 10 optional)
max_pages = 10 + len(mandatory)  # Allow mandatory + up to 10 optional

# After:
# Apply quota from ruleset (TC-953: respect section-specific max_pages)
quota = section_quotas.get(section, {"min_pages": 1, "max_pages": 10})
max_pages = quota.get("max_pages", 10)
```

### 3. New Unit Test File
**File**: `tests/unit/workers/test_w4_quota_enforcement.py` (created)

12 comprehensive unit tests:
- Test 1: Load ruleset quotas from YAML
- Test 2-6: Per-section quota enforcement
- Test 7: Total page count aggregation
- Test 8: Mandatory pages always included
- Test 9: Quota enforcement across launch tiers
- Test 10: Page count scaling comparison
- Test 11: Missing file error handling
- Test 12: Deterministic quota selection

## Impact Analysis

### Backward Compatibility
- No breaking changes to public APIs
- Ruleset loading is additive (new code path)
- Existing W4 functionality preserved for cases where templates don't exist

### Performance Impact
- Minimal: Single YAML file loaded once per W4 execution
- No impact on page generation speed or quality

### Testing Impact
- All existing tests still pass (22/22 W4 template tests)
- New tests verify quota enforcement (12/12 tests passing)
- Test coverage increased by ~400 lines

## Page Count Scaling

### Old Behavior (Production Quotas)
- Products: 10 pages max
- Docs: 50 pages max
- Reference: 100 pages max
- KB: 30 pages max
- Blog: 20 pages max
- **Total max: 210 pages**

### New Behavior (Pilot Quotas)
- Products: 6 pages max
- Docs: 10 pages max
- Reference: 6 pages max
- KB: 10 pages max
- Blog: 3 pages max
- **Total max: 35 pages**

### Pilot Minimum Pages
- Products: 1 page (mandatory overview)
- Docs: 2 pages (mandatory getting started + 1 how-to)
- Reference: 1 page (mandatory API overview)
- KB: 3 pages (mandatory FAQ, limitations, troubleshooting)
- Blog: 1 page (mandatory announcement)
- **Total min: 8 pages** (up from observed ~5)

## Validation Steps Completed
1. ✓ Ruleset syntax valid (YAML loads successfully)
2. ✓ W4 imports new functionality
3. ✓ New function `load_ruleset_quotas` works correctly
4. ✓ Quota application in template selection verified
5. ✓ All unit tests pass (12/12)
6. ✓ No regression in existing W4 tests (22/22 still pass)
7. ✓ Page count calculation verified (8 min, 35 max)

## Files Changed Summary

| File | Type | Lines Added | Lines Removed | Net Change |
|------|------|-------------|---------------|-----------|
| specs/rulesets/ruleset.v1.yaml | Modified | 0 | 0 | 5 lines changed |
| src/launch/workers/w4_ia_planner/worker.py | Modified | 51 | 1 | 50 lines added |
| tests/unit/workers/test_w4_quota_enforcement.py | Created | 400+ | - | New file |

**Total**: 1 modified, 1 enhanced, 1 created = 3 files affected
