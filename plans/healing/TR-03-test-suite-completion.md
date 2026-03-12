# TR-03 — Complete TC-3904 Test Suite (Dropped + Weakened Tests)

**Source**: Self-review of TC-3904, GAP-04 + GAP-05 + GAP-06 + GAP-07.
**Date**: 2026-03-09
**Sprint**: Thin-Repo Parity — Post-implementation healing.
**Depends on**: TR-01 (GAP-04), TR-02 (GAP-05). GAP-06 and GAP-07 are independent.

---

## Context

TC-3904 delivered 15 tests, but 4 gaps remain in test coverage:

| Gap | Test file | What's missing |
|-----|-----------|----------------|
| GAP-04 | `test_section_prompt.py` | Spec's 4th test (`test_skip_fires_with_code_evidence_sparse_flag`) was dropped; it requires TR-01 to be implemented first |
| GAP-05 | `test_ts_analyzer.py` | `test_require_syntax` was weakened to `assert isinstance(result, str)` instead of asserting the fix; requires TR-02 |
| GAP-06 | `test_surface_classifier.py` | No test verifies the `reason` string contains `code_evidence=X(sparse=Y)` |
| GAP-07 | `test_ts_analyzer.py` | No test for the fallback path when `_get_parser` returns `None` |

GAP-04 and GAP-05 are unblocked by TR-01 and TR-02 respectively. GAP-06 and GAP-07 are
independent and can be done at any time.

---

## Taskcard TR-03

**Status**: Done
**Gap linkage**: GAP-04, GAP-05, GAP-06, GAP-07
**Role**: Senior engineer. Drop-in, production-ready.

---

### Scope

**Fix**: Complete the TC-3904 test suite by:
1. (After TR-01) Add `test_skip_fires_with_code_evidence_sparse_flag` (GAP-04)
2. (After TR-02) Replace `test_require_syntax_passthrough` with `test_require_syntax` (GAP-05)
3. (Independent) Add `test_reason_string_includes_sparse_info` (GAP-06)
4. (Independent) Add `test_normalize_imports_ast_fallback_when_no_parser` (GAP-07)

**Allowed paths**:
- `tests/unit/shared/test_ts_analyzer.py`
- `tests/unit/workers/generate/test_section_prompt.py`
- `tests/unit/shared/test_surface_classifier.py`

**Forbidden**: any other file or path. No production code changes.

---

### Implementation Steps

#### Step 1 — GAP-06 (independent): `tests/unit/shared/test_surface_classifier.py`

Add to `TestCodeEvidenceSparse`:

```python
def test_reason_string_includes_sparse_info(self) -> None:
    """classify_richness_with_surface reason string carries code_evidence=X(sparse=Y)."""
    repo = _make_repo_info(example_count=0)
    result = classify_richness_with_surface(repo, extracted_snippet_count=0)
    assert "code_evidence=0" in result.reason
    assert "sparse=True" in result.reason

def test_reason_string_sparse_false_for_rich_repo(self) -> None:
    """Rich repo reason string shows sparse=False."""
    repo = _make_repo_info(example_count=10, doc_count=5, readme="x" * 600)
    result = classify_richness_with_surface(repo, extracted_snippet_count=15)
    # code_evidence_score = min(10,10) + min(15,10) = 20
    assert "code_evidence=20" in result.reason
    assert "sparse=False" in result.reason
```

#### Step 2 — GAP-07 (independent): `tests/unit/shared/test_ts_analyzer.py`

Add to `TestNormalizeImportsAst`:

```python
def test_fallback_when_parser_unavailable(self, monkeypatch):
    """When _get_parser returns None, falls back to regex normalize_imports gracefully."""
    import launcher.shared.ts_analyzer as _ts
    monkeypatch.setattr(_ts, "_get_parser", lambda _lang: None)
    # Correct import — regex fallback is a no-op for already-correct specifiers
    code = "import { Scene } from '@aspose/3d-foss';"
    result = normalize_imports_ast(code, "typescript", "@aspose/3d-foss")
    assert isinstance(result, str)
    # Should not raise; behavior is defined (delegates to normalize_imports)
```

#### Step 3 — GAP-04 (requires TR-01): `tests/unit/workers/generate/test_section_prompt.py`

Add to `TestSkipInstruction`:

```python
def test_skip_fires_with_code_evidence_sparse_flag(self) -> None:
    """code_evidence_sparse=True triggers EVIDENCE ABSENT for non-code roles (TR-01).

    Regression guard: verifies that a non-code page role with code_evidence_sparse=True
    still receives the EVIDENCE ABSENT instruction when no snippets are available.
    blog_announcement is not in _CODE_EVIDENCE_ROLES — only the sparse flag fires this.
    """
    from launcher.models.plan import PlannedPage
    from launcher.workers.generate.section_prompt import build_section_prompt
    from launcher.shared.page_skeletons import SkeletonSection

    page = PlannedPage(
        page_id="tr03-sparse-gate-test",
        page_role="blog_announcement",   # NOT in _CODE_EVIDENCE_ROLES
        title="TR-03 Sparse Gate Test",
        assigned_claims=["CLM-TR03"],
        code_evidence_sparse=True,       # TR-01 field
    )
    section = SkeletonSection("Announcement", 2, True, "Describe the release.", 50, 300)
    claim = Claim(
        claim_id="CLM-TR03",
        text="New 3D file format support.",
        kind="feature",
        evidence=[],
    )
    prompt = build_section_prompt(section, 0, 1, page, _make_product(), [claim], [])
    assert "EVIDENCE ABSENT" in prompt
```

#### Step 4 — GAP-05 (requires TR-02): `tests/unit/shared/test_ts_analyzer.py`

Replace `test_require_syntax_passthrough` with the spec-required test.
Note: this step is identical to what TR-02 delivers in its Step 2. If TR-02 has already
added the test, this step is a no-op. The canonical home for the `require()` tests is
TR-02's implementation; TR-03 only needs to verify TR-02's deliverable is present.

Verify the following exist after TR-02:
- `test_require_syntax` — asserts `@aspose/3d-foss-foss` not in output
- `test_require_syntax_non_aspose_unchanged` — asserts `lodash` untouched
- `test_require_and_import_both_fixed_in_same_file` — mixed-syntax test

If any are absent (e.g., TR-02 was not fully executed), add them here.

---

### Final Test Count After TR-03

| File | Before TR-03 | After TR-03 | Net |
|------|:---:|:---:|:---:|
| `test_ts_analyzer.py::TestNormalizeImportsAst` | 6 | 8 (+GAP-07, TR-02 replaces GAP-05) | +2 |
| `test_surface_classifier.py::TestCodeEvidenceSparse` | 5 | 7 (+GAP-06 ×2) | +2 |
| `test_section_prompt.py::TestSkipInstruction` | 4 | 5 (+GAP-04, TR-01 adds 1 more) | +1–2 |
| **Total new** | — | — | **+5–6** |

---

### Acceptance Checks

**CLI** (run after TR-01 and TR-02 are complete):
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/shared/test_ts_analyzer.py::TestNormalizeImportsAst \
  tests/unit/shared/test_surface_classifier.py::TestCodeEvidenceSparse \
  tests/unit/workers/generate/test_section_prompt.py::TestSkipInstruction \
  -v 2>&1 | tail -25
# Expected: all tests pass, including the 5-6 new ones
```

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3
# Expected: 3183+ passed, 0 regressions
```

**Tests (GAP-06)**:
- `test_reason_string_includes_sparse_info`: `"code_evidence=0"` and `"sparse=True"` in reason
- `test_reason_string_sparse_false_for_rich_repo`: `"code_evidence=20"` and `"sparse=False"` in reason

**Tests (GAP-07)**:
- `test_fallback_when_parser_unavailable`: does not raise; returns a string

**Tests (GAP-04, after TR-01)**:
- `test_skip_fires_with_code_evidence_sparse_flag`: `"EVIDENCE ABSENT"` in prompt for
  `blog_announcement` role with `code_evidence_sparse=True`

**Tests (GAP-05, after TR-02)**:
- `test_require_syntax`: `"@aspose/3d-foss-foss"` NOT in output; `"@aspose/3d-foss"` IN output

**No mock data in production paths**: all tests use real models/functions.

---

### Deliverables

1. `tests/unit/shared/test_surface_classifier.py` — 2 new tests in `TestCodeEvidenceSparse`
   (GAP-06; independent, can land immediately)
2. `tests/unit/shared/test_ts_analyzer.py` — 1 new test in `TestNormalizeImportsAst`
   (GAP-07; independent); GAP-05 handled by TR-02
3. `tests/unit/workers/generate/test_section_prompt.py` — 1 new test in `TestSkipInstruction`
   (GAP-04; requires TR-01)

---

### Hard Rules

- No production code changes (test-only taskcard)
- No network in tests (`monkeypatch` used for GAP-07, no HTTP)
- `monkeypatch` scoped to individual test function — no module-level state mutation
- `PYTHONHASHSEED=0` safe: no dict iteration or set ordering in new tests
- Keep existing test method names (no rename of passing tests)

---

### Review Dimensions (5/5 criteria for this taskcard)

| Dimension | 5/5 means |
|-----------|-----------|
| Spec alignment | All 4 gaps from TC-3904 spec deviation are closed |
| Coverage | Every meaningful branch of TR-01 and TR-02 fixes has a regression guard |
| Robustness | `test_fallback_when_parser_unavailable` covers the degradation path |
| Minimality | Tests only; no production code; small, focused additions |
| Independence | GAP-06 + GAP-07 can land before TR-01/TR-02 are complete |

---

### Now (Runbook)

```bash
# Phase A: Independent (no blocking dependencies)

# 1a. Add GAP-06 tests to test_surface_classifier.py
#     TestCodeEvidenceSparse: add test_reason_string_includes_sparse_info
#                                    test_reason_string_sparse_false_for_rich_repo

# 1b. Add GAP-07 test to test_ts_analyzer.py
#     TestNormalizeImportsAst: add test_fallback_when_parser_unavailable

# 1c. Verify Phase A
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/shared/test_surface_classifier.py::TestCodeEvidenceSparse \
  tests/unit/shared/test_ts_analyzer.py::TestNormalizeImportsAst \
  -v 2>&1 | tail -15

# Phase B: After TR-01 is complete
# 2. Add GAP-04 test to test_section_prompt.py::TestSkipInstruction
#    test_skip_fires_with_code_evidence_sparse_flag

PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/generate/test_section_prompt.py::TestSkipInstruction -v

# Phase C: After TR-02 is complete
# 3. Verify GAP-05 tests are present (TR-02 should have added them)
#    If absent: add test_require_syntax + test_require_syntax_non_aspose_unchanged

PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/shared/test_ts_analyzer.py::TestNormalizeImportsAst -v

# Phase D: Full suite regression check
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3
```
