# Feature & Testability Gaps

**Verification Run**: 20260127-1518
**Agent**: AGENT_F (Feature & Testability Validator)
**Date**: 2026-01-27

---

## Gap Classification

- **BLOCKER**: Prevents production readiness or breaks core system guarantees
- **MAJOR**: Significantly impacts quality, testability, or maintainability
- **MINOR**: Improvement opportunity without immediate impact

---

## BLOCKER Gaps (13)

### F-GAP-001: REQ-024 Rollback + Recovery Contract - Not Implemented
- **Severity**: BLOCKER
- **Category**: Feature Completeness
- **Description**: REQ-024 (Guarantee L: Rollback + recovery contract) has features defined (FEAT-058, FEAT-059) but TC-480 (PR Manager W9) is not started. No implementation exists for rollback metadata validation.
- **Evidence**:
  - TRACEABILITY_MATRIX.md:274-284: "Runtime validation PENDING (See TC-480 - TC not started)"
  - TRACEABILITY_MATRIX.md:618-628: "Status: NOT YET IMPLEMENTED"
  - specs/12_pr_and_release.md: Rollback requirements defined
  - specs/34_strict_compliance_guarantees.md: Guarantee L binding
- **Impact**: Cannot create production-ready PRs without rollback metadata. Prevents safe deployment rollback.
- **Proposed Fix**:
  1. Start TC-480 implementation immediately
  2. Define rollback metadata schema in specs/schemas/pr.schema.json
  3. Implement rollback validation in launch_validate (prod profile)
  4. Add acceptance tests: base_ref present, run_id linkage, rollback_steps populated, affected_paths listed
  5. Integrate with launch_open_pr MCP tool (FEAT-069)
- **Blocking**: REQ-024, FEAT-058, FEAT-059, FEAT-069
- **Estimated Effort**: 2-3 weeks (TC-480 is epic-level taskcard)

---

### F-GAP-022: FEAT-019, FEAT-020 (Truth Lock & Claim Markers) - Not Testable
- **Severity**: BLOCKER
- **Category**: Independent Testability
- **Description**: TC-413 (Truth Lock Compile Minimal) is not started. No acceptance tests defined for claim stability, claim ID hashing, or truth lock report generation.
- **Evidence**:
  - TRACEABILITY_MATRIX.md:47-53: "TC-413 (truth lock compile minimal), Validate: TC-460, TC-570"
  - TRACEABILITY_MATRIX.md:358-360: "Status: NOT YET IMPLEMENTED (See TC-413, TC-460)"
  - specs/04_claims_compiler_truth_lock.md: Truth lock rules defined
- **Impact**: Cannot enforce "all claims trace to evidence" requirement (REQ-003). Core system guarantee unverifiable.
- **Proposed Fix**:
  1. Start TC-413 implementation
  2. Define acceptance criteria:
     - Claim IDs stable across runs (same claim_text → same claim_id)
     - Truth lock report validates against schema
     - Uncited claims detected and reported
     - Inference constraints enforced
  3. Create test fixtures: ProductFacts with claims, EvidenceMap with citations, content with claim markers
  4. Implement TruthLock gate (Gate 9) in runtime validator
  5. Add determinism test: same ProductFacts → same truth_lock_report.json
- **Blocking**: REQ-003, FEAT-019, FEAT-020, FEAT-052 (TruthLock Gate)
- **Estimated Effort**: 1-2 weeks

---

### F-GAP-025: FEAT-026, FEAT-028, FEAT-030 (Page Planning) - Not Testable
- **Severity**: BLOCKER
- **Category**: Independent Testability
- **Description**: TC-430 (IA Planner W4) is not started. No acceptance tests defined for page plan generation, cross-link planning, or content quota enforcement.
- **Evidence**:
  - TRACEABILITY_MATRIX.md:58-60: "TC-430 — W4 IA Planner"
  - specs/06_page_planning.md: Page planning rules defined
  - specs/06_page_planning.md:55-83: Planning failure modes defined
- **Impact**: Cannot verify deterministic page inventory. Cannot test cross-link consistency. Core planning logic unverifiable.
- **Proposed Fix**:
  1. Start TC-430 implementation
  2. Define acceptance criteria:
     - page_plan.json validates against schema
     - All required sections have minimum page count
     - Cross-links use url_path (not output_path)
     - Page order stable (section priority → slug alphabetical)
     - URL collision detection works
  3. Create test fixtures: ProductFacts with varying evidence quality, run_configs with different required_sections
  4. Add determinism test: same inputs → same page_plan.json
  5. Test launch tier selection logic with quality signals
- **Blocking**: REQ-001 (deterministic page inventory), FEAT-026, FEAT-028, FEAT-030
- **Estimated Effort**: 2-3 weeks (W4 is complex worker)

---

### F-GAP-027: FEAT-058, FEAT-059 (PR Management) - Not Testable
- **Severity**: BLOCKER
- **Category**: Independent Testability
- **Description**: Same as F-GAP-001. TC-480 not started, no acceptance tests for PR creation or rollback metadata.
- **Evidence**: (Same as F-GAP-001)
- **Impact**: Cannot verify PR creation workflow end-to-end. Cannot test rollback metadata population.
- **Proposed Fix**: (Same as F-GAP-001)
- **Blocking**: REQ-007, REQ-024, FEAT-058, FEAT-059
- **Estimated Effort**: 2-3 weeks

---

### F-GAP-028: FEAT-071 (LangGraph Orchestrator) - Not Testable
- **Severity**: BLOCKER
- **Category**: Independent Testability
- **Description**: TC-300 (Orchestrator LangGraph) is not started. No acceptance criteria for state transitions, event emission, worker coordination, or error propagation.
- **Evidence**:
  - TRACEABILITY_MATRIX.md:13-15: "TC-300 (orchestrator architecture)"
  - plans/taskcards/INDEX.md:13: "TC-300 — Orchestrator graph wiring and run loop"
- **Impact**: Cannot verify orchestrator state machine. Cannot test worker handoffs. Cannot verify deterministic execution (REQ-001).
- **Proposed Fix**:
  1. Start TC-300 implementation immediately (critical path dependency)
  2. Define acceptance criteria:
     - All state transitions valid (per specs/state-management.md)
     - Events emitted for every state change
     - Worker failures propagate correctly
     - Resumable from any state boundary
     - Deterministic state transitions (same events → same final state)
  3. Create test fixtures: Mock workers, synthetic event logs, state snapshots
  4. Add unit tests for each state transition
  5. Add integration tests for full pipeline (CREATED → DONE)
  6. Integrate with TC-522 (CLI E2E) and TC-523 (MCP E2E)
- **Blocking**: REQ-001 (deterministic execution), REQ-005 (LLM integration), FEAT-071
- **Estimated Effort**: 4-5 weeks (most critical component)

---

### F-GAP-030: FEAT-073 (Deterministic Execution) - Not Testable
- **Severity**: BLOCKER
- **Category**: Independent Testability, Determinism Controls
- **Description**: TC-560 (Determinism Harness) is not started. No determinism harness fixtures, no golden run comparison, no prompt hash validation.
- **Evidence**:
  - TRACEABILITY_MATRIX.md:17-25: "TC-560 (determinism harness)"
  - specs/10_determinism_and_caching.md: Determinism requirements defined
- **Impact**: Cannot verify core system guarantee: "Same inputs -> same plan -> near-identical diffs". Cannot validate temperature=0.0 enforcement. Cannot detect determinism regressions.
- **Proposed Fix**:
  1. Start TC-560 implementation
  2. Define acceptance criteria:
     - Golden runs produce bit-identical artifacts (page_plan.json, patch_bundle.json, validation_report.json)
     - Prompt hashes recorded and stable
     - LLM calls logged with temperature validation
     - Artifact ordering deterministic
     - Diff reports show zero delta on re-run
  3. Create golden run fixtures for both pilots (TC-520)
  4. Implement diff comparison utility (artifact-level, line-level, semantic-level)
  5. Add CI integration: fail on determinism regression
  6. Add telemetry event: DETERMINISM_VIOLATION with diff details
- **Blocking**: REQ-001 (core system guarantee), FEAT-073
- **Estimated Effort**: 2 weeks

---

### F-GAP-052: FEAT-058, FEAT-059 - No Determinism Controls
- **Severity**: BLOCKER
- **Category**: Determinism Controls
- **Description**: PR creation and rollback metadata generation have no determinism controls defined. No seed, no ordering, no hashing strategy for PR metadata.
- **Evidence**: (Same as F-GAP-001)
- **Impact**: Re-runs may produce different PR bodies or rollback metadata. Cannot verify determinism for PR workflow.
- **Proposed Fix**:
  1. Define determinism requirements for PR Manager:
     - PR title template stable (based on run_config.product_slug)
     - PR body template versioned (ruleset_version)
     - Evidence bundle ordering stable (sort by artifact name)
     - Rollback metadata fields deterministic (base_ref from site_ref, run_id from run context)
  2. Add acceptance test: same run → same PR body (excluding timestamps)
  3. Document ordering rules in TC-480
  4. Add telemetry: PRMANAGER_DETERMINISM_CHECK event
- **Blocking**: REQ-001, FEAT-058, FEAT-059
- **Estimated Effort**: Included in TC-480 (F-GAP-001)

---

### F-GAP-054: FEAT-071 - No Determinism Controls
- **Severity**: BLOCKER
- **Category**: Determinism Controls
- **Description**: LangGraph orchestrator has no seed/ordering/hashing strategy defined. No acceptance criteria for deterministic state transitions.
- **Evidence**: (Same as F-GAP-028)
- **Impact**: State machine may produce non-deterministic event sequences. Cannot verify REQ-001 (same inputs → same outputs).
- **Proposed Fix**:
  1. Define determinism requirements:
     - State transition order stable (based on event ordering)
     - Worker invocation order deterministic (W1 → W2 → W3 → ... → W9)
     - Parallel workers use stable ordering (alphabetical by worker name if truly parallel)
     - Event timestamps do NOT affect state transitions
     - Snapshot serialization deterministic (sorted keys)
  2. Add acceptance test: replay events.ndjson → reproduce snapshot.json
  3. Document in TC-300 and specs/state-management.md
  4. Add determinism test to TC-522 (CLI E2E)
- **Blocking**: REQ-001, FEAT-071
- **Estimated Effort**: Included in TC-300 (F-GAP-028)

---

### F-GAP-061: launch_open_pr - No Error Codes Defined
- **Severity**: BLOCKER
- **Category**: MCP Tool Callability
- **Description**: launch_open_pr (FEAT-069) has incomplete MCP contract. No error codes enumerated for commit service failures, rollback validation failures, or PR creation failures.
- **Evidence**:
  - 24_mcp_tool_schemas.md:345-368: Tool contract defined but error codes missing
  - REPORT.md Check 5: "launch_open_pr: ❌ Incomplete"
- **Impact**: MCP clients cannot handle errors correctly. No typed error responses for debugging.
- **Proposed Fix**:
  1. Add error codes to specs/24_mcp_tool_schemas.md:
     - PR_MANAGER_VALIDATION_FAILED: Rollback metadata missing or invalid (prod profile)
     - PR_MANAGER_COMMIT_SERVICE_FAILED: Commit service rejected request
     - PR_MANAGER_BRANCH_EXISTS: Branch already exists (conflict)
     - PR_MANAGER_NO_CHANGES: Patch bundle empty (no-op)
     - PR_MANAGER_ILLEGAL_STATE: Precondition failed (state != READY_FOR_PR or validation_report.ok != true)
  2. Add examples for each error scenario
  3. Document retryable vs non-retryable errors
  4. Update specs/schemas/api_error.schema.json if needed
- **Blocking**: FEAT-069, REQ-004 (MCP endpoints)
- **Estimated Effort**: 1-2 days (documentation only, implementation in TC-480)

---

### F-GAP-062: launch_open_pr - No Rollback Metadata Validation
- **Severity**: BLOCKER
- **Category**: MCP Tool Callability, Feature Completeness
- **Description**: launch_open_pr has no specification for rollback metadata validation in prod profile. Guarantee L (REQ-024) requires validation but no enforcement mechanism defined.
- **Evidence**:
  - specs/34_strict_compliance_guarantees.md:274-284: "Runtime validation PENDING"
  - TRACEABILITY_MATRIX.md:618-628: "Status: PENDING IMPLEMENTATION"
- **Impact**: Prod profile PRs may be created without rollback metadata. Violates Guarantee L.
- **Proposed Fix**:
  1. Add precondition to launch_open_pr:
     - If run_config.validation_profile == "prod":
       - Validate PR metadata includes base_ref, run_id, rollback_steps, affected_paths
       - Fail with error_code PR_MISSING_ROLLBACK_METADATA if any field missing
  2. Add to specs/24_mcp_tool_schemas.md tool contract
  3. Implement in TC-480 PR Manager
  4. Add acceptance test: prod profile rejects PR without rollback metadata
- **Blocking**: REQ-024 (Guarantee L), FEAT-069
- **Estimated Effort**: Included in TC-480 (F-GAP-001)

---

### F-GAP-079: FEAT-058, FEAT-059 - No Acceptance Criteria
- **Severity**: BLOCKER
- **Category**: Feature Completeness
- **Description**: Same as F-GAP-001, F-GAP-027. TC-480 not started, no acceptance criteria documented.
- **Evidence**: (Same as F-GAP-001)
- **Impact**: Cannot define "done" for PR Manager. Cannot write acceptance tests.
- **Proposed Fix**: (Same as F-GAP-001)
- **Blocking**: FEAT-058, FEAT-059
- **Estimated Effort**: Included in TC-480

---

### F-GAP-081: FEAT-071 - No Acceptance Criteria
- **Severity**: BLOCKER
- **Category**: Feature Completeness
- **Description**: Same as F-GAP-028. TC-300 not started, no acceptance criteria for orchestrator state transitions.
- **Evidence**: (Same as F-GAP-028)
- **Impact**: Cannot define "done" for orchestrator. Cannot verify state machine correctness.
- **Proposed Fix**: (Same as F-GAP-028)
- **Blocking**: FEAT-071
- **Estimated Effort**: Included in TC-300

---

### F-GAP-087: Runtime Validation Gates Not Implemented
- **Severity**: BLOCKER
- **Category**: Feature Completeness
- **Description**: Runtime gates (Gates 1-10, TemplateTokenLint, Universality gates) are specified but not implemented. TC-460 (Validator W7) and TC-570 (Validation Gates Extensions) not started.
- **Evidence**:
  - TRACEABILITY_MATRIX.md:294-403: "Runtime Gates: Status: NOT YET IMPLEMENTED (See TC-460, TC-570)"
  - TRACEABILITY_MATRIX.md:679-681: "Runtime validation gates NOT YET IMPLEMENTED"
  - src/launch/validators/cli.py: Exists but only 273 lines (minimal stub)
- **Impact**: Cannot validate runs end-to-end. Cannot enforce TruthLock, Hugo build, internal links, consistency gates. Core validation loop (REQ-009) incomplete.
- **Proposed Fix**:
  1. Start TC-460 implementation immediately
  2. Implement all 10 core gates (schema, lint, hugo_config, content_layout_platform, hugo_build, internal_links, external_links, snippets, truthlock, consistency)
  3. Implement TemplateTokenLint gate (no unresolved __TOKENS__)
  4. Implement Universality gates (tier compliance, limitations honesty, distribution correctness, no hidden inference)
  5. Add launch_validate CLI entrypoint integration
  6. Add profile-based gate selection (local/ci/prod)
  7. Add timeout enforcement per gate
  8. Create validation_report.json with all gate results
  9. Add acceptance tests for each gate
  10. Start TC-570 for gate extensions (content_layout_platform gate, universality gates)
- **Blocking**: REQ-009 (validation gates), FEAT-044 through FEAT-053, FEAT-065
- **Estimated Effort**: 3-4 weeks (TC-460 + TC-570)

---

## MAJOR Gaps (6)

### F-GAP-002: No Justification for MCP Inference 80% Confidence Threshold
- **Severity**: MAJOR
- **Category**: Design Rationale
- **Description**: launch_start_run_from_github_repo_url (FEAT-062) uses 80% confidence threshold for inference ambiguity detection, but no ADR or empirical validation explains why 80% vs. 70% or 90%.
- **Evidence**:
  - 24_mcp_tool_schemas.md:227-231: "Confidence threshold: both family and platform must exceed 80% confidence"
  - REPORT.md Check 2: "No justification for 80% confidence threshold"
- **Impact**: May reject valid repos (too high) or accept ambiguous repos (too low). No data supporting threshold choice.
- **Proposed Fix**:
  1. Conduct empirical validation with sample repos:
     - Test 20-30 diverse repos (Python, .NET, Java, Node, Go, multi-platform)
     - Measure inference confidence for family and platform
     - Plot confidence distribution
     - Identify false positive rate (ambiguous repos accepted) and false negative rate (valid repos rejected) for thresholds 70%, 75%, 80%, 85%, 90%
  2. Document findings in ADR or spec section
  3. Choose threshold based on acceptable false positive/negative rate
  4. Update specs/24_mcp_tool_schemas.md with rationale
  5. Add telemetry: INFERENCE_CONFIDENCE event with actual confidence scores
- **Blocking**: FEAT-062 (MCP quickstart from GitHub)
- **Estimated Effort**: 3-5 days (empirical study + documentation)

---

### F-GAP-003: No Justification for Profile-Based Gate Timeout Values
- **Severity**: MAJOR
- **Category**: Design Rationale
- **Description**: Profile-based gate timeouts (FEAT-054, FEAT-055) use specific values (30s/60s/120s for local, 60s/120s/180s for ci) but no load testing data or rationale explains choices.
- **Evidence**:
  - 09_validation_gates.md:84-120: Timeout values defined without rationale
  - REPORT.md Check 2: "No justification for timeout values"
- **Impact**: Timeouts may be too short (false failures on slow hardware) or too long (hang detection delayed).
- **Proposed Fix**:
  1. Conduct load testing with pilot repos:
     - Measure actual gate execution times on reference hardware (CI runner specs)
     - Run each gate 10 times, record min/mean/max/p95/p99
     - Test on slow hardware (low-end dev machine)
  2. Set timeouts at p99 + 20% safety margin
  3. Document findings in specs/09_validation_gates.md or ADR
  4. Update timeout values based on data
  5. Add telemetry: GATE_EXECUTION_TIME event per gate
- **Blocking**: FEAT-054, FEAT-055
- **Estimated Effort**: 2-3 days (load testing + documentation)

---

### F-GAP-012: No Fixtures for Template Rendering Edge Cases
- **Severity**: MAJOR
- **Category**: Independent Testability
- **Description**: Content drafting features (FEAT-034 through FEAT-037) have partial testability. No fixtures for edge cases: missing tokens, recursive includes, circular template dependencies.
- **Evidence**:
  - REPORT.md Check 3: "No fixtures for template rendering edge cases"
  - specs/07_section_templates.md: Template rules defined but edge cases not enumerated
- **Impact**: Cannot verify error handling for malformed templates. Cannot test token replacement completeness.
- **Proposed Fix**:
  1. Create edge case fixtures:
     - template_with_missing_token.md (contains `__UNDEFINED_TOKEN__`)
     - template_with_recursive_include.md (includes itself)
     - template_with_circular_deps.md (A includes B, B includes A)
     - template_with_partial_platform_tokens.md (some __PLATFORM__ resolved, some not)
  2. Add acceptance tests:
     - Missing token → BLOCKER issue with token name and location
     - Recursive include → BLOCKER issue with include chain
     - Circular deps → BLOCKER issue with dependency graph
     - Partial resolution → BLOCKER issue (no unresolved tokens allowed)
  3. Document edge case handling in TC-440 (SectionWriter W5)
  4. Add to TemplateTokenLint gate (validate no unresolved tokens)
- **Blocking**: FEAT-034, FEAT-035, FEAT-036, FEAT-037
- **Estimated Effort**: 1 week

---

### F-GAP-033: No Prompt Hash Validation for LLM-Based Extraction
- **Severity**: MAJOR
- **Category**: Determinism Controls
- **Description**: LLM-based extraction (FEAT-012, FEAT-014, FEAT-015, FEAT-017, FEAT-018) has partial determinism. Temperature=0.0 enforced, but no prompt hash validation to detect prompt drift.
- **Evidence**:
  - REPORT.md Check 4: "LLM-based extraction with temperature=0.0, but no prompt hash validation"
  - specs/10_determinism_and_caching.md: "Replayable decisions (prompt hashes + input hashes)"
- **Impact**: Prompt changes break determinism without detection. Cannot debug "why did output change?" issues.
- **Proposed Fix**:
  1. Add prompt versioning to all LLM workers:
     - Compute prompt_hash = sha256(prompt_template + version)
     - Record prompt_hash in telemetry event for every LLM call
     - Record prompt_hash in artifact metadata (e.g., product_facts.json includes "extractor_prompt_hash")
  2. Add determinism check: if input unchanged but output changed, emit DETERMINISM_VIOLATION with prompt_hash diff
  3. Add to TC-560 (Determinism Harness): validate prompt_hash stability across golden runs
  4. Document in specs/10_determinism_and_caching.md
- **Blocking**: FEAT-012, FEAT-014, FEAT-015, FEAT-017, FEAT-018
- **Estimated Effort**: 1 week (add to all LLM workers)

---

### F-GAP-041: No Template Versioning Enforcement
- **Severity**: MAJOR
- **Category**: Determinism Controls
- **Description**: Template rendering (FEAT-034, FEAT-037) uses ruleset_version and templates_version but enforcement not verified. No runtime check that templates match declared version.
- **Evidence**:
  - REPORT.md Check 4: "Template versioning not enforced"
  - specs/20_rulesets_and_templates_registry.md: Versioning contract defined
  - specs/34_strict_compliance_guarantees.md (Guarantee K): "Spec/taskcard version locking"
- **Impact**: Template changes may break determinism without detection. Cannot reproduce runs if templates change.
- **Proposed Fix**:
  1. Add template version validation:
     - At run start, compute templates_hash = sha256(all_template_files_sorted)
     - Compare to expected hash for declared templates_version (from registry)
     - Fail with POLICY_TEMPLATE_VERSION_MISMATCH if hash differs
  2. Add to preflight validation (Gate P enhancement)
  3. Record templates_hash in run metadata (run_config or snapshot.json)
  4. Add to TC-560 (Determinism Harness): validate templates_hash matches golden run
  5. Document in specs/20_rulesets_and_templates_registry.md
- **Blocking**: FEAT-034, FEAT-037, REQ-023 (Guarantee K)
- **Estimated Effort**: 1 week

---

### F-GAP-063: No Centralized Error Code Registry
- **Severity**: MAJOR
- **Category**: MCP Tool Callability
- **Description**: MCP tool contracts define ~40 tool-specific error codes, but no centralized registry exists. Error codes defined inline in specs/24_mcp_tool_schemas.md and specs/01_system_contract.md:87-135, but not consolidated.
- **Evidence**:
  - REPORT.md Check 5: "No centralized error code registry"
  - 24_mcp_tool_schemas.md:33-44: Minimum error codes defined
  - 01_system_contract.md:92-135: Error code format and examples defined
- **Impact**: Error code collisions possible. No single source of truth for error codes. Hard to maintain consistency.
- **Proposed Fix**:
  1. Create docs/ERROR_CODES.md registry:
     - Format: Table with columns: Code | Component | Severity | Retryable | Description | Example
     - Consolidate all error codes from specs
     - Add usage examples and debugging guidance
  2. Add to Gate A1 (Spec Pack Validation): validate no error code collisions
  3. Generate error code enum from registry (Python enum or JSON schema)
  4. Update all specs to reference registry
  5. Add to CONTRIBUTING.md: "When adding new error code, update docs/ERROR_CODES.md"
- **Blocking**: All MCP tools (FEAT-060 through FEAT-070)
- **Estimated Effort**: 2-3 days (consolidation + validation)

---

## MINOR Gaps (3)

### F-GAP-004: No Explanation for Contradiction Priority Difference Threshold
- **Severity**: MINOR
- **Category**: Design Rationale
- **Description**: Automated contradiction resolution (FEAT-016) uses priority_diff >= 2 for automatic resolution vs. priority_diff == 1 for manual review, but no rationale explains why 2 vs. 1 or 3.
- **Evidence**:
  - 03_product_facts_and_evidence.md:138-146: "If priority_diff >= 2: Automatically prefer higher-priority source"
  - REPORT.md Check 2: "No explanation for priority difference threshold"
- **Impact**: Low impact (algorithm works, just lacks documentation). May be non-optimal threshold.
- **Proposed Fix**:
  1. Add rationale to specs/03_product_facts_and_evidence.md:
     - priority_diff == 1: Adjacent sources (e.g., source code constants vs. test assertions) may have legitimate disagreements → require human review
     - priority_diff >= 2: Non-adjacent sources (e.g., manifests vs. implementation docs) have clear authority hierarchy → auto-resolve
  2. Document examples:
     - Manifest (priority 1) vs. Implementation doc (priority 4): priority_diff = 3 → auto-resolve (prefer manifest)
     - Source constants (priority 2) vs. Test assertions (priority 3): priority_diff = 1 → manual review
  3. Consider making threshold configurable via ruleset if empirical data suggests different value
- **Blocking**: FEAT-016
- **Estimated Effort**: 1 hour (documentation only)

---

### F-GAP-084: No E2E Tests for Orchestrator State Transitions
- **Severity**: MINOR
- **Category**: Feature Completeness
- **Description**: E2E verification strategy defined (TC-522, TC-523) but no explicit E2E tests for orchestrator state transitions (CREATED → INGESTING → EXTRACTING → ... → DONE).
- **Evidence**:
  - REPORT.md Check 6: "No E2E tests for orchestrator state transitions"
  - TRACEABILITY_MATRIX.md:79-80: Pilot E2E defined but state transition coverage not explicit
- **Impact**: Cannot verify full pipeline state transitions. May miss state machine bugs not caught by unit tests.
- **Proposed Fix**:
  1. Add to TC-522 (CLI E2E):
     - Test: Run full pipeline (launch_run → DONE)
     - Verify: All expected state transitions occur (CREATED → INGESTING → EXTRACTING → CURATING → PLANNING → DRAFTING → LINKING → VALIDATING → READY_FOR_PR → DONE)
     - Verify: events.ndjson includes all state change events
     - Verify: No unexpected state transitions
  2. Add to TC-523 (MCP E2E):
     - Same as TC-522 but via MCP calls (launch_start_run → launch_get_status polling → launch_open_pr)
  3. Add negative test: simulate worker failure, verify state transition to FAILED
- **Blocking**: None (enhancement)
- **Estimated Effort**: 2-3 days (add to existing TC-522, TC-523)

---

### F-GAP-085: No E2E Tests for Fix Loop
- **Severity**: MINOR
- **Category**: Feature Completeness
- **Description**: E2E verification strategy defined but no explicit E2E tests for fix loop (VALIDATING → FIXING → VALIDATING).
- **Evidence**:
  - REPORT.md Check 6: "No E2E tests for fix loop"
  - specs/09_validation_gates.md:77-82: Fix loop defined
- **Impact**: Cannot verify end-to-end fix workflow. May miss integration bugs between Validator (W7) and Fixer (W8).
- **Proposed Fix**:
  1. Add to TC-522 (CLI E2E):
     - Test: Run with intentionally invalid content (e.g., broken internal link)
     - Verify: State transitions VALIDATING → FIXING → VALIDATING
     - Verify: launch_fix_next called, issue fixed, validation re-runs
     - Verify: Final validation_report.ok == true
  2. Add to TC-523 (MCP E2E):
     - Same as TC-522 but via MCP calls (launch_validate → launch_fix_next loop)
  3. Add negative test: max_fix_attempts exhausted, verify state transition to FAILED with error_code FIX_EXHAUSTED
- **Blocking**: None (enhancement)
- **Estimated Effort**: 2-3 days (add to existing TC-522, TC-523)

---

## Additional Gaps (Not Classified as BLOCKER/MAJOR/MINOR)

The following gaps are documented in REPORT.md but are cross-cutting or lower priority:

### Testability Gaps (FEAT-004 through FEAT-011, FEAT-021 through FEAT-025, etc.)

These are documented in REPORT.md Check 3 as "Partially Testable" or "Not Testable" but do not block production readiness. They represent incremental quality improvements:

- F-GAP-005: No acceptance criteria for "example candidates" from tests/
- F-GAP-006: No fixtures for multi-locale, multi-platform Hugo configs
- F-GAP-007: No acceptance criteria for multi-file citations
- F-GAP-008: No fixtures for asymmetric format support
- F-GAP-009: No determinism test for tier adjustment
- F-GAP-010: No fixtures for URL collision detection
- F-GAP-011: No acceptance criteria for V1/V2 mixed sections
- F-GAP-013: No integration tests for profile transitions
- F-GAP-014: No acceptance criteria for deterministic issue ordering
- F-GAP-015: No fixtures for ambiguous inference scenarios

These should be addressed during implementation taskcards but are not pre-implementation blockers.

### Determinism Gaps (FEAT-008, FEAT-010, FEAT-025, FEAT-030, etc.)

Documented in REPORT.md Check 4 as "No Determinism Controls" but lower priority:

- F-GAP-046: FEAT-008 (Binary Assets Discovery) - No ordering, no hashing
- F-GAP-047: FEAT-010 (Frontmatter Contract Discovery) - No seed, no ordering
- F-GAP-048: FEAT-025 (Generated Snippet Policy) - No prompt versioning
- F-GAP-049: FEAT-030, FEAT-032 (Content Quota & Product Type Adaptation) - No determinism controls
- F-GAP-050: FEAT-039, FEAT-040, FEAT-043 (Patch Engine Features) - No cache invalidation rules
- F-GAP-051: FEAT-057 (Fix Attempt Limiting) - No determinism guarantee
- F-GAP-053: FEAT-063 through FEAT-070 (MCP Tools) - No determinism controls beyond idempotency_key

These represent enhancement opportunities but do not block core determinism guarantee (TC-560 will test end-to-end determinism).

### Acceptance Criteria Gaps (Various features)

Documented in REPORT.md Check 6 as "Partial Acceptance Criteria":

- F-GAP-065: Discovery features - No acceptance criteria for empty results
- F-GAP-066: FEAT-010 - No acceptance criteria for missing frontmatter schema
- F-GAP-067: FEAT-011 - No acceptance criteria for multi-platform site configs
- F-GAP-068: FEAT-012 - No acceptance criteria for insufficient evidence boundary
- F-GAP-069: FEAT-014 - No acceptance criteria for multi-file citations
- F-GAP-070: FEAT-018 - No acceptance criteria for empty limitations
- F-GAP-071: FEAT-019, FEAT-020 - See F-GAP-022 (BLOCKER)
- F-GAP-072: Snippet features - No acceptance criteria for deduplication
- F-GAP-073: FEAT-025 - No acceptance criteria for allow_generated_snippets=false
- F-GAP-074: Planning features - No acceptance criteria for tier elevation/reduction
- F-GAP-075: URL features - No acceptance criteria for URL collision
- F-GAP-076: Content drafting - No acceptance criteria for token replacement completeness
- F-GAP-077: Fixer - No acceptance criteria for deterministic issue ordering
- F-GAP-078: Conflict features - No E2E verification strategy
- F-GAP-080: launch_open_pr - See F-GAP-061 (BLOCKER)
- F-GAP-082: FEAT-072 (Event Sourcing) - No acceptance criteria for event replay
- F-GAP-083: FEAT-073 (Deterministic Execution) - See F-GAP-030 (BLOCKER)

These should be addressed during taskcard implementation but do not block pre-implementation phase.

### MCP Tool Contract Gaps (FEAT-065, FEAT-066, FEAT-067)

Documented in REPORT.md Check 5 as "Partial Contracts":

- F-GAP-055: launch_validate - Error codes not fully enumerated
- F-GAP-056: launch_validate - No examples for gate-specific failures
- F-GAP-057: launch_fix_next - No examples for deterministic issue ordering
- F-GAP-058: launch_fix_next - No specification of single-issue-at-a-time enforcement
- F-GAP-059: launch_resume - No error codes enumerated
- F-GAP-060: launch_resume - No specification of resumable boundaries
- F-GAP-064: Validation failures - No examples for specific validation errors

These should be addressed in TC-460, TC-470 implementation but are not pre-implementation blockers.

### E2E Verification Gaps

Documented in REPORT.md Check 6:

- F-GAP-086: No E2E tests for multi-locale, multi-platform runs

Should be addressed in TC-520, TC-522, TC-523.

### Gate Coverage Gaps

Documented in REPORT.md Check 6:

- F-GAP-088: No gate for snippet deduplication
- F-GAP-089: No gate for cross-link validity

Enhancement opportunities, not blockers.

---

## Summary

**Total Gaps**: 86+ identified (22 detailed above, ~64 additional cross-cutting gaps documented in REPORT.md)

**Critical Path Blockers (Must Fix Before Production)**:
1. F-GAP-001, F-GAP-027, F-GAP-052, F-GAP-062, F-GAP-079: TC-480 (PR Manager) not started
2. F-GAP-022: TC-413 (Truth Lock) not started
3. F-GAP-025: TC-430 (Page Planner) not started
4. F-GAP-028, F-GAP-054, F-GAP-081: TC-300 (Orchestrator) not started
5. F-GAP-030: TC-560 (Determinism Harness) not started
6. F-GAP-061: launch_open_pr error codes missing
7. F-GAP-087: TC-460, TC-570 (Runtime Gates) not started

**Priority Order for Implementation**:
1. **Phase 1 (Critical Path)**: TC-300 (Orchestrator), TC-413 (TruthLock), TC-430 (PagePlanner) - 6-8 weeks
2. **Phase 2 (Validation)**: TC-460 (Validator), TC-570 (Gates), TC-560 (Determinism) - 5-6 weeks
3. **Phase 3 (PR & Release)**: TC-480 (PRManager), F-GAP-061/062 (MCP contracts) - 2-3 weeks
4. **Phase 4 (Quality)**: F-GAP-002/003 (Design Rationale), F-GAP-033/041 (Determinism), F-GAP-063 (Error Registry) - 2-3 weeks

**Estimated Total Effort**: 15-20 weeks (4-5 months) to close all BLOCKER and MAJOR gaps.

---

**End of Gaps Report**
