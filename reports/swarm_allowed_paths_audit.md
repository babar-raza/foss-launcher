# Allowed Paths Overlap Audit Report

**Generated**: 2026-01-22

## Summary

- **Total unique path patterns**: 176
- **Overlapping path patterns**: 4
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

ℹ️ **4 path pattern(s) used by multiple taskcards**:

### `.github/workflows/ci.yml` - ℹ️ Non-critical

Used by: TC-100, TC-601

### `plans/taskcards/INDEX.md` - ℹ️ Non-critical

Used by: TC-603, TC-604

### `plans/taskcards/TC-520_pilots_and_regression.md` - ℹ️ Non-critical

Used by: TC-603, TC-604

### `plans/taskcards/TC-522_pilot_e2e_cli.md` - ℹ️ Non-critical

Used by: TC-603, TC-604

**Note**: Some overlap is acceptable for:
- Reports paths (each taskcard writes to its own subdirectory)
- Test paths (if properly scoped by module)

**Action required for critical overlaps only** (src/**, repo-root files).

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
