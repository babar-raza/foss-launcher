---
id: TC-HAL-01
title: "Contradiction resolver: method-vs-property type check"
status: Done
priority: Critical
owner: "Agent-B"
updated: "2026-03-11"
tags: ["hallucination", "understand", "contradiction-resolver"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-HAL-01_contradiction-resolver-method-property-split.md
  - src/launcher/workers/understand/extract/_contradiction_resolver.py
  - tests/unit/workers/understand/extract/test_contradiction_resolver.py
evidence_required:
  - reports/TC-HAL-01/evidence.md
---

# Taskcard TC-HAL-01 — Contradiction resolver: method-vs-property type check

## Objective
Add a method-vs-property type check to `resolve_contradictions()` so that claims calling `foo()` where `foo` is a property (not a method) are downgraded to `visibility=internal`. This eliminates hallucinated method calls like `node.parent_nodes()`, `node.excluded()`, `node.root_node()`.

## Required spec references
- `specs/claims_evidence.md` (Section: Evidence anchor format, Visibility filtering)
- `specs/worker_understand.md` (Section: Phase B.4 Post-LLM validation)

## Scope
### In scope
- Add `method_ids` and `property_ids` sets built from `ClassBrief.methods` and `ClassBrief.properties`
- Add Check 2b: scan claim text for `identifier()` call patterns; if identifier is ONLY in `property_ids` and NOT in `method_ids`, downgrade claim to `visibility=internal`
- Unit tests for the new check

### Out of scope
- Changes to `ClassBrief` model (methods/properties already separated)
- Changes to `_api_surface.py` (already builds separate methods/properties lists)
- Changes to `_validation.py` (already filters by visibility=public)

## Inputs
- `src/launcher/workers/understand/extract/_contradiction_resolver.py` — current resolver
- `src/launcher/models/product.py` — `ClassBrief` model with `.methods` and `.properties` fields

## Outputs
- Updated `_contradiction_resolver.py` with method/property split in `resolve_contradictions()`
- New unit test file: `tests/unit/workers/understand/extract/test_contradiction_resolver.py`

## Allowed paths
- plans/taskcards/TC-HAL-01_contradiction-resolver-method-property-split.md
- src/launcher/workers/understand/extract/_contradiction_resolver.py
- tests/unit/workers/understand/extract/test_contradiction_resolver.py

### Allowed paths rationale
`_contradiction_resolver.py` is the only file that needs modification. Tests go in the existing tests/unit/workers/understand/extract/ directory.

## Implementation steps

### Step 1: Extend api_ids building in resolve_contradictions()
In `_contradiction_resolver.py:49–57`, alongside building `api_ids`, build two additional sets:
```python
method_ids: set[str] = set()
property_ids: set[str] = set()
if api_surface:
    for cls in getattr(api_surface, "class_briefs", []) or []:
        for m in cls.methods or []:
            method_ids.add(m.lower())
        for p in cls.properties or []:
            property_ids.add(p.lower())
```

### Step 2: Add Check 2b after existing Check 2
After the existing PascalCase/backtick check (lines 102–122), add:
```python
# Check 2b: method-call pattern on property-only identifier
if not was_modified and property_ids:
    call_refs = re.findall(r'\b([a-zA-Z_]\w+)\s*\(', claim.text)
    for ref in call_refs:
        ref_lower = ref.lower()
        if ref_lower in property_ids and ref_lower not in method_ids:
            claim = claim.model_copy(update={"visibility": "internal"})
            contradiction_log.append({
                "claim_id": claim.claim_id,
                "type": "method_property_mismatch",
                "original_text": claim.text[:200],
                "resolution": f"downgraded to internal — '{ref}' is a property, not a callable",
                "evidence": f"property_ids contains '{ref_lower}'; method_ids does not",
            })
            was_modified = True
            break
```

### Step 3: Write unit tests
Create `tests/unit/workers/understand/extract/test_contradiction_resolver.py` with tests:
1. `test_property_as_method_downgraded` — claim text "call node.parent_nodes()", ClassBrief with parent_nodes in properties only → assertion: resolved claim has visibility=internal
2. `test_method_as_method_passes` — claim text "call node.add_child_node()", ClassBrief with add_child_node in methods → assertion: resolved claim keeps visibility=public
3. `test_property_in_both_passes` — identifier in both methods and properties (edge case) → assertion: claim passes (not downgraded)
4. `test_no_api_surface_no_crash` — api_surface=None → assertion: no exception, claims unchanged

### Step 4: Run tests and verify
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/extract/test_contradiction_resolver.py -v
```

## Failure modes

### Failure mode 1: False positives on common word patterns
**Detection**: Legitimate method calls like `str()`, `list()`, `range()` get caught by call pattern if they happen to appear as property names in some class
**Resolution**: The pattern only fires when `ref_lower` is in `property_ids` AND NOT in `method_ids`. Built-in names are not in ClassBrief.properties so this can't happen. No action needed.
**Gate**: Self-review check — run against existing test suite with zero regressions expected

### Failure mode 2: Empty ClassBrief.properties list
**Detection**: If code_analyzer doesn't populate `properties`, `property_ids` is empty and Check 2b is a no-op
**Resolution**: This is safe — the check degrades gracefully to no-op. Log property_ids and method_ids sizes in debug log.
**Gate**: Unit test test_property_as_method_downgraded must use a fixture with populated properties list

### Failure mode 3: Claim references property from a different class
**Detection**: Class A has property `name`; claim about Class B calls `name()` → might not be a hallucination if Class B has a `name()` method
**Resolution**: The `property_ids` set is across ALL classes. If `name` is a property in ANY class, calling `name()` in ANY claim gets flagged. Mitigation: use `method_ids` override — if `name` is ALSO a method in any class, it passes. This is acceptable false-negative rate.
**Gate**: Review contradiction_log in extraction_audit to verify no legitimate method calls are being dropped

## Task-specific review checklist

1. [ ] `property_ids` and `method_ids` correctly populated from `ClassBrief.methods` and `ClassBrief.properties`
2. [ ] Check 2b only fires when identifier is in `property_ids` AND NOT in `method_ids`
3. [ ] Contradiction log entry has `type: "method_property_mismatch"` for traceability
4. [ ] Unit test covers property-only identifier → downgraded case
5. [ ] Unit test covers method identifier → not downgraded case
6. [ ] Unit test covers `api_surface=None` → no exception
7. [ ] No existing tests broken (zero regressions)
8. [ ] `was_modified` flag prevents double-downgrading
<!-- Documentation checks (AG-019 — required when modifying src/launcher/** or specs/**) -->
9. [ ] Docstrings updated for all new/changed public functions
10. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
11. [ ] Schema `"description"` fields present for all new/changed properties
<!-- Docs layer checks (AG-019 extension — docs/guides/ ownership map) -->
12. [ ] Checked `docs/README.md` ownership map — if a trigger event applies, relevant guide updated
13. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables
1. Updated `src/launcher/workers/understand/extract/_contradiction_resolver.py`
2. New test file `tests/unit/workers/understand/extract/test_contradiction_resolver.py`
3. `reports/TC-HAL-01/evidence.md` with test output

## Acceptance checks
1. [ ] `test_property_as_method_downgraded` PASS
2. [ ] `test_method_as_method_passes` PASS
3. [ ] `test_property_in_both_passes` PASS
4. [ ] `test_no_api_surface_no_crash` PASS
5. [ ] Full understand test suite passes with 0 regressions
6. [ ] `contradiction_log` emitted in `resolve_contradictions()` contains `type: "method_property_mismatch"` entries for property-as-method cases

## Self-review
### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: contradiction_resolver checks PASS
- [ ] Evidence captured: reports/TC-HAL-01/evidence.md
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --since HEAD~N` (or `--uncommitted` on orphan/single-commit branch) — clean / acknowledged

## E2E verification
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/extract/test_contradiction_resolver.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -q
```

**Expected results**:
- All 4 new tests PASS
- Zero regressions in tests/unit/workers/understand/

## Integration boundary proven
**Upstream**: `_entry.py` calls `resolve_contradictions(claims, api_surface, limitations)`
**Downstream**: Returned `resolved_claims` pass through `_validate_and_normalize_claims()` which filters to `visibility=public`
**Contract**: `Claim.visibility` field; downgraded claims have `visibility="internal"` and are filtered by validation
