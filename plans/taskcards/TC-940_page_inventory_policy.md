# TC-940: Page Inventory Policy (Mandatory vs Optional)

**Status**: ✅ DONE
**Priority**: HIGH
**Estimated Effort**: 2 hours
**Actual Effort**: 2 hours
**Agent**: Agent B
**Created**: 2026-02-03
**Completed**: 2026-02-03

---

## Problem Statement

The current page planning system generates minimal content inventory without a clear policy distinguishing mandatory pages (required for launch) from optional pages (selected based on evidence quality). This leads to:

1. Inconsistent page counts across different runs
2. No clear minimum viable launch criteria per section
3. Difficulty in understanding what content is essential vs enhancement

**Production Impact**: Launch readiness cannot be reliably assessed because there's no formal policy on what constitutes a complete section.

---

## Root Cause Analysis

**Current State**:
- `specs/06_page_planning.md` describes min/max quotas as "configurable" but doesn't mandate which specific pages are required
- `specs/rulesets/ruleset.v1.yaml` defines `min_pages` and `max_pages` per section but no guidance on WHICH pages those should be
- Page planner has no deterministic selection rule when evidence could support 10+ pages but max is 5

**Gap**: Missing formal policy for:
- Mandatory page types per section (e.g., products MUST have overview, docs MUST have getting-started)
- Optional page selection criteria when evidence exceeds max_pages
- Deterministic ranking/prioritization algorithm

---

## Solution Design

### 1. Mandatory Page Policy (Per Section)

**products** (min: 1, max: 10):
- **Mandatory**:
  - Overview/Landing page (slug: `overview` or `index`)
- **Optional** (select based on evidence, up to max_pages):
  - Features page
  - Quickstart page
  - Supported Environments page
  - Installation guide
  - Additional feature showcases

**docs** (min: 2, max: 50):
- **Mandatory**:
  - Getting Started guide (slug: `getting-started`)
  - At least one workflow-based how-to guide
- **Optional** (select based on workflow coverage and snippet quality):
  - Additional how-to guides (one per validated workflow)
  - Advanced tutorials
  - Migration guides

**reference** (min: 1, max: 100):
- **Mandatory**:
  - API Overview/Landing page (slug: `index` or `api-overview`)
- **Optional** (select based on API surface extraction):
  - Module/namespace pages (prioritize by usage in snippets)
  - Class/interface detail pages

**kb** (min: 3, max: 30):
- **Mandatory**:
  - FAQ page
  - Known Limitations page
  - Basic troubleshooting guide
- **Optional** (select based on claim coverage):
  - Performance optimization guides
  - Platform-specific deployment guides
  - Additional troubleshooting scenarios

**blog** (min: 1, max: 20):
- **Mandatory**:
  - Announcement post (product introduction)
- **Optional** (select based on workflow completeness):
  - Deep-dive technical posts
  - Release note style posts
  - Use case showcases

### 2. Optional Page Selection Algorithm (Deterministic)

When evidence supports more pages than `max_pages`, select using this priority ranking:

**Priority 1: Core Navigation Pages**
- Landing pages for each section
- Getting started guides

**Priority 2: Evidence Quality Score**
For each candidate page, calculate:
```
quality_score = (claim_count * 2) + (snippet_count * 3) + (api_symbol_count * 1)
```

**Priority 3: Workflow Coverage**
- Pages covering distinct workflows get higher priority
- Avoid duplicate workflow coverage

**Selection Process** (deterministic, stable):
1. Add all mandatory pages to page_plan
2. Collect all optional page candidates
3. Sort candidates by (priority_tier, quality_score DESC, slug ASC)
4. Select top N candidates where N = (max_pages - mandatory_count)
5. Record rejected candidates in telemetry with rejection reason

### 3. Schema Updates (Optional)

The current schema already supports `min_pages` and `max_pages`. No schema changes required, but we document that:
- `min_pages` refers to minimum MANDATORY pages for section viability
- `max_pages` is the hard limit including optional pages
- The gap between min and max is filled using the deterministic selection algorithm

---

## Implementation Checklist

- [x] Document mandatory page policy in `specs/06_page_planning.md`
- [x] Document optional page selection algorithm in `specs/06_page_planning.md`
- [x] Update `specs/07_section_templates.md` to reference mandatory vs optional page types
- [x] Verify `specs/schemas/ruleset.schema.json` supports current policy (no changes needed)
- [x] Verify `specs/rulesets/ruleset.v1.yaml` min/max values align with mandatory page counts

---

## Testing Strategy

**Validation Gates**:
- `validate_swarm_ready` confirms specs are consistent
- Manual review of updated specs for clarity

**Future Implementation Testing** (when planner is updated):
- Unit test: Planning with minimal evidence produces only mandatory pages
- Unit test: Planning with rich evidence applies deterministic selection up to max_pages
- Unit test: Two runs with identical evidence produce identical page_plan.json

---

## Acceptance Criteria

- [x] `specs/06_page_planning.md` includes "Mandatory vs Optional Page Policy" section
- [x] Each section (products/docs/reference/kb/blog) has documented mandatory page list
- [x] Deterministic optional page selection algorithm is specified
- [x] `specs/07_section_templates.md` references mandatory page types in template selection
- [x] `validate_swarm_ready` passes all gates
- [x] Taskcard evidence collected in `reports/agents/tc938_content_20260203_121910/TC-940/`

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Mandatory pages too strict for sparse repos | Blocker on minimal evidence | Launch_tier=minimal reduces mandatory page count |
| Optional selection algorithm not stable | Flaky tests, inconsistent output | Use deterministic sorting (no randomness) |
| Max_pages too low for rich repos | Missing important content | Allow max_pages override in RunConfig |

---

## Evidence and Artifacts

**Modified Files**:
- `specs/06_page_planning.md` - Added mandatory vs optional page policy section
- `specs/07_section_templates.md` - Clarified template variants for mandatory pages

**Validation**:
- `validate_swarm_ready` output showing all gates pass

**Stored in**: `c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\runs\tc938_content_20260203_121910\reports\TC-940\`

---

## Related Work

- **TC-938**: Absolute cross-subdomain links (cross-section navigation must be absolute URLs)
- **TC-935/936**: Deterministic validation_report (stable gate metrics)
- **Specs**: `specs/06_page_planning.md`, `specs/07_section_templates.md`

---

## Sign-off

**Completed by**: Agent B
**Reviewed by**: TBD
**Date**: 2026-02-03
