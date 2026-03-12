---
id: GR-01
title: "Fix grade-B parametrize showing [NOTSET] when no grade-B pages exist"
status: Open
priority: Medium
owner: agent
updated: "2026-03-09"
tags: [golden, regression, test-quality]
depends_on: []
allowed_paths:
  - plans/healing/GR-01-grade-b-notset-fix.md
  - tests/golden/test_checks_regression.py
evidence_required:
  - reports/GR-01/evidence.md
---

# GR-01 — Fix grade-B parametrize [NOTSET] confusion

## Objective

When `_load_grade_b_pages()` returns an empty list, pytest parametrize generates
a single test case with ID `[NOTSET]` that always passes vacuously. Replace with
a non-parametrized smoke test that explicitly skips if no grade-B pages exist,
making the empty-list state visible rather than silently collected.

## Gap source

TC-3876b self-review: the current grade corpus has no `grade: B` files.
The `test_no_critical_on_grade_b[NOTSET]` test appears to pass but proves nothing.

## Required spec references

- `plans/purrfect-beaming-crown.md` (Phase 1 — TC-3876b section)

## Scope

### In scope
- Replace `@pytest.mark.parametrize` on `test_no_critical_on_grade_b` with a
  non-parametrized function that loops and skips cleanly
- Add `test_grade_b_pages_exist_or_skip` smoke test

### Out of scope
- Adding grade-B golden files to the corpus (separate concern)
- Any changes to `golden_loader.py`

## Inputs

- `tests/golden/test_checks_regression.py` (current implementation)
- `golden/` directory (runtime — checked at test collection)

## Outputs

- `tests/golden/test_checks_regression.py` (modified)
- `reports/GR-01/evidence.md`

## Allowed paths

- plans/healing/GR-01-grade-b-notset-fix.md
- tests/golden/test_checks_regression.py

### Allowed paths rationale

Single test file change to fix parametrize behaviour when list is empty.

## Implementation steps

### Step 1: Replace parametrized grade-B test

Replace:
```python
@pytest.mark.golden
@pytest.mark.skipif(not GOLDEN_DIR.exists(), reason="golden/ directory not present")
@pytest.mark.parametrize("page", _load_grade_b_pages(), ids=lambda p: p.source_path.name)
def test_no_critical_on_grade_b(page):
    ...
```

With:
```python
@pytest.mark.golden
@pytest.mark.skipif(not GOLDEN_DIR.exists(), reason="golden/ directory not present")
def test_no_critical_on_grade_b():
    """Grade-B golden pages must produce zero critical content-quality findings."""
    pages = _load_grade_b_pages()
    if not pages:
        pytest.skip("No grade-B golden pages in corpus — add grade: B files to unblock")
    for page in pages:
        findings = _run_deterministic_checks(
            page.content, page.source_path.stem,
            page_role=page.page_role,
            product_name=_PLACEHOLDER_PRODUCT,
            canonical_import=_PLACEHOLDER_IMPORT,
            golden_dir=GOLDEN_DIR,
        )
        critical = [
            f for f in findings
            if f.check in _CONTENT_QUALITY_CHECKS
            and f.severity == "critical"
        ]
        assert not critical, _fmt_failures(page, critical)
```

### Step 2: Add corpus composition smoke test

Add after `test_grade_a_pages_exist`:
```python
@pytest.mark.golden
@pytest.mark.skipif(not GOLDEN_DIR.exists(), reason="golden/ directory not present")
def test_grade_b_pages_exist_or_skip():
    """Documents whether grade-B pages are present; skips (not fails) if absent."""
    pages = _load_grade_b_pages()
    if not pages:
        pytest.skip(
            "No grade-B pages found. Add markdown files with 'grade: B' frontmatter "
            "to golden/ to enable grade-B regression assertions."
        )
    assert len(pages) >= 1  # Reached only when pages exist
```

### Step 3: Run and verify

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/golden/ -m golden -v
```

Expected: `test_no_critical_on_grade_b` shows as `SKIPPED` (not `PASSED [NOTSET]`).
No test collection warnings about empty parametrize lists.

## Failure modes

### Failure mode 1: Loop approach hides individual page identity

**Detection**: A failing page is not identified in the test name
**Resolution**: The `_fmt_failures()` output includes page filename — assertion
message is sufficient for diagnosis. If needed, add a `for` loop with
`pytest.fail(f"Page {page.source_path.name}: ..." )` calls per failing page.
**Gate**: `_fmt_failures` includes source_path.name

### Failure mode 2: pytest.skip not reached (GOLDEN_DIR missing)

**Detection**: Test is collected but skipif guard fires first
**Resolution**: `skipif not GOLDEN_DIR.exists()` fires before `pytest.skip()` —
correct behaviour, no action needed
**Gate**: `skipif` decorator has priority over function body

### Failure mode 3: [NOTSET] still appears

**Detection**: `pytest -v` output shows `[NOTSET]` in test IDs
**Resolution**: The parametrize decorator was not fully removed — check for
any remaining `@pytest.mark.parametrize` on grade-B test
**Gate**: `grep -n "parametrize.*grade_b\|grade_b.*parametrize" tests/golden/test_checks_regression.py`
returns no results

## Task-specific review checklist

1. [ ] `[NOTSET]` no longer appears in `pytest -v` output
2. [ ] Grade-B test shows `SKIPPED` with legible reason message
3. [ ] `test_grade_b_pages_exist_or_skip` collected and skips cleanly
4. [ ] When grade-B pages are added in future, loop test runs without code changes
5. [ ] No parametrize-related warnings in pytest output
6. [ ] Existing grade-A parametrized test unchanged
7. [ ] Docstrings updated for modified test functions
8. [ ] Spec file: no worker behavior change — no spec drift
9. [ ] Schema: not applicable (test file only)
10. [ ] Checked `docs/README.md` ownership map — no trigger events apply
11. [ ] No new `docs/guides/` file added

## Deliverables

1. `tests/golden/test_checks_regression.py` (grade-B test converted from parametrize to loop)
2. `reports/GR-01/evidence.md` (pytest -v output showing SKIPPED)

## Acceptance checks

1. [ ] `pytest tests/golden/ -m golden -v` shows no `[NOTSET]` test IDs
2. [ ] `test_no_critical_on_grade_b` shows `SKIPPED` when corpus has no grade-B pages
3. [ ] All existing grade-A tests still pass/xfail as before
4. [ ] No new test failures introduced

## Self-review

### Verification results
- [ ] Tests: X/X PASS (golden suite)
- [ ] Evidence captured: reports/GR-01/evidence.md
- [ ] Doc freshness: not applicable

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/golden/ -m golden -v 2>&1
```

**Expected results**:
- `test_no_critical_on_grade_b` → `SKIPPED`
- `test_grade_b_pages_exist_or_skip` → `SKIPPED`
- All smoke and grade-A tests unchanged

## Integration boundary proven

**Upstream**: `GoldenIndex.all_pages()` + `grade_letter` (TC-3876a)
**Downstream**: TC-3877/3878/3879 threshold fixes — grade-B suite unblocks once
grade-B corpus files are added
**Contract**: Empty grade-B list → `SKIPPED`, not false `PASSED`
