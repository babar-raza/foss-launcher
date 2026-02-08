# TC-985 Evidence Report

> Agent: Agent-B (Implementation)
> Taskcard: TC-985
> Date: 2026-02-05

## Objective

Add mandatory page presence validation (Rule 8) to W7 Gate 14, per specs/09_validation_gates.md Gate 14 rule 8 (TC-983).

## Files Changed

- `src/launch/workers/w7_validator/worker.py` (the only allowed path)

## Changes Made

### 1. Added `_load_ruleset_for_validation()` helper (lines 633-649)

Private helper function that loads `specs/rulesets/ruleset.v1.yaml` from repo root. Returns `None` if file is missing or YAML parsing fails (graceful degradation). Uses `yaml.safe_load` which was already imported in the module.

### 2. Updated `validate_content_distribution()` signature (lines 652-680)

Added optional `repo_root: Optional[Path] = None` parameter for backward compatibility. When `None`, the mandatory page check is skipped entirely, preserving existing behavior for all current callers that do not pass this argument.

### 3. Added Rule 8: Mandatory Page Presence check (lines 877-944)

At the end of `validate_content_distribution()`, after existing rules 1-7:
- Loads ruleset via `_load_ruleset_for_validation(repo_root)`
- Extracts `product_slug` from `page_plan`
- Imports `load_and_merge_page_requirements` from W4 (TC-984) for consistent merge logic
- Builds a lookup of existing pages per section from `page_plan.pages`
- Iterates sorted sections and their mandatory pages from merged config
- For each missing mandatory slug, emits an issue with:
  - `error_code`: `"GATE14_MANDATORY_PAGE_MISSING"`
  - `code`: `1411`
  - `severity`: `"warn"` for local profile, `"error"` for ci/prod
  - `message`: format matches spec: `"Mandatory page '{slug}' (page_role: {role}) missing from {section} section in page_plan"`
  - `suggested_fix`: `"Add mandatory page '{slug}' to W4 IAPlanner output for section '{section}'"`
  - `gate`: `"gate_14_content_distribution"`
  - `status`: `"OPEN"`

### 4. Updated Gate 14 call site in `execute_validator()` (lines 1081-1093)

Passes `repo_root=run_dir.parent.parent` to `validate_content_distribution()`, following the same pattern used by `gate_t_test_determinism()` (line 512). Added TC-985 to the Gate 14 comment.

## Commands Run

### Syntax check
```
python -c "import ast; ast.parse(open('src/launch/workers/w7_validator/worker.py', encoding='utf-8').read()); print('Syntax OK')"
```
Result: `Syntax OK`

### Existing test regression check
```
python -m pytest tests/unit/workers/test_w7_gate14.py -v
```
Result: `19 passed, 0 failed`

### Functional verification (inline tests)
7 custom tests executed:
1. **Backward compat (no repo_root)**: No mandatory issues emitted when `repo_root=None` -- PASS
2. **Missing pages detected**: 11 mandatory page issues found for product_slug=3d with minimal page_plan -- PASS
3. **Local profile severity**: All mandatory issues have `severity=warn` -- PASS
4. **CI profile severity**: All mandatory issues have `severity=error` -- PASS
5. **Issue structure**: `code=1411`, `suggested_fix` present, `gate=gate_14_content_distribution` -- PASS
6. **Family overrides**: `model-loading` detected as mandatory for 3d family (from family_overrides) -- PASS
7. **All present**: Zero mandatory issues when all mandatory pages exist in page_plan -- PASS

## Spec References

- specs/09_validation_gates.md lines 551-559 (Gate 14 Rule 8)
- specs/rulesets/ruleset.v1.yaml lines 47-129 (mandatory_pages + family_overrides)
- specs/09_validation_gates.md line 573 (GATE14_MANDATORY_PAGE_MISSING code 1411)

## Determinism Verification

- Sections are iterated in `sorted()` order (line 911)
- Mandatory pages within each section are iterated in ruleset order (deterministic YAML load order)
- Issue IDs use `f"gate14_mandatory_missing_{section_name}_{m_slug}"` -- deterministic based on section+slug
- No timestamps, random IDs, or environment-dependent outputs
