---
id: CGB-02
title: "AG-002 retroactive taskcards for Wave 2D / 3C / 4F / 4G"
status: Resolved
priority: High
gap: AG-002-VIOLATION
plan: crispy-growing-pebble
waves: [2D, 3C, 4F, 4G]
updated: "2026-03-11"
allowed_paths:
  - plans/healing/CGB-02-ag002-retroactive-taskcards.md
  - plans/taskcards/TC-4041_wave2d-deterministic-titles.md
  - plans/taskcards/TC-4042_wave3c-fallback-paragraph.md
  - plans/taskcards/TC-4043_wave4f-editorial-grading.md
  - plans/taskcards/TC-4044_wave4g-editorial-go-criterion.md
---

# CGB-02 — AG-002 Retroactive Taskcards (Wave 2D / 3C / 4F / 4G)

## Gap linkage

**Gap**: AG-002-VIOLATION (HIGH)
**Origin**: Self-review of crispy-growing-pebble implementation
**Violation**: Four waves modified `src/launcher/**` without In-Progress taskcards:
- **Wave 2D**: `plan.py` — deterministic title formulas + `_TOPIC_LABELS` + `_ROLE_TITLE_TEMPLATES`
- **Wave 3C**: `fallback.py` — paragraph-from-claim instead of bare bullet list
- **Wave 4F**: `grader.py` — `EDITORIAL_CRITICAL_CHECKS` + `_is_editorial_critical()` + grade_page() update
- **Wave 4G**: `go_criteria.py` — 4th GO criterion (editorial-critical HIGH rate ≤ 15%)

**Risk**: Future audits will see undocumented protected-path writes. Per CLAUDE.md: "ZERO exceptions."

## Role

Governance / documentation — no code changes needed, taskcards only

## Scope

### Fix
Create four retroactive taskcards (one per wave). Each must:
- Document what was actually implemented (past tense)
- Set status to `Done` (work already shipped)
- Reference allowed_paths that match what was changed
- Include the evidence already present in the codebase

### Allowed paths
- `plans/taskcards/TC-4041_wave2d-deterministic-titles.md`
- `plans/taskcards/TC-4042_wave3c-fallback-paragraph.md`
- `plans/taskcards/TC-4043_wave4f-editorial-grading.md`
- `plans/taskcards/TC-4044_wave4g-editorial-go-criterion.md`
- `plans/healing/CGB-02-ag002-retroactive-taskcards.md`

### Forbidden
- Any `src/launcher/**` edits — this taskcard is documentation only

## Taskcard outlines

### TC-4041 — Wave 2D: Deterministic title formulas
```yaml
id: TC-4041
title: "Wave 2D: Deterministic title formulas in plan.py"
status: Done
allowed_paths:
  - src/launcher/workers/planner/plan.py
```
**What was done**: Added `_TOPIC_LABELS` (15 entries), `_ROLE_TITLE_TEMPLATES` (6 entries),
updated `_generate_evidence_aware_title()` to accept `product_name=` and `topic_category=`
kwargs, added deterministic title formulas keyed by role × topic_category.

### TC-4042 — Wave 3C: Fallback paragraph improvement
```yaml
id: TC-4042
title: "Wave 3C: Fallback paragraph-from-claim instead of bare list"
status: Done
allowed_paths:
  - src/launcher/workers/generate/fallback.py
  - tests/unit/workers/test_generate.py
  - tests/unit/workers/generate/test_fallback_deterministic.py
```
**What was done**: In `render_section_deterministic()`, for non-tabular sections with claims:
renders first 2 claims as a prose paragraph (`BlockIR(type=paragraph)`); remaining claims
(if any) as a bullet list. Two tests updated to match new output shape.

### TC-4043 — Wave 4F: Editorial-critical grading tier
```yaml
id: TC-4043
title: "Wave 4F: EDITORIAL_CRITICAL_CHECKS + Grade D on editorial HIGH"
status: Done
allowed_paths:
  - src/launcher/workers/evaluate/grader.py
```
**What was done**: Added `EDITORIAL_CRITICAL_CHECKS = frozenset({"route_consistency", "claim_coverage"})`,
added `_is_editorial_critical()`, updated `grade_page()` to track `editorial_high` count,
included `editorial_high > 0` in the Grade D condition.

### TC-4044 — Wave 4G: Editorial GO criterion
```yaml
id: TC-4044
title: "Wave 4G: 4th GO criterion — editorial-critical HIGH rate ≤ 15%"
status: Done
allowed_paths:
  - src/launcher/workers/evaluate/go_criteria.py
```
**What was done**: Added `_editorial_critical_rate()` helper, added 4th `GoCriteria` entry
("Editorial-critical HIGH rate", threshold ≤ 15%), imported `EDITORIAL_CRITICAL_CHECKS`
from grader.

## Acceptance checks

- [ ] TC-4041 exists at `plans/taskcards/TC-4041_wave2d-deterministic-titles.md` with status Done
- [ ] TC-4042 exists at `plans/taskcards/TC-4042_wave3c-fallback-paragraph.md` with status Done
- [ ] TC-4043 exists at `plans/taskcards/TC-4043_wave4f-editorial-grading.md` with status Done
- [ ] TC-4044 exists at `plans/taskcards/TC-4044_wave4g-editorial-go-criterion.md` with status Done
- [ ] Each taskcard has `allowed_paths` matching the files actually changed
- [ ] Each taskcard has `status: Done`

## Deliverables

1. `plans/taskcards/TC-4041_wave2d-deterministic-titles.md`
2. `plans/taskcards/TC-4042_wave3c-fallback-paragraph.md`
3. `plans/taskcards/TC-4043_wave4f-editorial-grading.md`
4. `plans/taskcards/TC-4044_wave4g-editorial-go-criterion.md`

## Hard rules

- Do NOT change any source code — this is documentation only
- Retroactive taskcards must be status `Done`, not `In-Progress`
- `allowed_paths` in each TC must match what was actually changed

## Now (runbook)

```
1. Read TC-000_TEMPLATE.md for structure reference
2. Create TC-4041 through TC-4044 from template
3. Fill each with past-tense documentation of what was implemented
4. Set status: Done on all four
5. Mark CGB-02 Resolved
```
