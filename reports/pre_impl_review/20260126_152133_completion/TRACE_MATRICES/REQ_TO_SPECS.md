# Requirements → Specs → Plans → Enforcement Traceability

**Generated**: 2026-01-26
**Purpose**: End-to-end traceability from high-level requirements to implementation

## Format

Each entry includes:
- **Requirement ID** and statement
- **Spec(s)** that define it (binding)
- **Plan(s)** / Taskcards that implement it
- **Enforcement** mechanism (gates, runtime checks)
- **Status**: ✅ Complete | ⚠ Partial | ❌ Missing

---

## REQ-001: Launch hundreds of products deterministically

**Statement**: System must handle hundreds of products with diverse repository structures deterministically

**Specs**:
- [/specs/00_overview.md](/specs/00_overview.md) - Scale requirement (hundreds of products)
- [/specs/10_determinism_and_caching.md](/specs/10_determinism_and_caching.md) - Deterministic hashing, stable ordering
- [/specs/01_system_contract.md](/specs/01_system_contract.md) - Binding rules

**Plans/Taskcards**:
- [/plans/00_orchestrator_master_prompt.md](/plans/00_orchestrator_master_prompt.md) - Orchestration strategy
- TC-300 (Orchestrator), TC-560 (Determinism harness)
- TC-200 (Schemas ensuring deterministic I/O)

**Enforcement**:
- Gate A1: Spec pack validation
- TC-560: Determinism harness tests

**Status**: ✅ Complete (spec coverage + taskcard coverage)

---

## REQ-002: Adapt to diverse repository structures

**Statement**: Universal handling of different repo layouts (flat, src-layout, monorepo, etc.)

**Specs**:
- [/specs/02_repo_ingestion.md](/specs/02_repo_ingestion.md) - Repo profiling
- [/specs/26_repo_adapters_and_variability.md](/specs/26_repo_adapters_and_variability.md) - Platform adapters
- [/specs/27_universal_repo_handling.md](/specs/27_universal_repo_handling.md) - Universal handling guidelines

**Plans/Taskcards**:
- TC-400 (RepoScout W1 orchestration)
- TC-401 (Clone and resolve SHAs)
- TC-402 (Repo fingerprint and inventory)
- TC-403 (Frontmatter contract discovery)
- TC-404 (Hugo site context + build matrix)

**Enforcement**:
- TC-522, TC-523: E2E pilot validation (2 pilot repos with different archetypes)

**Status**: ✅ Complete (spec coverage + taskcard coverage + pilots)

---

## REQ-003: All claims must trace to evidence

**Statement**: Every factual claim must link to evidence source; no uncited facts

**Specs**:
- [/specs/03_product_facts_and_evidence.md](/specs/03_product_facts_and_evidence.md) - Evidence extraction
- [/specs/04_claims_compiler_truth_lock.md](/specs/04_claims_compiler_truth_lock.md) - TruthLock compilation
- [/specs/23_claim_markers.md](/specs/23_claim_markers.md) - Inline claim attribution

**Plans/Taskcards**:
- TC-410 (Facts Builder W2)
- TC-411 (Facts extract catalog)
- TC-412 (Evidence map linking)
- TC-413 (Truth lock compilation)

**Enforcement**:
- TC-460: TruthLock gate validates claim→evidence mapping
- TC-570: Claim marker validation gate

**Status**: ✅ Complete (spec coverage + taskcard coverage + gates)

---

## REQ-004: MCP endpoints for all features

**Statement**: Expose all launcher features via Model Context Protocol

**Specs**:
- [/specs/14_mcp_endpoints.md](/specs/14_mcp_endpoints.md) - MCP server interface
- [/specs/24_mcp_tool_schemas.md](/specs/24_mcp_tool_schemas.md) - Tool definitions

**Plans/Taskcards**:
- TC-510 (MCP server)
- TC-511 (MCP quickstart: product URL)
- TC-512 (MCP quickstart: GitHub repo URL)

**Enforcement**:
- Gate H: MCP contract validation (quickstart tools in specs)
- TC-523: MCP E2E pilot test

**Status**: ✅ Complete (spec coverage + taskcard coverage + gate)

---

## REQ-005: OpenAI-compatible LLM providers only

**Statement**: Use only OpenAI-compatible API interfaces (no provider-specific APIs)

**Specs**:
- [/specs/15_llm_providers.md](/specs/15_llm_providers.md) - Provider abstraction
- [/specs/25_frameworks_and_dependencies.md](/specs/25_frameworks_and_dependencies.md) - LangChain/LangGraph usage

**Plans/Taskcards**:
- TC-500 (Clients and services)
- TC-300 (Orchestrator using LangGraph)

**Enforcement**:
- Code review: No provider-specific imports
- TC-522, TC-523: E2E tests use configurable endpoints

**Status**: ✅ Complete (spec coverage + taskcard coverage)

---

## REQ-006: Centralized telemetry for all events

**Statement**: All events must log to centralized telemetry API

**Specs**:
- [/specs/16_local_telemetry_api.md](/specs/16_local_telemetry_api.md) - Telemetry API contract
- [/specs/11_state_and_events.md](/specs/11_state_and_events.md) - State machine events

**Plans/Taskcards**:
- TC-500 (Telemetry client implementation)
- TC-580 (Observability and evidence bundle)
- TC-300 (Orchestrator event emission)

**Enforcement**:
- Runtime: TC-300 emits events at state transitions
- TC-580: Evidence bundle collects telemetry

**Status**: ✅ Complete (spec coverage + taskcard coverage)

---

## REQ-007: Centralized GitHub commit service

**Statement**: All commits must go through centralized service with templates

**Specs**:
- [/specs/17_github_commit_service.md](/specs/17_github_commit_service.md) - Commit service
- [/specs/12_pr_and_release.md](/specs/12_pr_and_release.md) - PR creation

**Plans/Taskcards**:
- TC-500 (GitHub commit service client)
- TC-480 (PR manager W9)

**Enforcement**:
- Runtime: TC-480 uses commit service for all Git operations

**Status**: ✅ Complete (spec coverage + taskcard coverage)

---

## REQ-008: Hugo config awareness

**Statement**: System must parse Hugo config and adapt validation/layout

**Specs**:
- [/specs/31_hugo_config_awareness.md](/specs/31_hugo_config_awareness.md) - Hugo config scanning
- [/specs/18_site_repo_layout.md](/specs/18_site_repo_layout.md) - Site structure

**Plans/Taskcards**:
- TC-404 (Hugo site context + build matrix)
- TC-550 (Hugo config awareness extension)

**Enforcement**:
- TC-460, TC-570: Config-aware validation gates

**Status**: ✅ Complete (spec coverage + taskcard coverage + gates)

---

## REQ-009: Validation gates with profiles

**Statement**: Multiple validation profiles (local/ci/prod) with different strictness

**Specs**:
- [/specs/09_validation_gates.md](/specs/09_validation_gates.md) - Gate definitions + profiles

**Plans/Taskcards**:
- TC-460 (Validator W7)
- TC-570 (Validation gates extension)

**Enforcement**:
- Gate D through S: 21 validation gates
- Profile precedence: run_config → CLI → env → default

**Status**: ✅ Complete (spec coverage + taskcard coverage + profile implementation)

---

## REQ-010: Platform-aware content layout (V2)

**Statement**: Content organized by platform (/{locale}/{platform}/) with auto-detection

**Specs**:
- [/specs/32_platform_aware_content_layout.md](/specs/32_platform_aware_content_layout.md) - **BINDING**
- [/specs/18_site_repo_layout.md](/specs/18_site_repo_layout.md) - Updated for V2

**Plans/Taskcards**:
- TC-540 (Content path resolver - platform-aware)
- TC-403 (Frontmatter discovery - V2 root detection)
- TC-404 (Hugo context - layout_mode resolution)
- TC-570 (Validation gates - platform layout gate)

**Enforcement**:
- TC-570: content_layout_platform gate blocks V2 violations
- Gate F: Platform layout consistency validation

**Status**: ✅ Complete (spec coverage + taskcard coverage + gate)

---

## REQ-011: Idempotent patch engine

**Statement**: Patches apply cleanly; re-run produces same result

**Specs**:
- [/specs/08_patch_engine.md](/specs/08_patch_engine.md) - Patch engine rules

**Plans/Taskcards**:
- TC-450 (Linker and patcher W6)
- TC-540 (Content path resolver)

**Enforcement**:
- TC-560: Determinism harness validates idempotency
- TC-571: Policy gate (no manual edits)

**Status**: ✅ Complete (spec coverage + taskcard coverage)

---

## REQ-011a: Two pilot projects for regression

**Statement**: Two pilot projects validate specification

**Specs**:
- [/specs/13_pilots.md](/specs/13_pilots.md) - Pilot specifications
- [/specs/pilots/README.md](/specs/pilots/README.md) - Pilot details

**Plans/Taskcards**:
- TC-520 (Pilots and regression)
- TC-522 (CLI E2E pilot)
- TC-523 (MCP E2E pilot)

**Enforcement**:
- TC-522, TC-523: E2E validation with golden outputs

**Status**: ✅ Complete (spec coverage + taskcard coverage + 2 pilot configs)

---

## REQ-012: No manual content edits

**Statement**: System-generated content must not be manually edited (policy enforcement)

**Specs**:
- [/specs/01_system_contract.md](/specs/01_system_contract.md) - Binding rule
- [/plans/policies/no_manual_content_edits.md](/plans/policies/no_manual_content_edits.md) - Policy

**Plans/Taskcards**:
- TC-201 (Emergency mode for manual edits)
- TC-571 (Policy gate enforcement)

**Enforcement**:
- Gate (TC-571): Detects manual edits via metadata/markers
- Emergency mode flag required to override

**Status**: ✅ Complete (spec coverage + taskcard coverage + gate)

---

## REQ-013: (Guarantee A) Input immutability - pinned commit SHAs

**Statement**: All `*_ref` fields must use commit SHAs (no branches/tags)

**Specs**:
- [/specs/34_strict_compliance_guarantees.md](/specs/34_strict_compliance_guarantees.md) - Guarantee A
- [/specs/schemas/run_config.schema.json](/specs/schemas/run_config.schema.json) - Schema enforcement

**Plans/Taskcards**:
- TC-100 (Repo bootstrap with schema validation)
- TC-200 (Schema I/O validation)

**Enforcement**:
- Gate J: [/tools/validate_pinned_refs.py](/tools/validate_pinned_refs.py) - ✅ IMPLEMENTED
- Runtime: `launch_validate` rejects floating refs in prod profile

**Status**: ✅ Complete (spec + taskcard + preflight gate + runtime enforcement)

---

## REQ-014: (Guarantee B) Hermetic execution boundaries

**Statement**: All file operations confined to allowed_paths and RUN_DIR

**Specs**:
- [/specs/34_strict_compliance_guarantees.md](/specs/34_strict_compliance_guarantees.md) - Guarantee B
- [/specs/29_project_repo_structure.md](/specs/29_project_repo_structure.md) - RUN_DIR isolation

**Plans/Taskcards**:
- TC-100 (Repo structure + allowed_paths enforcement)
- TC-200 (Path validation utilities)

**Enforcement**:
- Gate E: [/tools/audit_allowed_paths.py](/tools/audit_allowed_paths.py) validates zero critical overlaps - ✅ IMPLEMENTED
- Runtime: [/src/launch/util/path_validation.py](/src/launch/util/path_validation.py) rejects escapes - ✅ IMPLEMENTED
- Tests: [/tests/unit/util/test_path_validation.py](/tests/unit/util/test_path_validation.py) - ✅ IMPLEMENTED

**Status**: ✅ Complete (spec + taskcard + preflight gate + runtime enforcement + tests)

---

## REQ-015: (Guarantee C) Supply-chain pinning

**Statement**: All dependencies pinned with lock files (no version ranges)

**Specs**:
- [/specs/34_strict_compliance_guarantees.md](/specs/34_strict_compliance_guarantees.md) - Guarantee C
- [/specs/00_environment_policy.md](/specs/00_environment_policy.md) - .venv policy
- [/specs/19_toolchain_and_ci.md](/specs/19_toolchain_and_ci.md) - Toolchain requirements

**Plans/Taskcards**:
- TC-100 (Dependency management)
- TC-300 (Framework pinning)

**Enforcement**:
- Gate 0: .venv policy validation - ✅ IMPLEMENTED
- Gate K: [/tools/validate_supply_chain_pinning.py](/tools/validate_supply_chain_pinning.py) - ✅ IMPLEMENTED
- CI: Workflows use `uv sync --frozen`

**Status**: ✅ Complete (spec + taskcard + multiple gates)

---

## REQ-016: (Guarantee D) Network allowlist

**Statement**: All network requests must target allowlisted domains

**Specs**:
- [/specs/34_strict_compliance_guarantees.md](/specs/34_strict_compliance_guarantees.md) - Guarantee D

**Plans/Taskcards**:
- TC-500 (HTTP client with allowlist enforcement)

**Enforcement**:
- Gate N: [/tools/validate_network_allowlist.py](/tools/validate_network_allowlist.py) validates allowlist exists - ✅ IMPLEMENTED
- Runtime: [/src/launch/clients/http.py](/src/launch/clients/http.py) enforces allowlist - ✅ IMPLEMENTED

**Status**: ✅ Complete (spec + taskcard + preflight gate + runtime enforcement)

---

## REQ-017: (Guarantee E) Secrets hygiene

**Statement**: No secrets in repository or logs

**Specs**:
- [/specs/34_strict_compliance_guarantees.md](/specs/34_strict_compliance_guarantees.md) - Guarantee E

**Plans/Taskcards**:
- TC-590 (Security and secrets handling)

**Enforcement**:
- Gate L: [/tools/validate_secrets_hygiene.py](/tools/validate_secrets_hygiene.py) - ✅ IMPLEMENTED
- Gate M: No placeholders in production - ✅ IMPLEMENTED

**Status**: ✅ Complete (spec + taskcard + gates)

---

## REQ-018: (Guarantees F/G) Budget enforcement

**Statement**: Token/cost budgets enforced; change budgets for existing content

**Specs**:
- [/specs/34_strict_compliance_guarantees.md](/specs/34_strict_compliance_guarantees.md) - Guarantees F & G

**Plans/Taskcards**:
- TC-100 (Budget config schema)
- TC-200 (Budget validation)

**Enforcement**:
- Gate O: [/tools/validate_budgets_config.py](/tools/validate_budgets_config.py) - ✅ IMPLEMENTED
- Tests: [/tests/integration/test_gate_o_budgets.py](/tests/integration/test_gate_o_budgets.py) - ✅ IMPLEMENTED

**Status**: ✅ Complete (spec + taskcard + gate + tests)

---

## REQ-019: (Guarantee H) CI parity

**Statement**: CI uses identical commands to local runs (canonical commands)

**Specs**:
- [/specs/34_strict_compliance_guarantees.md](/specs/34_strict_compliance_guarantees.md) - Guarantee H
- [/specs/19_toolchain_and_ci.md](/specs/19_toolchain_and_ci.md) - Toolchain + CI

**Plans/Taskcards**:
- TC-100 (CI workflow setup)
- TC-530 (CLI entrypoints)

**Enforcement**:
- Gate Q: [/tools/validate_ci_parity.py](/tools/validate_ci_parity.py) parses .github/workflows - ✅ IMPLEMENTED

**Status**: ✅ Complete (spec + taskcard + gate)

---

## REQ-020: (Guarantee I) Deterministic hashing

**Statement**: PYTHONHASHSEED=0 enforced everywhere

**Specs**:
- [/specs/34_strict_compliance_guarantees.md](/specs/34_strict_compliance_guarantees.md) - Guarantee I
- [/specs/10_determinism_and_caching.md](/specs/10_determinism_and_caching.md) - Determinism rules

**Plans/Taskcards**:
- TC-560 (Determinism harness)
- TC-100 (Test configuration)

**Enforcement**:
- Test configuration: pytest.ini sets PYTHONHASHSEED=0
- All validation gates run with PYTHONHASHSEED=0

**Status**: ✅ Complete (spec + taskcard + environment enforcement)

---

## REQ-021: (Guarantee J) Untrusted code policy

**Statement**: Parse-only (no exec/eval) for untrusted repo code

**Specs**:
- [/specs/34_strict_compliance_guarantees.md](/specs/34_strict_compliance_guarantees.md) - Guarantee J

**Plans/Taskcards**:
- TC-200 (Safe subprocess wrapper)

**Enforcement**:
- Gate R: [/tools/validate_untrusted_code_policy.py](/tools/validate_untrusted_code_policy.py) - ✅ IMPLEMENTED
- Runtime: [/src/launch/util/subprocess.py](/src/launch/util/subprocess.py) - ✅ IMPLEMENTED
- Tests: [/tests/unit/util/test_subprocess.py](/tests/unit/util/test_subprocess.py) - ✅ IMPLEMENTED

**Status**: ✅ Complete (spec + taskcard + gate + implementation + tests)

---

## REQ-022: (Guarantee K) Taskcard version locks

**Statement**: All taskcards pin spec_ref, ruleset_version, templates_version

**Specs**:
- [/specs/34_strict_compliance_guarantees.md](/specs/34_strict_compliance_guarantees.md) - Guarantee K

**Plans/Taskcards**:
- All taskcards (41 total) include version lock fields

**Enforcement**:
- Gate B: [/tools/validate_taskcards.py](/tools/validate_taskcards.py) validates frontmatter - ✅ IMPLEMENTED
- Gate P: [/tools/validate_taskcard_version_locks.py](/tools/validate_taskcard_version_locks.py) - ✅ IMPLEMENTED

**Status**: ✅ Complete (spec + all taskcards + 2 gates)

---

## Summary

**Total Requirements**: 22 (REQ-001 through REQ-022, including REQ-011a)
**Spec Coverage**: 22/22 (100%)
**Taskcard Coverage**: 22/22 (100%)
**Enforcement Coverage**: 22/22 (100%) - All have gates or runtime enforcement
**Status**: ✅ **ALL REQUIREMENTS COMPLETE**

