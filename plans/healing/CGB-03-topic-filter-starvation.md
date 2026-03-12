---
id: CGB-03
title: "Topic filter starvation — add fallback + logging in _assign_claims()"
status: Resolved
priority: High
gap: FILTER-STARVATION
plan: crispy-growing-pebble
waves: [1A]
updated: "2026-03-11"
allowed_paths:
  - plans/healing/CGB-03-topic-filter-starvation.md
  - src/launcher/workers/planner/plan.py
  - tests/unit/workers/test_planner_per_module.py
  - plans/taskcards/TC-4045_topic-filter-starvation.md
---

# CGB-03 — Topic Filter Starvation Fallback

## Gap linkage

**Gap**: FILTER-STARVATION (HIGH)
**Origin**: Self-review of TC-4031 (`_TOPIC_KEYWORDS` claim filter)
**Effect**: When `_topic_words` is set and no candidate claim contains any keyword match,
`_assign_claims()` silently produces 0 claims for that page. The page is created with no
claims, the LLM generates hollow content, and the evaluate worker grades it D/F. There is
no log warning, no fallback, no operator visibility. DEFECT-2 persists in a different form.

## Role

Engineering — planner worker

## Scope

### Fix
In `_assign_claims()`, after the topic-filtered claim loop completes:
1. If `_topic_words` is set AND `assigned` is empty after filtering → log a WARNING
2. Apply a **graceful fallback**: relax keyword filter, retry with `eligible_kinds` only
   (same behavior as pre-TC-4031) and assign up to `max_claims` from the relaxed pool
3. Mark the page with `_topic_filter_relaxed: true` for downstream observability

### Allowed paths
- `src/launcher/workers/planner/plan.py`
- `tests/unit/workers/test_planner_per_module.py`
- `plans/taskcards/TC-4045_topic-filter-starvation.md` (required before coding)
- `plans/healing/CGB-03-topic-filter-starvation.md`

### Forbidden
- `specs/rulesets/ruleset.yaml` — topic_category additions are done (TC-4030)
- Any evaluate worker changes — starvation fix belongs in the planner

## Pre-requisite

Create `plans/taskcards/TC-4045_topic-filter-starvation.md` with status `In-Progress`
before any code changes (AG-002).

## Implementation steps

### Step 1: Locate the starvation point

In `plan.py`, find `_assign_claims()`. After the inner loop that uses `_topic_words`:
```python
# Current code (simplified):
for claim in candidates:
    if _topic_words and not any(w in claim.text.lower() for w in _topic_words):
        continue
    assigned.append(claim)
    if len(assigned) >= max_claims:
        break
```

### Step 2: Add starvation detection + fallback

```python
# After the filtered loop:
if _topic_words and not assigned and candidates:
    import logging as _logging
    _logging.getLogger(__name__).warning(
        "topic_filter_starvation page=%s topic=%s candidates=%d — relaxing to eligible_kinds only",
        page.get("slug", "?"), _page_topic, len(candidates),
    )
    # Relaxed pass: eligible_kinds only, no keyword filter
    for claim in candidates:
        assigned.append(claim)
        if len(assigned) >= max_claims:
            break
    page["_topic_filter_relaxed"] = True
```

### Step 3: Add unit test

In `tests/unit/workers/test_planner_per_module.py`, add a test that:
- Creates a page with `topic_category="formula_calculation"`
- Provides claims whose text contains no formula/calculate/compute/sum/function keywords
- Asserts: assigned is non-empty (fallback triggered), and a WARNING was logged

## Acceptance checks

- [ ] Starvation scenario (all claims fail keyword filter) produces a WARNING log entry
- [ ] Starvation scenario produces non-empty claim assignment (fallback to eligible_kinds)
- [ ] Normal scenario (claims match keywords) is unchanged — no regression
- [ ] `_topic_filter_relaxed: true` appears on the page dict when fallback fires
- [ ] New unit test passes (PYTHONHASHSEED=0)
- [ ] All existing planner tests pass

## Deliverables

1. Updated `src/launcher/workers/planner/plan.py` with fallback + logging
2. New test in `tests/unit/workers/test_planner_per_module.py`
3. Taskcard `plans/taskcards/TC-4045_topic-filter-starvation.md` (Done)

## Hard rules

- Taskcard TC-4045 must exist In-Progress before code edit (AG-002)
- Fallback must be conservative: eligible_kinds only, same max_claims cap
- Log at WARNING, not ERROR — starvation is recoverable
- Do not remove the topic filter; make it resilient

## Review dimensions

1. **Correctness**: Does fallback assign claims for all-mismatch scenarios?
2. **Observability**: Is the WARNING visible in structured logs with slug + topic?
3. **Non-regression**: Normal filtering unchanged?
4. **Test coverage**: At least 2 tests (normal path + starvation path)?

## Now (runbook)

```
1. Create TC-4045 → In-Progress
2. Read plan.py _assign_claims() (full function)
3. Insert starvation detection block after filtered loop
4. Add warning log + page["_topic_filter_relaxed"] = True
5. Add unit test for starvation scenario
6. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/ --tb=short -q
7. Mark TC-4045 Done; mark CGB-03 Resolved
```
