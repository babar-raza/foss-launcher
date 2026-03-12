# SRI-03: Remove Dead Code from Ported Intake Modules

**Status:** Not Started
**Gap linkage:** Intake port self-review, Dimension 4 (Code Quality)
**Role:** Cleanup
**Scope:** Remove unused code carried over from v1 port

---

## Problem

`config_generator.py` contains `_PLATFORM_TO_FAMILY` dict that was used in v1 but is never referenced in v2. There may be other v1 artifacts (stale comments referencing v1 paths, unused imports) across the 5 ported modules.

## Acceptance Checks

- [ ] `_PLATFORM_TO_FAMILY` removed from `config_generator.py` (or justified if still needed)
- [ ] No unused imports in any of the 5 intake modules
- [ ] No stale v1 path references (`launch.intake`, `src/launch/`)
- [ ] All tests still pass after cleanup

## Deliverables

1. Cleaned `src/launcher/intake/config_generator.py`
2. Audit results for other 4 modules (org_scanner, repo_classifier, scheduler, config_loader)

## Hard Rules

- Only remove provably dead code — verify with grep before deleting
- Do not refactor working code

## Review Dimensions

- Dead code elimination completeness
- No false positives (don't remove code that IS used)

## Runbook

1. Grep for `_PLATFORM_TO_FAMILY` across codebase — confirm zero references
2. Run `pylint --disable=all --enable=W0611` (unused imports) on all 5 modules
3. Grep for `launch.intake` or `src/launch` references
4. Remove dead code
5. Run tests
