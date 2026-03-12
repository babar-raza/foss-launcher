---
id: TC-HAL-02
title: "Contradiction resolver: lowercase API identifier detection"
status: Done
priority: Critical
owner: "Agent-B"
updated: "2026-03-11"
tags: ["hallucination", "understand", "contradiction-resolver"]
depends_on: ["TC-HAL-01"]
allowed_paths:
  - plans/taskcards/TC-HAL-02_contradiction-resolver-lowercase-api-check.md
  - src/launcher/workers/understand/extract/_contradiction_resolver.py
  - tests/unit/workers/understand/extract/test_contradiction_resolver.py
evidence_required:
  - reports/TC-HAL-02/evidence.md
---

# Taskcard TC-HAL-02 — Contradiction resolver: lowercase API identifier detection

## Objective
Extend Check 2 in `resolve_contradictions()` to catch lowercase API identifiers used in `api`-kind claims that are NOT in the API surface. Current Check 2 only catches PascalCase compound names and backtick-wrapped identifiers, missing `entity.visible`, `entity.excluded`, `create_box()`, `root_node()`, `Scene.properties()`.

## Required spec references
- `specs/claims_evidence.md` (Section: Visibility filtering)

## Scope
### In scope
- For `kind == "api"` claims only: extract dot-notation identifiers from claim text
- Verify extracted identifiers exist in `api_ids` (case-insensitive)
- If not found → downgrade claim to `visibility=internal`

### Out of scope
- Non-api kind claims (feature, format, install, etc.) — too many false positives on prose
- Changes to existing PascalCase/backtick check (Check 2 remains unchanged)

## Inputs
- `src/launcher/workers/understand/extract/_contradiction_resolver.py`

## Outputs
- Updated `_contradiction_resolver.py` with Check 2c for lowercase API identifiers
- Additional unit tests in `tests/unit/workers/understand/extract/test_contradiction_resolver.py`

## Allowed paths
- plans/taskcards/TC-HAL-02_contradiction-resolver-lowercase-api-check.md
- src/launcher/workers/understand/extract/_contradiction_resolver.py
- tests/unit/workers/understand/extract/test_contradiction_resolver.py

### Allowed paths rationale
Same file as TC-HAL-01. This task extends the same function. Implement as separate step after TC-HAL-01 to avoid merge conflict.

## Implementation steps

### Step 1: Add Check 2c to resolve_contradictions()
After Check 2b (from TC-HAL-01), add:
```python
# Check 2c: lowercase dot-notation API identifiers for api-kind claims
if not was_modified and api_ids and claim.kind == "api":
    # Extract identifiers from obj.member or obj.member() patterns
    dot_refs = re.findall(r'\b\w+\.([a-z_]\w*)\b', claim.text)
    for ref in dot_refs:
        if len(ref) < 3:
            continue  # skip very short names (x, id, etc.)
        if ref.lower() not in api_ids:
            claim = claim.model_copy(update={"visibility": "internal"})
            contradiction_log.append({
                "claim_id": claim.claim_id,
                "type": "unknown_lowercase_api",
                "original_text": claim.text[:200],
                "resolution": f"downgraded to internal — '.{ref}' not in API surface",
                "evidence": f"api_ids does not contain '{ref.lower()}'",
            })
            was_modified = True
            break
```

### Step 2: Add unit tests
Add to `tests/unit/workers/understand/extract/test_contradiction_resolver.py`:
- `test_lowercase_dot_identifier_unknown` — api-kind claim "set entity.visible = True", api_ids empty → downgraded
- `test_lowercase_dot_identifier_known` — api-kind claim "call obj.name", api_ids contains "name" → not downgraded
- `test_feature_kind_not_checked` — feature-kind claim with unknown dot identifier → NOT downgraded (kind guard)
- `test_short_identifier_skipped` — api-kind claim "use obj.id" — "id" < 3 chars? No, 2 chars < 3 → skipped

## Failure modes

### Failure mode 1: False positives on common attribute patterns
**Detection**: Claims like "use obj.name" where `name` is a Python built-in attribute → caught if `name` not in api_ids
**Resolution**: Limit to `api` kind claims. Most false positives are in feature-kind prose. Accept some loss on ambiguous api claims.
**Gate**: Run full understand test suite; verify 0 regressions

### Failure mode 2: Python dunder or magic methods
**Detection**: Claims about `obj.__len__()` → `__len__` starts with `_` and won't be in api_ids
**Resolution**: The regex `[a-z_]\w*` would match `__len__`. However, such claims would already be filtered as internal by `_classify_claims.py`. Acceptable false-positive if it fires; the double-filtering is safe.
**Gate**: Unit test verifies `__dunder__` calls don't crash the function

### Failure mode 3: Claims about third-party objects
**Detection**: "use pandas.DataFrame.shape" → `shape` not in api_ids → downgraded
**Resolution**: Contamination filter (`_filter_contaminated_claims`) should catch third-party references before the resolver runs. The resolver is a secondary guard.
**Gate**: Check that contamination filter runs BEFORE contradiction resolver in _entry.py execution order. CONFIRMED: contamination filter runs at B.4d AFTER resolver at B.4b — acceptable since resolver fires first and the claim gets downgraded (same outcome).

## Task-specific review checklist
1. [ ] Check 2c only fires on `claim.kind == "api"` claims
2. [ ] Minimum identifier length check (< 3 chars → skip) to avoid false positives on `id`, `x`, etc.
3. [ ] `contradiction_log` entry has `type: "unknown_lowercase_api"`
4. [ ] Unit test: unknown lowercase API identifier in api-kind claim → downgraded
5. [ ] Unit test: known lowercase identifier → not downgraded
6. [ ] Unit test: feature-kind claim with unknown dot identifier → NOT downgraded
7. [ ] No regressions in full test suite
<!-- Documentation checks (AG-019 — required when modifying src/launcher/** or specs/**) -->
8. [ ] Docstrings updated for all new/changed public functions
9. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
10. [ ] Schema `"description"` fields present for all new/changed properties
<!-- Docs layer checks (AG-019 extension — docs/guides/ ownership map) -->
11. [ ] Checked `docs/README.md` ownership map — if a trigger event applies, relevant guide updated
12. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables
1. Updated `src/launcher/workers/understand/extract/_contradiction_resolver.py` (added Check 2c)
2. Additional unit tests
3. `reports/TC-HAL-02/evidence.md`

## Acceptance checks
1. [ ] `test_lowercase_dot_identifier_unknown` PASS
2. [ ] `test_lowercase_dot_identifier_known` PASS
3. [ ] `test_feature_kind_not_checked` PASS
4. [ ] Full understand test suite 0 regressions

## Self-review
### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: contradiction_resolver checks PASS
- [ ] Evidence captured: reports/TC-HAL-02/evidence.md
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --since HEAD~N` (or `--uncommitted` on orphan/single-commit branch) — clean / acknowledged

## E2E verification
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/extract/test_contradiction_resolver.py -v
```

**Expected results**:
- All new tests PASS
- Zero regressions in tests/unit/workers/understand/

## Integration boundary proven
**Upstream**: `_entry.py` calls resolver after LLM extraction
**Downstream**: `_validate_and_normalize_claims()` filters to visibility=public
**Contract**: `Claim.kind == "api"` + `Claim.visibility` fields
