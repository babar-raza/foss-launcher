---
id: TC-3901
title: "AST-based TypeScript import normalization (replaces broken regex)"
status: Done
priority: Critical
owner: "Agent-B"
updated: "2026-03-09"
tags: [typescript, imports, ts_analyzer, section_validator, bug-fix]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3901_ts_import_ast_normalization.md
  - src/launcher/shared/ts_analyzer.py
  - src/launcher/workers/generate/section_validator.py
  - tests/test_ts_analyzer.py
evidence_required:
  - reports/agents/B/TC-3901/evidence.md
---

# Taskcard TC-3901 — AST-based TypeScript import normalization

## Objective

Replace the regex-based `normalize_imports()` for JS/TS with a tree-sitter AST implementation
that correctly handles hyphenated npm scoped package names. The current regex `(@aspose/\w+)`
truncates `@aspose/3d-foss` to `@aspose/3d`, then replaces, producing `@aspose/3d-foss-foss`.
This causes 13/59 HIGH severity findings in the 3D TypeScript pilot run.

## Required spec references

- `specs/worker_generate.md` (Section: Post-LLM code block normalization)

## Scope

### In scope
- Add `normalize_imports_ast()` to `src/launcher/shared/ts_analyzer.py`
- Update `src/launcher/workers/generate/section_validator.py:351` to call `normalize_imports_ast`
- Tests in `tests/test_ts_analyzer.py`

### Out of scope
- Python import normalization (handled by separate `_normalize_imports()` in section_validator.py)
- Java, C#, Go, PHP, Rust imports (handled by existing regex `normalize_imports()`)
- Changes to `section_writer.txt` prompt

## Inputs

- `src/launcher/shared/ts_analyzer.py` — existing `normalize_imports()` + `_get_parser()` + `_collect_nodes()`
- `src/launcher/workers/generate/section_validator.py:349-354` — call site

## Outputs

- `normalize_imports_ast()` function in `ts_analyzer.py`
- Updated call in `section_validator.py`
- Tests proving correct → no-op, wrong → fixed, Python → untouched

## Allowed paths

- plans/taskcards/TC-3901_ts_import_ast_normalization.md
- src/launcher/shared/ts_analyzer.py
- src/launcher/workers/generate/section_validator.py
- tests/test_ts_analyzer.py

### Allowed paths rationale
- `ts_analyzer.py`: new function lives here (next to existing normalize_imports)
- `section_validator.py`: call site update (one import + one call change)
- `tests/test_ts_analyzer.py`: test file for ts_analyzer

## Implementation steps

### Step 1: Add `normalize_imports_ast()` to `ts_analyzer.py`

After the existing `normalize_imports()` function (line ~453), add:

```python
def normalize_imports_ast(code: str, language: str, canonical_import: str) -> str:
    """Rewrite @aspose/* imports using tree-sitter AST.

    Byte-precise replacement — handles hyphens, dots, and any npm package name.
    Falls back to regex-based normalize_imports() if tree-sitter unavailable.
    Only processes JS/TS; other languages delegate to normalize_imports().
    """
    resolved = _resolve_lang_name(language)

    if resolved not in ("javascript", "typescript"):
        return normalize_imports(code, language, canonical_import)

    parser = _get_parser(language)
    if parser is None or not canonical_import:
        return normalize_imports(code, language, canonical_import)

    code_bytes = code.encode("utf-8", errors="replace")
    tree = parser.parse(code_bytes)

    replacements: list[tuple[int, int, bytes]] = []
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

    if not replacements:
        return code

    result = bytearray(code_bytes)
    for start, end, new_bytes in sorted(replacements, reverse=True):
        result[start:end] = new_bytes
    return result.decode("utf-8", errors="replace")
```

### Step 2: Update `section_validator.py`

At line 351, change:
```python
from launcher.shared.ts_analyzer import normalize_imports as _ts_normalize
```
to:
```python
from launcher.shared.ts_analyzer import normalize_imports_ast as _ts_normalize
```

### Step 3: Write tests in `tests/test_ts_analyzer.py`

Test cases:
1. Already-correct import → no-op: `"from '@aspose/3d-foss'"` with canonical `@aspose/3d-foss` → unchanged
2. Double-suffix bug fixed: `"from '@aspose/3d-foss-foss'"` → `"from '@aspose/3d-foss'"`
3. Non-aspose import → unchanged: `"from 'lodash'"` → unchanged
4. Python language → delegates to normalize_imports: no AST parsing
5. No tree-sitter → falls back gracefully
6. Named import syntax: `"import { Scene } from '@aspose/3d-foss-foss'"` → corrected

## Failure modes

### Failure mode 1: tree-sitter grammar not installed

**Detection**: `_get_parser("typescript")` returns `None`
**Resolution**: Function falls back to `normalize_imports()` (regex). Logs `no_tree_sitter_grammar` at DEBUG level. No pipeline breakage.
**Gate**: Graceful degradation — existing pattern in codebase

### Failure mode 2: Import uses backtick template literal (rare)

**Detection**: `child.type == "template_string"` instead of `"string"`
**Resolution**: These are not standard static imports — skip them. Falls back to regex for that block.
**Gate**: Template literals in static imports are invalid TypeScript; tree-sitter may parse them differently

### Failure mode 3: Byte offset drift after multi-byte UTF-8

**Detection**: Test case with non-ASCII chars in surrounding code
**Resolution**: Replacements applied in REVERSE byte order so earlier positions are not shifted. Already handled by `sorted(replacements, reverse=True)`.
**Gate**: Unit test with non-ASCII surrounding code

## Task-specific review checklist

1. [ ] `normalize_imports_ast("from '@aspose/3d-foss'", "typescript", "@aspose/3d-foss")` returns unchanged
2. [ ] `normalize_imports_ast("from '@aspose/3d-foss-foss'", "typescript", "@aspose/3d-foss")` returns corrected
3. [ ] Python code block passed to `normalize_imports_ast` delegates to `normalize_imports()` unchanged
4. [ ] `normalize_imports_ast` with `parser=None` falls back without raising
5. [ ] `section_validator.py` imports `normalize_imports_ast` (not `normalize_imports`)
6. [ ] All existing tests pass after change
7. [ ] Docstrings updated for `normalize_imports_ast`
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map — if a trigger event applies, relevant guide updated
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables

1. `src/launcher/shared/ts_analyzer.py` — `normalize_imports_ast()` added after line 453
2. `src/launcher/workers/generate/section_validator.py` — call site updated at line 351
3. `tests/test_ts_analyzer.py` — 6 new test cases
4. `reports/agents/B/TC-3901/evidence.md`

## Acceptance checks

1. [ ] `normalize_imports_ast("from '@aspose/3d-foss-foss'", "typescript", "@aspose/3d-foss")` == `"from '@aspose/3d-foss'"`
2. [ ] `normalize_imports_ast("from '@aspose/3d-foss'", "typescript", "@aspose/3d-foss")` == `"from '@aspose/3d-foss'"` (no change)
3. [ ] All existing tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3`

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/agents/B/TC-3901/evidence.md
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --uncommitted`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_ts_analyzer.py -v -k "normalize_import"
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -5
```

**Expected results**:
- All 6 new tests pass
- No existing test regressions

## Integration boundary proven

**Upstream**: `section_validator.py:349-354` — receives LLM-generated code block + language + canonical_import
**Downstream**: Returns normalized code string with correct import path
**Contract**: If `inner == canonical_import` → no-op. If tree-sitter unavailable → regex fallback.
