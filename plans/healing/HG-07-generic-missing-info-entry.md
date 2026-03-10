# HG-07 — GenericExtractor Should Emit MissingInfoEntry

**Status**: Not Started
**Gap linkage**: G7 (GenericExtractor does not emit MissingInfoEntry on fallback)
**Role**: Senior engineer. Drop-in, production-ready.
**Priority**: Medium

## Context

The plan states:
> "Generic fallback produces ClassBrief with names only + MissingInfoEntry"

The principle (from humming-greeting-kay): "Fail-open with reporting. Extraction
failures produce MissingInfoEntry records, not silent empty fields. Downstream workers
can distinguish 'no formats exist' from 'extraction failed'."

Currently, when `get_extractor("rust")` returns a `GenericExtractor`, the extraction
proceeds and produces ClassBrief objects with name-only entries (no typed_methods).
But no `MissingInfoEntry` is created to signal that typed extraction was unavailable.

This means:
- A Rust ClassBrief with empty typed_methods looks identical to a Python ClassBrief
  with no typed members
- Downstream workers cannot distinguish "extraction failed" from "no methods exist"
- The `FieldConfidence` model exists for exactly this purpose but is never populated
  for the generic fallback case

## Scope

### Fix

1. In `_entry.py`, after adapter extraction, detect when `GenericExtractor` was used:
   ```python
   from launcher.workers.understand.adapters._generic import GenericExtractor
   if isinstance(_adapter, GenericExtractor) or _adapter is None:
       _missing_info.append(MissingInfoEntry(
           field="api_surface.typed_methods",
           reason=f"No typed extraction available for platform '{product.platform}'",
           attempted_strategies=["generic_regex"],
           fallback_used="regex",
       ))
   ```
2. Wire `_missing_info` into the `ProductEvidence` constructor
3. Also add `FieldConfidence(source="absent")` to `product_evidence.confidence["typed_methods"]`
   when generic fallback was used
4. Write tests confirming this behavior

### Allowed paths

```
src/launcher/workers/understand/extract/_entry.py
tests/unit/workers/test_understand.py
tests/integration/test_understand_pipeline.py
plans/taskcards/TC-4013_generic_missing_info.md
```

### Forbidden

`adapters/_generic.py` — the extractor itself should not change.
`models/understanding.py` — MissingInfoEntry already exists.

## Acceptance checks

### CLI
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -k "missing_info or MissingInfo" -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=no -q
```

### Tests
- `test_generic_adapter_emits_missing_info_entry`: when platform is "rust" (generic),
  ProductEvidence.missing_info has entry for "api_surface.typed_methods"
- `test_generic_adapter_confidence_absent`: FieldConfidence for "typed_methods" is "absent"
- `test_python_adapter_no_missing_info_for_typed_methods`: Python platform → no missing_info
  for typed_methods (Python has full AST extraction)
- Failure path: MissingInfoEntry does not break bundle serialization

### Config respected end-to-end
- MissingInfoEntry is persisted in UnderstandingBundle artifacts
- Downstream workers can read `product_evidence.missing_info` to adjust behavior

### No mock data in production paths
- Tests use `get_extractor("rust")` and verify actual _entry.py dispatch behavior

## Deliverables

1. Updated `_entry.py` with GenericExtractor detection + MissingInfoEntry emission
2. 3+ new tests
3. `plans/taskcards/TC-4013_generic_missing_info.md`

## Hard rules

- Detection uses `isinstance(_adapter, GenericExtractor)` — not string comparison on platform
- Also triggers when `_adapter is None` (adapter resolution failed)
- Does NOT emit MissingInfoEntry for known-good adapters (Python, TypeScript) unless
  their extraction actually fails
- No import of _generic.py in test code — tests should use the extractor registry

## Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Correctness | MissingInfoEntry present when generic fallback used |
| Observability | FieldConfidence "absent" for typed_methods in generic case |
| Robustness | Serialization of MissingInfoEntry works; no crash |
| Minimality | Only _entry.py changed; 3 tests added |
| Consistency | Same MissingInfoEntry pattern as other failure paths |

## Now (runbook)

```
1. Read src/launcher/workers/understand/extract/_entry.py (lines 56-65)
2. After adapter resolution, add isinstance check:
   _missing_info: list[MissingInfoEntry] = []
   if isinstance(_adapter, GenericExtractor):
       _missing_info.append(MissingInfoEntry(
           field="api_surface.typed_methods",
           reason=f"No typed extraction for platform '{product.platform}'",
           attempted_strategies=["generic_regex"],
           fallback_used="regex",
       ))
3. In ProductEvidence constructor (line ~205), add:
   missing_info=_missing_info,
   confidence={"typed_methods": FieldConfidence(source="absent")} if _missing_info else {}
4. Write 3 tests
5. Run full suite
```
