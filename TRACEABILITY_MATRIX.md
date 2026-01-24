# Traceability Matrix (Root-Level)

This file provides **root-level traceability** linking requirements to specs to plans to taskcards to acceptance checks.

> **Note**: A detailed spec-to-taskcard mapping already exists in [plans/traceability_matrix.md](plans/traceability_matrix.md). This file provides a higher-level view.

## Purpose

Ensure that:
1. Every important requirement has specification coverage
2. Every spec area has implementation coverage (taskcards)
3. Every taskcard has acceptance checks
4. Gaps are visible and documented

## High-Level Requirement → Spec → Plan Mapping

### REQ-001: Launch hundreds of products deterministically
- **Specs**:
  - [specs/00_overview.md](specs/00_overview.md) (scale requirement)
  - [specs/10_determinism_and_caching.md](specs/10_determinism_and_caching.md)
  - [specs/01_system_contract.md](specs/01_system_contract.md)
- **Plans**:
  - [plans/00_orchestrator_master_prompt.md](plans/00_orchestrator_master_prompt.md)
- **Key Taskcards**: TC-300 (orchestrator), TC-560 (determinism harness)
- **Acceptance**: Deterministic hashing, stable ordering, idempotent patches

### REQ-002: Adapt to diverse repository structures
- **Specs**:
  - [specs/02_repo_ingestion.md](specs/02_repo_ingestion.md) (repo profiling)
  - [specs/26_repo_adapters_and_variability.md](specs/26_repo_adapters_and_variability.md)
  - [specs/27_universal_repo_handling.md](specs/27_universal_repo_handling.md)
- **Plans**:
  - [plans/taskcards/INDEX.md](plans/taskcards/INDEX.md) (W1 RepoScout)
- **Key Taskcards**: TC-401, TC-402, TC-403, TC-404 (W1 micro-taskcards)
- **Acceptance**: Correct platform detection, archetype classification, adapter selection

### REQ-003: All claims must trace to evidence
- **Specs**:
  - [specs/03_product_facts_and_evidence.md](specs/03_product_facts_and_evidence.md)
  - [specs/04_claims_compiler_truth_lock.md](specs/04_claims_compiler_truth_lock.md)
  - [specs/23_claim_markers.md](specs/23_claim_markers.md)
- **Plans**:
  - [plans/taskcards/TC-410_facts_builder_w2.md](plans/taskcards/TC-410_facts_builder_w2.md)
- **Key Taskcards**: TC-411, TC-412, TC-413 (facts extraction, evidence linking, truth lock)
- **Acceptance**: EvidenceMap complete, TruthLock gate passes, claim markers present

### REQ-004: MCP endpoints for all features
- **Specs**:
  - [specs/14_mcp_endpoints.md](specs/14_mcp_endpoints.md)
  - [specs/24_mcp_tool_schemas.md](specs/24_mcp_tool_schemas.md)
- **Plans**:
  - [plans/taskcards/TC-510_mcp_server.md](plans/taskcards/TC-510_mcp_server.md)
- **Key Taskcards**: TC-510
- **Acceptance**: MCP server runs, tools exposed, schemas valid

### REQ-005: OpenAI-compatible LLM providers only
- **Specs**:
  - [specs/15_llm_providers.md](specs/15_llm_providers.md)
  - [specs/25_frameworks_and_dependencies.md](specs/25_frameworks_and_dependencies.md)
- **Plans**:
  - [plans/taskcards/TC-500_clients_services.md](plans/taskcards/TC-500_clients_services.md)
- **Key Taskcards**: TC-500
- **Acceptance**: No provider-specific APIs, configurable endpoint/model

### REQ-006: Centralized telemetry for all events
- **Specs**:
  - [specs/16_local_telemetry_api.md](specs/16_local_telemetry_api.md)
  - [specs/11_state_and_events.md](specs/11_state_and_events.md)
- **Plans**:
  - [plans/taskcards/TC-500_clients_services.md](plans/taskcards/TC-500_clients_services.md)
  - [plans/taskcards/TC-580_observability_and_evidence_bundle.md](plans/taskcards/TC-580_observability_and_evidence_bundle.md)
- **Key Taskcards**: TC-500, TC-580
- **Acceptance**: All events logged via HTTP API, event schemas valid

### REQ-007: Centralized GitHub commit service
- **Specs**:
  - [specs/17_github_commit_service.md](specs/17_github_commit_service.md)
  - [specs/12_pr_and_release.md](specs/12_pr_and_release.md)
- **Plans**:
  - [plans/taskcards/TC-480_pr_manager_w9.md](plans/taskcards/TC-480_pr_manager_w9.md)
- **Key Taskcards**: TC-480, TC-500
- **Acceptance**: All commits go through service, templates applied

### REQ-008: Hugo config awareness
- **Specs**:
  - [specs/31_hugo_config_awareness.md](specs/31_hugo_config_awareness.md)
  - [specs/18_site_repo_layout.md](specs/18_site_repo_layout.md)
- **Plans**:
  - [plans/taskcards/TC-404_hugo_site_context_build_matrix.md](plans/taskcards/TC-404_hugo_site_context_build_matrix.md)
  - [plans/taskcards/TC-550_hugo_config_awareness_ext.md](plans/taskcards/TC-550_hugo_config_awareness_ext.md)
- **Key Taskcards**: TC-404, TC-550
- **Acceptance**: Build matrix created, validation config-aware

### REQ-009: Validation gates with profiles
- **Specs**:
  - [specs/09_validation_gates.md](specs/09_validation_gates.md)
  - [specs/19_toolchain_and_ci.md](specs/19_toolchain_and_ci.md)
- **Plans**:
  - [plans/taskcards/TC-460_validator_w7.md](plans/taskcards/TC-460_validator_w7.md)
  - [plans/taskcards/TC-570_validation_gates_ext.md](plans/taskcards/TC-570_validation_gates_ext.md)

### REQ-010: Platform-aware content layout (V2)
- **Specs**:
  - [specs/32_platform_aware_content_layout.md](specs/32_platform_aware_content_layout.md) — **BINDING**
  - [specs/18_site_repo_layout.md](specs/18_site_repo_layout.md) (updated for V2)
  - [specs/20_rulesets_and_templates_registry.md](specs/20_rulesets_and_templates_registry.md) (platform template hierarchy)
- **Plans**:
  - [plans/taskcards/TC-540_content_path_resolver.md](plans/taskcards/TC-540_content_path_resolver.md) — platform-aware path resolution
  - [plans/taskcards/TC-403_frontmatter_contract_discovery.md](plans/taskcards/TC-403_frontmatter_contract_discovery.md) — V2 root detection
  - [plans/taskcards/TC-404_hugo_site_context_build_matrix.md](plans/taskcards/TC-404_hugo_site_context_build_matrix.md) — layout_mode resolution
  - [plans/taskcards/TC-570_validation_gates_ext.md](plans/taskcards/TC-570_validation_gates_ext.md) — content_layout_platform gate
- **Key Taskcards**: TC-540, TC-403, TC-404, TC-570
- **Acceptance**:
  - Products use `/{locale}/{platform}/` paths in V2 (NOT `/{platform}/` alone)
  - Auto-detection is deterministic (same filesystem → same result)
  - Platform layout gate blocks V2 violations
  - Templates include `__PLATFORM__` token and platform hierarchy
  - No unresolved `__PLATFORM__` tokens in generated content

### REQ-011: Idempotent patch engine
- **Specs**:
  - [specs/08_patch_engine.md](specs/08_patch_engine.md)
- **Plans**:
  - [plans/taskcards/TC-450_linker_and_patcher_w6.md](plans/taskcards/TC-450_linker_and_patcher_w6.md)
- **Key Taskcards**: TC-450, TC-540
- **Acceptance**: Patches apply cleanly, re-run produces same result, minimal diffs

### REQ-011: Two pilot projects for regression
- **Specs**:
  - [specs/13_pilots.md](specs/13_pilots.md)
  - [specs/pilots/README.md](specs/pilots/README.md)
- **Plans**:
  - [plans/taskcards/TC-520_pilots_and_regression.md](plans/taskcards/TC-520_pilots_and_regression.md)
- **Key Taskcards**: TC-520
- **Acceptance**: Both pilots produce golden outputs matching expectations

### REQ-012: No manual content edits
- **Specs**:
  - [specs/01_system_contract.md](specs/01_system_contract.md)
  - [plans/policies/no_manual_content_edits.md](plans/policies/no_manual_content_edits.md)
- **Plans**:
  - [plans/taskcards/TC-201_emergency_mode_manual_edits.md](plans/taskcards/TC-201_emergency_mode_manual_edits.md)
  - [plans/taskcards/TC-571_policy_gate_no_manual_edits.md](plans/taskcards/TC-571_policy_gate_no_manual_edits.md)
- **Key Taskcards**: TC-201, TC-571
- **Acceptance**: Policy gate enforces, emergency mode flag required for manual edits

### REQ-013: (Guarantee A) Input immutability - pinned commit SHAs
- **Specs**:
  - [specs/34_strict_compliance_guarantees.md](specs/34_strict_compliance_guarantees.md) (Guarantee A) — **BINDING**
  - [specs/schemas/run_config.schema.json](specs/schemas/run_config.schema.json)
- **Enforcement**:
  - Preflight: [tools/validate_pinned_refs.py](tools/validate_pinned_refs.py) (Gate J) — ✅ IMPLEMENTED
  - Runtime: `launch_validate` rejects floating refs in prod profile
- **Tests**: Validated by Gate J (inline tests in validation script)
- **Acceptance**: All `*_ref` fields use commit SHAs (no branches/tags) in production configs

### REQ-014: (Guarantee B) Hermetic execution boundaries
- **Specs**:
  - [specs/34_strict_compliance_guarantees.md](specs/34_strict_compliance_guarantees.md) (Guarantee B) — **BINDING**
  - [specs/29_project_repo_structure.md](specs/29_project_repo_structure.md) (RUN_DIR isolation)
- **Enforcement**:
  - Preflight: Gate J validates `allowed_paths` do not escape repo root
  - Runtime: [src/launch/util/path_validation.py](src/launch/util/path_validation.py) rejects path escapes — ✅ IMPLEMENTED
- **Tests**: [tests/unit/util/test_path_validation.py](tests/unit/util/test_path_validation.py) — ✅ IMPLEMENTED
- **Acceptance**: All file operations confined to RUN_DIR and allowed_paths, symlink escapes blocked

### REQ-015: (Guarantee C) Supply-chain pinning
- **Specs**:
  - [specs/34_strict_compliance_guarantees.md](specs/34_strict_compliance_guarantees.md) (Guarantee C) — **BINDING**
  - [specs/00_environment_policy.md](specs/00_environment_policy.md) (.venv policy)
  - [specs/19_toolchain_and_ci.md](specs/19_toolchain_and_ci.md)
- **Enforcement**:
  - Preflight: [tools/validate_supply_chain_pinning.py](tools/validate_supply_chain_pinning.py) (Gate K) — ✅ IMPLEMENTED
  - CI: Workflows use `uv sync --frozen`
- **Tests**: Validated by Gate K (inline tests in validation script)
- **Acceptance**: All installs use lock file, no ad-hoc `pip install`

### REQ-016: (Guarantee D) Network egress allowlist
- **Specs**:
  - [specs/34_strict_compliance_guarantees.md](specs/34_strict_compliance_guarantees.md) (Guarantee D) — **BINDING**
- **Enforcement**:
  - Preflight: [tools/validate_network_allowlist.py](tools/validate_network_allowlist.py) (Gate N) — ✅ IMPLEMENTED
  - Runtime: [src/launch/clients/http.py](src/launch/clients/http.py) enforces allowlist — ✅ IMPLEMENTED
- **Tests**: [tests/unit/clients/test_http.py](tests/unit/clients/test_http.py) — ✅ IMPLEMENTED
- **Acceptance**: All HTTP requests to allowlisted hosts only, unauthorized hosts blocked

### REQ-017: (Guarantee E) Secret hygiene / redaction
- **Specs**:
  - [specs/34_strict_compliance_guarantees.md](specs/34_strict_compliance_guarantees.md) (Guarantee E) — **BINDING**
- **Plans**:
  - [plans/taskcards/TC-590_security_and_secrets.md](plans/taskcards/TC-590_security_and_secrets.md)
- **Enforcement**:
  - Preflight: [tools/validate_secrets_hygiene.py](tools/validate_secrets_hygiene.py) (Gate L) — ✅ IMPLEMENTED
  - Runtime: Logging utilities redact secret patterns (PENDING implementation)
- **Tests**: Gate L validates no secrets in repository (STUB - needs enhancement for runtime logs)
- **Acceptance**: No secrets in logs/artifacts/reports, redaction verified

### REQ-018: (Guarantee F) Budget + circuit breakers
- **Specs**:
  - [specs/34_strict_compliance_guarantees.md](specs/34_strict_compliance_guarantees.md) (Guarantee F) — **BINDING**
  - [specs/schemas/run_config.schema.json](specs/schemas/run_config.schema.json) (budgets object) — ✅ IMPLEMENTED
- **Enforcement**:
  - Preflight: [tools/validate_budgets_config.py](tools/validate_budgets_config.py) (Gate O) — ✅ IMPLEMENTED
  - Runtime: [src/launch/util/budget_tracker.py](src/launch/util/budget_tracker.py) (orchestrator integration ready) — ✅ IMPLEMENTED
- **Tests**:
  - [tests/unit/util/test_budget_tracker.py](tests/unit/util/test_budget_tracker.py) — ✅ IMPLEMENTED
  - [tests/integration/test_gate_o_budgets.py](tests/integration/test_gate_o_budgets.py) — ✅ IMPLEMENTED
- **Budget Fields** (all required):
  - `max_runtime_s`: Maximum wall-clock time (seconds)
  - `max_llm_calls`: Maximum LLM API calls
  - `max_llm_tokens`: Maximum tokens (input + output)
  - `max_file_writes`: Maximum files written
  - `max_patch_attempts`: Maximum patch retries
- **Error Codes**: `BUDGET_EXCEEDED_RUNTIME`, `BUDGET_EXCEEDED_LLM_CALLS`, `BUDGET_EXCEEDED_LLM_TOKENS`, `BUDGET_EXCEEDED_FILE_WRITES`, `BUDGET_EXCEEDED_PATCH_ATTEMPTS`
- **Acceptance**: All runs have budgets, exceeding budgets fails fast with typed exceptions

### REQ-019: (Guarantee G) Change budget + minimal-diff discipline
- **Specs**:
  - [specs/34_strict_compliance_guarantees.md](specs/34_strict_compliance_guarantees.md) (Guarantee G) — **BINDING**
  - [specs/schemas/run_config.schema.json](specs/schemas/run_config.schema.json) (max_lines_per_file, max_files_changed) — ✅ IMPLEMENTED
  - [specs/08_patch_engine.md](specs/08_patch_engine.md)
- **Enforcement**:
  - Preflight: [tools/validate_budgets_config.py](tools/validate_budgets_config.py) (Gate O validates change budgets) — ✅ IMPLEMENTED
  - Runtime: [src/launch/util/diff_analyzer.py](src/launch/util/diff_analyzer.py) (patch bundle analysis) — ✅ IMPLEMENTED
- **Tests**:
  - [tests/unit/util/test_diff_analyzer.py](tests/unit/util/test_diff_analyzer.py) — ✅ IMPLEMENTED
  - [tests/integration/test_gate_o_budgets.py](tests/integration/test_gate_o_budgets.py) — ✅ IMPLEMENTED
- **Change Budget Fields**:
  - `max_lines_per_file`: Maximum lines changed per file (default: 500)
  - `max_files_changed`: Maximum files changed per run (default: 100)
- **Formatting Detection**: Normalizes whitespace and line endings, compares semantic content
- **Error Codes**: `POLICY_CHANGE_BUDGET_EXCEEDED`
- **Acceptance**: No excessive diffs, formatting-only changes detected, budget violations fail with typed exceptions

### REQ-020: (Guarantee H) CI parity / single canonical entrypoint
- **Specs**:
  - [specs/34_strict_compliance_guarantees.md](specs/34_strict_compliance_guarantees.md) (Guarantee H) — **BINDING**
  - [specs/19_toolchain_and_ci.md](specs/19_toolchain_and_ci.md)
- **Enforcement**:
  - Preflight: [tools/validate_ci_parity.py](tools/validate_ci_parity.py) (Gate Q) — ✅ IMPLEMENTED
- **Tests**: Validated by Gate Q (parses CI workflows)
- **Acceptance**: CI uses same commands as local (make install-uv, pytest, validate_swarm_ready.py)

### REQ-021: (Guarantee I) Non-flaky tests
- **Specs**:
  - [specs/34_strict_compliance_guarantees.md](specs/34_strict_compliance_guarantees.md) (Guarantee I) — **BINDING**
- **Enforcement**:
  - Test configuration enforces `PYTHONHASHSEED=0`
  - All tests use seeded RNGs
- **Tests**: All tests in `tests/**` MUST be deterministic
- **Acceptance**: No random failures, all tests deterministic

### REQ-022: (Guarantee J) No execution of untrusted repo code
- **Specs**:
  - [specs/34_strict_compliance_guarantees.md](specs/34_strict_compliance_guarantees.md) (Guarantee J) — **BINDING**
  - [specs/02_repo_ingestion.md](specs/02_repo_ingestion.md) (ingestion is parse-only)
- **Enforcement**:
  - Preflight: [tools/validate_untrusted_code_policy.py](tools/validate_untrusted_code_policy.py) (Gate R) — ✅ IMPLEMENTED
  - Runtime: [src/launch/util/subprocess.py](src/launch/util/subprocess.py) blocks untrusted execution — ✅ IMPLEMENTED
- **Tests**: [tests/unit/util/test_subprocess.py](tests/unit/util/test_subprocess.py) — ✅ IMPLEMENTED
- **Acceptance**: No subprocess execution from ingested repo, only parsing allowed

### REQ-023: (Guarantee K) Spec/taskcard version locking
- **Specs**:
  - [specs/34_strict_compliance_guarantees.md](specs/34_strict_compliance_guarantees.md) (Guarantee K) — **BINDING**
  - [specs/01_system_contract.md](specs/01_system_contract.md) (change control + versioning)
- **Plans**:
  - [plans/taskcards/00_TASKCARD_CONTRACT.md](plans/taskcards/00_TASKCARD_CONTRACT.md) (version lock fields)
- **Enforcement**:
  - Preflight: [tools/validate_taskcards.py](tools/validate_taskcards.py) (Gate B) validates version lock fields — ✅ IMPLEMENTED
  - Preflight: [tools/validate_taskcard_version_locks.py](tools/validate_taskcard_version_locks.py) (Gate P) additional validation — ✅ IMPLEMENTED
- **Tests**: Validated by Gates B and P (inline validation)
- **Acceptance**: All taskcards have `spec_ref`, `ruleset_version`, `templates_version` fields

### REQ-024: (Guarantee L) Rollback + recovery contract
- **Specs**:
  - [specs/34_strict_compliance_guarantees.md](specs/34_strict_compliance_guarantees.md) (Guarantee L) — **BINDING**
  - [specs/12_pr_and_release.md](specs/12_pr_and_release.md) (updated with rollback requirements)
- **Plans**:
  - [plans/taskcards/TC-480_pr_manager_w9.md](plans/taskcards/TC-480_pr_manager_w9.md)
- **Enforcement**:
  - Runtime: `launch_validate` checks rollback metadata exists in prod profile (PENDING implementation)
- **Tests**: BLOCKER - No implementation or tests yet (TC-480 not started)
- **Acceptance**: All PR artifacts include rollback steps, base ref, run_id linkage

## Cross-Reference

For detailed spec-to-taskcard mapping, see:
- [plans/traceability_matrix.md](plans/traceability_matrix.md)

For taskcard index and sequencing, see:
- [plans/taskcards/INDEX.md](plans/taskcards/INDEX.md)

For 12-dimension quality checks, see:
- [reports/templates/self_review_12d.md](reports/templates/self_review_12d.md)

---

*This matrix will be refined during Phase 1-2 hardening to ensure complete coverage.*
