---
id: TC-HYBRID-02
title: "Typed API Surface — MethodSignature, PropertyRecord, EnumRecord in ClassBrief"
status: Done
priority: High
owner: "Agent-B"
updated: "2026-03-10"
tags: [evidence-model, api-surface, extraction]
depends_on: [TC-HYBRID-01]
allowed_paths:
  - plans/taskcards/TC-HYBRID-02_typed-api-surface.md
  - src/launcher/models/product.py
  - src/launcher/workers/understand/extract/_api_surface.py
  - src/launcher/shared/code_analyzer.py
  - tests/unit/workers/test_understand.py
  - tests/unit/models/test_product_models.py
  - reports/TC-HYBRID-02/evidence.md
  - reports/agents/B/TC-HYBRID-02/self_review.md
  - reports/agents/B/TC-HYBRID-02/plan.md
evidence_required:
  - reports/TC-HYBRID-02/evidence.md
---

# Taskcard TC-HYBRID-02 — Typed API Surface (MethodSignature, PropertyRecord, EnumRecord)

## Objective

Extend `ClassBrief` in `src/launcher/models/product.py` with optional typed members
(`MethodSignature`, `PropertyRecord`, `EnumRecord`) so the LLM receives accurate
parameter types, return types, property types, and enum members rather than guessing
them. This eliminates the class of hallucination where the LLM invents method
signatures, wrong property types, and wrong enum casing.

## Required spec references

- `specs/product_model.md` (Section: ProductIdentity, ApiSurface, ClassBrief)
- `specs/worker_understand.md` (Section: Phase B — deterministic extraction)
- `specs/worker_generate.md` (Section: code generation context)

## Scope

### In scope
- Add `MethodParam`, `MethodSignature`, `PropertyRecord`, `EnumMember`, `EnumRecord` models to `src/launcher/models/product.py`
- Extend `ClassBrief` with optional fields: `typed_methods: list[MethodSignature]`, `typed_properties: list[PropertyRecord]`, `enums: list[EnumRecord]`
- Update `_extract_api_surface()` in `_api_surface.py` to populate typed members from `analyze_file_safe()` results (which already return rich dicts)
- Update `shared/code_analyzer.py` to extract parameter types and return types from Python AST
- Unit tests covering: typed methods populated, property types populated, enum members with exact casing

### Out of scope
- TypeScript/Java/.NET typed extraction (Python-first; other langs default to name-only)
- Format matrix extraction (TC-HYBRID-03)
- Injecting typed context into generation prompts (TC-HYBRID-07)
- API verification gate (TC-HYBRID-05)

## Inputs

- `src/launcher/models/product.py` — current `ClassBrief` model (methods/properties as `list[str]`)
- `src/launcher/workers/understand/extract/_api_surface.py` — `_extract_api_surface()` populating `ClassBrief`
- `src/launcher/shared/code_analyzer.py` — `analyze_file_safe()` dispatching to language parsers
- Python AST from product repos (available at runtime via `repo_dir`)

## Outputs

- Extended `ClassBrief` with `typed_methods`, `typed_properties`, `enums` fields (all optional, default empty list)
- `MethodSignature`, `PropertyRecord`, `EnumRecord` models usable downstream by TC-HYBRID-05 (API verification gate) and TC-HYBRID-07 (holistic context injection)
- `src/launcher/shared/code_analyzer.py` extended to return param types and return types in method dicts
- Test evidence: typed members populated for a mock Python class fixture

## Allowed paths

- plans/taskcards/TC-HYBRID-02_typed-api-surface.md
- src/launcher/models/product.py
- src/launcher/workers/understand/extract/_api_surface.py
- src/launcher/shared/code_analyzer.py
- tests/unit/workers/test_understand.py
- tests/unit/models/test_product_models.py
- reports/TC-HYBRID-02/evidence.md
- reports/agents/B/TC-HYBRID-02/self_review.md
- reports/agents/B/TC-HYBRID-02/plan.md

### Allowed paths rationale
- `product.py`: new models live here alongside `ClassBrief`/`ApiSurface`
- `_api_surface.py`: where `ClassBrief` is populated from analyzer results
- `code_analyzer.py`: must return param types/return types from AST
- `test_understand.py`, `test_product_models.py`: unit tests for new models and extraction
- `reports/`: evidence and self-review

## Implementation steps

### Step 1: Add typed member models to product.py

Add the following new models **before** `ClassBrief` in `src/launcher/models/product.py`:

```python
class MethodParam(LauncherBaseModel):
    """A single method parameter with optional type annotation."""
    name: str
    type_annotation: str = ""   # e.g. "str", "int", "Vector3", ""

class MethodSignature(LauncherBaseModel):
    """Typed method signature extracted from source AST."""
    name: str
    parameters: list[MethodParam] = Field(default_factory=list)
    return_type: str = ""       # e.g. "bool", "None", "Scene", ""
    is_static: bool = False
    is_async: bool = False
    docstring_snippet: str = ""

class PropertyRecord(LauncherBaseModel):
    """Typed property extracted from source AST."""
    name: str
    type_annotation: str = ""  # e.g. "Vector3[]", "str", "bool"
    is_readonly: bool = False
    docstring_snippet: str = ""

class EnumMember(LauncherBaseModel):
    """A single enum member with exact source casing."""
    name: str                  # exact casing from source
    value: str = ""            # string repr of value
    docstring_snippet: str = ""

class EnumRecord(LauncherBaseModel):
    """An enum class with all members, extracted from source."""
    name: str
    members: list[EnumMember] = Field(default_factory=list)
    docstring_snippet: str = ""
```

Then extend `ClassBrief`:
```python
class ClassBrief(LauncherBaseModel):
    """Compact summary of a public class for prompt injection."""
    name: str
    docstring_snippet: str = ""
    methods: list[str] = Field(default_factory=list)
    properties: list[str] = Field(default_factory=list)
    # New typed members — populated when AST extraction succeeds
    typed_methods: list[MethodSignature] = Field(default_factory=list)
    typed_properties: list[PropertyRecord] = Field(default_factory=list)
    enums: list[EnumRecord] = Field(default_factory=list)
```

Also add `enums: list[EnumRecord]` to `ApiSurface`:
```python
class ApiSurface(LauncherBaseModel):
    """Extracted API surface of a product repository."""
    public_classes: list[str]
    import_allowlist: list[str]
    confidence: Literal["high", "medium", "low"]
    api_identifiers: list[str] = Field(default_factory=list)
    class_briefs: list[ClassBrief] = Field(default_factory=list)
    enums: list[EnumRecord] = Field(default_factory=list)  # top-level enums
```

### Step 2: Extend code_analyzer.py to extract typed method info

In `src/launcher/shared/code_analyzer.py`, find the Python AST method extraction
and extend it to return param types and return types:

Current pattern (in the Python AST branch):
```python
{"name": method_name, "docstring": "..."}
```

Target output:
```python
{
    "name": method_name,
    "parameters": [{"name": "p", "type_annotation": "str"}, ...],
    "return_type": "bool",
    "is_static": False,
    "is_async": False,
    "docstring": "...",
}
```

For Python AST extraction:
- `ast.FunctionDef.args.args` → parameter names
- `ast.arg.annotation` → type annotation (use `ast.unparse(ann)` if Python 3.9+, else `ast.dump`)
- `ast.FunctionDef.returns` → return type annotation
- `@staticmethod` decorator → `is_static = True`
- `isinstance(node, ast.AsyncFunctionDef)` → `is_async = True`

For properties (Python AST):
- `@property` decorator on a method → `is_readonly = True`
- Return annotation on the property getter = property type

For enums (Python AST):
- Detect `class Foo(Enum):` or `class Foo(IntEnum):` etc.
- Walk `ast.ClassBody` for `ast.Assign` nodes → member names and values

Cap: extract at most 20 methods, 20 properties, 10 enum members per class.
On extraction failure: silently skip, leave lists empty. Never raise.

### Step 3: Update _api_surface.py to populate typed members

In `_extract_api_surface()` where `ClassBrief` is constructed (lines 237-242):

Current:
```python
class_briefs.append(ClassBrief(
    name=cls_name,
    docstring_snippet=docstring_snippet,
    methods=methods[:10],
    properties=properties[:10],
))
```

Extend to also populate `typed_methods`, `typed_properties`, `enums` from the
richer dict returned by the updated `analyze_file_safe()`:

```python
typed_methods = []
for m in cls_entry.get("methods", []):
    if isinstance(m, dict) and "parameters" in m:
        params = [MethodParam(name=p["name"], type_annotation=p.get("type_annotation",""))
                  for p in m.get("parameters", [])]
        typed_methods.append(MethodSignature(
            name=m["name"],
            parameters=params,
            return_type=m.get("return_type", ""),
            is_static=m.get("is_static", False),
            is_async=m.get("is_async", False),
            docstring_snippet=_first_sentence(m.get("docstring", "")),
        ))

typed_properties = []
for p in cls_entry.get("properties", []):
    if isinstance(p, dict):
        typed_properties.append(PropertyRecord(
            name=p["name"],
            type_annotation=p.get("type_annotation", ""),
            is_readonly=p.get("is_readonly", False),
            docstring_snippet=_first_sentence(p.get("docstring", "")),
        ))

class_briefs.append(ClassBrief(
    name=cls_name,
    docstring_snippet=docstring_snippet,
    methods=methods[:10],
    properties=properties[:10],
    typed_methods=typed_methods[:20],
    typed_properties=typed_properties[:20],
))
```

Also extract top-level enums from the same `analyze_file_safe()` results (check for
`"enums"` key in the file result dict).

### Step 4: Add the import statements

In `_api_surface.py`, add to the import from `launcher.models.product`:
```python
from launcher.models.product import (
    ApiSurface, ClassBrief, EnumMember, EnumRecord,
    MethodParam, MethodSignature, ProductIdentity, PropertyRecord,
)
```

### Step 5: Write unit tests

In `tests/unit/models/test_product_models.py` (create if doesn't exist):
- `test_class_brief_typed_methods_default_empty`: `ClassBrief(name="Foo")` → `typed_methods == []`
- `test_method_signature_model`: round-trip Pydantic model with params and return_type
- `test_enum_record_model`: round-trip with EnumMember list

In `tests/unit/workers/test_understand.py`:
- `test_api_surface_typed_methods_populated`: mock `analyze_file_safe()` to return rich dict with `parameters` and `return_type`; call `_extract_api_surface()`; assert `class_briefs[0].typed_methods[0].return_type` is populated
- `test_api_surface_typed_properties_populated`: same for properties with `type_annotation`
- `test_api_surface_backward_compat_name_list`: when analyzer returns plain string methods (old format), `methods` list still populated; `typed_methods` empty — no regression

### Step 6: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/models/ tests/unit/workers/test_understand.py -v --tb=short
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

All existing tests must continue to pass. New tests must pass.

### Step 7: Write evidence and self-review

Create `reports/TC-HYBRID-02/evidence.md` and `reports/agents/B/TC-HYBRID-02/self_review.md`.

## Failure modes

### Failure mode 1: analyze_file_safe() returns plain strings, not dicts

**Detection**: `isinstance(m, str)` for methods in `_extract_api_surface()`; typed_methods remains empty.
**Resolution**: Keep backward compat path — plain strings populate `methods: list[str]` as before. Rich dicts populate `typed_methods`. Both can coexist.
**Gate**: Backward compat test `test_api_surface_backward_compat_name_list`

### Failure mode 2: ast.unparse() not available (Python < 3.9)

**Detection**: `AttributeError: module 'ast' has no attribute 'unparse'`
**Resolution**: Use `ast.dump(ann)` as fallback, or simple name extraction for `ast.Name` nodes (`node.id`), `ast.Attribute` nodes (`f"{node.value.id}.{node.attr}"`). No external dependency.
**Gate**: Unit test must pass on Python 3.8+

### Failure mode 3: Enum detection misclassifies regular classes

**Detection**: Class named `FooEnum` that inherits from `object` flagged as enum.
**Resolution**: Only detect enum classes that have `Enum`, `IntEnum`, `StrEnum`, `Flag`, or `IntFlag` in their base class names. Check `ast.ClassDef.bases` for `ast.Name.id` or `ast.Attribute.attr` in the enum base set.
**Gate**: Unit test with fixture showing only true enums extracted

### Failure mode 4: Test file import fails (new model not exported from __init__.py)

**Detection**: `ImportError: cannot import name 'MethodSignature' from 'launcher.models.product'`
**Resolution**: All new models are in `product.py` which is already imported directly. Check `src/launcher/models/__init__.py` to see if models need re-export.
**Gate**: `python -c "from launcher.models.product import MethodSignature"` succeeds

## Task-specific review checklist

1. [ ] `MethodSignature`, `PropertyRecord`, `EnumRecord`, `MethodParam`, `EnumMember` models defined in `product.py`
2. [ ] `ClassBrief` extended with `typed_methods`, `typed_properties`, `enums` — all default to empty list
3. [ ] `ApiSurface.enums` field added for top-level enums
4. [ ] `code_analyzer.py` returns `parameters`, `return_type`, `is_static`, `is_async` in method dicts
5. [ ] `_api_surface.py` populates typed members when rich dicts available; falls back gracefully for string-only
6. [ ] All new typed fields are `Optional`/defaulted — no breaking change for existing call sites
7. [ ] Docstrings updated for all new models and updated functions
8. [ ] Spec file `specs/product_model.md` updated with new models
9. [ ] Schema `"description"` fields present for all new model properties
10. [ ] Checked `docs/README.md` ownership map — no trigger event applies
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables

1. `src/launcher/models/product.py` — 5 new models, `ClassBrief` and `ApiSurface` extended
2. `src/launcher/workers/understand/extract/_api_surface.py` — typed member population
3. `src/launcher/shared/code_analyzer.py` — param types and return types in method dicts
4. `tests/unit/models/test_product_models.py` — new model round-trip tests
5. `tests/unit/workers/test_understand.py` — extraction tests with rich dict fixture
6. `reports/TC-HYBRID-02/evidence.md` — test output and model field verification
7. `reports/agents/B/TC-HYBRID-02/self_review.md` — 12-dimension self-review

## Acceptance checks

1. [ ] `MethodSignature`, `PropertyRecord`, `EnumRecord` importable from `launcher.models.product`
2. [ ] `ClassBrief.typed_methods` populated when `analyze_file_safe()` returns rich method dicts
3. [ ] `ClassBrief.methods` still populated for backward compat when string-only dicts returned
4. [ ] All 3+ new tests pass: typed method, typed property, backward compat
5. [ ] Full test suite passes: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no`
6. [ ] No existing `ClassBrief` or `ApiSurface` consumer breaks (grep for usages, all are optional field accesses)

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: all ClassBrief consumers PASS (backward compat)
- [ ] Evidence captured: reports/TC-HYBRID-02/evidence.md
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --since HEAD~N` clean / acknowledged

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/models/ tests/unit/workers/test_understand.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

**Expected results**:
- All new model tests pass
- Full suite passes (same count as TC-HYBRID-01 baseline: 3325 + new tests)

## Integration boundary proven

**Upstream**: `shared/code_analyzer.py` → `analyze_file_safe()` returns richer method dicts
**Downstream**: `_api_surface.py` populates `ClassBrief.typed_methods`; TC-HYBRID-05 (API verification gate) reads `ClassBrief.typed_methods`; TC-HYBRID-07 (holistic context) injects typed members into prompts
**Contract**: `ClassBrief.typed_methods: list[MethodSignature]` — default empty; never None; safe for all consumers using `brief.typed_methods or []`
