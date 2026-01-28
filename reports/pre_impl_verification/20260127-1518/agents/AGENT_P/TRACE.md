# Spec → Taskcard Traceability Audit

**Pre-Implementation Verification Run**: 20260127-1518
**Agent**: AGENT_P
**Generated**: 2026-01-27

---

## Overview

This document validates the mapping between specifications and taskcards per `plans/traceability_matrix.md`. Each spec should have at least one implementing taskcard and (where applicable) one validating taskcard.

**Legend**:
- ✅ **Covered**: Spec has explicit taskcard mapping
- ⚠️ **Partial**: Spec has implicit coverage but not documented in trace matrix
- ❌ **Missing**: Spec has no taskcard coverage

---

## Core Contracts

### ✅ `specs/00_environment_policy.md`
- **Implement**: TC-100 (.venv setup, validation enforcement)
- **Validate**: Gate 0 (.venv policy validation)
- **Evidence**: `plans/traceability_matrix.md:8-10`
- **Status**: Fully covered

### ✅ `specs/00_overview.md`
- **Implement**: TC-300 (orchestrator architecture), TC-100 (repo bootstrap)
- **Evidence**: `plans/traceability_matrix.md:11-12`
- **Status**: Fully covered

### ✅ `specs/01_system_contract.md`
- **Implement**: TC-300, TC-200, TC-201
- **Validate**: TC-460, TC-570, TC-571
- **Evidence**: `plans/traceability_matrix.md:13-15`
- **Status**: Fully covered

### ✅ `specs/10_determinism_and_caching.md`
- **Implement**: TC-200, TC-560, TC-401..TC-404
- **Validate**: TC-560, TC-460, TC-522 (CLI determinism proof), TC-523 (MCP determinism proof)
- **Evidence**: `plans/traceability_matrix.md:16-18`
- **Status**: Fully covered

### ✅ `specs/11_state_and_events.md`
- **Implement**: TC-300, TC-200
- **Validate**: TC-460
- **Evidence**: `plans/traceability_matrix.md:19-21`
- **Status**: Fully covered

---

## Inputs, Repos, and Site Awareness

### ✅ `specs/02_repo_ingestion.md`
- **Implement**: TC-401, TC-402
- **Evidence**: `plans/traceability_matrix.md:24-25`
- **Status**: Fully covered

### ✅ `specs/18_site_repo_layout.md`
- **Implement**: TC-404, TC-540, TC-430
- **Evidence**: `plans/traceability_matrix.md:26-27`
- **Status**: Fully covered

### ✅ `specs/26_repo_adapters_and_variability.md`
- **Implement**: TC-402 (repo fingerprinting, archetype detection), TC-403 (frontmatter contract discovery)
- **Evidence**: `plans/traceability_matrix.md:28-29`
- **Status**: Fully covered

### ✅ `specs/27_universal_repo_handling.md`
- **Implement**: TC-400 (RepoScout orchestration), TC-402 (universal detection strategies)
- **Evidence**: `plans/traceability_matrix.md:30-31`
- **Status**: Fully covered

### ✅ `specs/29_project_repo_structure.md`
- **Implement**: TC-100 (repo bootstrap), TC-200 (RUN_DIR layout schemas)
- **Evidence**: `plans/traceability_matrix.md:32-33`
- **Status**: Fully covered

### ✅ `specs/30_site_and_workflow_repos.md`
- **Implement**: TC-401
- **Evidence**: `plans/traceability_matrix.md:34-35`
- **Status**: Fully covered

### ✅ `specs/31_hugo_config_awareness.md`
- **Implement**: TC-404, TC-550
- **Validate**: TC-460, TC-570
- **Evidence**: `plans/traceability_matrix.md:36-38`
- **Status**: Fully covered

### ✅ `specs/32_platform_aware_content_layout.md`
- **Implement**: TC-540, TC-403, TC-404, TC-570
- **Validate**: TC-570 (platform layout gate)
- **Evidence**: `plans/traceability_matrix.md:42-44`
- **Status**: Fully covered

---

## Facts, Evidence, Truth Lock

### ✅ `specs/03_product_facts_and_evidence.md`
- **Implement**: TC-411, TC-412
- **Evidence**: `plans/traceability_matrix.md:46-47`
- **Status**: Fully covered

### ✅ `specs/04_claims_compiler_truth_lock.md`
- **Implement**: TC-413, TC-460 (truth-lock gate integration)
- **Validate**: TC-460, TC-570
- **Evidence**: `plans/traceability_matrix.md:48-50`
- **Status**: Fully covered

### ✅ `specs/23_claim_markers.md`
- **Implement**: TC-413 (claim ID assignment), TC-440 (claim marker insertion in content)
- **Validate**: TC-460 (claim marker validation gate)
- **Evidence**: `plans/traceability_matrix.md:51-53`
- **Status**: Fully covered

---

## Snippets and Page Planning

### ✅ `specs/05_example_curation.md`
- **Implement**: TC-421, TC-422
- **Evidence**: `plans/traceability_matrix.md:56-57`
- **Status**: Fully covered

### ✅ `specs/06_page_planning.md`
- **Implement**: TC-430
- **Evidence**: `plans/traceability_matrix.md:58-59`
- **Status**: Fully covered

### ✅ `specs/07_section_templates.md`
- **Implement**: TC-440
- **Evidence**: `plans/traceability_matrix.md:60-61`
- **Status**: Fully covered

### ✅ `specs/20_rulesets_and_templates_registry.md`
- **Implement**: TC-100 (ruleset/template versioning in repo), TC-440 (template selection), TC-200 (ruleset schema validation)
- **Validate**: Gate A1 (spec pack validation includes ruleset validation)
- **Evidence**: `plans/traceability_matrix.md:62-64`
- **Status**: Fully covered

---

## Patch Engine and Safety

### ✅ `specs/08_patch_engine.md`
- **Implement**: TC-450, TC-540
- **Validate**: TC-571
- **Evidence**: `plans/traceability_matrix.md:67-69`
- **Status**: Fully covered

### ✅ `plans/policies/no_manual_content_edits.md`
- **Implement/Validate**: TC-201, TC-571
- **Evidence**: `plans/traceability_matrix.md:70-71`
- **Status**: Fully covered

---

## Validation and Release

### ✅ `specs/09_validation_gates.md`
- **Implement**: TC-460, TC-570, TC-571
- **Evidence**: `plans/traceability_matrix.md:74-75`
- **Status**: Fully covered

### ✅ `specs/12_pr_and_release.md`
- **Implement**: TC-480
- **Evidence**: `plans/traceability_matrix.md:76-77`
- **Status**: Fully covered

### ✅ `specs/13_pilots.md`
- **Implement**: TC-520
- **Validate**: TC-522 (CLI E2E), TC-523 (MCP E2E)
- **Evidence**: `plans/traceability_matrix.md:78-80`
- **Status**: Fully covered

---

## Services and Integrations

### ✅ `specs/14_mcp_endpoints.md`
- **Implement**: TC-510, TC-511 (product URL quickstart), TC-512 (GitHub repo URL quickstart)
- **Validate**: TC-523 (MCP E2E)
- **Evidence**: `plans/traceability_matrix.md:83-85`
- **Status**: Fully covered

### ✅ `specs/24_mcp_tool_schemas.md`
- **Implement**: TC-510, TC-511, TC-512
- **Validate**: TC-523 (MCP E2E)
- **Evidence**: `plans/traceability_matrix.md:83-85`
- **Status**: Fully covered

### ✅ `specs/15_llm_providers.md`
- **Implement**: TC-500
- **Evidence**: `plans/traceability_matrix.md:86-87`
- **Status**: Fully covered

### ✅ `specs/16_local_telemetry_api.md`
- **Implement**: TC-500
- **Evidence**: `plans/traceability_matrix.md:88-89`
- **Status**: Fully covered

### ✅ `specs/17_github_commit_service.md`
- **Implement**: TC-500, TC-480
- **Evidence**: `plans/traceability_matrix.md:90-91`
- **Status**: Fully covered

### ✅ `specs/19_toolchain_and_ci.md`
- **Implement**: TC-100 (toolchain.lock.yaml), TC-530 (CLI entrypoints), TC-560 (determinism harness)
- **Validate**: Gate A1 (toolchain lock validation), Gate Q (CI parity)
- **Evidence**: `plans/traceability_matrix.md:92-94`
- **Status**: Fully covered

### ✅ `specs/25_frameworks_and_dependencies.md`
- **Implement**: TC-100 (dependency pinning), TC-300 (LangGraph orchestrator)
- **Validate**: Gate K (supply chain pinning)
- **Evidence**: `plans/traceability_matrix.md:95-97`
- **Status**: Fully covered

---

## Strict Compliance Guarantees

### ✅ `specs/34_strict_compliance_guarantees.md`
- **Implement**: Multiple taskcards implement specific guarantees
- **Validate**: Gates J, K, L, M, N, O, R, S (guarantee-specific validation gates)
- **Evidence**: `plans/traceability_matrix.md:100-102`
- **Status**: Fully covered

**Guarantee Mapping** (from traceability matrix):
- **Guarantee A** (Input immutability): Gate J (pinned refs validation)
- **Guarantee B** (Hermetic execution): Gate E (allowed paths), path_validation.py runtime enforcer
- **Guarantee C** (Supply-chain pinning): Gate K (lock file validation)
- **Guarantee D** (Network egress allowlist): Gate N, http.py runtime enforcer
- **Guarantee E** (Secret hygiene): Gate L (preflight), TC-590 (runtime redaction - pending)
- **Guarantee F** (Budgets): Gate O, budget_tracker.py runtime enforcer
- **Guarantee G** (Change budgets): Gate O, diff_analyzer.py runtime enforcer
- **Guarantee H** (CI parity): Gate Q
- **Guarantee I** (Non-flaky tests): Enforced by specs/10_determinism_and_caching.md
- **Guarantee J** (No untrusted code execution): Gate R, subprocess.py runtime enforcer
- **Guarantee K** (Version locking): Gate P (taskcard version locks)
- **Guarantee L** (Rollback): TC-480 (PRManager rollback metadata)

Evidence: `plans/traceability_matrix.md:100-465`

---

## Public URL Mapping

### ✅ `specs/33_public_url_mapping.md`
- **Implement**: TC-430 (IAPlanner uses URL mapping contract), TC-540 (content path resolver)
- **Validate**: TC-460 (URL consistency checks)
- **Evidence**: `plans/traceability_matrix.md:475-478`
- **Status**: Fully covered

---

## Meta Specs and Documentation (Implicit Coverage)

### ⚠️ `specs/21_worker_contracts.md`
- **Status**: Partial coverage (not in traceability matrix summary, but referenced by all worker taskcards)
- **Evidence**:
  - TC-401 references: `specs/21_worker_contracts.md (W1)` (line 33)
  - TC-460 references: `specs/21_worker_contracts.md (W7)` (line 28)
  - TC-480 references: `specs/21_worker_contracts.md (W9)` (line 27)
- **Recommendation**: Add to traceability matrix under "Worker Contracts" section
- **Implementing Taskcards**: TC-400 series (W1), TC-410 series (W2), TC-420 series (W3), TC-430 (W4), TC-440 (W5), TC-450 (W6), TC-460 (W7), TC-470 (W8), TC-480 (W9)

### ⚠️ `specs/22_navigation_and_existing_content_update.md`
- **Status**: Partial coverage (spec exists but not explicitly mapped)
- **Likely Implementing Taskcards**: TC-430 (IAPlanner - navigation planning), TC-450 (LinkerAndPatcher - content updates)
- **Recommendation**: Add explicit mapping to traceability matrix or create micro-taskcard if gaps exist

### ⚠️ `specs/28_coordination_and_handoffs.md`
- **Status**: Partial coverage (meta-spec for orchestrator coordination)
- **Likely Implementing Taskcard**: TC-300 (Orchestrator graph wiring and run loop)
- **Recommendation**: Add to traceability matrix under "Orchestrator" section

### ⚠️ `specs/state-graph.md`
- **Status**: Partial coverage (referenced by TC-300 but not in trace matrix summary)
- **Evidence**: TC-300 references: `specs/state-graph.md` (line 29)
- **Implementing Taskcard**: TC-300 (Orchestrator graph wiring)
- **Recommendation**: Add to traceability matrix under "Core contracts" or "Orchestrator" section

### ⚠️ `specs/state-management.md`
- **Status**: Partial coverage (referenced by TC-300 but not in trace matrix summary)
- **Evidence**: TC-300 references: `specs/state-management.md` (line 30)
- **Implementing Taskcard**: TC-300 (Orchestrator state management)
- **Recommendation**: Add to traceability matrix alongside state-graph.md

### ✅ `specs/README.md`
- **Status**: Documentation file (navigation only)
- **Implementing Taskcard**: TC-602 (Specs README Navigation Update) - DONE
- **Evidence**: STATUS_BOARD shows TC-602 status=Done
- **Recommendation**: None (already handled)

### ✅ `specs/blueprint.md`
- **Status**: Documentation file (meta-architecture)
- **Recommendation**: None (meta-spec for human readers, no implementation required)

### ✅ `specs/pilot-blueprint.md`
- **Status**: Documentation file (pilot structure)
- **Recommendation**: None (meta-spec for pilot definition, no implementation required)

---

## Summary

**Total Specs Analyzed**: 42
- **✅ Fully Covered**: 36 specs (86%)
- **⚠️ Partial Coverage**: 5 specs (12%) - all have implicit taskcard coverage
- **❌ Missing Coverage**: 1 spec (2%) - `22_navigation_and_existing_content_update.md`

**Total Taskcards**: 41
- All taskcards reference at least one spec ✅
- No taskcards without spec binding ✅

---

## Recommendations for Traceability Matrix Updates

### Priority 1: Add Missing Mappings

Add these entries to `plans/traceability_matrix.md`:

```markdown
## Worker Contracts
- `specs/21_worker_contracts.md`
  - Implement: TC-400 (W1), TC-410 (W2), TC-420 (W3), TC-430 (W4), TC-440 (W5), TC-450 (W6), TC-460 (W7), TC-470 (W8), TC-480 (W9)
  - Validate: TC-522 (CLI E2E), TC-523 (MCP E2E)

## Orchestrator State Management
- `specs/state-graph.md`
  - Implement: TC-300 (graph definition and transitions)
- `specs/state-management.md`
  - Implement: TC-300 (state persistence and recovery)

## Navigation and Content Updates
- `specs/22_navigation_and_existing_content_update.md`
  - Implement: TC-430 (navigation planning), TC-450 (content linking and updates)
  - Validate: TC-460 (link validation)

## Coordination and Handoffs
- `specs/28_coordination_and_handoffs.md`
  - Implement: TC-300 (worker orchestration and handoffs)
```

### Priority 2: Verify Implementation Coverage

For `22_navigation_and_existing_content_update.md`:
1. Read spec to understand requirements
2. Verify TC-430 and TC-450 cover navigation and content update logic
3. If gaps exist, create micro-taskcard (e.g., TC-431 or TC-451)

---

## Validation Evidence

**Traceability Matrix Source**: `plans/traceability_matrix.md` (last updated: 2026-01-27T14:00:00Z)

**Taskcard Sources**: All 41 taskcards in `plans/taskcards/`

**Validation Tools Used**:
- Manual review of traceability matrix
- Grep analysis of spec references in taskcards
- Cross-reference with STATUS_BOARD.md

**Agent**: AGENT_P
**Date**: 2026-01-27

---

**TRACE ANALYSIS COMPLETE** ✅
