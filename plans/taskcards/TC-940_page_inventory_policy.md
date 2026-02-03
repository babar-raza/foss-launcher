---
id: TC-940
title: "Page Inventory Policy (Mandatory vs Optional)"
status: Done
owner: agent_b
created: "2026-02-03"
updated: "2026-02-03"
spec_ref: 403ca6d5a19cbf1ad5aec8da58008aa8ac99a5d3
ruleset_version: v1
templates_version: v1
tags: [finalization, content-quality, page-planning]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-940_page_inventory_policy.md
  - specs/06_page_planning.md
  - specs/07_section_templates.md
  - specs/rulesets/ruleset.v1.yaml
  - specs/schemas/ruleset.schema.json
  - runs/tc938_content_20260203_121910/**
  - reports/agents/**/TC-940/**
evidence_required:
  - specs/06_page_planning.md
  - specs/07_section_templates.md
  - runs/tc938_content_20260203_121910/reports/TC-940/**
---

# Taskcard TC-940 — Page Inventory Policy (Mandatory vs Optional)

## Objective

Define and document a formal policy distinguishing mandatory pages (required for launch) from optional pages (selected based on evidence quality) to enable consistent page planning and reliable launch readiness assessment.

## Required spec references

- specs/06_page_planning.md
- specs/07_section_templates.md
- specs/rulesets/ruleset.v1.yaml
- specs/schemas/ruleset.schema.json

## Allowed paths

- plans/taskcards/TC-940_page_inventory_policy.md
- specs/06_page_planning.md
- specs/07_section_templates.md
- specs/rulesets/ruleset.v1.yaml
- specs/schemas/ruleset.schema.json
- runs/tc938_content_20260203_121910/**
- reports/agents/**/TC-940/**

## Problem Statement

The current page planning system generates minimal content inventory without a clear policy distinguishing mandatory pages (required for launch) from optional pages (selected based on evidence quality). This leads to:

1. Inconsistent page counts across different runs
2. No clear minimum viable launch criteria per section
3. Difficulty in understanding what content is essential vs enhancement

**Production Impact**: Launch readiness cannot be reliably assessed because there's no formal policy on what constitutes a complete section.

## Scope

**In Scope**:
- Document mandatory page policy per section (products/docs/reference/kb/blog)
- Document optional page selection algorithm (deterministic)
- Update specs/06_page_planning.md with policy
- Update specs/07_section_templates.md to reference mandatory page types
- Verify ruleset configuration aligns with policy

**Out of Scope**:
- Code implementation (documentation only)
- Changing min/max page quotas in ruleset
- Template content modifications

## Inputs

- Current specs/06_page_planning.md (existing page planning contract)
- Current specs/07_section_templates.md (existing template specifications)
- Current specs/rulesets/ruleset.v1.yaml (min/max quotas)

## Outputs

- Updated specs/06_page_planning.md with "Mandatory vs Optional Page Policy" section
- Updated specs/07_section_templates.md referencing mandatory page types
- Validation report showing all gates pass
- Evidence package in reports/agents/tc938_content_20260203_121910/TC-940/

## Root Cause Analysis

**Current State**:
- `specs/06_page_planning.md` describes min/max quotas as "configurable" but doesn't mandate which specific pages are required
- `specs/rulesets/ruleset.v1.yaml` defines `min_pages` and `max_pages` per section but no guidance on WHICH pages those should be
- Page planner has no deterministic selection rule when evidence could support 10+ pages but max is 5

**Gap**: Missing formal policy for:
- Mandatory page types per section (e.g., products MUST have overview, docs MUST have getting-started)
- Optional page selection criteria when evidence exceeds max_pages
- Deterministic ranking/prioritization algorithm

## Implementation steps

1. Document mandatory page policy per section in specs/06_page_planning.md
2. Document optional page selection algorithm in specs/06_page_planning.md
3. Update specs/07_section_templates.md to reference mandatory vs optional page types
4. Verify specs/schemas/ruleset.schema.json supports current policy (no changes needed)
5. Verify specs/rulesets/ruleset.v1.yaml min/max values align with mandatory page counts
6. Run validation: `validate_swarm_ready.py`
7. Collect evidence in reports/agents/tc938_content_20260203_121910/TC-940/

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

## Deliverables

- specs/06_page_planning.md - Updated with "Mandatory vs Optional Page Policy" section
- specs/07_section_templates.md - Updated to reference mandatory page types
- Validation report showing all gates pass
- Evidence package in reports/agents/tc938_content_20260203_121910/TC-940/

## Acceptance checks

- specs/06_page_planning.md includes "Mandatory vs Optional Page Policy" section
- Each section (products/docs/reference/kb/blog) has documented mandatory page list
- Deterministic optional page selection algorithm is specified
- specs/07_section_templates.md references mandatory page types in template selection
- validate_swarm_ready passes all gates
- Taskcard evidence collected in reports/agents/tc938_content_20260203_121910/TC-940/

## Self-review

**Documentation Quality**:
- [x] Mandatory page policy clear for each section
- [x] Optional page selection algorithm deterministic and stable
- [x] Policy aligns with existing ruleset quotas
- [x] Template specifications updated consistently

**Completeness**:
- [x] All 5 sections (products/docs/reference/kb/blog) covered
- [x] Both mandatory and optional pages defined
- [x] Selection algorithm fully specified
- [x] All required spec files updated

**Accuracy**:
- [x] Policy reflects actual content generation needs
- [x] Algorithm ensures deterministic output
- [x] No conflicts with existing specs
- [x] Validation gates passing

## Testing Strategy

**Validation Gates**:
- `validate_swarm_ready` confirms specs are consistent
- Manual review of updated specs for clarity

**Future Implementation Testing** (when planner is updated):
- Unit test: Planning with minimal evidence produces only mandatory pages
- Unit test: Planning with rich evidence applies deterministic selection up to max_pages
- Unit test: Two runs with identical evidence produce identical page_plan.json

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Mandatory pages too strict for sparse repos | Blocker on minimal evidence | Launch_tier=minimal reduces mandatory page count |
| Optional selection algorithm not stable | Flaky tests, inconsistent output | Use deterministic sorting (no randomness) |
| Max_pages too low for rich repos | Missing important content | Allow max_pages override in RunConfig |

## E2E verification

**Expected artifacts**:
- specs/06_page_planning.md with "Mandatory vs Optional Page Policy" section
- specs/07_section_templates.md referencing mandatory page types
- runs/tc938_content_20260203_121910/reports/TC-940/ with evidence

**Verification commands**:
```bash
# Verify policy documented
grep -i "mandatory.*optional.*page.*policy" specs/06_page_planning.md && echo "PASS: Policy documented"

# Verify section coverage
grep -E "(products|docs|reference|kb|blog).*mandatory" specs/06_page_planning.md && echo "PASS: All sections covered"

# Verify template spec updated
grep -i "mandatory" specs/07_section_templates.md && echo "PASS: Template spec updated"

# Verify validation passes
.venv/Scripts/python.exe tools/validate_swarm_ready.py 2>&1 | grep -E "(Gate A2|Gate B|Gate P)" | grep PASS && echo "PASS: Gates passing"

# Verify evidence collected
test -d runs/tc938_content_20260203_121910/reports/TC-940 && echo "PASS: Evidence collected"
```

## Integration boundary proven

**Upstream integration**:
- Reads existing specs/06_page_planning.md for page planning rules
- Reads existing specs/07_section_templates.md for template specifications
- Uses existing specs/rulesets/ruleset.v1.yaml for min/max quotas
- References existing specs/schemas/ruleset.schema.json for schema validation

**Downstream integration**:
- Future page planner implementations will use mandatory page policy
- Launch readiness checks will verify mandatory pages present
- Optional page selection will follow deterministic algorithm
- All existing tests continue to pass

**Verification**:
- All existing tests pass (pytest)
- TC-940 taskcard validates against Gate A2 and Gate B schemas
- No conflicts with existing specs
- validate_swarm_ready passes all gates

## Related Work

- **TC-938**: Absolute cross-subdomain links (cross-section navigation must be absolute URLs)
- **TC-935/936**: Deterministic validation_report (stable gate metrics)
- **Specs**: `specs/06_page_planning.md`, `specs/07_section_templates.md`

## Sign-off

**Completed by**: Agent B
**Reviewed by**: TBD
**Date**: 2026-02-03
**Status**: ✅ DONE
