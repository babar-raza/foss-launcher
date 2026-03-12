---
id: TC-4051
title: "Wave 2D: Deterministic title formulas in plan.py"
status: Done
priority: High
owner: "orchestrator"
updated: "2026-03-11"
tags: [crispy-growing-pebble, wave-2d, retroactive]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4051_wave2d-deterministic-titles.md
  - src/launcher/workers/planner/plan.py
evidence_required:
  - reports/TC-4051/evidence.md
---

# Taskcard TC-4051 — Wave 2D: Deterministic Title Formulas

## Objective

Retroactive taskcard (AG-002 compliance) for Wave 2D changes to `plan.py`. Deterministic
title formulas were added keyed by `topic_category × page_role`, replacing the evidence-
hunting heuristic with a predictable formula that prevents JSON/garbled titles.

## Required spec references

- `crispy-growing-pebble.md` Wave 2D

## Scope

### In scope
- `_TOPIC_LABELS` dict (15 entries) mapping topic_category → human-readable label
- `_ROLE_TITLE_TEMPLATES` dict (6 entries) mapping page_role → title template
- Updated `_generate_evidence_aware_title()` signature: `product_name=""`, `topic_category=""`
- Deterministic title formula logic: howto_article + topic_category → "How to {label} with {product}"
- Updated call site in `_assign_claims()`

### Out of scope
- SEO metadata (Wave 2E)
- Slug generation

## What was implemented

```python
_TOPIC_LABELS: dict[str, str] = {
    "load_file": "Load Spreadsheets",
    "save_file": "Save Spreadsheets",
    "convert_formats": "Convert Spreadsheet Formats",
    "formula_calculation": "Calculate Formulas",
    "spreadsheet_ops": "Work with Spreadsheets",
    "troubleshoot": "Troubleshoot Issues",
    "optimize_performance": "Optimize Performance",
    # ... (15 total)
}

_ROLE_TITLE_TEMPLATES: dict[str, str] = {
    "api_reference": "{product} API Reference",
    "landing": "{product}",
    "getting_started": "Get Started with {product}",
    # ... (6 total)
}
```

`_generate_evidence_aware_title()` now accepts `product_name` and `topic_category` kwargs;
deterministic formula fires first; heuristic fires as fallback.

## Inputs

- `src/launcher/workers/planner/plan.py` (before Wave 2D)

## Outputs

- Updated `src/launcher/workers/planner/plan.py`

## Allowed paths

- plans/taskcards/TC-4051_wave2d-deterministic-titles.md
- src/launcher/workers/planner/plan.py

## Self-review

### Verification results

- [x] `_TOPIC_LABELS` present in plan.py
- [x] `_ROLE_TITLE_TEMPLATES` present in plan.py
- [x] `_generate_evidence_aware_title` accepts `product_name`, `topic_category` kwargs
- [x] All planner tests pass (PYTHONHASHSEED=0)

## Integration boundary proven

**Upstream**: `_assign_claims()` calls `_generate_evidence_aware_title()` after claim assignment
**Downstream**: `PlannedPage.title` field used in generate worker prompt
**Contract**: deterministic formula → human-readable title → used in LLM prompt context
