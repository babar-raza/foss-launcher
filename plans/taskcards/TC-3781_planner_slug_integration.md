---
id: TC-3781
title: "Planner Slug Integration — Evidence-Aware"
status: Done
priority: High
owner: Agent-B
updated: "2026-03-07"
tags: [phase-3, planner, slug]
depends_on: [TC-3779, TC-3780]
allowed_paths:
  - plans/taskcards/TC-3781_planner_slug_integration.md
  - src/launcher/workers/planner/plan.py
  - src/launcher/workers/planner/worker.py
  - specs/rulesets/ruleset.yaml
  - tests/unit/workers/test_plan_slug_integration.py
  - reports/agents/B/TC-3781/
evidence_required:
  - reports/agents/B/TC-3781/evidence.md
---

# Taskcard TC-3781 — Planner Slug Integration — Evidence-Aware

## Objective

Replace the Planner's static and generic slug generation with evidence-aware slugs from `slug_engine.py`. This eliminates meaningless slugs like `feature_showcase-1` by deriving slugs from product evidence (claims, workflows, platform keywords), with an optional LLM refinement pass and algorithmic fallback.

## Required spec references

- `specs/rulesets/ruleset.yaml` (Section: page definitions with slug templates — will be extended with `slug_strategy` fields)
- `specs/site_model_hugo.md` (Section: Hugo URL structure, permalink conventions, slug format constraints)

## Scope

### In scope

- Update `run_plan()` signature to accept `ProductEvidence` and optional `llm_client`
- Replace mandatory KB how-to slugs with evidence-aware slugs via `derive_evidence_aware_slug()`
- Replace blog slugs with evidence-enriched slugs via `score_blog_workflow()` + `derive_blog_evidence_slug()`
- Replace optional page slugs (`f"{kind}-{i+1}"`) with semantic/evidence-derived slugs using a new `_derive_optional_slug()` helper
- Add LLM refinement pass via `refine_slugs_batch()` with algorithmic fallback
- Update `specs/rulesets/ruleset.yaml` to add `slug_strategy` fields on relevant page definitions
- Update `src/launcher/workers/planner/worker.py` to pass `product_evidence` through to `run_plan()`

### Out of scope

- ProductEvidence extraction — handled by TC-3779
- `slug_engine.py` creation — handled by TC-3780
- Changes to workers other than Planner (Understand, Generate, Evaluate, Publish)

## Inputs

- `UnderstandingBundle.product_evidence` (from TC-3779)
- `slug_engine.py` functions: `derive_evidence_aware_slug()`, `score_blog_workflow()`, `derive_blog_evidence_slug()`, `refine_slugs_batch()` (from TC-3780)
- `specs/rulesets/ruleset.yaml` (existing page definitions)

## Outputs

- Modified `src/launcher/workers/planner/plan.py` with evidence-aware slug derivation
- Modified `src/launcher/workers/planner/worker.py` with product_evidence pass-through
- Modified `specs/rulesets/ruleset.yaml` with `slug_strategy` fields
- New `tests/unit/workers/test_plan_slug_integration.py` with integration tests

## Allowed paths

- `plans/taskcards/TC-3781_planner_slug_integration.md`
- `src/launcher/workers/planner/plan.py`
- `src/launcher/workers/planner/worker.py`
- `specs/rulesets/ruleset.yaml`
- `tests/unit/workers/test_plan_slug_integration.py`
- `reports/agents/B/TC-3781/`

### Allowed paths rationale

- `plan.py`: Core file where slug generation logic lives; must be updated to call slug_engine functions
- `worker.py`: Planner worker entry point; must thread product_evidence from the understanding bundle into `run_plan()`
- `ruleset.yaml`: Page definitions need `slug_strategy` metadata so the planner knows which derivation method to use per page kind
- `test_plan_slug_integration.py`: New test file to verify evidence-aware slug integration end-to-end
- `reports/agents/B/TC-3781/`: Evidence capture directory for acceptance proof

## Implementation steps

### Step 1: Update `run_plan()` signature

Add `product_evidence: Optional[ProductEvidence] = None` and `llm_client: Optional[Any] = None` keyword arguments to `run_plan()`. When `product_evidence` is None, all slug derivation falls back to existing behavior (backward compatibility).

### Step 2: Replace KB how-to slugs with evidence-aware slugs

In `_enumerate_mandatory_pages()` (or equivalent), for KB entries whose `topic_category` is populated, call `derive_evidence_aware_slug(family, platform, topic_category, product_evidence)` instead of the current static slug construction. Pass the family keyword and platform from the run config.

### Step 3: Replace blog slugs with evidence-enriched slugs

In the blog section of plan construction, call `score_blog_workflow(product_evidence)` to rank workflows, then `derive_blog_evidence_slug(top_workflow, family, platform)` to produce a meaningful blog slug instead of a generic one.

### Step 4: Add `_derive_optional_slug()` helper

Create a private helper `_derive_optional_slug(kind: str, index: int, product_evidence: Optional[ProductEvidence], family: str)` that:
1. Filters `product_evidence.claims` to those relevant to the page `kind`
2. Picks the top claim by confidence score
3. Derives a slug from the claim's subject + family keyword
4. Falls back to `f"{kind}-{family_keyword}-{index+1}"` if no claims match

### Step 5: Replace optional page slug pattern

In `_apply_optional_expansion()` (or equivalent), replace `f"{kind}-{i+1}"` with a call to `_derive_optional_slug()`. This ensures optional pages like `feature_showcase` get meaningful names.

### Step 6: Add LLM refinement pass

After `_build_frontmatter()` and before `_validate_plan()`, add an optional call to `refine_slugs_batch(slug_list, llm_client)` when `llm_client` is not None. Apply a post-refinement safety check: if any refined slug fails URL-safety validation (lowercase alphanumeric + hyphens, no trailing hyphens, max 80 chars), keep the original algorithmic slug.

### Step 7: Update `specs/rulesets/ruleset.yaml`

Add `slug_strategy` field to relevant page definitions:
- KB how-to entries: `slug_strategy: evidence_aware`
- Blog entries: `slug_strategy: blog_workflow`
- Optional pages: `slug_strategy: claim_derived`
- Static pages (overview, getting-started): `slug_strategy: static` (no change)

### Step 8: Update `worker.py` to pass product_evidence

In the planner worker's main entry point, extract `bundle.product_evidence` from the understanding bundle and pass it as a keyword argument to `run_plan()`. Also pass `llm_client` if available in the worker context.

### Step 9: Write integration tests

Create `tests/unit/workers/test_plan_slug_integration.py` with tests for:
- KB how-to slug derivation with evidence produces family+platform+topic slug
- Blog slug derivation with scored workflow produces meaningful slug
- Optional page slug derivation replaces `feature_showcase-1` pattern
- LLM refinement fallback when client is None
- LLM refinement fallback when refined slug fails safety check
- Backward compatibility: `product_evidence=None` produces same slugs as before
- Collision detection in `_validate_plan()` catches duplicate evidence-derived slugs

## Failure modes

### Failure mode 1: Evidence-aware slug produces permalink collision

**Detection**: `_validate_plan()` logs a permalink collision error when two pages resolve to the same slug (e.g., two how-to pages both derive `convert-pdf-python`)
**Resolution**: On collision, append a disambiguating suffix from the claim's secondary keyword or a numeric counter. Re-validate after disambiguation.
**Gate**: Permalink uniqueness gate (G6)

### Failure mode 2: Optional slug derivation finds no matching claims

**Detection**: `_derive_optional_slug()` receives an empty claim list after filtering by page kind; logs a warning
**Resolution**: Fall back to `f"{kind}-{family_keyword}-{i+1}"` which preserves current behavior but includes the family keyword for minimal semantic content
**Gate**: Plan completeness validation (all required pages present with valid slugs)

### Failure mode 3: LLM refinement corrupts good algorithmic slugs

**Detection**: Post-refinement safety check detects non-URL-safe characters, excessive length (>80 chars), empty string, or slug that lost the family keyword
**Resolution**: Discard the refined slug and keep the original algorithmic slug. Log the rejection reason for debugging. The LLM pass is strictly optional and must never degrade quality.
**Gate**: URL-safety validation in `_validate_plan()`

## Task-specific review checklist

1. [ ] KB how-to slugs include family keyword and platform (e.g., `convert-pdf-cells-python` not `convert-pdf`)
2. [ ] Blog slug derives from top-scored workflow via `score_blog_workflow()`
3. [ ] Optional pages have meaningful slugs — no `feature_showcase-1` or `{kind}-{i+1}` pattern remains
4. [ ] LLM refinement has algorithmic fallback — works identically when `llm_client=None`
5. [ ] Existing planner tests still pass — backward compatible when `product_evidence=None`
6. [ ] `_validate_plan()` catches slug collisions introduced by evidence-derived slugs
7. [ ] `ruleset.yaml` has `slug_strategy` field on KB how-to, blog, and optional page entries
8. [ ] Post-refinement safety check rejects non-URL-safe slugs and keeps originals

## Deliverables

1. Modified `src/launcher/workers/planner/plan.py` with evidence-aware slug derivation
2. Modified `src/launcher/workers/planner/worker.py` with product_evidence pass-through
3. Modified `specs/rulesets/ruleset.yaml` with `slug_strategy` fields
4. New `tests/unit/workers/test_plan_slug_integration.py` with integration tests
5. Evidence bundle at `reports/agents/B/TC-3781/evidence.md`

## Acceptance checks

1. [ ] Planner tests pass: `.venv/Scripts/python.exe -m pytest tests/ -k plan -v`
2. [ ] New integration test demonstrates evidence-aware slug for KB how-to (slug contains family keyword + topic)
3. [ ] Optional page slug test confirms no `feature_showcase-1` pattern in output
4. [ ] Full test suite passes: `.venv/Scripts/python.exe -m pytest tests/ -v` with PYTHONHASHSEED=0
5. [ ] `ruleset.yaml` validates against its schema (if schema exists)

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: permalink uniqueness gate PASS
- [ ] Evidence captured: reports/agents/B/TC-3781/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_plan_slug_integration.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -k plan -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -v
```

**Expected results**:
- All planner tests pass including new slug integration tests
- Evidence-aware slugs contain family keyword + platform + topic (e.g., `convert-pdf-cells-python`)
- No `feature_showcase-1` or `{kind}-{i+1}` slugs in test output
- Full suite green with zero regressions

## Integration boundary proven

**Upstream**: TC-3779 (ProductEvidence extraction in Understand worker) provides `UnderstandingBundle.product_evidence`; TC-3780 (slug_engine.py) provides derivation functions
**Downstream**: Generate worker (W3) consumes the plan's page entries with their slugs to produce content at the correct URL paths; Publish worker (W5) uses slugs for final file paths
**Contract**: `PageEntry.slug` field (string, URL-safe, unique within plan) — validated by `_validate_plan()` permalink check and pydantic model constraints on `PageEntry`
