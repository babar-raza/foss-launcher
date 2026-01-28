# TC-430 Implementation Report: W4 IAPlanner

**Agent**: W4_AGENT
**Taskcard**: TC-430 - W4 IAPlanner (Information Architecture Planning)
**Date**: 2026-01-28
**Status**: COMPLETE

## Executive Summary

Successfully implemented W4 IAPlanner worker per specs/06_page_planning.md and specs/21_worker_contracts.md:157-176. The implementation generates comprehensive page plans (information architecture) for documentation content before any writing occurs.

**Key Metrics**:
- Tests: 30/30 passing (100%)
- Test Coverage: Comprehensive (all core functions tested)
- Spec Compliance: Full compliance with all referenced specs
- LOC: ~800 lines (worker.py) + ~750 lines (tests)

## Implementation Summary

### 1. Worker Module (src/launch/workers/w4_ia_planner/worker.py)

Implemented complete page planning workflow:

**Core Functions**:
- `execute_ia_planner()`: Main entry point, orchestrates full planning pipeline
- `load_product_facts()`: Loads product_facts.json from TC-410 (W2 FactsBuilder)
- `load_snippet_catalog()`: Loads snippet_catalog.json from TC-420 (W3 SnippetCurator)
- `determine_launch_tier()`: Determines launch tier (minimal/standard/rich) based on repository quality signals
- `infer_product_type()`: Infers product type (sdk/library/cli/service) from positioning
- `compute_url_path()`: Computes canonical URL paths per specs/33_public_url_mapping.md
- `compute_output_path()`: Computes content file paths relative to site repo root
- `plan_pages_for_section()`: Generates page specifications for each section
- `add_cross_links()`: Adds cross-links between pages per spec rules
- `check_url_collisions()`: Detects URL path collisions (blocker error)
- `validate_page_plan()`: Validates page plan against schema requirements

**Launch Tier Logic** (per specs/06_page_planning.md:116-139):
- Default tier: standard
- Reduction signals:
  - Contradictions detected → force minimal
  - CI absent → reduce by one level
  - Phantom paths detected → reduce by one level
  - No examples + only generated snippets → force minimal
- Elevation signals:
  - CI present + tests present + validated examples + structured docs → elevate to rich

**Section Planning** (per specs/06_page_planning.md:42-49):
- **products**: Overview page with positioning, features, platforms
- **docs**: Getting-started + workflow-based guides (1-5 pages based on tier)
- **reference**: API overview + module pages (1-4 pages based on tier)
- **kb**: FAQ + troubleshooting + limitations (1-3 pages based on tier)
- **blog**: Announcement post

**Cross-linking Rules** (per specs/06_page_planning.md:31-35):
- docs → reference (API documentation)
- kb → docs (how-to guides)
- blog → products (product overview)

**URL Computation** (per specs/33_public_url_mapping.md):
- V2 layout: `/<family>/<platform>/<section>/<slug>/`
- Default language (en): locale dropped from URL
- Deterministic slugs from workflow IDs and section names

**Deterministic Ordering** (per specs/10_determinism_and_caching.md:39-48):
- Pages sorted by (section_order, output_path)
- Section order: products < docs < reference < kb < blog
- Ensures stable outputs for caching

**Event Emission** (per specs/11_state_and_events.md):
- WORK_ITEM_STARTED: Planning started
- ARTIFACT_WRITTEN: page_plan.json written
- WORK_ITEM_FINISHED: Planning completed successfully
- ISSUE_OPENED: URL collision or insufficient evidence
- RUN_FAILED: Fatal error during planning

**Error Handling**:
- Missing artifacts (product_facts.json, snippet_catalog.json) → IAPlannerError
- URL collisions → IAPlannerURLCollisionError (blocker issue)
- Insufficient evidence → IAPlannerPlanIncompleteError (blocker issue)
- Invalid page plan → IAPlannerValidationError

### 2. Package Exports (src/launch/workers/w4_ia_planner/__init__.py)

Exported public API:
- `execute_ia_planner`: Main entry point
- `IAPlannerError`: Base exception
- `IAPlannerPlanIncompleteError`: Insufficient evidence exception
- `IAPlannerURLCollisionError`: URL collision exception
- `IAPlannerValidationError`: Validation failure exception

### 3. Comprehensive Tests (tests/unit/workers/test_tc_430_ia_planner.py)

**30 tests covering**:

**Artifact Loading (Tests 1-4)**:
- Load product_facts.json successfully
- Error on missing product_facts.json
- Load snippet_catalog.json successfully
- Error on missing snippet_catalog.json

**Launch Tier Determination (Tests 5-8)**:
- Default tier determination
- Explicit config override
- Contradictions force minimal tier
- Quality signals elevate to rich tier

**Product Type Inference (Tests 9-10)**:
- SDK inference (multi-platform)
- Library inference (single-platform)

**URL and Path Computation (Tests 11-14)**:
- URL path for products section
- URL path for docs section
- Output path for products section
- Output path for docs section

**Page Planning (Tests 15-18)**:
- Plan pages for products section
- Plan pages for docs section
- Minimal tier page count constraints
- Rich tier expanded page count

**Cross-linking (Test 19)**:
- Cross-link addition per spec rules

**URL Collision Detection (Tests 20-21)**:
- No collisions detected (valid case)
- Collision detected (error case)

**Page Plan Validation (Tests 22-25)**:
- Valid page plan passes
- Missing required field fails
- Invalid launch tier fails
- Invalid section fails

**Full Integration (Tests 26-30)**:
- Execute full IA planner successfully
- Deterministic page ordering
- Event emission verification
- Schema validation (all required fields)
- Missing artifacts error handling

## Test Results

```
============================= test session starts =============================
platform win32 -- Python 3.13.2, pytest-8.4.2, pluggy-1.6.0
collected 30 items

tests\unit\workers\test_tc_430_ia_planner.py ........................... [ 90%]
...                                                                      [100%]

============================= 30 passed in 0.82s ==============================
```

**Test Pass Rate**: 30/30 (100%)

## Spec Compliance

### specs/06_page_planning.md
- ✅ PagePlan structure (lines 6-18)
- ✅ Planning rules (lines 24-35)
- ✅ Determinism requirements (lines 37-40)
- ✅ Content quotas (lines 42-49)
- ✅ Planning failure modes (lines 55-83)
- ✅ Launch tiers (lines 86-92)
- ✅ Tier-driven page inventory (lines 94-108)
- ✅ Product type adaptation (lines 110-115)
- ✅ Launch tier quality signals (lines 116-139)

### specs/21_worker_contracts.md:157-176
- ✅ W4 IAPlanner contract
- ✅ Input artifacts (product_facts.json, snippet_catalog.json)
- ✅ Output artifact (page_plan.json)
- ✅ Template selection (deterministic by tier)
- ✅ URL path computation via specs/33_public_url_mapping.md

### specs/10_determinism_and_caching.md
- ✅ Stable ordering (section_order, output_path)
- ✅ Deterministic slugs
- ✅ Sorted cross-links

### specs/11_state_and_events.md
- ✅ Event emission (STARTED, FINISHED, ARTIFACT_WRITTEN)
- ✅ Append-only event log (events.ndjson)
- ✅ Trace ID and span ID in events

### specs/33_public_url_mapping.md
- ✅ V2 layout URL computation
- ✅ Default language handling (locale dropped)
- ✅ Platform in URL path

### specs/schemas/page_plan.schema.json
- ✅ All required fields present
- ✅ Launch tier enum validation
- ✅ Section enum validation
- ✅ Page field requirements

## Artifacts Produced

1. **src/launch/workers/w4_ia_planner/worker.py** (~800 lines)
   - Complete page planning implementation
   - Launch tier determination with quality signals
   - URL and path computation
   - Cross-linking logic
   - Event emission
   - Error handling

2. **src/launch/workers/w4_ia_planner/__init__.py** (24 lines)
   - Public API exports
   - Exception hierarchy

3. **tests/unit/workers/test_tc_430_ia_planner.py** (~750 lines)
   - 30 comprehensive tests
   - 100% pass rate
   - Mock fixtures for run directory, product facts, snippet catalog

4. **reports/agents/W4_AGENT/TC-430/report.md** (this file)
   - Implementation summary
   - Test results
   - Spec compliance checklist

5. **reports/agents/W4_AGENT/TC-430/self_review.md** (separate file)
   - 12-dimension quality assessment

## Dependencies Verified

All dependencies confirmed complete:
- ✅ TC-200 (IO layer) - Used RunLayout, atomic_write_json
- ✅ TC-250 (Models) - Used Event model
- ✅ TC-300 (Orchestrator) - Worker contract integration ready
- ✅ TC-500 (LLM client) - Interface ready (not used in heuristic implementation)
- ✅ TC-410 (W2 FactsBuilder) - Consumes product_facts.json
- ✅ TC-420 (W3 SnippetCurator) - Consumes snippet_catalog.json

## Known Limitations

1. **LLM-based planning**: Current implementation uses heuristic page planning. LLM client parameter accepted but not used. This is acceptable for initial implementation per spec.

2. **Product type inference**: Uses simple keyword matching. Could be enhanced with more sophisticated analysis of API surface.

3. **Cross-link intelligence**: Current implementation follows strict rules (docs→reference, kb→docs, blog→products). Could be enhanced to suggest more specific cross-links based on content similarity.

4. **SEO keywords**: Currently basic (product_slug, platform, section). Could be enhanced with claim-based keyword extraction.

## Integration Notes

**For Orchestrator (TC-300)**:
```python
from launch.workers.w4_ia_planner import execute_ia_planner

result = execute_ia_planner(
    run_dir=run_dir,
    run_config=run_config,
    llm_client=llm_client  # Optional
)

# result["status"] == "success"
# result["artifact_path"] == path to page_plan.json
# result["page_count"] == number of pages planned
# result["launch_tier"] == final tier (minimal/standard/rich)
```

**Output Schema** (page_plan.json):
```json
{
  "schema_version": "1.0",
  "product_slug": "3d",
  "launch_tier": "standard",
  "launch_tier_adjustments": [...],
  "inferred_product_type": "library",
  "pages": [
    {
      "section": "products",
      "slug": "overview",
      "output_path": "content/docs.aspose.org/3d/en/python/overview.md",
      "url_path": "/3d/python/overview/",
      "title": "Product Overview",
      "purpose": "Product overview and positioning",
      "template_variant": "standard",
      "required_headings": ["Overview", "Features", ...],
      "required_claim_ids": ["claim_001", ...],
      "required_snippet_tags": ["basic", "load"],
      "cross_links": [...],
      "seo_keywords": ["3d", "python", "overview"],
      "forbidden_topics": []
    }
  ]
}
```

## Conclusion

TC-430 implementation is complete and production-ready:
- ✅ All 30 tests passing (100%)
- ✅ Full spec compliance
- ✅ Deterministic outputs
- ✅ Event emission
- ✅ Schema validation
- ✅ Error handling
- ✅ Documentation complete

Ready for integration with orchestrator and downstream workers (W5 SectionWriter).
