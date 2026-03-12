---
id: GR-09
title: "Add missing grade_letter edge case tests: empty string and single-case isolation"
status: Open
priority: Low
owner: agent
updated: "2026-03-09"
tags: [golden, golden-loader, test-quality]
depends_on: []
allowed_paths:
  - plans/healing/GR-09-grade-letter-edge-cases.md
  - tests/shared/test_golden_loader.py
evidence_required:
  - reports/GR-09/evidence.md
---

# GR-09 — grade_letter edge case tests

## Objective

Two test quality gaps in `TestTC3876aContentAndAllPages`:

1. `grade_letter` with `grade = ""` (empty string) is not tested. The implementation
   uses `self.grade[0]` which will raise `IndexError` on empty string. The fallback
   `if self.grade` handles this — but it is untested.

2. `test_grade_letter_strips_modifier` loops two cases (B+ and A-) in a single
   test. If B+ fails but A- passes, the test stops at B+, masking the A- case.
   Each case should be a separate test for clean failure isolation.

## Gap source

TC-3876b self-review (SR-09, SR-10): edge case coverage and test isolation.

## Required spec references

- `src/launcher/shared/golden_loader.py` (grade_letter property)

## Scope

### In scope
- Add `test_grade_letter_empty_string_defaults_to_a` test
- Split `test_grade_letter_strips_modifier` into two tests:
  `test_grade_letter_strips_plus_modifier` and `test_grade_letter_strips_minus_modifier`
- Keep the original combined test if splitting would break TC-3876a acceptance
  check references (add new tests instead of replacing)

### Out of scope
- Modifying the `grade_letter` property implementation
- Other test files

## Inputs

- `tests/shared/test_golden_loader.py` (TestTC3876aContentAndAllPages class)
- `src/launcher/shared/golden_loader.py` (grade_letter property implementation)

## Outputs

- `tests/shared/test_golden_loader.py` (new tests added)
- `reports/GR-09/evidence.md`

## Allowed paths

- plans/healing/GR-09-grade-letter-edge-cases.md
- tests/shared/test_golden_loader.py

### Allowed paths rationale

Test-only additions. No src/ changes.

## Implementation steps

### Step 1: Read current grade_letter implementation

Locate `grade_letter` property in `golden_loader.py`:
```python
@property
def grade_letter(self) -> str:
    return self.grade[0].upper() if self.grade else "A"
```

The `if self.grade` guard returns "A" for empty string. This is correct but untested.

### Step 2: Read current test

In `TestTC3876aContentAndAllPages`, find `test_grade_letter_strips_modifier`:
```python
def test_grade_letter_strips_modifier(self, tmp_path):
    """grade_letter normalizes 'B+' → 'B' and 'A-' → 'A'."""
    md_b_plus = "---\ntitle: Test\ngrade: \"B+\"\n---\n## Section\nText here.\n"
    md_a_minus = "---\ntitle: Test\ngrade: \"A-\"\n---\n## Section\nText here.\n"

    from launcher.shared.golden_loader import _parse_golden_file
    for content, expected_grade, expected_letter in [
        (md_b_plus, "B+", "B"),
        (md_a_minus, "A-", "A"),
    ]:
        ...
```

### Step 3: Add empty string edge case test

Add to `TestTC3876aContentAndAllPages`:
```python
def test_grade_letter_empty_string_returns_a(self, tmp_path):
    """grade_letter returns 'A' when grade is empty string (safe fallback)."""
    from launcher.shared.golden_loader import GoldenPage
    page = GoldenPage(
        source_path=tmp_path / "test.md",
        page_role="workflow_page",
        variant="standard",
        subdomain="docs.aspose.org",
        grade="",  # Empty string — should not raise IndexError
        sections=[],
        total_word_count=0,
    )
    # Must not raise IndexError — grade_letter has 'if self.grade' guard
    assert page.grade_letter == "A", (
        f"Empty grade must fall back to 'A', got '{page.grade_letter}'"
    )
```

### Step 4: Add split tests for modifier stripping

Add to `TestTC3876aContentAndAllPages`:
```python
def test_grade_letter_strips_plus_modifier(self, tmp_path):
    """grade_letter normalizes 'B+' → 'B'."""
    md = "---\ntitle: Test\ngrade: \"B+\"\n---\n## Section\nText here.\n"
    f = tmp_path / "test.md"
    f.write_text(md, encoding="utf-8")
    from launcher.shared.golden_loader import _parse_golden_file
    page = _parse_golden_file(f, tmp_path)
    assert page is not None
    assert page.grade == "B+", f"Expected grade 'B+', got '{page.grade}'"
    assert page.grade_letter == "B", f"Expected letter 'B', got '{page.grade_letter}'"


def test_grade_letter_strips_minus_modifier(self, tmp_path):
    """grade_letter normalizes 'A-' → 'A'."""
    md = "---\ntitle: Test\ngrade: \"A-\"\n---\n## Section\nText here.\n"
    f = tmp_path / "test.md"
    f.write_text(md, encoding="utf-8")
    from launcher.shared.golden_loader import _parse_golden_file
    page = _parse_golden_file(f, tmp_path)
    assert page is not None
    assert page.grade == "A-", f"Expected grade 'A-', got '{page.grade}'"
    assert page.grade_letter == "A", f"Expected letter 'A', got '{page.grade_letter}'"
```

Note: Keep the original `test_grade_letter_strips_modifier` (do not delete it —
it exists in evidence for TC-3876a). The new tests are ADDITIONAL.

### Step 5: Run and verify

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/shared/test_golden_loader.py -v -k "grade_letter"
```

Expected: all grade_letter tests pass, including the new ones.

## Failure modes

### Failure mode 1: Empty string grade raises IndexError

**Detection**: `test_grade_letter_empty_string_returns_a` raises `IndexError`
**Resolution**: The `if self.grade` guard in `grade_letter` must handle `""`.
`bool("") == False` so `return "A"` is the fallback — should not raise.
If it does raise, the property has a bug → escalate (src/ change required,
create separate TC, do NOT modify here).
**Gate**: Test passes without IndexError

### Failure mode 2: _parse_golden_file returns None for grade modifier files

**Detection**: `assert page is not None` fails in split tests
**Resolution**: The test files have valid frontmatter and sections. If None,
check that `_parse_golden_file` handles quoted grade values (`grade: "B+"`).
Verify with `grep "raw_grade\|grade" golden_loader.py`.
**Gate**: Existing `test_grade_letter_strips_modifier` passes → split tests must too

### Failure mode 3: GoldenPage constructor changes (new required field)

**Detection**: `TypeError: GoldenPage() missing required argument`
**Resolution**: Update the `GoldenPage(...)` constructor call in the edge case test
to include the new field.
**Gate**: `test_grade_letter_empty_string_returns_a` collection succeeds

## Task-specific review checklist

1. [ ] `test_grade_letter_empty_string_returns_a` added and passes
2. [ ] `test_grade_letter_strips_plus_modifier` added (separate from minus)
3. [ ] `test_grade_letter_strips_minus_modifier` added (separate from plus)
4. [ ] Original `test_grade_letter_strips_modifier` NOT deleted (TC-3876a evidence)
5. [ ] All new tests in `TestTC3876aContentAndAllPages` class
6. [ ] Each new test has its own descriptive docstring
7. [ ] Spec file: not applicable (test only)
8. [ ] Schema: not applicable
9. [ ] Checked `docs/README.md` — no trigger events apply
10. [ ] No new `docs/guides/` file added

## Deliverables

1. `tests/shared/test_golden_loader.py` (3 new tests added)
2. `reports/GR-09/evidence.md`

## Acceptance checks

1. [ ] `pytest tests/shared/test_golden_loader.py -v -k "grade_letter"` shows ≥5 tests
2. [ ] All grade_letter tests pass
3. [ ] `test_grade_letter_empty_string_returns_a` in output
4. [ ] `test_grade_letter_strips_plus_modifier` and `test_grade_letter_strips_minus_modifier` in output

## Self-review

### Verification results
- [ ] All grade_letter tests pass
- [ ] Evidence captured: reports/GR-09/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/shared/test_golden_loader.py -v -k "grade_letter" 2>&1
```

**Expected results**:
- `test_grade_letter_returns_single_letter` PASSED (existing)
- `test_grade_letter_strips_modifier` PASSED (existing)
- `test_grade_letter_empty_string_returns_a` PASSED (new)
- `test_grade_letter_strips_plus_modifier` PASSED (new)
- `test_grade_letter_strips_minus_modifier` PASSED (new)

## Integration boundary proven

**Upstream**: `GoldenPage.grade_letter` property (TC-3876a)
**Downstream**: `test_checks_regression.py` — uses `grade_letter` for corpus filtering
**Contract**: `grade_letter` never raises; always returns single uppercase letter or "A"
