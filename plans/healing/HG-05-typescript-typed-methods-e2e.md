# HG-05 — TypeScript ClassBrief `typed_methods` Population (End-to-End Verification)

**Status**: In Progress
**Gap linkage**: G5 (TypeScript typed_methods not verified end-to-end)
**Role**: Senior engineer. Drop-in, production-ready.
**Priority**: High

## Context

Phase 3 enhanced `ts_analyzer.py::_extract_class()` to return richer dicts with
`parameters`, `return_type`, `property_details`, `is_enum`, `enum_members`.

However, the bridge from these richer dicts to `ClassBrief.typed_methods`,
`ClassBrief.typed_properties`, `ClassBrief.enums` population was never confirmed
end-to-end. The critical question is:

**Does `_extract_api_surface.py`'s ClassBrief builder read `typed_methods` from
the enhanced ts_analyzer dict?**

The suspected gap: `_api_surface.py` calls `extractor.extract_class_details()` which
returns `list[dict]`. It then builds `ClassBrief` from each dict. If the ClassBrief
builder only reads `{"name", "docstring", "methods": [str]}` and ignores
`{"method_details": [{"parameters": [...], "return_type": ...}]}`, then the Phase 3
work is effectively dead code for TypeScript.

## Scope

### Fix

**Step 1: Audit**
1. Read `src/launcher/workers/understand/extract/_api_surface.py` to find where
   ClassBrief is built from adapter dict output
2. Identify which dict keys are used to populate `typed_methods`, `typed_properties`, `enums`
3. Determine if the TypeScript path actually populates these fields

**Step 2: Fix if needed**
If the ClassBrief builder does NOT read typed_methods from the enhanced dict:
1. Update `_api_surface.py`'s ClassBrief builder to:
   - Read `method_details[i]["parameters"]` → `MethodParam` → `MethodSignature`
   - Read `method_details[i]["return_type"]` → `MethodSignature.return_type`
   - Read `property_details` → `PropertyRecord` list
   - Read `enum_members` when `is_enum=True` → `EnumRecord`

**Step 3: End-to-end test**
3. Add an integration test that runs `TypeScriptExtractor.extract_class_details()`
   on a real `.ts` fixture file and asserts `ClassBrief.typed_methods` is populated

### Allowed paths

```
src/launcher/workers/understand/extract/_api_surface.py  (fix ClassBrief builder)
src/launcher/workers/understand/adapters/_typescript.py  (if TypeScriptExtractor needs fix)
tests/unit/workers/test_understand.py                    (new e2e test)
tests/integration/test_understand_pipeline.py            (new integration assertion)
plans/taskcards/TC-4011_typescript_typed_methods_e2e.md
```

### Forbidden

`shared/ts_analyzer.py` — do NOT change (already enhanced in Phase 3).

## Acceptance checks

### CLI
```bash
# Verify TypeScript ClassBrief has typed_methods (not just names):
PYTHONHASHSEED=0 .venv/Scripts/python.exe -c "
from pathlib import Path
import tempfile, os
from launcher.workers.understand.adapters._typescript import TypeScriptExtractor
from launcher.models.product import ProductIdentity

# Create minimal TS fixture
ts_code = '''
export class Scene {
  private _name: string;
  constructor(name: string) { this._name = name; }
  getName(): string { return this._name; }
  get rootNode(): Node { return new Node(); }
}
'''
with tempfile.TemporaryDirectory() as tmpdir:
    p = Path(tmpdir) / 'scene.ts'
    p.write_text(ts_code)
    product = ProductIdentity(family='test', platform='typescript',
                              display_name='T', canonical_import='t',
                              runtime_import='t', repo_url='http://x')
    ext = TypeScriptExtractor()
    result = ext.extract_class_details(p, Path(tmpdir), product)
    print('classes:', len(result))
    if result:
        print('typed_methods:', result[0].get('method_details', []))
        print('typed_properties:', result[0].get('property_details', []))
"
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -k "TypeScript" -v
```

### Tests
- `test_typescript_classbrie_has_typed_methods`: TypeScriptExtractor on fixture → ClassBrief.typed_methods populated
- `test_typescript_classbrie_has_typed_properties`: TypeScriptExtractor on fixture → ClassBrief.typed_properties populated
- `test_typescript_classbrie_has_enum_records`: TS enum → ClassBrief.enums populated
- `test_typescript_classbrie_method_has_return_type`: method detail includes return_type str
- Failure path: fixture with no type annotations → typed_methods empty (no crash)

### Config respected end-to-end
- TypeScriptExtractor uses existing tree-sitter grammar (no new deps)

### No mock data in production paths
- Tests use real tree-sitter parsing on actual `.ts` fixture content

## Deliverables

1. Audit report (inline comment in taskcard — was the gap present or not?)
2. If gap found: updated `_api_surface.py` ClassBrief builder
3. If gap found: updated `_typescript.py` if needed
4. 5+ new tests asserting typed fields populated for TypeScript
5. `plans/taskcards/TC-4011_typescript_typed_methods_e2e.md`

## Hard rules

- If the bridge already works (typed_methods IS populated), just add the 5 tests to
  confirm and close the gap — no code changes needed
- If the bridge is broken, fix only `_api_surface.py` dict→ClassBrief mapping
- Do NOT rewrite ts_analyzer.py (Phase 3 work is complete)
- No changes to Python extraction path — Python must remain bit-identical

## Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Correctness | TS ClassBrief.typed_methods has MethodSignature entries with params |
| Testability | Real tree-sitter parse on fixture; not mocked |
| Thoroughness | typed_methods + typed_properties + enums all verified |
| Minimality | If gap exists: only _api_surface.py changed |
| Robustness | No-type-annotation TS code → typed fields empty, no crash |

## Now (runbook)

```
1. Read src/launcher/workers/understand/extract/_api_surface.py
   - Find where ClassBrief is built from the adapter's extract_class_details() output
   - Search for "typed_methods", "MethodSignature", "method_details" in the builder code
2. If typed_methods NOT populated from dict:
   a. Add builder logic: read method_details → MethodSignature
   b. Add builder logic: read property_details → PropertyRecord
   c. Add builder logic: read enum_members when is_enum → EnumRecord
3. Write diagnostic script (see CLI command above) to confirm
4. Write 5 unit tests in test_understand.py
5. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -k "TypeScript" -v
6. Run full suite
```
