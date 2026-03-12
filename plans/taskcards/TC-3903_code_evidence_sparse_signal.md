---
id: TC-3903
title: "code_evidence_sparse: orthogonal evidence-poverty signal in RichnessResult"
status: Done
priority: High
owner: "Agent-B"
updated: "2026-03-09"
tags: [surface_classifier, richness, thin-repo, evidence, models]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3903_code_evidence_sparse_signal.md
  - src/launcher/models/product.py
  - src/launcher/shared/surface_classifier.py
  - tests/test_surface_classifier.py
evidence_required:
  - reports/agents/B/TC-3903/evidence.md
---

# Taskcard TC-3903 — code_evidence_sparse signal

## Objective

Add a `code_evidence_sparse: bool` field to `RichnessResult` that is `True` when a repo
has fewer than 3 combined example files + extracted snippets. This closes the gap where
a Tier B repo (like 3D TypeScript: score 15/25, has tests+CI+docs) has zero executable
code evidence, yet no existing thin-repo guard fires. Rich repos (Cells Python: 10 example
files + many snippets) always get `code_evidence_sparse=False` — no behavior change.

## Required spec references

- `specs/product_model.md` (Section: RichnessResult)

## Scope

### In scope
- Add `code_evidence_sparse: bool = False` to `RichnessResult` in `models/product.py`
- Compute `code_evidence_sparse` in `classify_richness_with_surface()` in `surface_classifier.py`
- Thread through `UnderstandingBundle.richness_tier` → planner → `PlannedPage.richness_tier`
- Tests in `tests/test_surface_classifier.py`

### Out of scope
- Adding a new richness Tier D (not a tier change — orthogonal flag only)
- Changes to `classify_richness()` (base function — unchanged)
- Changes to the word-count caps or template selection (those remain Tier C only)
- Planner claim-assignment logic (unaffected)

## Inputs

- `src/launcher/models/product.py` — `RichnessResult` model
- `src/launcher/shared/surface_classifier.py` — `classify_richness_with_surface()`
- `src/launcher/models/understanding.py` — `UnderstandingBundle`
- `src/launcher/models/plan.py` — `PlannedPage.richness_tier` field

## Outputs

- `RichnessResult.code_evidence_sparse: bool = False`
- `classify_richness_with_surface()` computes and sets the flag
- Field propagates through pipeline; used by TC-3902 as additional gate

## Allowed paths

- plans/taskcards/TC-3903_code_evidence_sparse_signal.md
- src/launcher/models/product.py
- src/launcher/shared/surface_classifier.py
- tests/test_surface_classifier.py

### Allowed paths rationale
- `product.py`: model change (new field with default)
- `surface_classifier.py`: computation of the new field
- `tests/test_surface_classifier.py`: verification

## Implementation steps

### Step 1: Add `code_evidence_sparse` to `RichnessResult` in `models/product.py`

```python
class RichnessResult(LauncherBaseModel):
    tier: RichnessTier
    score: int
    reason: str
    code_evidence_sparse: bool = False  # True when example_files + extracted_snippets < 3
```

Default `False` ensures backward compatibility with all existing code that constructs
`RichnessResult` without the new field (e.g., `classify_richness()` base function).

### Step 2: Compute `code_evidence_sparse` in `classify_richness_with_surface()`

In `surface_classifier.py`, after computing `new_score`:

```python
# Code evidence score: executable proof available in the repo
# Counts example files + extracted snippets (capped to avoid dominating)
_code_evidence_score = (
    min(len(repo_info.example_paths), 10)
    + min(extracted_snippet_count, 10)
)
code_evidence_sparse = _code_evidence_score < 3

reasons.append(f"code_evidence={_code_evidence_score}(sparse={code_evidence_sparse})")

return RichnessResult(
    tier=tier,
    score=new_score,
    reason="; ".join(reasons),
    code_evidence_sparse=code_evidence_sparse,
)
```

### Step 3: Tests in `tests/test_surface_classifier.py`

1. Thin repo (0 examples, 0 snippets) → `code_evidence_sparse=True`
2. Rich repo (10 examples, 15 snippets) → `code_evidence_sparse=False`
3. Boundary (2 examples + 0 snippets = 2) → `code_evidence_sparse=True` (< 3)
4. Boundary (3 examples + 0 snippets = 3) → `code_evidence_sparse=False` (== 3, NOT < 3)
5. `classify_richness()` (base) → `code_evidence_sparse=False` (default, not computed)

## Failure modes

### Failure mode 1: `classify_richness()` base function used downstream without the field

**Detection**: Code that checks `result.code_evidence_sparse` on a `classify_richness()` result
**Resolution**: Default `False` is set at model level — safe to read even if not computed
**Gate**: Pydantic default ensures no AttributeError

### Failure mode 2: `extracted_snippet_count` not available at classify time

**Detection**: `extracted_snippet_count=0` passed when snippets actually exist
**Resolution**: Caller (`understand/worker.py`) must pass `extracted_snippet_count=len(bundle.snippets)` — already done for the existing `extracted_snippets >= 10` signal check
**Gate**: Test: verify understand worker passes non-zero count for snippet-rich repos

### Failure mode 3: Score threshold too low causes false positives

**Detection**: Repos with 2 example files but full content being marked sparse
**Resolution**: Threshold `< 3` is conservative. A repo with 2 example files but no extracted snippets is genuinely evidence-sparse. Tunable constant `_CODE_EVIDENCE_SPARSE_THRESHOLD = 3`
**Gate**: boundary tests at 2 and 3

## Task-specific review checklist

1. [ ] `code_evidence_sparse: bool = False` in `RichnessResult` model
2. [ ] `classify_richness()` base function returns `code_evidence_sparse=False` (default)
3. [ ] `classify_richness_with_surface()` computes and sets the flag
4. [ ] Cells Python equivalent (10 examples) → `code_evidence_sparse=False`
5. [ ] 3D TypeScript equivalent (0 examples, 0 snippets) → `code_evidence_sparse=True`
6. [ ] Threshold constant named `_CODE_EVIDENCE_SPARSE_THRESHOLD` (not magic number)
7. [ ] Docstrings updated
8. [ ] Spec file updated for `product_model.md`
9. [ ] Schema description present for new field
10. [ ] Checked `docs/README.md` ownership map
11. [ ] If new docs guide added: `docs/README.md` index updated

## Deliverables

1. `src/launcher/models/product.py` — new field with default
2. `src/launcher/shared/surface_classifier.py` — computation in `classify_richness_with_surface`
3. `tests/test_surface_classifier.py` — 5 new test cases
4. `reports/agents/B/TC-3903/evidence.md`

## Acceptance checks

1. [ ] `RichnessResult(tier=..., score=..., reason=...)` (no code_evidence_sparse) → default False
2. [ ] 3D TypeScript equivalent → `code_evidence_sparse=True`
3. [ ] Cells Python equivalent → `code_evidence_sparse=False`
4. [ ] All tests pass

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/agents/B/TC-3903/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_surface_classifier.py -v -k "code_evidence"
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -5
```

## Integration boundary proven

**Upstream**: `understand/worker.py` calls `classify_richness_with_surface(repo_info, extracted_snippet_count=N)`
**Downstream**: `section_prompt.py` reads `page.richness_tier.code_evidence_sparse` as gate
**Contract**: `code_evidence_sparse=False` → no behavioral change downstream
