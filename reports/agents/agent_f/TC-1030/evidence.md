# TC-1030: Typed Artifact Models -- Foundation -- Evidence Report

**Agent**: agent-f
**Taskcard**: TC-1030
**Date**: 2026-02-07
**Status**: Complete

## Files Changed/Added

### New model files (6 files)
1. `src/launch/models/repo_inventory.py` -- RepoInventory, RepoFingerprint, RepoProfile, PhantomPath, DocEntrypointDetail, PublicApiScope
2. `src/launch/models/site_context.py` -- SiteContext, RepoRef, HugoConfigFile, BuildMatrixEntry, HugoConfig
3. `src/launch/models/frontmatter.py` -- FrontmatterContract, SectionContract
4. `src/launch/models/hugo_facts.py` -- HugoFacts
5. `src/launch/models/truth_lock.py` -- TruthLockReport, TruthLockPage, Issue
6. `src/launch/models/ruleset.py` -- Ruleset, StyleRules, TruthRules, EditingRules, HugoRules, ClaimsRules, MandatoryPage, OptionalPagePolicy, StyleBySection, LimitsBySection, SectionConfig, SectionOverride, FamilyOverride

### Modified files (1 file)
7. `src/launch/models/__init__.py` -- Added imports and __all__ exports for all 6 new models

### New test files (6 files)
8. `tests/unit/models/test_repo_inventory.py` -- 19 tests
9. `tests/unit/models/test_site_context.py` -- 15 tests
10. `tests/unit/models/test_frontmatter.py` -- 12 tests
11. `tests/unit/models/test_hugo_facts.py` -- 9 tests
12. `tests/unit/models/test_truth_lock.py` -- 14 tests
13. `tests/unit/models/test_ruleset.py` -- 27 tests

### Taskcard and reports (3 files)
14. `plans/taskcards/TC-1030_typed_artifact_models_foundation.md`
15. `reports/agents/agent_f/TC-1030/evidence.md`
16. `reports/agents/agent_f/TC-1030/self_review.md`

## Commands Run

```
# Model-specific tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/models/ -v
# Result: 122 passed, 0 failed, 1 warning in 0.49s

# Full test suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
# Result: 2045 passed, 12 skipped, 0 failed in 77.57s
```

## Test Results

- **Model tests**: 122 passed (including 96 new tests from TC-1030)
- **Full suite**: 2045 passed, 12 skipped, 0 failures
- **Regressions**: None

## Design Decisions

### 1. Follow Artifact base class pattern
All 6 models extend `Artifact` (which extends `BaseModel`), getting `to_json()`, `from_json()`, `load()`, `save()`, and `validate_schema()` for free.

### 2. Typed sub-component classes
Complex nested objects are modeled as separate classes rather than raw dicts:
- RepoInventory: RepoFingerprint, RepoProfile, PhantomPath, DocEntrypointDetail, PublicApiScope
- SiteContext: RepoRef, HugoConfigFile, BuildMatrixEntry, HugoConfig
- FrontmatterContract: SectionContract
- TruthLockReport: TruthLockPage, Issue
- Ruleset: StyleRules, TruthRules, EditingRules, HugoRules, ClaimsRules, SectionConfig, SectionOverride, FamilyOverride, MandatoryPage, OptionalPagePolicy, StyleBySection, LimitsBySection

### 3. Deterministic serialization
All `to_dict()` methods produce sorted keys for dicts and sorted lists where semantically appropriate (languages, paths, claim_ids, etc.). This satisfies specs/10_determinism_and_caching.md.

### 4. Schema fidelity
Each model's fields match the corresponding JSON schema in specs/schemas/. Required vs optional fields match schema definitions. Validation methods check types, required fields, and enum constraints.

### 5. Graceful missing-field handling
`from_dict()` uses `data.get()` with appropriate defaults for all optional fields. Required fields use `data["key"]` to fail-fast with clear KeyError.

### 6. YAML loading for Ruleset
Ruleset includes `load_from_yaml()` class method since the canonical ruleset is stored as YAML. Uses `yaml.safe_load` for security.

## Deterministic Verification

1. Ran `to_dict()` twice on same objects, verified identical output
2. Tested sorted keys in all dict serializations
3. Tested sorted lists for languages, paths, claim_ids, shortcodes, weasel_words
4. Round-trip tests verify from_dict(to_dict()) preserves all data
5. JSON round-trip tests verify from_json(to_json()) preserves all data
6. PYTHONHASHSEED=0 used for all test runs
