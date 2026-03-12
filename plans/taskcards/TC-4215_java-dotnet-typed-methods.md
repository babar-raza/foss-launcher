---
id: TC-4215
title: "Java + C# adapters — typed method extraction via ts_analyzer"
status: Done
priority: Normal
owner: "orchestrator-agent"
updated: "2026-03-11"
tags: ["understand", "java", "dotnet", "adapters", "typed-methods"]
depends_on: ["TC-HYBRID-02", "TC-4214"]
allowed_paths:
  - plans/taskcards/TC-4215_java-dotnet-typed-methods.md
  - src/launcher/workers/understand/adapters/_java.py
  - src/launcher/workers/understand/adapters/_dotnet.py
  - tests/unit/workers/understand/test_java_adapter.py
  - tests/unit/workers/understand/test_dotnet_adapter.py
  - reports/agents/wave2/TC-4215/evidence.md
evidence_required:
  - reports/agents/wave2/TC-4215/evidence.md
---

# Taskcard TC-4215 — Java + C# adapters: typed method extraction

## Objective

Enhance `_java.py` and `_dotnet.py` adapters' `extract_class_details()` to explicitly
call `ts_analyzer.analyzer.analyze_file()` with the correct language tag (`"java"` and
`"csharp"` respectively), ensuring typed method signatures, typed properties, and enum
records are populated deterministically without relying on file-extension dispatch.

## Required spec references

- `specs/worker_understand.md` (Section: API surface extraction)
- `specs/system_contract.md` (Section: Extract worker outputs)

## Scope

### In scope
- Modify `_java.py` `extract_class_details()` to call `ts_analyzer.analyzer.analyze_file()` with `language="java"`
- Modify `_dotnet.py` `extract_class_details()` to call `ts_analyzer.analyzer.analyze_file()` with `language="csharp"` (which resolves via `_LANG_PACK_ALIASES` to the c_sharp_separate grammar)
- Write unit tests for both adapters with fixture `.java` and `.cs` files
- Fallback to existing `code_analyzer.analyze_file_safe()` when ts_analyzer returns empty

### Out of scope
- Changes to `_api_surface.py` (uses `code_analyzer.analyze_file_safe()` directly, not adapters)
- Changes to TypeScript adapter (TC-4214)
- C++ or other language adapters

## Inputs

- `src/launcher/workers/understand/adapters/_java.py` — Java adapter
- `src/launcher/workers/understand/adapters/_dotnet.py` — .NET/C# adapter
- `src/launcher/shared/ts_analyzer.py` — `analyzer.analyze_file(path, language)` method
- `_LANG_PACK_ALIASES` in ts_analyzer: `"csharp"` → `"_c_sharp_separate"` (uses tree_sitter_c_sharp)

## Outputs

- Enhanced `_java.py` with explicit `language="java"` dispatch
- Enhanced `_dotnet.py` with explicit `language="csharp"` dispatch
- `tests/unit/workers/understand/test_java_adapter.py` — new test
- `tests/unit/workers/understand/test_dotnet_adapter.py` — new test
- `reports/agents/wave2/TC-4215/evidence.md` — test output

## Allowed paths

- plans/taskcards/TC-4215_java-dotnet-typed-methods.md
- src/launcher/workers/understand/adapters/_java.py
- src/launcher/workers/understand/adapters/_dotnet.py
- tests/unit/workers/understand/test_java_adapter.py
- tests/unit/workers/understand/test_dotnet_adapter.py
- reports/agents/wave2/TC-4215/evidence.md

### Allowed paths rationale

- Both adapter files need typed method dispatch hardening
- Two new test files for Java and C# adapters
- Evidence file required by governance rule

## Implementation steps

### Step 1: Understand language alias for C#

In `ts_analyzer._LANG_PACK_ALIASES`: `"csharp"` → `"_c_sharp_separate"` sentinel.
The `_get_parser("csharp")` call loads `tree_sitter_c_sharp` package.
So the adapter must pass `language="csharp"` (not `"cs"` or `"c_sharp"`) — both aliases
map to the same sentinel but `"csharp"` is the canonical key used in `_LANG_DOC_STYLE`.

### Step 2: Enhance `_java.py`

Replace `code_analyzer.analyze_file_safe()` with:
```python
from launcher.shared.ts_analyzer import analyzer as _ts_analyzer
result = _ts_analyzer.analyze_file(file_path, language="java", repo_dir=repo_dir)
if result.classes:
    return result.classes
```
Fallback to `code_analyzer.analyze_file_safe()` when `result.classes` is empty.

### Step 3: Enhance `_dotnet.py`

Same pattern with `language="csharp"`:
```python
result = _ts_analyzer.analyze_file(file_path, language="csharp", repo_dir=repo_dir)
```

### Step 4: Create Java fixture and test

Write `tests/unit/workers/understand/test_java_adapter.py`:
- Fixture `.java` file with `public class MyDocument` containing typed public methods
- Run `JavaExtractor().extract_class_details(path, repo_dir, product)`
- Assert first class has `method_details` with at least one entry
- Assert method has `name`, `parameters`, `return_type` keys

### Step 5: Create C# fixture and test

Write `tests/unit/workers/understand/test_dotnet_adapter.py`:
- Fixture `.cs` file with `public class WorkbookImpl` containing typed methods
- Assert `method_details` non-empty

### Step 6: Run full test suite

`PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -x -q`

## Failure modes

### Failure mode 1: C# grammar not installed

**Detection**: `_get_parser("csharp")` returns None (tree_sitter_c_sharp not in venv)
**Resolution**: Fallback to `code_analyzer.analyze_file_safe()` — test skips/passes gracefully
**Gate**: Test uses `pytest.mark.skipif` or checks result non-empty

### Failure mode 2: Java class body not captured

**Detection**: `result.classes` empty despite valid Java class in fixture
**Resolution**: Check `_CLASS_TYPES["java"]` includes `"class_declaration"`; verify fixture uses public keyword
**Gate**: `assert len(class_list) >= 1`

### Failure mode 3: C# method_details empty due to tree-sitter node type mismatch

**Detection**: `method_details` empty for C# class with methods
**Resolution**: ts_analyzer `_FUNC_TYPES["_c_sharp_separate"]` includes `"method_declaration"` — verify fixture has valid C# method syntax
**Gate**: `assert len(class_list[0]["method_details"]) > 0`

## Task-specific review checklist

1. [ ] `_java.py` passes `language="java"` explicitly to ts_analyzer
2. [ ] `_dotnet.py` passes `language="csharp"` explicitly to ts_analyzer
3. [ ] Both adapters fall back to `code_analyzer.analyze_file_safe()` when ts_analyzer empty
4. [ ] Java test fixture has a public class with typed methods
5. [ ] C# test fixture has a public class with typed methods
6. [ ] Both tests assert `method_details` non-empty
7. [ ] Docstrings updated for changed methods
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map — no guide update needed
11. [ ] No new `docs/guides/` file added

## Deliverables

1. `src/launcher/workers/understand/adapters/_java.py` — enhanced with explicit java dispatch
2. `src/launcher/workers/understand/adapters/_dotnet.py` — enhanced with explicit csharp dispatch
3. `tests/unit/workers/understand/test_java_adapter.py` — new test
4. `tests/unit/workers/understand/test_dotnet_adapter.py` — new test
5. `reports/agents/wave2/TC-4215/evidence.md` — test output

## Acceptance checks

1. [ ] `tests/unit/workers/understand/test_java_adapter.py` — all tests PASS
2. [ ] `tests/unit/workers/understand/test_dotnet_adapter.py` — all tests PASS
3. [ ] Java adapter returns `method_details` in class dicts
4. [ ] C# adapter returns `method_details` in class dicts

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: adapters return typed data
- [ ] Evidence captured: reports/agents/wave2/TC-4215/evidence.md
- [ ] Doc freshness: clean

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_java_adapter.py tests/unit/workers/understand/test_dotnet_adapter.py -v
```

**Expected results**:
- All tests PASS
- typed_methods populated for Java and C# class fixtures

## Integration boundary proven

**Upstream**: `ts_analyzer.analyzer.analyze_file()` provides typed AST data for Java and C#
**Downstream**: `_api_surface.py` builds `ClassBrief` from class dicts with `method_details`
**Contract**: Class dict shape `{name, methods, method_details, property_details, is_enum, enum_members}`
