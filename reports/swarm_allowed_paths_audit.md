# Allowed Paths Overlap Audit Report

**Generated**: 2026-01-22

## Summary

- **Total unique path patterns**: 160
- **Overlapping path patterns**: 0
- **Shared library violations**: 0

## Shared Library Single-Writer Enforcement

The following directories require single-writer governance:

- `src/launch/io/**` - Owner: TC-200
- `src/launch/util/**` - Owner: TC-200
- `src/launch/models/**` - Owner: TC-250
- `src/launch/clients/**` - Owner: TC-500

## Shared Library Violations

✓ **No violations found** - All taskcards respect single-writer rules
## Critical Path Overlap Analysis (Zero Tolerance)

✓ **No critical overlaps** - All src/** and repo-root files have single ownership
## All Path Overlaps (Including Non-Critical)

✓ **No overlapping paths** - All taskcards have isolated allowed_paths
## Recommendations

### High Priority

1. **Fix shared library violations** immediately
2. **Review implementation code overlaps** - ensure no merge conflicts possible
3. **Tighten path patterns** - use specific patterns over wildcards where possible

### Medium Priority

1. **Split overlapping test directories** - use `tests/unit/<module>/test_<tc_id>_*.py` pattern
2. **Document intentional overlaps** - add comments in taskcard frontmatter

### Low Priority

1. **Monitor reports/** overlap** - acceptable as long as each TC has unique subdirectory

## Audit Trail

This audit was performed by `tools/audit_allowed_paths.py` on 2026-01-22.
Re-run after updating taskcard frontmatter to verify fixes.

**Command**: `python tools/audit_allowed_paths.py`
