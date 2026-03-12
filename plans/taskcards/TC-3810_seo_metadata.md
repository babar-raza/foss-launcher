---
id: TC-3810
title: "Post-generation SEO metadata optimization (Phase 1.5)"
status: Done
priority: High
owner: agent
updated: "2026-03-07"
tags: [seo, metadata, generate]
depends_on: [TC-3809]
allowed_paths:
  - plans/taskcards/TC-3810_seo_metadata.md
  - src/launcher/workers/generate/seo_metadata.py
  - src/launcher/workers/generate/worker.py
  - tests/unit/workers/generate/test_seo_metadata.py
evidence_required:
  - test output
---

# Taskcard TC-3810 — Post-generation SEO Metadata Optimization

## Objective
Create seo_metadata.py with post-generation SEO optimization (title sanitization, seoTitle, smart descriptions, canonical URLs, robots directives, keyword enhancement) and wire it as Phase 1.5 in Generate worker.

## Scope
### In scope
- seo_metadata.py: optimize_seo_metadata() public entry point
- Title sanitization (entity stripping via slug_engine)
- seoTitle generation (distinct from title, <=60 chars)
- Description generation (Gemini priority, heuristic fallback chain)
- Canonical URL construction
- Robots directive
- Keyword enhancement from claims + research bundle
- Metadata quality enforcement
- Generate worker Phase 1.5 integration

### Out of scope
- Evaluate checks enhancement (TC-3811)
- Config/allowlist wiring (TC-3812)

## Allowed paths
- plans/taskcards/TC-3810_seo_metadata.md
- src/launcher/workers/generate/seo_metadata.py
- src/launcher/workers/generate/worker.py
- tests/unit/workers/generate/test_seo_metadata.py

## Failure modes
### FM1: _strip_html_entities import breaks
**Detection**: ImportError on import
**Resolution**: Import from slug_engine.py directly

### FM2: PageIR frontmatter mutation side effects
**Detection**: Downstream rendering uses stale frontmatter
**Resolution**: Return new PageIR with updated frontmatter (immutable pattern)

### FM3: Description too short after all fallbacks
**Detection**: Empty string or <50 chars
**Resolution**: Template fallback always produces valid-length output

## Task-specific review checklist
1. [ ] Title sanitization strips HTML entities
2. [ ] seoTitle is distinct from title, <=60 chars
3. [ ] Description uses priority chain (Gemini > purpose > content > claim > template)
4. [ ] Canonical URL constructed correctly
5. [ ] Robots directive correct for index vs content pages
6. [ ] Keywords enhanced and capped at 8
7. [ ] Metadata quality enforced (no duplicates, length bounds)
8. [ ] Generate worker Phase 1.5 integrated between Phase 1 and Phase 2
9. [ ] All existing tests pass

## Acceptance checks
1. [ ] All existing tests pass (PYTHONHASHSEED=0)
2. [ ] New unit tests pass for seo_metadata.py
