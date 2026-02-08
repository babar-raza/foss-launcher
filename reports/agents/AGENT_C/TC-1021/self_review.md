# TC-1021 Self-Review: 12-Dimension Assessment

## Task: Update run_config Schema + Model for Configurable Ingestion

### Dimension Scores

| # | Dimension | Score | Notes |
|---|-----------|-------|-------|
| 1 | Spec fidelity | 5/5 | Schema fields exactly match specs/02 (scan_directories, gitignore_mode) and specs/05 (example_directories). Defaults match spec requirements. |
| 2 | Schema compliance | 5/5 | JSON schema is valid. All 6 fields have correct types, defaults, and descriptions. additionalProperties=false enforced. ingestion is optional (not in required array). |
| 3 | Backward compatibility | 5/5 | All existing pilot configs load without modification. No required fields added. to_dict() omits ingestion when None. 3 pilot configs tested. |
| 4 | Determinism | 5/5 | Round-trip test passes. JSON sort_keys=True. PYTHONHASHSEED=0 used for all runs. No timestamps, random values, or environment-dependent outputs. |
| 5 | Test coverage | 5/5 | 42 tests covering: backward compat (3), ingestion section handling (4), helper defaults with None (6), helper defaults with {} (6), configured values (6), boolean edge cases (4), schema validation (10), pilot config compat (3). |
| 6 | Error handling | 5/5 | All helpers handle: ingestion=None, ingestion={}, missing sub-keys, explicit False vs None for booleans. No exceptions possible from helper methods. |
| 7 | Code quality | 5/5 | Helpers follow existing model patterns. Docstrings reference specs. Type hints present. Follows project conventions (Optional[Dict], .get() with defaults). |
| 8 | Write fence | 5/5 | Only modified allowed_paths: schema, model, tests, taskcard, evidence. No shared library modifications. |
| 9 | Evidence completeness | 5/5 | Evidence includes: files changed, schema changes, model changes, test results, backward compat verification, determinism verification, spec alignment table, commands run. |
| 10 | Security | 5/5 | No secrets, no network calls, no file system access outside allowed paths. Pure data model changes. |
| 11 | Documentation | 5/5 | Docstrings on all helper methods reference spec sections. Schema has description fields. Taskcard fully populated per contract. |
| 12 | Integration readiness | 5/5 | W1/W2/W3 workers can immediately use `rc.get_scan_directories()`, `rc.get_gitignore_mode()`, `rc.get_example_directories()` etc. No breaking changes to existing callers. |

### Overall: 60/60

### Fix Plan

No dimensions scored below 4. No fixes needed.

### Reviewer Notes

- The `ingestion` field is a Dict[str, Any] rather than a typed dataclass. This follows the existing pattern used by `hugo`, `platform_hints`, `repo_hints`, and other optional object fields in RunConfig. A typed dataclass could be introduced later if the field set stabilizes.
- Boolean helpers use `val is not None` check rather than truthiness to correctly handle `False` values (tested with explicit edge cases).
- The `or` pattern in list/string helpers (e.g., `self.ingestion.get("scan_directories") or ["."]`) correctly handles both `None` and empty-list cases, returning the default in both situations. This is intentional: an empty scan_directories should fall back to scanning the root.
