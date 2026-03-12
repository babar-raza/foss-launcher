---
id: TC-3845
title: "Anchor Text Optimization (SEO-19)"
status: Done
priority: High
owner: "agent"
updated: "2026-03-08"
tags: [seo, linker, anchor-text]
depends_on: [TC-3837]
allowed_paths:
  - plans/taskcards/TC-3845_anchor_text_optimization.md
  - src/launcher/shared/linker.py
  - tests/test_linker.py
evidence_required:
  - reports/TC-3845/evidence.md
---

# Taskcard TC-3845 — Anchor Text Optimization (SEO-19)

## Objective

Add `_GENERIC_ANCHORS`, `_NON_DESCRIPTIVE` pattern sets and enhanced
`_validate_anchor()` + `_check_anchor_diversity()` to `linker.py`
(AFTER TC-3837's keyword overlap changes) to reject generic, non-descriptive
anchor text and ensure variety across outbound links.

## Required spec references

- `specs/seo.md` (anchor text quality requirements)

## Scope

### In scope
- `_GENERIC_ANCHORS: frozenset[str]` — exact-match generic anchors ("click here", "read more", "learn more", "here", "this", "link")
- `_NON_DESCRIPTIVE_RE` — compiled regex for 1-2 word anchors that are not descriptive
- Enhanced `_validate_anchor(text: str) -> bool` that rejects generic and non-descriptive anchors
- `_check_anchor_diversity(anchors: list[str]) -> bool` — returns True if ≥50% of anchors are unique
- Wire `_validate_anchor()` into the anchor text generation pipeline

### Out of scope
- LLM-based anchor text generation changes — caller already uses LLM
- Contextual link injection — already done in TC-3837 (inject_contextual_links)
- Retroactive fixing of existing pages — evaluate check is detection only

## Inputs

- `src/launcher/shared/linker.py` (TC-3837 must be Done first)

## Outputs

- `linker.py` with `_GENERIC_ANCHORS`, `_validate_anchor()`, `_check_anchor_diversity()`
- Anchor text generation pipeline rejects generic anchors

## Allowed paths

- plans/taskcards/TC-3845_anchor_text_optimization.md
- src/launcher/shared/linker.py
- tests/test_linker.py

### Allowed paths rationale

Only linker.py extended; test file extended with new class.

## Implementation steps

### Step 1: Add constants to linker.py

```python
_GENERIC_ANCHORS: frozenset[str] = frozenset({
    "click here", "read more", "learn more", "here", "this", "link",
    "more", "info", "details", "page", "article", "post",
})

import re as _re
_NON_DESCRIPTIVE_RE = _re.compile(r"^\w+(\s+\w+)?$")  # 1-2 word, no context
```

### Step 2: Add _validate_anchor() function

```python
def _validate_anchor(text: str) -> bool:
    """Return True if *text* is acceptable as anchor text.

    Rejects:
    - Generic anchors from _GENERIC_ANCHORS (case-insensitive)
    - Very short (≤3 chars) anchors
    - Anchors that are just a number or single word
    """
    if not text or len(text.strip()) <= 3:
        return False
    lower = text.strip().lower()
    if lower in _GENERIC_ANCHORS:
        return False
    return True
```

### Step 3: Add _check_anchor_diversity() function

```python
def _check_anchor_diversity(anchors: list[str]) -> bool:
    """Return True if ≥50% of anchors are unique (no repetition problem)."""
    if not anchors:
        return True
    unique = len(set(a.lower().strip() for a in anchors))
    return unique / len(anchors) >= 0.5
```

### Step 4: Wire _validate_anchor() into anchor generation

In the existing anchor text generation/validation path (look for `_validate_anchor_text`
or the anchor generation helper), add a call to `_validate_anchor()` to filter results.
If LLM returns a generic anchor, fall back to the page title.

### Step 5: Add tests

`tests/test_linker.py` — new class `TestAnchorTextOptimization`:
```python
class TestAnchorTextOptimization:
    def test_generic_anchor_rejected(self):
        assert not _validate_anchor("click here")
        assert not _validate_anchor("read more")
        assert not _validate_anchor("here")

    def test_descriptive_anchor_accepted(self):
        assert _validate_anchor("Convert Excel to PDF using Python")
        assert _validate_anchor("Working with Cells API")

    def test_too_short_rejected(self):
        assert not _validate_anchor("hi")
        assert not _validate_anchor("")

    def test_diversity_all_unique(self):
        assert _check_anchor_diversity(["anchor one", "anchor two", "anchor three"])

    def test_diversity_too_repetitive(self):
        assert not _check_anchor_diversity(["click here", "click here", "click here"])

    def test_diversity_empty(self):
        assert _check_anchor_diversity([])
```

## Failure modes

### Failure mode 1: _validate_anchor rejects too many anchors (false positives)

**Detection**: Too many fallbacks to page title; links use generic titles
**Resolution**: Test with real page data; adjust _GENERIC_ANCHORS if needed
**Gate**: False positive guard tests

### Failure mode 2: _NON_DESCRIPTIVE_RE causes performance issue in loops

**Detection**: Slow link scoring when many anchors
**Resolution**: `_NON_DESCRIPTIVE_RE` is pre-compiled at module level; O(1) per call
**Gate**: No O(N²) loops — pattern match is O(len(text))

### Failure mode 3: Case sensitivity causes missed generic anchors

**Detection**: "Click Here" passes validation
**Resolution**: `text.strip().lower()` before lookup in `_GENERIC_ANCHORS`
**Gate**: Unit test with mixed-case inputs

## Task-specific review checklist

1. [ ] `_GENERIC_ANCHORS` frozenset defined at module level
2. [ ] `_validate_anchor("click here")` returns False
3. [ ] `_validate_anchor("Convert Excel to PDF using Python")` returns True
4. [ ] `_check_anchor_diversity(["a", "a", "a"])` returns False
5. [ ] `_check_anchor_diversity(["a", "b", "c"])` returns True
6. [ ] All existing linker tests still pass (120 tests from TC-3837)

## Deliverables

1. `src/launcher/shared/linker.py` — `_GENERIC_ANCHORS`, `_validate_anchor()`, `_check_anchor_diversity()`
2. `tests/test_linker.py` — `TestAnchorTextOptimization` class with 6+ tests

## Acceptance checks

1. [ ] `pytest tests/test_linker.py -v -k "AnchorText"` — all PASS
2. [ ] `_validate_anchor("click here") == False`
3. [ ] `pytest tests/ -x -q` — 0 failures (≥120 linker tests)

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: generic anchors rejected; descriptive anchors accepted
- [ ] Evidence file: `reports/TC-3845/evidence.md`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_linker.py -v -k "AnchorText"
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Expected results**:
- TestAnchorTextOptimization tests pass
- Full suite: 0 failures

## Integration boundary proven

**Upstream**: TC-3837's keyword overlap scoring and inject_contextual_links()
**Downstream**: Anchor text filtering improves SEO link quality; evaluate check (future) detects remaining generic anchors
**Contract**: `_validate_anchor(text: str) -> bool`; `_check_anchor_diversity(anchors: list[str]) -> bool`
