---
id: TC-3876b
title: "Check regression suite: all 15 deterministic checks against golden pages"
status: Done
priority: High
owner: agent
updated: "2026-03-09"
tags: [golden, regression, evaluate, testing]
depends_on: [TC-3876a]
allowed_paths:
  - plans/taskcards/TC-3876b_check_regression_suite.md
  - tests/golden/__init__.py
  - tests/golden/test_checks_regression.py
evidence_required:
  - reports/TC-3876b/evidence.md
---

# Taskcard TC-3876b — Check regression suite

## Objective

Build the parametrized regression test suite that runs all 15 deterministic checks
against golden pages, revealing every false positive. This IS the evidence base for
threshold fixes in TC-3877/3878/3879. Initial failures are expected and documented.

## Required spec references

- `plans/purrfect-beaming-crown.md` (Phase 1 — TC-3876b section)

## Scope

### In scope
- New test file `tests/golden/test_checks_regression.py`
- New empty `tests/golden/__init__.py`
- Parametrized tests: grade-A pages (no high/critical from content checks), grade-B pages (no critical)
- `CONTENT_QUALITY_CHECKS` filter set (excludes seo, frontmatter, claim_leakage — meta checks)
- KNOWN FAILURES comments documenting initial false positives
- `@pytest.mark.golden` marker

### Out of scope
- Gate regression suite (TC-3876c)
- Threshold fixes (TC-3877/3878/3879)
- Modifying existing check implementations

## Inputs

- `GoldenIndex.all_pages()`, `GoldenPage.content`, `GoldenPage.grade_letter` (TC-3876a)
- `_run_deterministic_checks()` from `launcher.workers.evaluate.worker`
- `golden/` directory (22 exemplar files)

## Outputs

- `tests/golden/__init__.py` (new, empty)
- `tests/golden/test_checks_regression.py` (new, ~120 lines)
- `reports/TC-3876b/evidence.md` (test run output with KNOWN FAILURES documented)

## Allowed paths

- plans/taskcards/TC-3876b_check_regression_suite.md
- tests/golden/__init__.py
- tests/golden/test_checks_regression.py

### Allowed paths rationale

New test directory with regression suite. No src/ changes in this TC.

## Implementation steps

### Step 1: Create `tests/golden/__init__.py` (empty)

### Step 2: Create `tests/golden/test_checks_regression.py`

```python
"""
Golden corpus regression suite — TC-3876b.

Every grade-A golden page must produce zero high/critical findings
from content-quality checks. Every grade-B page must produce zero
critical findings.

Checks excluded from assertions (meta/infrastructure, not content quality):
  - seo          : golden files lack seoTitle, robots, canonical, keywords
  - frontmatter  : golden files lack slug, url (low severity only — fine)
  - claim_leakage: no claim IDs in golden by design (trivially passes)

Initial run will show KNOWN FAILURES before TC-3877/3878/3879 fix thresholds.
"""
import pytest
from pathlib import Path
from launcher.shared.golden_loader import GoldenIndex
from launcher.workers.evaluate.worker import _run_deterministic_checks

GOLDEN_DIR = Path(__file__).parent.parent.parent / "golden"

# Checks that measure CONTENT quality — golden pages must satisfy these.
# Excludes meta/infrastructure checks that golden files deliberately omit.
_CONTENT_QUALITY_CHECKS = frozenset({
    "density",
    "readability",
    "repetition",
    "structure",
    "artifacts",
    "product_names",
    "safety",
    "spec_leakage",
    "semantic_structure",
    "code",
    "reference_completeness",
})

# Generic placeholder product_name matching the __FAMILY__/__PLATFORM__ template
# variables used throughout golden files. Prevents product_name checks from
# firing on the literal template variable strings.
_PLACEHOLDER_PRODUCT = "Aspose.__FAMILY__ for __PLATFORM__"
_PLACEHOLDER_IMPORT = "aspose_family_foss"


def _load_grade_a_pages() -> list:
    index = GoldenIndex.load(GOLDEN_DIR)
    return [p for p in index.all_pages() if p.grade_letter == "A"]


def _load_grade_b_pages() -> list:
    index = GoldenIndex.load(GOLDEN_DIR)
    return [p for p in index.all_pages() if p.grade_letter == "B"]


def _fmt_failures(page, findings) -> str:
    lines = [
        f"Golden page '{page.source_path.name}' "
        f"(grade={page.grade}, role={page.page_role}, variant={page.variant}) failed:"
    ]
    for f in findings:
        lines.append(f"  [{f.severity.upper()}] {f.check}: {f.message} @ {f.location}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Grade-A: zero high/critical findings from content checks
# ---------------------------------------------------------------------------

@pytest.mark.golden
@pytest.mark.skipif(not GOLDEN_DIR.exists(), reason="golden/ directory not present")
@pytest.mark.parametrize("page", _load_grade_a_pages(), ids=lambda p: p.source_path.name)
def test_no_high_critical_on_grade_a(page):
    """Grade-A golden pages must produce zero high/critical content-quality findings."""
    findings = _run_deterministic_checks(
        page.content, page.source_path.stem,
        page_role=page.page_role,
        product_name=_PLACEHOLDER_PRODUCT,
        canonical_import=_PLACEHOLDER_IMPORT,
        golden_dir=GOLDEN_DIR,
    )
    blockers = [
        f for f in findings
        if f.check in _CONTENT_QUALITY_CHECKS
        and f.severity in ("critical", "high")
    ]
    assert not blockers, _fmt_failures(page, blockers)


# ---------------------------------------------------------------------------
# Grade-B: zero critical findings from content checks
# ---------------------------------------------------------------------------

@pytest.mark.golden
@pytest.mark.skipif(not GOLDEN_DIR.exists(), reason="golden/ directory not present")
@pytest.mark.parametrize("page", _load_grade_b_pages(), ids=lambda p: p.source_path.name)
def test_no_critical_on_grade_b(page):
    """Grade-B golden pages must produce zero critical content-quality findings."""
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


# ---------------------------------------------------------------------------
# Smoke test: regression suite can collect pages (not a content assertion)
# ---------------------------------------------------------------------------

@pytest.mark.golden
@pytest.mark.skipif(not GOLDEN_DIR.exists(), reason="golden/ directory not present")
def test_grade_a_pages_exist():
    """Sanity: golden corpus contains at least one grade-A page."""
    pages = _load_grade_a_pages()
    assert len(pages) >= 1, "Expected at least one grade-A golden page"


@pytest.mark.golden
@pytest.mark.skipif(not GOLDEN_DIR.exists(), reason="golden/ directory not present")
def test_all_pages_have_content():
    """All golden pages loaded by all_pages() have non-empty content field."""
    index = GoldenIndex.load(GOLDEN_DIR)
    for page in index.all_pages():
        assert page.content, f"Empty content on {page.source_path}"
```

### Step 3: Run and document KNOWN FAILURES

Run:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/golden/ -m golden -v 2>&1
```

For every failing test, add a comment in the test file under the relevant parametrize
list documenting:
- Which page
- Which check fired
- What the finding message is
- Which TC will fix it

## Failure modes

### Failure mode 1: _run_deterministic_checks import fails (nested function)

**Detection**: `ImportError: cannot import name '_run_deterministic_checks'`
**Resolution**: Function is module-level in worker.py (line 370) — import is valid
**Gate**: `test_all_pages_have_content` collection succeeds

### Failure mode 2: Parametrize with empty list (golden/ missing)

**Detection**: `pytest.PytestUnraisableExceptionWarning` or zero test collection
**Resolution**: The `skipif not GOLDEN_DIR.exists()` guard handles missing dir
**Gate**: `test_grade_a_pages_exist` skip (not error) when golden/ absent

### Failure mode 3: Unexpected failures beyond KNOWN FAILURES

**Detection**: Test failures not matching any documented KNOWN FAILURES
**Resolution**: Add to KNOWN FAILURES list and investigate root cause before fixing
**Gate**: All failures must be documented; no silent surprises

## Task-specific review checklist

1. [ ] `@pytest.mark.golden` applied to all regression tests
2. [ ] `_CONTENT_QUALITY_CHECKS` set documented with rationale for excluded checks
3. [ ] `skipif not GOLDEN_DIR.exists()` on all parametrized tests (CI portability)
4. [ ] Smoke tests collect even when no grade-A/B pages found
5. [ ] KNOWN FAILURES comments added for every failing test after initial run
6. [ ] `_fmt_failures()` output includes check name, severity, location (actionable)
7. [ ] Docstrings updated (module docstring documents the exclusion rationale)
8. [ ] Spec file: no worker behavior change — no spec drift
9. [ ] Schema: not applicable (test file only)
10. [ ] Checked `docs/README.md` ownership map — no trigger events apply
11. [ ] No new `docs/guides/` file added

## Deliverables

1. `tests/golden/__init__.py`
2. `tests/golden/test_checks_regression.py`
3. `reports/TC-3876b/evidence.md` (with KNOWN FAILURES listed)

## Acceptance checks

1. [ ] `pytest tests/golden/ -m golden` collects all tests without error
2. [ ] Smoke tests pass (grade-A pages exist, all pages have content)
3. [ ] Every parametrized failure is documented in KNOWN FAILURES list
4. [ ] No unexpected failures beyond documented ones

## Self-review

### Verification results
- [ ] Tests collected: X tests
- [ ] Smoke tests pass
- [ ] KNOWN FAILURES documented

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/golden/ -m golden -v
```

**Expected results**:
- All smoke tests pass
- Parametrized test failures match KNOWN FAILURES list exactly

## Integration boundary proven

**Upstream**: TC-3876a (`GoldenPage.content`, `GoldenPage.grade_letter`, `GoldenIndex.all_pages()`)
**Downstream**: TC-3877/3878/3879 (threshold fixes driven by this suite's failures)
**Contract**: Failures in this suite are the authoritative list of miscalibrated thresholds
