---
id: TC-1002
title: "Document Absolute cross_links in Specs/Schemas"
status: Complete
priority: P3
owner: Agent-D
updated: "2026-02-06"
tags: ["specs", "schemas", "cross_links", "docs"]
depends_on:
  - TC-1001
allowed_paths:
  - specs/schemas/page_plan.schema.json
  - specs/06_page_planning.md
  - specs/21_worker_contracts.md
  - reports/agents/agent_d/TC-1002/**
evidence_required:
  - reports/agents/agent_d/TC-1002/evidence.md
  - reports/agents/agent_d/TC-1002/self_review.md
spec_ref: "46d7ac2be0e1e3f1096f5d45ac1493d621436a99"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1002 — Document Absolute cross_links in Specs/Schemas

## Objective

Update specs and schemas to document that cross_links contains absolute URLs (https://...) rather than relative paths.

## Problem Statement

After TC-1001 changes cross_links to absolute URLs, the specs and schemas need to reflect this change for consistency and clarity.

## Required spec references

- specs/schemas/page_plan.schema.json (cross_links definition)
- specs/06_page_planning.md (page planning spec)
- specs/21_worker_contracts.md (W4 contract)

## Scope

### In scope
- Update page_plan.schema.json cross_links description
- Update specs/06_page_planning.md cross_links section
- Update specs/21_worker_contracts.md W4 outputs

### Out of scope
- Code changes (TC-1001)
- Other spec files

## Inputs
- Current specs with relative cross_links description
- TC-1001 implementation (cross_links now absolute)

## Outputs
- Updated schema with absolute URL description
- Updated specs documenting cross_links format

## Allowed paths

- specs/schemas/page_plan.schema.json
- specs/06_page_planning.md
- specs/21_worker_contracts.md
- reports/agents/agent_d/TC-1002/**

## Implementation steps

### Step 1: Update page_plan.schema.json
Find cross_links definition and update description:
```json
"cross_links": {
  "type": "array",
  "items": { "type": "string", "format": "uri" },
  "description": "Absolute URLs to related pages on other subdomains (e.g., https://docs.aspose.org/cells/python/overview/)"
}
```

### Step 2: Update specs/06_page_planning.md
Add or update section on cross_links:
```markdown
### cross_links Format

The `cross_links` field contains absolute URLs pointing to related pages:
- Format: `https://<subdomain>/<family>/<platform>/<slug>/`
- Example: `https://docs.aspose.org/cells/python/overview/`
- Subdomain matches section: docs → docs.aspose.org, kb → kb.aspose.org
```

### Step 3: Update specs/21_worker_contracts.md
In W4 outputs section, clarify cross_links format:
```markdown
- `cross_links`: Array of absolute URLs to related pages across subdomains
```

### Step 4: Verify consistency
Search all specs for cross_links references and ensure consistency.

## Failure modes

### Failure mode 1: Schema validation breaks
**Detection:** JSON schema validation errors
**Resolution:** Ensure schema changes are backward-compatible
**Spec/Gate:** Gate 1 (Schema Validation)

### Failure mode 2: Inconsistent spec references
**Detection:** Different specs describe cross_links differently
**Resolution:** Audit all references and align
**Spec/Gate:** Gate D (docs)

### Failure mode 3: Missing format constraint
**Detection:** Schema doesn't enforce URI format
**Resolution:** Add "format": "uri" to schema items
**Spec/Gate:** Schema completeness

## Task-specific review checklist

1. [x] page_plan.schema.json updated
2. [x] specs/06_page_planning.md updated
3. [x] specs/21_worker_contracts.md updated
4. [x] Format explicitly documented as absolute URL
5. [x] Example URLs included
6. [x] All cross-references consistent

## Deliverables

- Updated specs/schemas/page_plan.schema.json
- Updated specs/06_page_planning.md
- Updated specs/21_worker_contracts.md
- reports/agents/agent_d/TC-1002/evidence.md
- reports/agents/agent_d/TC-1002/self_review.md

## Acceptance checks

1. [x] Schema describes cross_links as absolute URLs
2. [x] Specs document cross_links format with examples
3. [x] W4 contract mentions absolute URL output

## E2E verification

```bash
# Validate schema
.venv/Scripts/python.exe -c "import json; json.load(open('specs/schemas/page_plan.schema.json')); print('Schema valid')"

# Search for cross_links documentation
grep -r "cross_links" specs/ --include="*.md" --include="*.json"
```

**Expected artifacts:**
- **specs/schemas/page_plan.schema.json** - cross_links with format: uri
- **specs/06_page_planning.md** - cross_links format section
- **specs/21_worker_contracts.md** - W4 outputs mention absolute URLs

## Integration boundary proven

**Upstream:** TC-1001 implements absolute cross_links
**Downstream:** Future consumers of page_plan.json understand cross_links format
**Contract:** cross_links is array of absolute URLs per schema

## Self-review

12-dimension self-review required. All dimensions >=4/5.
