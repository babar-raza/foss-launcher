---
id: TC-4250
title: "Per-page evidence gate in Planner (skip/downgrade insufficient pages)"
status: In-Progress
priority: High
owner: "agent-B"
updated: "2026-03-12"
tags: [planner, page-evidence, sufficiency-gate]
depends_on: [TC-4249]
allowed_paths:
  - plans/taskcards/TC-4250_planner-page-evidence-gate.md
  - src/launcher/workers/planner/worker.py
  - src/launcher/workers/planner/plan.py
  - tests/unit/workers/test_planner_tier_gates.py
  - reports/agents/B_implementation/TC-4250/evidence.md
  - reports/agents/B_implementation/TC-4250/self_review.md
evidence_required:
  - reports/agents/B_implementation/TC-4250/evidence.md
---

# Taskcard TC-4250 — Per-page evidence gate in Planner

## Objective

Consume `bundle.page_evidence_index` (populated by TC-4249) in the Planner worker to:
1. Skip non-mandatory pages where `evidence_sufficient=False`
2. Log skipped/downgraded pages for inspection

This prevents the generate worker from producing pages it cannot support with real evidence.

## Required spec references

- `C:\Users\prora\.claude\plans\bright-kindling-eagle.md` (Section D Step 7 — Planner side)

## Scope

### In scope
- In `PlannerWorker.run()`: extract `page_evidence_index` from bundle, pass to `run_plan()`
- In `run_plan()`: accept `page_evidence_index` parameter; skip non-mandatory pages where `evidence_sufficient=False`
- Log which pages are skipped with reason
- Mandatory pages are NEVER skipped (but log a warning if evidence is insufficient)
- Tests

### Out of scope
- Modifying `PageEvidenceScore` model (TC-4249 owns it)
- Changing how scores are computed (TC-4249 owns it)
- Adding new page roles or changing the mandatory page taxonomy

## Inputs

- `bundle.page_evidence_index: dict[str, PageEvidenceScore]` (from TC-4249)
- `pages` list from `_enumerate_mandatory_pages()` and optional page generation

## Outputs

- Modified `worker.py` and `plan.py` with evidence-gated planning
- Test coverage

## Allowed paths

- plans/taskcards/TC-4250_planner-page-evidence-gate.md
- src/launcher/workers/planner/worker.py
- src/launcher/workers/planner/plan.py
- tests/unit/workers/test_planner_tier_gates.py
- reports/agents/B_implementation/TC-4250/evidence.md
- reports/agents/B_implementation/TC-4250/self_review.md

## Implementation steps

### Step 1: Read current `planner/worker.py` and `planner/plan.py`

Before implementing, read both files in full. Key areas:
- `PlannerWorker.run()` → how it calls `run_plan()`
- `run_plan()` signature in `plan.py` and how it enumerates pages
- How `mandatory` pages are marked in the page dict

### Step 2: Update `PlannerWorker.run()` in `worker.py`

In `PlannerWorker.run()`, extract `page_evidence_index` from the bundle:

```python
        # TC-4250: Per-page evidence gate — read index produced by TC-4249
        page_evidence_index = getattr(bundle, "page_evidence_index", {}) or {}

        pages, claim_assignment_index = run_plan(
            bundle.product, bundle.richness_tier, bundle.claims, bundle.snippets,
            product_evidence=bundle.product_evidence,
            keyword_bundle=getattr(bundle, "keyword_research", None),
            api_surface=bundle.api_surface,
            gemini_client=gemini_client,
            page_evidence_index=page_evidence_index,  # TC-4250
        )
```

### Step 3: Update `run_plan()` signature in `plan.py`

Add `page_evidence_index: dict = None` parameter to `run_plan()`:

```python
def run_plan(
    product,
    richness_tier,
    claims,
    snippets,
    *,
    product_evidence=None,
    keyword_bundle=None,
    api_surface=None,
    gemini_client=None,
    page_evidence_index: "dict | None" = None,   # TC-4250
) -> ...:
```

### Step 4: Apply the evidence gate in `run_plan()`

After all pages (mandatory + optional) have been collected, before returning, add filtering:

```python
    # TC-4250: Evidence gate — skip non-mandatory pages with evidence_sufficient=False
    if page_evidence_index:
        pre_filter_count = len(pages)
        filtered_pages = []
        for page in pages:
            page_role = page.get("page_role", "")
            is_mandatory = page.get("mandatory", False)
            score = page_evidence_index.get(page_role)
            if score is not None and not score.evidence_sufficient and not is_mandatory:
                logger.info(
                    "page_evidence_gate: skipping non-mandatory page role=%s slug=%s missing=%s",
                    page_role, page.get("slug", ""), getattr(score, "missing", []),
                )
                continue  # skip this page
            if score is not None and not score.evidence_sufficient and is_mandatory:
                logger.warning(
                    "page_evidence_gate: mandatory page role=%s has insufficient evidence: %s",
                    page_role, getattr(score, "missing", []),
                )
            filtered_pages.append(page)
        pages = filtered_pages
        skipped = pre_filter_count - len(pages)
        if skipped > 0:
            logger.info("page_evidence_gate: skipped %d non-mandatory pages", skipped)
```

**IMPORTANT**: Insert this block AFTER all page enumeration and claim assignment, but BEFORE the return statement. The exact insertion point depends on the current `run_plan()` structure — read the file carefully.

### Step 5: Add tests in `test_planner_tier_gates.py`

Read `tests/unit/workers/test_planner_tier_gates.py` first. Then add:

```python
class TestPageEvidenceGate:
    """TC-4250: Non-mandatory pages are skipped when evidence_sufficient=False."""

    def _make_score(self, sufficient: bool, missing: list = None):
        """Create a PageEvidenceScore-like object."""
        from types import SimpleNamespace
        return SimpleNamespace(
            evidence_sufficient=sufficient,
            missing=missing or [],
        )

    def test_non_mandatory_page_skipped_when_insufficient(self, ...):
        """A non-mandatory page with evidence_sufficient=False is excluded from plan."""
        # Call run_plan with a mock bundle where format_conversion has evidence_sufficient=False
        # Assert format_conversion pages are not in the resulting pages list
        ...

    def test_mandatory_page_kept_even_when_insufficient(self, ...):
        """A mandatory page is never skipped, even with evidence_sufficient=False."""
        ...

    def test_no_evidence_index_skips_nothing(self, ...):
        """When page_evidence_index is empty/None, all pages are kept unchanged."""
        ...
```

**Note**: If the existing test infrastructure in `test_planner_tier_gates.py` doesn't have suitable fixtures, use minimal mocks. The key invariant to test is:
1. Non-mandatory page with `evidence_sufficient=False` → excluded from `pages`
2. Mandatory page with `evidence_sufficient=False` → kept (with warning log)
3. No page_evidence_index → no filtering

## Failure modes

### Failure mode 1: Claim assignment happens AFTER the evidence gate removes pages

**Detection**: Pages that were assigned claims before the gate have `assigned_claims` references to removed pages, causing `claim_assignment_index` key errors.
**Resolution**: Apply the evidence gate BEFORE claim assignment, or ensure the claim assignment index only references pages still in the final `pages` list. The safest location is AFTER claim assignment (claims assigned to skipped pages are simply lost — acceptable since those pages are not generated). Read `run_plan()` carefully to find the right insertion point.
**Gate**: No KeyError when planner iterates `claim_assignment_index`.

### Failure mode 2: `page_evidence_index.get(page_role)` always returns None for all pages

**Detection**: No pages are ever skipped even with insufficient evidence.
**Resolution**: Verify that the `page_role` keys in the index match exactly the `page_role` values in the page dicts. The index uses roles like `"format_conversion"`, `"api_reference"` — confirm the page dicts use the same strings.
**Gate**: Test that a known role (`"format_conversion"`) is looked up correctly.

### Failure mode 3: `run_plan()` signature change breaks other callers

**Detection**: `TypeError: run_plan() got an unexpected keyword argument` in other tests.
**Resolution**: The new `page_evidence_index` parameter has a default value of `None` — all existing call sites pass nothing for it and remain backward-compatible.
**Gate**: All planner tests pass without changing their call sites.

## Task-specific review checklist

1. [ ] `page_evidence_index=None` default ensures all existing `run_plan()` callers unchanged
2. [ ] Mandatory pages (`mandatory=True`) are NEVER skipped by the gate
3. [ ] Skipped pages are logged at INFO level (not WARNING)
4. [ ] Mandatory pages with insufficient evidence logged at WARNING
5. [ ] Evidence gate is applied after page enumeration but uses the correct insertion point (no broken claim references)
6. [ ] Tests added covering the 3 key invariants
7. [ ] Docstrings updated for `run_plan()`

## Acceptance checks

1. [ ] Non-mandatory page with `evidence_sufficient=False` is excluded from returned `pages`
2. [ ] Mandatory page with `evidence_sufficient=False` is included (with WARNING log)
3. [ ] No existing planner tests break (run_plan signature is backward-compatible)

## E2E verification

```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_planner_tier_gates.py \
  tests/unit/orchestrator/test_graph_builder.py -x -v \
  --ignore=tests/unit/workers/test_plan_slug_integration.py \
  --ignore=tests/unit/workers/test_plan_slugs.py \
  --ignore=tests/unit/workers/test_scenario_planning.py \
  --ignore=tests/test_planner_per_module.py
```

## Integration boundary proven

**Upstream**: TC-4249 produces `bundle.page_evidence_index` in `UnderstandingBundle`
**Downstream**: Generate worker receives only pages with sufficient evidence
**Contract**: `run_plan()` accepts optional `page_evidence_index: dict | None`; mandatory pages always included
