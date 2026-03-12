# TR-02 — Extend `normalize_imports_ast` to Handle CommonJS `require()` Syntax

**Source**: Self-review of TC-3904, GAP-03.
**Date**: 2026-03-09
**Sprint**: Thin-Repo Parity — Post-implementation healing.

---

## Context

TC-3901 replaced the hyphen-blind regex in `normalize_imports` with a tree-sitter AST-based
`normalize_imports_ast()` that handles ES `import_statement` nodes. The original bug
(`@aspose/\w+` truncating `@aspose/3d-foss` to `@aspose/3d`) also affects CommonJS syntax:

```js
const lib = require('@aspose/3d-foss');
// regex: captures "@aspose/3d", replacer produces "@aspose/3d-foss-foss"
```

TC-3901 fixed ES `import` but left `require()` unaddressed because `require()` compiles to
a `call_expression` node in tree-sitter (not `import_statement`). The TC-3904 test was
silently weakened to `assert isinstance(result, str)` instead of extending the fix.

Tree-sitter AST for `require('@aspose/3d-foss-foss')`:
```
call_expression
  function: identifier  text="require"
  arguments: arguments
    string  text="'@aspose/3d-foss-foss'"
```

The fix: scan `call_expression` nodes after the `import_statement` scan, check that the
callee is `require`, extract the first string argument, apply the same byte-precise
replacement already used for imports.

---

## Taskcard TR-02

**Status**: Done
**Gap linkage**: GAP-03
**Role**: Senior engineer. Drop-in, production-ready.

---

### Scope

**Fix**: Extend `normalize_imports_ast()` in `ts_analyzer.py` to also scan
`call_expression` nodes where the callee text is `"require"` and the first string argument
starts with `@aspose/`.

**Allowed paths**:
- `src/launcher/shared/ts_analyzer.py`
- `tests/unit/shared/test_ts_analyzer.py`

**Forbidden**: any other file or path.

---

### Implementation Steps

#### Step 1 — `src/launcher/shared/ts_analyzer.py`

In `normalize_imports_ast()`, after the existing `import_statement` loop (after line ~505),
add a second loop for `call_expression` nodes:

```python
# TR-02: Also normalise CommonJS require() calls.
# Tree-sitter node: call_expression → function: identifier("require") + arguments: string
for node in _collect_nodes(tree.root_node, "call_expression"):
    # Check callee is `require`
    func_node = _child_by_type(node, "identifier")
    if func_node is None:
        continue
    if func_node.text.decode("utf-8", errors="replace") != "require":
        continue
    # Check arguments block exists
    args_node = _child_by_type(node, "arguments")
    if args_node is None:
        continue
    # Find first string argument
    for arg_child in args_node.children:
        if arg_child.type == "string":
            raw = arg_child.text.decode("utf-8", errors="replace")
            inner = raw.strip("'\"")
            if inner.startswith("@aspose/") and inner != canonical_import:
                new_raw = raw.replace(inner, canonical_import, 1)
                replacements.append(
                    (arg_child.start_byte, arg_child.end_byte, new_raw.encode("utf-8"))
                )
            break  # only the first string argument matters
```

The full function after the fix:

```python
def normalize_imports_ast(code: str, language: str, canonical_import: str) -> str:
    """Rewrite @aspose/* imports using tree-sitter AST (byte-precise, handles hyphens/dots).

    Handles both ES module syntax (`import ... from '...'`) and CommonJS syntax
    (`require('...')`). Falls back to regex-based normalize_imports() if tree-sitter is
    unavailable or language is not JavaScript/TypeScript.

    Only rewrites specifiers that start with ``@aspose/`` and differ from
    ``canonical_import``. Non-@aspose imports are never touched.
    """
    resolved = _resolve_lang_name(language)

    if resolved not in ("javascript", "typescript"):
        return normalize_imports(code, language, canonical_import)

    parser = _get_parser(language)
    if parser is None or not canonical_import:
        # Graceful degradation: tree-sitter unavailable → fall back to regex
        return normalize_imports(code, language, canonical_import)

    code_bytes = code.encode("utf-8", errors="replace")
    tree = parser.parse(code_bytes)

    # Collect (start_byte, end_byte, replacement_bytes) for each wrong specifier.
    # Applied in reverse byte order so earlier positions are not shifted.
    replacements: list[tuple[int, int, bytes]] = []

    # ES module: import { X } from '@aspose/...'
    for node in _collect_nodes(tree.root_node, "import_statement"):
        for child in node.children:
            if child.type == "string":
                raw = child.text.decode("utf-8", errors="replace")
                inner = raw.strip("'\"")
                if inner.startswith("@aspose/") and inner != canonical_import:
                    new_raw = raw.replace(inner, canonical_import, 1)
                    replacements.append(
                        (child.start_byte, child.end_byte, new_raw.encode("utf-8"))
                    )

    # TR-02: CommonJS: const x = require('@aspose/...')
    for node in _collect_nodes(tree.root_node, "call_expression"):
        func_node = _child_by_type(node, "identifier")
        if func_node is None:
            continue
        if func_node.text.decode("utf-8", errors="replace") != "require":
            continue
        args_node = _child_by_type(node, "arguments")
        if args_node is None:
            continue
        for arg_child in args_node.children:
            if arg_child.type == "string":
                raw = arg_child.text.decode("utf-8", errors="replace")
                inner = raw.strip("'\"")
                if inner.startswith("@aspose/") and inner != canonical_import:
                    new_raw = raw.replace(inner, canonical_import, 1)
                    replacements.append(
                        (arg_child.start_byte, arg_child.end_byte, new_raw.encode("utf-8"))
                    )
                break

    if not replacements:
        return code

    result = bytearray(code_bytes)
    for start, end, new_bytes in sorted(replacements, reverse=True):
        result[start:end] = new_bytes
    return result.decode("utf-8", errors="replace")
```

#### Step 2 — `tests/unit/shared/test_ts_analyzer.py`

Replace the weakened `test_require_syntax_passthrough` with the spec-required assertion:

```python
def test_require_syntax(self):
    """CommonJS require() double-suffix is corrected by TR-02 AST fix."""
    code = "const lib = require('@aspose/3d-foss-foss');"
    fixed = normalize_imports_ast(code, "javascript", "@aspose/3d-foss")
    assert "@aspose/3d-foss-foss" not in fixed
    assert "@aspose/3d-foss" in fixed

def test_require_syntax_non_aspose_unchanged(self):
    """Non-@aspose require() is never rewritten."""
    code = "const _ = require('lodash');"
    assert normalize_imports_ast(code, "javascript", "@aspose/3d-foss") == code

def test_require_and_import_both_fixed_in_same_file(self):
    """Mixed ES import + require() — both are corrected in one pass."""
    code = (
        "import { Scene } from '@aspose/3d-foss-foss';\n"
        "const lib = require('@aspose/3d-foss-foss');\n"
    )
    fixed = normalize_imports_ast(code, "typescript", "@aspose/3d-foss")
    assert fixed.count("@aspose/3d-foss-foss") == 0
    assert fixed.count("@aspose/3d-foss") == 2
```

---

### Acceptance Checks

**CLI**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/shared/test_ts_analyzer.py::TestNormalizeImportsAst \
  -v 2>&1 | tail -15
# Expected: 8 tests pass (6 original − 1 weakened + 3 new = 8 total)
```

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3
# Expected: 3179+ passed, 0 regressions
```

**Tests**:
- `test_require_syntax` PASS: `@aspose/3d-foss-foss` corrected to `@aspose/3d-foss`
- `test_require_syntax_non_aspose_unchanged` PASS: `lodash` untouched
- `test_require_and_import_both_fixed_in_same_file` PASS: both patterns fixed in one call
- All existing `TestNormalizeImportsAst` tests PASS

**No mock data in production paths**: test uses real tree-sitter parser.

**Config respected end-to-end**: fallback to `normalize_imports()` still active when
`parser is None`.

---

### Deliverables

1. `src/launcher/shared/ts_analyzer.py` — `normalize_imports_ast()` extended with
   CommonJS `require()` loop; docstring updated
2. `tests/unit/shared/test_ts_analyzer.py` — `test_require_syntax_passthrough` replaced
   with `test_require_syntax` (proper assertion) + 2 additional cases

---

### Hard Rules

- Keep `normalize_imports_ast` public signature unchanged
- No new dependencies (tree-sitter already present)
- Fallback path (`parser is None` → `normalize_imports()`) unchanged
- `_child_by_type` is already present in `ts_analyzer.py` — use it; do not duplicate
- Deterministic: byte-precise replacement, reverse-sorted, no randomness
- Non-`@aspose/` imports never touched

---

### Review Dimensions (5/5 criteria for this taskcard)

| Dimension | 5/5 means |
|-----------|-----------|
| Correctness | `require('@aspose/3d-foss-foss')` → `require('@aspose/3d-foss')` in both JS and TS |
| Spec alignment | TC-3904 spec test now passes as written (not xfail) |
| Non-regression | `require('lodash')` untouched; ES import path unchanged |
| Minimality | ~15 lines added to one function; no new helpers |
| Robustness | `_child_by_type` returns None safely; `break` after first string arg prevents over-matching |

---

### Now (Runbook)

```bash
# 1. Extend normalize_imports_ast in ts_analyzer.py
#    After the import_statement loop, add the call_expression loop (see Step 1 above)

# 2. Update tests
#    Replace test_require_syntax_passthrough with test_require_syntax
#    Add test_require_syntax_non_aspose_unchanged
#    Add test_require_and_import_both_fixed_in_same_file

# 3. Verify new tests pass
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/shared/test_ts_analyzer.py::TestNormalizeImportsAst -v

# 4. Verify no regressions
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3

# 5. Quick smoke test from Python REPL (optional)
# .venv/Scripts/python.exe -c "
# from launcher.shared.ts_analyzer import normalize_imports_ast
# print(normalize_imports_ast(\"const x = require('@aspose/3d-foss-foss');\", 'javascript', '@aspose/3d-foss'))
# "
# Expected output: const x = require('@aspose/3d-foss');
```
