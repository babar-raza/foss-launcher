---
id: TC-3808
title: "5-source keyword research engine"
status: In-Progress
priority: High
owner: agent
updated: "2026-03-07"
tags: [seo, keywords, research]
depends_on: [TC-3806, TC-3807]
allowed_paths:
  - plans/taskcards/TC-3808_keyword_research_engine.md
  - src/launcher/shared/keyword_research.py
  - tests/unit/shared/test_keyword_research.py
evidence_required:
  - tests/unit/shared/test_keyword_research.py
---

# Taskcard TC-3808 — 5-source keyword research engine

## Objective

Create the keyword research engine that merges 5 sources (Google Trends, Google Suggest, Gemini, claim-derived, dev search patterns) into a KeywordResearchBundle. All external calls cached and rate-limited.

## Scope

### In scope
- `keyword_research.py` with `research_keywords()` entry point
- KeywordResearchBundle model
- 5 source functions, offline mode, graceful degradation

### Out of scope
- Pipeline integration (TC-3809)
- Planner/Generate changes (TC-3810+)

## Allowed paths
- plans/taskcards/TC-3808_keyword_research_engine.md
- src/launcher/shared/keyword_research.py
- tests/unit/shared/test_keyword_research.py

## Failure modes

### FM1: PyTrends not installed
**Detection**: ImportError on `from pytrends.request import TrendReq`
**Resolution**: Skip trends source, log warning, degrade to 4-source

### FM2: All external APIs fail
**Detection**: Empty results from trends, suggest, gemini
**Resolution**: Use claims + patterns only (always works)

### FM3: Offline mode
**Detection**: `offline=True` parameter
**Resolution**: Skip all external APIs, use cache + local only

## Task-specific review checklist
1. [ ] All 5 sources implemented
2. [ ] Offline mode skips external APIs
3. [ ] Graceful degradation chain works
4. [ ] Per-page keyword assignment implemented
5. [ ] Results deduplicated and capped
6. [ ] Tests pass with PYTHONHASHSEED=0

## Acceptance checks
1. [ ] All tests pass
2. [ ] No existing tests broken
