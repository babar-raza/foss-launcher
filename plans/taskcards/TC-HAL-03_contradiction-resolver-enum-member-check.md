---
id: TC-HAL-03
title: "Contradiction resolver: enum member verification"
status: Done
priority: High
owner: "Agent-B"
updated: "2026-03-11"
tags: ["hallucination", "understand", "contradiction-resolver"]
depends_on: ["TC-HAL-01"]
allowed_paths:
  - plans/taskcards/TC-HAL-03_contradiction-resolver-enum-member-check.md
  - src/launcher/workers/understand/extract/_contradiction_resolver.py
  - tests/unit/workers/understand/extract/test_contradiction_resolver.py
evidence_required:
  - reports/TC-HAL-03/evidence.md
---

# Taskcard TC-HAL-03 — Contradiction resolver: enum member verification

## Objective
Verify `ClassName.MEMBER` patterns in claims against actual enum members in the API surface. Catches hallucinations like `FileFormat.OBJ` when `OBJ` is not a member of the `FileFormat` enum in the Python bindings.

## Required spec references
- `specs/claims_evidence.md` (Section: Visibility filtering)
- `specs/worker_understand.md` (Section: API surface extraction)

## Scope
### In scope
- Build `enum_member_map: dict[str, set[str]]` from `api_surface.enums`
- Add Check 2d: scan claim text for `ClassName.ALL_CAPS_MEMBER` patterns
- If class is a known enum AND member not in its member set → downgrade claim

### Out of scope
- Non-enum class member access (method calls, property access — covered by TC-HAL-01/02)
- Creating EnumRecord data — already populated by `_api_surface.py`

## Inputs
- `src/launcher/workers/understand/extract/_contradiction_resolver.py`
- `src/launcher/models/product.py` — `EnumRecord` model with `.name` and `.members` fields

## Outputs
- Updated `_contradiction_resolver.py` with Check 2d
- Unit tests

## Allowed paths
- plans/taskcards/TC-HAL-03_contradiction-resolver-enum-member-check.md
- src/launcher/workers/understand/extract/_contradiction_resolver.py
- tests/unit/workers/understand/extract/test_contradiction_resolver.py

### Allowed paths rationale
Same file as TC-HAL-01/02. Implement after TC-HAL-01.

## Implementation steps

### Step 1: Build enum_member_map
In `resolve_contradictions()`, after building `api_ids`, add:
```python
# Build enum member lookup for Check 2d
enum_member_map: dict[str, set[str]] = {}
if api_surface:
    for enum_rec in getattr(api_surface, "enums", []) or []:
        member_names = {m.name.lower() for m in (enum_rec.members or [])}
        enum_member_map[enum_rec.name.lower()] = member_names
        # Also add class_briefs that are enums
    for cls in getattr(api_surface, "class_briefs", []) or []:
        for enum_rec in (cls.enums or []):
            member_names = {m.name.lower() for m in (enum_rec.members or [])}
            enum_member_map[enum_rec.name.lower()] = member_names
```

### Step 2: Add Check 2d
After Check 2c:
```python
# Check 2d: Enum member verification — ClassName.MEMBER
if not was_modified and enum_member_map:
    # Pattern: PascalCase class name followed by ALL_CAPS_MEMBER
    enum_refs = re.findall(r'\b([A-Z][a-zA-Z0-9]+)\.([A-Z][A-Z0-9_]+)\b', claim.text)
    for cls_name, member_name in enum_refs:
        cls_lower = cls_name.lower()
        if cls_lower not in enum_member_map:
            continue  # not a known enum class — skip
        if member_name.lower() not in enum_member_map[cls_lower]:
            claim = claim.model_copy(update={"visibility": "internal"})
            contradiction_log.append({
                "claim_id": claim.claim_id,
                "type": "enum_member_unknown",
                "original_text": claim.text[:200],
                "resolution": f"downgraded to internal — '{cls_name}.{member_name}' member not in enum",
                "evidence": f"enum_member_map['{cls_lower}'] = {list(enum_member_map[cls_lower])[:5]}",
            })
            was_modified = True
            break
```

### Step 3: Add unit tests
- `test_enum_member_unknown` — FileFormat enum with members FBX, GLTF; claim references FileFormat.OBJ → downgraded
- `test_enum_member_known` — FileFormat.FBX → not downgraded
- `test_non_enum_class_not_checked` — ClassName.MEMBER where ClassName not in enum_member_map → not downgraded
- `test_empty_enum_map` — enum_member_map empty → no change

## Failure modes

### Failure mode 1: Enum class name mismatch
**Detection**: API surface uses `FileFormat` but code uses `fileformat` — case-insensitive lookup handles this
**Resolution**: Both `cls_lower` and `enum_member_map` keys use `.lower()` → case-insensitive match. Safe.
**Gate**: Unit test with mixed-case class name

### Failure mode 2: Partial enum extraction
**Detection**: Not all enum members extracted from the Python bindings (AST might miss dynamically assigned members)
**Resolution**: Only downgrade when class IS in enum_member_map. If FileFormat is not in enum_member_map (not extracted), no downgrade happens — safe degradation.
**Gate**: Verify `enum_member_map` is populated when running against aspose.threed repo

### Failure mode 3: ALL_CAPS pattern matches non-enum constants
**Detection**: Regex `[A-Z][A-Z0-9_]+` might match version strings like V3, ERROR_CODE
**Resolution**: The outer guard `cls_lower not in enum_member_map` ensures we only flag when the class is a known enum. Non-enum constants won't be in enum_member_map.
**Gate**: Unit test with ALL_CAPS constant on non-enum class

## Task-specific review checklist
1. [ ] `enum_member_map` populated from both `api_surface.enums` and `cls.enums` within `class_briefs`
2. [ ] Check 2d only fires when class IS in `enum_member_map`
3. [ ] All comparisons use lowercase for case-insensitivity
4. [ ] `contradiction_log` entry has `type: "enum_member_unknown"`
5. [ ] Unit test: known enum, unknown member → downgraded
6. [ ] Unit test: known enum, known member → not downgraded
7. [ ] Unit test: non-enum class → not downgraded
<!-- Documentation checks (AG-019 — required when modifying src/launcher/** or specs/**) -->
8. [ ] Docstrings updated for all new/changed public functions
9. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
10. [ ] Schema `"description"` fields present for all new/changed properties
<!-- Docs layer checks (AG-019 extension — docs/guides/ ownership map) -->
11. [ ] Checked `docs/README.md` ownership map — if a trigger event applies, relevant guide updated
12. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables
1. Updated `_contradiction_resolver.py` with Check 2d
2. Additional unit tests
3. `reports/TC-HAL-03/evidence.md`

## Acceptance checks
1. [ ] `test_enum_member_unknown` PASS
2. [ ] `test_enum_member_known` PASS
3. [ ] `test_non_enum_class_not_checked` PASS
4. [ ] `test_empty_enum_map` PASS

## Self-review
### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: enum member check PASS
- [ ] Evidence captured: reports/TC-HAL-03/evidence.md
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --since HEAD~N` (or `--uncommitted` on orphan/single-commit branch) — clean / acknowledged

## E2E verification
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/extract/test_contradiction_resolver.py -v
```

**Expected results**:
- All 4 new tests PASS
- Zero regressions in tests/unit/workers/understand/

## Integration boundary proven
**Upstream**: api_surface.enums populated by `_api_surface.py`
**Downstream**: contradiction_log recorded in extraction_audit.json
**Contract**: EnumRecord model in api_surface.enums with name + members fields
