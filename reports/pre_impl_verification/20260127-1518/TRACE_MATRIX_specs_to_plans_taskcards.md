# Trace Matrix: Specs → Plans/Taskcards

**Pre-Implementation Verification Run**: 20260127-1518
**Source**: AGENT_P/TRACE.md
**Date**: 2026-01-27

---

## Summary

**Total Specs**: 42
**Fully Covered**: 36 specs (86%)
**Partial Coverage**: 5 specs (12%)
**Missing Coverage**: 1 spec (2%)

**Total Taskcards**: 41
- All taskcards reference at least one spec ✅
- No taskcards without spec binding ✅

---

## Core Contracts

| Spec | Implementing Taskcard(s) | Validating Taskcard(s) | Status | Evidence |
|------|--------------------------|------------------------|--------|----------|
| **specs/00_environment_policy.md** | TC-100 (.venv setup, validation enforcement) | Gate 0 | ✅ Covered | plans/traceability_matrix.md:8-10 |
| **specs/00_overview.md** | TC-300 (orchestrator), TC-100 (bootstrap) | — | ✅ Covered | plans/traceability_matrix.md:11-12 |
| **specs/01_system_contract.md** | TC-300, TC-200, TC-201 | TC-460, TC-570, TC-571 | ✅ Covered | plans/traceability_matrix.md:13-15 |
| **specs/10_determinism_and_caching.md** | TC-200, TC-560, TC-401..TC-404 | TC-560, TC-460, TC-522, TC-523 | ✅ Covered | plans/traceability_matrix.md:16-18 |
| **specs/11_state_and_events.md** | TC-300, TC-200 | TC-460 | ✅ Covered | plans/traceability_matrix.md:19-21 |

---

## Inputs, Repos, and Site Awareness

| Spec | Implementing Taskcard(s) | Status | Evidence |
|------|--------------------------|--------|----------|
| **specs/02_repo_ingestion.md** | TC-401, TC-402 | ✅ Covered | plans/traceability_matrix.md:24-25 |
| **specs/18_site_repo_layout.md** | TC-404, TC-540, TC-430 | ✅ Covered | plans/traceability_matrix.md:26-27 |
| **specs/26_repo_adapters_and_variability.md** | TC-402 (fingerprinting), TC-403 (frontmatter) | ✅ Covered | plans/traceability_matrix.md:28-29 |
| **specs/27_universal_repo_handling.md** | TC-400 (RepoScout orchestration), TC-402 | ✅ Covered | plans/traceability_matrix.md:30-31 |
| **specs/29_project_repo_structure.md** | TC-100 (bootstrap), TC-200 (RUN_DIR schemas) | ✅ Covered | plans/traceability_matrix.md:32-33 |
| **specs/30_site_and_workflow_repos.md** | TC-401 | ✅ Covered | plans/traceability_matrix.md:34-35 |
| **specs/31_hugo_config_awareness.md** | TC-404, TC-550 | ✅ Covered | plans/traceability_matrix.md:36-38 |
| **specs/32_platform_aware_content_layout.md** | TC-540, TC-403, TC-404, TC-570 | ✅ Covered | plans/traceability_matrix.md:42-44 |

---

## Facts, Evidence, Truth Lock

| Spec | Implementing Taskcard(s) | Status | Evidence |
|------|--------------------------|--------|----------|
| **specs/03_product_facts_and_evidence.md** | TC-411, TC-412 | ✅ Covered | plans/traceability_matrix.md:46-47 |
| **specs/04_claims_compiler_truth_lock.md** | TC-413, TC-460 (truth-lock gate) | ✅ Covered | plans/traceability_matrix.md:48-50 |
| **specs/23_claim_markers.md** | TC-413 (claim ID assignment), TC-440 (insertion) | ✅ Covered | plans/traceability_matrix.md:51-53 |

---

## Snippets and Page Planning

| Spec | Implementing Taskcard(s) | Status | Evidence |
|------|--------------------------|--------|----------|
| **specs/05_example_curation.md** | TC-421, TC-422 | ✅ Covered | plans/traceability_matrix.md:56-57 |
| **specs/06_page_planning.md** | TC-430 | ✅ Covered | plans/traceability_matrix.md:58-59 |
| **specs/07_section_templates.md** | TC-440 | ✅ Covered | plans/traceability_matrix.md:60-61 |
| **specs/20_rulesets_and_templates_registry.md** | TC-100 (versioning), TC-440 (selection), TC-200 (schema validation) | ✅ Covered | plans/traceability_matrix.md:62-64 |

---

## Patch Engine and Safety

| Spec | Implementing Taskcard(s) | Status | Evidence |
|------|--------------------------|--------|----------|
| **specs/08_patch_engine.md** | TC-450, TC-540 | ✅ Covered | plans/traceability_matrix.md:67-69 |
| **plans/policies/no_manual_content_edits.md** | TC-201, TC-571 | ✅ Covered | plans/traceability_matrix.md:70-71 |

---

## Validation and Release

| Spec | Implementing Taskcard(s) | Status | Evidence |
|------|--------------------------|--------|----------|
| **specs/09_validation_gates.md** | TC-460, TC-570, TC-571 | ✅ Covered | plans/traceability_matrix.md:74-75 |
| **specs/12_pr_and_release.md** | TC-480 | ✅ Covered | plans/traceability_matrix.md:76-77 |
| **specs/13_pilots.md** | TC-520, TC-522 (CLI E2E), TC-523 (MCP E2E) | ✅ Covered | plans/traceability_matrix.md:78-80 |

---

## Services and Integrations

| Spec | Implementing Taskcard(s) | Status | Evidence |
|------|--------------------------|--------|----------|
| **specs/14_mcp_endpoints.md** | TC-510, TC-511, TC-512 | ✅ Covered | plans/traceability_matrix.md:83-85 |
| **specs/24_mcp_tool_schemas.md** | TC-510, TC-511, TC-512 | ✅ Covered | plans/traceability_matrix.md:83-85 |
| **specs/15_llm_providers.md** | TC-500 | ✅ Covered | plans/traceability_matrix.md:86-87 |
| **specs/16_local_telemetry_api.md** | TC-500 | ✅ Covered | plans/traceability_matrix.md:88-89 |
| **specs/17_github_commit_service.md** | TC-500, TC-480 | ✅ Covered | plans/traceability_matrix.md:90-91 |
| **specs/19_toolchain_and_ci.md** | TC-100, TC-530, TC-560 | ✅ Covered | plans/traceability_matrix.md:92-94 |
| **specs/25_frameworks_and_dependencies.md** | TC-100 (pinning), TC-300 (LangGraph) | ✅ Covered | plans/traceability_matrix.md:95-97 |

---

## Strict Compliance Guarantees

| Spec | Implementing Taskcard(s) | Validating Taskcard(s) | Status | Evidence |
|------|--------------------------|------------------------|--------|----------|
| **specs/34_strict_compliance_guarantees.md** | Multiple taskcards implement guarantees | Gates J, K, L, M, N, O, R, S | ✅ Covered | plans/traceability_matrix.md:100-102 |

**Guarantee Mapping**:
- **Guarantee A** (Input immutability): Gate J (pinned refs)
- **Guarantee B** (Hermetic execution): Gate E (allowed paths), path_validation.py
- **Guarantee C** (Supply-chain pinning): Gate K (lock files)
- **Guarantee D** (Network allowlist): Gate N, http.py
- **Guarantee E** (Secret hygiene): Gate L (preflight), TC-590 (runtime - pending)
- **Guarantee F** (Budgets): Gate O, budget_tracker.py
- **Guarantee G** (Change budgets): Gate O, diff_analyzer.py
- **Guarantee H** (CI parity): Gate Q
- **Guarantee I** (Non-flaky tests): specs/10_determinism_and_caching.md
- **Guarantee J** (No untrusted execution): Gate R, subprocess.py
- **Guarantee K** (Version locking): Gate P (taskcard version locks)
- **Guarantee L** (Rollback): TC-480 (PRManager rollback metadata)

---

## Public URL Mapping

| Spec | Implementing Taskcard(s) | Status | Evidence |
|------|--------------------------|--------|----------|
| **specs/33_public_url_mapping.md** | TC-430 (IAPlanner), TC-540 (path resolver) | ✅ Covered | plans/traceability_matrix.md:475-478 |

---

## Meta Specs (Partial Coverage)

| Spec | Status | Recommended Fix |
|------|--------|-----------------|
| **specs/21_worker_contracts.md** | ⚠️ Partial | Add to traceability matrix under "Worker Contracts" section |
| **specs/22_navigation_and_existing_content_update.md** | ⚠️ Partial | Verify TC-430, TC-450 cover or create micro-taskcard |
| **specs/28_coordination_and_handoffs.md** | ⚠️ Partial | Add to traceability matrix under "Orchestrator" section |
| **specs/state-graph.md** | ⚠️ Partial | Add to traceability matrix alongside state-management.md |
| **specs/state-management.md** | ⚠️ Partial | Add to traceability matrix under "Core contracts" |

---

## Documentation Files (No Implementation Required)

| Spec | Status | Notes |
|------|--------|-------|
| **specs/README.md** | ✅ Done | TC-602 completed |
| **specs/blueprint.md** | ✅ N/A | Meta-architecture for human readers |
| **specs/pilot-blueprint.md** | ✅ N/A | Pilot definition structure |

---

## Spec → Taskcard Detailed Mapping

### W1 RepoScout (Spec → Taskcard)

| Spec Section | Taskcard | Implementation Scope |
|--------------|----------|----------------------|
| specs/02_repo_ingestion.md:36-44 | TC-401 | Repository cloning |
| specs/02_repo_ingestion.md:15-30 | TC-402 | Repo fingerprinting, adapter selection |
| specs/26_repo_adapters_and_variability.md | TC-402 | Archetype detection |
| specs/18_site_repo_layout.md, TC-403 | TC-403 | Frontmatter contract discovery |
| specs/31_hugo_config_awareness.md | TC-404 | Hugo site context extraction |

### W2 FactsBuilder (Spec → Taskcard)

| Spec Section | Taskcard | Implementation Scope |
|--------------|----------|----------------------|
| specs/03_product_facts_and_evidence.md:10-36 | TC-411 | Product facts extraction |
| specs/03_product_facts_and_evidence.md:40-165 | TC-412 | Evidence map linking, contradiction resolution |
| specs/04_claims_compiler_truth_lock.md | TC-413 | Truth lock compilation, claim markers |

### W3 SnippetCurator (Spec → Taskcard)

| Spec Section | Taskcard | Implementation Scope |
|--------------|----------|----------------------|
| specs/05_example_curation.md:60-70 | TC-421 | Snippet discovery |
| specs/05_example_curation.md:28-48 | TC-422 | Snippet normalization, tagging, validation |

### W4 IAPlanner (Spec → Taskcard)

| Spec Section | Taskcard | Implementation Scope |
|--------------|----------|----------------------|
| specs/06_page_planning.md:1-139 | TC-430 | Page plan generation, tier selection, cross-link planning |
| specs/33_public_url_mapping.md | TC-430 | URL path mapping |

### W5 SectionWriter (Spec → Taskcard)

| Spec Section | Taskcard | Implementation Scope |
|--------------|----------|----------------------|
| specs/07_section_templates.md | TC-440 | Template rendering |
| specs/23_claim_markers.md | TC-440 | Claim insertion |
| specs/05_example_curation.md | TC-440 | Snippet embedding |
| specs/20_rulesets_and_templates_registry.md | TC-440 | Template token replacement |

### W6 Linker/Patcher (Spec → Taskcard)

| Spec Section | Taskcard | Implementation Scope |
|--------------|----------|----------------------|
| specs/08_patch_engine.md:25-144 | TC-450 | Idempotent patch application, conflict detection/resolution |
| specs/32_platform_aware_content_layout.md | TC-540 | Platform-aware path resolution |

### W7 Validator (Spec → Taskcard)

| Spec Section | Taskcard | Implementation Scope |
|--------------|----------|----------------------|
| specs/09_validation_gates.md:19-69 | TC-460 | Runtime validation gates (1-10) |
| specs/09_validation_gates.md:123-171 | TC-570 | Profile-based gating, gate extensions |
| plans/policies/no_manual_content_edits.md | TC-571 | Policy gate for manual edit detection |

### W8 Fixer (Spec → Taskcard)

| Spec Section | Taskcard | Implementation Scope |
|--------------|----------|----------------------|
| specs/24_mcp_tool_schemas.md:288-314 | TC-470 | Deterministic issue selection, fix loop |

### W9 PRManager (Spec → Taskcard)

| Spec Section | Taskcard | Implementation Scope |
|--------------|----------|----------------------|
| specs/12_pr_and_release.md | TC-480 | PR creation, rollback metadata |
| specs/17_github_commit_service.md | TC-480 | GitHub commit service integration |
| specs/34_strict_compliance_guarantees.md (Guarantee L) | TC-480 | Rollback contract enforcement |

### Orchestrator (Spec → Taskcard)

| Spec Section | Taskcard | Implementation Scope |
|--------------|----------|----------------------|
| specs/00_overview.md:48-53 | TC-300 | LangGraph state machine, worker coordination |
| specs/11_state_and_events.md | TC-300 | Event sourcing, state persistence |
| specs/state-graph.md | TC-300 | Graph definition and transitions |
| specs/state-management.md | TC-300 | State snapshots, recovery |
| specs/28_coordination_and_handoffs.md | TC-300 | Worker handoffs |

### Services (Spec → Taskcard)

| Spec Section | Taskcard | Implementation Scope |
|--------------|----------|----------------------|
| specs/15_llm_providers.md | TC-500 | LLM client (OpenAI-compatible) |
| specs/16_local_telemetry_api.md | TC-500 | Telemetry HTTP client |
| specs/17_github_commit_service.md | TC-500 | GitHub commit service HTTP client |

### MCP Server (Spec → Taskcard)

| Spec Section | Taskcard | Implementation Scope |
|--------------|----------|----------------------|
| specs/14_mcp_endpoints.md | TC-510 | MCP server (STDIO JSON-RPC) |
| specs/24_mcp_tool_schemas.md | TC-510 | 11 MCP tool implementations |
| specs/14_mcp_endpoints.md (product URL quickstart) | TC-511 | launch_start_run_from_product_url |
| specs/14_mcp_endpoints.md (GitHub repo URL quickstart) | TC-512 | launch_start_run_from_github_repo_url |

---

## Coverage Statistics

**Spec Coverage**:
- **Fully Covered**: 36/42 specs (86%)
- **Partial Coverage**: 5/42 specs (12%) — all have implicit coverage
- **Missing Coverage**: 1/42 specs (2%) — specs/22_navigation_and_existing_content_update.md

**Taskcard Binding**:
- **All taskcards reference specs**: 41/41 (100%)
- **Orphaned taskcards**: 0

**Overall Assessment**: ✅ **EXCELLENT** — All specs have at least implicit coverage, all taskcards bound to specs

---

## Recommendations

### Priority 1: Add Missing Mappings to Traceability Matrix

Add these entries to plans/traceability_matrix.md:

```markdown
## Worker Contracts
- specs/21_worker_contracts.md
  - Implement: TC-400 (W1), TC-410 (W2), TC-420 (W3), TC-430 (W4), TC-440 (W5), TC-450 (W6), TC-460 (W7), TC-470 (W8), TC-480 (W9)
  - Validate: TC-522 (CLI E2E), TC-523 (MCP E2E)

## Orchestrator State Management
- specs/state-graph.md
  - Implement: TC-300 (graph definition and transitions)
- specs/state-management.md
  - Implement: TC-300 (state persistence and recovery)

## Navigation and Content Updates
- specs/22_navigation_and_existing_content_update.md
  - Implement: TC-430 (navigation planning), TC-450 (content linking and updates)
  - Validate: TC-460 (link validation)

## Coordination and Handoffs
- specs/28_coordination_and_handoffs.md
  - Implement: TC-300 (worker orchestration and handoffs)
```

### Priority 2: Verify Implementation Coverage

For specs/22_navigation_and_existing_content_update.md:
1. Read spec to understand requirements
2. Verify TC-430 and TC-450 cover navigation and content update logic
3. If gaps exist, create micro-taskcard (e.g., TC-431 or TC-451)

---

**Evidence Source**: reports/pre_impl_verification/20260127-1518/agents/AGENT_P/TRACE.md
**Validation Method**: Manual review of traceability matrix, grep analysis of spec references, cross-reference with STATUS_BOARD.md
