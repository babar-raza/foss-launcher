# TC-3687 Report — Skeleton Compliance Gate

## Summary
Wired `validate_against_skeleton()` (dead infrastructure from TC-3674)
into a new W9 gate `gate_skeleton_compliance.py` (order 51, warning severity).
Gate count: 50 → 51.

## Changes
- New `gate_skeleton_compliance.py`: Loads page_plan.json, maps files to roles,
  looks up skeleton from `PAGE_ROLE_SKELETONS`, calls `validate_against_skeleton()`.
  Error codes: `SKELETON_SECTION_MISSING`, `SKELETON_SEE_ALSO_POSITION`,
  `SKELETON_DUPLICATE_H2`. All severity `warning` (overlaps with G4).
- `gates_registry.yaml`: Added entry at order 51
- `gates/__init__.py`: Added to `__all__`
- Updated golden comparison tests to exclude registry-only gates

## Tests
- 14 new tests in `tests/unit/workers/w9/test_gate_skeleton_compliance.py`
  - `TestMissingRequiredSection` (3): missing overview, all present, multiple missing
  - `TestSeeAlsoPosition` (1): See Also not last warns
  - `TestDuplicateH2` (1): duplicate warns
  - `TestGracefulSkip` (4): no plan, unknown role, no site, empty role
  - `TestIndexSlugResolution` (1): _index.md parent dir
  - `TestClassifyErrorCode` (4): all code classifications

## Verification
- Full suite: 8617 passed, 0 failed (PYTHONHASHSEED=0)
