---
id: HC-01
title: "Import allowlist: replace regex with TreeSitterAnalyzer.extract_exports()"
status: Done
priority: High
owner: "agent-B"
updated: "2026-03-07"
tags: [healing, multi-platform, tree-sitter, understand]
depends_on: [TC-3790]
allowed_paths:
  - plans/healing/HC-01_import_allowlist_treesitter.md
  - src/launcher/workers/understand/extract.py
  - tests/unit/workers/test_extract_allowlist.py
evidence_required:
  - reports/healing/HC-01/evidence.md
---

# Taskcard HC-01 — Import Allowlist: TreeSitter Integration

## Objective

Replace the regex-based import allowlist builder in `extract.py` (lines 477-563)
with `TreeSitterAnalyzer.extract_exports()` for non-Python languages. Currently
Java and C# use first-match regex that misses most public API surfaces.

## Required spec references

- `specs/worker_understand.md` (Section: import allowlist construction)

## Scope

### In scope
- Update `_build_import_allowlist()` to call `TreeSitterAnalyzer.extract_exports()` for non-Python
- Keep Python path unchanged (uses `__all__` / AST inspection)
- Add unit tests for Java, C#, Go, Rust export extraction in allowlist context

### Out of scope
- Changes to `ts_analyzer.py` itself (already handles exports)
- Import normalization in section_validator (HC-03)

## Inputs

- TreeSitterAnalyzer with working `extract_exports()` (TC-3790)
- Source files in any language from repo_info

## Outputs

- Updated `_build_import_allowlist()` dispatching to TreeSitterAnalyzer
- Unit tests proving multi-language export extraction

## Allowed paths

- plans/healing/HC-01_import_allowlist_treesitter.md
- src/launcher/workers/understand/extract.py
- tests/unit/workers/test_extract_allowlist.py

### Allowed paths rationale
- extract.py: contains `_build_import_allowlist()` to update
- test file: new tests for the updated function

## Implementation steps

### Step 1: Update `_build_import_allowlist()`

In `extract.py` lines 477-563, add a branch for non-Python languages:
```python
if lang != "python":
    from launcher.shared.ts_analyzer import analyzer as _ts
    exports = _ts.extract_exports_from_code(source_code, lang)
    allowlist.update(exports)
```

### Step 2: Add unit tests

Create `tests/unit/workers/test_extract_allowlist.py` with synthetic Java/C#/Go/Rust
source files and verify that public/exported names appear in the allowlist.

## Failure modes

### Failure mode 1: TreeSitterAnalyzer not available
**Detection**: ImportError when importing ts_analyzer
**Resolution**: Fall back to existing regex behavior (graceful degradation)
**Gate**: No crash on missing dependency

### Failure mode 2: export extraction returns empty for valid source
**Detection**: allowlist is empty when source has public classes
**Resolution**: Debug tree-sitter node types for that language; add to `_CLASS_TYPES`
**Gate**: Unit test catches empty allowlist

### Failure mode 3: Over-extraction pollutes allowlist
**Detection**: Private/internal names appear in allowlist
**Resolution**: Tighten `_is_public()` checks per language
**Gate**: Unit test verifies only public names included

## Task-specific review checklist

1. [ ] `_build_import_allowlist()` dispatches to TreeSitterAnalyzer for non-Python
2. [ ] Python path unchanged (still uses `__all__` / AST)
3. [ ] Graceful fallback if tree-sitter unavailable
4. [ ] Java public classes appear in allowlist
5. [ ] C# public classes appear in allowlist
6. [ ] Go exported (capitalized) names appear in allowlist
7. [ ] Rust `pub` items appear in allowlist
8. [ ] Private/internal names excluded from allowlist

## Deliverables

1. Updated `src/launcher/workers/understand/extract.py`
2. New `tests/unit/workers/test_extract_allowlist.py`
3. Evidence at `reports/healing/HC-01/evidence.md`

## Acceptance checks

1. [ ] `_build_import_allowlist()` uses TreeSitterAnalyzer for Java/C#/Go/Rust
2. [ ] All new unit tests pass
3. [ ] Full test suite: 0 failures
4. [ ] Python allowlist behavior unchanged

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/healing/HC-01/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_extract_allowlist.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x
```

**Expected results**:
- All allowlist tests pass
- Full suite: 0 regressions

## Integration boundary proven

**Upstream**: TreeSitterAnalyzer.extract_exports() from TC-3790
**Downstream**: Import validation in section_validator (HC-03), snippet import normalization
**Contract**: `extract_exports()` returns `list[str]` of public/exported names
