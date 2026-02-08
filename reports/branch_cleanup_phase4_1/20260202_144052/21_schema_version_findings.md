# schema_version Investigation Findings

## Issue Summary
4 W4 IA Planner tests fail with `KeyError: 'schema_version'` at `src/launch/models/run_config.py:174`

## Root Cause
`RunConfig.from_dict()` directly accesses `data["schema_version"]` without checking if the key exists. Test fixtures in `test_tc_430_ia_planner.py` don't include `schema_version` in the mock run_config.

## schema_version Contract (from base.py:115)
Per `specs/01_system_contract.md`, all artifacts must include `schema_version`. The `Artifact` base class requires it in `__init__`.

## Current Usage Pattern
- **Standard value**: "1.0" is most common across codebase
- **Variants**: Some tests use "1.0.0" or "v1.0"
- **All other models**: ProductFacts, State, etc. use `data.get("schema_version", ...)` pattern or have schema_version in their fixtures

## Failing Test Fixture
`mock_run_config` fixture (line 189-195 in test_tc_430_ia_planner.py):
```python
{
    "run_id": "test_run_001",
    "github_repo_url": "...",
    "github_ref": "main",
}
```
Missing: `schema_version` field

## Recommended Fix
**Two-part approach for backward compatibility:**

### A) Update RunConfig.from_dict() (run_config.py:174)
Change:
```python
schema_version=data["schema_version"],
```
To:
```python
schema_version=data.get("schema_version", "1.0"),
```

Add logging to warn when defaulting (helps identify legacy configs):
```python
import logging
logger = logging.getLogger(__name__)

# In from_dict()
if "schema_version" not in data:
    logger.warning("schema_version missing from run_config, defaulting to '1.0'")
```

### B) Update W4 Test Fixtures
Add `"schema_version": "1.0"` to all mock_run_config usages in test_tc_430_ia_planner.py

## Default Value Rationale
- Use "1.0" (not "1.0.0" or "v1.0") to match the most common pattern
- Consistent with what W4 worker outputs (line 1110 in w4_ia_planner/worker.py)
- Matches conftest.py:68 which uses "1.0" for shared fixtures

## Impact
- **Tests**: 4 failing tests will pass
- **Runtime**: Real-world configs without schema_version won't crash (degraded gracefully with warning)
- **Contract**: Still enforces schema_version in output artifacts, only relaxes input validation
