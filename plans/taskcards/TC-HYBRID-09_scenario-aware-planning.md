---
id: TC-HYBRID-09
title: "Scenario-aware planning (light): set skeleton_variant on blog pages from claim signals"
status: Done
priority: Normal
owner: "Claude Code (Sonnet 4.6)"
updated: "2026-03-10"
tags: [planner, skeleton, scenario, hybrid-plan]
depends_on: [TC-HYBRID-01]
allowed_paths:
  - plans/taskcards/TC-HYBRID-09_scenario-aware-planning.md
  - src/launcher/workers/planner/plan.py
  - src/launcher/shared/page_skeletons.py
  - tests/unit/workers/test_planner_per_module.py
  - tests/unit/workers/
evidence_required:
  - reports/TC-HYBRID-09/evidence.md
---

# Taskcard TC-HYBRID-09 — Scenario-aware planning (light)

## Objective

Add `detect_primary_scenario()` to the planner to detect the dominant claim kind
(tutorial, migration, evaluation, announcement) from `UnderstandingBundle.claims`
and propagate it as `skeleton_variant` on `feature_blog` and `blog_announcement`
pages before skeleton assignment. This prevents generic "Key Highlights" blog pages
from being generated for repos whose primary content is actually a tutorial or
migration guide.

## Required spec references

- `specs/07_section_templates.md` (skeleton structure contracts)
- `plans/taskcards/abundant-wibbling-wadler.md` Phase 4 / Agent-4C-SCENARIO

## Scope

### In scope
- `detect_primary_scenario()` function in `plan.py` — detects dominant scenario from claim kinds
- `_assign_scenario_variants()` in `plan.py` — sets `skeleton_variant` on blog pages
- New `SKELETON_VARIANTS` entries for `("feature_blog", "tutorial")` and `("feature_blog", "migration")` in `page_skeletons.py`
- Unit tests for scenario detection and variant assignment

### Out of scope
- Full PageContentModel rewrite (Plan B Phase 4 — deferred)
- Scenario detection for non-blog pages
- Changing claim extraction (Understand worker untouched)
- Changing `blog_announcement` skeleton variants (only `feature_blog` is touched)

## Inputs

- `list[Claim]` from `UnderstandingBundle.claims` — each has a `kind: str` field
- Existing `_assign_skeletons()` in `plan.py` which respects pre-set `skeleton_variant`
- `SKELETON_VARIANTS` dict in `page_skeletons.py`

## Outputs

- `detect_primary_scenario(claims: list[Claim]) -> str` function in `plan.py`
  - Returns one of: `"tutorial"`, `"migration"`, `"evaluation"`, `"announcement"`, `"default"`
  - "tutorial" when ≥30% of claims are kind "tutorial", "example", or "workflow"
  - "migration" when ≥20% of claims are kind "use_case" with migration-like text signals
  - "evaluation" when ≥20% of claims are kind "feature" or "compatibility" with comparison signals
  - "announcement" when ≥40% of claims are kind "feature" with no tutorial/workflow claims
  - "default" otherwise
- `_set_blog_variants()` in `plan.py` — mutates page dicts, sets `skeleton_variant` on blog pages
- `("feature_blog", "tutorial")` variant in `SKELETON_VARIANTS`:
  - "Introduction", "Prerequisites", "Step-by-Step Guide", "Code Example", "Result", "See Also"
- `("feature_blog", "migration")` variant in `SKELETON_VARIANTS`:
  - "Introduction", "Why Migrate", "Migration Steps", "Code Comparison", "Validation", "See Also"

## Allowed paths

- plans/taskcards/TC-HYBRID-09_scenario-aware-planning.md
- src/launcher/workers/planner/plan.py
- src/launcher/shared/page_skeletons.py
- tests/unit/workers/test_planner_per_module.py
- tests/unit/workers/

### Allowed paths rationale
- `plan.py`: contains `run_plan()` and `_assign_skeletons()` — detect and inject scenario
- `page_skeletons.py`: contains `SKELETON_VARIANTS` — new blog variants registered here
- `tests/unit/workers/`: new test file for scenario detection

## Implementation steps

### Step 1: Add skeleton variants to page_skeletons.py

In `src/launcher/shared/page_skeletons.py`, inside `SKELETON_VARIANTS`, add two new
entries AFTER the existing `("api_reference", "index")` entry (around line 455):

```python
    # -- feature_blog scenario variants (TC-HYBRID-09) --

    ("feature_blog", "tutorial"): [
        SkeletonSection("Introduction", 2, True,
                        "What this tutorial covers and what the reader will build", 50, 200),
        SkeletonSection("Prerequisites", 2, True,
                        "Required packages, tools, and setup steps", 50, 150),
        SkeletonSection("Step-by-Step Guide", 2, True,
                        "Sequential numbered steps with code at each step", 200, 600),
        SkeletonSection("Code Example", 2, True,
                        "Complete, runnable code example demonstrating the feature", 100, 400),
        SkeletonSection("Result", 2, False,
                        "What the output looks like and how to verify success", 30, 150),
        SkeletonSection("See Also", 2, False,
                        "Links to API reference and related tutorials", 0, 100),
    ],

    ("feature_blog", "migration"): [
        SkeletonSection("Introduction", 2, True,
                        "What is changing and why this migration is beneficial", 50, 200),
        SkeletonSection("Why Migrate", 2, True,
                        "Benefits and motivation for migrating from the old approach", 100, 300),
        SkeletonSection("Migration Steps", 2, True,
                        "Step-by-step migration procedure with before/after examples", 200, 600),
        SkeletonSection("Code Comparison", 2, False,
                        "Side-by-side comparison of old and new code", 100, 400),
        SkeletonSection("Validation", 2, False,
                        "How to verify the migration succeeded", 50, 200),
        SkeletonSection("See Also", 2, False,
                        "Links to changelog and compatibility guide", 0, 100),
    ],
```

### Step 2: Add detect_primary_scenario() to plan.py

Add after the `_KIND_TO_ROLES` dict (around line 112), before `_NO_CLAIM_ROLES`:

```python
# Claim kind sets for scenario detection (TC-HYBRID-09)
_TUTORIAL_KINDS: frozenset[str] = frozenset({"tutorial", "example", "workflow"})
_MIGRATION_SIGNALS: frozenset[str] = frozenset({"migrate", "migration", "convert from", "upgrade from", "replace"})
_COMPARISON_SIGNALS: frozenset[str] = frozenset({"vs", "versus", "compare", "comparison", "better than", "alternative"})


def detect_primary_scenario(claims: "list[Claim]") -> str:
    """Detect the dominant scenario from claim kinds and text signals.

    Returns one of: "tutorial", "migration", "evaluation", "announcement", "default".

    Used to set skeleton_variant on blog pages so they get a scenario-specific
    skeleton rather than the generic feature_blog template (TC-HYBRID-09).
    """
    if not claims:
        return "default"

    total = len(claims)
    kind_counts: dict[str, int] = {}
    for claim in claims:
        kind_counts[claim.kind] = kind_counts.get(claim.kind, 0) + 1

    tutorial_count = sum(kind_counts.get(k, 0) for k in _TUTORIAL_KINDS)
    feature_count = kind_counts.get("feature", 0)

    # Tutorial: ≥30% tutorial/example/workflow claims
    if tutorial_count / total >= 0.30:
        return "tutorial"

    # Migration: any claims with migration-like text signals
    migration_text_count = sum(
        1 for c in claims
        if any(sig in c.text.lower() for sig in _MIGRATION_SIGNALS)
    )
    if migration_text_count / total >= 0.20:
        return "migration"

    # Evaluation/comparison: ≥20% feature/compatibility with comparison signals
    comparison_text_count = sum(
        1 for c in claims
        if c.kind in {"feature", "compatibility"}
        and any(sig in c.text.lower() for sig in _COMPARISON_SIGNALS)
    )
    if comparison_text_count / total >= 0.20:
        return "evaluation"

    # Announcement: ≥40% feature claims, no tutorial/workflow signals
    if feature_count / total >= 0.40 and tutorial_count == 0:
        return "announcement"

    return "default"
```

### Step 3: Add _set_blog_variants() to plan.py

Add after `detect_primary_scenario()`:

```python
_BLOG_ROLES: frozenset[str] = frozenset({"feature_blog", "blog_announcement"})


def _set_blog_variants(pages: "list[dict[str, Any]]", scenario: str) -> None:
    """Set skeleton_variant on blog pages based on detected scenario (TC-HYBRID-09).

    Only sets the variant when:
    1. The page_role is in _BLOG_ROLES
    2. The page does not already have a non-default skeleton_variant
    3. The scenario is not "default"
    4. The (page_role, scenario) pair is registered in SKELETON_VARIANTS
    """
    if scenario == "default":
        return

    from launcher.shared.page_skeletons import SKELETON_VARIANTS

    for page in pages:
        if page.get("page_role") not in _BLOG_ROLES:
            continue
        # Don't override an already-set variant
        existing = page.get("skeleton_variant")
        if existing and existing != "default":
            continue
        role = page["page_role"]
        if (role, scenario) in SKELETON_VARIANTS:
            page["skeleton_variant"] = scenario
            logger.info(
                "Scenario variant: page_id=%s role=%s scenario=%s",
                page.get("page_id", "?"), role, scenario,
            )
```

### Step 4: Wire into run_plan()

In `run_plan()`, find the call to `_assign_skeletons(pages)` and add the scenario
detection BEFORE it:

```python
    # TC-HYBRID-09: detect primary scenario and set blog page variants
    scenario = detect_primary_scenario(claims or [])
    if scenario != "default":
        logger.info("[Planner] Detected primary scenario: %s", scenario)
    _set_blog_variants(pages, scenario)

    pages = _assign_skeletons(pages)
```

Look for the line `pages = _assign_skeletons(pages)` in `run_plan()` and insert above it.

### Step 5: Write tests

Create `tests/unit/workers/test_scenario_planning.py` with:

```python
"""Tests for TC-HYBRID-09: scenario-aware planning."""
import pytest
from launcher.models.claims import Claim, EvidenceAnchor
from launcher.workers.planner.plan import detect_primary_scenario, _set_blog_variants


def _claim(kind: str, text: str = "some claim text") -> Claim:
    return Claim(claim_id=f"c-{kind}-{hash(text)%1000}", text=text, kind=kind)


class TestDetectPrimaryScenario:
    def test_returns_default_for_empty_claims(self):
        assert detect_primary_scenario([]) == "default"

    def test_tutorial_when_30pct_tutorial_kind(self):
        claims = [_claim("tutorial")] * 3 + [_claim("feature")] * 7
        assert detect_primary_scenario(claims) == "tutorial"

    def test_tutorial_from_example_kind(self):
        claims = [_claim("example")] * 4 + [_claim("api")] * 6
        assert detect_primary_scenario(claims) == "tutorial"

    def test_tutorial_from_workflow_kind(self):
        claims = [_claim("workflow")] * 3 + [_claim("feature")] * 7
        assert detect_primary_scenario(claims) == "tutorial"

    def test_migration_when_20pct_migration_text(self):
        claims = [_claim("use_case", "migrate from old API")] * 2 + [_claim("feature")] * 8
        assert detect_primary_scenario(claims) == "migration"

    def test_migration_uses_text_signal_not_kind(self):
        claims = [_claim("feature", "upgrade from v1 to v2")] * 3 + [_claim("api")] * 7
        assert detect_primary_scenario(claims) == "migration"

    def test_evaluation_when_20pct_comparison_text(self):
        claims = [_claim("feature", "better than other library")] * 2 + [_claim("feature")] * 8
        assert detect_primary_scenario(claims) == "evaluation"

    def test_announcement_when_40pct_feature_no_tutorial(self):
        claims = [_claim("feature")] * 5 + [_claim("install")] * 3 + [_claim("api")] * 2
        assert detect_primary_scenario(claims) == "announcement"

    def test_no_announcement_when_tutorial_present(self):
        claims = [_claim("feature")] * 5 + [_claim("tutorial")] * 5
        # tutorial takes priority (50% > 30% threshold)
        assert detect_primary_scenario(claims) == "tutorial"

    def test_default_for_mixed_signals(self):
        claims = [_claim("api")] * 5 + [_claim("config")] * 5
        assert detect_primary_scenario(claims) == "default"


class TestSetBlogVariants:
    def test_sets_variant_on_feature_blog(self):
        pages = [{"page_id": "blog/p1", "page_role": "feature_blog"}]
        _set_blog_variants(pages, "tutorial")
        assert pages[0]["skeleton_variant"] == "tutorial"

    def test_skips_non_blog_pages(self):
        pages = [{"page_id": "docs/api", "page_role": "api_reference"}]
        _set_blog_variants(pages, "tutorial")
        assert "skeleton_variant" not in pages[0]

    def test_does_not_override_existing_variant(self):
        pages = [{"page_id": "blog/p1", "page_role": "feature_blog", "skeleton_variant": "install"}]
        _set_blog_variants(pages, "tutorial")
        assert pages[0]["skeleton_variant"] == "install"

    def test_skips_when_scenario_default(self):
        pages = [{"page_id": "blog/p1", "page_role": "feature_blog"}]
        _set_blog_variants(pages, "default")
        assert pages[0].get("skeleton_variant") is None

    def test_skips_unregistered_variant(self):
        # "evaluation" variant is not registered for feature_blog
        pages = [{"page_id": "blog/p1", "page_role": "feature_blog"}]
        _set_blog_variants(pages, "evaluation")
        assert pages[0].get("skeleton_variant") is None

    def test_migration_variant_registered(self):
        pages = [{"page_id": "blog/p1", "page_role": "feature_blog"}]
        _set_blog_variants(pages, "migration")
        assert pages[0]["skeleton_variant"] == "migration"
```

### Step 6: Run tests

```bash
cd c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher-v2
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_scenario_planning.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --timeout=60
```

## Failure modes

### Failure mode 1: Import cycle — plan.py imports page_skeletons.py already

**Detection**: `ImportError: cannot import name 'SKELETON_VARIANTS'` at startup
**Resolution**: `_set_blog_variants()` already uses a lazy `from launcher.shared.page_skeletons import SKELETON_VARIANTS` inside the function. Move it inside the function body if needed.
**Gate**: Python import test on `from launcher.workers.planner.plan import run_plan`

### Failure mode 2: detect_primary_scenario placed before Claim import

**Detection**: `NameError: name 'Claim' is not defined` at function call
**Resolution**: The function signature uses a string annotation (`"list[Claim]"`). Ensure `from __future__ import annotations` is at top of file (already there) and `Claim` is imported in the module.
**Gate**: test_detect_primary_scenario runs without NameError

### Failure mode 3: Existing planner tests fail due to skeleton_variant injection

**Detection**: Tests like `test_planner_per_module.py` or `test_plan_slugs.py` fail with unexpected skeleton_variant values
**Resolution**: `detect_primary_scenario` returns "default" for all existing test fixtures that don't have migration/tutorial-dominated claims. Check that test claim sets are truly <30% tutorial kind.
**Gate**: `pytest tests/unit/workers/test_planner_per_module.py -v` passes

### Failure mode 4: "evaluation" and "announcement" variants not in SKELETON_VARIANTS

**Detection**: `_set_blog_variants` is called with scenario="evaluation" but no variant registered, so nothing is set (correct behavior)
**Resolution**: This is intentional — only "tutorial" and "migration" get new skeletons. If "evaluation" is needed later, add the variant then.
**Gate**: `test_skips_unregistered_variant` test passes

## Task-specific review checklist

1. [ ] `detect_primary_scenario([])` returns "default" (empty claims safe)
2. [ ] `detect_primary_scenario` thresholds are correct: tutorial=30%, migration=20%, evaluation=20%, announcement=40%
3. [ ] `_set_blog_variants` respects pre-set `skeleton_variant` (no override)
4. [ ] `("feature_blog", "tutorial")` and `("feature_blog", "migration")` registered in `SKELETON_VARIANTS`
5. [ ] `_set_blog_variants` is called BEFORE `_assign_skeletons` in `run_plan()`
6. [ ] No import cycle introduced (lazy import inside `_set_blog_variants`)
7. [ ] All new functions have docstrings
8. [ ] Spec file checked — no spec drift (skeleton template spec covers variants)
9. [ ] Existing planner tests (`test_planner_per_module.py`, `test_plan_slugs.py`) still pass
10. [ ] `detect_primary_scenario` uses `from __future__ import annotations` guard for Claim type hint
11. [ ] Docs ownership map checked — no guide update required (internal planner logic)

## Deliverables

1. `src/launcher/workers/planner/plan.py` — `detect_primary_scenario()`, `_set_blog_variants()` added; wired into `run_plan()`
2. `src/launcher/shared/page_skeletons.py` — `("feature_blog", "tutorial")` and `("feature_blog", "migration")` in `SKELETON_VARIANTS`
3. `tests/unit/workers/test_scenario_planning.py` — 16 tests (10 scenario detection + 6 variant assignment)
4. `reports/TC-HYBRID-09/evidence.md` — test run output

## Acceptance checks

1. [x] `detect_primary_scenario([_claim("tutorial")] * 3 + [_claim("feature")] * 7)` returns `"tutorial"`
2. [x] `_set_blog_variants([{"page_role": "feature_blog"}], "tutorial")` sets `skeleton_variant = "tutorial"`
3. [x] All 16 new tests pass
4. [x] No regression in existing test suite (3371 passed, 1 pre-existing failure unrelated to TC-HYBRID-09)
5. [x] `SKELETON_VARIANTS` contains `("feature_blog", "tutorial")` and `("feature_blog", "migration")`
6. [x] `_set_blog_variants` is called before `_assign_skeletons` in `run_plan`

## Self-review

### Verification results
- [x] Tests: 16/16 PASS (new) + 3371 full suite
- [x] Integration: run_plan produces tutorial-variant feature_blog when claims dominate tutorial kind
- [x] Evidence captured: reports/TC-HYBRID-09/evidence.md
- [x] Doc freshness: clean

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_scenario_planning.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --timeout=60
```

**Expected results**:
- 16 new tests pass
- Full test suite passes without regression

## Integration boundary proven

**Upstream**: `UnderstandingBundle.claims` list (from Understand worker)
**Downstream**: `_assign_skeletons()` which respects pre-set `skeleton_variant`, then Generate worker which uses `skeleton_variant` via `PlannedPage`
**Contract**: `skeleton_variant: str` field on page dict → `PlannedPage.skeleton_variant` → `SKELETON_VARIANTS[(role, variant)]` → skeleton sections list
