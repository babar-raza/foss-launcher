---
id: TC-4055
title: "Topic filter starvation — fallback + warning in _assign_claims()"
status: Done
priority: High
owner: "orchestrator"
updated: "2026-03-11"
tags: [crispy-growing-pebble, cgb-03, wave-1a]
depends_on: [TC-4031]
allowed_paths:
  - plans/taskcards/TC-4055_topic-filter-starvation.md
  - src/launcher/workers/planner/plan.py
  - tests/unit/workers/test_planner_per_module.py
evidence_required:
  - reports/TC-4055/evidence.md
---

# Taskcard TC-4055 — Topic Filter Starvation Fallback

## Objective

When `_TOPIC_KEYWORDS` filter is active and ALL candidate claims fail keyword matching,
`_assign_claims()` produces 0 claims silently. Add a WARNING log and a fallback to
eligible_kinds-only (no keyword filter) so pages always receive some claims.

## Scope

### In scope
- Add starvation detection after per-page claim assignment loop
- Log WARNING with slug, topic_category, candidate count
- Fallback: retry with eligible_kinds only, same max_claims cap
- Mark page with `_topic_filter_relaxed: true`

### Out of scope
- Removing the topic filter (it stays, just made resilient)

## Allowed paths

- plans/taskcards/TC-4055_topic-filter-starvation.md
- src/launcher/workers/planner/plan.py
- tests/unit/workers/test_planner_per_module.py

## Acceptance checks

- [ ] Starvation → WARNING logged
- [ ] Starvation → non-empty claim assignment via fallback
- [ ] Normal filter path → unchanged
- [ ] Unit test for starvation scenario passes
