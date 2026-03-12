---
id: TC-4251
title: "BUG: Fix EnumMember.get() AttributeError in _build_api_facts"
status: Done
priority: Critical
owner: "Agent"
updated: "2026-03-12"
tags: [understand, extraction-database, bugfix, enum, crash]
depends_on: [TC-4244]
allowed_paths:
  - plans/taskcards/TC-4251_understand-fix-enum-member-getattr.md
  - src/launcher/workers/understand/extract/_entry.py
  - tests/unit/workers/understand/extract/test_build_api_facts.py
evidence_required:
  - reports/TC-4251/evidence.md
---

# Taskcard TC-4251 — BUG: Fix EnumMember.get() AttributeError in _build_api_facts

## Objective

TC-4244 introduced `_build_api_facts()` which iterates over `ClassBrief.enums`
members and calls `member.get("name", "")` assuming dict-like access. However,
`EnumMember` is a Pydantic model with a `.name` attribute, not a dict. This
crashes the Understand worker on any repo with enum classes, blocking the full
pipeline.

## Required spec references

- `specs/worker_understand.md` (Section: ExtractionDatabase population)

## Scope

### In scope
- Fix line 190 in `_entry.py`: replace `member.get("name", "")` with `getattr(member, "name", "")`
- Add a unit test that passes an `EnumMember` Pydantic model to `_build_api_facts`
  and confirms it extracts the member name without error

### Out of scope
- Any other changes to `_build_api_facts` logic
- Changes to the `EnumMember` model itself

## Inputs

- `src/launcher/workers/understand/extract/_entry.py` line 190 — bug location
- `src/launcher/models/product.py` — `EnumMember` Pydantic model definition

## Outputs

- Fixed `_entry.py` — no crash on Pydantic `EnumMember` objects
- New test confirming `_build_api_facts` handles `EnumMember` correctly

## Allowed paths

- plans/taskcards/TC-4251_understand-fix-enum-member-getattr.md
- src/launcher/workers/understand/extract/_entry.py
- tests/unit/workers/understand/extract/test_build_api_facts.py

### Allowed paths rationale

`_entry.py` is the sole location of the bug. One new test file.

## Implementation steps

### Step 1: Fix line 190

Change:
```python
member_name = member if isinstance(member, str) else member.get("name", "")
```
To:
```python
member_name = member if isinstance(member, str) else getattr(member, "name", "")
```

### Step 2: Write unit test

Create `tests/unit/workers/understand/extract/test_build_api_facts.py` with:
- A test that constructs a `ClassBrief` with an `EnumBrief` containing `EnumMember` objects
- Calls `_build_api_facts(api_surface, product)` and asserts no exception and correct fact IDs

### Step 3: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/extract/ -v -q
```

## Failure modes

### Failure mode 1: Other non-dict member types in enums list

**Detection**: Different AttributeError on a different attribute name.
**Resolution**: Use `getattr(member, "name", "") or (member if isinstance(member, str) else "")` pattern.
**Gate**: Unit test with multiple member types

### Failure mode 2: Empty enum members list

**Detection**: No facts produced — no error.
**Resolution**: Guard with `or []` is already present on line 189.
**Gate**: Existing handling is correct.

### Failure mode 3: String members (legacy data)

**Detection**: `isinstance(member, str)` branch still needed.
**Resolution**: Keep the `isinstance(member, str)` check — the `else` branch now uses `getattr` instead of `.get`.
**Gate**: Test with both str and EnumMember inputs.

## Task-specific review checklist

1. [ ] Line 190 uses `getattr(member, "name", "")` not `member.get("name", "")`
2. [ ] `isinstance(member, str)` guard still present for legacy str members
3. [ ] Unit test: EnumMember Pydantic model → fact extracted correctly
4. [ ] Unit test: str member → still works
5. [ ] Pilot run no longer crashes at `_build_api_facts`
6. [ ] No other `.get()` calls on potentially non-dict objects in `_build_api_facts`
7. [ ] Docstrings: function docstring unchanged (no new behavior)
8. [ ] Spec: no new behavior, bug fix only
9. [ ] Schema: no changes
10. [ ] `docs/README.md`: N/A
11. [ ] No new `docs/guides/` file added

## Deliverables

1. Fixed `src/launcher/workers/understand/extract/_entry.py` (1-line change)
2. New `tests/unit/workers/understand/extract/test_build_api_facts.py`

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -v` — all pass
2. [ ] Pilot run proceeds past Understand worker without crash
3. [ ] `_build_api_facts` produces correct fact IDs for enum members

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: pilot run past Understand PASS
- [ ] Evidence captured: reports/TC-4251/evidence.md
- [ ] Doc freshness: bug fix only, no spec drift

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -v -q
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-cells-foss-python.yaml
```

**Expected results**:
- All understand tests pass
- Pilot run proceeds past Understand (no AttributeError)

## Integration boundary proven

**Upstream**: `api_surface.class_briefs[].enums[].members[]` — may be `str` or `EnumMember`
**Downstream**: `ExtractionDatabase.api_facts` — populated with correct enum member names
**Contract**: `_build_api_facts` handles both str and Pydantic-model enum members
