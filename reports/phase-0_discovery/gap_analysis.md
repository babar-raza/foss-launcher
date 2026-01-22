# Phase 0: Gap Analysis

**Date**: 2026-01-22
**Phase**: Discovery & Gap Report
**Purpose**: Identify gaps, contradictions, ambiguities, and "agent will guess here" hotspots

---

## Critical Gaps (Immediate Action Required)

### GAP-001: Missing Spec Files Referenced in Traceability
**Location**: [plans/traceability_matrix.md](../../plans/traceability_matrix.md)
**Issue**: Traceability matrix references spec files that may not exist or may have incomplete content:
- References to "specs/31_hugo_config_awareness.md" - EXISTS ✓
- References to "specs/04_claims_compiler_truth_lock.md" - EXISTS ✓
- References to "specs/09_validation_gates.md" - EXISTS ✓
- References to "specs/10_determinism_and_caching.md" - EXISTS ✓
- References to "specs/11_state_and_events.md" - EXISTS ✓
**Impact**: Medium (all referenced specs exist, but need content verification)
**Action**: Verify all referenced specs have complete content covering what traceability claims

### GAP-002: Taskcard Status Not Tracked
**Location**: All taskcards in [plans/taskcards/](../../plans/taskcards/)
**Issue**: No metadata indicating whether taskcards are Draft or Ready for implementation
**Impact**: High - agents cannot determine which taskcards are implementation-ready
**Agent Guessing Risk**: HIGH - agent might implement incomplete taskcards
**Action**: Add status field to all taskcards (Draft/Ready/In-Progress/Complete)

### GAP-003: Missing Implementation Evidence Standards
**Location**: Taskcards
**Issue**: While [plans/taskcards/00_TASKCARD_CONTRACT.md](../../plans/taskcards/00_TASKCARD_CONTRACT.md) requires evidence, there's no standard for:
- Minimum acceptable test coverage
- What constitutes "meaningful" tests
- When mocks are acceptable vs real integration tests
**Impact**: Medium - agents may write insufficient tests
**Agent Guessing Risk**: MEDIUM - agents will guess at test sufficiency
**Action**: Add explicit test coverage requirements to taskcard contract

### GAP-004: Incomplete Acceptance Criteria in Some Taskcards
**Location**: Various taskcards
**Issue**: Some taskcards have detailed acceptance checks, others have minimal or vague checks
**Examples**:
- TC-100: Has clear checkboxes ✓
- TC-401: Has clear checkboxes ✓
- Some epic taskcards (TC-400, TC-410, TC-420): May have less granular checks
**Impact**: Medium - inconsistent implementation quality
**Agent Guessing Risk**: MEDIUM - agents will interpret vague criteria differently
**Action**: Standardize acceptance criteria format across all taskcards

### GAP-005: Missing Error Code Catalog
**Location**: [specs/01_system_contract.md](../../specs/01_system_contract.md#L86)
**Issue**: Spec requires "stable error_code" mapping but no catalog exists defining:
- What error codes exist
- What each error code means
- When each should be used
**Impact**: High - different agents will invent different error codes
**Agent Guessing Risk**: HIGH - leads to inconsistent error handling
**Action**: Create `specs/schemas/error_codes.catalog.yaml` or similar

---

## Ambiguities (Clarification Required)

### AMB-001: "Minimal scaffold" vs "Full implementation" Boundary Unclear
**Location**: [README.md](../../README.md)
**Issue**: README states scaffold implements "only" certain features, but boundary between scaffold and agent-implemented features is not crisp
**Impact**: Low-Medium - agents may duplicate scaffold code or skip implementation
**Agent Guessing Risk**: MEDIUM
**Action**: Add explicit section in README listing "Implemented Features" vs "Agent-Implemented Features"

### AMB-002: Lockfile Strategy Decision Point Not Clear
**Location**: `specs/29_project_repo_structure.md:58`
**Issue**: Spec says "uv (preferred) or Poetry" but doesn't specify decision criteria or who decides
**Impact**: Low - orchestrator must decide, but criteria unclear
**Agent Guessing Risk**: LOW (limited scope)
**Action**: Document decision criteria in DECISIONS.md or spec

### AMB-003: "Best effort" vs "Required" Ambiguity
**Location**: Multiple specs (e.g., [specs/02_repo_ingestion.md](../../specs/02_repo_ingestion.md))
**Issue**: Terms like "best effort", "SHOULD", "MAY" used inconsistently
**Examples**:
- "test_roots SHOULD include..." (line 110) - is this required or optional?
- "recommended_test_commands" (line 24) - is omission acceptable?
**Impact**: Medium - unclear what constitutes conformant implementation
**Agent Guessing Risk**: MEDIUM - agents will interpret requirements differently
**Action**: Create RFC 2119 compliance section in specs/README.md clarifying MUST/SHOULD/MAY

### AMB-004: Adapter Selection Algorithm Not Specified
**Location**: `specs/02_repo_ingestion.md:163`
**Issue**: Spec says "select an adapter based on:" but doesn't specify algorithm:
- Priority order when multiple signals match?
- Tie-breaking rules?
- Fallback adapter?
**Impact**: High - critical for universal repo handling
**Agent Guessing Risk**: HIGH - different implementations will select different adapters
**Action**: Add explicit adapter selection algorithm to spec or create separate spec section

### AMB-005: Validation Profile Transition Rules Unclear
**Location**: [specs/09_validation_gates.md](../../specs/09_validation_gates.md)
**Issue**: Specs mention profiles (local/ci/prod) but don't specify:
- When to use which profile
- Whether profile can change mid-run
- Whether profile is in run_config or runtime arg
**Impact**: Medium
**Agent Guessing Risk**: MEDIUM
**Action**: Add profile selection rules to validation gates spec

### AMB-006: "Minimal" vs "Standard" vs "Rich" Launch Tier Thresholds
**Location**: [specs/06_page_planning.md](../../specs/06_page_planning.md)
**Issue**: Spec mentions launch tiers but criteria for tier selection may need more precision:
- Exact quality signals that trigger tier upgrades
- Can tier be manually overridden in run_config?
**Impact**: Medium - affects content quality and scope
**Agent Guessing Risk**: MEDIUM
**Action**: Verify page_planning spec has explicit tier selection logic

---

## Contradictions (Resolve Immediately)

### CON-001: Traceability Matrix Location Duplication
**Location**: [TRACEABILITY_MATRIX.md](../../TRACEABILITY_MATRIX.md) (root) vs [plans/traceability_matrix.md](../../plans/traceability_matrix.md)
**Issue**: Two traceability matrices with different scopes:
- Root: High-level requirement → spec → plan
- Plans: Detailed spec → taskcard mapping
**Impact**: Low - not truly contradictory, but could confuse
**Resolution**: Root TRACEABILITY_MATRIX.md explicitly references plans/traceability_matrix.md and clarifies scopes (ALREADY DONE in creation)
**Status**: RESOLVED ✓

### CON-002: Temperature Default Inconsistency (Potential)
**Location**: `specs/01_system_contract.md:39` and [specs/15_llm_providers.md](../../specs/15_llm_providers.md)
**Issue**: Need to verify both specs agree on temperature default = 0.0
**Impact**: High if contradiction exists - affects determinism
**Action**: Verify consistency and add cross-reference if needed

### CON-003: No Contradictions Found in Structural Organization
**Status**: ✓ Documentation structure is internally consistent

---

## "Agent Will Guess Here" Hotspots

### GUESS-001: Worker Handoff Protocol Details
**Location**: [specs/28_coordination_and_handoffs.md](../../specs/28_coordination_and_handoffs.md)
**Issue**: While spec exists, need to verify it specifies:
- Exact artifact names each worker reads/writes
- Order guarantees (W1 before W2 before W3...)
- What to do when upstream worker fails
**Risk**: Agents might implement ad-hoc handoff protocols
**Action**: Verify spec completeness, add explicit handoff contract matrix if missing

### GUESS-002: Retry and Backoff Parameters Not Specified
**Location**: Multiple specs mention retry/backoff but no central params
**Issue**: Specs mention retry but don't specify:
- Max retry attempts for each operation type
- Backoff algorithm (exponential? linear?)
- Backoff base and max values
**Affected Areas**:
- Telemetry API transport (`specs/01_system_contract.md:100`)
- External service calls (commit service, LLM API)
**Risk**: Each agent will invent different retry logic
**Action**: Create retry policy spec or add section to relevant specs

### GUESS-003: Snapshot Write Frequency Not Specified
**Location**: [specs/11_state_and_events.md](../../specs/11_state_and_events.md)
**Issue**: Spec requires snapshot.json but doesn't specify:
- Write on every state transition?
- Periodic interval?
- Atomic write protocol details
**Risk**: Performance issues if written too often, recovery issues if too infrequent
**Action**: Add snapshot write policy to state management spec

### GUESS-004: Telemetry Payload Size Limits Not Specified
**Location**: [specs/16_local_telemetry_api.md](../../specs/16_local_telemetry_api.md)
**Issue**: No guidance on:
- Max event payload size
- Truncation strategy for large outputs
- Batching strategy
**Risk**: Agents might send unbounded payloads causing API failures
**Action**: Add payload limits and truncation rules to telemetry spec

### GUESS-005: Frontmatter Key Naming Conventions
**Location**: Template files
**Issue**: While templates exist, unclear if there's a naming convention for:
- Custom frontmatter keys (camelCase? snake_case? kebab-case?)
- Reserved key prefixes
- Validation of custom keys
**Risk**: Inconsistent frontmatter across generated files
**Action**: Verify frontmatter contract schema and add naming convention if missing

### GUESS-006: Patch Conflict Resolution Strategy
**Location**: `specs/08_patch_engine.md:31`
**Issue**: Spec says "record issue, move to FIXING, generate new patch" but doesn't specify:
- How many attempts before giving up?
- Should agent try different patch strategy or same patch with adjusted selector?
- Manual intervention protocol
**Risk**: Infinite fix loops or premature failures
**Action**: Add explicit conflict resolution retry policy with max attempts

### GUESS-007: Claim ID Generation Algorithm Not Specified
**Location**: [specs/04_claims_compiler_truth_lock.md](../../specs/04_claims_compiler_truth_lock.md)
**Issue**: Spec requires "stable claim_id" but algorithm may not be specified:
- Hash of what exactly?
- Collision handling?
- Claim ID format/structure
**Risk**: Non-deterministic claim IDs breaking truth lock
**Action**: Verify claim ID algorithm is fully specified

### GUESS-008: Hugo Build Timeout Not Specified
**Location**: [specs/09_validation_gates.md](../../specs/09_validation_gates.md)
**Issue**: Hugo build is a gate but timeout not specified:
- Local mode timeout?
- CI mode timeout?
- Fail fast on timeout or retry?
**Risk**: Builds hang indefinitely or fail prematurely
**Action**: Add timeout values to validation gates spec or toolchain spec

### GUESS-009: Snippet Length Limits Not Specified
**Location**: [specs/05_example_curation.md](../../specs/05_example_curation.md)
**Issue**: No guidance on:
- Max snippet length (lines or characters)?
- Truncation strategy for large examples
- Multi-file snippet handling
**Risk**: Generated content with huge code blocks or inconsistent curation
**Action**: Add snippet size limits and normalization rules to curation spec

### GUESS-010: Emergency Mode Audit Trail Format Not Specified
**Location**: `specs/01_system_contract.md:70`
**Issue**: Spec requires manual edits to be documented but doesn't specify:
- Format of before/after diff record
- Where exactly to record (validation_report? separate artifact?)
- Required metadata (editor, timestamp, rationale)
**Risk**: Insufficient audit trail for compliance
**Action**: Add emergency mode audit requirements to spec or create schema

---

## Missing Cross-References

### XREF-001: Specs Don't Cross-Reference Related Specs Enough
**Issue**: Many specs reference other specs by name but not all include hyperlinks
**Impact**: Low - doesn't block implementation but reduces navigability
**Action**: Add markdown links between related specs during Phase 1

### XREF-002: Taskcards Don't Reference Related Taskcards
**Issue**: Taskcards list dependencies but often don't link to them
**Impact**: Low - INDEX.md provides navigation
**Action**: Add links in "Dependencies" sections during Phase 2

### XREF-003: Schemas Not Linked from Specs Consistently
**Issue**: Some specs mention schemas by name, others link to schema files
**Impact**: Low - schemas discoverable via folder browse
**Action**: Standardize schema references with links during Phase 1

---

## Documentation Debt (Non-Blocking but Should Address)

### DEBT-001: Some Specs May Lack Failure Modes Section
**Issue**: Not all specs have explicit "Failure modes" or "Error handling" sections
**Impact**: Low - covered in system_contract generally
**Action**: Audit each spec during Phase 1 for failure mode coverage

### DEBT-002: Pilots Have Notes But No Formal Expected Outputs
**Issue**: Pilot folders have expected_page_plan.json and expected_validation_report.json but unclear if these are:
- Golden files for regression tests?
- Examples for reference?
- Binding expected outputs?
**Impact**: Low - likely reference examples
**Action**: Clarify pilot expected outputs purpose in specs/13_pilots.md

### DEBT-003: No Versioning Strategy for Traceability Matrix
**Issue**: Traceability matrix will evolve but no version tracking
**Impact**: Low - living document
**Action**: Consider adding "Last Updated" date to traceability matrices

### DEBT-004: Report Templates Missing Usage Examples
**Issue**: Templates exist but no filled-out examples
**Impact**: Low - templates are self-documenting
**Action**: Consider adding example filled reports to reports/examples/ folder

---

## Strengths to Preserve

### STRENGTH-001: Explicit Schema Validation
- All artifacts have JSON schemas ✓
- Schemas are versioned ✓
- Unknown keys forbidden ✓

### STRENGTH-002: Clear Binding Language
- "MUST", "binding", "non-negotiable" used consistently ✓
- Scope sections in taskcards ✓

### STRENGTH-003: Micro-Taskcard Decomposition
- W1-W3 broken into granular tasks ✓
- Reduces implementation risk ✓

### STRENGTH-004: Evidence-First Culture
- Truth lock requirement ✓
- Claim markers ✓
- EvidenceMap ✓

### STRENGTH-005: Determinism as First-Class Requirement
- Explicit throughout specs ✓
- Dedicated spec for determinism ✓

---

## Priority Rankings

### P0 - Critical (Must Fix Before Phase 1 Completion)
1. GAP-002: Taskcard status tracking
2. GAP-005: Error code catalog
3. AMB-004: Adapter selection algorithm
4. GUESS-007: Claim ID generation algorithm

### P1 - High (Should Fix During Phase 1-2)
1. GAP-003: Implementation evidence standards
2. GAP-004: Acceptance criteria standardization
3. AMB-003: MUST/SHOULD/MAY clarification
4. AMB-005: Validation profile rules
5. GUESS-001: Worker handoff protocol
6. GUESS-006: Patch conflict resolution
7. GUESS-008: Build timeouts

### P2 - Medium (Address During Phase 2 or Later)
1. AMB-001: Scaffold vs full implementation boundary
2. AMB-002: Lockfile strategy decision
3. AMB-006: Launch tier thresholds verification
4. GUESS-002: Retry/backoff parameters
5. GUESS-004: Telemetry payload limits
6. GUESS-009: Snippet length limits
7. XREF-001/002/003: Cross-reference improvements

### P3 - Low (Nice to Have)
1. GAP-001: Spec content verification
2. DEBT-001/002/003/004: Documentation debt items

---

## Recommendations

1. **Immediate**: Create issue tracker for P0 gaps in OPEN_QUESTIONS.md
2. **Phase 1**: Focus on spec completeness for P0/P1 items
3. **Phase 2**: Harden taskcards and plans for P1/P2 items
4. **Phase 3**: Verify all gaps resolved or documented as acceptable risks

---

## Gap Summary Statistics

- **Critical Gaps**: 5
- **Ambiguities**: 6
- **Contradictions**: 2 (1 resolved, 1 to verify)
- **Guessing Hotspots**: 10
- **Missing Cross-References**: 3
- **Documentation Debt**: 4
- **Total Issues Identified**: 30
- **P0 Issues**: 4
- **P1 Issues**: 8
- **P2 Issues**: 7
- **P3 Issues**: 2
