---
id: TC-HAL-05
title: "Fix () appended to properties in docstring claim harvesting"
status: Done
priority: High
owner: "Agent-B"
updated: "2026-03-11"
tags: ["hallucination", "understand", "docstring"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-HAL-05_docstring-property-callable-fix.md
  - src/launcher/workers/understand/extract/_entry.py
  - tests/unit/workers/understand/test_extract.py
evidence_required:
  - reports/TC-HAL-05/evidence.md
---

# Taskcard TC-HAL-05 — Fix () appended to properties in docstring claim harvesting

## Objective
`_harvest_docstring_claims_raw()` appends `()` to all `typed_methods` entries unconditionally (`f"{brief.name}.{ms.name}(): {doc}"`). If a `@property` is misclassified as a method in `method_details` by the AST analyzer, the harvested claim will incorrectly represent it as callable. Fix by checking against `typed_properties` before appending `()`.

## Required spec references
- `specs/worker_understand.md` (Section: Phase B.2b Docstring harvesting)
- `specs/claims_evidence.md` (Section: Claim kinds — api)

## Scope
### In scope
- In `_harvest_docstring_claims_raw()`, build `property_name_set` from `brief.typed_properties`
- When rendering `ms.name`, omit `()` if `ms.name` is in `property_name_set`
- Add per-property claims for `typed_properties` with non-trivial docstrings (>20 chars, not boilerplate)

### Out of scope
- Fixing the AST analyzer's classification of @property methods (separate concern)
- Changing typed_methods/typed_properties model fields

## Inputs
- `src/launcher/workers/understand/extract/_entry.py:372–448` — `_harvest_docstring_claims_raw()`

## Outputs
- Updated `_entry.py` with property-aware rendering
- Unit tests

## Allowed paths
- plans/taskcards/TC-HAL-05_docstring-property-callable-fix.md
- src/launcher/workers/understand/extract/_entry.py
- tests/unit/workers/understand/test_extract.py

### Allowed paths rationale
Only `_entry.py` changes. Tests extend existing test_extract.py.

## Implementation steps

### Step 1: Build property_name_set in _harvest_docstring_claims_raw()
In the per-class brief loop (around line 424), before the typed_methods loop:
```python
# Build property name set for () omission (TC-HAL-05)
property_name_set = {p.name for p in (brief.typed_properties or [])}
```

### Step 2: Use property_name_set when rendering method claims
Change line 439 from:
```python
"text": f"{brief.name}.{ms.name}(): {doc}",
```
to:
```python
"text": (
    f"{brief.name}.{ms.name}: {doc}"
    if ms.name in property_name_set
    else f"{brief.name}.{ms.name}(): {doc}"
),
```

### Step 3: Add per-property claims for typed_properties
After the typed_methods loop (around line 448), add a new loop:
```python
# Per-property docstring claims (TC-HAL-05)
for pd in (brief.typed_properties or [])[:10]:  # cap at 10 per class
    if not pd.docstring_snippet:
        continue
    doc = pd.docstring_snippet.strip()
    if len(doc) < 20:
        continue
    # Skip boilerplate
    doc_lower = doc.lower()
    if any(doc_lower.startswith(bp) for bp in _BOILERPLATE_STARTS) and len(doc) < 50:
        continue
    raw_claims.append({
        "text": f"{brief.name}.{pd.name}: {doc}",
        "kind": "api",
        "visibility": "public",
        "claim_source": "docstring",
        "evidence": [{
            "source_file": f"docstring:{brief.name}.{pd.name}",
            "snippet": doc[:200],
        }],
    })
```

### Step 4: Add unit tests
Add to `tests/unit/workers/understand/test_extract.py`:
- `test_property_in_typed_methods_no_parens` — ClassBrief with `parent_nodes` in both typed_methods and typed_properties → harvested claim text does NOT contain `parent_nodes()`
- `test_pure_method_has_parens` — ClassBrief with `add_child` in typed_methods but NOT in typed_properties → harvested claim text DOES contain `add_child()`
- `test_typed_properties_claims_added` — ClassBrief with typed_properties having non-trivial docstring → additional claim generated without `()`

## Failure modes

### Failure mode 1: typed_properties is None or empty
**Detection**: `property_name_set` is empty → all typed_methods get `()` (original behavior preserved)
**Resolution**: This is correct fallback behavior — if no property data, we can't know what's a property.
**Gate**: Unit test with empty typed_properties → all methods get ()

### Failure mode 2: Same name in both typed_methods and typed_properties
**Detection**: Some Python properties have both getter and setter methods — getter is @property, setter is @foo.setter
**Resolution**: If `ms.name` is in `property_name_set`, we render without `()`. This is correct — the caller should use it as a property, not a method.
**Gate**: Unit test with name in both → no () rendered (property access is correct)

### Failure mode 3: max_claims cap reached before property claims
**Detection**: 200-claim cap reached before per-property claims
**Resolution**: Per-property claims are added AFTER per-method claims in the same loop — they share the 200 cap. This is acceptable. Properties add ≤10 claims per class. Consider raising cap further if needed.
**Gate**: Log warning when cap reached (already exists from TC-4094)

## Task-specific review checklist
1. [ ] `property_name_set` built from `brief.typed_properties` (not typed_methods)
2. [ ] `()` omitted when `ms.name in property_name_set`
3. [ ] Per-property claims use `pd.name` (not `pd.name + "()"`)
4. [ ] Per-property claims have `claim_source: "docstring"` for correct provenance
5. [ ] Boilerplate filter applied to property docstrings same as method docstrings
6. [ ] Unit test: method in typed_methods + property_name_set → no ()
7. [ ] Unit test: method NOT in property_name_set → () retained
8. [ ] No regressions in full test suite
<!-- Documentation checks (AG-019 — required when modifying src/launcher/** or specs/**) -->
9. [ ] Docstrings updated for all new/changed public functions
10. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
11. [ ] Schema `"description"` fields present for all new/changed properties
<!-- Docs layer checks (AG-019 extension — docs/guides/ ownership map) -->
12. [ ] Checked `docs/README.md` ownership map — if a trigger event applies, relevant guide updated
13. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables
1. Updated `src/launcher/workers/understand/extract/_entry.py`
2. Unit tests
3. `reports/TC-HAL-05/evidence.md`

## Acceptance checks
1. [ ] `test_property_in_typed_methods_no_parens` PASS
2. [ ] `test_pure_method_has_parens` PASS
3. [ ] `test_typed_properties_claims_added` PASS
4. [ ] Full understand test suite 0 regressions

## Self-review
### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: docstring harvesting checks PASS
- [ ] Evidence captured: reports/TC-HAL-05/evidence.md
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --since HEAD~N` (or `--uncommitted` on orphan/single-commit branch) — clean / acknowledged

## E2E verification
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -q
```

**Expected results**:
- All 3 new tests PASS
- Zero regressions in tests/unit/workers/understand/

## Integration boundary proven
**Upstream**: `api_surface.class_briefs[].typed_methods` and `typed_properties` populated by `_api_surface.py`
**Downstream**: Harvested raw claims passed to `_validate_and_normalize_claims()`
**Contract**: `ClassBrief.typed_methods` (list[MethodSignature]) and `ClassBrief.typed_properties` (list[PropertyRecord]) fields
