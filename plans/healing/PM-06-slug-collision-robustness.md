# PM-06: Slug Collision Robustness + Test

## Status: Done

## Gap Linkage: PM-G8, PM-G9

## Role
Senior engineer. Drop-in, production-ready.

## Context
`_class_name_to_slug()` falls back to `"reference-object"` when:
- The class name is empty
- The generated slug fails `validate_slug_safety()`

If multiple classes produce this same fallback slug, the existing
`_disambiguate_slugs()` function will append numeric suffixes (`reference-object`,
`reference-object-2`, etc.), which are meaningless and confusing. A better
fallback would incorporate a unique element (e.g., a hash or the raw lowercased
class name).

Additionally, two classes producing the same slug via CamelCase splitting
(e.g., `Cell` and `CELL` both produce `"cell"`) is untested.

## Scope

### Fix
1. Improve `_class_name_to_slug()` fallback to include a truncated hash or
   the lowercased class name with non-alphanumeric chars stripped, rather than
   a generic `"reference-object"` for all failures.
2. Add a test for two classes that produce the same slug (verified that
   `_disambiguate_slugs` resolves it).
3. Add a test for a class name that fails `validate_slug_safety()` (verify
   fallback is unique per class).

### Allowed paths
- `src/launcher/workers/planner/plan.py`
- `tests/test_planner_per_module.py`

### Forbidden
- Any other file/path

## Acceptance checks

### CLI
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_planner_per_module.py -v` — all pass

### Tests
- New test: `test_slug_collision_two_same_name_classes` — two classes producing
  same slug both get unique page_ids after disambiguation
- New test: `test_slug_fallback_is_unique_per_class` — two classes failing
  safety check produce different fallback slugs
- Existing tests pass

### Config respected end-to-end
- N/A

### No mock data in production paths
- N/A

## Deliverables
- Modified `src/launcher/workers/planner/plan.py`: improved fallback in
  `_class_name_to_slug()`
- Modified `tests/test_planner_per_module.py`: 2 new test methods

## Hard rules
- Keep public signatures unchanged
- Deterministic fallback (no random elements — use hash of class name)
- No network in offline tests
- Deterministic runs (PYTHONHASHSEED=0)
- No new deps

## Review dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Robustness | No two classes can silently produce identical fallback slugs |
| Correctness | Disambiguation works end-to-end through run_plan |
| Testability | Both collision and fallback paths tested |
| Minimality | Small improvement to fallback logic, no architectural changes |

## Now (runbook)

```bash
# 1. Improve fallback in _class_name_to_slug:
#    Instead of always returning "reference-object", return:
#      slug = f"ref-{cls_name.lower()[:20]}"
#      slug = re.sub(r"[^a-z0-9-]", "", slug)
#      if not slug or slug == "ref-":
#          slug = f"ref-{hashlib.md5(cls_name.encode()).hexdigest()[:8]}"

# 2. Add tests

# 3. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_planner_per_module.py -v

# 4. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```
