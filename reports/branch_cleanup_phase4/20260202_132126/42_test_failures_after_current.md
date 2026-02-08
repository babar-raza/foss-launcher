# Test Failures After Current Branch Merge

## Summary

4 tests failed in tests/unit/workers/test_tc_430_ia_planner.py

All failures are the same issue: `KeyError: 'schema_version'`

## Failing Tests

1. test_execute_ia_planner_success
2. test_execute_ia_planner_deterministic_ordering
3. test_execute_ia_planner_event_emission
4. test_execute_ia_planner_schema_validation

## Root Cause

The RunConfig.from_dict() method expects a 'schema_version' key in the configuration dictionary, but the test data in test_tc_430_ia_planner.py does not include this field.

Error location: src\launch\models\run_config.py:174
```python
schema_version=data["schema_version"],
```

## Impact

This appears to be a test data incompatibility introduced during the merge. The feat/golden-2pilots-20260201 branch likely has fixes to W4 that changed the test structure, but the test data setup doesn't match.

## Next Steps

This requires investigation to determine:
1. Whether the schema_version field was added in tc300 or current branch
2. Whether the test fixtures need updating to include schema_version
3. Whether there are other similar incompatibilities

