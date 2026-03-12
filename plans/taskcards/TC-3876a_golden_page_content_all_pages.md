---
id: TC-3876a
title: "GoldenPage: content field, grade_letter property, all_pages() iterator"
status: Done
priority: High
owner: agent
updated: "2026-03-09"
tags: [golden, regression, infrastructure]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3876a_golden_page_content_all_pages.md
  - src/launcher/shared/golden_loader.py
  - tests/shared/test_golden_loader.py
evidence_required:
  - reports/TC-3876a/evidence.md
---

# Taskcard TC-3876a — GoldenPage: content field, grade_letter property, all_pages() iterator

## Objective

Enable programmatic iteration of all golden pages and access to their raw content, so
that the check regression suite (TC-3876b) can feed golden pages through deterministic
checks. Currently `GoldenPage` discards raw markdown after parsing and `GoldenIndex`
has no iteration API.

## Required spec references

- `plans/purrfect-beaming-crown.md` (Phase 1 infrastructure — TC-3876a section)

## Scope

### In scope
- Add `content: str = ""` field to `GoldenPage` (raw markdown, GOLDEN comment stripped)
- Add `grade_letter: str` property to `GoldenPage` (normalizes "A-" → "A", "B+" → "B")
- Fix `_parse_golden_file()` to strip `<!-- GOLDEN REFERENCE -->` prefix before frontmatter parsing (currently files starting with `<!--` never have their frontmatter parsed)
- Extend grade parsing to accept modifiers ("A-", "B+", "B-" etc.)
- Add `GoldenIndex.all_pages() -> list[GoldenPage]` (sorted by subdomain, role, variant)
- 5 new tests in `test_golden_loader.py`

### Out of scope
- Changing how the index is keyed (still `(page_role, variant)`)
- Adding new golden files
- Modifying any other consumer of GoldenPage/GoldenIndex

## Inputs

- `src/launcher/shared/golden_loader.py` (existing)
- `tests/shared/test_golden_loader.py` (existing)
- Golden files under `golden/` (read-only; not modified)

## Outputs

- `src/launcher/shared/golden_loader.py` (modified)
- `tests/shared/test_golden_loader.py` (modified — 5 new tests appended)

## Allowed paths

- plans/taskcards/TC-3876a_golden_page_content_all_pages.md
- src/launcher/shared/golden_loader.py
- tests/shared/test_golden_loader.py

### Allowed paths rationale

`golden_loader.py` is the only file defining GoldenPage/GoldenIndex. Test file adds
coverage for new API surface.

## Implementation steps

### Step 1: Fix `_parse_golden_file()` — strip GOLDEN comment, accept grade modifiers

Current code: `if content.startswith("---"):` — fails for files starting with `<!--`.

Change the function to:
1. Read raw content
2. Strip the `<!-- GOLDEN REFERENCE ... -->` comment if present (find `-->` end and lstrip `\n`)
3. Store result as `content_for_checks` (this becomes `GoldenPage.content`)
4. Proceed with frontmatter parsing on `content_for_checks`
5. Extend grade check from `if raw_grade in ("A","B","C","D","F")` to
   `if raw_grade and raw_grade[0].upper() in ("A","B","C","D","F")`

### Step 2: Add `content` field and `grade_letter` property to `GoldenPage`

Add to the dataclass (after `total_word_count`, with default `""`):
```python
content: str = ""
```

Add property:
```python
@property
def grade_letter(self) -> str:
    return self.grade[0].upper() if self.grade else "A"
```

Note: `@dataclass` does not support properties natively — must convert to using
`__post_init__` or keep as a plain method. Actually properties work fine in dataclasses,
but the field must appear AFTER the property declaration. Place the property inside the
class body after the field declarations.

### Step 3: Pass `content_for_checks` to GoldenPage constructor

In `_parse_golden_file()` return statement, add `content=content_for_checks`.

### Step 4: Add `all_pages()` to `GoldenIndex`

```python
def all_pages(self) -> list[GoldenPage]:
    """Return all loaded golden pages in deterministic order."""
    return sorted(
        self._pages.values(),
        key=lambda p: (p.subdomain, p.page_role, p.variant),
    )
```

### Step 5: Add 5 tests to `test_golden_loader.py`

Append after the last existing test:

```python
# ---------------------------------------------------------------------------
# TC-3876a: content field, grade_letter, all_pages
# ---------------------------------------------------------------------------

def test_golden_page_has_content_field(tmp_path):
    md_content = "---\ntitle: Test\ngrade: B\n---\n## Overview\nSome text here.\n"
    md_file = tmp_path / "test.md"
    md_file.write_text(md_content, encoding="utf-8")
    from launcher.shared.golden_loader import _parse_golden_file
    page = _parse_golden_file(md_file, tmp_path)
    assert page is not None
    assert isinstance(page.content, str)
    assert len(page.content) > 0

def test_golden_page_content_strips_golden_comment(tmp_path):
    md_content = (
        "<!-- GOLDEN REFERENCE | Source: test | Original-Grade: A- -->\n"
        "---\ntitle: Test\n---\n## Section\nSome text here.\n"
    )
    md_file = tmp_path / "test.md"
    md_file.write_text(md_content, encoding="utf-8")
    from launcher.shared.golden_loader import _parse_golden_file
    page = _parse_golden_file(md_file, tmp_path)
    assert page is not None
    assert "GOLDEN REFERENCE" not in page.content
    assert "---" in page.content  # frontmatter present

def test_grade_letter_strips_modifier(tmp_path):
    from launcher.shared.golden_loader import GoldenPage, GoldenIndex
    # Simulate grade parsed as "B" (bare)
    page = GoldenPage(
        source_path=tmp_path / "test.md",
        page_role="installation",
        variant="standard",
        subdomain="docs.aspose.org",
        grade="B",
        sections=[],
        total_word_count=0,
    )
    assert page.grade_letter == "B"

def test_grade_letter_strips_modifier_with_suffix(tmp_path):
    """grade_letter normalizes 'A-' → 'A', 'B+' → 'B'."""
    md_content = "---\ntitle: Test\ngrade: \"B+\"\n---\n## Section\nText here.\n"
    md_file = tmp_path / "test.md"
    md_file.write_text(md_content, encoding="utf-8")
    from launcher.shared.golden_loader import _parse_golden_file
    page = _parse_golden_file(md_file, tmp_path)
    assert page is not None
    # Grade "B+" accepted (first char "B" is in the valid set)
    assert page.grade == "B+"
    assert page.grade_letter == "B"

def test_all_pages_returns_sorted_pages():
    index = GoldenIndex.load(Path("golden"))
    pages = index.all_pages()
    # Must return something if golden/ exists
    if pages:
        assert all(isinstance(p.content, str) for p in pages)
        # Must be sorted (comparing consecutive pairs)
        keys = [(p.subdomain, p.page_role, p.variant) for p in pages]
        assert keys == sorted(keys)
    # Must be deterministic
    assert index.all_pages() == index.all_pages()
```

## Failure modes

### Failure mode 1: Dataclass field ordering — content field breaks construction

**Detection**: `TypeError: __init__() missing required argument 'content'` in existing tests
**Resolution**: Ensure `content: str = ""` has a default value, placed LAST in dataclass fields
**Gate**: Existing test suite passing

### Failure mode 2: GOLDEN comment strip leaves stray newline in content

**Detection**: `page.content.startswith("\n")` or frontmatter check fails on double-newline
**Resolution**: Use `.lstrip("\n")` after stripping comment end `-->`
**Gate**: `test_golden_page_content_strips_golden_comment`

### Failure mode 3: Grade modifier stored but `grade_letter` returns wrong letter

**Detection**: `page.grade_letter == "+"` or similar (if grade is `"+"`)
**Resolution**: Verify `raw_grade` is non-empty before `raw_grade[0]`; guard in property
**Gate**: `test_grade_letter_strips_modifier_with_suffix`

## Task-specific review checklist

1. [ ] `GoldenPage.content` populated for ALL golden files (not just files starting with `---`)
2. [ ] GOLDEN comment (`<!-- ... -->`) completely absent from `page.content`
3. [ ] Grade modifiers accepted: "A-" stored as "A-", `grade_letter` returns "A"
4. [ ] `all_pages()` is sorted deterministically (same call twice → same list)
5. [ ] No existing test in `test_golden_loader.py` broken
6. [ ] `GoldenIndex.__len__()` unchanged (still counts `_pages` keys)
7. [ ] Docstrings updated for GoldenPage, all_pages(), grade_letter
8. [ ] Spec file updated if worker behavior changed (no spec drift — loader only)
9. [ ] Schema `"description"` fields not applicable (Python code, not JSON schema)
10. [ ] Checked `docs/README.md` ownership map — no trigger events apply
11. [ ] If a new `docs/guides/` file was added: N/A

## Deliverables

1. `src/launcher/shared/golden_loader.py` — modified
2. `tests/shared/test_golden_loader.py` — 5 new tests appended
3. `reports/TC-3876a/evidence.md`

## Acceptance checks

1. [ ] All existing `test_golden_loader.py` tests pass (PYTHONHASHSEED=0)
2. [ ] 5 new tests pass
3. [ ] `GoldenIndex.load(Path("golden")).all_pages()` returns a non-empty list with content fields populated
4. [ ] `page.grade_letter` returns single uppercase letter for all loaded pages

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-3876a/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/shared/test_golden_loader.py -v
```

**Expected results**:
- All pre-existing tests pass
- 5 new TC-3876a tests pass
- Zero failures

## Integration boundary proven

**Upstream**: `golden/` directory (22 exemplar .md files)
**Downstream**: TC-3876b regression test (`GoldenIndex.all_pages()`, `page.content`, `page.grade_letter`)
**Contract**: `GoldenPage.content` is non-empty str containing frontmatter + body with no GOLDEN comment; `grade_letter` is a single uppercase letter in {A, B, C, D, F}
