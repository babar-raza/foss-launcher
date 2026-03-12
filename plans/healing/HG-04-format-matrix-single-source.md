# HG-04 — Format Matrix Single Source of Truth

**Status**: Not Started
**Gap linkage**: G4 (format_matrix still duplicated across ApiSurface and ProductEvidence)
**Role**: Senior engineer. Drop-in, production-ready.
**Priority**: High

## Context

The plan (Phase 4, "Evidence Model Cleanup") required:
> Remove `format_matrix` from `ApiSurface` — move to `ProductEvidence` as single source
> (add deprecation alias)

Currently `ApiSurface.format_matrix: list[FormatRecord]` and
`ProductEvidence.supported_formats: list[str]` both carry format data, creating two
sources of truth. The plan says `ProductEvidence` should hold `format_matrix: list[FormatRecord]`
as the canonical field, and `ApiSurface.format_matrix` should be a property that delegates.

Downstream consumers `contradiction.py` and `format_truth.py` both read from
`api_surface.format_matrix`. If we move the data without an alias, both break.

## Scope

### Fix

1. Add `format_matrix: list[FormatRecord]` field to `ProductEvidence` in
   `models/understanding.py`
2. Add a `@property format_matrix` deprecation alias on `ApiSurface` in
   `models/product.py` that delegates to a provided `ProductEvidence` reference
   — OR — keep the field on `ApiSurface` but emit a deprecation warning when
   accessed and ensure `ProductEvidence` is the primary recipient after extraction
3. Update `_entry.py` to populate `ProductEvidence.format_matrix` directly
4. Update `evaluate/checks/contradiction.py` and `evaluate/checks/format_truth.py`
   to read from `api_surface.format_matrix` (unchanged — alias handles it) OR from
   the passed `product_evidence.format_matrix` if the worker can provide it
5. Write tests verifying single-source behavior

### Decision required before implementation

Option A (simpler): Keep `ApiSurface.format_matrix` as is. Copy it into
`ProductEvidence.format_matrix` during `_entry.py` assembly. Both fields exist;
`ProductEvidence` is the "canonical" one; `ApiSurface` is the "pass-through."
Add a `TODO: deprecate ApiSurface.format_matrix` comment.

Option B (correct): Add `@property` on `ApiSurface` that reads from an injected
`ProductEvidence` reference. More complex, requires `ApiSurface` to hold a weak ref.

**Recommendation**: Option A first (safe, backwards-compatible, lower risk).
Option B as follow-up once all consumers have migrated.

### Allowed paths

```
src/launcher/models/understanding.py          (add format_matrix to ProductEvidence)
src/launcher/workers/understand/extract/_entry.py  (populate both fields)
tests/unit/workers/test_understand.py         (new tests)
plans/taskcards/TC-4010_format_matrix_dedup.md
```

### Forbidden

`models/product.py` (ApiSurface) — do NOT modify in this taskcard.
`evaluate/checks/contradiction.py` — read-only.
`evaluate/checks/format_truth.py` — read-only.

## Acceptance checks

### CLI
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -k "format_matrix" -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=no -q
```

### Tests
- `test_product_evidence_has_format_matrix_field`: ProductEvidence can hold list[FormatRecord]
- `test_entry_populates_product_evidence_format_matrix`: mock extraction → ProductEvidence.format_matrix set
- `test_api_surface_format_matrix_unchanged`: existing ApiSurface.format_matrix still works
- `test_format_matrix_values_consistent`: same formats in both places after extraction

### Config respected end-to-end
- Contradiction check still works (reads ApiSurface.format_matrix, which is still populated)
- Format truth check still works (same)

### No mock data in production paths
- Tests use FormatRecord instances, not string mocks

## Deliverables

1. Updated `models/understanding.py` with `format_matrix` in `ProductEvidence`
2. Updated `_entry.py` to copy format_matrix into ProductEvidence after extraction
3. 4+ new tests
4. `plans/taskcards/TC-4010_format_matrix_dedup.md`

## Hard rules

- Do NOT break `api_surface.format_matrix` access — downstream code reads this
- ProductEvidence.format_matrix uses Option A (copy, not alias) for safety
- Forward-compatible: when Option B is implemented, only _entry.py changes

## Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Consistency | One canonical field in ProductEvidence; ApiSurface still works |
| Correctness | Contradiction resolver and format_truth both still function |
| Minimality | Only 2 source files changed; no cascading changes |
| Testability | 4 unit tests verify both paths |
| Robustness | Empty format_matrix handled in both fields |

## Now (runbook)

```
1. Read src/launcher/models/understanding.py (ProductEvidence section)
2. Read src/launcher/workers/understand/extract/_entry.py (ProductEvidence assembly)
3. Add to ProductEvidence:
   format_matrix: list[FormatRecord] = Field(default_factory=list)
4. In _entry.py ProductEvidence constructor, add:
   format_matrix=_format_matrix,
5. Write 4 tests
6. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -v
7. Run full suite
```
