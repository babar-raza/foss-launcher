---
id: TC-4085
title: "Diagnostic clarity for non-Python API surface extraction failures"
status: Done
priority: Normal
owner: agent
updated: "2026-03-11"
tags: [phase4, understand, diagnostics]
depends_on: [TC-4084]
allowed_paths:
  - plans/taskcards/TC-4085_non_python_diagnostic.md
  - src/launcher/workers/understand/worker.py
evidence_required:
  - reports/TC-4085/evidence.md
---

# Taskcard TC-4085 — Diagnostic clarity for non-Python API surface extraction failures

## Objective

When api_surface_empty fires for non-Python repos, the current message is generic.
Differentiate between "tree-sitter not installed" vs "tree-sitter available but 0 classes"
to give an actionable diagnosis.

## Allowed paths

- plans/taskcards/TC-4085_non_python_diagnostic.md
- src/launcher/workers/understand/worker.py

## Implementation steps

### Step 1: Check tree-sitter availability in self_review for non-Python

In `self_review()`, when `api_surface_empty` fires for non-Python, check tree-sitter:

```python
if not _is_python and len(bundle.api_surface.public_classes) == 0:
    try:
        import tree_sitter  # noqa: F401
        ts_available = True
    except ImportError:
        ts_available = False
    if not ts_available:
        _ts_message = (
            f"api_surface has no public classes for {primary_lang!r} — "
            "tree-sitter is not installed. "
            f"Run: pip install tree-sitter tree-sitter-{primary_lang}"
        )
    else:
        _ts_message = (
            f"api_surface has no public classes for {primary_lang!r} despite "
            "tree-sitter being available. Package root detection or import filter "
            "may have failed. Check extraction_audit.json."
        )
    # Update the message on the existing finding
```

This replaces the existing generic message — not an additional finding.

## Task-specific review checklist

1. [ ] tree-sitter import check is inside try/except
2. [ ] Message is actionable: tells reviewer what to install or where to check
3. [ ] Not an additional finding — updates existing api_surface_empty message
4. [ ] No regressions in self_review tests

## Acceptance checks

1. [ ] Non-Python repo with tree-sitter absent → message includes "tree-sitter is not installed"
2. [ ] Non-Python repo with tree-sitter present but 0 classes → message includes "Check extraction_audit.json"
