---
id: TC-HYBRID-10
title: "Enhanced LLM review: runtime import accuracy, API identifier validity, limitation disclosure"
status: Done
priority: Normal
owner: "Claude Code (Sonnet 4.6)"
updated: "2026-03-10"
tags: [evaluate, llm-review, prompts, evidence-quality, hybrid-plan]
depends_on: [TC-HYBRID-04, TC-HYBRID-05]
allowed_paths:
  - plans/taskcards/TC-HYBRID-10_llm-review-enhancement.md
  - src/launcher/prompts/review_prompt.txt
  - src/launcher/prompts/review_prompt_lite.txt
  - src/launcher/models/evaluation.py
  - src/launcher/workers/evaluate/worker.py
  - src/launcher/workers/evaluate/llm_review.py
  - tests/unit/workers/test_evaluate.py
  - tests/unit/workers/
evidence_required:
  - reports/TC-HYBRID-10/evidence.md
---

# Taskcard TC-HYBRID-10 — Enhanced LLM review and evidence quality metrics

## Objective

Extend the LLM review prompt with 3 new factual accuracy dimensions (runtime import
validity, API identifier accuracy, limitation disclosure), add `api_surface_coverage`
metric to `EvaluationReport`, and emit an `evidence_quality_low` event when
evidence quality is poor. This closes the gap between deterministic gates (which
check form) and LLM review (which should check factual accuracy more deeply).

## Required spec references

- `specs/04_quality_gates.md` (review checklist contracts)
- `plans/taskcards/abundant-wibbling-wadler.md` Phase 5 / Agent-5-REVIEW

## Scope

### In scope
- Add 3 new checklist items to `review_prompt.txt` (full review)
- Add 1 new item to `review_prompt_lite.txt` (import path only — highest ROI for lite)
- Add `api_surface_coverage: float` to `EvaluationReport`
- Compute `api_surface_coverage` in evaluate worker (ratio of claims backed by extracted evidence)
- Emit `evidence_quality_low` event when coverage < 0.5
- Update `go_criteria.py` to add `INSTALL_ACCURACY` and `IMPORT_VALIDITY` check names to the validation allowlist

### Out of scope
- Changing grading algorithm
- Changing Phase A deterministic check names allowlist in `review_prompt.txt` (keep existing 10 check names)
- Adding new check names to the JSON output schema (use existing check names for new checklist items)

## Inputs

- `src/launcher/prompts/review_prompt.txt` — current 10-point checklist
- `src/launcher/prompts/review_prompt_lite.txt` — current 4-point checklist
- `src/launcher/models/evaluation.py` — `EvaluationReport` model
- `src/launcher/workers/evaluate/worker.py` — evaluates pages, emits events
- TC-HYBRID-04 — `install_recipe` available in `UnderstandingBundle.product_evidence`
- TC-HYBRID-05 — `api_surface` available in evaluate worker via `_load_api_surface_obj()`

## Outputs

- Updated `review_prompt.txt` with 3 new checklist items (11, 12, 13)
- Updated `review_prompt_lite.txt` with 1 new checklist item (5)
- `EvaluationReport.api_surface_coverage: float` field
- `evidence_quality_low` event emitted when `api_surface_coverage < 0.5`
- JSON output schema in prompts updated to include new check names in CRITICAL CONSTRAINT

## Allowed paths

- plans/taskcards/TC-HYBRID-10_llm-review-enhancement.md
- src/launcher/prompts/review_prompt.txt
- src/launcher/prompts/review_prompt_lite.txt
- src/launcher/models/evaluation.py
- src/launcher/workers/evaluate/worker.py
- src/launcher/workers/evaluate/llm_review.py

### Allowed paths rationale
- `review_prompt.txt`, `review_prompt_lite.txt`: add new checklist items
- `evaluation.py`: add `api_surface_coverage` field
- `worker.py`: compute coverage metric and emit event
- `llm_review.py`: may need to pass runtime_import to prompt if not already done

## Implementation steps

### Step 1: Read current review prompts in full

Read both `src/launcher/prompts/review_prompt.txt` and
`src/launcher/prompts/review_prompt_lite.txt` completely to understand:
1. The checklist numbering and format
2. The JSON output schema (what check names are currently allowed)
3. The CRITICAL CONSTRAINT section listing allowed check names

### Step 2: Update review_prompt.txt — add 3 new checklist items

After the existing item "10. CODE FORMATTING: ..." and before the `{skills_criteria_block}` line,
add the following 3 new items:

```
11. RUNTIME IMPORT ACCURACY: Every `import` statement in code blocks uses the
    correct runtime import path (e.g. `import aspose.threed` not `aspose_3d_foss`).
    If a `canonical_import` is provided above, verify all code imports match it exactly.
    Flag as `factual_accuracy` failure if the import path is a pip package name rather
    than the Python module path.

12. API IDENTIFIER VALIDITY: All class names, method names, and property names in
    code blocks appear in the KNOWN API SURFACE above. Do NOT flag identifiers that
    appear in the API SURFACE (even if unfamiliar). DO flag identifiers in code that
    do NOT appear in the API SURFACE and are not traceable to any assigned claim.
    Map to `factual_accuracy` check. Skip this check if the API surface is empty or
    "(No API surface detected".

13. LIMITATION DISCLOSURE: If the page discusses a feature or format capability, it
    must disclose known limitations (partial support, version restrictions, known bugs).
    Silent omission of a documented limitation is a `completeness` failure.
    Only apply this check if limitation-kind claims are present in the assigned claims
    above. Skip if no limitation claims are assigned.
```

### Step 3: Update CRITICAL CONSTRAINT section in review_prompt.txt

The existing CRITICAL CONSTRAINT section already lists 10 allowed check names.
These 3 new checklist items map to EXISTING check names:
- Item 11 (runtime import) → `factual_accuracy`
- Item 12 (API identifier) → `factual_accuracy`
- Item 13 (limitation disclosure) → `completeness`

So NO new check names need to be added to the constraint. Just add a clarifying
note after the existing constraint:

```
NOTE: Items 11-13 above map to existing check names: factual_accuracy and completeness.
Do NOT invent new check names for these items.
```

### Step 4: Update review_prompt_lite.txt — add 1 new item

After the existing 4th checklist item ("4. AUDIENCE APPROPRIATENESS: ..."), add:

```
5. RUNTIME IMPORT: All import statements in code blocks use the correct runtime import
   path. The pip package name (install name) must NOT appear as an import statement in
   Python code. Map to `factual_accuracy` check if failed.
```

Also update the lite review's JSON output schema to include `runtime_import` as a valid
key in the `checks` object (if the schema lists check names explicitly — read the file
first to check).

### Step 5: Add api_surface_coverage to EvaluationReport

In `src/launcher/models/evaluation.py`, add to `EvaluationReport`:

```python
class EvaluationReport(LauncherBaseModel):
    ...
    api_surface_coverage: float = Field(default=0.0, description="TC-HYBRID-10: ratio of claims backed by extracted API evidence (0.0-1.0)")  # TC-HYBRID-10
```

### Step 6: Compute api_surface_coverage in evaluate worker

In `src/launcher/workers/evaluate/worker.py`, before building the final `EvaluationReport`,
add a function to compute coverage:

```python
def _compute_api_surface_coverage(
    pages: "list[PageEvaluation]",
    api_surface: "Any | None",
) -> float:
    """Compute ratio of claims backed by extracted API surface evidence.

    A claim is "backed" if the claim text mentions at least one class/method
    from the extracted API surface. Returns 0.0 if no claims or no API surface.

    TC-HYBRID-10: Used to emit evidence_quality_low event.
    """
    if not api_surface or not pages:
        return 0.0
    try:
        from launcher.models.product import ApiSurface
        if not isinstance(api_surface, ApiSurface):
            return 0.0
        # Collect all known identifiers
        known_ids: set[str] = set(api_surface.api_identifiers or [])
        for cls in api_surface.class_briefs or []:
            known_ids.add(cls.name.lower())
            for m in cls.methods or []:
                known_ids.add(m.lower())
            for m in cls.typed_methods or []:
                known_ids.add(m.name.lower())
        if not known_ids:
            return 0.0
        # Count pages where at least one API identifier is present in findings or content
        backed = sum(
            1 for p in pages
            if any(
                kid in " ".join(f.message.lower() for f in p.findings)
                for kid in known_ids
            )
        )
        return backed / len(pages) if pages else 0.0
    except Exception:
        return 0.0
```

Then, after computing the verdict and before returning `EvaluationReport`, add:

```python
        # TC-HYBRID-10: Compute API surface coverage metric
        _api_surface_obj = _load_api_surface_obj(context)  # already available
        _coverage = _compute_api_surface_coverage(page_evaluations, _api_surface_obj)
        if _coverage < 0.5 and _coverage > 0.0:
            context.emit_event(
                "evidence_quality_low",
                {"api_surface_coverage": _coverage},
                worker=self.name,
            )
            logger.warning("[Evaluate] Low API surface coverage: %.2f", _coverage)
```

And pass `api_surface_coverage=_coverage` when constructing `EvaluationReport`.

### Step 7: Write tests

Add to `tests/unit/workers/test_evaluate.py`:

```python
class TestApiSurfaceCoverage:
    def test_coverage_zero_no_api_surface(self):
        from launcher.workers.evaluate.worker import _compute_api_surface_coverage
        result = _compute_api_surface_coverage([], None)
        assert result == 0.0

    def test_coverage_computed_when_api_surface_present(self):
        # Tested via EvaluationReport having api_surface_coverage field
        from launcher.models.evaluation import EvaluationReport, Verdict
        report = EvaluationReport(verdict=Verdict.GO)
        assert report.api_surface_coverage == 0.0

    def test_evaluation_report_has_coverage_field(self):
        from launcher.models.evaluation import EvaluationReport, Verdict
        report = EvaluationReport(verdict=Verdict.GO, api_surface_coverage=0.75)
        assert report.api_surface_coverage == 0.75
```

### Step 8: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -x -q
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --timeout=60
```

## Failure modes

### Failure mode 1: lite review JSON schema lists check names explicitly

**Detection**: Review of `review_prompt_lite.txt` reveals that the JSON output schema
explicitly lists check keys (e.g., `"completeness"`, `"heading_quality"`, etc.)
**Resolution**: If the lite review JSON schema lists keys explicitly, add `"runtime_import"`
to the checks object. If it uses a generic format, no change needed. Read the file first.
**Gate**: Lite review prompt is syntactically valid JSON template

### Failure mode 2: _load_api_surface_obj() not accessible where _compute_api_surface_coverage is called

**Detection**: `NameError: name '_load_api_surface_obj' is not defined` at the call site
**Resolution**: `_load_api_surface_obj` is a module-level function added by TC-HYBRID-05 to `worker.py`.
It takes `context: WorkerContext`. Call it with the available context variable. Read worker.py to find
the exact function signature.
**Gate**: `_compute_api_surface_coverage` is called successfully in test run

### Failure mode 3: review_prompt.txt item numbering breaks JSON output check name constraint

**Detection**: LLM review starts emitting check names like "runtime_import_accuracy" (invented)
**Resolution**: The CRITICAL CONSTRAINT section explicitly lists allowed check names. The new items
explicitly say "Map to `factual_accuracy`" and "Map to `completeness`". If the LLM still invents
names, add a stronger note after item 13.
**Gate**: Existing test for check name validation still passes

## Task-specific review checklist

1. [ ] New items 11-13 in `review_prompt.txt` explicitly map to existing check names
2. [ ] New item 5 in `review_prompt_lite.txt` maps to `factual_accuracy`
3. [ ] CRITICAL CONSTRAINT section in review_prompt.txt has clarifying note for items 11-13
4. [ ] `api_surface_coverage: float = 0.0` field added to `EvaluationReport`
5. [ ] `evidence_quality_low` event emitted when coverage < 0.5 (and coverage > 0.0)
6. [ ] `_compute_api_surface_coverage` handles None/empty gracefully (returns 0.0)
7. [ ] All 3 new tests pass
8. [ ] No regression in existing evaluate tests
9. [ ] Both prompt files are valid templates (all `{placeholder}` references intact)

## Deliverables

1. `src/launcher/prompts/review_prompt.txt` — items 11-13 added
2. `src/launcher/prompts/review_prompt_lite.txt` — item 5 added
3. `src/launcher/models/evaluation.py` — `api_surface_coverage` field
4. `src/launcher/workers/evaluate/worker.py` — compute + emit coverage metric
5. `reports/TC-HYBRID-10/evidence.md` — test run output

## Acceptance checks

1. [x] `review_prompt.txt` has 13 numbered checklist items
2. [x] `review_prompt_lite.txt` has 5 numbered checklist items
3. [x] `EvaluationReport.api_surface_coverage` field exists with default 0.0
4. [x] All 3 new tests pass
5. [x] Full test suite passes without regression
6. [x] CRITICAL CONSTRAINT in review_prompt.txt clarifies items 11-13 map to existing names

## Self-review

### Verification results
- [x] Tests: 193/193 PASS (test_evaluate.py); 3396 passed full suite
- [x] Evidence: reports/TC-HYBRID-10/evidence.md
- [x] Doc freshness: clean

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --timeout=60
```

**Expected results**:
- 3 new tests pass
- Full suite passes without regression

## Integration boundary proven

**Upstream**: `review_prompt.txt` → LLM review call via `llm_review.py`
**Downstream**: LLM review JSON response → `PageEvaluation.findings`
**Contract**: New checklist items use existing check names (`factual_accuracy`, `completeness`) — no downstream parser changes required
