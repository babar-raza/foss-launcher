---
id: TC-3790
title: "TreeSitterAnalyzer foundation — universal multi-language code analysis"
status: In-Progress
priority: High
owner: "agent-B"
updated: "2026-03-07"
tags: [multi-platform, tree-sitter, understand]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3790_treesitter_analyzer_foundation.md
  - src/launcher/shared/ts_analyzer.py
  - src/launcher/shared/code_analyzer.py
  - pyproject.toml
  - tests/unit/shared/test_ts_analyzer.py
evidence_required:
  - reports/agents/B/TC-3790/evidence.md
---

# Taskcard TC-3790 — TreeSitterAnalyzer Foundation

## Objective

Create a universal code analyzer using tree-sitter that handles all non-Python
languages (Java, C#, JS, TS, Go, PHP, Rust, Ruby, and any future language)
with AST-level parsing. Python keeps its existing stdlib `ast` analyzer
untouched. This establishes the dual-parser architecture.

## Required spec references

- `specs/worker_understand.md` (Phase B: Extract — AST parsing)
- `specs/product_model.md` (Platform taxonomy)

## Scope

### In scope
- New `ts_analyzer.py` module with `TreeSitterAnalyzer` class
- Language loading for all target languages (including C# via separate package)
- Class/function/constant extraction via AST traversal
- Doc comment extraction (Javadoc, XML doc, JSDoc, GoDoc, PHPDoc, rustdoc, YARD)
- Import/export extraction per language
- Snippet validation via `has_error`
- Import normalization per language
- Dispatcher update in `code_analyzer.py`
- Dependency addition to `pyproject.toml`
- Comprehensive test suite

### Out of scope
- Changes to Python analyzer (stays untouched)
- Pipeline integration (Phase 4 cross-cutting fixes)
- Manifest parsing changes (Phase 5)

## Inputs
- Source code files in any of 165+ tree-sitter-supported languages
- Language name string (from file_classifier.LANG_BY_EXT)

## Outputs
- `AnalysisResult` dataclass matching Python analyzer output shape
- Validated snippets (True/False)
- Extracted doc comments, imports, exports

## Allowed paths
- plans/taskcards/TC-3790_treesitter_analyzer_foundation.md
- src/launcher/shared/ts_analyzer.py
- src/launcher/shared/code_analyzer.py
- pyproject.toml
- tests/unit/shared/test_ts_analyzer.py

### Allowed paths rationale
- ts_analyzer.py: New module — core deliverable
- code_analyzer.py: Dispatcher update to route non-Python to ts_analyzer
- pyproject.toml: Add tree-sitter dependencies
- tests: Verification

## Implementation steps

### Step 1: Add dependencies to pyproject.toml
Add `tree-sitter>=0.25.0`, `tree-sitter-language-pack>=0.13.0`,
`tree-sitter-c-sharp>=0.23.0` to dependencies.

### Step 2: Create ts_analyzer.py
Build TreeSitterAnalyzer class with:
- Language loading (language-pack for most, separate package for C#)
- `analyze_file()` -> AnalysisResult
- `validate_snippet()` -> bool
- `extract_doc_comments()` -> list
- `extract_imports()` -> list
- `extract_exports()` -> list
- `normalize_imports()` -> str
- Language query registry with generic fallback

### Step 3: Update code_analyzer.py dispatcher
Modify `analyze_file_safe()` to route non-Python to TreeSitterAnalyzer.

### Step 4: Write comprehensive tests
Test all target languages with synthetic code strings.

## Failure modes

### Failure mode 1: tree-sitter grammar unavailable for a language
**Detection**: `LookupError` from `get_parser()`
**Resolution**: Fall back to generic traversal or empty AnalysisResult
**Gate**: Graceful degradation — never crash on unsupported language

### Failure mode 2: C# uses separate package, not in language-pack
**Detection**: `LookupError: Could not find language library for c_sharp`
**Resolution**: Use `tree_sitter_c_sharp.language()` directly
**Gate**: Language loading must handle both paths

### Failure mode 3: tree-sitter v0.25 API changes (no query.matches())
**Detection**: `AttributeError` on Query object
**Resolution**: Use recursive AST traversal instead of query API
**Gate**: All extraction must work without query.matches()

## Task-specific review checklist

1. [ ] TreeSitterAnalyzer.analyze_file() returns AnalysisResult for all 8 named languages
2. [ ] AnalysisResult shape matches Python analyzer output
3. [ ] validate_snippet() catches broken code and passes valid code
4. [ ] Doc comments extracted for Java, C#, JS/TS, Go, PHP, Rust, Ruby
5. [ ] Import/export extraction works for all target languages
6. [ ] Import normalization rewrites Aspose imports to canonical form
7. [ ] Generic fallback works for unlisted languages (Kotlin, Dart, Scala)
8. [ ] C# loading via separate package works
9. [ ] No existing tests broken
10. [ ] code_analyzer.py dispatcher routes correctly

## Deliverables

1. `src/launcher/shared/ts_analyzer.py`
2. Updated `src/launcher/shared/code_analyzer.py`
3. Updated `pyproject.toml`
4. `tests/unit/shared/test_ts_analyzer.py`

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_ts_analyzer.py -v` — all pass
2. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x` — full suite, 0 failures
3. [ ] TreeSitterAnalyzer works for Java, C#, JS, TS, Go, PHP, Rust, Ruby, Kotlin, Dart, Scala

## Self-review

### Verification results
- [ ] Tests: PASS
- [ ] Full regression: PASS
- [ ] Evidence captured

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_ts_analyzer.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x
```

**Expected results**:
- All new tests pass
- All existing 9454+ tests pass

## Integration boundary proven

**Upstream**: file_classifier.py provides language name from file extension
**Downstream**: extract.py, worker.py consume AnalysisResult for snippet validation and claim extraction
**Contract**: AnalysisResult dataclass with classes, functions, constants, imports, exports, module_path, language
