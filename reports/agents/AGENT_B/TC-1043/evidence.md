# TC-1043: Workflow Enrichment - Evidence

## Taskcard
- **ID**: TC-1043
- **Title**: Implement workflow enrichment for W2 FactsBuilder
- **Status**: Complete
- **Agent**: Agent-B

## Changes Made

### 1. New file: `src/launch/workers/w2_facts_builder/enrich_workflows.py`

Created complete workflow enrichment module with the following functions:

- **`enrich_workflow(workflow_tag, claim_ids, claims, snippets)`**: Main entry point. Enriches a minimal workflow with metadata including complexity, estimated time, ordered steps, and description.
- **`_determine_complexity(claims)`**: Returns "simple" (<=2 claims), "moderate" (<=5), or "complex" (>5).
- **`_estimate_time(claims)`**: Base time (5/10/15 min) + 5 min per additional claim.
- **`_order_workflow_steps(claims, snippets)`**: Orders claims into logical phases: install -> setup -> config -> basic -> advanced.
- **`_find_matching_snippet(claim, snippets)`**: Matches snippets to claims by tag overlap.
- **`_extract_step_name(claim_text)`**: Truncates claim text to 60 chars.
- **`_prettify_workflow_name(tag)`**: Converts tag to title case.
- **`_generate_workflow_description(tag, claims)`**: Template-based descriptions.
- **`_get_snippet_tags(tag)`**: Maps workflow tags to snippet tags.

### 2. `src/launch/workers/w2_facts_builder/worker.py`

Replaced simple workflow building (dict literals) with enriched workflow calls:
- Loads snippet_catalog.json if available
- Calls `enrich_workflow()` for installation and quickstart workflows
- Enriched workflows include: workflow_id, name, title, description, complexity, estimated_time_minutes, ordered steps, snippet_tags

## Test Results

```
tests/unit/workers/test_tc_411_extract_claims.py: 42 passed (includes assemble_product_facts tests)
tests/unit/workers/test_tc_412_map_evidence.py: 38 passed
```

## Verification

- Existing tests pass because enriched workflows are a superset of the old structure
- Old fields (`workflow_tag`, `title`, `claim_ids`, `snippet_tags`) are all preserved
- New fields (`workflow_id`, `name`, `description`, `complexity`, `estimated_time_minutes`, `steps`) are additive
