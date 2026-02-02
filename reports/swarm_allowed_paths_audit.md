# Allowed Paths Overlap Audit Report

**Generated**: 2026-01-22

## Summary

- **Total unique path patterns**: 253
- **Overlapping path patterns**: 19
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

❌ **2 CRITICAL overlap(s) found** - MUST BE FIXED:

### `src/launch/workers/_git/clone_helpers.py`

Used by: TC-401, TC-921

### `src/launch/workers/w4_ia_planner/worker.py`

Used by: TC-701, TC-902, TC-925, TC-926

**Required action**: Remove critical overlaps immediately.
Critical paths (zero tolerance for overlaps):
- All `src/**` paths
- Repo-root files: README.md, Makefile, pyproject.toml, .gitignore

## All Path Overlaps (Including Non-Critical)

ℹ️ **19 path pattern(s) used by multiple taskcards**:

### `.github/workflows/ci.yml` - ℹ️ Non-critical

Used by: TC-100, TC-601

### `plans/taskcards/INDEX.md` - ℹ️ Non-critical

Used by: TC-603, TC-604, TC-633, TC-900, TC-901, TC-902, TC-903, TC-910, TC-920, TC-921, TC-922, TC-923, TC-924, TC-925, TC-926, TC-928

### `plans/taskcards/STATUS_BOARD.md` - ℹ️ Non-critical

Used by: TC-604, TC-633, TC-900, TC-901, TC-902, TC-903, TC-910, TC-920, TC-921, TC-922, TC-923, TC-924, TC-925, TC-926, TC-928

### `plans/taskcards/TC-520_pilots_and_regression.md` - ℹ️ Non-critical

Used by: TC-603, TC-604

### `plans/taskcards/TC-522_pilot_e2e_cli.md` - ℹ️ Non-critical

Used by: TC-603, TC-604

### `plans/taskcards/TC-901_ruleset_max_pages_and_section_style.md` - ℹ️ Non-critical

Used by: TC-901, TC-910

### `plans/taskcards/TC-902_w4_template_enumeration_with_quotas.md` - ℹ️ Non-critical

Used by: TC-902, TC-910

### `plans/taskcards/TC-903_vfv_harness_strict_2run_goldenize.md` - ℹ️ Non-critical

Used by: TC-903, TC-910

### `plans/taskcards/TC-924_add_legacy_foss_pattern_to_validator.md` - ℹ️ Non-critical

Used by: TC-924, TC-928

### `plans/taskcards/TC-925_fix_w4_load_and_validate_run_config_signature.md` - ℹ️ Non-critical

Used by: TC-925, TC-928

### `scripts/run_multi_pilot_vfv.py` - ℹ️ Non-critical

Used by: TC-703, TC-903, TC-920

### `scripts/run_pilot_vfv.py` - ℹ️ Non-critical

Used by: TC-703, TC-900, TC-903, TC-920

### `specs/06_page_planning.md` - ℹ️ Non-critical

Used by: TC-700, TC-901

### `specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml` - ℹ️ Non-critical

Used by: TC-632, TC-900

### `src/launch/workers/_git/clone_helpers.py` - ❌ CRITICAL

Used by: TC-401, TC-921

### `src/launch/workers/w4_ia_planner/worker.py` - ❌ CRITICAL

Used by: TC-701, TC-902, TC-925, TC-926

### `tests/e2e/test_tc_903_vfv.py` - ℹ️ Non-critical

Used by: TC-903, TC-920

### `tests/unit/workers/test_tc_401_clone.py` - ℹ️ Non-critical

Used by: TC-401, TC-921

### `tests/unit/workers/test_tc_480_pr_manager.py` - ℹ️ Non-critical

Used by: TC-480, TC-631

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
