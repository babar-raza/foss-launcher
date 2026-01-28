# Phase 4 Changes - Agent D

**Date**: 2026-01-27
**Phase**: 4 of 4 (Final Phase)
**Tasks Completed**: 5/5

---

## Summary

All 5 tasks completed successfully:
- TASK-SPEC-4A: Added telemetry GET endpoint to specs/16 and specs/24
- TASK-SPEC-4B: Added template resolution order algorithm to specs/20
- TASK-SPEC-4C: Created test harness contract spec at specs/35
- TASK-SPEC-4D: Added empty input handling to specs/03
- TASK-SPEC-4E: Added floating reference detection to specs/34

All changes are append-only (no deletions or modifications to existing content).

---

## TASK-SPEC-4A: Add Telemetry GET Endpoint (S-GAP-020)

### File 1: specs/16_local_telemetry_api.md

**Location**: After line 74 (after "Avoid randomness in `run_id`" section)

**Change Type**: APPEND (new section)

**Content Added**:
```markdown
## Telemetry Retrieval API

### GET /telemetry/{run_id}

**Purpose:** Retrieve telemetry data for a specific run

**Request:**
- Method: GET
- Path: `/telemetry/{run_id}`
- Headers: `Accept: application/json`
- Body: None

**Response (Success):**
- Status: 200 OK
- Body: Telemetry JSON object (see schema: specs/schemas/telemetry.schema.json)

**Response (Not Found):**
- Status: 404 Not Found
- Body: `{"error": "run_id not found", "run_id": "abc123"}`

**Response (Error):**
- Status: 500 Internal Server Error
- Body: `{"error": "description"}`

**Example:**
```bash
curl http://localhost:8080/telemetry/20250125-1530
```

**Caching:** Results are cached per run_id (immutable after run completion)

**MCP Tool:** See specs/24_mcp_tool_schemas.md (tool schema: get_run_telemetry)
```

**Evidence**: specs/16_local_telemetry_api.md:76-107

---

### File 2: specs/24_mcp_tool_schemas.md

**Location**: After line 386 (after launch_list_runs section)

**Change Type**: APPEND (new tool schema)

**Content Added**:
```markdown
---

### get_run_telemetry

**Purpose:** Retrieve telemetry data for a specific run via MCP protocol

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "run_id": {
      "type": "string",
      "description": "Run identifier (format: YYYYMMDD-HHMM)",
      "pattern": "^[0-9]{8}-[0-9]{4}$"
    }
  },
  "required": ["run_id"]
}
```

**Output Schema:**
```json
{
  "type": "object",
  "description": "Telemetry data for the run (see specs/schemas/telemetry.schema.json)"
}
```

**Error Cases:**
- Run ID not found → MCP error with code "NOT_FOUND"
- Invalid run ID format → MCP error with code "INVALID_INPUT"

**Example Usage:**
```json
{
  "tool": "get_run_telemetry",
  "input": {
    "run_id": "20250125-1530"
  }
}
```

**HTTP Mapping:** Calls GET /telemetry/{run_id} endpoint (see specs/16_local_telemetry_api.md)
```

**Evidence**: specs/24_mcp_tool_schemas.md:388-431

**Cross-references**:
- specs/16:107 → specs/24 (MCP tool schema reference)
- specs/24:431 → specs/16 (HTTP endpoint reference)

---

## TASK-SPEC-4B: Add Template Resolution Order (R-GAP-004)

### File: specs/20_rulesets_and_templates_registry.md

**Location**: After line 77 (before "### V1 Layout (Legacy)" section)

**Change Type**: APPEND (new algorithm section)

**Content Added**:
```markdown
### Template Resolution Order Algorithm

**Purpose:** Deterministic resolution when multiple templates match a file type

**Algorithm:**
1. Load all templates from registry (specs/20:70-85)
2. Filter templates where `file_pattern` regex matches target file path
3. If zero matches → Use default template (specs/08:45-60)
4. If one match → Use that template
5. If multiple matches → Sort by **specificity score** (highest first), break ties by **template name** (lexicographic)
6. Return first template from sorted list

**Specificity Score Calculation:**
- Start with 0
- +100 for each literal path segment (e.g., "src/pages" = 2 segments = +200)
- +50 for each extension match (e.g., ".md" = +50)
- +10 for each wildcard in pattern (e.g., "*.md" = 1 wildcard = +10)
- Longer patterns = higher specificity (more precise matching)

**Example:**
- Pattern: `src/pages/*.md` → Score: 200 (2 literal segments) + 50 (extension) + 10 (wildcard) = 260
- Pattern: `*.md` → Score: 50 (extension) + 10 (wildcard) = 60
- Pattern: `src/pages/about.md` → Score: 200 (2 segments) + 50 (extension) + 0 (no wildcard) = 250

**Determinism:** Guaranteed (specificity is deterministic, lexicographic tie-breaking is deterministic)

**Error Cases:**
- No templates in registry → ERROR: TEMPLATE_REGISTRY_EMPTY
- Circular template inheritance → ERROR: TEMPLATE_CIRCULAR_DEPENDENCY
```

**Evidence**: specs/20_rulesets_and_templates_registry.md:79-107

---

## TASK-SPEC-4C: Create Test Harness Contract Spec (S-GAP-023)

### File: specs/35_test_harness_contract.md (NEW FILE)

**Location**: New file created at specs/35_test_harness_contract.md

**Change Type**: CREATE (new spec file)

**Content**: Complete test harness contract with 6 requirements (REQ-TH-001 through REQ-TH-006)

**Structure**:
- Title: "35. Test Harness Contract"
- Status: Binding
- Owner: Test Infrastructure Team
- 6 Requirements:
  - REQ-TH-001: Test Harness Invocation (CLI interface)
  - REQ-TH-002: Preflight Gates Execution
  - REQ-TH-003: Runtime Gates Execution
  - REQ-TH-004: Test Isolation
  - REQ-TH-005: Test Report Schema
  - REQ-TH-006: Pilot Test Execution
- Cross-references to specs/09, specs/11, specs/13, specs/34

**Evidence**: specs/35_test_harness_contract.md:1-160 (complete file)

**Cross-references**:
- specs/35:5 → specs/09 (validation gates)
- specs/35:5 → specs/13 (pilots)
- specs/35:26 → specs/09:20-135 (preflight gates)
- specs/35:36 → specs/09:140-285 (runtime gates)
- specs/35:42 → specs/11 (state transitions)
- specs/35:59 → specs/schemas/validation_report.schema.json
- specs/35:99 → specs/13 (pilot test specifications)
- specs/35:153 → specs/34 (determinism guarantees)

---

## TASK-SPEC-4D: Add Empty Input Handling Requirement (R-GAP-001)

### File: specs/03_product_facts_and_evidence.md

**Location**: After line 36 (after "**Rule:** if a field cannot be determined..." paragraph)

**Change Type**: APPEND (new edge case section)

**Content Added**:
```markdown
### Edge Case: Empty Input Handling

**Scenario:** Repository has zero documentation files (no README, no docs/, no wiki)

**Detection:**
- repo_inventory.json shows `file_count: 0` OR
- All files are in `phantom_paths` (excluded by .hugophantom)

**Behavior:**
1. Emit ERROR with code: `REPO_EMPTY` (see specs/01)
2. Do NOT generate product_facts.json (validation fails before artifact creation)
3. Exit with non-zero status code

**Rationale:** Cannot extract facts from non-existent documentation. User must provide repository with at least one documentation file.

**Test Case:** See `pilots/pilot-empty-repo/` (TO BE CREATED during implementation phase)

**Related:** See specs/02:65-76 (empty repository edge case for ingestion)
```

**Evidence**: specs/03_product_facts_and_evidence.md:38-55

**Cross-references**:
- specs/03:47 → specs/01 (REPO_EMPTY error code from Phase 1)
- specs/03:55 → specs/02:65-76 (empty repository edge case from Phase 2)

---

## TASK-SPEC-4E: Add Floating Ref Detection Requirement (R-GAP-002)

### File: specs/34_strict_compliance_guarantees.md

**Location**: After line 85 (after Runtime Enforcement rationale, before "### B) Hermetic Execution Boundaries")

**Change Type**: APPEND (new guarantee section)

**Content Added**:
```markdown
### Guarantee L: Floating Reference Detection

**Guarantee:** System MUST detect and reject floating Git references (branches, tags) in spec_ref field

**Definition:** Floating reference = Git ref that can move over time (e.g., branch name "main", tag "latest")

**Enforcement:**
1. Validate spec_ref field is exactly 40-character hex SHA (see specs/01:180-195 field definition)
2. Reject branch names (e.g., "main", "develop", "feature/foo")
3. Reject tag names (e.g., "v1.0.0", "latest")
4. Reject short SHAs (e.g., "a1b2c3d" - 7 chars)
5. Reject symbolic refs (e.g., "HEAD", "FETCH_HEAD")

**Error Cases:**
- spec_ref is branch/tag → ERROR: SPEC_REF_INVALID (see specs/01:134)
- spec_ref is not 40-char hex → ERROR: SPEC_REF_INVALID
- spec_ref field missing → ERROR: SPEC_REF_MISSING (see specs/01:135)

**Validation:**
- Preflight Gate 2 validates spec_ref format (see specs/09:30-42)
- Runtime Gate 1 validates spec_ref resolves to commit (see specs/09:145-158)

**Rationale:** Floating refs break reproducibility. Only immutable commit SHAs allowed.

**Example (VALID):**
```json
{
  "spec_ref": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"
}
```

**Example (INVALID):**
```json
{
  "spec_ref": "main"  // ERROR: branch name not allowed
}
```

**Test Case:** See `tests/test_spec_ref_validation.py` (TO BE CREATED during implementation phase)
```

**Evidence**: specs/34_strict_compliance_guarantees.md:87-125

**Cross-references**:
- specs/34:94 → specs/01:180-195 (spec_ref field definition from Phase 3)
- specs/34:101 → specs/01:134 (SPEC_REF_INVALID error code from Phase 1)
- specs/34:103 → specs/01:135 (SPEC_REF_MISSING error code from Phase 1)
- specs/34:106 → specs/09:30-42 (Preflight Gate 2)
- specs/34:107 → specs/09:145-158 (Runtime Gate 1)

---

## Summary Statistics

**Files Modified**: 5
- specs/16_local_telemetry_api.md (APPEND)
- specs/24_mcp_tool_schemas.md (APPEND)
- specs/20_rulesets_and_templates_registry.md (APPEND)
- specs/03_product_facts_and_evidence.md (APPEND)
- specs/34_strict_compliance_guarantees.md (APPEND)

**Files Created**: 1
- specs/35_test_harness_contract.md (NEW)

**Total Lines Added**: ~200 lines

**Cross-references Added**: 12
- 2 cross-references between specs/16 and specs/24
- 2 cross-references from specs/03 to specs/01 and specs/02
- 5 cross-references from specs/34 to specs/01 and specs/09
- 3 cross-references from specs/35 to specs/09, specs/11, specs/13, specs/34

**Gaps Resolved**: 3 spec-level BLOCKER gaps
- S-GAP-020: Missing telemetry GET endpoint spec
- R-GAP-004: Missing template resolution order algorithm
- S-GAP-023: Missing test harness contract spec
- R-GAP-001: Missing empty input handling requirement
- R-GAP-002: Missing floating ref detection requirement

**All Changes**: Append-only (zero deletions, zero modifications to existing content)
