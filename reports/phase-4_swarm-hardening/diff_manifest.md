# Phase 4 Swarm Hardening — Diff Manifest

**Date**: 2026-01-22

This manifest provides a detailed, file-by-file accounting of all changes made during Phase 4 Swarm Hardening.

## Files Created (7)

### 1. tools/validate_swarm_ready.py
**Purpose**: Unified validation command for all 6 swarm readiness gates
**Size**: ~199 lines
**Key features**:
- `GateRunner` class for executing validation gates
- Runs gates A1, A2, B, C, D, E in sequence
- Captures output and results
- Checks for warnings in Gate A2
- Provides summary with pass/fail status
- Returns exit code 0 only if all gates pass

### 2. reports/phase-4_swarm-hardening/ (directory)
**Purpose**: Phase 4 deliverable reports container

### 3. reports/phase-4_swarm-hardening/gate_outputs/ (directory)
**Purpose**: Stores gate validation outputs

### 4. reports/phase-4_swarm-hardening/gate_outputs/baseline_gates.txt
**Purpose**: Baseline gate validation results before Phase 4 changes
**Key finding**: Gate E showed 33 shared-library violations

### 5. reports/phase-4_swarm-hardening/gate_outputs/final_validation.txt
**Purpose**: Final gate validation results after Phase 4 changes
**Key finding**: Gate E shows 0 shared-library violations (down from 33)

### 6. reports/phase-4_swarm-hardening/change_log.md
**Purpose**: Chronological log of all Phase 4 changes

### 7. reports/phase-4_swarm-hardening/diff_manifest.md
**Purpose**: Detailed file-by-file manifest (this file)

## Files Modified

### Taskcard Files (36 total)

#### plans/taskcards/INDEX.md
**Changes**:
- Added TC-250 to Bootstrap section
- Positioned after TC-201, before TC-300

**Before**:
```yaml
## Bootstrap
- TC-100 — Bootstrap repo, toolchain, minimal skeleton
- TC-200 — Schemas and IO foundations
- TC-201 — Emergency mode flag (allow_manual_edits) and policy plumbing
- TC-300 — Orchestrator graph wiring and run loop
```

**After**:
```yaml
## Bootstrap
- TC-100 — Bootstrap repo, toolchain, minimal skeleton
- TC-200 — Schemas and IO foundations
- TC-201 — Emergency mode flag (allow_manual_edits) and policy plumbing
- TC-250 — Shared library governance and data models
- TC-300 — Orchestrator graph wiring and run loop
```

#### plans/taskcards/TC-100_bootstrap_repo.md
**Section modified**: `allowed_paths`
**Key changes**:
- Removed: `src/**`, `tests/**`
- Added specific paths: `pyproject.toml`, `src/launch/__init__.py`, `src/launch/__main__.py`, `scripts/bootstrap_check.py`, `.github/workflows/ci.yml`, `README.md`, `tests/unit/test_bootstrap.py`

#### plans/taskcards/TC-200_schemas_and_io.md
**Section modified**: `allowed_paths`
**Key changes**:
- Removed: `scripts/**`
- Added specific path: `scripts/validate_schemas.py`
- Retained ownership: `src/launch/io/**`, `src/launch/util/**`

#### plans/taskcards/TC-201_emergency_mode_manual_edits.md
**Section modified**: `allowed_paths`
**Key changes**:
- Removed: `src/launch/util/**`
- Kept specific policy module paths

#### plans/taskcards/TC-250_shared_libs_governance.md
**Section modified**: `allowed_paths`
**Key changes**:
- Removed: `src/launch/io/**`, `src/launch/util/**`
- Retained ownership: `src/launch/models/**`

#### plans/taskcards/TC-300_orchestrator_langgraph.md
**Section modified**: `allowed_paths`
**Key changes**:
- Removed: `src/launch/io/**`, `src/launch/util/**`
- Retained: `src/launch/orchestrator/**`, `src/launch/state/**`

#### plans/taskcards/TC-400_repo_scout_w1.md
**Section modified**: `allowed_paths`
**Key changes**:
- Removed: `src/launch/workers/w1_repo_scout.py`, `src/launch/util/**`, `src/launch/io/**`, `tests/**`
- Added: `src/launch/workers/w1_repo_scout/__init__.py`, `src/launch/workers/_git/__init__.py`, `tests/integration/test_tc_400_w1_integration.py`
- **Architecture change**: Epic now owns only integration glue, not implementation

#### plans/taskcards/TC-401_clone_and_resolve_shas.md
**Section modified**: `allowed_paths`
**Key changes**:
- Removed: shared worker module
- Added: `src/launch/workers/w1_repo_scout/clone.py`, `src/launch/workers/_git/clone_helpers.py`, `tests/unit/workers/test_tc_401_clone.py`
- **Architecture change**: Micro-taskcard owns specific module file

#### plans/taskcards/TC-402_repo_fingerprint_and_inventory.md
**Section modified**: `allowed_paths`
**Key changes**:
- Added: `src/launch/workers/w1_repo_scout/fingerprint.py`, `src/launch/adapters/repo_fingerprinter.py`, `tests/unit/workers/test_tc_402_fingerprint.py`

#### plans/taskcards/TC-403_frontmatter_contract_discovery.md
**Section modified**: `allowed_paths`
**Key changes**:
- Added: `src/launch/workers/w1_repo_scout/frontmatter.py`, `src/launch/adapters/frontmatter_parser.py`, `tests/unit/workers/test_tc_403_frontmatter.py`

#### plans/taskcards/TC-404_hugo_site_context_build_matrix.md
**Section modified**: `allowed_paths`
**Key changes**:
- Added: `src/launch/workers/w1_repo_scout/hugo_scan.py`, `src/launch/adapters/hugo_scanner.py`, `tests/unit/workers/test_tc_404_hugo_scan.py`

#### plans/taskcards/TC-410_facts_builder_w2.md
**Section modified**: `allowed_paths`
**Key changes**:
- Removed: `src/launch/workers/w2_facts_builder.py`, `src/launch/util/**`, `src/launch/io/**`, `tests/**`
- Added: `src/launch/workers/w2_facts_builder/__init__.py`, `tests/integration/test_tc_410_w2_integration.py`
- **Architecture change**: Epic now owns only integration glue

#### plans/taskcards/TC-411_facts_extract_catalog.md
**Section modified**: `allowed_paths`
**Key changes**:
- Added: `src/launch/workers/w2_facts_builder/facts_extract.py`, `src/launch/adapters/facts_extractor.py`, `tests/unit/workers/test_tc_411_facts_extract.py`

#### plans/taskcards/TC-412_evidence_map_linking.md
**Section modified**: `allowed_paths`
**Key changes**:
- Added: `src/launch/workers/w2_facts_builder/evidence_map.py`, `tests/unit/workers/test_tc_412_evidence_map.py`

#### plans/taskcards/TC-413_truth_lock_compile_minimal.md
**Section modified**: `allowed_paths`
**Key changes**:
- Added: `src/launch/workers/w2_facts_builder/truth_lock.py`, `tests/unit/workers/test_tc_413_truth_lock.py`

#### plans/taskcards/TC-420_snippet_curator_w3.md
**Section modified**: `allowed_paths`
**Key changes**:
- Removed: `src/launch/workers/w3_snippet_curator.py`, `src/launch/util/**`, `src/launch/io/**`, `tests/**`
- Added: `src/launch/workers/w3_snippet_curator/__init__.py`, `tests/integration/test_tc_420_w3_integration.py`
- **Architecture change**: Epic now owns only integration glue

#### plans/taskcards/TC-421_snippet_inventory_tagging.md
**Section modified**: `allowed_paths`
**Key changes**:
- Added: `src/launch/workers/w3_snippet_curator/inventory.py`, `src/launch/adapters/snippet_tagger.py`, `tests/unit/workers/test_tc_421_snippet_inventory.py`

#### plans/taskcards/TC-422_snippet_selection_rules.md
**Section modified**: `allowed_paths`
**Key changes**:
- Added: `src/launch/workers/w3_snippet_curator/selection.py`, `tests/unit/workers/test_tc_422_snippet_selection.py`

#### plans/taskcards/TC-430_ia_planner_w4.md
**Section modified**: `allowed_paths`
**Key changes**:
- Removed: `src/launch/util/**`, `src/launch/io/**`, `tests/**`
- Retained: `src/launch/workers/w4_ia_planner.py`
- Added specific: `tests/unit/workers/test_tc_430_ia_planner.py`

#### plans/taskcards/TC-440_section_writer_w5.md
**Section modified**: `allowed_paths`
**Key changes**:
- Removed: `src/launch/util/**`, `src/launch/io/**`, `tests/**`
- Retained: `src/launch/workers/w5_section_writer.py`
- Added specific: `tests/unit/workers/test_tc_440_section_writer.py`

#### plans/taskcards/TC-450_linker_and_patcher_w6.md
**Section modified**: `allowed_paths`
**Key changes**:
- Removed: `src/launch/util/**`, `src/launch/io/**`, `tests/**`
- Retained: `src/launch/workers/w6_linker_and_patcher.py`
- Added specific: `tests/unit/workers/test_tc_450_linker_patcher.py`

#### plans/taskcards/TC-460_validator_w7.md
**Section modified**: `allowed_paths`
**Key changes**:
- Removed: `src/launch/util/**`, `src/launch/io/**`, `tests/**`
- Retained: `src/launch/workers/w7_validator.py`, `src/launch/validation/**`
- Added specific: `tests/unit/workers/test_tc_460_validator.py`

#### plans/taskcards/TC-470_fixer_w8.md
**Section modified**: `allowed_paths`
**Key changes**:
- Removed: `src/launch/util/**`, `src/launch/io/**`, `tests/**`
- Retained: `src/launch/workers/w8_fixer.py`
- Added specific: `tests/unit/workers/test_tc_470_fixer.py`

#### plans/taskcards/TC-480_pr_manager_w9.md
**Section modified**: `allowed_paths`
**Key changes**:
- Removed: `src/launch/util/**`, `src/launch/io/**`, `src/launch/clients/**`, `tests/**`
- Retained: `src/launch/workers/w9_pr_manager.py`
- Added specific: `tests/unit/workers/test_tc_480_pr_manager.py`

#### plans/taskcards/TC-500_clients_services.md
**Section modified**: `allowed_paths`
**Key changes**:
- Removed: `src/launch/util/**`, `src/launch/io/**`, `tests/**`
- Retained ownership: `src/launch/clients/**`
- Added specific: `tests/unit/clients/**`

#### plans/taskcards/TC-510_mcp_server.md
**Section modified**: `allowed_paths`
**Key changes**:
- Removed: `src/launch/util/**`, `tests/**`
- Retained: `src/launch/mcp_server/**`
- Added specific: `tests/unit/mcp_server/**`

#### plans/taskcards/TC-520_pilots_and_regression.md
**Section modified**: `allowed_paths`
**Key changes**:
- Removed: `src/**`, `tests/**`, `reports/**`
- Added specific: `src/launch/pilots/**`, `tests/integration/pilots/**`, `reports/pilots/**`

#### plans/taskcards/TC-530_cli_entrypoints_and_runbooks.md
**Section modified**: `allowed_paths`
**Key changes**:
- Removed: `src/**`
- Added specific: `src/launch/cli/**`, `src/launch/__main__.py`, `scripts/cli_runner.py`, `docs/cli_usage.md`, `README.md`, `tests/unit/cli/test_tc_530_entrypoints.py`

#### plans/taskcards/TC-540_content_path_resolver.md
**Section modified**: `allowed_paths`
**Key changes**:
- Removed: `src/launch/util/content_paths.py` (was violation - TC-200 owns util)
- Added: `src/launch/resolvers/content_paths.py` (new dedicated directory)
- Added: `tests/unit/resolvers/test_tc_540_content_path_resolver.py`

#### plans/taskcards/TC-550_hugo_config_awareness_ext.md
**Section modified**: `allowed_paths`
**Key changes**:
- Removed: `src/launch/util/hugo_config.py` (was violation)
- Added: `src/launch/resolvers/hugo_config.py` (new dedicated directory)
- Added: `tests/unit/resolvers/test_tc_550_hugo_config.py`

#### plans/taskcards/TC-560_determinism_harness.md
**Section modified**: `allowed_paths`
**Key changes**:
- Removed: `src/launch/util/determinism.py`, `src/launch/util/hashing.py` (were violations)
- Added: `src/launch/tools/determinism.py`, `src/launch/tools/hashing.py` (new dedicated directory)
- Added: `tests/unit/tools/test_tc_560_determinism.py`

#### plans/taskcards/TC-570_validation_gates_ext.md
**Section modified**: `allowed_paths`
**Key changes**:
- Removed: `src/launch/util/frontmatter_validate.py`, `src/launch/util/linkcheck.py`, `src/launch/util/hugo_smoke.py` (were violations)
- Added: `src/launch/tools/validate.py`, `src/launch/tools/frontmatter_validate.py`, `src/launch/tools/linkcheck.py`, `src/launch/tools/hugo_smoke.py` (new dedicated directory)
- Added: `tests/unit/tools/test_tc_570_validation.py`

#### plans/taskcards/TC-571_policy_gate_no_manual_edits.md
**Section modified**: `allowed_paths`
**Key changes**:
- Removed: `src/launch/util/**`, `tests/**`
- Retained: `src/launch/validators/policy_gate.py`
- Added specific: `tests/unit/validators/test_tc_571_policy_gate.py`

#### plans/taskcards/TC-580_observability_and_evidence_bundle.md
**Section modified**: `allowed_paths`
**Key changes**:
- Removed: `src/launch/util/report_index.py` (was violation)
- Added: `src/launch/tools/evidence_bundle.py`, `src/launch/tools/report_index.py` (new dedicated directory)
- Added: `tests/unit/tools/test_tc_580_evidence_bundle.py`

#### plans/taskcards/TC-590_security_and_secrets.md
**Section modified**: `allowed_paths`
**Key changes**:
- Removed: `src/launch/util/redact.py`, `src/launch/util/logging.py` (were violations)
- Added: `src/launch/tools/secrets_scan.py`, `src/launch/tools/redact.py`, `src/launch/tools/secure_logging.py` (new dedicated directory)
- Added: `tests/unit/tools/test_tc_590_security.py`

#### plans/taskcards/TC-600_failure_recovery_and_backoff.md
**Section modified**: `allowed_paths`
**Key changes**:
- Removed: `src/launch/util/retry.py`, `src/launch/util/backoff.py`, `src/launch/util/step_state.py` (were violations)
- Added: `src/launch/recovery/retry.py`, `src/launch/recovery/step_state.py` (new dedicated directory)
- Added: `tests/unit/recovery/test_tc_600_recovery.py`

### Tooling Files (2 total)

#### tools/validate_taskcards.py
**Changes**:
1. Added shared libraries registry:
```python
SHARED_LIBS = {
    "src/launch/io/**": "TC-200",
    "src/launch/util/**": "TC-200",
    "src/launch/models/**": "TC-250",
    "src/launch/clients/**": "TC-500",
}
```

2. Added ultra-broad patterns registry:
```python
ULTRA_BROAD_PATTERNS = {
    "src/**",
    "src/launch/**",
    "tests/**",
    "scripts/**",
    ".github/**",
}
```

3. Added broad pattern allowlist (currently empty):
```python
BROAD_PATTERN_ALLOWLIST = {
    # No taskcards currently allowed broad patterns
}
```

4. Enhanced `validate_frontmatter()` to check each path for:
   - Shared library violations (exact match)
   - Shared library violations (prefix match)
   - Ultra-broad pattern usage
   - Provides detailed error messages with remediation guidance

#### tools/validate_swarm_ready.py
**Status**: NEW FILE (see "Files Created" section above)

### Report Files (2 total)

#### reports/sanity_checks.md
**Changes**:

1. **Gate 4: Allowed Paths and Overlaps** section:
   - Status changed from "PASSED WITH WARNINGS" to "PASSED"
   - Shared library violations: 33 → **0**
   - Added "Phase 4 Hardening Actions Completed" subsection documenting all 4 actions

2. **Python Environment Check** section:
   - Documented `jsonschema` as missing (will be fixed by TC-100)

3. **Commands Summary** section:
   - Updated to recommend `validate_swarm_ready.py` as primary validation command

#### reports/swarm_readiness_review.md
**Changes**:

1. **Executive Summary**:
   - Status changed to "🟢 GO"
   - Added "Phase 4 Hardening: COMPLETED"
   - Updated shared-lib violations: 33 → **0**

2. **Phase 4: Allowed Paths Hardening** section (new):
   - Replaced "Allowed Paths Overlap" section
   - Documented all 4 Phase 4 actions
   - Provided current status with 0 violations

### Governance Files (2 total)

#### plans/swarm_coordination_playbook.md
**Changes**:
Added new subsection "Critical Clarifications" under "Core Principles" section:

```markdown
### Critical Clarifications

**allowed_paths means WRITE fence only**:
- `allowed_paths` lists define which files a taskcard may **MODIFY/CREATE**
- Reading, importing, and using existing code is **ALWAYS allowed** for all taskcards
- Do NOT include shared libraries in `allowed_paths` just because you need to import/use them
- Example: If TC-401 needs to use `src/launch/io/write_json()`, it does NOT include `src/launch/io/**` in its `allowed_paths`

**Shared libs = owners only (zero tolerance)**:
- After Phase 4 hardening, repo enforces **zero shared-library write violations**
- Tooling (`validate_taskcards.py`, `validate_swarm_ready.py`) rejects violations
- No "acceptable overlap" exceptions - violations must be fixed before proceeding

**Preflight validation (mandatory)**:
- Before starting ANY taskcard implementation, run: `python tools/validate_swarm_ready.py`
- All gates must pass (Gate A1 may fail due to jsonschema - this will be fixed by TC-100)
- If Gate E fails (shared lib violations), repo is not ready for implementation
```

#### plans/taskcards/00_TASKCARD_CONTRACT.md
**Changes**:
Added new subsection "Critical clarifications" after "Core rules" section:

```markdown
### Critical clarifications

**allowed_paths = write fence only**:
- `allowed_paths` lists define which files a taskcard may **MODIFY or CREATE**
- Reading, importing, and using existing code is **ALWAYS allowed** for all taskcards
- Do NOT include shared libraries in `allowed_paths` just because you need to import/use them
- Example: If TC-401 needs to use `src/launch/io/write_json()`, it does NOT include `src/launch/io/**` in its `allowed_paths`

**Shared libraries = owners only (zero tolerance)**:
- After Phase 4 hardening, the repository enforces **zero shared-library write violations**
- Shared libraries and their designated owners:
  - `src/launch/io/**` → TC-200
  - `src/launch/util/**` → TC-200
  - `src/launch/models/**` → TC-250
  - `src/launch/clients/**` → TC-500
- Only the owner taskcard may include these paths in their `allowed_paths`
- Validation tooling (`validate_taskcards.py`, `validate_swarm_ready.py`) rejects violations
- No "acceptable overlap" exceptions permitted

**Preflight validation (mandatory)**:
- Before starting ANY taskcard implementation, run: `python tools/validate_swarm_ready.py`
- All gates must pass before proceeding (Gate A1 may fail due to missing `jsonschema` module - this will be resolved by TC-100)
- If Gate E fails (shared-lib violations), the repository is not ready for implementation work
- Gate failures indicate planning/specification issues that must be fixed first
```

## Summary Statistics

### Files Changed: 43 total
- **Created**: 7 files
  - 1 Python script (validate_swarm_ready.py)
  - 2 directories
  - 4 report/output files
- **Modified**: 36 files
  - 35 taskcards (100% of all taskcards)
  - 1 taskcard index
  - 1 validation tool
  - 2 status reports
  - 2 governance documents

### Lines Changed (Estimated)
- **Added**: ~700 lines
  - validate_swarm_ready.py: ~199 lines
  - Governance clarifications: ~60 lines
  - Report updates: ~140 lines
  - Change log: ~300 lines
- **Modified**: ~350 lines (allowed_paths sections across 35 taskcards)
- **Removed**: ~200 lines (ultra-broad patterns, shared-lib violations)

### Violations Resolved
- **Shared-lib violations**: 33 → 0 (100% reduction)
- **Ultra-broad patterns**: All eliminated or explicitly allowlisted
- **Micro-taskcard overlaps**: All resolved through module splitting

### Architecture Improvements
- **Worker families**: Changed from single-file to directory structure
- **Hardening utilities**: Moved from shared util/ to dedicated directories (resolvers/, tools/, recovery/)
- **Validation tooling**: Enhanced enforcement + unified command

## Verification Commands

To verify these changes:

```bash
# Run unified validation
python tools/validate_swarm_ready.py

# Check specific gates
python tools/validate_taskcards.py
python tools/audit_allowed_paths.py
python tools/check_markdown_links.py
python tools/generate_status_board.py
python scripts/validate_plans.py

# View before/after gate outputs
cat reports/phase-4_swarm-hardening/gate_outputs/baseline_gates.txt
cat reports/phase-4_swarm-hardening/gate_outputs/final_validation.txt
```

**Expected result**: All gates pass except Gate A1 (missing jsonschema - will be fixed by TC-100).

## Traceability

All changes traceable to:
- **Briefing document**: Phase 4 Swarm Hardening requirements
- **Gate E violations**: Baseline audit showing 33 shared-lib violations
- **Tooling requirements**: Enforce zero-tolerance policy
- **Governance needs**: Clarify write-fence semantics

**Status**: Phase 4 Swarm Hardening COMPLETE
