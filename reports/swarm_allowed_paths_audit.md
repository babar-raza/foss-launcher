# Allowed Paths Overlap Audit Report

**Generated**: 2026-01-22

## Summary

- **Total unique path patterns**: 486
- **Overlapping path patterns**: 70
- **Shared library violations**: 5

## Shared Library Single-Writer Enforcement

The following directories require single-writer governance:

- `src/launch/io/**` - Owner: TC-200
- `src/launch/util/**` - Owner: TC-200
- `src/launch/models/**` - Owner: TC-250
- `src/launch/clients/**` - Owner: TC-500

## Shared Library Violations

⚠️ **5 taskcard(s) violate single-writer rules**:

### TC-1021

- Path `src/launch/models/run_config.py` overlaps with shared lib owned by TC-250

### TC-1030

- Path `src/launch/models/repo_inventory.py` overlaps with shared lib owned by TC-250
- Path `src/launch/models/site_context.py` overlaps with shared lib owned by TC-250
- Path `src/launch/models/frontmatter.py` overlaps with shared lib owned by TC-250
- Path `src/launch/models/hugo_facts.py` overlaps with shared lib owned by TC-250
- Path `src/launch/models/truth_lock.py` overlaps with shared lib owned by TC-250
- Path `src/launch/models/ruleset.py` overlaps with shared lib owned by TC-250
- Path `src/launch/models/__init__.py` overlaps with shared lib owned by TC-250

### TC-1031

- Path `src/launch/models/snippet_catalog.py` overlaps with shared lib owned by TC-250
- Path `src/launch/models/page_plan.py` overlaps with shared lib owned by TC-250
- Path `src/launch/models/patch_bundle.py` overlaps with shared lib owned by TC-250
- Path `src/launch/models/validation_report.py` overlaps with shared lib owned by TC-250
- Path `src/launch/models/pr_artifact.py` overlaps with shared lib owned by TC-250
- Path `src/launch/models/__init__.py` overlaps with shared lib owned by TC-250

### TC-1032

- Path `src/launch/io/artifact_store.py` overlaps with shared lib owned by TC-200
- Path `src/launch/io/__init__.py` overlaps with shared lib owned by TC-200

### TC-1033

- Path `src/launch/io/atomic.py` overlaps with shared lib owned by TC-200

**Required action**: Update the above taskcards to remove shared lib paths
from their `allowed_paths` unless they are the designated owner.

## Critical Path Overlap Analysis (Zero Tolerance)

❌ **16 CRITICAL overlap(s) found** - MUST BE FIXED:

### `pyproject.toml`

Used by: TC-100, TC-978

### `src/launch/models/__init__.py`

Used by: TC-1030, TC-1031

### `src/launch/workers/w1_repo_scout/clone.py`

Used by: TC-401, TC-976

### `src/launch/workers/w1_repo_scout/discover_docs.py`

Used by: TC-1022, TC-1024

### `src/launch/workers/w1_repo_scout/discover_examples.py`

Used by: TC-1023, TC-1024

### `src/launch/workers/w1_repo_scout/fingerprint.py`

Used by: TC-1024, TC-1025, TC-402

### `src/launch/workers/w1_repo_scout/worker.py`

Used by: TC-1023, TC-1024, TC-1025, TC-1033, TC-1034

### `src/launch/workers/w2_facts_builder/code_analyzer.py`

Used by: TC-1041, TC-1050-T1

### `src/launch/workers/w2_facts_builder/embeddings.py`

Used by: TC-1046, TC-1050-T3

### `src/launch/workers/w2_facts_builder/map_evidence.py`

Used by: TC-1013, TC-1046, TC-1050-T3, TC-412, UNKNOWN

### `src/launch/workers/w2_facts_builder/worker.py`

Used by: TC-1026, TC-1033, TC-1045, TC-410

### `src/launch/workers/w4_ia_planner/worker.py`

Used by: TC-1001, TC-1010, TC-1033, TC-902, TC-953, TC-957, TC-958, TC-959, TC-963, TC-964, TC-966, TC-967, TC-970, TC-972, TC-977, TC-980, TC-981, TC-984

### `src/launch/workers/w5_section_writer/worker.py`

Used by: TC-1033, TC-964, TC-973, TC-977, TC-982

### `src/launch/workers/w6_linker_and_patcher/worker.py`

Used by: TC-1000, TC-1033, TC-938, TC-952

### `src/launch/workers/w7_validator/worker.py`

Used by: TC-1033, TC-935, TC-974, TC-985

### `src/launch/workers/w9_pr_manager/worker.py`

Used by: TC-1033, TC-631

**Required action**: Remove critical overlaps immediately.
Critical paths (zero tolerance for overlaps):
- All `src/**` paths
- Repo-root files: README.md, Makefile, pyproject.toml, .gitignore

## All Path Overlaps (Including Non-Critical)

ℹ️ **70 path pattern(s) used by multiple taskcards**:

### `.github/workflows/ci.yml` - ℹ️ Non-critical

Used by: TC-100, TC-601

### `plans/taskcards/INDEX.md` - ℹ️ Non-critical

Used by: TC-1050-T1, TC-1050-T2, TC-1050-T3, TC-603, TC-604, TC-633, TC-900, TC-901, TC-902, TC-903, TC-910, TC-920, TC-921, TC-922, TC-923, TC-924, TC-925, TC-926, TC-928, TC-930, TC-931, TC-932, TC-934, TC-935, TC-936, TC-937, TC-939, TC-950, TC-951, TC-952, TC-953, TC-954, TC-955, TC-961, TC-962, TC-963, TC-964, TC-965, TC-966, TC-967, TC-970

### `plans/taskcards/STATUS_BOARD.md` - ℹ️ Non-critical

Used by: TC-604, TC-633, TC-900, TC-901, TC-902, TC-903, TC-910, TC-920, TC-921, TC-922, TC-923, TC-924, TC-925, TC-926, TC-928, TC-930, TC-931, TC-932, TC-934, TC-935, TC-936, TC-937, TC-950, TC-951, TC-952, TC-953, TC-954, TC-955

### `plans/taskcards/TC-520_pilots_and_regression.md` - ℹ️ Non-critical

Used by: TC-603, TC-604

### `plans/taskcards/TC-522_pilot_e2e_cli.md` - ℹ️ Non-critical

Used by: TC-603, TC-604

### `plans/taskcards/TC-681_w4_template_driven_page_enumeration_3d.md` - ℹ️ Non-critical

Used by: TC-681, TC-931

### `plans/taskcards/TC-901_ruleset_max_pages_and_section_style.md` - ℹ️ Non-critical

Used by: TC-901, TC-910

### `plans/taskcards/TC-902_w4_template_enumeration_with_quotas.md` - ℹ️ Non-critical

Used by: TC-902, TC-910

### `plans/taskcards/TC-903_vfv_harness_strict_2run_goldenize.md` - ℹ️ Non-critical

Used by: TC-903, TC-910

### `plans/taskcards/TC-924_add_legacy_foss_pattern_to_validator.md` - ℹ️ Non-critical

Used by: TC-924, TC-928

### `plans/taskcards/TC-925_fix_w4_load_and_validate_run_config_signature.md` - ℹ️ Non-critical

Used by: TC-925, TC-928, TC-932

### `plans/taskcards/TC-926_fix_w4_path_construction_blog_and_subdomains.md` - ℹ️ Non-critical

Used by: TC-926, TC-932

### `plans/taskcards/TC-930_fix_pilot1_3d_pinned_shas.md` - ℹ️ Non-critical

Used by: TC-930, TC-931

### `plans/taskcards/TC-935_make_validation_report_deterministic.md` - ℹ️ Non-critical

Used by: TC-935, TC-937

### `plans/taskcards/TC-936_stabilize_gate_l_secrets_scan_time.md` - ℹ️ Non-critical

Used by: TC-936, TC-937

### `pyproject.toml` - ❌ CRITICAL

Used by: TC-100, TC-978

### `reports/agents/AGENT_D/WS-VFV-001-002/**` - ℹ️ Non-critical

Used by: TC-961, TC-962

### `reports/agents/agent_d/TC-1022_1023/evidence.md` - ℹ️ Non-critical

Used by: TC-1022, TC-1023

### `reports/agents/agent_d/TC-1022_1023/self_review.md` - ℹ️ Non-critical

Used by: TC-1022, TC-1023

### `reports/agents/agent_d/TC-1024_1025/evidence.md` - ℹ️ Non-critical

Used by: TC-1024, TC-1025

### `reports/agents/agent_d/TC-1024_1025/self_review.md` - ℹ️ Non-critical

Used by: TC-1024, TC-1025

### `runs/tc938_content_20260203_121910/**` - ℹ️ Non-critical

Used by: TC-938, TC-940

### `scripts/run_multi_pilot_vfv.py` - ℹ️ Non-critical

Used by: TC-703, TC-903, TC-920, TC-950

### `scripts/run_pilot_vfv.py` - ℹ️ Non-critical

Used by: TC-703, TC-900, TC-903, TC-920, TC-950, TC-951

### `specs/03_product_facts_and_evidence.md` - ℹ️ Non-critical

Used by: TC-1020, TC-1040

### `specs/06_page_planning.md` - ℹ️ Non-critical

Used by: TC-1002, TC-700, TC-901, TC-940, TC-953, TC-971, TC-983

### `specs/07_section_templates.md` - ℹ️ Non-critical

Used by: TC-901, TC-940, TC-953, TC-971, TC-983

### `specs/08_content_distribution_strategy.md` - ℹ️ Non-critical

Used by: TC-971, TC-983

### `specs/09_validation_gates.md` - ℹ️ Non-critical

Used by: TC-971, TC-983

### `specs/21_worker_contracts.md` - ℹ️ Non-critical

Used by: TC-1002, TC-1020, TC-1040, TC-1100, TC-983

### `specs/40_storage_model.md` - ℹ️ Non-critical

Used by: TC-939, TC-955

### `specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json` - ℹ️ Non-critical

Used by: TC-1012, TC-630, TC-935, TC-998

### `specs/pilots/pilot-aspose-3d-foss-python/expected_validation_report.json` - ℹ️ Non-critical

Used by: TC-630, TC-935

### `specs/pilots/pilot-aspose-3d-foss-python/notes.md` - ℹ️ Non-critical

Used by: TC-630, TC-930, TC-935

### `specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml` - ℹ️ Non-critical

Used by: TC-632, TC-900, TC-930

### `specs/pilots/pilot-aspose-note-foss-python/expected_page_plan.json` - ℹ️ Non-critical

Used by: TC-1012, TC-935, TC-998

### `specs/rulesets/ruleset.v1.yaml` - ℹ️ Non-critical

Used by: TC-1011, TC-901, TC-940, TC-953, TC-983

### `specs/schemas/page_plan.schema.json` - ℹ️ Non-critical

Used by: TC-1002, TC-964, TC-971, TC-983

### `specs/schemas/ruleset.schema.json` - ℹ️ Non-critical

Used by: TC-901, TC-940, TC-953, TC-983

### `specs/schemas/run_config.schema.json` - ℹ️ Non-critical

Used by: TC-1021, TC-1040, TC-1100

### `src/launch/models/__init__.py` - ❌ CRITICAL

Used by: TC-1030, TC-1031

### `src/launch/workers/w1_repo_scout/clone.py` - ❌ CRITICAL

Used by: TC-401, TC-976

### `src/launch/workers/w1_repo_scout/discover_docs.py` - ❌ CRITICAL

Used by: TC-1022, TC-1024

### `src/launch/workers/w1_repo_scout/discover_examples.py` - ❌ CRITICAL

Used by: TC-1023, TC-1024

### `src/launch/workers/w1_repo_scout/fingerprint.py` - ❌ CRITICAL

Used by: TC-1024, TC-1025, TC-402

### `src/launch/workers/w1_repo_scout/worker.py` - ❌ CRITICAL

Used by: TC-1023, TC-1024, TC-1025, TC-1033, TC-1034

### `src/launch/workers/w2_facts_builder/code_analyzer.py` - ❌ CRITICAL

Used by: TC-1041, TC-1050-T1

### `src/launch/workers/w2_facts_builder/embeddings.py` - ❌ CRITICAL

Used by: TC-1046, TC-1050-T3

### `src/launch/workers/w2_facts_builder/map_evidence.py` - ❌ CRITICAL

Used by: TC-1013, TC-1046, TC-1050-T3, TC-412, UNKNOWN

### `src/launch/workers/w2_facts_builder/worker.py` - ❌ CRITICAL

Used by: TC-1026, TC-1033, TC-1045, TC-410

### `src/launch/workers/w4_ia_planner/worker.py` - ❌ CRITICAL

Used by: TC-1001, TC-1010, TC-1033, TC-902, TC-953, TC-957, TC-958, TC-959, TC-963, TC-964, TC-966, TC-967, TC-970, TC-972, TC-977, TC-980, TC-981, TC-984

### `src/launch/workers/w5_section_writer/worker.py` - ❌ CRITICAL

Used by: TC-1033, TC-964, TC-973, TC-977, TC-982

### `src/launch/workers/w6_linker_and_patcher/worker.py` - ❌ CRITICAL

Used by: TC-1000, TC-1033, TC-938, TC-952

### `src/launch/workers/w7_validator/worker.py` - ❌ CRITICAL

Used by: TC-1033, TC-935, TC-974, TC-985

### `src/launch/workers/w9_pr_manager/worker.py` - ❌ CRITICAL

Used by: TC-1033, TC-631

### `tests/e2e/test_tc_903_vfv.py` - ℹ️ Non-critical

Used by: TC-903, TC-920

### `tests/unit/io/**` - ℹ️ Non-critical

Used by: TC-1032, TC-200

### `tests/unit/models/**` - ℹ️ Non-critical

Used by: TC-1030, TC-1031, TC-250

### `tests/unit/workers/test_tc_401_clone.py` - ℹ️ Non-critical

Used by: TC-401, TC-921

### `tests/unit/workers/test_tc_402_fingerprint.py` - ℹ️ Non-critical

Used by: TC-1024, TC-1025, TC-402

### `tests/unit/workers/test_tc_410_facts_builder.py` - ℹ️ Non-critical

Used by: TC-1026, TC-410

### `tests/unit/workers/test_tc_412_map_evidence.py` - ℹ️ Non-critical

Used by: TC-412, UNKNOWN

### `tests/unit/workers/test_tc_430_ia_planner.py` - ℹ️ Non-critical

Used by: TC-1010, TC-1011, TC-430, TC-958

### `tests/unit/workers/test_tc_480_pr_manager.py` - ℹ️ Non-critical

Used by: TC-480, TC-631

### `tests/unit/workers/test_w2_code_analyzer.py` - ℹ️ Non-critical

Used by: TC-1041, TC-1050-T1

### `tests/unit/workers/test_w4_content_distribution.py` - ℹ️ Non-critical

Used by: TC-972, TC-980, TC-981

### `tests/unit/workers/test_w4_docs_token_generation.py` - ℹ️ Non-critical

Used by: TC-970, TC-981

### `tests/unit/workers/test_w4_template_enumeration_placeholders.py` - ℹ️ Non-critical

Used by: TC-966, TC-967

### `tests/unit/workers/test_w5_specialized_generators.py` - ℹ️ Non-critical

Used by: TC-973, TC-982

### `tests/unit/workers/test_w6_content_export.py` - ℹ️ Non-critical

Used by: TC-1000, TC-952

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
