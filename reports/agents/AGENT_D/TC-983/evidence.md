# TC-983 Evidence Report: Specs & Schemas for Evidence-Driven Page Scaling

**Agent**: Agent-D (Docs & Specs)
**Taskcard**: TC-983
**Date**: 2026-02-05
**Status**: Complete

---

## Files Changed (9 files)

### 1. specs/rulesets/ruleset.v1.yaml

**Changes**:
- Added `mandatory_pages` array to all 5 sections (products, docs, reference, kb, blog)
- Added `optional_page_policies` array to all 5 sections
- Added `family_overrides` top-level key with "3d" family entry
- Updated `min_pages`: docs 2 -> 5, kb 3 -> 4
- Docs mandatory_pages: `_index` (toc), `installation` (workflow_page), `getting-started` (workflow_page), `overview` (landing), `developer-guide` (comprehensive_guide)
- KB mandatory_pages: `faq` (troubleshooting), `troubleshooting` (troubleshooting)
- Products mandatory_pages: `overview` (landing)
- Reference mandatory_pages: `api-overview` (api_reference)
- Blog mandatory_pages: `announcement` (landing)
- Optional policies: docs has per_feature (p1) and per_workflow (p2), kb has per_key_feature (p1), reference has per_api_symbol (p1), blog has per_deep_dive (p2)
- family_overrides.3d.sections.docs.mandatory_pages: model-loading (workflow_page), rendering (workflow_page)

### 2. specs/schemas/ruleset.schema.json

**Changes**:
- Extended `sectionMinPages` $def with `mandatory_pages` (array of objects with required slug + page_role) and `optional_page_policies` (array of objects with required page_role + source + priority)
- Added `sectionOverride` $def: same properties as `sectionMinPages` but without `required: ["min_pages"]` (allows family overrides to specify only the fields they override)
- Added `family_overrides` as optional top-level property: object with additionalProperties being objects with optional `sections` property (uses `sectionOverride` $ref)
- page_role enum in both $defs matches page_plan.schema.json exactly: ["landing", "toc", "comprehensive_guide", "workflow_page", "feature_showcase", "troubleshooting", "api_reference"]

### 3. specs/schemas/page_plan.schema.json

**Changes**:
- Added `evidence_volume` as optional top-level property: `{ type: "object", additionalProperties: true }` with TC-983 description
- Added `effective_quotas` as optional top-level property: `{ type: "object", additionalProperties: true }` with TC-983 description
- Both properties are NOT in the `required` array, maintaining backward compatibility
- Placed between `inferred_product_type` and `pages` in property order

### 4. specs/schemas/validation_report.schema.json

**Changes**:
- Updated `issues` array description to include full list of Gate 14 error codes including new `GATE14_MANDATORY_PAGE_MISSING` (code: 1411, TC-983)
- Error codes documented: 1401-1411 (GATE14_ROLE_MISSING through GATE14_MANDATORY_PAGE_MISSING)

### 5. specs/06_page_planning.md

**Changes**:
- Updated "Mandatory Pages by Section" (now dated 2026-02-05, TC-983): changed from hardcoded lists to "configured via ruleset mandatory_pages". All entries now reference `sections.<section>.mandatory_pages` config path.
- Added "Configurable Page Requirements" section: documents mandatory_pages + family_overrides merge logic (union strategy, deduplicate by slug), configuration sources, example merge for 3d family, schema and worker references.
- Updated "Launch Tier Adjustments": documented that CI-absent ALONE no longer reduces to minimal; only CI-absent AND tests-absent together reduces. Added specific rules for both cases.
- Updated "Tier reduction signals": changed CI-absent rule to require both CI and tests absent. Added new rule for CI-absent + tests-present (keep tier).
- Updated "Optional Page Selection Algorithm": added Step 0 (compute evidence_volume), Step 1.5 (compute effective_quotas with tier scaling), updated Step 2 (generate candidates from optional_page_policies), updated Step 4 (rank by priority from policies), updated Step 5 (use effective_max_pages).

### 6. specs/07_section_templates.md

**Changes**:
- Added "Per-Feature Workflow Page Templates" section before "Template Discovery and Filtering"
- Documents: purpose, page_role (workflow_page), template structure (required headings), candidate generation from optional_page_policies, slug convention, validation rules, example for 3d family

### 7. specs/08_content_distribution_strategy.md

**Changes**:
- Added "Configurable Page Requirements" section before "Revision History"
- Documents: optional_page_policies overview, supported sources table (per_feature, per_workflow, per_key_feature, per_api_symbol, per_deep_dive), candidate generation algorithm from evidence, quality_score selection, interaction with content allocation rules, configuration references
- Updated revision history with TC-983 entry

### 8. specs/09_validation_gates.md

**Changes**:
- Added Gate 14 rule 8 "Mandatory Page Presence" (TC-983): all mandatory_pages slugs from merged ruleset config MUST exist in page_plan.pages - ERROR
- Documents: merge strategy (global + family_overrides for product_slug), detection algorithm, message format, suggested fix
- Added error code `GATE14_MANDATORY_PAGE_MISSING` (code: 1411, TC-983) to error codes list
- Added `specs/rulesets/ruleset.v1.yaml` to Gate 14 inputs (for mandatory page presence validation)

### 9. specs/21_worker_contracts.md

**Changes**:
- Added new W4 input: "Merged page requirements from ruleset (TC-983)" documenting mandatory_pages, optional_page_policies, and family_overrides from ruleset.v1.yaml with merge strategy
- Added new W4 output fields: `page_plan.evidence_volume` (dict with total_score, claim_count, snippet_count, api_symbol_count, workflow_count, key_feature_count) and `page_plan.effective_quotas` (dict mapping section names to computed max_pages)
- Added W4 binding requirements for: reading family_overrides, computing evidence_volume, computing effective_quotas with tier scaling coefficients

---

## Cross-Reference Consistency Check

### page_role enum consistency
- **page_plan.schema.json**: `["landing", "toc", "comprehensive_guide", "workflow_page", "feature_showcase", "troubleshooting", "api_reference"]`
- **ruleset.schema.json sectionMinPages.mandatory_pages[].page_role**: same enum
- **ruleset.schema.json sectionMinPages.optional_page_policies[].page_role**: same enum
- **ruleset.schema.json sectionOverride.mandatory_pages[].page_role**: same enum
- **ruleset.schema.json sectionOverride.optional_page_policies[].page_role**: same enum
- **PASS**: All enums match exactly

### mandatory_pages slug consistency
- **ruleset.v1.yaml docs**: `[_index, installation, getting-started, overview, developer-guide]` (5 entries, matching min_pages: 5)
- **ruleset.v1.yaml kb**: `[faq, troubleshooting]` (2 entries, min_pages: 4 allows 2 more optional)
- **ruleset.v1.yaml products**: `[overview]` (1 entry, matching min_pages: 1)
- **ruleset.v1.yaml reference**: `[api-overview]` (1 entry, matching min_pages: 1)
- **ruleset.v1.yaml blog**: `[announcement]` (1 entry, matching min_pages: 1)
- **06_page_planning.md**: Lists same slugs for each section
- **PASS**: All consistent

### evidence_volume and effective_quotas
- **page_plan.schema.json**: Defined as optional top-level properties
- **06_page_planning.md**: Algorithm documents computing and recording both fields
- **21_worker_contracts.md**: W4 output documents both fields with field descriptions
- **PASS**: All consistent

### GATE14_MANDATORY_PAGE_MISSING error code
- **validation_report.schema.json**: Documented as code 1411 in issues description
- **09_validation_gates.md**: Documented as code 1411 with severity ERROR in Gate 14 rule 8 and error codes list
- **PASS**: Code and severity consistent

### family_overrides
- **ruleset.v1.yaml**: Defined with 3d entry under docs.mandatory_pages
- **ruleset.schema.json**: family_overrides property uses sectionOverride $ref (no required fields)
- **06_page_planning.md**: Merge logic documented (union strategy, deduplicate by slug)
- **21_worker_contracts.md**: W4 binding requirements document reading and merging
- **09_validation_gates.md**: Gate 14 rule 8 documents merged config loading
- **PASS**: All consistent

### CI-absent tier reduction
- **06_page_planning.md "Launch Tier Adjustments"**: Both CI-absent AND tests-absent required for reduction
- **06_page_planning.md "Tier reduction signals"**: Updated rules match
- **PASS**: Consistent

### Optional page policies sources
- **ruleset.v1.yaml**: per_feature, per_workflow, per_key_feature, per_api_symbol, per_deep_dive
- **08_content_distribution_strategy.md**: Same 5 sources documented with evidence inputs and generation algorithms
- **06_page_planning.md**: Same sources listed in Step 2 of Optional Page Selection Algorithm
- **07_section_templates.md**: per_feature and per_workflow documented in template context
- **PASS**: All consistent

### Backward compatibility check
- **page_plan.schema.json**: evidence_volume and effective_quotas are NOT in required array
- **ruleset.schema.json**: mandatory_pages and optional_page_policies are NOT required in sectionMinPages
- **ruleset.schema.json**: family_overrides is NOT in top-level required array
- **PASS**: All new properties are optional

---

## No Orphan References Found

All references from specs point to fields that exist in schemas. All schema fields referenced in specs are documented. No orphan references detected.
