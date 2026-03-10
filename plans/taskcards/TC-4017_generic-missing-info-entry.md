---
id: TC-4017
title: "GenericExtractor emits MissingInfoEntry for typed_methods absence"
status: Done
priority: Medium
owner: "orchestrator"
updated: "2026-03-11"
tags: [humming-greeting-kay, hg-07, observability]
depends_on: [TC-4003, TC-4005]
ruleset_version: "1.0"
spec_ref: "6a56035"
templates_version: "1.0"
allowed_paths:
  - plans/taskcards/TC-4017_generic-missing-info-entry.md
  - src/launcher/workers/understand/extract/_entry.py
  - tests/unit/workers/test_understand.py
evidence_required:
  - phase_store/TC-4017_evidence.md
---

# Taskcard TC-4017 — GenericExtractor MissingInfoEntry Emission

## Objective

When `get_extractor(platform)` returns a `GenericExtractor` (any unknown platform
like Rust, Go, C++ once adapters are not present), or when adapter resolution fails
entirely (`_adapter is None`), `_entry.py` should emit a `MissingInfoEntry` record
so downstream workers can distinguish "typed extraction unavailable" from "no methods exist".

## Required spec references

- `src/launcher/models/understanding.py` (MissingInfoEntry, FieldConfidence, ProductEvidence)
- `src/launcher/workers/understand/adapters/_generic.py` (GenericExtractor)

## Scope

### In scope

- Detect `isinstance(_adapter, GenericExtractor) or _adapter is None` in `_entry.py`
- Emit `MissingInfoEntry(field="api_surface.typed_methods", ...)` into `_missing_info` list
- Wire `_missing_info` into `ProductEvidence` constructor
- Add `FieldConfidence(source="absent")` to `product_evidence.confidence["typed_methods"]`
- 3+ unit tests

### Out of scope

- Changing `adapters/_generic.py`
- Changing `models/understanding.py`
- Python or TypeScript adapter behavior

## Inputs

- `src/launcher/workers/understand/extract/_entry.py` (current state)
- `src/launcher/workers/understand/adapters/_generic.py` (read-only)
- `src/launcher/models/understanding.py` (MissingInfoEntry, FieldConfidence)

## Outputs

- Updated `src/launcher/workers/understand/extract/_entry.py`
- New tests in `tests/unit/workers/test_understand.py`

## Allowed paths

- plans/taskcards/TC-4017_generic-missing-info-entry.md
- src/launcher/workers/understand/extract/_entry.py
- tests/unit/workers/test_understand.py

### Allowed paths rationale

Only `_entry.py` needs the GenericExtractor detection logic. Tests go in the existing `test_understand.py`.

## Implementation steps

### Step 1: Add MissingInfoEntry emission after adapter resolution

In `run_extract()`, after `_adapter = get_extractor(product.platform)`,
add:

```python
_missing_info: list = []
from launcher.workers.understand.adapters._generic import GenericExtractor
from launcher.models.understanding import MissingInfoEntry, FieldConfidence
if isinstance(_adapter, GenericExtractor) or _adapter is None:
    _missing_info.append(MissingInfoEntry(
        field="api_surface.typed_methods",
        reason=f"No typed extraction available for platform '{product.platform}'",
        attempted_strategies=["generic_regex"],
        fallback_used="regex",
    ))
```

### Step 2: Wire into ProductEvidence constructor

In the ProductEvidence constructor call (near line 205), add:

```python
product_evidence = ProductEvidence(
    limitations=limitations,
    workflow_examples=workflow_examples,
    install_recipe=install_recipe,
    missing_info=_missing_info,
    confidence={"typed_methods": FieldConfidence(source="absent")} if _missing_info else {},
)
```

### Step 3: Write 3 unit tests

In `tests/unit/workers/test_understand.py`, add class `TestHG07GenericMissingInfo`:
- `test_generic_adapter_emits_missing_info_entry`
- `test_generic_adapter_confidence_absent`
- `test_known_adapter_no_missing_info`

## Failure modes

### Failure mode 1: Circular import in _entry.py

**Detection**: `ImportError: cannot import name GenericExtractor`
**Resolution**: Move import inside function body (lazy import)
**Gate**: Module import

### Failure mode 2: ProductEvidence.missing_info not serialized correctly

**Detection**: Schema validation error on understand output
**Resolution**: MissingInfoEntry is a pydantic model — it serializes as dict automatically
**Gate**: Schema validation

### Failure mode 3: Python/TypeScript adapters accidentally trigger missing_info

**Detection**: Test `test_known_adapter_no_missing_info` fails
**Resolution**: Ensure isinstance check is precise — only GenericExtractor, not base PlatformExtractor
**Gate**: Unit test

## Task-specific review checklist

- [ ] `isinstance(_adapter, GenericExtractor) or _adapter is None` condition is correct
- [ ] `_missing_info` list is initialized before any use
- [ ] ProductEvidence.missing_info receives `_missing_info`
- [ ] ProductEvidence.confidence receives FieldConfidence when generic
- [ ] Python adapter: no missing_info emitted
- [ ] TypeScript adapter: no missing_info emitted
- [ ] Rust platform (generic): missing_info emitted with correct field/reason
- [x] All 3 tests pass

## Deliverables

1. Updated `src/launcher/workers/understand/extract/_entry.py`
2. 3 new tests in `TestHG07GenericMissingInfo`
3. Updated `plans/taskcards/TC-4017_generic-missing-info-entry.md` (Done)

## Acceptance checks

- [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -k "HG07 or MissingInfo or missing_info" -v` — 3 passed
- [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=no -q` — zero new failures (3548 passed, 6 pre-existing)

## Self-review

**What was done**: Added GenericExtractor detection in `run_extract()`. When platform maps to GenericExtractor or adapter is None, a `MissingInfoEntry(field="api_surface.typed_methods", ...)` is appended and wired into `ProductEvidence.missing_info`. `FieldConfidence(source="absent")` is added to `product_evidence.confidence["typed_methods"]`.

**Risk**: Low — all new code is in a try/except block; failure is non-fatal.

**Tests**: 3 tests pass. Python adapter correctly emits no missing_info. Rust adapter correctly emits missing_info with correct field and reason.

## E2E verification

```bash
# Verify missing_info emitted for Rust platform
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py \
  -k "HG07 or missing_info" -v

# Verify no missing_info for Python
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py \
  -k "known_adapter" -v
```

**Expected artifacts**:
- `tests/unit/workers/test_understand.py` — 3 new tests in `TestHG07GenericMissingInfo`
- `src/launcher/workers/understand/extract/_entry.py` — `_missing_info` detection after adapter resolution

## Integration boundary proven

**Upstream**: `get_extractor(platform)` registry → GenericExtractor detection in `_entry.py`
**Downstream**: `ProductEvidence.missing_info` → persisted in `UnderstandingBundle` → inspectable by downstream workers (Generate, Evaluate)
