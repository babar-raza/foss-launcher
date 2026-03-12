---
id: GR-04
title: "Guard _CONTENT_QUALITY_CHECKS against silent drift when new checks are added"
status: Open
priority: Medium
owner: agent
updated: "2026-03-09"
tags: [golden, regression, test-quality, drift-guard]
depends_on: []
allowed_paths:
  - plans/healing/GR-04-content-quality-checks-drift-guard.md
  - tests/golden/test_checks_regression.py
evidence_required:
  - reports/GR-04/evidence.md
---

# GR-04 — _CONTENT_QUALITY_CHECKS drift guard

## Objective

`_CONTENT_QUALITY_CHECKS` is a hardcoded frozenset in `test_checks_regression.py`.
When a new check is added to `_run_deterministic_checks()`, the regression suite
will silently ignore it unless the frozenset is manually updated. Add an
audit test that verifies the frozenset covers all checks actually returned by
the function, so new checks surface immediately.

## Gap source

TC-3876b self-review: the frozenset was defined by manually listing 11 checks.
If `_run_deterministic_checks()` gains a new check (e.g. `link_rot`, `citation`),
the regression suite will not cover it — no failure, no warning, silent gap.

## Required spec references

- `plans/purrfect-beaming-crown.md` (Phase 1 — TC-3876b; _CONTENT_QUALITY_CHECKS rationale)

## Scope

### In scope
- Add `test_content_quality_checks_covers_all_deterministic_checks` audit test
- The test runs `_run_deterministic_checks` on a minimal synthetic content string
  and collects all unique `f.check` names returned
- Asserts that every check name that is NOT in the explicit exclusion list IS
  in `_CONTENT_QUALITY_CHECKS`, and every check in `_CONTENT_QUALITY_CHECKS`
  IS returned by the function (no phantom entries)

### Out of scope
- Modifying `_run_deterministic_checks` itself
- Adding new checks

## Inputs

- `tests/golden/test_checks_regression.py`
- `_run_deterministic_checks` from `launcher.workers.evaluate.worker`

## Outputs

- `tests/golden/test_checks_regression.py` (new audit test added)
- `reports/GR-04/evidence.md`

## Allowed paths

- plans/healing/GR-04-content-quality-checks-drift-guard.md
- tests/golden/test_checks_regression.py

### Allowed paths rationale

New test added to existing regression suite. No src/ changes.

## Implementation steps

### Step 1: Define the explicit exclusion set in the test file

Add near `_CONTENT_QUALITY_CHECKS`:
```python
# Checks explicitly excluded from golden regression assertions.
# These are meta/infrastructure checks that golden files deliberately lack:
_EXCLUDED_CHECKS = frozenset({
    "seo",           # golden files lack seoTitle, robots, canonical, keywords
    "frontmatter",   # golden files lack slug, url (low severity — acceptable)
    "claim_leakage", # no claim IDs in golden by design (trivially passes)
    "slug_safety",   # not called by _run_deterministic_checks
})
```

### Step 2: Add audit test

Add after the smoke tests:
```python
@pytest.mark.golden
def test_content_quality_checks_covers_all_deterministic_checks():
    """_CONTENT_QUALITY_CHECKS must cover all checks returned by _run_deterministic_checks.

    Drift guard: if a new check is added to _run_deterministic_checks but not to
    _CONTENT_QUALITY_CHECKS (or _EXCLUDED_CHECKS), this test fails immediately,
    preventing silent coverage gaps.
    """
    # Minimal content that exercises all checks without triggering too many errors
    synthetic_content = (
        "---\ntitle: Test Page\n---\n\n"
        "## Overview\n\n"
        "This is a test page for drift detection purposes.\n\n"
        "## Usage\n\n"
        "```python\nimport aspose_family_foss\n```\n"
    )
    findings = _run_deterministic_checks(
        synthetic_content,
        "test-drift-guard",
        page_role="workflow_page",
        product_name=_PLACEHOLDER_PRODUCT,
        canonical_import=_PLACEHOLDER_IMPORT,
        golden_dir=None,  # Don't load golden for this audit
    )
    returned_checks = {f.check for f in findings}

    # Every returned check must be classified as either quality or excluded
    classified = _CONTENT_QUALITY_CHECKS | _EXCLUDED_CHECKS
    unclassified = returned_checks - classified
    assert not unclassified, (
        f"New checks returned by _run_deterministic_checks are not classified:\n"
        f"  Unclassified: {sorted(unclassified)}\n"
        f"  Add each to _CONTENT_QUALITY_CHECKS or _EXCLUDED_CHECKS with rationale."
    )

    # Every entry in _CONTENT_QUALITY_CHECKS must be returned by the function
    # (detects phantom entries — checks removed from _run_deterministic_checks)
    # Note: some checks may not fire on synthetic content — only warn, don't fail
    never_returned = _CONTENT_QUALITY_CHECKS - returned_checks
    if never_returned:
        import warnings
        warnings.warn(
            f"_CONTENT_QUALITY_CHECKS entries never returned by _run_deterministic_checks "
            f"on synthetic content: {sorted(never_returned)}. "
            f"May be content-specific — verify manually.",
            stacklevel=2,
        )
```

### Step 3: Run and verify

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/golden/test_checks_regression.py::test_content_quality_checks_covers_all_deterministic_checks -v
```

Expected: PASSED (no unclassified checks returned from synthetic content).

## Failure modes

### Failure mode 1: Synthetic content doesn't trigger any checks

**Detection**: `returned_checks` is empty → `unclassified` is empty → test passes vacuously
**Resolution**: Verify that `_run_deterministic_checks` returns findings for the
synthetic content. If not, use a more adversarial synthetic string (e.g. deliberately
trigger density by using very short content).
**Gate**: Add `assert returned_checks, "No findings returned — synthetic content too benign"`

### Failure mode 2: `_run_deterministic_checks` raises on `golden_dir=None`

**Detection**: `TypeError` or `AttributeError` when `golden_dir=None`
**Resolution**: `check_golden_spec_from_markdown` should no-op when `golden_dir=None`.
If it raises, this is a separate bug — report and use `golden_dir=GOLDEN_DIR`
as fallback (with `skipif not GOLDEN_DIR.exists()` guard).
**Gate**: `test_content_quality_checks_covers_all_deterministic_checks` collects without error

### Failure mode 3: New check added to _run_deterministic_checks breaks this test

**Detection**: `AssertionError: New checks returned ... are not classified: {'new_check'}`
**Resolution**: Intended behaviour — add `new_check` to `_CONTENT_QUALITY_CHECKS`
or `_EXCLUDED_CHECKS` with rationale comment. This is the drift guard working correctly.
**Gate**: Test failure itself is the detection mechanism

## Task-specific review checklist

1. [ ] `_EXCLUDED_CHECKS` frozenset defined alongside `_CONTENT_QUALITY_CHECKS`
2. [ ] `_EXCLUDED_CHECKS` rationale comments match what was in the module docstring
3. [ ] Audit test asserts `unclassified == set()` (fails on new unclassified checks)
4. [ ] Phantom entry detection uses `warnings.warn` (not assert) — content-specific checks may not fire
5. [ ] Test does NOT have `@pytest.mark.skipif` on golden dir (uses `golden_dir=None`)
6. [ ] `@pytest.mark.golden` applied
7. [ ] Docstrings updated (audit test has docstring explaining drift-guard purpose)
8. [ ] Spec file: no worker behavior change
9. [ ] Schema: not applicable
10. [ ] Checked `docs/README.md` — no trigger events apply
11. [ ] No new `docs/guides/` file added

## Deliverables

1. `tests/golden/test_checks_regression.py` (audit test + `_EXCLUDED_CHECKS` added)
2. `reports/GR-04/evidence.md`

## Acceptance checks

1. [ ] `test_content_quality_checks_covers_all_deterministic_checks` passes
2. [ ] `_EXCLUDED_CHECKS` frozenset with rationale comments present in test file
3. [ ] All existing golden tests unchanged
4. [ ] `grep "_EXCLUDED_CHECKS" tests/golden/test_checks_regression.py` returns ≥2 matches

## Self-review

### Verification results
- [ ] Audit test passes
- [ ] Evidence captured: reports/GR-04/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/golden/ -m golden -v 2>&1
```

**Expected results**:
- Audit test PASSED
- All prior golden tests unchanged
- No new failures

## Integration boundary proven

**Upstream**: `_run_deterministic_checks()` (worker.py — single source of truth for check names)
**Downstream**: TC-3877/3878/3879 — when thresholds are fixed, new checks will not be silently missed
**Contract**: `_CONTENT_QUALITY_CHECKS ∪ _EXCLUDED_CHECKS ⊇ {f.check for f in _run_deterministic_checks(...)}`
