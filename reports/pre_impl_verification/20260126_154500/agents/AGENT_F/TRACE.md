# Feature-to-Requirement Trace Matrix

**Generated:** 2026-01-26
**Agent:** AGENT_F (Feature & Testability Validator)

---

## Legend

- ✅ Full Coverage: Feature fully implements requirement
- ⚠️ Partial Coverage: Feature partially implements requirement or has gaps
- ❌ No Requirement: Feature exists but no explicit requirement mapped
- 🔴 No Feature: Requirement exists but no implementing feature

---

## Trace Matrix

| Feature ID | Feature Name | Requirements Covered | Coverage Status | Evidence | Notes |
|------------|--------------|---------------------|-----------------|----------|-------|
| FEAT-001 | Repo ingestion & fingerprinting | REQ-ING-001 (clone), REQ-ING-002 (fingerprint), REQ-DET-001 (determinism) | ✅ Full | specs/02_repo_ingestion.md:1-243, specs/21_worker_contracts.md:53-84, TC-400 | Includes SHA resolution, file tree hashing, adapter selection |
| FEAT-002 | Frontmatter contract discovery | REQ-ING-003 (site discovery), REQ-DET-002 (deterministic sampling) | ✅ Full | specs/21_worker_contracts.md:75-78, specs/examples/frontmatter_models.md, TC-403 | Deterministic sampling algorithm defined |
| FEAT-003 | Hugo config awareness & build matrix | REQ-HUGO-001 (config scan), REQ-HUGO-002 (build matrix) | ✅ Full | specs/31_hugo_config_awareness.md, specs/21_worker_contracts.md:72-74, TC-404 | Build matrix inference rules defined |
| FEAT-004 | Repo adapter selection | REQ-ADAPT-001 (platform detection), REQ-ADAPT-002 (archetype selection) | ✅ Full | specs/02_repo_ingestion.md:163-243, specs/26_repo_adapters_and_variability.md, TC-402 | Deterministic tie-breaking rules included |
| FEAT-005 | ProductFacts extraction with evidence | REQ-FACTS-001 (grounded claims), REQ-FACTS-002 (evidence priority) | ✅ Full | specs/03_product_facts_and_evidence.md:1-133, specs/21_worker_contracts.md:87-106, TC-411 | Evidence priority ranking defined (table with 7 levels) |
| FEAT-006 | EvidenceMap with stable claim IDs | REQ-CLAIM-001 (stable IDs), REQ-CLAIM-002 (citations) | ✅ Full | specs/04_claims_compiler_truth_lock.md:1-58, specs/21_worker_contracts.md:100-102, TC-412 | Claim ID algorithm: sha256(normalized_text + anchor + ruleset_version) |
| FEAT-007 | TruthLock enforcement | REQ-TRUTH-001 (no uncited claims), REQ-TRUTH-002 (no inference for formats) | ✅ Full | specs/04_claims_compiler_truth_lock.md:32-51, specs/09_validation_gates.md:64, TC-413 | Validation gate enforces claim marker presence |
| FEAT-008 | Snippet catalog with provenance | REQ-SNIP-001 (stable snippet IDs), REQ-SNIP-002 (tags from ruleset) | ✅ Full | specs/05_example_curation.md:1-88, specs/21_worker_contracts.md:109-127, TC-421, TC-422 | Snippet ID: {path, line_range, sha256(content)} |
| FEAT-009 | PagePlan with public URL paths | REQ-PLAN-001 (output_path + url_path), REQ-PLAN-002 (required sections) | ✅ Full | specs/06_page_planning.md, specs/21_worker_contracts.md:130-157, specs/33_public_url_mapping.md, TC-430 | URL resolver uses hugo_facts |
| FEAT-010 | Section-specific content drafting | REQ-WRITE-001 (template fill), REQ-WRITE-002 (claim markers) | ✅ Full | specs/07_section_templates.md, specs/21_worker_contracts.md:160-182, TC-440 | Claim marker embedding per factual sentence |
| FEAT-011 | Claim marker embedding | REQ-MARKER-001 (embed in content), REQ-MARKER-002 (TruthLock validation) | ✅ Full | specs/23_claim_markers.md, specs/21_worker_contracts.md:174-175, TC-440 | HTML comment format or frontmatter block |
| FEAT-012 | Patch engine with idempotency | REQ-PATCH-001 (deterministic order), REQ-PATCH-002 (allowed_paths fence) | ✅ Full | specs/08_patch_engine.md:1-43, specs/21_worker_contracts.md:185-205, TC-450 | Patch types: create_file, update_file_range, update_by_anchor, update_frontmatter_keys, delete_file |
| FEAT-013 | Validation gates orchestration | REQ-GATE-001 (schema), REQ-GATE-002 (Hugo build), REQ-GATE-003 (TruthLock), REQ-GATE-004 (links) | ✅ Full | specs/09_validation_gates.md:1-212, specs/21_worker_contracts.md:207-227, TC-460 | 10+ gates defined with stable issue ordering |
| FEAT-014 | Profile-based gating (local/ci/prod) | REQ-GATE-005 (profile selection), REQ-GATE-006 (timeout enforcement) | ✅ Full | specs/09_validation_gates.md:123-159 | Timeout tables defined for local/ci/prod |
| FEAT-015 | Strict compliance gates (J-R) | REQ-COMP-001 to REQ-COMP-009 (pinned refs, secrets, network allowlist, budget, CI parity, untrusted code) | ⚠️ Partial | specs/09_validation_gates.md:196-212, specs/34_strict_compliance_guarantees.md | **GAP:** Gates J-R referenced but not implemented (see F-GAP-002 to F-GAP-005) |
| FEAT-016 | Targeted single-issue fixer | REQ-FIX-001 (fix exactly one), REQ-FIX-002 (no new claims) | ✅ Full | specs/21_worker_contracts.md:229-252, specs/08_patch_engine.md, TC-470 | FixNoOp blocker if no meaningful diff |
| FEAT-017 | PR manager with commit service | REQ-PR-001 (deterministic branch), REQ-PR-002 (commit SHA association), REQ-PR-003 (rollback metadata) | ⚠️ Partial | specs/21_worker_contracts.md:254-274, specs/12_pr_and_release.md, TC-480 | **GAP:** pr.json includes rollback metadata but no rollback *execution* feature (see F-GAP-001) |
| FEAT-018 | Determinism harness (golden runs) | REQ-DET-003 (byte-identical artifacts), REQ-DET-004 (stable ordering) | ✅ Full | specs/10_determinism_and_caching.md:1-53, TC-560 | Canonical JSON writer + hash comparison |
| FEAT-019 | MCP server with 11 tools | REQ-MCP-001 to REQ-MCP-011 (all tools) | ✅ Full | specs/14_mcp_endpoints.md:1-27, specs/24_mcp_tool_schemas.md:82-392, TC-510 | All tools have request/response schemas + error codes |
| FEAT-020 | MCP product URL quickstart | REQ-MCP-012 (URL derivation), REQ-MCP-013 (idempotency) | ✅ Full | specs/24_mcp_tool_schemas.md:110-151, TC-511 | 5 URL patterns supported |
| FEAT-021 | MCP GitHub repo URL quickstart | REQ-MCP-014 (inference), REQ-MCP-015 (ambiguity handling) | ✅ Full | specs/24_mcp_tool_schemas.md:153-240, TC-512 | Ambiguity handling: return suggested_values on failure |
| FEAT-022 | Local telemetry API integration | REQ-TELEM-001 (parent run), REQ-TELEM-002 (child runs), REQ-TELEM-003 (commit association), REQ-TELEM-004 (buffering) | ⚠️ Partial | specs/16_local_telemetry_api.md:1-142, specs/11_state_and_events.md:39-50, TC-500 | **GAP:** Buffering strategy defined but no E2E test (see F-GAP-011) |
| FEAT-023 | Event sourcing & snapshot state | REQ-STATE-001 (replay), REQ-STATE-002 (resume) | ⚠️ Partial | specs/11_state_and_events.md:1-116, specs/schemas/event.schema.json, TC-300 | **GAP:** Resume feature defined but no E2E test scenario (see F-GAP-010) |
| FEAT-024 | LangGraph orchestrator | REQ-ORCH-001 (state machine), REQ-ORCH-002 (worker dispatch), REQ-ORCH-003 (fix loop) | ⚠️ Partial | specs/00_overview.md:49-54, specs/21_worker_contracts.md:1-281, TC-300 | **GAP:** Fix loop convergence criteria vague (see F-GAP-026) |
| FEAT-025 | Schema validation for all artifacts | REQ-SCHEMA-001 (validate JSON), REQ-SCHEMA-002 (frontmatter) | ✅ Full | specs/01_system_contract.md:41-57, specs/09_validation_gates.md:21-22, TC-200 | 22 schemas defined; unknown keys forbidden |
| FEAT-026 | Allowed paths write fence | REQ-SAFE-001 (allowed_paths), REQ-SAFE-002 (blocker on violation) | ✅ Full | specs/01_system_contract.md:60-66, specs/09_validation_gates.md:201-202, TC-571 | AllowedPathsViolation blocker issue |
| FEAT-027 | Emergency manual edits mode | REQ-SAFE-003 (default false), REQ-SAFE-004 (enumerate files) | ⚠️ Partial | specs/01_system_contract.md:69-76, TC-201 | **GAP:** No E2E test for enumeration enforcement (see F-GAP-024) |
| FEAT-028 | Versioned rulesets & templates | REQ-VER-001 (ruleset_version), REQ-VER-002 (templates_version) | ✅ Full | specs/01_system_contract.md:10-13, specs/20_rulesets_and_templates_registry.md, TC-100 | Every artifact has schema_version field |
| FEAT-029 | Platform-aware content layout (V2) | REQ-LAYOUT-001 (locale/platform paths), REQ-LAYOUT-002 (gate enforcement) | ✅ Full | specs/32_platform_aware_content_layout.md, specs/09_validation_gates.md:34-43, TC-570 | Gate 4: content_layout_platform validates paths |
| FEAT-030 | Pilots with pinned SHAs | REQ-PILOT-001 (two pilots), REQ-PILOT-002 (golden PagePlan), REQ-PILOT-003 (regression detection) | ✅ Full | specs/13_pilots.md, specs/00_overview.md:75-79, TC-520, TC-522, TC-523 | pilot-aspose-3d-foss-python, pilot-aspose-note-foss-python |
| (no feature) | **Batch execution** | 🔴 REQ-BATCH-001 (queue runs), 🔴 REQ-BATCH-002 (bounded concurrency) | 🔴 No Feature | specs/00_overview.md:16 | **GAP F-GAP-009:** Requirement exists but no feature/taskcard (see F-GAP-022) |
| (no feature) | **Caching infrastructure** | 🔴 REQ-CACHE-001 (cache storage), 🔴 REQ-CACHE-002 (cache invalidation) | 🔴 No Feature | specs/10_determinism_and_caching.md:30-38 | **GAP F-GAP-007, F-GAP-015, F-GAP-023:** Cache keys defined but no implementation |
| (no feature) | **Content rollback execution** | 🔴 REQ-ROLLBACK-001 (rollback command) | 🔴 No Feature | specs/34_strict_compliance_guarantees.md (Guarantee L) | **GAP F-GAP-001:** pr.json has rollback metadata but no rollback tool |
| (no feature) | **Network allowlist gate (Gate N)** | 🔴 REQ-COMP-004 (network allowlist validation) | 🔴 No Feature | specs/09_validation_gates.md:204, specs/34_strict_compliance_guarantees.md (Guarantee D) | **GAP F-GAP-002:** Gate referenced but not implemented |
| (no feature) | **Budget enforcement (Gates O)** | 🔴 REQ-COMP-006 (budget limits), 🔴 REQ-COMP-007 (budget tracking) | 🔴 No Feature | specs/09_validation_gates.md:205 | **GAP F-GAP-003:** Gate referenced but not implemented |
| (no feature) | **CI parity gate (Gate Q)** | 🔴 REQ-COMP-008 (CI canonical commands) | 🔴 No Feature | specs/09_validation_gates.md:206 | **GAP F-GAP-004:** Gate referenced but not implemented |
| (no feature) | **Untrusted code non-execution gate (Gate R)** | 🔴 REQ-COMP-009 (parse-only ingestion) | 🔴 No Feature | specs/09_validation_gates.md:207 | **GAP F-GAP-005:** Gate referenced but not implemented |

---

## Coverage Summary

- **Total features:** 30
- **Total requirements covered:** 60+ (explicit requirements identified)
- **Full coverage:** 23 features (77%)
- **Partial coverage:** 7 features (23%)
- **No feature (requirement gap):** 5 requirement categories (batch execution, caching, rollback execution, Gates N/O/Q/R)
- **No requirement (unnecessary feature):** 0 features

---

## Requirements Without Features (Critical Gaps)

1. **REQ-BATCH-001, REQ-BATCH-002:** Batch execution with bounded concurrency
   - **Source:** specs/00_overview.md:16
   - **Impact:** BLOCKER - "hundreds of products" scale requirement unimplementable
   - **Gap ID:** F-GAP-009, F-GAP-022

2. **REQ-CACHE-001, REQ-CACHE-002:** Caching infrastructure with invalidation
   - **Source:** specs/10_determinism_and_caching.md:30-38
   - **Impact:** MAJOR - Determinism strategy incomplete; cache keys defined but unusable
   - **Gap IDs:** F-GAP-007, F-GAP-015, F-GAP-023

3. **REQ-ROLLBACK-001:** Content rollback execution
   - **Source:** specs/34_strict_compliance_guarantees.md (Guarantee L)
   - **Impact:** MAJOR - Rollback metadata collected but not actionable
   - **Gap ID:** F-GAP-001

4. **REQ-COMP-004:** Network allowlist validation (Gate N)
   - **Source:** specs/09_validation_gates.md:204, specs/34_strict_compliance_guarantees.md (Guarantee D)
   - **Impact:** MAJOR - Security compliance guarantee unenforceable
   - **Gap ID:** F-GAP-002

5. **REQ-COMP-006, REQ-COMP-007:** Budget enforcement (Gate O)
   - **Source:** specs/09_validation_gates.md:205, specs/34_strict_compliance_guarantees.md (Guarantees F, G)
   - **Impact:** MAJOR - Cost controls unenforceable
   - **Gap ID:** F-GAP-003

6. **REQ-COMP-008:** CI parity validation (Gate Q)
   - **Source:** specs/09_validation_gates.md:206, specs/34_strict_compliance_guarantees.md (Guarantee H)
   - **Impact:** MAJOR - CI drift risk unmitigated
   - **Gap ID:** F-GAP-004

7. **REQ-COMP-009:** Untrusted code non-execution (Gate R)
   - **Source:** specs/09_validation_gates.md:207, specs/34_strict_compliance_guarantees.md (Guarantee J)
   - **Impact:** MAJOR - Security guarantee unenforceable
   - **Gap ID:** F-GAP-005

---

## Features Without Requirements (None Identified)

All 30 features trace to explicit requirements in specs/plans or are part of binding system contracts (specs/00_overview.md, specs/01_system_contract.md).

---

## Partial Coverage Details

### FEAT-015: Strict Compliance Gates (J-R)
- **Covered:** Gates J, K, L, M, P defined conceptually
- **Gap:** Gates N, O, Q, R referenced but no implementation specs
- **Evidence:** specs/09_validation_gates.md:196-212 lists all gates; specs/19_toolchain_and_ci.md:79-171 implements only Gates 1-9 + TemplateTokenLint
- **Impact:** 4 compliance guarantees (D, F, G, H, J) unenforceable

### FEAT-017: PR Manager with Commit Service
- **Covered:** pr.json schema includes rollback metadata (base_ref, run_id, rollback_steps, affected_paths)
- **Gap:** No rollback *execution* tool (no MCP tool or CLI command to apply rollback)
- **Evidence:** specs/schemas/pr.schema.json, TC-480:38-41, 54-55, 136
- **Impact:** Rollback metadata collected but not actionable

### FEAT-022: Local Telemetry API Integration
- **Covered:** Telemetry emission, parent/child runs, commit association all defined
- **Gap:** Buffering retry strategy defined (specs/16_local_telemetry_api.md:123-135) but no E2E test for API outage scenario
- **Evidence:** TC-500 referenced but not in STATUS_BOARD.md as Done/InProgress
- **Impact:** Transport resilience untested

### FEAT-023: Event Sourcing & Snapshot State
- **Covered:** Event schema, snapshot schema, replay logic defined
- **Gap:** Resume feature (specs/11_state_and_events.md:112-115) has no E2E test scenario
- **Evidence:** specs/11_state_and_events.md:112-115 requires "resume continues from last stable state"
- **Impact:** Resume correctness unverified

### FEAT-024: LangGraph Orchestrator
- **Covered:** State machine, worker dispatch, fix loop defined
- **Gap:** Fix loop convergence criteria vague (specs/09_validation_gates.md:78 references "max_fix_attempts" with no default value)
- **Evidence:** specs/09_validation_gates.md:78-79, specs/01_system_contract.md:158
- **Impact:** Fix loop may not converge; no "give up" threshold

### FEAT-027: Emergency Manual Edits Mode
- **Covered:** `allow_manual_edits` flag, enumeration requirement defined
- **Gap:** No validation gate to enforce enumeration (specs/01_system_contract.md:74 requires "enumerates the affected files" but no gate checks this)
- **Evidence:** specs/01_system_contract.md:69-76, TC-201 exists but no E2E test
- **Impact:** Manual edits could bypass enumeration requirement

---

## Traceability Quality Assessment

- **Forward traceability (requirement → feature):** ⚠️ PARTIAL - 7 requirement categories have no features
- **Backward traceability (feature → requirement):** ✅ EXCELLENT - All 30 features trace to explicit requirements
- **Traceability maintenance:** ✅ GOOD - plans/traceability_matrix.md:1-100 exists and maps specs ↔ taskcards
- **Evidence quality:** ✅ EXCELLENT - All mappings include file paths and line ranges
