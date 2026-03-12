---
id: TC-3904
title: "Thin-repo regression test suite (3D TypeScript fixture)"
status: Done
priority: Normal
owner: "Agent-C"
updated: "2026-03-09"
tags: [tests, thin-repo, regression, typescript, ts_analyzer, section_prompt, surface_classifier]
depends_on: [TC-3901, TC-3902, TC-3903]
allowed_paths:
  - plans/taskcards/TC-3904_thin_repo_regression_tests.md
  - tests/test_ts_analyzer.py
  - tests/test_section_prompt.py
  - tests/test_surface_classifier.py
evidence_required:
  - reports/agents/C/TC-3904/evidence.md
---

# Taskcard TC-3904 — Thin-repo regression test suite

## Objective

Add deterministic unit tests that exercise all three thin-repo fixes and prevent future
regression. These tests serve as CI gates: if any of the three fixes is accidentally
reverted, at least one test fails immediately.

## Required spec references

- None (test-only taskcard)

## Scope

### In scope
- Tests for `normalize_imports_ast()` (TC-3901) in `tests/test_ts_analyzer.py`
- Tests for skip_instruction injection (TC-3902) in `tests/test_section_prompt.py`
- Tests for `code_evidence_sparse` flag (TC-3903) in `tests/test_surface_classifier.py`

### Out of scope
- Integration / E2E tests (pilot re-runs)
- Changes to production code

## Inputs

- All three implementation TCs must be Done (TC-3901, TC-3902, TC-3903)

## Outputs

- New test cases in three existing test files

## Allowed paths

- plans/taskcards/TC-3904_thin_repo_regression_tests.md
- tests/test_ts_analyzer.py
- tests/test_section_prompt.py
- tests/test_surface_classifier.py

## Implementation steps

### Step 1: `tests/test_ts_analyzer.py` — normalize_imports_ast (6 cases)

```python
def test_normalize_imports_ast_no_change_when_correct():
    code = "import { Scene } from '@aspose/3d-foss';"
    assert normalize_imports_ast(code, "typescript", "@aspose/3d-foss") == code

def test_normalize_imports_ast_fixes_double_suffix():
    code = "import { Scene } from '@aspose/3d-foss-foss';"
    fixed = normalize_imports_ast(code, "typescript", "@aspose/3d-foss")
    assert "@aspose/3d-foss-foss" not in fixed
    assert "@aspose/3d-foss" in fixed

def test_normalize_imports_ast_non_aspose_unchanged():
    code = "import _ from 'lodash';"
    assert normalize_imports_ast(code, "typescript", "@aspose/3d-foss") == code

def test_normalize_imports_ast_python_delegates():
    """Python language routes to existing normalize_imports(), not AST path."""
    code = "import Aspose.Cells"
    # Should not raise; Python handled by different branch
    result = normalize_imports_ast(code, "python", "aspose_cells_foss")
    assert isinstance(result, str)

def test_normalize_imports_ast_require_syntax():
    code = "const lib = require('@aspose/3d-foss-foss');"
    fixed = normalize_imports_ast(code, "javascript", "@aspose/3d-foss")
    assert "@aspose/3d-foss-foss" not in fixed

def test_normalize_imports_ast_named_import():
    code = "import { Renderer, Scene } from '@aspose/3d-foss-foss';"
    fixed = normalize_imports_ast(code, "typescript", "@aspose/3d-foss")
    assert "from '@aspose/3d-foss'" in fixed
    assert "3d-foss-foss" not in fixed
```

### Step 2: `tests/test_section_prompt.py` — skip_instruction injection (4 cases)

```python
def test_skip_instruction_injected_when_no_snippets_code_required():
    """Evidence-absent instruction fires for code-required roles with no snippets."""
    # Build a minimal PlannedPage for a code-required role with no snippets
    prompt = build_section_prompt(..., section_snippets=[], page_role="installation")
    assert "EVIDENCE ABSENT" in prompt

def test_skip_instruction_absent_when_snippets_present():
    """Rich repo: instruction never injected when snippets available."""
    prompt = build_section_prompt(..., section_snippets=[some_snippet], page_role="installation")
    assert "EVIDENCE ABSENT" not in prompt

def test_skip_instruction_absent_for_non_code_role():
    """Non-code roles: instruction not injected even with no snippets."""
    prompt = build_section_prompt(..., section_snippets=[], page_role="blog_announcement")
    assert "EVIDENCE ABSENT" not in prompt

def test_skip_instruction_fires_with_code_evidence_sparse_flag():
    """code_evidence_sparse=True + no snippets triggers instruction regardless of role."""
    page = make_planned_page(richness_tier=RichnessResult(..., code_evidence_sparse=True))
    prompt = build_section_prompt(..., section_snippets=[], page=page)
    assert "EVIDENCE ABSENT" in prompt
```

### Step 3: `tests/test_surface_classifier.py` — code_evidence_sparse (5 cases)

```python
def test_code_evidence_sparse_true_for_zero_evidence():
    repo = make_repo_info(example_paths=[], ...)
    result = classify_richness_with_surface(repo, extracted_snippet_count=0)
    assert result.code_evidence_sparse is True

def test_code_evidence_sparse_false_for_rich_repo():
    repo = make_repo_info(example_paths=["ex1.py"]*10, ...)
    result = classify_richness_with_surface(repo, extracted_snippet_count=15)
    assert result.code_evidence_sparse is False

def test_code_evidence_sparse_boundary_below():
    repo = make_repo_info(example_paths=["ex1.py", "ex2.py"], ...)
    result = classify_richness_with_surface(repo, extracted_snippet_count=0)
    assert result.code_evidence_sparse is True  # 2 < 3

def test_code_evidence_sparse_boundary_at():
    repo = make_repo_info(example_paths=["ex1.py", "ex2.py", "ex3.py"], ...)
    result = classify_richness_with_surface(repo, extracted_snippet_count=0)
    assert result.code_evidence_sparse is False  # 3 == 3, NOT < 3

def test_classify_richness_base_has_default_false():
    repo = make_repo_info(example_paths=[], ...)
    result = classify_richness(repo)
    assert result.code_evidence_sparse is False  # default, not computed
```

## Failure modes

### Failure mode 1: Test helpers (make_repo_info, make_planned_page) not available

**Detection**: `NameError` or fixture missing in test file
**Resolution**: Use existing test fixtures from the test file; add minimal inline builders if needed
**Gate**: Test import check

### Failure mode 2: `build_section_prompt` signature changes in TC-3902

**Detection**: Test fails with wrong argument error
**Resolution**: Update test calls to match final `build_section_prompt` signature from TC-3902
**Gate**: Sequential dependency — run TC-3902 first

### Failure mode 3: tree-sitter not installed in test environment

**Detection**: `normalize_imports_ast` falls back to regex, test_normalize_imports_ast_fixes_double_suffix fails
**Resolution**: The regex fallback still has the `\w+` bug → test would fail → signals tree-sitter is needed for CI. Add tree-sitter to test dependencies.
**Gate**: CI dependency check

## Task-specific review checklist

1. [x] 6 normalize_imports_ast tests added to test_ts_analyzer.py
2. [x] 4 skip_instruction tests added to test_section_prompt.py
3. [x] 5 code_evidence_sparse tests added to test_surface_classifier.py
4. [x] All 15 new tests pass under PYTHONHASHSEED=0
5. [x] No existing tests broken (3176 passed, up from 3161)
6. [x] Docstrings added to test functions (one-line description)
7. [x] No spec changes needed (test-only)
8. [x] No schema changes needed
9. [x] Checked docs/README.md ownership map — no trigger
10. [x] No new docs guides added
11. [x] Test file headers note dependency on TC-3901/3902/3903

## Deliverables

1. `tests/test_ts_analyzer.py` — 6 new test cases
2. `tests/test_section_prompt.py` — 4 new test cases
3. `tests/test_surface_classifier.py` — 5 new test cases
4. `reports/agents/C/TC-3904/evidence.md`

## Acceptance checks

1. [x] All 15 new tests pass
2. [x] Full suite passes: 3176 passed, 1 skipped, 3 xfailed

## Self-review

### Verification results
- [x] Tests: 15/15 PASS
- [x] Evidence captured: reports/agents/C/TC-3904/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_ts_analyzer.py tests/test_section_prompt.py tests/test_surface_classifier.py -v 2>&1 | tail -30
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -5
```

## Integration boundary proven

**Upstream**: TC-3901, TC-3902, TC-3903 implementations
**Downstream**: CI — these tests run on every commit
**Contract**: If any fix is reverted, at least one test fails immediately
