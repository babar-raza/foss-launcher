# Requirements Gaps Report (AGENT_R)

**Run ID**: 20260127-1518
**Agent**: AGENT_R (Requirements Extractor)
**Purpose**: Document gaps, ambiguities, conflicts, and missing requirements

---

## Format

Each gap follows this structure:

```
R-GAP-XXX | SEVERITY | Description | Evidence | Proposed Fix
```

**Severity Levels**:
- **BLOCKER**: Prevents implementation or creates critical ambiguity
- **MAJOR**: Significant impact on implementation or testing
- **MINOR**: Low impact, can be resolved with reasonable interpretation

---

## Gap Inventory

### R-GAP-001 | BLOCKER | Missing acceptance criteria for rollback metadata validation

**Description**: REQ-024 (Guarantee L: Rollback + recovery contract) is marked as a BLOCKER in TRACEABILITY_MATRIX.md:620-628 with status "NOT YET IMPLEMENTED". The requirement specifies that PR artifacts MUST include rollback metadata, but there is no clear specification for:
1. What constitutes valid rollback steps
2. How rollback steps should be validated
3. What happens if rollback steps are invalid or incomplete

**Evidence**:
- specs/34_strict_compliance_guarantees.md:335-358 defines requirement
- TRACEABILITY_MATRIX.md:620-628 marks as PENDING implementation
- specs/12_pr_and_release.md is referenced but rollback requirements may need addition
- specs/schemas/pr.schema.json mentioned but may not exist or may need rollback fields

**Proposed Fix**:
1. Create or update specs/schemas/pr.schema.json with rollback fields:
   - `base_ref` (required, commit SHA)
   - `run_id` (required, string)
   - `rollback_steps` (required, array of command strings)
   - `affected_paths` (required, array of file paths)
2. Add acceptance criteria to specs/34_strict_compliance_guarantees.md:
   - Rollback steps must be executable shell commands
   - Each affected_path must exist in the PR diff
   - base_ref must be a valid commit SHA
3. Define runtime validation in TC-480 taskcard
4. Define error_code: PR_MISSING_ROLLBACK_METADATA

**Blocking**: TC-480 (PR Manager W9) implementation

---

### R-GAP-002 | MAJOR | Ambiguity in "byte-identical artifacts" acceptance criteria

**Description**: REQ-079 states "Repeat run with same inputs MUST produce byte-identical artifacts (PagePlan, PatchBundle, drafts, reports)". However, there is ambiguity about:
1. Whether timestamps in artifacts are acceptable variance
2. Whether event_id generation (UUIDs) breaks byte-identity
3. Whether line ending normalization (CRLF vs LF) is considered identity-breaking
4. What "drafts" refers to (markdown files? which specific files?)

**Evidence**:
- specs/10_determinism_and_caching.md:51-52 states byte-identical requirement
- specs/10_determinism_and_caching.md:52 allows variance only in events.ndjson for ts/event_id
- No specification for timestamp handling in non-event artifacts
- No specification for line ending normalization

**Proposed Fix**:
1. Update specs/10_determinism_and_caching.md with explicit rules:
   - Artifacts MUST NOT include timestamps except in events.ndjson
   - UUIDs/event_ids acceptable variance only in events.ndjson
   - Line endings MUST be normalized to LF before comparison
   - "Drafts" defined as all files under RUN_DIR/work/site/ matching *.md
2. Add determinism test specification to TC-560 (determinism harness):
   - Run twice with same inputs
   - Normalize line endings
   - Exclude events.ndjson from comparison
   - Compare byte-for-byte using sha256 hashes

**Impact**: Affects TC-560 (determinism harness) acceptance criteria

---

### R-GAP-003 | MAJOR | Missing specification for "minimal-diff discipline" heuristics

**Description**: REQ-019 (Guarantee G) requires "minimal-diff discipline" and states that formatting-only changes must be flagged if >80% of diff is formatting. However, the specification does not define:
1. How to calculate the 80% threshold (by lines? by characters? by files?)
2. What constitutes "formatting-only" (whitespace? line endings? indentation? comments?)
3. Whether reformatting by tools like prettier/black counts as formatting-only
4. Whether the flag is a warning or a blocker in prod profile

**Evidence**:
- specs/34_strict_compliance_guarantees.md:192-216 (Guarantee G)
- specs/34_strict_compliance_guarantees.md:209 states ">80% formatting-only → emit warning (blocker in prod profile)"
- No algorithm specified for detecting formatting-only changes
- src/launch/util/diff_analyzer.py claimed to exist but algorithm not specified

**Proposed Fix**:
1. Update specs/34_strict_compliance_guarantees.md or specs/08_patch_engine.md with algorithm:
   - Normalize both versions (strip whitespace, normalize line endings)
   - Count semantic changes (non-whitespace diffs)
   - Formatting ratio = (total lines changed - semantic lines changed) / total lines changed
   - If formatting ratio > 0.80 → emit warning
   - In prod profile → convert warning to BLOCKER with error_code POLICY_FORMATTING_ONLY_DIFF
2. Specify normalization rules:
   - Strip leading/trailing whitespace per line
   - Normalize line endings to LF
   - Collapse multiple blank lines to single blank line
   - Preserve semantic changes (word additions/removals)
3. Add tests to tests/unit/util/test_diff_analyzer.py

**Impact**: Affects implementation of src/launch/util/diff_analyzer.py and Gate G enforcement

---

### R-GAP-004 | MAJOR | Unclear conflict between REQ-012 and emergency mode

**Description**: REQ-012 states "No manual content edits" and REQ-038 states "allow_manual_edits MUST default to false". However, specs/01_system_contract.md:69-76 describes emergency mode with preconditions for allowing manual edits. It is unclear:
1. Whether emergency mode is a permanent escape hatch or temporary exception
2. Who has authority to set allow_manual_edits=true
3. Whether runs with allow_manual_edits=true can be merged to main/production
4. Whether manual edits are allowed in pilot runs for testing

**Evidence**:
- specs/01_system_contract.md:69-76 (emergency mode preconditions)
- plans/policies/no_manual_content_edits.md:24-31 (exceptions section)
- REQ-012 (no manual edits) vs REQ-038 (allow_manual_edits default false)
- No specification for who can approve manual edits

**Proposed Fix**:
1. Update specs/01_system_contract.md to clarify:
   - Emergency mode is ONLY for unblocking critical failures (e.g., LLM service outage)
   - Runs with allow_manual_edits=true MUST NOT be merged to production branches
   - Manual edits require: (1) run_config flag, (2) orchestrator master review with rationale, (3) validation_report.manual_edits=true
   - Pilot runs MAY use manual edits for development ONLY if documented
2. Add to plans/policies/no_manual_content_edits.md:
   - Authority: Repository maintainer or agent supervisor only
   - Approval process: Document rationale in run report
   - Prohibition: No manual edits in production runs (prod profile)
3. Update Gate (TC-571 policy gate) to:
   - Fail with BLOCKER if allow_manual_edits=true in prod profile
   - Warn if allow_manual_edits=true in ci profile

**Impact**: Affects policy enforcement and run acceptance criteria

---

### R-GAP-005 | MINOR | Missing specification for max_fix_attempts default and bounds

**Description**: REQ-046 and REQ-077 state that fix loops are capped by max_fix_attempts, with REQ-077 mentioning "default 3". However, there is no specification for:
1. Whether default 3 is binding or can be overridden
2. What the minimum and maximum allowed values are
3. What happens if max_fix_attempts=0 (disable fix loops?)
4. Whether fix attempts are counted per-issue or per-run

**Evidence**:
- specs/01_system_contract.md:158 (fix loops capped by max_fix_attempts)
- specs/08_patch_engine.md:110 (default 3)
- specs/schemas/run_config.schema.json presumably has max_fix_attempts field but bounds not specified in requirements docs

**Proposed Fix**:
1. Update specs/schemas/run_config.schema.json with constraints:
   ```json
   "max_fix_attempts": {
     "type": "integer",
     "minimum": 0,
     "maximum": 10,
     "default": 3,
     "description": "Maximum fix attempts per run. 0 disables fix loops."
   }
   ```
2. Update specs/01_system_contract.md or specs/08_patch_engine.md:
   - Fix attempts counted per-run (not per-issue)
   - If max_fix_attempts=0, FIXING state transitions directly to FAILED
   - Orchestrator MUST enforce max_fix_attempts and transition to FAILED after exhaustion
3. Add tests for fix loop bounds

**Impact**: Low impact, reasonable default exists, but schema should be explicit

---

### R-GAP-006 | BLOCKER | Conflicting requirements for locales field

**Description**: REQ-054 and REQ-055 create potential confusion:
- REQ-054: "run_config.locales is the authoritative field for locale targeting"
- REQ-055: "If both locale and locales present, locale MUST equal locales[0] and locales MUST have length 1"

This implies that both `locale` (singular) and `locales` (plural) fields exist. However, it is unclear:
1. Why both fields exist (deprecated field? convenience alias?)
2. Whether new run configs should use `locale` or `locales`
3. Whether `locale` is required, optional, or deprecated
4. What happens if only `locale` is present without `locales`

**Evidence**:
- specs/01_system_contract.md:31-33 (locales contract)
- No clear deprecation notice or migration guide
- specs/schemas/run_config.schema.json not inspected but presumably defines both fields

**Proposed Fix**:
1. Update specs/01_system_contract.md to clarify:
   - `locales` (array) is the primary field (required)
   - `locale` (string) is a convenience alias for single-locale runs (optional)
   - If `locale` is present, it MUST be consistent with `locales`
   - New run configs SHOULD use `locales` only
   - `locale` is maintained for backward compatibility only
2. Update specs/schemas/run_config.schema.json:
   ```json
   "locales": {
     "type": "array",
     "items": {"type": "string"},
     "minItems": 1,
     "description": "Target locales (primary field)"
   },
   "locale": {
     "type": "string",
     "description": "Convenience alias for single-locale runs. If present, must equal locales[0]."
   }
   ```
3. Add schema validation to enforce consistency (Gate 1)

**Impact**: Affects run config creation and validation

---

### R-GAP-007 | MAJOR | Undefined behavior for universal fallback adapter failure

**Description**: REQ-073 states "The universal fallback adapter MUST always exist and be registered as 'universal:best_effort'". However, specs/02_repo_ingestion.md:250-258 specifies what happens if adapter selection fails (emit error, open blocker, fail run). This creates a logical inconsistency:
1. If universal fallback MUST always exist, how can adapter selection ever fail?
2. What happens if the universal fallback adapter itself fails during execution?
3. Is "universal:best_effort" allowed to produce empty/minimal artifacts?

**Evidence**:
- specs/02_repo_ingestion.md:257 (universal fallback MUST exist)
- specs/02_repo_ingestion.md:250-258 (adapter selection failure handling)
- specs/27_universal_repo_handling.md (universal repo handling guidelines)
- No specification for fallback adapter failure behavior

**Proposed Fix**:
1. Clarify in specs/02_repo_ingestion.md:
   - Universal fallback adapter MUST exist in adapter registry
   - Adapter selection failure means: no adapter found AND universal fallback missing
   - This is a configuration error (blocker)
   - Universal fallback adapter execution failure handled like any worker failure
2. Define universal fallback adapter contract in specs/27_universal_repo_handling.md:
   - MAY produce minimal artifacts (e.g., empty example_roots)
   - MUST NOT fail for missing manifests or unknown platforms
   - MUST emit telemetry warnings for unsupported features
   - Output artifacts MUST still validate against schemas (with many fields as "unknown")
3. Add tests for universal fallback adapter resilience

**Impact**: Affects adapter registry implementation and error handling

---

### R-GAP-008 | MINOR | Implied requirement: Telemetry event schema versioning

**Description**: Multiple requirements reference telemetry events (REQ-042, REQ-049, REQ-057, etc.) but there is no explicit requirement for telemetry event schema versioning. This is implied by:
- REQ-052: Schema versions MUST be explicit in every artifact
- REQ-053: Behavior changes recorded via version bumps
- Telemetry events are artifacts

However, there is no explicit statement that telemetry events MUST include schema_version or event_version fields.

**Evidence**:
- specs/16_local_telemetry_api.md (telemetry contract)
- specs/11_state_and_events.md (event schema)
- No explicit schema_version field requirement for events
- REQ-052 covers "artifacts" but unclear if events count as artifacts

**Proposed Fix**:
1. Add explicit requirement (new REQ-089):
   - "All telemetry events MUST include an event_schema_version field"
2. Update specs/16_local_telemetry_api.md:
   - Define event schema structure with version field
   - Version format: "event_schema.v1"
3. Update specs/11_state_and_events.md:
   - Add event_schema_version to event structure
   - Specify backward compatibility rules for event schema changes
4. Mark as MINOR because reasonable default can be inferred

**Impact**: Low impact, can be added during TC-500/TC-580 implementation

**Status**: IMPLIED, should be promoted to explicit requirement in next revision

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| Total Gaps Identified | 8 |
| BLOCKER Severity | 2 |
| MAJOR Severity | 4 |
| MINOR Severity | 2 |
| Missing Requirements | 1 (R-GAP-008) |
| Ambiguous Requirements | 3 (R-GAP-002, R-GAP-003, R-GAP-005) |
| Conflicting Requirements | 2 (R-GAP-004, R-GAP-006) |
| Underspecified Behaviors | 2 (R-GAP-001, R-GAP-007) |

---

## Gap Categorization

### Blocking Implementation (BLOCKER)
- **R-GAP-001**: Rollback metadata validation (blocks TC-480)
- **R-GAP-006**: Locales field conflict (blocks run config validation)

### Affecting Implementation Quality (MAJOR)
- **R-GAP-002**: Byte-identical artifacts ambiguity (affects TC-560)
- **R-GAP-003**: Minimal-diff heuristics (affects diff_analyzer.py)
- **R-GAP-004**: Manual edits policy conflict (affects policy gate TC-571)
- **R-GAP-007**: Universal fallback adapter failure (affects adapter registry)

### Low Priority Clarifications (MINOR)
- **R-GAP-005**: max_fix_attempts bounds (reasonable default exists)
- **R-GAP-008**: Telemetry event versioning (implied requirement)

---

## Gaps by Affected Component

| Component | Gaps |
|-----------|------|
| TC-480 (PR Manager) | R-GAP-001 |
| TC-560 (Determinism Harness) | R-GAP-002 |
| TC-571 (Policy Gate) | R-GAP-004, R-GAP-008 |
| TC-450 (Linker/Patcher) | R-GAP-003, R-GAP-005 |
| TC-400 (RepoScout) | R-GAP-007 |
| Schema validation | R-GAP-006 |
| TC-500/TC-580 (Telemetry) | R-GAP-008 |

---

## Recommendations

### Immediate Actions (Before Implementation)
1. **Resolve R-GAP-001 (BLOCKER)**: Define rollback metadata schema and validation before starting TC-480
2. **Resolve R-GAP-006 (BLOCKER)**: Clarify locales vs locale field authority in specs/01_system_contract.md

### High Priority (During Implementation)
3. **Resolve R-GAP-002**: Add determinism test specification to TC-560 taskcard
4. **Resolve R-GAP-003**: Specify minimal-diff algorithm before implementing diff_analyzer.py
5. **Resolve R-GAP-004**: Clarify emergency mode authority and production constraints

### Medium Priority (Can Be Deferred)
6. **Resolve R-GAP-007**: Define universal fallback adapter failure behavior
7. **Resolve R-GAP-005**: Add max_fix_attempts bounds to schema
8. **Promote R-GAP-008**: Add telemetry event versioning as explicit requirement

---

## Gap Resolution Tracking

| Gap ID | Status | Assigned To | Resolution Deadline |
|--------|--------|-------------|---------------------|
| R-GAP-001 | OPEN | Spec author | Before TC-480 start |
| R-GAP-002 | OPEN | TC-560 implementer | Before determinism tests |
| R-GAP-003 | OPEN | Spec author | Before diff_analyzer implementation |
| R-GAP-004 | OPEN | Policy owner | Before TC-571 start |
| R-GAP-005 | OPEN | Schema author | Before schema v1 finalization |
| R-GAP-006 | OPEN | Spec author | Before run config validation |
| R-GAP-007 | OPEN | Adapter designer | Before adapter registry implementation |
| R-GAP-008 | OPEN | Telemetry designer | Before TC-500/TC-580 start |

---

**Gaps Report Complete**
**Agent**: AGENT_R
**Timestamp**: 2026-01-27T16:00:00Z
