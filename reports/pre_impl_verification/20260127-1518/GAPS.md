# Consolidated Gaps Report

**Pre-Implementation Verification Run**: 20260127-1518
**Date**: 2026-01-27
**Source**: All 7 Agents (R, F, S, C, G, P, L)

---

## Executive Summary

**Total Gaps Identified**: 39 unique gaps
- **BLOCKER**: 4 (must fix before implementation starts)
- **MAJOR**: 5 (significant impact on quality/testability)
- **MINOR**: 30 (documentation, clarifications, enhancements)

**Critical Finding**: Most BLOCKER gaps relate to unstarted taskcards (TC-300, TC-413, TC-430, TC-460, TC-480, TC-560). No fundamental architecture or design flaws identified.

---

## Format

Each gap uses pattern: `GAP-NNN | SEVERITY | Category | Description`

**Severity Levels**:
- **BLOCKER**: Prevents implementation or creates critical ambiguity
- **MAJOR**: Significant impact on implementation, testing, or enforcement
- **MINOR**: Low impact, documentation/clarification/enhancement

---

## BLOCKER Gaps (4)

### GAP-001 | BLOCKER | Runtime Validation Gates Not Implemented

**Category**: Gates/Validators
**Source**: AGENT_G (G-GAP-001)

**Description**: Content validation gates (Gates 4-12) not implemented. Only scaffold stubs exist in src/launch/validators/cli.py:216-250.

**Impact**:
- No markdown quality enforcement
- No Hugo build validation
- No link integrity checks
- No TruthLock enforcement
- Scaffold correctly marks as FAILED in prod (no false passes), but gates not functional

**Evidence**:
- src/launch/validators/cli.py:216-250 (stubs)
- TRACEABILITY_MATRIX.md:321-324
- TC-460 (Validator W7): Not started
- TC-570 (validation gates extensions): Not started

**Proposed Fix**:
1. Implement Gates 4-12 in src/launch/validators/cli.py
2. Use deterministic patterns (sorted iteration, fixed rules, typed error codes)
3. Add gate results to validation_report.json
4. Respect profile-based timeouts (specs/09_validation_gates.md:86-119)

**Blocking**: TC-460, TC-570

---

### GAP-002 | BLOCKER | Rollback Metadata Validation Not Implemented

**Category**: Safety/PR Management
**Source**: AGENT_G (G-GAP-002), AGENT_R (R-GAP-001), AGENT_F (F-GAP-001)

**Description**: Guarantee L (Rollback + Recovery Contract) requires validation of rollback metadata, but no validator exists.

**Impact**:
- No enforcement of rollback metadata in PR artifacts
- Rollback procedures may fail
- Production runs may proceed without recovery plan

**Evidence**:
- specs/34_strict_compliance_guarantees.md (Guarantee L)
- TRACEABILITY_MATRIX.md:619-627 (status: PENDING)
- TC-480 (PRManager W9): Not started
- specs/schemas/pr.schema.json: rollback fields may need addition

**Required Fields**:
- `base_ref` (commit SHA, 40-char hex)
- `run_id` (string)
- `rollback_steps` (array of executable commands)
- `affected_paths` (array of file paths in PR diff)

**Error Code**: PR_MISSING_ROLLBACK_METADATA

**Proposed Fix**:
1. Add/update specs/schemas/pr.schema.json with rollback fields
2. Add rollback_metadata gate to src/launch/validators/cli.py (prod profile only)
3. Validate base_ref SHA format, affected_paths in PR diff
4. Define acceptance criteria in specs/34_strict_compliance_guarantees.md

**Blocking**: TC-480 (PRManager W9)

---

### GAP-003 | BLOCKER | Unstarted Critical Taskcards Block E2E Flow

**Category**: Plans/Taskcards
**Source**: AGENT_F (F-GAP-028, F-GAP-030, F-GAP-052, F-GAP-054, F-GAP-081), AGENT_P (STATUS_BOARD analysis)

**Description**: 5 critical taskcards not started, blocking E2E orchestration flow.

**Impact**:
- No orchestrator to coordinate workers (TC-300)
- No TruthLock/claim markers (TC-413)
- No page planning (TC-430)
- No PR management (TC-480)
- No determinism harness (TC-560)
- Cannot run end-to-end tests

**Unstarted Taskcards**:
1. **TC-300** (Orchestrator): LangGraph state machine, worker coordination
2. **TC-413** (TruthLock): Claim compilation, stability tracking
3. **TC-430** (IAPlanner): Page plan generation, tier selection
4. **TC-480** (PRManager): PR creation, rollback metadata, commit service integration
5. **TC-560** (Determinism Harness): Golden runs, diff comparison, byte-identity verification

**Evidence**:
- plans/taskcards/STATUS_BOARD.md: All 5 taskcards marked "not started"
- AGENT_F/REPORT.md: Testability gaps for corresponding features (FEAT-071, FEAT-019/020, FEAT-026/028/030, FEAT-058/059, FEAT-073)

**Proposed Fix**:
1. Prioritize TC-300 (Orchestrator) and TC-560 (Determinism) for Phase 1
2. Follow with TC-413, TC-430, TC-480 in Phase 2
3. Define acceptance criteria for each taskcard before starting implementation
4. Create test fixtures for determinism validation

**Blocking**: All E2E flows, pilot validation (TC-522, TC-523)

---

### GAP-004 | BLOCKER | Missing Specification for Floating Ref Runtime Rejection

**Category**: Safety/Guarantees
**Source**: AGENT_G (G-GAP-003), AGENT_R (referenced)

**Description**: Guarantee A (Input Immutability) requires runtime rejection of floating refs, but implementation not integrated.

**Impact**:
- Floating refs may be used at runtime despite preflight validation
- Violates Guarantee A at runtime surface
- No circuit breaker for determinism violations

**Evidence**:
- specs/34_strict_compliance_guarantees.md:40-58 (Guarantee A)
- Gate J (tools/validate_pinned_refs.py): Preflight enforcement ✅
- Runtime enforcement: TRACEABILITY_MATRIX.md:346-350 (status: PENDING)
- TC-300, TC-460: Runtime rejection not integrated

**Proposed Fix**:
1. Add runtime validation to launch_validate (src/launch/validators/cli.py)
2. Validate all *_ref fields in run_config are commit SHAs (40-char hex)
3. Reject floating refs (refs/heads/*, refs/tags/*, branch names) with error code: POLICY_FLOATING_REF_DETECTED
4. Integration: TC-300 (orchestrator), TC-460 (runtime gates)

**Blocking**: Guarantee A runtime enforcement

---

## MAJOR Gaps (5)

### GAP-005 | MAJOR | Missing Design Rationale for Key Thresholds

**Category**: Design Justification
**Source**: AGENT_F (F-GAP-002, F-GAP-003, F-GAP-004)

**Description**: No justification for critical threshold choices:
1. MCP inference confidence threshold (80%)
2. Profile-based gate timeout values (30s/60s/120s)
3. Contradiction resolution priority difference threshold (>= 2)

**Impact**:
- Cannot validate threshold choices against empirical data
- May need re-tuning in production
- No rationale for reviewers/auditors

**Evidence**:
- specs/24_mcp_tool_schemas.md:227-231 (80% confidence, no justification)
- specs/09_validation_gates.md:84-120 (timeouts, no load testing data)
- specs/03_product_facts_and_evidence.md:138-146 (priority_diff >= 2, no rationale)

**Proposed Fix**:
1. Add ADR (Architecture Decision Record) for each threshold
2. Document trade-offs, alternatives considered
3. Plan empirical validation during pilot phase (TC-520)
4. Allow tuning via run_config overrides for testing

**Blocking**: Production threshold validation

---

### GAP-006 | MAJOR | No Centralized Error Code Registry

**Category**: Error Handling
**Source**: AGENT_F (F-GAP-063), AGENT_R (referenced)

**Description**: Error codes defined across 10+ files with no centralized registry or validation.

**Impact**:
- Risk of error code collisions
- No canonical list for documentation
- Cannot validate error_code uniqueness

**Evidence**:
- specs/01_system_contract.md:92-136 (defines error taxonomy)
- Used in: path_validation.py, budget_tracker.py, diff_analyzer.py, http.py, subprocess.py, and others
- No centralized error_codes.py or ERROR_CODES.md

**Proposed Fix**:
1. Create src/launch/util/error_codes.py with all error codes
2. Add ERROR_CODES.md documentation
3. Add preflight gate to validate no duplicates
4. Require all new error codes added to registry

---

### GAP-007 | MAJOR | Determinism Controls Missing for LLM Features

**Category**: Determinism
**Source**: AGENT_F (F-GAP-033, F-GAP-035, F-GAP-041, F-GAP-042)

**Description**: LLM-based features (facts extraction, content drafting, fixing) use temperature=0.0 but lack prompt versioning and determinism harness.

**Impact**:
- Cannot guarantee byte-identical outputs
- Prompt changes may break determinism silently
- No validation of determinism claims

**Evidence**:
- FEAT-012 (Product Facts Extraction): temperature=0.0 but no prompt hash
- FEAT-034 (Template Rendering): LLM-based but template versioning not enforced
- FEAT-041/042 (Conflict Resolution): LLM-based fixer, no determinism harness
- specs/10_determinism_and_caching.md: No prompt versioning requirement

**Proposed Fix**:
1. Add prompt_version field to all LLM calls (hash of prompt template)
2. Log prompt_version to telemetry for every LLM call
3. Add determinism validation to TC-560 harness (compare prompts across runs)
4. Enforce ruleset_version and templates_version for all prompts

**Blocking**: TC-560 (Determinism Harness), REQ-079 validation

---

### GAP-008 | MAJOR | Missing Test Fixtures for Edge Cases

**Category**: Testability
**Source**: AGENT_F (F-GAP-005 through F-GAP-077)

**Description**: 22 features lack test fixtures for edge cases:
- Multi-locale/multi-platform Hugo configs
- URL collision detection
- Template rendering with missing tokens
- Snippet deduplication
- Asymmetric format support
- Mixed V1/V2 platform paths

**Impact**:
- Cannot test edge cases until runtime
- Risk of production failures
- Incomplete coverage in test suite

**Evidence**:
- AGENT_F/REPORT.md: 25/73 features marked "Partially Testable"
- No fixtures/ directory in repository
- TC-522, TC-523 (pilot E2E): No edge case fixtures defined

**Proposed Fix**:
1. Create tests/fixtures/ directory structure
2. Add synthetic repos for each adapter archetype
3. Add edge case configs (multi-locale, missing tokens, etc.)
4. Reference fixtures in taskcard acceptance criteria
5. Use fixtures in TC-522, TC-523 E2E tests

---

### GAP-009 | MAJOR | Ambiguity in "Byte-Identical Artifacts" Acceptance Criteria

**Category**: Determinism
**Source**: AGENT_R (R-GAP-002)

**Description**: REQ-079 requires "byte-identical artifacts" but ambiguous about:
1. Whether timestamps acceptable variance
2. Whether event_id/UUID generation breaks identity
3. Whether line ending normalization (CRLF vs LF) counts
4. What "drafts" refers to (which files?)

**Impact**:
- Cannot implement TC-560 determinism harness without clarification
- Risk of false failures in determinism tests
- Unclear acceptance criteria for REQ-079

**Evidence**:
- specs/10_determinism_and_caching.md:51-52 (byte-identical requirement)
- specs/10_determinism_and_caching.md:52 (allows variance only in events.ndjson for ts/event_id)
- No specification for timestamp handling in other artifacts
- No line ending normalization rules

**Proposed Fix**:
1. Update specs/10_determinism_and_caching.md with explicit rules:
   - Artifacts MUST NOT include timestamps except in events.ndjson
   - UUIDs/event_ids acceptable variance only in events.ndjson
   - Line endings MUST be normalized to LF before comparison
   - "Drafts" = all files under RUN_DIR/work/site/ matching *.md
2. Add determinism test specification to TC-560:
   - Run twice with same inputs
   - Normalize line endings
   - Exclude events.ndjson from comparison
   - Compare byte-for-byte using sha256 hashes

---

## MINOR Gaps (30)

*(Selected Most Critical)*

### GAP-010 | MINOR | Traceability Matrix Missing Worker Contracts Spec

**Category**: Documentation
**Source**: AGENT_P (P-GAP-001)

**Description**: specs/21_worker_contracts.md extensively referenced but not in traceability matrix summary.

**Fix**: Add to plans/traceability_matrix.md under "Worker Contracts" section

---

### GAP-011 | MINOR | State Management Specs Not in Traceability Matrix

**Category**: Documentation
**Source**: AGENT_P (P-GAP-002)

**Description**: specs/state-graph.md and specs/state-management.md not in traceability matrix.

**Fix**: Add to plans/traceability_matrix.md under "Core contracts" section

---

### GAP-012 | MINOR | Navigation Spec Missing Explicit Mapping

**Category**: Documentation
**Source**: AGENT_P (P-GAP-003)

**Description**: specs/22_navigation_and_existing_content_update.md has no explicit taskcard mapping.

**Fix**: Verify TC-430, TC-450 cover requirements or create micro-taskcard

---

### GAP-013 | MINOR | Missing Specification for "Minimal-Diff Discipline" Heuristics

**Category**: Specification Clarity
**Source**: AGENT_R (R-GAP-003)

**Description**: Guarantee G requires >80% formatting-only changes flagged, but no algorithm specified for detecting formatting-only.

**Fix**: Add algorithm to specs/34_strict_compliance_guarantees.md (normalize whitespace, compare semantic content)

---

### GAP-014 | MINOR | No Automated Gate for Test Determinism (Guarantee I)

**Category**: Gates/Validators
**Source**: AGENT_G (G-GAP-010), AGENT_R (referenced)

**Description**: Guarantee I (Non-Flaky Tests) has no automated gate to validate PYTHONHASHSEED=0 in test configs.

**Fix**: Add Gate T to validate pytest.ini or pyproject.toml includes PYTHONHASHSEED=0

---

### GAP-015 | MINOR | Schema SHA Format Validation Missing for Guarantee A

**Category**: Schemas
**Source**: AGENT_G (G-GAP-009)

**Description**: run_config.schema.json lacks SHA format validation for *_ref fields (Guarantee A).

**Fix**: Add pattern: "^[a-f0-9]{40}$" to all *_ref fields in run_config.schema.json

---

### Additional MINOR Gaps (GAP-016 through GAP-039)

*(Consolidated list from all agents, see individual agent reports for details)*

- GAP-016: No E2E tests for orchestrator state transitions (AGENT_F F-GAP-084)
- GAP-017: No E2E tests for fix loop (AGENT_F F-GAP-085)
- GAP-018: No E2E tests for multi-locale/platform runs (AGENT_F F-GAP-086)
- GAP-019: No gate for snippet deduplication (AGENT_F F-GAP-088)
- GAP-020: No gate for cross-link validity (AGENT_F F-GAP-089)
- GAP-021: Missing acceptance criteria for source root discovery (AGENT_F F-GAP-016)
- GAP-022: Missing fixtures for test command inference (AGENT_F F-GAP-017)
- GAP-023: Missing acceptance criteria for binary vs text detection (AGENT_F F-GAP-018)
- GAP-024: Missing fixtures for frontmatter schema edge cases (AGENT_F F-GAP-019)
- GAP-025: Missing acceptance criteria for minimal vs zero evidence boundary (AGENT_F F-GAP-020)
- GAP-026: Missing fixtures for limitations extraction (AGENT_F F-GAP-021)
- GAP-027: Missing fixtures for snippet deduplication (AGENT_F F-GAP-023)
- GAP-028: Missing acceptance criteria for generated snippet policy (AGENT_F F-GAP-024)
- GAP-029: Missing fixtures for circular patch dependencies (AGENT_F F-GAP-026)
- GAP-030: MCP validate tool partial contract (AGENT_F F-GAP-055/056)
- GAP-031: MCP fix_next deterministic ordering examples missing (AGENT_F F-GAP-057/058)
- GAP-032: MCP resume error codes not enumerated (AGENT_F F-GAP-059/060)
- GAP-033: MCP validation error examples missing (AGENT_F F-GAP-064)
- GAP-034: Secret redaction utilities pending (AGENT_G G-GAP-004)
- GAP-035: Template token lint gate pending (AGENT_G G-GAP-006)
- GAP-036: Internal links gate behavior undefined for broken anchors (AGENT_G G-GAP-007)
- GAP-037: External links gate profile behavior needs clarification (AGENT_G G-GAP-008)
- GAP-038: Implied requirements not promoted (AGENT_R R-GAP-004 through R-GAP-008)
- GAP-039: Coordination spec missing explicit callouts (AGENT_P P-GAP-004)

---

## Gap Summary by Source Agent

| Agent | BLOCKER | MAJOR | MINOR | Total |
|-------|---------|-------|-------|-------|
| AGENT_R (Requirements) | 1 | 2 | 5 | 8 |
| AGENT_F (Features) | 1 | 1 | 20 | 22 |
| AGENT_S (Specs) | 0 | 0 | 7 | 7 |
| AGENT_C (Schemas) | 0 | 0 | 0 | 0 |
| AGENT_G (Gates) | 2 | 0 | 8 | 10 |
| AGENT_P (Plans) | 0 | 0 | 6 | 6 |
| AGENT_L (Links) | 0 | 2 | 6 | 8 |

**Total Unique Gaps**: 39 (after de-duplication)

---

## Prioritization for Healing

### Phase 1 (Pre-Implementation) - Must Fix Before Starting

1. **GAP-003**: Start critical taskcards (TC-300, TC-413, TC-430, TC-480, TC-560)
2. **GAP-009**: Clarify byte-identical acceptance criteria
3. **GAP-005**: Document threshold rationale (ADRs)
4. **GAP-008**: Create test fixtures

### Phase 2 (During Implementation) - Fix Alongside Development

1. **GAP-001**: Implement runtime validation gates (TC-460, TC-570)
2. **GAP-002**: Implement rollback metadata validation (TC-480)
3. **GAP-004**: Integrate floating ref runtime rejection (TC-300, TC-460)
4. **GAP-007**: Add prompt versioning for determinism
5. **GAP-006**: Create centralized error code registry

### Phase 3 (Documentation & Polish) - Fix Before Production

1. **GAP-010 through GAP-015**: Documentation updates
2. **GAP-016 through GAP-039**: Minor gaps (fixtures, examples, clarifications)

---

## Evidence Sources

All gaps consolidated from:
- reports/pre_impl_verification/20260127-1518/agents/AGENT_R/GAPS.md
- reports/pre_impl_verification/20260127-1518/agents/AGENT_F/GAPS.md
- reports/pre_impl_verification/20260127-1518/agents/AGENT_S/GAPS.md
- reports/pre_impl_verification/20260127-1518/agents/AGENT_C/GAPS.md
- reports/pre_impl_verification/20260127-1518/agents/AGENT_G/GAPS.md
- reports/pre_impl_verification/20260127-1518/agents/AGENT_P/GAPS.md
- reports/pre_impl_verification/20260127-1518/agents/AGENT_L/GAPS.md

**Consolidation Method**: De-duplicated, renumbered, prioritized by severity and implementation phase
**Validation**: All gaps have evidence citations and proposed fixes
