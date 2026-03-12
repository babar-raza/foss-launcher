# HG-06 — .NET and Java Adapters: Typed Extraction (not Regex-Only)

**Status**: Not Started
**Gap linkage**: G6 (.NET/Java adapters use regex-only class extraction; no typed_methods)
**Role**: Senior engineer. Drop-in, production-ready.
**Priority**: High

## Context

The plan's Phase 5 acceptance criteria state:
> "C# `ClassBrief` from fixture has `typed_methods`"
> "Java `ClassBrief` from fixture has `typed_methods`"

The current `DotNetExtractor` and `JavaExtractor` implement `extract_class_details()`
by calling `analyze_file_safe(file_path, repo_dir=repo_dir)`. The `analyze_file_safe`
function dispatches to `ts_analyzer.analyze_file()` for non-Python files, which uses
tree-sitter grammars for Java and C#.

The critical question is whether `ts_analyzer.analyze_file()` for C# and Java actually
returns method parameter types and return types, or just method names.

If tree-sitter Java/C# grammars are available in the environment, the Phase 3
enhancements to `_extract_class()` in ts_analyzer may already handle them.
If not, the adapters need to implement their own typed extraction.

## Scope

### Fix

**Step 1: Audit what ts_analyzer returns for C# and Java**
1. Check which tree-sitter grammars are installed: `pip show tree-sitter-languages`
2. Run `analyze_file_safe` on a minimal .cs and .java fixture
3. Confirm whether output includes `method_details` with `parameters` and `return_type`

**Step 2a: If typed extraction works via ts_analyzer**
- Add 5 unit tests verifying C# and Java ClassBrief.typed_methods populated
- Update acceptance criteria status to Done

**Step 2b: If typed extraction is missing (regex only)**
- Implement tree-sitter C# method parameter extraction in DotNetExtractor
- Implement tree-sitter Java method parameter extraction in JavaExtractor
- These must populate the same dict format as ts_analyzer for Python compatibility

### Allowed paths

```
src/launcher/workers/understand/adapters/_dotnet.py
src/launcher/workers/understand/adapters/_java.py
tests/unit/workers/test_understand.py
plans/taskcards/TC-4012_dotnet_java_typed_extraction.md
```

### Forbidden

`shared/ts_analyzer.py` — no changes (authoritative for tree-sitter logic).
`shared/code_analyzer.py` — read-only.

## Acceptance checks

### CLI
```bash
# Diagnostic: what does analyze_file_safe return for a .cs file?
PYTHONHASHSEED=0 .venv/Scripts/python.exe -c "
from pathlib import Path
import tempfile
from launcher.shared.code_analyzer import analyze_file_safe

cs_code = '''
public class Scene {
    public string Name { get; set; }
    public Scene FromFile(string path) { return new Scene(); }
}
'''
with tempfile.TemporaryDirectory() as d:
    f = Path(d) / 'Scene.cs'
    f.write_text(cs_code)
    result = analyze_file_safe(f, repo_dir=Path(d))
    print(result)
"
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -k "DotNet or Java" -v
```

### Tests
- `test_dotnet_extract_class_details_fixture`: C# fixture → ClassBrief with method names
- `test_dotnet_classbrie_typed_methods_if_available`: if tree-sitter C# available → typed_methods
- `test_java_extract_class_details_fixture`: Java fixture → ClassBrief with method names
- `test_java_classbrie_typed_methods_if_available`: if tree-sitter Java available → typed_methods
- `test_dotnet_graceful_no_grammar`: when tree-sitter C# unavailable → ClassBrief with names only + no crash

### Config respected end-to-end
- If tree-sitter grammar absent: MissingInfoEntry recorded, fallback to names-only

### No mock data in production paths
- Tests use real `tmp_path` fixtures with actual C#/Java code snippets

## Deliverables

1. Audit findings documented in this taskcard (Step 1 result)
2. Updated `_dotnet.py` and `_java.py` if Step 2b is needed
3. 5+ tests per adapter
4. `plans/taskcards/TC-4012_dotnet_java_typed_extraction.md`

## Hard rules

- Use tree-sitter only if grammar is available; otherwise fail gracefully
- Do not add tree-sitter grammar packages to pyproject.toml without explicit approval
- MissingInfoEntry must be emitted when typed extraction unavailable
- No changes to Python or TypeScript extraction paths

## Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Correctness | C# and Java ClassBrief.typed_methods populated when grammar available |
| Robustness | Missing grammar → names-only + MissingInfoEntry; no crash |
| Testability | Real fixture content; parametrized across both platforms |
| Consistency | Same dict format as Python/TypeScript output |
| Minimality | Only _dotnet.py and _java.py changed if gap exists |

## Now (runbook)

```
1. Run diagnostic (see CLI section) for .cs
2. Run diagnostic for .java
3. Inspect output: does "method_details" contain "parameters" key?
4a. If yes (typed extraction works): write 5+ tests and close
4b. If no: implement tree-sitter C# parameter extraction in _dotnet.py
    - Query: (method_declaration return_type: _ name: _ parameters: _)
    - Parse parameter_list → list[MethodParam]
    - Return same dict format as ts_analyzer
5. Repeat for Java in _java.py
6. Write tests with tmp_path fixtures
7. Run full suite
```
