---
id: TC-4083
title: "Add informative medium findings to self_review for thin Python extraction"
status: Done
priority: Normal
owner: agent
updated: "2026-03-11"
tags: [phase3, understand, python, self_review]
depends_on: [TC-4082]
allowed_paths:
  - plans/taskcards/TC-4083_self_review_thin_python.md
  - src/launcher/workers/understand/worker.py
  - tests/unit/workers/understand/test_python_hardening.py
evidence_required:
  - reports/TC-4083/evidence.md
---

# Taskcard TC-4083 — Add informative medium findings to self_review for thin Python

## Objective

When self_review detects thin Python extraction (1 public class or low claim count),
the current finding messages say only that something failed, not WHY. Add actionable
medium-severity findings that explain the gap and direct the reviewer to the correct artifact.

## Allowed paths

- plans/taskcards/TC-4083_self_review_thin_python.md
- src/launcher/workers/understand/worker.py
- tests/unit/workers/understand/test_python_hardening.py

## Implementation steps

### Step 1: Add thin-API finding in `self_review`

After the existing `api_surface_empty` check, add:

```python
# TC-4083: Thin API surface for Python repos — medium, not blocking
if (
    _is_python
    and 0 < len(bundle.api_surface.public_classes) <= 1
):
    findings.append({
        "category": "thin_api_surface",
        "message": (
            f"Only {len(bundle.api_surface.public_classes)} public class(es) found for a "
            f"Python repo. Package root detection may be incomplete (namespace packages). "
            "Check extraction_audit.json → public_class_count and inspect package_root "
            "in logs. Ensure runtime_import is set in families.yaml for this product."
        ),
        "severity": "medium",
    })
```

### Step 2: Add low claim count finding

After existing claim count checks, add:

```python
# TC-4083: Low claim count when API surface is non-empty
if (
    len(bundle.api_surface.public_classes) > 0
    and len(bundle.claims) < 10
):
    findings.append({
        "category": "low_claim_count",
        "message": (
            f"Claim count is low ({len(bundle.claims)}) for a repo with "
            f"{len(bundle.api_surface.public_classes)} public API class(es). "
            "Evidence context may be thin or LLM is unreachable. "
            "Check extraction_audit.json claim_provenance_counts."
        ),
        "severity": "medium",
    })
```

## Failure modes

### Failure mode 1: Medium findings trigger false positives
**Detection**: Test repos with deliberately sparse APIs fail self_review unexpectedly
**Resolution**: Both are medium — not blocking; they explain the gap, not block progress
**Gate**: self_review

### Failure mode 2: Finding text too long for display
**Detection**: message exceeds column width in artifact
**Resolution**: Messages are already line-wrapped in the plan
**Gate**: self_review

### Failure mode 3: Interaction with existing high-severity api_surface_empty
**Detection**: Both api_surface_empty (high) and thin_api_surface (medium) fire simultaneously
**Resolution**: Expected — api_surface_empty fires when 0 classes, thin fires when 1 class
**Gate**: self_review (correct behavior)

## Task-specific review checklist

1. [ ] Thin API finding only fires when 0 < class_count <= 1
2. [ ] Thin API finding only fires for Python repos (`_is_python`)
3. [ ] Low claim count finding only fires when api_surface non-empty
4. [ ] Both findings are medium severity (not blocking)
5. [ ] Messages direct reviewer to extraction_audit.json
6. [ ] No regression in existing self_review tests
7. [ ] Docstrings updated
8. [ ] Spec confirmed — no drift

## Acceptance checks

1. [ ] Python repo with 1 class → medium "thin_api_surface" finding in self_review
2. [ ] Python repo with 3+ claims and 0 classes → NOT flagged by thin_api (api_surface_empty fires instead)
3. [ ] Non-Python repo with 1 class → NOT flagged by thin_api_surface (Python-specific)
4. [ ] self_review still passes when only medium findings present

## E2E verification

```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_python_hardening.py::TestSelfReviewThinPython -v
```
