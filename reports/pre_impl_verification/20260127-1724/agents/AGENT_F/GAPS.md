# Feature Validation Gaps

This document catalogs all gaps identified during AGENT_F feature validation.

**Generation Date**: 2026-01-27
**Agent**: AGENT_F
**Total Gaps Identified**: 25

**Severity Breakdown:**
- **BLOCKER**: 3 (implementation blockers preventing full validation)
- **WARNING**: 5 (testability or reproducibility concerns)
- **MINOR**: 17 (documentation gaps, missing ADRs, or missing test fixtures)

---

## BLOCKER Gaps

### F-GAP-021 | BLOCKER | Runtime Secret Redaction Not Implemented
**Feature:** FEAT-030 (Secret Redaction - Guarantee E)
**Evidence:** `plans/traceability_matrix.md:284` states "Gate L implemented preflight scan only; runtime redaction PENDING"
**Impact:** Secrets may leak in runtime logs/artifacts/reports despite preflight scan passing
**Root Cause:** TC-590 (security and secrets) not started
**Proposed Fix:**
1. Implement runtime redaction utilities in `src/launch/util/redaction.py` or `src/launch/util/logging.py`
2. Integrate redaction into all logging statements (use logging filters)
3. Scan `runs/**/logs/**` and `runs/**/reports/**` post-run
4. Add tests in `tests/unit/util/test_redaction.py`
5. Evidence: `specs/34_strict_compliance_guarantees.md:173-187` (secret patterns, redaction rules)

**Acceptance Criteria:**
- All secret patterns redacted to `***REDACTED***` in logs
- Post-run scan detects zero leaked secrets
- Tests verify redaction for all patterns in `specs/34_strict_compliance_guarantees.md:173-178`

---

### F-GAP-022 | BLOCKER | Rollback Metadata Generation Not Implemented
**Feature:** FEAT-036 (Rollback Metadata Validation - Guarantee L)
**Evidence:** `plans/traceability_matrix.md:492` states "TC-480 not started"
**Impact:** Cannot validate Guarantee L (rollback contract) until PRManager implemented
**Root Cause:** TC-480 (PRManager W9) not started
**Proposed Fix:**
1. Implement TC-480 PRManager per `specs/21_worker_contracts.md:322-351`
2. Generate `pr.json` with rollback fields: `base_ref`, `run_id`, `rollback_steps`, `affected_paths`
3. Validate `pr.json` against `specs/schemas/pr.schema.json`
4. Integrate Gate 13 runtime validation per `specs/09_validation_gates.md:430-468`
5. Add tests in `tests/integration/test_pr_manager.py`

**Acceptance Criteria:**
- `pr.json` artifact exists with all required rollback fields
- Gate 13 passes in prod profile
- Rollback steps are executable and accurate

---

### F-GAP-023 | BLOCKER | LangGraph Orchestrator Not Implemented
**Feature:** FEAT-038 (LangGraph Orchestrator State Machine)
**Evidence:** `plans/traceability_matrix.md:30` states "TC-300 not started"
**Impact:** Cannot execute full pipeline end-to-end; all MCP tools depend on orchestrator
**Root Cause:** TC-300 (orchestrator) not started
**Proposed Fix:**
1. Implement TC-300 orchestrator per `specs/state-graph.md:1-150`
2. Define LangGraph state machine with nodes for W1-W9
3. Implement state transitions per `specs/28_coordination_and_handoffs.md:1-100`
4. Integrate with MCP tools per `specs/14_mcp_endpoints.md:8-17`
5. Add orchestrator integration tests per `plans/traceability_matrix.md:30`

**Acceptance Criteria:**
- Orchestrator executes full W1→W9 pipeline
- State transitions deterministic per `specs/10_determinism_and_caching.md:39-46`
- MCP tools invoke orchestrator successfully
- Integration tests pass (graph smoke tests, transition determinism)

---

## WARNING Gaps

### F-GAP-008 | WARNING | Template Rendering Reproducibility Conditional on LLM Determinism
**Feature:** FEAT-011 (Section Template Rendering)
**Evidence:** `specs/10_determinism_and_caching.md:4-9` enforces temperature=0.0, but LLM-based rendering may have variance
**Impact:** Byte-identical outputs not guaranteed across LLM providers
**Proposed Fix:**
1. Add determinism tests in TC-560 harness comparing outputs across runs
2. If variance detected, implement stricter prompt templates or structured output constraints
3. Document LLM provider compatibility matrix (which providers support byte-identical outputs)
4. Evidence: `specs/10_determinism_and_caching.md:80-106` (prompt versioning helps detect drift)

**Acceptance Criteria:**
- TC-560 determinism harness validates template rendering produces byte-identical outputs
- If variance > 0%, document which LLM providers are deterministic
- Prompt versioning tracks all template prompts

---

### F-GAP-011 | WARNING | Missing Test Fixtures for Patch Conflict Scenarios
**Feature:** FEAT-014 (Patch Idempotency and Conflict Detection)
**Evidence:** `specs/08_patch_engine.md:71-144` documents conflict detection algorithm, but no explicit test fixtures found
**Impact:** Cannot validate conflict detection logic without test cases
**Proposed Fix:**
1. Create test fixtures in `tests/fixtures/patch_conflicts/`
2. Test cases:
   - Anchor not found: file missing target heading
   - Line range out of bounds: patch targets line 100 in 50-line file
   - Content mismatch: expected content hash doesn't match actual
   - Path outside allowed_paths: patch targets forbidden path
3. Add tests in `tests/unit/patch_engine/test_conflict_detection.py`

**Acceptance Criteria:**
- All 5 conflict categories have test fixtures
- Conflict detection tests pass
- Edge cases documented in `specs/08_patch_engine.md:119-139`

---

### F-GAP-012 | WARNING | Fix Loop Reproducibility Conditional on LLM Determinism
**Feature:** FEAT-016 (Validation Fix Loop)
**Evidence:** `specs/21_worker_contracts.md:309-310` requires no new factual claims, but LLM-based fixes may vary
**Impact:** Fix attempts may produce different patches across runs
**Proposed Fix:**
1. Add fix loop tests in TC-560 determinism harness
2. If variance detected, implement stricter fix templates (similar to FEAT-011 solution)
3. Document which fix types are deterministic vs LLM-dependent
4. Evidence: `specs/08_patch_engine.md:98-107` (three-way merge with manual review fallback)

**Acceptance Criteria:**
- TC-560 validates fix loop produces consistent patches
- If variance > 0%, document non-deterministic fix scenarios
- Max fix attempts prevent infinite loops per `specs/01_system_contract.md:158`

---

### F-GAP-017 | WARNING | MCP Inference Algorithm Not Pilot-Validated
**Feature:** FEAT-020 (MCP Quickstart from GitHub Repo URL)
**Evidence:** `specs/adr/001_inference_confidence_threshold.md:21-30` pilot validation plan not yet executed
**Impact:** 80% confidence threshold may produce false positives (incorrect inference) or false negatives (unnecessary ambiguity)
**Proposed Fix:**
1. Execute ADR-001 pilot validation plan per `specs/adr/001_inference_confidence_threshold.md:21-30`
2. Test with 20+ representative repos (Python, .NET, Node, Java, multi-product)
3. Measure false positive rate (<5% target) and false negative rate
4. Tune threshold (80% → 85% or 90%) if false positive rate >5%
5. Document validated threshold in ADR-001

**Acceptance Criteria:**
- 20+ repos tested
- False positive rate <5%
- False negative rate documented
- Threshold validated or tuned

---

### F-GAP-024 | WARNING | Caching Implementation Status Unclear
**Feature:** FEAT-039 (Caching with Content Hashing)
**Evidence:** `specs/10_determinism_and_caching.md:30-38` defines caching strategy, but no taskcard references found
**Impact:** Unclear if caching is implemented; may impact performance and determinism validation
**Proposed Fix:**
1. Verify caching implementation status (search for cache_key usage in codebase)
2. If not implemented, create taskcard for caching implementation
3. If implemented, document in traceability matrix
4. Add caching tests in TC-560 (cache hits/misses, key computation)

**Acceptance Criteria:**
- Caching implementation status documented
- If implemented: tests verify cache_key formula `sha256(model_id + "|" + prompt_hash + "|" + inputs_hash)`
- If not implemented: taskcard created

---

## MINOR Gaps (Documentation/ADR/Fixtures)

### F-GAP-001 | MINOR | Missing Fixtures for .NET/Node/Java Adapters
**Feature:** FEAT-002 (Repository Adapter Selection)
**Evidence:** `specs/pilots/` contains only Python pilots (pilot-aspose-3d-foss-python, pilot-aspose-note-foss-python)
**Impact:** Adapter selection logic for .NET/Node/Java untested
**Proposed Fix:** Add pilot configs for .NET, Node, Java repos in `specs/pilots/`

---

### F-GAP-002 | MINOR | No Explicit Acceptance Tests for Adapter Selection Logic
**Feature:** FEAT-002 (Repository Adapter Selection)
**Evidence:** `plans/acceptance_test_matrix.md:37` covers deterministic fingerprints, but no explicit adapter selection tests
**Impact:** Adapter selection implicitly tested, but not explicitly validated
**Proposed Fix:** Add adapter selection tests to `plans/acceptance_test_matrix.md` or TC-520 pilots

---

### F-GAP-003 | MINOR | Missing Explicit Test Fixtures with Known Frontmatter Patterns
**Feature:** FEAT-003 (Frontmatter Contract Discovery)
**Evidence:** `specs/templates/` contain frontmatter examples, but no explicit test fixtures with known expected contracts
**Impact:** Frontmatter discovery implicitly tested via pilots, but edge cases not validated
**Proposed Fix:** Create test fixtures in `tests/fixtures/frontmatter_discovery/` with known schemas

---

### F-GAP-004 | MINOR | No ADR for Facts Extraction Methodology (LLM vs Rule-Based)
**Feature:** FEAT-005 (Product Facts Extraction)
**Evidence:** No ADR found documenting why LLM-based extraction vs rule-based parsing
**Impact:** Design rationale not documented; future implementers may question approach
**Proposed Fix:** Create ADR documenting LLM-based extraction choice (likely: universality, adaptability)

---

### F-GAP-005 | MINOR | No ADR for Snippet Extraction Methodology (Parse-Only vs Execute)
**Feature:** FEAT-008 (Snippet Extraction and Curation)
**Evidence:** No ADR found documenting why parse-only vs execution-based extraction
**Impact:** Design rationale implicit in Guarantee J (untrusted code), but not explicit ADR
**Proposed Fix:** Create ADR linking snippet extraction to Guarantee J (security rationale)

---

### F-GAP-006 | MINOR | No ADR for Page Planning Methodology (Plan-First vs Incremental)
**Feature:** FEAT-009 (Page Planning with Template Selection)
**Evidence:** No ADR found documenting why plan-first vs incremental page generation
**Impact:** Design rationale implicit in `specs/06_page_planning.md:10-25`, but not explicit ADR
**Proposed Fix:** Create ADR documenting plan-first benefits (validation before writing, parallelization)

---

### F-GAP-007 | MINOR | No ADR for V2 Layout Design Rationale
**Feature:** FEAT-010 (Platform-Aware Content Layout V2)
**Evidence:** No ADR found documenting why `/{locale}/{platform}/` path structure vs alternatives
**Impact:** Design rationale implicit in existing Aspose sites, but not documented
**Proposed Fix:** Create ADR documenting V2 layout benefits (cross-platform consistency, Hugo config alignment)

---

### F-GAP-009 | MINOR | No Explicit Acceptance Tests for Template Rendering
**Feature:** FEAT-011 (Section Template Rendering)
**Evidence:** `plans/acceptance_test_matrix.md:49-50` covers W5/W6 patches, but no explicit template rendering tests
**Impact:** Template rendering implicitly tested, but not explicitly validated
**Proposed Fix:** Add template rendering tests to acceptance matrix or TC-560

---

### F-GAP-010 | MINOR | Missing Explicit Test Fixtures with Claim Markers
**Feature:** FEAT-012 (Claim Marker Insertion)
**Evidence:** `specs/23_claim_markers.md` defines format, but no explicit test fixtures with expected claim markers
**Impact:** Claim marker insertion implicitly tested via Gate 9, but edge cases not validated
**Proposed Fix:** Create test fixtures in `tests/fixtures/claim_markers/` with expected markers

---

### F-GAP-013 | MINOR | Missing Explicit Test Fixtures for Fix Scenarios
**Feature:** FEAT-016 (Validation Fix Loop)
**Evidence:** `specs/08_patch_engine.md:98-114` documents fix strategies, but no explicit test fixtures
**Impact:** Fix loop implicitly tested, but specific fix scenarios not validated
**Proposed Fix:** Create test fixtures in `tests/fixtures/fix_scenarios/` (markdown lint fixes, frontmatter fixes, etc.)

---

### F-GAP-014 | MINOR | Missing Explicit Test Fixtures for PR Creation
**Feature:** FEAT-017 (PR Creation with Rollback Metadata)
**Evidence:** `specs/12_pr_and_release.md` defines PR template, but no explicit test fixtures
**Impact:** PR creation implicitly tested via pilots, but edge cases not validated
**Proposed Fix:** Create test fixtures in `tests/fixtures/pr_creation/` with expected PR bodies

---

### F-GAP-015 | MINOR | No ADR for MCP vs Other API Protocols
**Feature:** FEAT-018 (MCP Server with 10+ Tools)
**Evidence:** No ADR found documenting why MCP vs REST API vs gRPC
**Impact:** Design rationale implicit in MCP being agent-standard, but not documented
**Proposed Fix:** Create ADR documenting MCP choice (agent ecosystem, tool calling standard)

---

### F-GAP-016 | MINOR | Missing Explicit Acceptance Tests for URL Parsing Logic
**Feature:** FEAT-019 (MCP Quickstart from Product URL)
**Evidence:** `specs/24_mcp_tool_schemas.md:138-143` defines URL patterns, but no explicit parsing tests
**Impact:** URL parsing implicitly tested via MCP E2E (TC-523), but pattern edge cases not validated
**Proposed Fix:** Add URL parsing tests to TC-523 or create unit tests in `tests/unit/mcp/test_url_parsing.py`

---

### F-GAP-018 | MINOR | No ADR for LLM Provider Abstraction Approach
**Feature:** FEAT-022 (LLM Provider Abstraction)
**Evidence:** No ADR found documenting why OpenAI-compatible vs multi-provider SDKs
**Impact:** Design rationale implicit in LangChain usage, but not explicit ADR
**Proposed Fix:** Create ADR documenting OpenAI-compatible choice (may be implicit in LangChain)

---

### F-GAP-019 | MINOR | get_telemetry MCP Tool Schema Missing
**Feature:** FEAT-023 (Local Telemetry API)
**Evidence:** `specs/14_mcp_endpoints.md:92` mentions get_telemetry tool, but schema not in `specs/24_mcp_tool_schemas.md`
**Impact:** MCP callability incomplete (tool mentioned but not schema-defined)
**Proposed Fix:** Add get_telemetry schema to `specs/24_mcp_tool_schemas.md`

---

### F-GAP-020 | MINOR | Missing Explicit Test Fixtures for Commit Service Calls
**Feature:** FEAT-024 (GitHub Commit Service)
**Evidence:** `specs/17_github_commit_service.md` defines request/response, but no explicit test fixtures
**Impact:** Commit service implicitly tested via pilots, but edge cases not validated
**Proposed Fix:** Create test fixtures in `tests/fixtures/commit_service/` with mock requests/responses

---

### F-GAP-025 | MINOR | Prompt Versioning Implementation Status Unclear
**Feature:** FEAT-040 (Prompt Versioning for Determinism)
**Evidence:** `specs/10_determinism_and_caching.md:80-106` defines requirement, but no taskcard references found
**Impact:** Unclear if prompt versioning is implemented; critical for determinism validation
**Proposed Fix:**
1. Verify prompt versioning implementation (search for prompt_version in codebase)
2. If not implemented, create taskcard for prompt versioning
3. If implemented, document in traceability matrix
4. Add prompt versioning tests in TC-560

---

## Gap Summary by Category

### Implementation Gaps (BLOCKER)
- **F-GAP-021**: Runtime secret redaction (TC-590)
- **F-GAP-022**: Rollback metadata generation (TC-480)
- **F-GAP-023**: LangGraph orchestrator (TC-300)

### Testability Gaps (WARNING)
- **F-GAP-008**: Template rendering reproducibility (LLM determinism)
- **F-GAP-011**: Patch conflict test fixtures
- **F-GAP-012**: Fix loop reproducibility (LLM determinism)
- **F-GAP-017**: MCP inference algorithm pilot validation
- **F-GAP-024**: Caching implementation status

### Documentation Gaps (MINOR)
- **ADR Gaps**: F-GAP-004, F-GAP-005, F-GAP-006, F-GAP-007, F-GAP-015, F-GAP-018 (6 missing ADRs)
- **Test Fixture Gaps**: F-GAP-001, F-GAP-003, F-GAP-010, F-GAP-011, F-GAP-013, F-GAP-014, F-GAP-020 (7 missing fixtures)
- **Acceptance Test Gaps**: F-GAP-002, F-GAP-009, F-GAP-016 (3 implicit tests needing explicit coverage)
- **Schema Gaps**: F-GAP-019 (1 missing MCP tool schema)
- **Status Unclear**: F-GAP-024, F-GAP-025 (2 features with unclear implementation status)

---

## Prioritized Remediation Plan

### Phase 1: Blockers (Required for Implementation)
1. **F-GAP-023**: Implement TC-300 orchestrator (highest priority)
2. **F-GAP-022**: Implement TC-480 PRManager with rollback metadata
3. **F-GAP-021**: Implement TC-590 runtime secret redaction

### Phase 2: Testability Warnings (Required for Validation)
1. **F-GAP-024**: Verify caching implementation status
2. **F-GAP-025**: Verify prompt versioning implementation status
3. **F-GAP-017**: Execute ADR-001 pilot validation for MCP inference
4. **F-GAP-011**: Create patch conflict test fixtures
5. **F-GAP-008, F-GAP-012**: Add LLM determinism tests to TC-560

### Phase 3: Documentation Gaps (Quality Improvements)
1. Create 6 missing ADRs (F-GAP-004/005/006/007/015/018)
2. Create 7 missing test fixture sets
3. Add 3 explicit acceptance tests
4. Add get_telemetry MCP tool schema (F-GAP-019)

---

## Overall Gap Assessment

**Critical Path Blockers:** 3 (TC-300, TC-480, TC-590)
**Testability Concerns:** 5 (LLM determinism, pilot validation, implementation status)
**Quality Improvements:** 17 (ADRs, test fixtures, explicit tests)

**Pre-Implementation Readiness:** ⚠ **CONDITIONAL**
- **Specs are sufficient:** ✅ Yes (all features well-defined)
- **Features are testable:** ⚠ Mostly (3 BLOCKER implementation gaps, 5 WARNING testability concerns)
- **Design rationale documented:** ⚠ Partial (6 missing ADRs)
- **Implementation can proceed:** ⚠ Yes, but blockers (TC-300, TC-480, TC-590) must be addressed first

**Recommendation:** Address 3 BLOCKER implementation gaps before full implementation. Testability warnings can be addressed in parallel. Documentation gaps are lower priority.
