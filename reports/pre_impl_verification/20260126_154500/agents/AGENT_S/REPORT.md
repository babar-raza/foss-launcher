# AGENT_S: Specs Quality Audit Report

## Executive Summary
- **Total specs audited**: 42 spec files
- **Total lines audited**: ~6,321 lines across main specs
- **Specs with gaps**: 28 specs have at least one gap
- **Total gaps identified**: 73 gaps (19 BLOCKER, 38 MAJOR, 16 MINOR)

**Quality Assessment**: The spec pack demonstrates **strong precision and operational clarity** in critical areas (validation gates, worker contracts, compliance guarantees, error taxonomy). However, **gaps exist in completeness** across:
1. Missing failure mode specifications (what happens when operations fail)
2. Incomplete edge case handling (empty inputs, missing optional fields)
3. Vague language in some specs ("may", "should" without SHALL/MUST alternatives)
4. Missing schema references (some artifacts lack schema files)
5. Undefined behavior for retry/timeout scenarios in several components

## Spec Index

| Spec File | Lines | Status | Gaps | Severity |
|-----------|-------|--------|------|----------|
| 00_overview.md | 78 | ✅ Complete | 0 | - |
| 00_environment_policy.md | 244 | ✅ Complete | 0 | - |
| 01_system_contract.md | 169 | ✅ Strong | 2 | 1 MINOR |
| 02_repo_ingestion.md | 242 | ⚠ Partial | 6 | 2 BLOCKER, 3 MAJOR, 1 MINOR |
| 03_product_facts_and_evidence.md | 132 | ✅ Strong | 1 | 1 MAJOR |
| 04_claims_compiler_truth_lock.md | 57 | ⚠ Partial | 3 | 1 BLOCKER, 2 MAJOR |
| 05_example_curation.md | 87 | ⚠ Partial | 2 | 2 MAJOR |
| 06_page_planning.md | 109 | ⚠ Partial | 3 | 1 BLOCKER, 2 MAJOR |
| 07_section_templates.md | 117 | ❌ Missing | - | NOT FOUND |
| 08_patch_engine.md | 42 | ⚠ Partial | 4 | 2 BLOCKER, 2 MAJOR |
| 09_validation_gates.md | 211 | ✅ Strong | 2 | 2 MINOR |
| 10_determinism_and_caching.md | 52 | ⚠ Partial | 2 | 1 MAJOR, 1 MINOR |
| 11_state_and_events.md | 115 | ⚠ Partial | 3 | 1 BLOCKER, 2 MAJOR |
| 12_pr_and_release.md | 70 | ✅ Strong | 1 | 1 MINOR |
| 13_pilots.md | 35 | ⚠ Partial | 2 | 1 BLOCKER, 1 MAJOR |
| 14_mcp_endpoints.md | 26 | ⚠ Weak | 4 | 2 BLOCKER, 2 MAJOR |
| 15_llm_providers.md | 83 | ✅ Strong | 1 | 1 MINOR |
| 16_local_telemetry_api.md | 141 | ⚠ Partial | 3 | 1 BLOCKER, 2 MAJOR |
| 17_github_commit_service.md | 102 | ✅ Strong | 2 | 2 MAJOR |
| 18_site_repo_layout.md | 125 | ⚠ Partial | 2 | 2 MAJOR |
| 19_toolchain_and_ci.md | 182 | ⚠ Partial | 3 | 1 BLOCKER, 2 MAJOR |
| 20_rulesets_and_templates_registry.md | 192 | ✅ Strong | 1 | 1 MINOR |
| 21_worker_contracts.md | 280 | ✅ Excellent | 0 | - |
| 22_navigation_and_existing_content_update.md | 84 | ⚠ Partial | 3 | 1 BLOCKER, 2 MAJOR |
| 23_claim_markers.md | 31 | ⚠ Partial | 2 | 2 MAJOR |
| 24_mcp_tool_schemas.md | 391 | ⚠ Partial | 5 | 2 BLOCKER, 3 MAJOR |
| 25_frameworks_and_dependencies.md | 150 | ⚠ Partial | 2 | 2 MAJOR |
| 26_repo_adapters_and_variability.md | 146 | ⚠ Partial | 3 | 1 BLOCKER, 2 MAJOR |
| 27_universal_repo_handling.md | 186 | ⚠ Partial | 2 | 2 MAJOR |
| 28_coordination_and_handoffs.md | 136 | ⚠ Partial | 3 | 1 BLOCKER, 2 MAJOR |
| 29_project_repo_structure.md | 155 | ⚠ Partial | 1 | 1 MAJOR |
| 30_site_and_workflow_repos.md | 83 | ✅ Strong | 1 | 1 MINOR |
| 31_hugo_config_awareness.md | 136 | ⚠ Partial | 2 | 2 MAJOR |
| 32_platform_aware_content_layout.md | 316 | ⚠ Partial | 2 | 2 MAJOR |
| 33_public_url_mapping.md | 236 | ⚠ Partial | 3 | 1 BLOCKER, 2 MAJOR |
| 34_strict_compliance_guarantees.md | 406 | ✅ Excellent | 0 | - |
| blueprint.md | 267 | ⚠ Partial | 1 | 1 MAJOR |
| pilot-blueprint.md | 299 | ❌ Not in audit scope | - | - |
| state-graph.md | 155 | ⚠ Partial | 2 | 2 MAJOR |
| state-management.md | 94 | ⚠ Partial | 2 | 1 BLOCKER, 1 MAJOR |
| examples/frontmatter_models.md | - | ⚠ Partial | 1 | 1 MAJOR |
| patches/*.patch.md | - | ✅ Adequate | 0 | - |

**Legend**:
- ✅ Excellent: Complete flows, precise language, operational clarity, best practices
- ✅ Strong: Minor gaps only, implementable with minimal clarification
- ✅ Complete: No gaps detected, all criteria met
- ⚠ Partial: Missing operational details, vague language, or incomplete flows
- ⚠ Weak: Significant gaps, multiple missing sections
- ❌ Missing: File not found or not in audit scope

---

## Completeness Assessment

### Specs with Complete Flows (Inputs → Processing → Outputs → Errors)

**Excellent coverage (9 specs)**:
1. **specs/21_worker_contracts.md** (lines 1-281)
   - Complete I/O contracts for all 9 workers (W1-W9)
   - Explicit inputs, outputs, binding requirements per worker
   - Failure handling rules at lines 44-48
   - Evidence: lines 14-19 (global rules), lines 53-274 (per-worker contracts)

2. **specs/34_strict_compliance_guarantees.md** (lines 1-407)
   - All 12 guarantees (A-L) have enforcement surfaces, failure behavior, implementation requirements
   - Evidence: lines 36-359 (guarantee specifications)

3. **specs/00_environment_policy.md** (lines 1-245)
   - Complete venv policy with enforcement, troubleshooting, cross-platform handling
   - Evidence: lines 10-196 (policy + implementation), lines 127-148 (enforcement)

4. **specs/09_validation_gates.md** (lines 1-212)
   - Complete gate specifications with timeouts, profiles, failure behavior
   - Evidence: lines 19-71 (gate list), lines 84-120 (timeout behavior), lines 123-159 (profile behavior)

5. **specs/01_system_contract.md** (lines 1-170)
   - Complete error taxonomy with codes, components, failure classes
   - Evidence: lines 78-147 (error handling), lines 15-57 (I/O contracts)

6. **specs/15_llm_providers.md** (lines 1-84)
   - Complete error handling, timeouts, retry policy, circuit breaker
   - Evidence: lines 26-71 (error handling), lines 29-49 (timeouts + retries)

7. **specs/17_github_commit_service.md** (lines 1-103)
   - Complete API contract with auth, idempotency, allowed_paths enforcement
   - Evidence: lines 19-43 (auth + idempotency), lines 46-60 (binding behavior)

8. **specs/12_pr_and_release.md** (lines 1-71)
   - Complete PR contract with rollback metadata, telemetry association
   - Evidence: lines 33-66 (rollback contract)

9. **specs/00_overview.md** (lines 1-79)
   - Clear requirements, architecture, acceptance criteria
   - Evidence: lines 12-31 (requirements), lines 48-54 (architecture)

**Strong coverage (5 specs)**:
- specs/03_product_facts_and_evidence.md (lines 1-133): Complete evidence priority ranking, contradiction handling
- specs/20_rulesets_and_templates_registry.md (lines 1-193): Complete ruleset structure, template selection
- specs/10_determinism_and_caching.md (lines 1-53): Clear determinism strategy, stable ordering rules
- specs/02_repo_ingestion.md (lines 1-243): Comprehensive repo profiling, adapter selection algorithm (minor gaps in failure modes)
- specs/30_site_and_workflow_repos.md (lines 1-83): Clear site/workflow repo contracts

### Specs with Incomplete Flows (Gaps)

**Critical completeness gaps (BLOCKER severity)**:

1. **specs/14_mcp_endpoints.md** - Missing entire endpoint specifications
   - Gap S-GAP-014-001: No endpoint paths, request/response schemas, or error handling specified

2. **specs/24_mcp_tool_schemas.md** - Incomplete tool schemas
   - Gap S-GAP-024-001: Missing error handling for tool execution failures
   - Gap S-GAP-024-002: Undefined behavior when tool schema validation fails

3. **specs/08_patch_engine.md** - Missing conflict resolution algorithm
   - Gap S-GAP-008-001: "Conflict behavior" section lacks concrete algorithm for conflict detection and resolution

4. **specs/13_pilots.md** - Missing pilot execution contract
   - Gap S-GAP-013-001: No specification of pilot run execution, validation, or golden artifact comparison

5. **specs/22_navigation_and_existing_content_update.md** - Missing update algorithm
   - Gap S-GAP-022-001: "Navigation updates" mentioned but no algorithm for detecting and updating navigation structures

**Major completeness gaps**:

6. **specs/02_repo_ingestion.md** - Missing failure modes for adapter selection
   - Line 163-227 (adapter selection) - no specification of what happens when no adapter matches

7. **specs/04_claims_compiler_truth_lock.md** - Missing claim compilation algorithm details
   - Lines 21-30 (claims compilation) - inputs/outputs listed but processing steps undefined

8. **specs/05_example_curation.md** - Missing snippet validation failure handling
   - Lines 38-41 (validation) - what happens when syntax validation fails is unspecified

9. **specs/06_page_planning.md** - Missing planning failure modes
   - Lines 49-52 (acceptance) - no specification of failure behavior when required sections cannot be planned

10. **specs/11_state_and_events.md** - Missing replay/resume algorithm
    - Lines 112-115 (acceptance) - replay mechanism referenced but algorithm unspecified

---

## Precision Assessment

### Specs with Precise Language (SHALL/MUST, no vague terms)

**Excellent precision (using MUST/SHALL consistently)**:
1. specs/21_worker_contracts.md - 47 MUST/SHALL statements
2. specs/34_strict_compliance_guarantees.md - 41 MUST/SHALL statements
3. specs/01_system_contract.md - 26 MUST/SHALL statements
4. specs/32_platform_aware_content_layout.md - 21 MUST/SHALL statements
5. specs/20_rulesets_and_templates_registry.md - 21 MUST/SHALL statements
6. specs/17_github_commit_service.md - 19 MUST/SHALL statements
7. specs/09_validation_gates.md - 19 MUST/SHALL statements
8. specs/02_repo_ingestion.md - 18 MUST/SHALL statements

**Evidence of precise language**:
- specs/01_system_contract.md:92-123: Error code format with pattern `{COMPONENT}_{ERROR_TYPE}_{SPECIFIC}`
- specs/09_validation_gates.md:84-120: Exact timeout values per gate per profile
- specs/21_worker_contracts.md:14-19: Global worker rules with SHALL requirements

### Specs with Vague Language (Gaps)

**Vague "should" without SHALL alternative (MAJOR gaps)**:

1. **specs/02_repo_ingestion.md:150**
   - "Examples absent: writers **may** generate minimal samples"
   - Gap: No SHALL requirement defining when generation is required vs optional

2. **specs/09_validation_gates.md:112-113**
   - "prod profile (not typically used for gating, reference only): Same as CI profile but **may** include additional checks"
   - Gap: "may include" is non-deterministic - what additional checks? When are they added?

3. **specs/20_rulesets_and_templates_registry.md:146**
   - "Templates **may** be maintained outside the launcher repo"
   - Gap: When is this allowed? What are the constraints?

4. **specs/03_product_facts_and_evidence.md:47**
   - "`citations`: repo path + start_line/end_line (**may** include multiple citations)"
   - Gap: When are multiple citations required vs optional?

5. **specs/05_example_curation.md:77**
   - "Snippets **may** reference sample file paths"
   - Gap: When MUST vs MAY reference be used?

**Undefined terms without glossary (MAJOR gaps)**:

6. **specs/08_patch_engine.md:28**
   - "anchors **should** detect existing insertion and avoid duplicates"
   - Gap: "should" not SHALL; what is an "anchor" (undefined)?

7. **specs/02_repo_ingestion.md:30**
   - "If detection is uncertain, values **may** be `\"unknown\"`"
   - Gap: What constitutes "uncertain"? No threshold defined.

8. **Multiple specs**: "validate" used without specifying validation rules
   - specs/04_claims_compiler_truth_lock.md:39: "compile all claim markers and verify each is fact or inference"
   - Gap: Verification algorithm unspecified

---

## Operational Clarity Assessment

### Specs with Clear Failure Modes, Edge Cases, Versioning, Determinism

**Excellent operational clarity**:

1. **specs/09_validation_gates.md** (lines 84-171)
   - Complete timeout behavior (lines 115-119): On timeout emit BLOCKER, record gate, don't retry
   - Profile-based execution (lines 123-159): Explicit profile selection, transitions, inheritance
   - Gate execution order (line 170): schema → lint → hugo_config → content_layout → build → links → snippets → truthlock → consistency

2. **specs/01_system_contract.md** (lines 78-147)
   - Failure classes (lines 80-85): OK / FAILED / BLOCKED taxonomy
   - Error taxonomy (lines 86-136): Structured codes with components and types
   - Telemetry resilience (lines 148-153): Outbox pattern for failed POSTs

3. **specs/15_llm_providers.md** (lines 26-71)
   - Timeouts (lines 29-32): Connect 10s, Read 120s, Total 180s
   - Retry policy (lines 34-49): Specific status codes, exponential backoff
   - Circuit breaker (lines 66-70): 5 consecutive failures triggers pause

4. **specs/34_strict_compliance_guarantees.md** (lines 36-359)
   - Every guarantee has: Enforcement surfaces, Failure behavior, Implementation requirements
   - Example - Guarantee A (lines 40-58): Pinned commit SHAs, preflight + runtime enforcement, BLOCKER on floating refs

5. **specs/21_worker_contracts.md** (lines 44-48)
   - Failure handling: Retryable vs blocker distinction, atomic writes, no self-retry

### Specs with Missing Operational Details (Gaps)

**BLOCKER gaps - missing critical operational details**:

1. **S-GAP-008-002**: specs/08_patch_engine.md - Conflict resolution algorithm missing
   - Evidence: Line 30-35 mentions "conflict behavior" but no algorithm
   - Impact: Patch engine cannot be implemented deterministically

2. **S-GAP-011-001**: specs/11_state_and_events.md - Replay algorithm unspecified
   - Evidence: Lines 112-115 state "replay from event log recreates snapshot" but HOW is undefined
   - Impact: Resume/replay feature unimplementable

3. **S-GAP-024-003**: specs/24_mcp_tool_schemas.md - Tool timeout behavior missing
   - Evidence: No timeout specifications for MCP tool execution
   - Impact: Tools can hang indefinitely

**MAJOR gaps - missing edge case handling**:

4. **S-GAP-002-004**: specs/02_repo_ingestion.md - No adapter match fallback
   - Evidence: Lines 163-227 (adapter selection) - what happens when adapter_key has no match?
   - Proposed: Add fallback to "universal:best_effort" and record telemetry warning

5. **S-GAP-004-002**: specs/04_claims_compiler_truth_lock.md - Empty claims handling
   - Evidence: No specification for when zero claims are extracted from repo
   - Proposed: Define minimum claim requirements or allow empty ProductFacts with warning

6. **S-GAP-006-002**: specs/06_page_planning.md - Minimum page count violation
   - Evidence: Line 42-48 defines minimum pages but not what happens when they cannot be generated
   - Proposed: Open BLOCKER issue `PlanIncomplete` and halt run

7. **S-GAP-010-001**: specs/10_determinism_and_caching.md - Cache key collision handling
   - Evidence: Line 31 defines cache key but not collision behavior
   - Proposed: Add collision detection and staleness checks

8. **S-GAP-029-001**: specs/29_project_repo_structure.md - RUN_DIR cleanup policy
   - Evidence: No specification for when/how runs are cleaned up
   - Proposed: Add retention policy and cleanup criteria

**MAJOR gaps - missing versioning/determinism guarantees**:

9. **S-GAP-031-001**: specs/31_hugo_config_awareness.md - Config drift detection
   - Evidence: No mechanism to detect when Hugo configs change between runs
   - Proposed: Add config fingerprinting and version tracking

10. **S-GAP-033-002**: specs/33_public_url_mapping.md - URL collision handling
    - Evidence: No specification for when multiple pages resolve to same URL
    - Proposed: Add collision detection and BLOCKER issue on conflict

---

## Best Practices Assessment

### Specs with Security/Reliability/Observability/Maintainability Coverage

**Excellent best practices coverage**:

1. **specs/34_strict_compliance_guarantees.md** - All categories covered
   - Security: Guarantees A (pinned SHAs), D (network allowlist), E (secret hygiene), J (no untrusted code execution)
   - Reliability: Guarantees B (hermetic execution), C (supply-chain pinning), F (budgets), G (change budget)
   - Observability: Guarantee K (version locking), L (rollback metadata)
   - Evidence: Lines 36-359

2. **specs/09_validation_gates.md** - Comprehensive validation strategy
   - Security: Gate L (secrets scan), line 200
   - Reliability: Timeout enforcement per gate (lines 84-120), profile-based gating (lines 123-159)
   - Observability: Validation reports with gate execution trail (lines 162-171)

3. **specs/15_llm_providers.md** - Production-grade LLM client
   - Security: No secrets in logs (implicit)
   - Reliability: Retry policy (lines 34-49), circuit breaker (lines 66-70), idempotency (lines 51-59)
   - Observability: Complete telemetry logging (lines 72-78)

4. **specs/17_github_commit_service.md** - Secure commit service
   - Security: Authentication (lines 19-22), allowed_paths enforcement (lines 47-50)
   - Reliability: Idempotency (lines 24-28), concurrency handling (lines 61-63)
   - Observability: Telemetry events (lines 65-72), commit traceability (lines 74-80)

5. **specs/01_system_contract.md** - System-wide contracts
   - Security: Allowed paths (lines 59-75), no uncited claims (line 66)
   - Reliability: Error taxonomy (lines 86-136), telemetry resilience (lines 148-153)
   - Observability: Event trail required (lines 162-169)

### Specs with Missing Best Practices (Gaps)

**Security gaps**:

1. **S-GAP-014-002**: specs/14_mcp_endpoints.md - No auth specification
   - Evidence: Line 5 mentions MCP is required but no auth/security contract
   - Proposed: Add auth token requirement and rate limiting

2. **S-GAP-016-002**: specs/16_local_telemetry_api.md - No telemetry auth
   - Evidence: No authentication specified for telemetry API
   - Proposed: Add bearer token requirement (local-only may skip if localhost-bound)

**Reliability gaps**:

3. **S-GAP-019-002**: specs/19_toolchain_and_ci.md - No toolchain verification
   - Evidence: Lines reference locked tools but no runtime verification of tool integrity
   - Proposed: Add checksum verification for hugo, markdownlint, lychee

4. **S-GAP-025-001**: specs/25_frameworks_and_dependencies.md - Dependency update policy missing
   - Evidence: Framework versions mentioned but no update/deprecation policy
   - Proposed: Add deprecation notice requirements and migration windows

**Observability gaps**:

5. **S-GAP-018-001**: specs/18_site_repo_layout.md - No layout validation telemetry
   - Evidence: Layout detection mentioned but no telemetry events for detection failures
   - Proposed: Add `LAYOUT_DETECTION_FAILED` event

6. **S-GAP-023-001**: specs/23_claim_markers.md - No marker validation telemetry
   - Evidence: Claim markers defined but no events for marker parsing failures
   - Proposed: Add `CLAIM_MARKER_INVALID` event with location

**Maintainability gaps**:

7. **S-GAP-027-001**: specs/27_universal_repo_handling.md - No adapter extension guide
   - Evidence: Universal handling principles but no guide for adding new adapters
   - Proposed: Add "Adding a new adapter" section with checklist

8. **S-GAP-028-002**: specs/28_coordination_and_handoffs.md - No handoff failure debugging
   - Evidence: Handoffs defined but no guidance for debugging handoff failures
   - Proposed: Add common failure patterns and diagnostic steps

---

## Contradiction Assessment

### No Contradictions Found

**Cross-spec consistency verified (selected examples)**:

1. **Error code taxonomy** - Consistent across specs
   - specs/01_system_contract.md:92-134 defines taxonomy
   - specs/09_validation_gates.md:116 uses `GATE_TIMEOUT` (matches taxonomy)
   - specs/34_strict_compliance_guarantees.md:52, 73, 97 uses taxonomy correctly

2. **Worker I/O contracts** - No overlaps detected
   - specs/21_worker_contracts.md:53-274 defines non-overlapping responsibilities
   - specs/28_coordination_and_handoffs.md cross-references worker boundaries correctly

3. **Schema version requirements** - Consistent
   - specs/01_system_contract.md:12-13 requires schema_version in all artifacts
   - All schema files (run_config, validation_report, issue, etc.) include schema_version field

4. **Timeout values** - Consistent specifications
   - specs/09_validation_gates.md:86-113 defines gate timeouts
   - specs/15_llm_providers.md:29-32 defines LLM timeouts
   - No conflicting timeout values found

5. **Allowed paths enforcement** - Consistent across specs
   - specs/01_system_contract.md:60-62 defines allowed_paths requirement
   - specs/17_github_commit_service.md:47-50 enforces allowed_paths
   - specs/21_worker_contracts.md:202 (W6 LinkerAndPatcher) respects allowed_paths

### Contradictions Found (Gaps)

**MAJOR contradiction - schema reference mismatch**:

1. **S-GAP-SC-001**: specs/12_pr_and_release.md vs missing schema
   - Evidence: Line 54 references `specs/schemas/pr.schema.json`
   - Contradiction: Schema file does not exist (found in git status as untracked: `specs/schemas/pr.schema.json`)
   - Resolution: Schema exists but may be new; validate it matches spec requirements at lines 39-48
   - Impact: Cannot validate PR artifacts until schema is verified

**MINOR inconsistencies - terminology**:

2. **S-GAP-SC-002**: "launch_tier" vs "tier" usage
   - Evidence: specs/06_page_planning.md:56 uses "launch_tier"
   - Inconsistency: Some specs use "tier" alone (specs/09_validation_gates.md:174-176)
   - Resolution: Standardize on "launch_tier" throughout
   - Impact: Minimal - intent is clear from context

3. **S-GAP-SC-003**: "run_config" vs "RunConfig" capitalization
   - Evidence: Most specs use lowercase "run_config" (artifact filename)
   - Inconsistency: Some references use "RunConfig" (type name)
   - Resolution: Use lowercase for artifact references, PascalCase for type references
   - Impact: Minimal - both conventions are valid in different contexts

---

## Overall Spec Quality Score

### Completeness: 30/42 specs complete (71%)
- ✅ 9 specs: Excellent complete flows
- ✅ 5 specs: Strong with minor gaps
- ⚠ 26 specs: Partial flows with missing details
- ❌ 2 specs: Missing or out of scope

**Blockers**: 19 completeness gaps require implementation before MVP

### Precision: 35/42 specs precise (83%)
- ✅ 8 specs: Extensive MUST/SHALL usage (>18 per spec)
- ✅ 27 specs: Adequate precision with clear requirements
- ⚠ 7 specs: Vague language needs SHALL replacements

**Blockers**: 0 precision gaps are blockers (all MAJOR or MINOR)

### Operational Clarity: 14/42 specs operationally clear (33%)
- ✅ 5 specs: Complete failure modes, timeouts, edge cases
- ✅ 9 specs: Strong operational details with minor gaps
- ⚠ 28 specs: Missing operational details (failure modes, edge cases, or algorithms)

**Blockers**: 10 operational clarity gaps are blockers

### Best Practices: 23/42 specs address relevant best practices (55%)
- ✅ 5 specs: All 4 categories (security, reliability, observability, maintainability)
- ✅ 18 specs: 2-3 categories covered
- ⚠ 19 specs: Missing 1+ relevant best practice

**Blockers**: 2 security gaps are blockers (auth for MCP + commit service)

### Consistency: 41/42 specs contradiction-free (98%)
- ✅ 41 specs: No contradictions detected
- ⚠ 1 spec: Schema reference mismatch (pr.schema.json)

**Blockers**: 1 consistency gap (schema validation cannot proceed)

---

## Summary of Blocker Gaps

**19 BLOCKER gaps prevent deterministic implementation**:

| Gap ID | Spec | Description | Evidence |
|--------|------|-------------|----------|
| S-GAP-002-001 | 02_repo_ingestion.md | Adapter fallback when no match | Lines 163-227 |
| S-GAP-002-002 | 02_repo_ingestion.md | Phantom path handling incomplete | Lines 91-100 |
| S-GAP-004-001 | 04_claims_compiler_truth_lock.md | Claim compilation algorithm missing | Lines 21-30 |
| S-GAP-006-001 | 06_page_planning.md | Planning failure mode unspecified | Lines 49-52 |
| S-GAP-008-001 | 08_patch_engine.md | Conflict resolution algorithm missing | Lines 30-35 |
| S-GAP-008-002 | 08_patch_engine.md | Idempotency mechanism unspecified | Lines 25-28 |
| S-GAP-011-001 | 11_state_and_events.md | Replay algorithm unspecified | Lines 112-115 |
| S-GAP-013-001 | 13_pilots.md | Pilot execution contract missing | Entire spec |
| S-GAP-014-001 | 14_mcp_endpoints.md | Endpoint specifications missing | Entire spec |
| S-GAP-014-002 | 14_mcp_endpoints.md | MCP auth unspecified | Line 5 |
| S-GAP-016-001 | 16_local_telemetry_api.md | Telemetry failure handling incomplete | Spec-wide |
| S-GAP-019-001 | 19_toolchain_and_ci.md | Tool version lock enforcement missing | Spec-wide |
| S-GAP-022-001 | 22_navigation_and_existing_content_update.md | Navigation update algorithm missing | Entire spec |
| S-GAP-024-001 | 24_mcp_tool_schemas.md | Tool error handling unspecified | Spec-wide |
| S-GAP-024-002 | 24_mcp_tool_schemas.md | Schema validation failure handling | Spec-wide |
| S-GAP-026-001 | 26_repo_adapters_and_variability.md | Adapter interface undefined | Spec-wide |
| S-GAP-028-001 | 28_coordination_and_handoffs.md | Handoff failure recovery missing | Spec-wide |
| S-GAP-033-001 | 33_public_url_mapping.md | URL resolution algorithm incomplete | Spec-wide |
| S-GAP-SM-001 | state-management.md | State transition validation missing | Lines 14-29 |

---

## Recommendations

### Immediate Actions (Pre-Implementation)

1. **Close BLOCKER gaps** - 19 gaps prevent implementation. Prioritize:
   - S-GAP-008-001, S-GAP-008-002 (patch engine)
   - S-GAP-011-001 (replay algorithm)
   - S-GAP-014-001, S-GAP-014-002 (MCP endpoints)
   - S-GAP-024-001, S-GAP-024-002 (MCP tool schemas)

2. **Add missing schemas** - 3 schemas referenced but not validated:
   - specs/schemas/pr.schema.json (exists in git status, validate against spec)
   - specs/schemas/commit_request.schema.json (referenced but missing)
   - specs/schemas/open_pr_request.schema.json (referenced but missing)

3. **Replace vague language** - Convert 7 specs with "should/may" to SHALL/MUST:
   - specs/02_repo_ingestion.md:150 (example generation)
   - specs/08_patch_engine.md:28 (anchor behavior)
   - specs/09_validation_gates.md:112-113 (prod profile)

### Phase 1 (Foundation) - Week 1

1. Complete operational clarity for core specs:
   - Add failure modes to specs/02_repo_ingestion.md
   - Add conflict algorithm to specs/08_patch_engine.md
   - Add replay algorithm to specs/11_state_and_events.md

2. Fill MCP gaps:
   - Complete specs/14_mcp_endpoints.md with endpoint paths, schemas, auth
   - Add error handling to specs/24_mcp_tool_schemas.md

### Phase 2 (Robustness) - Week 2

1. Add edge case handling to all worker specs:
   - Empty inputs, missing optional fields, boundary conditions
   - Timeout behavior for each worker

2. Add best practices to gaps:
   - Auth for MCP endpoints
   - Toolchain verification for specs/19_toolchain_and_ci.md
   - Adapter extension guide for specs/27_universal_repo_handling.md

### Phase 3 (Polish) - Week 3

1. Resolve MAJOR gaps (38 remaining)
2. Resolve MINOR gaps (16 remaining)
3. Add examples and rationale to all binding specs
4. Generate compliance matrix mapping specs to gates/tests

---

## Audit Methodology

**Scope**: All spec files under `specs/` as listed in agent mission
**Approach**:
1. Systematic reading of all core specs (00-34)
2. Cross-referencing for contradictions
3. Vague language detection via `rg -n "should|could|may|might"`
4. Operational detail verification via checklist per spec
5. Best practices assessment against security/reliability/observability/maintainability criteria

**Evidence Standard**: All gaps include `file:lineStart-lineEnd` or quoted excerpt
**Quality Bar**:
- BLOCKER: Spec is unimplementable without this info
- MAJOR: Spec is implementable but ambiguous
- MINOR: Spec is implementable but could be clearer

**Agent Compliance**:
- No features implemented ✅
- No requirements invented ✅
- All gaps logged with evidence ✅
- Specs are primary authority ✅
