---
id: TC-3811
title: "Enhanced SEO validation checks in Evaluate worker"
status: Done
priority: High
owner: agent
updated: "2026-03-07"
tags: [seo, evaluate, validation]
depends_on: [TC-3810]
allowed_paths:
  - plans/taskcards/TC-3811_seo_evaluate_checks.md
  - src/launcher/workers/evaluate/checks/seo.py
  - tests/unit/workers/test_seo_check.py
evidence_required:
  - test output
---

# Taskcard TC-3811 — Enhanced SEO Validation Checks

## Objective
Enhance the existing seo.py check in Evaluate worker with 10 new validation checks for seoTitle, canonical, robots, keyword presence, template description detection, and HTML entity detection.

## Scope
### In scope
- seoTitle presence and length checks
- seoTitle != title check
- Canonical URL presence and validity
- Robots directive presence
- Keyword count minimum
- Keyword body presence (density)
- Template description detection
- HTML entity detection in title/description

### Out of scope
- Config/allowlist wiring (TC-3812)

## Allowed paths
- plans/taskcards/TC-3811_seo_evaluate_checks.md
- src/launcher/workers/evaluate/checks/seo.py
- tests/unit/workers/test_seo_check.py

## Failure modes
### FM1: New checks break existing test expectations
**Detection**: Existing seo tests fail
**Resolution**: New checks are additive — existing checks untouched

### FM2: False positives on _index pages
**Detection**: Index pages flagged for missing seoTitle
**Resolution**: Skip seoTitle/canonical checks for _index slugs

### FM3: Content keyword scan too expensive
**Detection**: Slow evaluation on large pages
**Resolution**: Only scan first 2000 chars of content body

## Task-specific review checklist
1. [ ] seoTitle presence check (medium severity)
2. [ ] seoTitle length <=60 check
3. [ ] seoTitle != title check
4. [ ] Canonical URL presence and validity
5. [ ] Robots directive presence
6. [ ] Keyword count >=3
7. [ ] Template description detection
8. [ ] HTML entity detection
9. [ ] All existing tests still pass

## Acceptance checks
1. [ ] All existing tests pass (PYTHONHASHSEED=0)
2. [ ] New checks produce correct findings
