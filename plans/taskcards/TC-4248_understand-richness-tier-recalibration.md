---
id: TC-4248
title: "Richness tier recalibration using ExtractionCompleteness"
status: Done
priority: High
owner: "agent-B"
updated: "2026-03-12"
tags: [understand, richness-tier, extraction-completeness]
depends_on: [TC-4242, TC-4244]
allowed_paths:
  - plans/taskcards/TC-4248_understand-richness-tier-recalibration.md
  - src/launcher/workers/understand/worker.py
  - tests/unit/workers/test_understand.py
  - reports/agents/B_implementation/TC-4248/evidence.md
  - reports/agents/B_implementation/TC-4248/self_review.md
evidence_required:
  - reports/agents/B_implementation/TC-4248/evidence.md
---

# Taskcard TC-4248 — Richness tier recalibration using ExtractionCompleteness

## Objective

Replace the file-structure-based richness tier scoring in `worker.py` with evidence-quality
scoring from `ExtractionCompleteness`. Tier A will now require rich, complete deterministic
evidence — not just many files. This prevents inflated tiers that cause over-ambitious
generation when API surface is actually thin.

## Required spec references

- `C:\Users\prora\.claude\plans\bright-kindling-eagle.md` (Section D Step 8)

## Scope

### In scope
- Add `_classify_richness_from_completeness(completeness: ExtractionCompleteness) -> RichnessResult` to `worker.py`
- Replace the `classify_richness_with_surface(repo_info, ...)` call in `worker.py` with the new function
- The new function uses the formula from the plan: api_method_count * 0.30 + format_count * 0.20 + api_confidence * 0.20 + snippet_count * 0.15 + format_confidence_avg * 0.15
- Update tests

### Out of scope
- Modifying `classify_richness_with_surface` in `surface_classifier.py` (keep it for other callers)
- Changing `ExtractionCompleteness` model (TC-4242 done)
- Changing what extraction produces (TC-4244 done)

## Inputs

- `src/launcher/workers/understand/worker.py` — UnderstandWorker.run()
- `src/launcher/models/understanding.py` — ExtractionCompleteness model
- `extraction_db.completeness` — populated by TC-4244

## Outputs

- Modified `worker.py` with evidence-quality richness scoring

## Allowed paths

- plans/taskcards/TC-4248_understand-richness-tier-recalibration.md
- src/launcher/workers/understand/worker.py
- tests/unit/workers/test_understand.py
- reports/agents/B_implementation/TC-4248/evidence.md
- reports/agents/B_implementation/TC-4248/self_review.md

### Allowed paths rationale
- `worker.py`: contains the `classify_richness_with_surface` call to replace
- `test_understand.py`: update tests for new richness scoring behavior
- Evidence/self_review: required by AG-002

## Implementation steps

### Step 1: Add `_classify_richness_from_completeness()` to `worker.py`

Add after the imports:

```python
from launcher.models.understanding import ExtractionCompleteness as _EC
from launcher.models.product import RichnessTier as _RT, RichnessResult

def _classify_richness_from_completeness(completeness: _EC) -> RichnessResult:
    """Evidence-quality richness tier from ExtractionCompleteness.

    TC-4248: Replaces file-structure-based classify_richness_with_surface().
    Tier A requires rich, complete deterministic evidence — not just many files.

    Scoring formula:
      api_methods_score = min(api_method_count / 50, 1.0) * 0.30
      format_score      = min(format_count / 10, 1.0) * 0.20
      api_conf_score    = (1.0 if api_confidence == "high" else 0.5 if api_confidence == "medium" else 0.0) * 0.20
      snippet_score     = min(snippet_count / 15, 1.0) * 0.15
      fmt_conf_score    = format_confidence_avg * 0.15

    Thresholds: >=0.70 → Tier A, >=0.40 → Tier B, <0.40 → Tier C
    """
    api_methods_score = min(completeness.api_method_count / 50, 1.0) * 0.30
    format_score = min(completeness.format_count / 10, 1.0) * 0.20
    if completeness.api_confidence == "high":
        api_conf_score = 1.0 * 0.20
    elif completeness.api_confidence == "medium":
        api_conf_score = 0.5 * 0.20
    else:
        api_conf_score = 0.0
    snippet_score = min(completeness.snippet_count / 15, 1.0) * 0.15
    fmt_conf_score = completeness.format_confidence_avg * 0.15

    total = api_methods_score + format_score + api_conf_score + snippet_score + fmt_conf_score

    if total >= 0.70:
        tier = _RT.A
    elif total >= 0.40:
        tier = _RT.B
    else:
        tier = _RT.C

    # Convert float score (0.0–1.0) to int score (0–100) for RichnessResult compatibility
    int_score = round(total * 100)
    reasons = [
        f"api_methods={completeness.api_method_count}(+{api_methods_score:.2f})",
        f"formats={completeness.format_count}(+{format_score:.2f})",
        f"api_conf={completeness.api_confidence}(+{api_conf_score:.2f})",
        f"snippets={completeness.snippet_count}(+{snippet_score:.2f})",
        f"fmt_conf_avg={completeness.format_confidence_avg:.2f}(+{fmt_conf_score:.2f})",
    ]
    return RichnessResult(tier=tier, score=int_score, reason="; ".join(reasons))
```

### Step 2: Replace `classify_richness_with_surface()` call in `worker.py`

In `UnderstandWorker.run()`, find:

```python
extracted_snippet_count = sum(
    1 for s in snippets if getattr(s, "source_type", "extracted") == "extracted"
)
richness = classify_richness_with_surface(
    repo_info,
    api_confidence=api_surface.confidence,
    public_class_count=len(api_surface.public_classes),
    extracted_snippet_count=extracted_snippet_count,
)
```

Replace with:

```python
richness = _classify_richness_from_completeness(extraction_db.completeness)
```

Remove the now-unused `extracted_snippet_count` variable and the `classify_richness_with_surface` import.

### Step 3: Update tests in `test_understand.py`

Add tests for `_classify_richness_from_completeness`:
- Empty ExtractionCompleteness → Tier C
- Rich completeness (50+ methods, 10+ formats, high confidence) → Tier A
- Medium completeness → Tier B
- Verify score is in 0–100 range (int_score = round(total * 100))

## Failure modes

### Failure mode 1: `RichnessResult` constructor rejects non-integer score

**Detection**: `ValidationError` when `int_score = round(total * 100)` produces a float
**Resolution**: Ensure `round()` returns int; `RichnessResult.score` field accepts int.
Check `models/product.py` for `RichnessResult.score` type annotation.
**Gate**: Test must construct `RichnessResult` without error.

### Failure mode 2: `classify_richness_with_surface` import becomes unused

**Detection**: Linter warning `imported but unused` in `worker.py`
**Resolution**: Remove the import. The function still exists in `surface_classifier.py`
for any other callers — do not remove it from there.
**Gate**: No import errors on module load.

### Failure mode 3: ExtractionCompleteness.overall_completeness not populated

**Detection**: `completeness.overall_completeness == 0.0` despite having api_facts/format_facts
**Resolution**: The formula uses individual fields (api_method_count, format_count, etc.),
NOT `overall_completeness`. The scoring function computes its own total. This is robust to
`overall_completeness` being 0.0.
**Gate**: Tests with known field values must produce expected tier.

## Task-specific review checklist

1. [ ] `_classify_richness_from_completeness` produces Tier A only when api_method_count ≥ 35 AND format_count ≥ 7 AND api_confidence=="high"
2. [ ] `_classify_richness_from_completeness(ExtractionCompleteness())` returns Tier C (all zeros)
3. [ ] `classify_richness_with_surface` import removed from `worker.py` (no longer called there)
4. [ ] `RichnessResult.score` is int, not float (check model definition)
5. [ ] Log message at "[Understand] Richness: Tier X (score=Y)" still works with new function
6. [ ] No test regressions outside the 4 pre-existing ignore files
7. [ ] Docstrings updated for `_classify_richness_from_completeness`
8. [ ] Spec file updated if worker behavior changed
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map — if a trigger event applies, relevant guide updated
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables

1. Modified `src/launcher/workers/understand/worker.py` with evidence-quality richness scoring
2. `reports/agents/B_implementation/TC-4248/evidence.md`

## Acceptance checks

1. [ ] `_classify_richness_from_completeness(ExtractionCompleteness())` returns Tier C
2. [ ] `_classify_richness_from_completeness` with api_method_count=50, format_count=10, api_confidence="high", snippet_count=15, format_confidence_avg=1.0 returns Tier A
3. [ ] Tests pass: `pytest tests/unit/workers/test_understand.py -x` (no new failures)

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: Tier A/B/C thresholds verified with boundary values
- [ ] Evidence captured: reports/agents/B_implementation/TC-4248/evidence.md

## E2E verification

```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -x \
  --ignore=tests/unit/workers/test_plan_slug_integration.py \
  --ignore=tests/unit/workers/test_plan_slugs.py \
  --ignore=tests/unit/workers/test_scenario_planning.py \
  --ignore=tests/test_planner_per_module.py -v
```

**Expected results**:
- All tests pass
- `_classify_richness_from_completeness` imported and callable from `worker.py`

## Integration boundary proven

**Upstream**: TC-4244 populates `extraction_db.completeness` in `run_extract()` return value
**Downstream**: Planner consumes `richness_tier` from UnderstandingBundle to decide page scope
**Contract**: `RichnessResult` with Tier A/B/C and integer score field
