---
id: HC-03
title: "Section validator: extend import normalization to all languages"
status: Done
priority: Medium
owner: "agent-B"
updated: "2026-03-07"
tags: [healing, multi-platform, tree-sitter, generate]
depends_on: [TC-3790]
allowed_paths:
  - plans/healing/HC-03_section_validator_multi_lang.md
  - src/launcher/workers/generate/section_validator.py
  - tests/unit/workers/test_section_validator_imports.py
evidence_required:
  - reports/healing/HC-03/evidence.md
---

# Taskcard HC-03 — Section Validator Multi-Language Import Normalization

## Objective

`section_validator.py` line ~159 only normalizes imports for Python
(`if (language or "").lower() in ("python", "py", "python3")`). Non-Python
imports pass through unnormalized, allowing incorrect import statements in
generated content. Dispatch to `ts_analyzer.normalize_imports()` for all
other languages.

## Required spec references

- `specs/worker_generate.md` (Section: section validation)
- `specs/worker_understand.md` (Section: import normalization)

## Scope

### In scope
- Update import normalization branch in section_validator.py to handle non-Python
- Dispatch to `ts_analyzer.normalize_imports()` for Java, C#, JS, TS, Go, PHP, Rust, Ruby
- Add unit tests for multi-language import normalization in section context

### Out of scope
- Changes to ts_analyzer.py normalize_imports (already implemented)
- Python import normalization (already working)

## Inputs

- Section content with code blocks containing imports
- Language tag from product config

## Outputs

- Normalized imports in generated sections for all languages
- Unit tests

## Allowed paths

- plans/healing/HC-03_section_validator_multi_lang.md
- src/launcher/workers/generate/section_validator.py
- tests/unit/workers/test_section_validator_imports.py

### Allowed paths rationale
- section_validator.py: add multi-language dispatch
- test file: new tests for the dispatch

## Implementation steps

### Step 1: Update import normalization dispatch

At line ~159 in section_validator.py, replace the Python-only check:
```python
if (language or "").lower() in ("python", "py", "python3"):
    # existing Python normalization
else:
    try:
        from launcher.shared.ts_analyzer import normalize_imports
        code = normalize_imports(code, language, canonical_import)
    except ImportError:
        pass
```

### Step 2: Add unit tests

Test that Java `import com.aspose.cells.*` gets rewritten to canonical,
C# `using Aspose.Cells;` gets rewritten, etc.

## Failure modes

### Failure mode 1: ts_analyzer not available
**Detection**: ImportError
**Resolution**: Skip normalization (pass through unchanged)
**Gate**: Graceful degradation

### Failure mode 2: normalize_imports corrupts code block
**Detection**: Invalid code after normalization
**Resolution**: Validate snippet after normalization; revert if invalid
**Gate**: Unit test with before/after comparison

### Failure mode 3: Language tag not passed to validator
**Detection**: language is None, defaults to Python path
**Resolution**: Ensure product.lang_tag propagated through generate pipeline
**Gate**: Integration test verifies language tag reaches validator

## Task-specific review checklist

1. [ ] Non-Python languages dispatch to `ts_analyzer.normalize_imports()`
2. [ ] Python path unchanged
3. [ ] Graceful fallback if tree-sitter unavailable
4. [ ] Java import normalization tested
5. [ ] C# using directive normalization tested
6. [ ] Go import normalization tested
7. [ ] No regression in existing Python normalization tests

## Deliverables

1. Updated `src/launcher/workers/generate/section_validator.py`
2. New `tests/unit/workers/test_section_validator_imports.py`
3. Evidence at `reports/healing/HC-03/evidence.md`

## Acceptance checks

1. [ ] section_validator dispatches to ts_analyzer for non-Python
2. [ ] All new tests pass
3. [ ] Full suite: 0 failures

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/healing/HC-03/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_section_validator_imports.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x
```

**Expected results**:
- Import normalization works for Java, C#, Go
- Full suite: 0 regressions

## Integration boundary proven

**Upstream**: ts_analyzer.normalize_imports() from TC-3790
**Downstream**: Generated content with correct imports passed to W4 (Evaluate)
**Contract**: `normalize_imports(code, language, canonical)` returns normalized code string
