---
id: TC-4218
title: "Plan: Fix _generate_evidence_aware_title — dedup + slug fallback + fragment rejection"
status: Done
priority: P0-Blocking
owner: "Agent-B"
updated: "2026-03-12"
tags: [plan, titles, publication-readiness]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4218_plan-title-dedup-fix.md
  - src/launcher/workers/planner/plan.py
  - tests/unit/workers/test_plan_slugs.py
  - reports/TC-4218/evidence.md
evidence_required:
  - reports/TC-4218/evidence.md
---

# Taskcard TC-4218 — Plan: Fix `_generate_evidence_aware_title` — dedup + slug fallback + fragment rejection

## Objective

`_generate_evidence_aware_title()` in `src/launcher/workers/planner/plan.py` (lines ~1608–1650) maps `topic_category` → label via `_TOPIC_LABELS` with no post-deduplication. Three title collisions exist in the 3d Python plan.json (`"Bounding boxes and transformations"` × 2, `"Import for 3D printing workflows"` × 2, `"5 example files demonstrating:"` × 2). The `howto_article` fallback also produces a description fragment (`"5 example files demonstrating:"` with trailing colon) as a page title. Fix: add post-deduplication using slug suffix, fix howto_article slug-derived fallback, add title validation rules, and add uniqueness assertion to planner self-review.

## Required spec references

- `specs/worker_generate.md` (Section: Plan output contract — page titles must be unique and publication-ready)
- `specs/schemas/plan_bundle.schema.json` (title field requirements)

## Scope

### In scope
- Post-deduplication of page titles using slug-derived suffix when collision detected
- Fix `howto_article` title fallback: derive from slug (e.g., `"load-3d-models-python"` → `"How to Load 3D Models with Python"`), never from description text
- Title validation: reject title ending with `:`, containing `"demonstrating"`, or shorter than 10 characters
- Add title uniqueness assertion to planner self-review alongside existing `page_id` uniqueness check — emit HIGH finding on collision

### Out of scope
- Changing `_TOPIC_LABELS` itself (the labels are correct; the issue is multiple pages sharing the same topic_category)
- Fixing A+B rate directly (affected pages score B, not C; this is a publication blocker)
- Any other planner logic outside title generation and self-review

## Inputs

- `src/launcher/workers/planner/plan.py` (lines 1608–1650: `_generate_evidence_aware_title`, `_TOPIC_LABELS`)
- `phase_store/3d/python/plan.json` (shows 3 title collisions + fragment title)

## Outputs

- Modified `src/launcher/workers/planner/plan.py`
- Modified `tests/unit/workers/test_plan_slugs.py` (or `test_planner_heal.py`) — new dedup + validation tests
- `reports/TC-4218/evidence.md`

## Allowed paths

- plans/taskcards/TC-4218_plan-title-dedup-fix.md
- src/launcher/workers/planner/plan.py
- tests/unit/workers/test_plan_slugs.py
- reports/TC-4218/evidence.md

### Allowed paths rationale
- `plan.py`: contains `_generate_evidence_aware_title` and planner self-review
- `test_plan_slugs.py`: existing test file for planner title/slug tests

## Implementation steps

### Step 1: Fix `howto_article` fallback

In `_generate_evidence_aware_title()`, the `howto_article` branch should derive title from slug when evidence is sparse. Example:

```python
if page_role == "howto_article":
    if topic_category in _TOPIC_LABELS:
        return f"How to {_TOPIC_LABELS[topic_category]} with {product_name}"
    # Slug-derived fallback — never use description text
    readable = slug.replace("-", " ").replace("_", " ").title()
    # Strip trailing platform/language suffix if present
    # e.g. "Load 3D Models Python" → "How to Load 3D Models with Python"
    if product_name:
        readable = readable.rstrip(" Python").rstrip(" Java").rstrip(" Csharp")
    return f"How to {readable} with {product_name}" if product_name else f"How to {readable}"
```

### Step 2: Add title validation

Add a `_validate_title(title: str) -> str` helper that:
1. Rejects title ending with `:` → strip trailing colon and whitespace
2. Rejects title containing `"demonstrating"` → raise ValueError (bug path, must not reach production)
3. Rejects title shorter than 10 characters → fall back to slug-derived title
Returns corrected title or raises on unfixable input.

### Step 3: Post-deduplication after all titles assigned

In the planner, after all page titles are generated, add a deduplication pass:

```python
from collections import Counter

title_counts = Counter(p.title for p in pages)
seen = {}
for page in pages:
    if title_counts[page.title] > 1:
        suffix = page.slug.split("/")[-1]  # e.g. "model-loading"
        suffix_readable = suffix.replace("-", " ").title()
        page.title = f"{page.title} — {suffix_readable}"
    # Validate after dedup
    page.title = _validate_title(page.title)
```

### Step 4: Add uniqueness assertion to planner self-review

In the planner self-review (lines ~190–200 in planner worker.py), alongside the existing `page_id` uniqueness check, add:

```python
titles = [p.title for p in pages]
if len(titles) != len(set(titles)):
    dupes = [t for t, c in Counter(titles).items() if c > 1]
    findings.append(PlannerFinding(
        severity="HIGH",
        check="title_uniqueness",
        message=f"Duplicate page titles: {dupes}",
    ))
```

### Step 5: Add tests

In `tests/unit/workers/test_plan_slugs.py`, add:
1. `test_howto_article_slug_derived_fallback` — no `topic_category`, asserts title derived from slug
2. `test_title_dedup_adds_suffix` — two pages same `topic_category`, asserts titles differ after dedup
3. `test_title_validation_trailing_colon` — title ending `:` corrected
4. `test_title_validation_min_length` — title < 10 chars gets slug fallback

## Failure modes

### Failure mode 1: Slug-derived title is generic (slug has no meaningful words)

**Detection**: Title like `"How to 3D with Python"` — slug was just `"3d-python"`.
**Resolution**: If slug-derived readable title is shorter than 20 chars after stripping platform suffix, append `product_name` full display name as context.
**Gate**: Title uniqueness assertion passes.

### Failure mode 2: Dedup suffix creates a new collision

**Detection**: Two pages with same base title AND same slug suffix.
**Resolution**: Use full slug path (not just last segment) as suffix. E.g., `"model-loading"` vs `"rendering"`.
**Gate**: Title uniqueness assertion PASS after dedup.

### Failure mode 3: Planner self-review emits HIGH finding but planner continues

**Detection**: Planner proceeds to generate despite HIGH title uniqueness finding.
**Resolution**: HIGH findings in planner self-review must block plan output OR surface as a gate failure. Verify that HIGH findings from self-review propagate to evaluate gate.
**Gate**: `evaluate.json` shows title_uniqueness HIGH finding when titles collide.

## Task-specific review checklist

1. [ ] `_generate_evidence_aware_title` howto_article branch uses slug-derived fallback, never description text
2. [ ] `_validate_title` rejects trailing colon and "demonstrating" substring
3. [ ] Post-deduplication pass fires after all titles assigned (not inside the generation loop)
4. [ ] Planner self-review uniqueness assertion emits HIGH finding on collision
5. [ ] All 3 original collisions would now produce distinct titles (verify with plan.json data)
6. [ ] 4 new unit tests added and passing
7. [ ] Docstrings updated for `_generate_evidence_aware_title` and `_validate_title`
8. [ ] Spec confirmed: planner output contract requires unique titles (or add to spec if missing)
9. [ ] Schema `description` for plan_bundle title field unchanged
10. [ ] `docs/README.md` ownership map checked — no trigger applies
11. [ ] No new `docs/guides/` files needed

## Deliverables

1. Modified `src/launcher/workers/planner/plan.py` with dedup + validation + self-review assertion
2. Modified `tests/unit/workers/test_plan_slugs.py` with 4 new tests
3. `reports/TC-4218/evidence.md` — test output + plan.json titles before/after

## Acceptance checks

1. [ ] `pytest tests/unit/workers/test_plan_slugs.py -v` — all tests PASS (new + existing)
2. [ ] Re-run plan on 3d Python: all 22 titles in `plan.json` are unique
3. [ ] No title in `plan.json` ends with `:`
4. [ ] `load-3d-models-python` and `save-3d-models-python` pages have distinct, human-readable titles
5. [ ] Planner self-review emits HIGH finding when two pages share a title (unit test proves)

## Self-review

### Verification results
- [x] Tests: 30/30 PASS (test_plan_slugs.py); 158/158 PASS (broader planner suite)
- [x] Validation: title uniqueness assertion PASS — emits HIGH finding on collision
- [x] Evidence captured: reports/TC-4218/evidence.md
- [x] All 3 original collision groups resolve to unique titles post-dedup

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_plan_slugs.py -v
```

**Expected results**:
- All existing slug/title tests pass
- 4 new dedup/validation tests pass

## Integration boundary proven

**Upstream**: Planner receives understand bundle (claims, API surface) → calls `_generate_evidence_aware_title()`
**Downstream**: `plan.json` titles consumed by Generate worker (section writer prompt) and by Publish (Hugo frontmatter `title:`)
**Contract**: `plan.json` page titles must be unique, ≥10 chars, no trailing colon, no description fragments
