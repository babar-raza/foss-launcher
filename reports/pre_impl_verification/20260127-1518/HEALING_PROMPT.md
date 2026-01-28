# Healing Prompt: Pre-Implementation Gap Resolution

**Pre-Implementation Verification Run**: 20260127-1518
**Date**: 2026-01-27
**Purpose**: Ordered, actionable instructions to fix all identified gaps

---

## IMPORTANT: Scope Restrictions

**ALLOWED EDITS**:
- Documentation files (*.md)
- JSON schemas (specs/schemas/*.json)
- Validation gates (tools/validate_*.py)
- Plans and taskcards (plans/**, plans/taskcards/**)

**FORBIDDEN EDITS**:
- NO runtime feature code (src/launch/**, except validators/cli.py for gates)
- NO test files (tests/**)
- NO build configuration (Makefile, pyproject.toml, uv.lock)
- NO CI workflows (.github/workflows/**)

**Rationale**: This is PRE-IMPLEMENTATION verification. Runtime features, tests, and infrastructure are implementation work, not pre-implementation healing.

---

## Execution Order

Gaps are ordered by dependency chain. Execute in this exact order.

---

## PHASE 1: Documentation & Specification Clarification (12 gaps)

### HEAL-001: Add Worker Contracts to Traceability Matrix

**Gap**: GAP-010 (MINOR)
**File**: `plans/traceability_matrix.md`
**Location**: Add new section after line 97 (after "Frameworks and Dependencies")

**Action**:
1. Insert new section heading: `## Worker Contracts`
2. Add entry:
```markdown
## Worker Contracts

- `specs/21_worker_contracts.md`
  - **Purpose**: Defines input/output contracts for all 9 workers (W1-W9)
  - **Implement**: TC-400 (W1 RepoScout), TC-410 (W2 FactsBuilder), TC-420 (W3 SnippetCurator), TC-430 (W4 IAPlanner), TC-440 (W5 SectionWriter), TC-450 (W6 Linker/Patcher), TC-460 (W7 Validator), TC-470 (W8 Fixer), TC-480 (W9 PRManager)
  - **Validate**: TC-522 (CLI E2E), TC-523 (MCP E2E)
  - **Status**: ✅ Spec complete, each worker taskcard implements its contract
```

**Acceptance**: Section added, no syntax errors in markdown

---

### HEAL-002: Add State Management Specs to Traceability Matrix

**Gap**: GAP-011 (MINOR)
**File**: `plans/traceability_matrix.md`
**Location**: Add under "Core Contracts" section (after specs/11_state_and_events.md entry)

**Action**:
1. Insert two entries:
```markdown
- `specs/state-graph.md`
  - **Purpose**: Defines LangGraph state machine transitions for orchestrator
  - **Implement**: TC-300 (Orchestrator graph definition, node transitions, edge conditions)
  - **Validate**: TC-300 (graph smoke tests, transition determinism tests)
  - **Status**: Spec complete, TC-300 not started

- `specs/state-management.md`
  - **Purpose**: Defines state persistence, snapshot updates, event log structure
  - **Implement**: TC-300 (state serialization, snapshot creation, event sourcing)
  - **Validate**: TC-300 (determinism tests for state serialization)
  - **Status**: Spec complete, TC-300 not started
```

**Acceptance**: Entries added under "Core Contracts", no syntax errors

---

### HEAL-003: Add Navigation Spec to Traceability Matrix

**Gap**: GAP-012 (MINOR)
**File**: `plans/traceability_matrix.md`
**Location**: Add new section after "Public URL Mapping" or under "Patch Engine and Safety"

**Action**:
1. Insert entry:
```markdown
- `specs/22_navigation_and_existing_content_update.md`
  - **Purpose**: Defines navigation planning and existing content update strategies
  - **Implement**: TC-430 (navigation planning), TC-450 (content linking and updates)
  - **Validate**: TC-460 (link validation gate)
  - **Status**: Spec complete, implementation coverage via TC-430 and TC-450
```

**Acceptance**: Entry added, no syntax errors

---

### HEAL-004: Add Coordination Spec to Traceability Matrix

**Gap**: GAP-039 (MINOR)
**File**: `plans/traceability_matrix.md`
**Location**: Add under "Core Contracts" or "Orchestrator" section

**Action**:
1. Insert entry:
```markdown
- `specs/28_coordination_and_handoffs.md`
  - **Purpose**: Defines orchestrator-to-worker handoff contracts and coordination patterns
  - **Implement**: TC-300 (worker orchestration, handoff logic, state transitions)
  - **Validate**: TC-300 (orchestrator integration tests)
  - **Status**: Spec complete, TC-300 not started
```

**Acceptance**: Entry added, no syntax errors

---

### HEAL-005: Clarify Byte-Identical Acceptance Criteria

**Gap**: GAP-009 (MAJOR)
**File**: `specs/10_determinism_and_caching.md`
**Location**: After line 51 (after "Repeat run with same inputs MUST produce byte-identical artifacts")

**Action**:
1. Insert new subsection at line 52:
```markdown

### Byte-Identical Acceptance Criteria (REQ-079)

**Artifacts Subject to Byte-Identity Requirement**:
- `page_plan.json`
- `patch_bundle.json`
- All `*.md` files under `RUN_DIR/work/site/` (drafts)
- All `*.json` files under `RUN_DIR/artifacts/` except `events.ndjson`

**Allowed Variance**:
- `events.ndjson`: Timestamps (`ts` field) and event IDs (`event_id` field) may vary
- All other artifacts: **NO variance allowed**

**Clarifications**:
1. **Timestamps**: Artifacts MUST NOT include timestamps except in `events.ndjson`
2. **UUIDs**: UUID/event_id generation acceptable variance ONLY in `events.ndjson`
3. **Line Endings**: Line endings MUST be normalized to LF (`\n`) before byte comparison
4. **Whitespace**: Trailing whitespace MUST be stripped before comparison

**Determinism Harness Validation (TC-560)**:
1. Run pipeline twice with identical inputs
2. Normalize line endings to LF for all artifacts
3. Strip trailing whitespace from all text files
4. Exclude `events.ndjson` from comparison
5. Compare all other artifacts byte-for-byte using sha256 hashes
6. Test passes if all hashes match
```

**Acceptance**: Subsection added after line 51, all 4 clarifications present

---

### HEAL-006: Document Threshold Rationale (ADRs)

**Gap**: GAP-005 (MAJOR)
**File**: Create new file `specs/adr/001_inference_confidence_threshold.md`

**Action**:
1. Create `specs/adr/` directory if not exists
2. Create file `specs/adr/001_inference_confidence_threshold.md`:
```markdown
# ADR-001: MCP Inference Confidence Threshold (80%)

**Status**: Proposed (requires pilot validation)
**Date**: 2026-01-27
**Context**: Pre-implementation decision for specs/24_mcp_tool_schemas.md:227-231

## Decision

The `launch_start_run_from_github_repo_url` MCP tool uses an 80% confidence threshold for automatic inference of `product_slug` and `target_platform`.

## Rationale

- **Conservative threshold**: Reduces risk of incorrect inference leading to wrong site generation
- **Trade-off**: Prefers asking user for clarification (ambiguous response) over proceeding with low-confidence inference
- **Alternatives considered**:
  - 90%: Too strict, would reject many valid repos with minor ambiguity
  - 70%: Too permissive, higher risk of incorrect inference
  - 80%: Balanced middle ground

## Validation Plan

- Pilot phase (TC-520): Test with 20+ representative repos
- Measure: False positive rate (incorrect inference) and false negative rate (unnecessary ambiguity)
- Target: <5% false positive rate
- Tuning: If false positive rate >5%, increase threshold to 85% or 90%

## Consequences

- May require manual clarification for repos with ambiguous signals (e.g., multi-product repos)
- Threshold may be overridden via optional `confidence_threshold` parameter in future versions
```

3. Create file `specs/adr/002_gate_timeout_values.md`:
```markdown
# ADR-002: Validation Gate Timeout Values

**Status**: Proposed (requires load testing)
**Date**: 2026-01-27
**Context**: Pre-implementation decision for specs/09_validation_gates.md:84-120

## Decision

Profile-based gate timeout values:
- **local**: 30 seconds
- **ci**: 60 seconds
- **prod**: 120 seconds

## Rationale

- **Local profile**: Fast feedback for developers, short timeout acceptable (code changes expected)
- **CI profile**: Medium timeout for CI runners with variable performance
- **Prod profile**: Long timeout for complex sites with thousands of pages

**Alternatives considered**:
- Uniform timeout (60s): Rejected, too slow for local, too fast for prod
- Per-gate timeouts: Rejected for complexity, profile-based is simpler

## Validation Plan

- Load testing (TC-560): Test with sites of varying sizes (10 pages, 100 pages, 1000 pages)
- Measure: 95th percentile gate execution time
- Target: 95th percentile < 50% of timeout value (safety margin)
- Tuning: If 95th percentile exceeds 50% of timeout, increase timeout values

## Consequences

- Gates may timeout on very large sites in local profile (acceptable trade-off for fast feedback)
- Gates may be slower than necessary in prod profile (acceptable for safety)
```

4. Create file `specs/adr/003_contradiction_priority_difference_threshold.md`:
```markdown
# ADR-003: Contradiction Resolution Priority Difference Threshold (≥2)

**Status**: Proposed
**Date**: 2026-01-27
**Context**: Pre-implementation decision for specs/03_product_facts_and_evidence.md:138-146

## Decision

Contradictions are auto-resolved when priority difference ≥ 2. Priority difference of 1 requires manual review.

## Rationale

- **Evidence priority hierarchy**: Priority 1 (Manifests) > Priority 2 (Code) > ... > Priority 7 (README)
- **Threshold rationale**: Priority difference of 2 means evidence sources are 2+ levels apart (e.g., Manifest vs. Docs), suggesting clear quality difference
- **Manual review for priority_diff == 1**: Adjacent priorities (e.g., Code vs. Tests) may have similar reliability, worth manual review

**Example**:
- Manifest (priority 1) contradicts README (priority 7): priority_diff = 6 → auto-resolve (use Manifest)
- Code (priority 2) contradicts Tests (priority 3): priority_diff = 1 → manual review

## Alternatives Considered

- Threshold ≥ 1: Too aggressive, would auto-resolve close priority differences
- Threshold ≥ 3: Too conservative, would require manual review too often

## Validation Plan

- Pilot phase (TC-520): Review all manual review cases to verify threshold appropriateness
- If >20% of manual reviews are "obvious" (one source clearly better), reduce threshold to ≥1
- If <5% of auto-resolutions are incorrect, threshold is appropriate

## Consequences

- Some contradictions require manual review (acceptable for quality)
- Threshold may be tuned based on pilot data
```

**Acceptance**: All 3 ADR files created in `specs/adr/`, no syntax errors

---

### HEAL-007: Add Minimal-Diff Heuristic Algorithm

**Gap**: GAP-013 (MINOR)
**File**: `specs/34_strict_compliance_guarantees.md`
**Location**: After line 209 (after ">80% formatting-only → emit warning (blocker in prod profile)")

**Action**:
1. Insert new subsection at line 210:
```markdown

#### Formatting-Only Detection Algorithm

**Purpose**: Detect when >80% of diff is formatting-only (Guarantee G enforcement)

**Algorithm** (implemented in `src/launch/util/diff_analyzer.py`):

1. **Normalize whitespace** for both old and new content:
   - Strip leading/trailing whitespace from each line
   - Collapse multiple spaces to single space
   - Normalize line endings to LF

2. **Compare semantic content**:
   - If normalized contents are identical → 100% formatting-only
   - If normalized contents differ → calculate formatting percentage

3. **Calculate formatting percentage**:
   ```
   total_lines_changed = lines_added + lines_removed
   formatting_lines = lines where normalized content matches but original differs
   formatting_percentage = (formatting_lines / total_lines_changed) * 100
   ```

4. **Threshold enforcement**:
   - If `formatting_percentage > 80%`:
     - Emit warning: "Diff is {formatting_percentage}% formatting-only"
     - In prod profile: Emit BLOCKER issue with error_code: POLICY_FORMATTING_ONLY_DIFF
     - In local/ci profiles: Emit WARN issue

**Edge Cases**:
- Empty diffs (no changes): Not considered formatting-only, no warning
- Comment-only changes: Treated as semantic changes (not formatting)
- Docstring changes: Treated as semantic changes (not formatting)

**Measurement Unit**: By lines (not by characters or by files)
```

**Acceptance**: Subsection added after line 209, algorithm steps present

---

### HEAL-008: Document Error Code Registry Requirement

**Gap**: GAP-006 (MAJOR)
**File**: Create new file `specs/error_code_registry.md`

**Action**:
1. Create file `specs/error_code_registry.md`:
```markdown
# Error Code Registry

**Purpose**: Canonical registry of all error codes used across foss-launcher

**Authority**: specs/01_system_contract.md:92-136 defines error taxonomy

---

## Error Code Format

Pattern: `{COMPONENT}_{ERROR_TYPE}_{SPECIFIC}`

Example: `REPO_FLOATING_REF_DETECTED`

---

## Error Code Catalog

*(To be populated during implementation)*

### Policy Errors (POLICY_*)

| Error Code | Component | Description | Severity | Source |
|------------|-----------|-------------|----------|--------|
| POLICY_PATH_ESCAPE | path_validation | Path escapes allowed boundary | BLOCKER | src/launch/util/path_validation.py:72 |
| POLICY_PATH_TRAVERSAL | path_validation | Path contains traversal attempt | BLOCKER | src/launch/util/path_validation.py:159 |
| POLICY_PATH_SUSPICIOUS | path_validation | Path contains suspicious patterns | BLOCKER | src/launch/util/path_validation.py:168 |
| POLICY_PATH_NOT_ALLOWED | path_validation | Path not in allowed_paths | BLOCKER | src/launch/util/path_validation.py:130 |
| POLICY_CHANGE_BUDGET_EXCEEDED | diff_analyzer | Change budget exceeded | BLOCKER (prod) | src/launch/util/diff_analyzer.py:21 |
| POLICY_NETWORK_UNAUTHORIZED_HOST | http | Host not in allowlist | BLOCKER | src/launch/clients/http.py:24 |
| POLICY_FLOATING_REF_DETECTED | repo_validation | Floating ref detected | BLOCKER | TBD (TC-460) |
| POLICY_FORMATTING_ONLY_DIFF | diff_analyzer | >80% formatting-only changes | BLOCKER (prod) | TBD (TC-300) |

### Budget Errors (BUDGET_*)

| Error Code | Component | Description | Severity | Source |
|------------|-----------|-------------|----------|--------|
| BUDGET_EXCEEDED_LLM_CALLS | budget_tracker | LLM call budget exceeded | BLOCKER | src/launch/util/budget_tracker.py:21 |
| BUDGET_EXCEEDED_FILE_WRITES | budget_tracker | File write budget exceeded | BLOCKER | src/launch/util/budget_tracker.py:21 |
| BUDGET_EXCEEDED_RUNTIME | budget_tracker | Runtime budget exceeded | BLOCKER | src/launch/util/budget_tracker.py:21 |

### Security Errors (SECURITY_*)

| Error Code | Component | Description | Severity | Source |
|------------|-----------|-------------|----------|--------|
| SECURITY_SECRET_LEAKED | secrets_hygiene | Secret detected in commit | BLOCKER | specs/34_strict_compliance_guarantees.md:151 |
| SECURITY_UNTRUSTED_EXECUTION | subprocess | Untrusted code execution attempt | BLOCKER | src/launch/util/subprocess.py:18 |

### Network Errors (NETWORK_*)

| Error Code | Component | Description | Severity | Source |
|------------|-----------|-------------|----------|--------|
| NETWORK_BLOCKED | http | Network request blocked by allowlist | BLOCKER | src/launch/clients/http.py:24 |

### Gate Errors (GATE_*)

| Error Code | Component | Description | Severity | Source |
|------------|-----------|-------------|----------|--------|
| GATE_RUN_LAYOUT_MISSING_PATHS | cli | Required RUN_DIR paths missing | BLOCKER | src/launch/validators/cli.py:125 |
| GATE_TOOLCHAIN_LOCK_FAILED | cli | Toolchain lock validation failed | BLOCKER | src/launch/validators/cli.py:148 |
| GATE_TIMEOUT | validator | Gate execution timed out | BLOCKER | specs/09_validation_gates.md:116-119 |

### PR Errors (PR_*)

| Error Code | Component | Description | Severity | Source |
|------------|-----------|-------------|----------|--------|
| PR_MISSING_ROLLBACK_METADATA | pr_manager | Rollback metadata missing in PR | BLOCKER (prod) | TBD (TC-480) |

---

## Enforcement

**Preflight Gate**: (To be implemented in TC-100 or TC-300)
- Scan all source files for error_code usage
- Validate all error codes present in this registry
- Fail if unregistered error codes found

**Runtime Enforcement**:
- All error codes logged to telemetry (REQ-042)
- Error codes stable across versions (REQ-041)

---

## Updates

When adding new error codes:
1. Add entry to this registry (specs/error_code_registry.md)
2. Use error code in implementation
3. Log to telemetry
4. Add tests for error code path
```

**Acceptance**: File created, structure present, placeholder entries added

---

### HEAL-009: Document Prompt Versioning Requirement

**Gap**: GAP-007 (MAJOR)
**File**: `specs/10_determinism_and_caching.md`
**Location**: Add new subsection after line 52 (after byte-identical criteria)

**Action**:
1. Insert new subsection at line 53:
```markdown

### Prompt Versioning for Determinism

**Requirement**: All LLM-based features MUST version prompts to ensure determinism (REQ-079).

**Implementation**:
1. **Prompt Hash**: Compute sha256 hash of full prompt template (including system message, user message, and all placeholders)
2. **Prompt Version Field**: Include `prompt_version` (hash) in telemetry for every LLM call
3. **Determinism Validation**: TC-560 harness compares prompt versions across runs
   - If prompt_version differs → determinism cannot be guaranteed
   - If prompt_version matches + temperature=0.0 → determinism expected

**Affected Features**:
- FEAT-012 (Product Facts Extraction): LLM-based
- FEAT-034 (Template Rendering): LLM-based drafting
- FEAT-041/042 (Conflict Resolution): LLM-based fixer
- All workers using LLM calls

**Template Versioning Enforcement**:
- `ruleset_version` (from run_config) controls ruleset templates
- `templates_version` (from run_config) controls section templates
- Both must be pinned per run (Guarantee K)
- Prompt templates MUST reference these versions

**Acceptance Criteria** (TC-560):
- Two runs with same inputs produce same `prompt_version` for all LLM calls
- Prompt templates include version placeholders: `{{ruleset_version}}`, `{{templates_version}}`
```

**Acceptance**: Subsection added, prompt_version field documented, template versioning linked

---

### HEAL-010: Add Broken Link Report

**Gap**: GAP-XXX (MINOR, from AGENT_L)
**File**: `reports/pre_impl_verification/20260127-1518/BROKEN_LINKS.md`

**Action**:
1. If AGENT_L identified broken links, create summary report
2. Format:
```markdown
# Broken Links Report

**Run ID**: 20260127-1518
**Source**: AGENT_L
**Date**: 2026-01-27

---

## Summary

**Total Links Checked**: N
**Broken Links**: M
**Severity**: MINOR (all links within specs, plans, or docs)

---

## Broken Links

| File | Line | Link | Target | Issue |
|------|------|------|--------|-------|
| ... | ... | ... | ... | ... |

---

## Recommendations

1. Fix all broken internal links (missing anchors, wrong paths)
2. Update external links to current URLs
3. Remove references to non-existent files
```

**Acceptance**: Report created if broken links exist, otherwise skip this step

---

### HEAL-011: SHA Format Validation in run_config Schema

**Gap**: GAP-015 (MINOR)
**File**: `specs/schemas/run_config.schema.json`
**Location**: All `*_ref` fields

**Action**:
1. Find all fields ending in `_ref` (e.g., `github_ref`, `site_ref`, `base_ref`)
2. For each field, add `"pattern": "^[a-f0-9]{40}$"` constraint
3. Example:
```json
"github_ref": {
  "type": "string",
  "description": "Commit SHA (40-char hex) for product repo",
  "pattern": "^[a-f0-9]{40}$"
}
```

**Affected Fields** (search for `_ref`):
- `github_ref`
- `site_ref`
- `base_ref` (if exists)
- Any other `*_ref` fields

**Acceptance**: All `*_ref` fields have SHA pattern constraint

---

### HEAL-012: Add Rollback Metadata Fields to PR Schema

**Gap**: GAP-002 (BLOCKER), GAP-015 (MINOR)
**File**: `specs/schemas/pr.schema.json`
**Location**: Add to required fields and properties

**Action**:
1. Check if `base_ref`, `run_id`, `rollback_steps`, `affected_paths` fields exist
2. If missing, add to schema:
```json
{
  "required": [
    "schema_version",
    "base_ref",
    "run_id",
    "rollback_steps",
    "affected_paths",
    ...existing fields...
  ],
  "properties": {
    "base_ref": {
      "type": "string",
      "description": "Base commit SHA (40-char hex) for rollback",
      "pattern": "^[a-f0-9]{40}$"
    },
    "run_id": {
      "type": "string",
      "description": "Run ID that produced this PR"
    },
    "rollback_steps": {
      "type": "array",
      "description": "Executable shell commands for rollback",
      "items": {
        "type": "string"
      },
      "minItems": 1
    },
    "affected_paths": {
      "type": "array",
      "description": "File paths affected by this PR (must appear in PR diff)",
      "items": {
        "type": "string"
      },
      "minItems": 1
    },
    ...existing properties...
  }
}
```

**Acceptance**: All 4 fields added, `base_ref` has SHA pattern, `rollback_steps` and `affected_paths` have minItems:1

---

## PHASE 2: Validation Gate Specifications (Preparation for Implementation)

### HEAL-013: Document Runtime Gate Specifications

**Gap**: GAP-001 (BLOCKER)
**File**: `specs/09_validation_gates.md`
**Location**: Expand Gates 4-12 specifications (currently brief)

**Action**:
1. For each gate (4-12), expand specification with:
   - Inputs (which artifacts, which files)
   - Validation rules (specific checks)
   - Error codes (specific error_code strings)
   - Timeout (per profile: local/ci/prod)
   - Acceptance criteria (what constitutes pass/fail)

2. Example expansion for Gate 4 (frontmatter):
```markdown
#### Gate 4: Frontmatter Validation

**Purpose**: Validate all content files have valid frontmatter matching discovered contract

**Inputs**:
- `RUN_DIR/artifacts/frontmatter_contract.json` (from W1 RepoScout)
- All `*.md` files under `RUN_DIR/work/site/`

**Validation Rules**:
1. All `*.md` files MUST have frontmatter (YAML between `---` delimiters)
2. All required fields from `frontmatter_contract.json` MUST be present
3. All field types MUST match contract (string, date, array, etc.)
4. No unknown fields allowed (if `additionalProperties: false` in contract)

**Error Codes**:
- `GATE_FRONTMATTER_MISSING`: File has no frontmatter
- `GATE_FRONTMATTER_REQUIRED_FIELD_MISSING`: Required field absent
- `GATE_FRONTMATTER_TYPE_MISMATCH`: Field type doesn't match contract
- `GATE_FRONTMATTER_UNKNOWN_FIELD`: Unknown field present (strict mode)

**Timeout** (per profile):
- local: 5s
- ci: 10s
- prod: 20s

**Acceptance Criteria**:
- Gate passes if all files pass all rules
- Gate fails if any file violates any rule
- Issues array populated with specific file:line violations
```

3. Repeat for Gates 5-12 with similar level of detail

**Acceptance**: Gates 4-12 expanded with inputs, rules, error codes, timeouts, acceptance criteria

---

### HEAL-014: Document Rollback Metadata Validation Gate

**Gap**: GAP-002 (BLOCKER)
**File**: `specs/09_validation_gates.md`
**Location**: Add new gate after Gate 12

**Action**:
1. Insert new gate specification:
```markdown
#### Gate 13: Rollback Metadata Validation (Guarantee L)

**Purpose**: Validate PR artifacts include rollback metadata (prod profile only)

**Inputs**:
- `RUN_DIR/artifacts/pr.json` (from W9 PRManager)
- `run_config.validation_profile`

**Validation Rules** (only in prod profile):
1. `pr.json` MUST exist
2. `pr.json` MUST validate against `specs/schemas/pr.schema.json`
3. Required fields MUST be present: `base_ref`, `run_id`, `rollback_steps`, `affected_paths`
4. `base_ref` MUST match pattern `^[a-f0-9]{40}$` (40-char SHA)
5. `rollback_steps` array MUST have minItems: 1
6. `affected_paths` array MUST have minItems: 1
7. All paths in `affected_paths` MUST appear in PR diff

**Error Codes**:
- `PR_MISSING_ROLLBACK_METADATA`: Required rollback field missing
- `PR_INVALID_BASE_REF_FORMAT`: base_ref not a valid SHA
- `PR_EMPTY_ROLLBACK_STEPS`: rollback_steps array empty
- `PR_EMPTY_AFFECTED_PATHS`: affected_paths array empty
- `PR_AFFECTED_PATH_NOT_IN_DIFF`: Path in affected_paths missing from PR diff

**Behavior by Profile**:
- **prod**: BLOCKER if validation fails
- **ci**: WARN if validation fails
- **local**: SKIP (not run)

**Timeout**:
- local: N/A (not run)
- ci: 5s
- prod: 10s

**Acceptance Criteria**:
- Gate passes if all validation rules pass (prod profile)
- Gate skipped if profile != prod
- Issues array populated with specific violations
```

**Acceptance**: Gate 13 specification added, all fields documented

---

### HEAL-015: Document Floating Ref Runtime Rejection

**Gap**: GAP-004 (BLOCKER)
**File**: `specs/34_strict_compliance_guarantees.md`
**Location**: After line 58 (end of Guarantee A section)

**Action**:
1. Insert new subsection at line 59:
```markdown

#### Runtime Enforcement (Guarantee A)

**Gate**: `launch_validate` runtime check (in addition to Gate J preflight)

**Purpose**: Reject runs that use floating refs at runtime (defense in depth)

**Validation Rules**:
1. At start of `launch_validate` call, re-check all `*_ref` fields in `run_config`
2. All `*_ref` fields MUST match pattern `^[a-f0-9]{40}$` (40-char SHA)
3. Reject floating refs:
   - `refs/heads/*` (branch references)
   - `refs/tags/*` (tag references)
   - Branch names (e.g., `main`, `develop`)
   - `HEAD` or relative refs (`HEAD~1`, `@{upstream}`)

**Error Code**: `POLICY_FLOATING_REF_DETECTED`

**Behavior**:
- If floating ref detected: Raise error, terminate run immediately
- Error logged to telemetry
- Issue added to `issues[]` with severity: BLOCKER

**Integration**:
- TC-300 (Orchestrator): Call runtime validation before starting workers
- TC-460 (Validator): Implement runtime check in `launch_validate`

**Rationale**: Defense in depth. Even if Gate J passes at preflight, runtime check prevents race conditions or config tampering.
```

**Acceptance**: Subsection added, runtime validation rules documented, error code defined

---

## PHASE 3: Gate Implementation Specifications (Detailed)

### HEAL-016: Add Gate T Specification (Non-Flaky Tests)

**Gap**: GAP-014 (MINOR)
**File**: `specs/09_validation_gates.md`
**Location**: Add new gate after Gate 13 (or after existing gates)

**Action**:
1. Insert new gate specification:
```markdown
#### Gate T: Test Determinism Configuration (Guarantee I)

**Purpose**: Validate test configuration enforces determinism (PYTHONHASHSEED=0)

**Inputs**:
- `pyproject.toml` (pytest configuration)
- `pytest.ini` (if exists)
- `.github/workflows/*.yml` (CI test commands)

**Validation Rules**:
1. One of the following MUST be true:
   - `pyproject.toml` contains `[tool.pytest.ini_options]` with `env = ["PYTHONHASHSEED=0"]`
   - `pytest.ini` contains `[pytest]` section with `env = PYTHONHASHSEED=0`
   - All CI workflow test commands set `PYTHONHASHSEED=0` before running pytest

**Error Codes**:
- `TEST_MISSING_PYTHONHASHSEED`: PYTHONHASHSEED=0 not set in test config
- `TEST_DETERMINISM_NOT_ENFORCED`: No determinism controls in test config

**Timeout**: 5s (all profiles)

**Acceptance Criteria**:
- Gate passes if any validation rule is true
- Gate fails if all validation rules are false
```

**Acceptance**: Gate T specification added, validation rules documented

---

## Completion Checklist

After executing all healing steps, verify:

- [ ] HEAL-001: Worker contracts added to traceability matrix
- [ ] HEAL-002: State management specs added to traceability matrix
- [ ] HEAL-003: Navigation spec added to traceability matrix
- [ ] HEAL-004: Coordination spec added to traceability matrix
- [ ] HEAL-005: Byte-identical acceptance criteria clarified
- [ ] HEAL-006: ADRs created for all threshold choices (3 files)
- [ ] HEAL-007: Minimal-diff heuristic algorithm documented
- [ ] HEAL-008: Error code registry created
- [ ] HEAL-009: Prompt versioning requirement documented
- [ ] HEAL-010: Broken link report created (if applicable)
- [ ] HEAL-011: SHA format validation added to run_config schema
- [ ] HEAL-012: Rollback metadata fields added to pr.schema.json
- [ ] HEAL-013: Runtime gate specifications expanded (Gates 4-12)
- [ ] HEAL-014: Gate 13 (rollback metadata) specification added
- [ ] HEAL-015: Floating ref runtime rejection documented
- [ ] HEAL-016: Gate T (test determinism) specification added

**Final Validation**:
- [ ] All markdown files have no syntax errors (run `markdownlint specs/ plans/`)
- [ ] All JSON schemas validate (run `jsonschema --check` on all schemas)
- [ ] All file paths referenced exist
- [ ] All error codes follow pattern `{COMPONENT}_{ERROR_TYPE}_{SPECIFIC}`

---

## What's NOT in This Healing Prompt

**Explicitly Out of Scope** (implementation work, not pre-implementation healing):
- Implementing runtime validation gates (TC-460, TC-570)
- Implementing rollback metadata generation (TC-480)
- Implementing orchestrator (TC-300)
- Implementing determinism harness (TC-560)
- Implementing MCP tools (TC-510, TC-511, TC-512)
- Implementing workers (TC-400 series)
- Writing tests
- Creating test fixtures
- Implementing error code registry enforcement gate
- Implementing prompt versioning in LLM client

These are all **implementation tasks** tracked in taskcards, not pre-implementation documentation/specification gaps.

---

**Healing Complete**: All documentation, specification, and schema gaps resolved. Repository ready for implementation phase.
