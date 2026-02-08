# TC-1050-T4: Add File Size Cap for Memory Safety

**Status**: Complete
**Owner**: Agent-B
**Created**: 2026-02-08
**Parent**: TC-1050 W2 Intelligence Refinements

## Objective
Add MAX_FILE_SIZE_MB check to prevent processing very large files that could cause memory issues.

## Context
Current implementation processes all discovered documents and examples without file size limits. A 3.3MB PDF was observed during testing. While this succeeded, larger files (e.g., 50MB+ documentation PDFs) could cause memory exhaustion or significant performance degradation.

## Scope
- `src/launch/workers/w2_facts_builder/map_evidence.py` (EDIT)
- `tests/unit/workers/test_tc_412_map_evidence.py` (ADD test)

## Acceptance Criteria
- [x] MAX_FILE_SIZE_MB constant added (default: 5MB)
- [x] File size check before reading in `_load_and_tokenize_files()`
- [x] Warning logged for skipped files with file path and size
- [x] Configurable via W2_MAX_FILE_SIZE_MB environment variable
- [x] Test coverage for large file skip behavior
- [x] All existing tests pass (228 W2 tests)
- [x] No performance regression

## Implementation Plan
1. Add MAX_FILE_SIZE_MB constant with env var override
2. Add file size check in `_load_and_tokenize_files()` before reading
3. Log warning with structured logging for skipped files
4. Add test with monkeypatch for small size limit
5. Verify no regression in pilot runs

## Allowed Paths
```yaml
allowed_paths:
  - src/launch/workers/w2_facts_builder/map_evidence.py
  - tests/unit/workers/test_tc_412_map_evidence.py
  - plans/taskcards/TC-1050-T4_file_size_cap.md
  - plans/taskcards/INDEX.md
  - reports/agents/agent_b/TC-1050-T4/**
```

## Evidence Required
- [x] Code diff for map_evidence.py showing size check
- [x] New test implementation
- [x] Test execution results (new test + full W2 suite)
- [x] Verification of warning logs for oversized files

## Results
- **Implementation**: 18 lines added to `map_evidence.py` (constant + size check)
- **Tests**: 3 new tests added (93 lines), all passing
- **Test Results**: 228/228 W2 tests passing (3.11s runtime)
- **12D Self-Review**: 60/60 (perfect score, all dimensions >= 4/5)
- **Evidence Bundle**: Complete in `reports/agents/agent_b/TC-1050-T4/`

## Spec Reference
- `specs/03_product_facts_and_evidence.md`: Evidence mapping performance requirements
- `specs/30_ai_agent_governance.md`: Agent task execution contract

## Ruleset Version
- v1.0 (specs/rulesets/ruleset.v1.yaml)

## Dependencies
- None (isolated change)

## Risks
- **Low**: Simple guard clause addition
- **Mitigation**: Test with both small and normal-sized files

## Notes
- Default 5MB limit balances memory safety with practical doc sizes
- Environment variable allows override for special cases
- Warning logs provide visibility into skipped files
