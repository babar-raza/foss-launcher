# TC-3622: Evidence Report — Evidence Map Schema Alignment

**Date**: 2026-03-01
**Author**: agent_b
**Pilot run**: r_20260301T100404Z_launch_pilot-aspose-cells-foss-python_c47529c_default_b5399032

## Problem Identified

`gate_1_schema_validation` failing on cells pilot with error:

```
Schema violation in evidence_map.json: Additional properties are not allowed
('benefit', 'end_line', 'example_domain', 'keyword_boost', 'section_kind',
 'source_file', 'start_line' were unexpected)
```

Additionally discovered (via full jsonschema validation):
- `truth_status: "verified"` in 6 synthesized use-case claims (not in enum)
- `steps` array field in 5 tutorial claims (not in schema)

## Root Cause

W2 workers (TC-411 `extract_claims.py`, TC-1618 `feature_profiles.py`, `worker.py`)
write 9 optional fields to `evidence_map.json` claim items that were not declared in
`specs/schemas/evidence_map.schema.json`. The schema has `additionalProperties: false`,
causing strict validation failure on any undeclared field.

## Changes Made

### 1. `specs/schemas/evidence_map.schema.json`
Added to `claims.items.properties` (all optional, not in `required`):
- `source_file` (string) — relative path to source file (TC-411)
- `start_line` (integer ≥0) — starting line in source (TC-411)
- `end_line` (integer ≥0) — ending line in source (TC-411)
- `section_kind` (string) — source section kind (TC-411)
- `keyword_boost` (boolean) — SEO keyword targeting flag (TC-411)
- `benefit` (string) — use-case key value proposition (TC-1618)
- `example_domain` (string) — use-case industry/domain (TC-1618)
- `steps` (array) — tutorial claim steps (TC-1618)

Extended `truth_status` enum: `["fact", "inference"]` → `["fact", "inference", "verified"]`
to allow the "verified" value written by `feature_profiles.py` for synthesized use cases.

### 2. `specs/03_product_facts_and_evidence.md §EvidenceMap`
Added "### Optional enrichment fields (claim-level)" table documenting all 9 changes
(7 new fields + `steps` + `truth_status` enum extension).

## Validation

Full jsonschema validation against the updated schema:
```
Remaining schema errors: 0
PASS: evidence_map.json validates cleanly against updated schema
```

Gate_1 pilot confirmation: to be run after heal loop completes (loop currently active).

## Claim properties in updated schema (28 total)
`claim_id`, `claim_text`, `claim_kind`, `truth_status`, `confidence`, `source_priority`,
`audience_level`, `complexity`, `prerequisites`, `use_cases`, `target_persona`,
`evidence_count`, `evidence_priority`, `normalized_text`, `source_relevance`,
`source_section`, `source_type`, `step_order`, `supporting_evidence`,
`source_file`, `start_line`, `end_line`, `section_kind`, `keyword_boost`,
`benefit`, `example_domain`, `steps`, `evidence_chunks`, `citations`
