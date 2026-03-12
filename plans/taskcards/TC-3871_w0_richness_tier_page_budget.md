---
id: TC-3871
title: "Wave 0: Richness Tier Multi-Signal Classification + Mandatory/Optional Page Budget"
status: In-Progress
priority: High
owner: "Agent-B"
updated: "2026-03-09"
tags: [wave-0, planner, tier, page-budget]
depends_on: [TC-3870]
allowed_paths:
  - plans/taskcards/TC-3871_w0_richness_tier_page_budget.md
  - src/launcher/workers/planner/plan.py
  - tests/planner/test_plan.py
  - reports/TC-3871/evidence.md
evidence_required:
  - reports/TC-3871/evidence.md
---

# Taskcard TC-3871 — Wave 0: Richness Tier Multi-Signal + Page Budget Enforcement

## Objective

Upgrade richness tier classification to use API surface count and snippet quality in addition
to doc file counts. Enforce that Tier C repos only generate mandatory pages, preventing
thin-content generation failures on lean repos.

## Required spec references

- `specs/worker_understand.md` (Section: richness tier definition)
- `specs/templates_rulesets.md` (Section: mandatory/optional ruleset binding)
- `specs/worker_generate.md` (Section: page plan, tier budgets)

## Scope

### In scope
- Read + audit current richness tier scoring in `plan.py`
- Add composite scoring: `tier_score = doc_score + api_surface_score + snippet_score`
- Add tier-gated page inclusion BEFORE claim assignment
- Hard rule: page excluded when `available_claims_for_role < MIN_CLAIMS_PER_ROLE`
- Tests for new tier scoring + page budget enforcement

### Out of scope
- Changes to the claim extraction logic (TC-3870/Wave 0)
- Changes to the generation prompts (TC-3876/Wave 2)
- Changes to the evaluation grading thresholds

## Inputs

- `src/launcher/workers/planner/plan.py` — current tier logic + `_prune_thin_pages`
- `specs/rulesets/ruleset.yaml` — mandatory/optional page sets
- `src/launcher/models/plan.py` — PlannedPage + PlanBundle models

## Outputs

- Updated `plan.py` with composite tier scoring + tier-gated page inclusion
- `reports/TC-3871/evidence.md` — changes made + test results

## Allowed paths

- plans/taskcards/TC-3871_w0_richness_tier_page_budget.md
- src/launcher/workers/planner/plan.py
- tests/planner/test_plan.py
- reports/TC-3871/evidence.md

### Allowed paths rationale
plan.py contains both the tier scoring logic and the page plan builder.

## Implementation steps

### Step 1: Audit current tier scoring

Read `plan.py` — find `_classify_richness_tier()` or equivalent function.
Document current signals used (doc count, file count, etc.).
Note: if tier scoring already uses API surface count, document and skip Step 2.

### Step 2: Upgrade tier scoring to composite

Add to tier scoring:
```python
# API surface signal (from understand worker output)
api_surface_score = min(3.0, len(plan_input.public_classes) / 10)
# Snippet quality signal
snippet_score = min(2.0, len([s for s in plan_input.snippets if s.source_type == "extracted"]) / 5)
# Composite
tier_score = existing_doc_score + api_surface_score + snippet_score
# Thresholds
if tier_score >= 5.0: tier = "A"
elif tier_score >= 2.5: tier = "B"
else: tier = "C"
```

Only add if NOT already implemented.

### Step 3: Tier-gated page inclusion

In `_build_page_plan` (or equivalent function that assembles the page list):
BEFORE claim assignment, apply:
```python
MIN_CLAIMS_PER_ROLE = {
    "landing": 3, "workflow_page": 5, "howto_article": 2,
    "installation": 1, "faq": 3, "api_reference": 2,
    # default for all others
    "_default": 2,
}
# Tier C: mandatory pages only (from ruleset.yaml mandatory set)
# Tier B: mandatory + 1 optional policy
# Tier A: mandatory + all eligible optional policies
```

Log dropped optional pages: `logger.info("Tier C: optional page skipped", page_role=role, reason="lean repo")`

### Step 4: Tests

Add/update `tests/planner/test_plan.py`:
- Test Tier C repo gets only mandatory pages
- Test Tier A repo with large API surface scores Tier A despite sparse docs
- Test page excluded when claim count < MIN_CLAIMS_PER_ROLE

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/planner/ -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --tb=short
```

## Failure modes

### Failure mode 1: API surface count not available at tier scoring time
**Detection**: `plan_input` doesn't have `public_classes` attribute at tier scoring
**Resolution**: Pass `understand_output.code_analysis.public_classes` into tier scorer;
if not available, fall back to file-count-only scoring (no regression)
**Gate**: Tier classification in plan bundle JSON artifact

### Failure mode 2: Tier C repos now generate 0 pages (all pruned)
**Detection**: Plan bundle shows 0 pages for a valid FOSS repo
**Resolution**: Mandatory page set from ruleset.yaml is the floor — at minimum 1 page
(e.g., installation or landing) should always be generated even for Tier C.
Add guard: if mandatory_pages empty for Tier C, generate at least installation page.
**Gate**: Plan bundle page count ≥ 1

### Failure mode 3: Existing tests break due to tier threshold changes
**Detection**: `pytest tests/planner/` shows failures
**Resolution**: Update test fixtures to match new composite tier scores;
or add `api_surface_count=0` to existing fixtures for backward compat
**Gate**: All 2944+ tests pass

## Task-specific review checklist

1. [ ] Composite tier scoring implemented (doc + API surface + snippet signals)
2. [ ] Tier C repos produce only mandatory pages (log evidence)
3. [ ] Tier A repos with large API surfaces classified correctly
4. [ ] `MIN_CLAIMS_PER_ROLE` enforced before plan assembly
5. [ ] Dropped optional pages logged at INFO level with reason
6. [ ] No reduction in mandatory page count for any existing pilot config
7. [ ] Docstrings updated for modified tier functions
8. [ ] Spec updated if tier behavior changed
9. [ ] Schema description fields present for new fields
10. [ ] Checked docs/README.md ownership map
11. [ ] evidence.md records: before/after tier scores, page counts, test results

## Deliverables

1. Updated `src/launcher/workers/planner/plan.py`
2. `reports/TC-3871/evidence.md`

## Acceptance checks

1. [ ] Lean repo (Tier C) generates mandatory pages only
2. [ ] API-rich repo correctly classified Tier A/B even without README
3. [ ] All 2944+ tests pass

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-3871/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --tb=short
```

**Expected results**:
- All 2944+ tests pass
- Tier scoring returns correct tier for test fixtures

## Integration boundary proven

**Upstream**: `understand_worker` provides `CodeAnalysis.public_classes` + snippet catalog
**Downstream**: `generate_worker` uses tier for variant selection and word-count targets
**Contract**: `PlanBundle.richness_tier: str` in {"A", "B", "C"}
