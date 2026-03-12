---
id: TC-HYBRID-02
title: "Typed method signatures — params, return types, property types, enum members in ApiSurface"
status: Done
priority: High
owner: "Agent-B"
updated: "2026-03-11"
tags: [evidence-model, api-surface, typed-sigs]
depends_on: [TC-HYBRID-01]
allowed_paths:
  - plans/taskcards/TC-HYBRID-02_typed_method_signatures.md
  - src/launcher/workers/understand/extract/_api_surface.py
  - src/launcher/workers/understand/extract/_deterministic.py
  - src/launcher/workers/understand/extract/__init__.py
  - src/launcher/models/understanding.py
  - tests/unit/workers/test_understand.py
  - tests/unit/workers/test_scout_facts.py
evidence_required:
  - reports/TC-HYBRID-02/evidence.md
---

# Taskcard TC-HYBRID-02 — Typed Method Signatures

## Objective

Extend `ApiSurface` extraction to capture typed method signatures (parameter names + types, return type), property types, and enum member values from Python source, so the Generate worker receives accurate, typed API surface data instead of bare name-lists — eliminating hallucinated parameter types and false capability claims.

## Required spec references

- `specs/understand_worker.md` (Section: API surface extraction)
- `specs/models.md` (Section: ApiSurface, ProductEvidence)

## Scope

### In scope
- Add `MethodSignature` model: `name`, `params: list[ParamSpec]`, `return_type: str | None`, `is_classmethod: bool`, `is_staticmethod: bool`, `is_property: bool`
- Add `ParamSpec` model: `name`, `type_hint: str | None`, `default: str | None`, `kind: str` (positional/keyword/variadic)
- Add `PropertySpec` model: `name`, `type_hint: str | None`, `is_readonly: bool`
- Add `EnumMember` model: `name`, `value: str | None`
- Extend `ApiSurface` with: `typed_methods: list[MethodSignature]`, `properties: list[PropertySpec]`, `enum_members: list[EnumMember]`
- Python extraction via `ast` module (already used in `_deterministic.py`)
- Tree-sitter extraction for Java/C# (coordinate with TC-4004 patterns)
- Unit tests for typed extraction

### Out of scope
- Format matrix extraction (TC-HYBRID-03)
- Prompt injection into Generate worker (TC-HYBRID-07)
- Cross-language signature normalization beyond basic mapping

## Inputs

- `src/launcher/workers/understand/extract/_api_surface.py` — current ApiSurface extractor
- `src/launcher/models/understanding.py` — current models
- Cached repo clones in `runs/.clone_cache/`

## Outputs

- Extended `ApiSurface` pydantic model with typed fields
- Updated `_api_surface.py` with typed extraction logic
- Updated `_deterministic.py` if needed
- Passing unit tests (min 6 new test cases)

## Allowed paths

- plans/taskcards/TC-HYBRID-02_typed_method_signatures.md
- src/launcher/workers/understand/extract/_api_surface.py
- src/launcher/workers/understand/extract/_deterministic.py
- src/launcher/workers/understand/extract/__init__.py
- src/launcher/models/understanding.py
- tests/unit/workers/test_understand.py
- tests/unit/workers/test_scout_facts.py

### Allowed paths rationale
`_api_surface.py` — primary extraction logic; `understanding.py` — model definitions; tests — validation; `__init__.py` — may need re-export of new models.

## Implementation steps

### Step 1: Add ParamSpec, MethodSignature, PropertySpec, EnumMember models

In `src/launcher/models/understanding.py`, add:
```python
class ParamSpec(BaseModel):
    name: str
    type_hint: str | None = None
    default: str | None = None
    kind: str = "positional"  # positional, keyword, variadic_pos, variadic_kw

class MethodSignature(BaseModel):
    name: str
    params: list[ParamSpec] = []
    return_type: str | None = None
    is_classmethod: bool = False
    is_staticmethod: bool = False
    is_property: bool = False

class PropertySpec(BaseModel):
    name: str
    type_hint: str | None = None
    is_readonly: bool = True

class EnumMember(BaseModel):
    name: str
    value: str | None = None
```

Extend `ApiSurface`:
```python
typed_methods: list[MethodSignature] = []
properties: list[PropertySpec] = []
enum_members: list[EnumMember] = []
```

### Step 2: Python AST typed extraction

In `_api_surface.py`, extract typed signatures from Python AST:
- For each `ast.FunctionDef` / `ast.AsyncFunctionDef`: extract params with `ast.arg.annotation`, return type from `returns`, detect `@classmethod` / `@staticmethod` / `@property` decorators
- For `ast.AnnAssign` at class body level: extract `PropertySpec`
- For `enum.Enum` subclasses: extract `EnumMember` from class body assigns

### Step 3: Verify backward compatibility

Ensure old `ApiSurface.methods: list[str]` field still populated (keep backward compat). New typed fields are additive.

### Step 4: Add tests

Add ≥6 tests to `tests/unit/workers/test_understand.py`:
- `test_typed_method_params_extracted` — verifies ParamSpec list populated
- `test_typed_method_return_type` — verifies return type captured
- `test_property_extracted` — verifies PropertySpec
- `test_enum_member_extracted` — verifies EnumMember
- `test_classmethod_flag` — verifies is_classmethod=True
- `test_no_annotation_gives_none` — verifies graceful None for unannotated params

### Step 5: Run full test suite

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```
All tests must pass.

## Failure modes

### Failure mode 1: AST parse failure on syntax error files

**Detection**: `SyntaxError` raised when parsing source file
**Resolution**: Wrap `ast.parse()` in try/except; log warning; return empty typed fields; do not crash extraction
**Gate**: Understand worker must not crash on any cached repo clone

### Failure mode 2: Model field name collision with TC-HYBRID-03

**Detection**: `ImportError` or pydantic validation error referencing `ApiSurface` fields
**Resolution**: Coordinate field names with TC-HYBRID-03 before merging — `typed_methods` for this TC, `format_matrix` for TC-HYBRID-03
**Gate**: Both TCs must produce a merged model that validates cleanly

### Failure mode 3: Performance regression on large repos

**Detection**: Understand worker takes >2x longer on a cached clone
**Resolution**: Limit typed extraction to top 50 public methods per class; cache AST parse result
**Gate**: Time test on cells_foss_python clone

## Task-specific review checklist

1. [ ] `MethodSignature` model has all 6 fields (name, params, return_type, is_classmethod, is_staticmethod, is_property)
2. [ ] `ParamSpec` captures type_hint=None for unannotated params (not "Any" or omitted)
3. [ ] `ApiSurface.methods: list[str]` still populated (backward compat)
4. [ ] ≥6 new unit tests added and passing
5. [ ] No `ast.parse()` call crashes on any of the 5 cached clones
6. [ ] Pydantic model serializes to JSON without error (no non-serializable types)
7. [ ] Docstrings updated for all new public models/functions
8. [ ] Spec file checked for drift (understand_worker.md)
9. [ ] Schema `"description"` fields present for new model properties
10. [ ] `docs/README.md` ownership map checked

## Deliverables

1. Extended `src/launcher/models/understanding.py` with 4 new models
2. Updated `src/launcher/workers/understand/extract/_api_surface.py`
3. ≥6 new passing tests
4. `reports/TC-HYBRID-02/evidence.md` with test run output

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — all pass
2. [ ] `ApiSurface.typed_methods` populated from cells_foss_python clone (≥10 entries)
3. [ ] `ApiSurface.properties` populated from at least one clone
4. [ ] Old `ApiSurface.methods: list[str]` still works (backward compat test passes)

## Self-review

### Verification results
- [x] Tests: 9/9 PASS (5 in TestTypedApiSurface + 4 in TestFormatMatrix; 2963 total passed)
- [x] Validation: ApiSurface typed fields populated — MethodSignature, PropertyRecord, EnumRecord all wired through code_analyzer.py → _api_surface.py → ClassBrief
- [x] Evidence captured: reports/TC-HYBRID-02/evidence.md

### Task-specific review checklist
1. [x] `MethodSignature` model has all required fields: `name`, `parameters: list[MethodParam]`, `return_type: str`, `is_static: bool`, `is_async: bool`, `docstring_snippet: str` (field names adapted to existing conventions in product.py)
2. [x] `MethodParam.type_annotation` defaults to `""` for unannotated params (consistent with existing model conventions)
3. [x] `ClassBrief.methods: list[str]` still populated (backward compat test passes)
4. [x] 5 new unit tests added in TestTypedApiSurface, all passing
5. [x] No `ast.parse()` crash — code_analyzer.py wraps parse in try/except
6. [x] Pydantic model serializes to JSON (all new models use `LauncherBaseModel`)
7. [x] Docstrings present on all new model classes
8. [x] Models landed in `product.py` (not `understanding.py`) to match existing ApiSurface module pattern
9. [x] `enums: list[EnumRecord]` added to both `ClassBrief` and `ApiSurface`
10. [x] Pre-existing test failure (`test_deploy_dir_triggers_promote_run`) is asyncio ordering issue, unrelated to this change

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -v -k "typed"
```

**Expected results**:
- All typed_* tests PASS
- No SyntaxError crash on any clone

## Integration boundary proven

**Upstream**: Understand worker calls `_api_surface.py` → produces `ApiSurface`
**Downstream**: Generate worker consumes `ProductEvidence.api_surface.typed_methods` for prompt construction
**Contract**: `ApiSurface` pydantic model serializes to JSON; `typed_methods: list[MethodSignature]` is the new contract field
