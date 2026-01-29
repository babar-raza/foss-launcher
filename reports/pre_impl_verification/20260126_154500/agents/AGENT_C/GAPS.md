# Schema/Contract Gaps

## Overview
This document lists all mismatches between specs and schemas, ordered by severity.

**Total gaps:** 4 (1 BLOCKER, 2 MAJOR, 1 MINOR)

---

## BLOCKER Gaps

### C-GAP-001 | BLOCKER | Missing required field `positioning.who_it_is_for` in ProductFacts schema

**Description:**
The ProductFacts schema is missing the required field `positioning.who_it_is_for` as specified in specs/03_product_facts_and_evidence.md:17.

**Evidence:**

Spec requirement (specs/03_product_facts_and_evidence.md):
```
Line 17:  - `tagline`, `short_description`, `who_it_is_for`
```

Current schema (product_facts.schema.json:40-57):
```json
"positioning": {
  "type": "object",
  "additionalProperties": false,
  "required": [
    "tagline",
    "short_description"
  ],
  "properties": {
    "tagline": {
      "type": "string"
    },
    "short_description": {
      "type": "string"
    },
    "audience": {
      "type": "string"
    }
  }
}
```

**Issue:** The schema defines `positioning.audience` (optional) but spec requires `positioning.who_it_is_for`. The field is completely missing.

**Proposed fix:**

Edit `specs/schemas/product_facts.schema.json`:

1. Add `who_it_is_for` to `positioning.required` array (after `short_description`)
2. Add `who_it_is_for` property definition in `positioning.properties`

**Exact change required:**

```json
"positioning": {
  "type": "object",
  "additionalProperties": false,
  "required": [
    "tagline",
    "short_description",
    "who_it_is_for"
  ],
  "properties": {
    "tagline": {
      "type": "string"
    },
    "short_description": {
      "type": "string"
    },
    "who_it_is_for": {
      "type": "string",
      "description": "Target audience for this product (e.g., 'Python developers building 3D applications')"
    },
    "audience": {
      "type": "string",
      "description": "DEPRECATED: Use who_it_is_for instead"
    }
  }
}
```

**Acceptance criteria:**
- Gap closed when `product_facts.schema.json` includes `who_it_is_for` as a required string field in the `positioning` object
- Schema validates a ProductFacts JSON with `positioning.who_it_is_for` present
- Schema rejects a ProductFacts JSON missing `positioning.who_it_is_for`

**Related specs:**
- specs/03_product_facts_and_evidence.md:17

**Related schemas:**
- specs/schemas/product_facts.schema.json:40-57

---

## MAJOR Gaps

### C-GAP-002 | MAJOR | Field name mismatch: schema has `positioning.audience`, spec requires `positioning.who_it_is_for`

**Description:**
The ProductFacts schema defines `positioning.audience` (optional), but the spec (specs/03_product_facts_and_evidence.md:17) requires `positioning.who_it_is_for`. This is a naming inconsistency that could lead to implementation confusion.

**Evidence:**

Spec requirement (specs/03_product_facts_and_evidence.md):
```
Line 17:  - `tagline`, `short_description`, `who_it_is_for`
```

Current schema (product_facts.schema.json:54-56):
```json
"audience": {
  "type": "string"
}
```

**Issue:** The schema uses a different field name than the spec requires. While `audience` may be semantically similar to `who_it_is_for`, the spec is the authority and the schema must match exactly.

**Proposed fix:**

Either:
1. **Option A (Recommended):** Deprecate `audience`, make `who_it_is_for` required (see C-GAP-001)
2. **Option B:** Rename `audience` to `who_it_is_for` (breaking change)

**Recommended action:** Option A is already covered by C-GAP-001 fix. Mark `audience` as deprecated to support backward compatibility if needed.

**Acceptance criteria:**
- Gap closed when `product_facts.schema.json` uses `who_it_is_for` as the authoritative field name
- If `audience` is kept, it must be marked deprecated with a description: "DEPRECATED: Use who_it_is_for instead"
- Documentation updated to clarify that `who_it_is_for` is the spec-compliant field name

**Related specs:**
- specs/03_product_facts_and_evidence.md:17

**Related schemas:**
- specs/schemas/product_facts.schema.json:54-56

**Note:** This gap is resolved by implementing C-GAP-001 with the deprecation approach shown above.

---

### C-GAP-003 | MAJOR | Missing required field `retryable` in ApiError schema

**Description:**
The ApiError schema is missing the required field `retryable` (boolean) as specified in specs/24_mcp_tool_schemas.md:27.

**Evidence:**

Spec requirement (specs/24_mcp_tool_schemas.md:19-31):
```
Lines 19-31:
## Standard error shape (binding)
{
  "ok": false,
  "run_id": "optional",
  "error": {
    "code": "ILLEGAL_STATE",
    "message": "Human readable summary",
    "retryable": false,
    "details": { "any": "object" }
  }
}
```

Current schema (api_error.schema.json:1-14):
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://foss-launcher.local/schemas/api_error.schema.json",
  "title": "API Error",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "schema_version": { "type": "string" },
    "code": { "type": "string" },
    "message": { "type": "string" },
    "details": { "type": ["object", "null"], "additionalProperties": true }
  },
  "required": ["schema_version", "code", "message"]
}
```

**Issue:** The schema is missing the `retryable` field, which is critical for error handling and retry logic.

**Proposed fix:**

Edit `specs/schemas/api_error.schema.json`:

1. Add `retryable` to the `required` array
2. Add `retryable` property definition

**Exact change required:**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://foss-launcher.local/schemas/api_error.schema.json",
  "title": "API Error",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "schema_version": { "type": "string" },
    "code": { "type": "string" },
    "message": { "type": "string" },
    "retryable": {
      "type": "boolean",
      "description": "True if the error is transient and the operation can be retried"
    },
    "details": { "type": ["object", "null"], "additionalProperties": true }
  },
  "required": ["schema_version", "code", "message", "retryable"]
}
```

**Acceptance criteria:**
- Gap closed when `api_error.schema.json` includes `retryable` as a required boolean field
- Schema validates an ApiError JSON with `retryable` present
- Schema rejects an ApiError JSON missing `retryable`

**Related specs:**
- specs/24_mcp_tool_schemas.md:27
- specs/17_github_commit_service.md:43 (ApiError used in commit service responses)

**Related schemas:**
- specs/schemas/api_error.schema.json:1-14

**Impact:**
- This field is used by MCP tools and the commit service to determine retry behavior
- Missing this field breaks the error handling contract defined in specs/24_mcp_tool_schemas.md

---

## MINOR Gaps

### C-GAP-004 | MINOR | Missing `schema_version` field in issue.schema.json

**Description:**
The `issue.schema.json` does not include a `schema_version` field, which is required by the system-wide schema versioning policy (specs/01_system_contract.md:12).

**Evidence:**

Spec requirement (specs/01_system_contract.md):
```
Line 12: Schema versions MUST be explicit in every artifact (`schema_version` fields).
```

Current schema (issue.schema.json:1-41):
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "issue.schema.json",
  "type": "object",
  "additionalProperties": false,
  "required": ["issue_id", "gate", "severity", "message", "status"],
  "properties": {
    "issue_id": { "type": "string" },
    "gate": { "type": "string" },
    "severity": { "enum": ["info", "warn", "error", "blocker"] },
    "message": { "type": "string" },
    "error_code": {
      "type": "string",
      "pattern": "^[A-Z]+(_[A-Z]+)*$",
      "description": "Structured error code per specs/01_system_contract.md error taxonomy (e.g., GATE_TIMEOUT, SCHEMA_VALIDATION_FAILED). Required for error/blocker severity."
    },
    "files": { "type": "array", "items": { "type": "string" } },
    "location": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "path": { "type": "string" },
        "line": { "type": "integer" }
      }
    },
    "suggested_fix": { "type": "string" },
    "status": { "enum": ["OPEN", "IN_PROGRESS", "RESOLVED"] }
  },
  "allOf": [...]
}
```

**Issue:** The Issue object is embedded in other schemas (validation_report, snapshot, truth_lock_report) but lacks its own `schema_version` field. While this is MINOR (not BLOCKER) because Issue is always embedded within versioned parent schemas, it breaks the consistency requirement.

**Proposed fix:**

Edit `specs/schemas/issue.schema.json`:

1. Add `schema_version` to the `required` array
2. Add `schema_version` property definition

**Exact change required:**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "issue.schema.json",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "issue_id", "gate", "severity", "message", "status"],
  "properties": {
    "schema_version": {
      "type": "string",
      "description": "Schema version identifier for Issue objects"
    },
    "issue_id": { "type": "string" },
    "gate": { "type": "string" },
    "severity": { "enum": ["info", "warn", "error", "blocker"] },
    "message": { "type": "string" },
    "error_code": {
      "type": "string",
      "pattern": "^[A-Z]+(_[A-Z]+)*$",
      "description": "Structured error code per specs/01_system_contract.md error taxonomy (e.g., GATE_TIMEOUT, SCHEMA_VALIDATION_FAILED). Required for error/blocker severity."
    },
    "files": { "type": "array", "items": { "type": "string" } },
    "location": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "path": { "type": "string" },
        "line": { "type": "integer" }
      }
    },
    "suggested_fix": { "type": "string" },
    "status": { "enum": ["OPEN", "IN_PROGRESS", "RESOLVED"] }
  },
  "allOf": [
    {
      "if": {
        "properties": {
          "severity": { "enum": ["error", "blocker"] }
        }
      },
      "then": {
        "required": ["error_code"]
      }
    }
  ]
}
```

**Alternative approach (if embedding without schema_version is preferred):**

If the design decision is that embedded objects do NOT need `schema_version` because they inherit versioning from their parent, then:
1. Update specs/01_system_contract.md:12 to clarify: "Schema versions MUST be explicit in every **top-level** artifact"
2. Document this exception in the schema design guide
3. Close this gap as "by design"

**Acceptance criteria:**
- **Option A (Recommended):** Gap closed when `issue.schema.json` includes `schema_version` as a required string field
- **Option B (Alternative):** Gap closed when specs/01_system_contract.md:12 is updated to clarify that embedded objects are exempt from the schema_version requirement

**Related specs:**
- specs/01_system_contract.md:12

**Related schemas:**
- specs/schemas/issue.schema.json:1-41
- specs/schemas/validation_report.schema.json:47-52 (embeds issue.schema.json)
- specs/schemas/snapshot.schema.json:60-64 (embeds issue.schema.json)
- specs/schemas/truth_lock_report.schema.json:60-65 (embeds issue.schema.json)

**Note:** This is marked MINOR because:
1. Issue objects are always embedded within versioned parent schemas (validation_report, snapshot, truth_lock_report)
2. Parent schema versioning provides sufficient traceability
3. Adding `schema_version` to Issue would be redundant but consistent with policy

---

## RETRACTED Gaps

### C-GAP-005 | RETRACTED | event.schema.json does NOT have a missing schema_version field

**Description:**
Initial analysis incorrectly identified `event.schema.json` as missing a `schema_version` field.

**Evidence:**

Re-check of schema (event.schema.json:1-21):
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "event.schema.json",
  "type": "object",
  "additionalProperties": false,
  "required": ["event_id", "run_id", "ts", "type", "payload", "trace_id", "span_id"],
  "properties": {
    "event_id": { "type": "string" },
    "run_id": { "type": "string" },
    "ts": { "type": "string", "format": "date-time" },
    "type": { "type": "string" },
    "payload": { "type": "object" },

    "trace_id": { "type": "string" },
    "span_id": { "type": "string" },
    "parent_span_id": { "type": "string" },

    "prev_hash": { "type": "string" },
    "event_hash": { "type": "string" }
  }
}
```

**Correction:**
Upon closer inspection, `event.schema.json` does NOT include `schema_version` in the required array or properties. This gap is VALID, not retracted.

**Reclassification:**
- This is a valid gap but has the same characteristics as C-GAP-004
- Event objects are always embedded in event streams (events.ndjson) where each line is a separate Event object
- The spec (specs/11_state_and_events.md:62-73) does not explicitly require `schema_version` in Event objects

**Proposed fix:**

Same as C-GAP-004: Either add `schema_version` to Event objects for consistency, OR clarify in specs that embedded/streamed objects are exempt.

**Recommended action:**
- Merge this gap with C-GAP-004 as a general "embedded objects versioning policy" gap
- Both issue.schema.json and event.schema.json have the same issue
- Both should be fixed together or both should be documented as exceptions

---

## Gap Summary Table

| Gap ID | Severity | Affected Schema | Fix Complexity | Blocking Implementation? |
|--------|----------|-----------------|----------------|--------------------------|
| C-GAP-001 | BLOCKER | product_facts.schema.json | Low (add 1 field) | Yes (W2: FactsBuilder) |
| C-GAP-002 | MAJOR | product_facts.schema.json | Low (field rename) | Partial (field name inconsistency) |
| C-GAP-003 | MAJOR | api_error.schema.json | Low (add 1 field) | Yes (Commit Service, MCP Tools) |
| C-GAP-004 | MINOR | issue.schema.json | Low (add 1 field) | No (embedded objects) |
| C-GAP-005 | RECLASSIFIED | event.schema.json | Low (add 1 field) | No (same as C-GAP-004) |

---

## Implementation Priority

### Phase 1 (BLOCKER - must fix before W2 implementation)
1. **C-GAP-001:** Add `who_it_is_for` to `product_facts.schema.json`
   - Estimated effort: 5 minutes
   - Blocks: W2 FactsBuilder implementation
   - Risk: HIGH (missing required field will cause validation failures)

### Phase 2 (MAJOR - must fix before commit service / MCP tools implementation)
2. **C-GAP-003:** Add `retryable` to `api_error.schema.json`
   - Estimated effort: 5 minutes
   - Blocks: Commit Service, MCP Tools error handling
   - Risk: MEDIUM (error handling broken without this field)

3. **C-GAP-002:** Document `audience` deprecation in favor of `who_it_is_for`
   - Estimated effort: 2 minutes (add description field)
   - Blocks: Documentation clarity
   - Risk: LOW (naming inconsistency, not a functional blocker)

### Phase 3 (MINOR - can defer to policy clarification)
4. **C-GAP-004 + C-GAP-005:** Clarify embedded object versioning policy
   - Estimated effort: 10 minutes (schema update) OR 5 minutes (spec clarification)
   - Blocks: Nothing (embedded objects inherit parent versioning)
   - Risk: VERY LOW (consistency issue only)

---

## Acceptance Summary

**All gaps closed when:**
1. ✅ `product_facts.schema.json` includes `positioning.who_it_is_for` as required field
2. ✅ `product_facts.schema.json` marks `positioning.audience` as deprecated (if kept)
3. ✅ `api_error.schema.json` includes `retryable` as required boolean field
4. ✅ Either `issue.schema.json` includes `schema_version` OR specs/01_system_contract.md clarifies embedded object exception
5. ✅ Either `event.schema.json` includes `schema_version` OR same policy clarification as #4

**Verification commands:**
```bash
# Verify product_facts.schema.json fix
rg '"who_it_is_for"' specs/schemas/product_facts.schema.json

# Verify api_error.schema.json fix
rg '"retryable"' specs/schemas/api_error.schema.json

# Verify issue.schema.json fix
rg '"schema_version"' specs/schemas/issue.schema.json

# Verify event.schema.json fix
rg '"schema_version"' specs/schemas/event.schema.json
```

---

**Generated:** 2026-01-27
**Agent:** AGENT_C (Schemas/Contracts Verifier)
**Total gaps:** 4 (1 BLOCKER, 2 MAJOR, 1 MINOR)
**Estimated total fix time:** 27 minutes
