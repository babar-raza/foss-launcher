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

## Cross-Reference

For detailed spec-to-taskcard mapping, see:
- [plans/traceability_matrix.md](plans/traceability_matrix.md)

For taskcard index and sequencing, see:
- [plans/taskcards/INDEX.md](plans/taskcards/INDEX.md)

For 12-dimension quality checks, see:
- [reports/templates/self_review_12d.md](reports/templates/self_review_12d.md)

---

*This matrix will be refined during Phase 1-2 hardening to ensure complete coverage.*
