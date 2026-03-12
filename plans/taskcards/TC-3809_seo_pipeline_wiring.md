---
id: TC-3809
title: "SEO pipeline wiring (Understand + Planner + Prompts)"
status: Done
priority: High
owner: agent
updated: "2026-03-07"
tags: [seo, pipeline, wiring]
depends_on: [TC-3808]
allowed_paths:
  - plans/taskcards/TC-3809_seo_pipeline_wiring.md
  - src/launcher/models/understanding.py
  - src/launcher/workers/understand/worker.py
  - src/launcher/workers/planner/plan.py
  - src/launcher/workers/generate/section_prompt.py
  - src/launcher/prompts/section_writer.txt
evidence_required:
  - test output
---

# Taskcard TC-3809 — SEO Pipeline Wiring

## Objective
Wire keyword research into the pipeline: add KeywordResearchBundle to UnderstandingBundle, call research_keywords() in Understand worker, enhance Planner keyword generation, inject keywords into section prompts.

## Scope
### In scope
- Model extension (understanding.py)
- Understand worker integration
- Planner enhanced _generate_seo_keywords()
- Section prompt keyword injection
- Prompt template update

### Out of scope
- seo_metadata.py (TC-3810)
- Evaluate checks (TC-3811)

## Allowed paths
- plans/taskcards/TC-3809_seo_pipeline_wiring.md
- src/launcher/models/understanding.py
- src/launcher/workers/understand/worker.py
- src/launcher/workers/planner/plan.py
- src/launcher/workers/generate/section_prompt.py
- src/launcher/prompts/section_writer.txt

## Failure modes
### FM1: KeywordResearchBundle import breaks existing bundle deserialization
**Detection**: Tests loading existing understand_checkpoint.json fail
**Resolution**: Default to empty bundle (Field(default_factory=...))

### FM2: Missing pytrends in test env
**Detection**: ImportError
**Resolution**: keyword_research handles this gracefully; offline mode used in tests

### FM3: Prompt template format string breaks
**Detection**: KeyError on {seo_keywords_block}
**Resolution**: Provide fallback value in build_section_prompt()

## Task-specific review checklist
1. [x] UnderstandingBundle backward compatible (default empty)
2. [x] Understand worker calls research_keywords() with offline fallback
3. [x] Planner uses research bundle for enhanced keywords
4. [x] Section prompt injects keywords without breaking existing format
5. [x] Prompt template updated with SEO keywords section
6. [x] All existing tests still pass

## Acceptance checks
1. [x] All existing tests pass (PYTHONHASHSEED=0) — 1843 passed
2. [x] New keyword_research field serializes/deserializes correctly
