---
id: HC-04
title: "code_analyzer.py: multi-platform discovery + limitations + DRY cleanup"
status: Done
priority: Medium
owner: "agent-B"
updated: "2026-03-07"
tags: [healing, multi-platform, understand, cleanup]
depends_on: [TC-3790]
allowed_paths:
  - plans/healing/HC-04_code_analyzer_multi_platform.md
  - src/launcher/shared/code_analyzer.py
  - tests/unit/shared/test_code_analyzer_multi_platform.py
evidence_required:
  - reports/healing/HC-04/evidence.md
---

# Taskcard HC-04 — code_analyzer.py Multi-Platform Gaps + Cleanup

## Objective

Fix 5 related gaps in `code_analyzer.py`, all stemming from Python-centric
assumptions:

1. `discover_source_files` (line ~1764): missing `.java`, `.php`, `.rs`, `.rb`, `.kt`, `.dart`, `.scala`
2. `discover_manifests` (line ~1788): missing `pom.xml`, `build.gradle`, `build.gradle.kts`
3. `extract_code_limitations` (line ~1987): only walks `*.py` files
4. DRY violation: `_EXT_TO_LANG` dict duplicates `file_classifier.LANG_BY_EXT`
5. Dead regex fallback code after TreeSitterAnalyzer try/except in `analyze_file_safe()`

## Required spec references

- `specs/worker_understand.md` (Section: source discovery, code limitations)

## Scope

### In scope
- Add missing extensions to `discover_source_files`
- Add missing manifests to `discover_manifests`
- Extend `extract_code_limitations` to walk all source extensions
- Replace `_EXT_TO_LANG` with import from `file_classifier.LANG_BY_EXT`
- Remove dead regex fallback after TreeSitterAnalyzer in `analyze_file_safe()`

### Out of scope
- `_detect_public_entrypoints` beyond `__init__.py` (low value, complex per-language)
- Manifest content parsing (HC-05 / future TC)

## Inputs

- `file_classifier.LANG_BY_EXT` as canonical extension → language mapping

## Outputs

- Updated code_analyzer.py with multi-platform discovery
- Unit tests for new extensions

## Allowed paths

- plans/healing/HC-04_code_analyzer_multi_platform.md
- src/launcher/shared/code_analyzer.py
- tests/unit/shared/test_code_analyzer_multi_platform.py

### Allowed paths rationale
- code_analyzer.py: all 5 fixes are in this file
- test file: new tests for multi-platform discovery

## Implementation steps

### Step 1: Replace `_EXT_TO_LANG` with `LANG_BY_EXT`

```python
from launcher.workers.understand.file_classifier import LANG_BY_EXT
# Delete the _EXT_TO_LANG dict entirely
# Update analyze_file_safe() to use LANG_BY_EXT.get(ext)
```

### Step 2: Add missing extensions to `discover_source_files`

Add `.java`, `.php`, `.rs`, `.rb`, `.kt`, `.kts`, `.dart`, `.scala`, `.swift` to
the glob patterns.

### Step 3: Add missing manifests to `discover_manifests`

Add `pom.xml`, `build.gradle`, `build.gradle.kts`, `*.gemspec` to manifest patterns.

### Step 4: Extend `extract_code_limitations`

Replace `*.py` glob with iteration over all source extensions from `LANG_BY_EXT`.
Use TreeSitterAnalyzer for non-Python files to detect TODO/FIXME/NotImplemented.

### Step 5: Remove dead regex fallback

In `analyze_file_safe()`, remove the regex fallback code that follows the
TreeSitterAnalyzer try/except block. The TreeSitterAnalyzer already has its
own graceful degradation.

## Failure modes

### Failure mode 1: Circular import from file_classifier
**Detection**: ImportError at module load
**Resolution**: Use lazy import inside function body
**Gate**: Module loads without error

### Failure mode 2: Too many files discovered slows pipeline
**Detection**: Understand phase takes >5x longer
**Resolution**: Add file count limit or depth limit to discovery
**Gate**: Performance within 2x of Python-only baseline

### Failure mode 3: extract_code_limitations crashes on non-Python
**Detection**: Exception during limitation extraction
**Resolution**: Wrap in try/except with graceful skip
**Gate**: No crash on any language

## Task-specific review checklist

1. [ ] `_EXT_TO_LANG` removed, replaced by `LANG_BY_EXT` import
2. [ ] `discover_source_files` includes all LANG_BY_EXT extensions
3. [ ] `discover_manifests` includes pom.xml, build.gradle, build.gradle.kts
4. [ ] `extract_code_limitations` walks all source extensions
5. [ ] Dead regex fallback removed from `analyze_file_safe()`
6. [ ] No circular import issues
7. [ ] All existing tests pass

## Deliverables

1. Updated `src/launcher/shared/code_analyzer.py`
2. New `tests/unit/shared/test_code_analyzer_multi_platform.py`
3. Evidence at `reports/healing/HC-04/evidence.md`

## Acceptance checks

1. [ ] `discover_source_files` finds .java, .rs, .go files in test fixtures
2. [ ] `discover_manifests` finds pom.xml, build.gradle in test fixtures
3. [ ] `extract_code_limitations` processes non-Python files
4. [ ] `_EXT_TO_LANG` no longer exists in code_analyzer.py
5. [ ] Full suite: 0 failures

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/healing/HC-04/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_code_analyzer_multi_platform.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x
```

**Expected results**:
- All discovery tests find multi-language files
- Full suite: 0 regressions

## Integration boundary proven

**Upstream**: File system (repo source files and manifests)
**Downstream**: Understand worker uses discovery results for analysis scope
**Contract**: `discover_source_files()` returns list of paths; `discover_manifests()` returns list of paths
