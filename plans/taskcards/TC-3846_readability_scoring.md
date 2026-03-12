---
id: TC-3846
title: "Readability Scoring — Flesch-Kincaid + Reading Time (SEO-20)"
status: Done
priority: High
owner: "agent"
updated: "2026-03-08"
tags: [seo, readability, evaluate, generate]
depends_on: [TC-3836, TC-3844]
allowed_paths:
  - plans/taskcards/TC-3846_readability_scoring.md
  - src/launcher/workers/evaluate/checks/readability.py
  - src/launcher/workers/evaluate/checks/__init__.py
  - src/launcher/workers/evaluate/worker.py
  - src/launcher/workers/generate/seo_metadata.py
  - tests/unit/workers/test_readability_check.py
evidence_required:
  - reports/TC-3846/evidence.md
---

# Taskcard TC-3846 — Readability Scoring (SEO-20)

## Objective

Create `workers/evaluate/checks/readability.py` with Flesch-Kincaid grade
level computation and wire it into the evaluate worker's deterministic check
pipeline. Also add `_calculate_reading_time()` to `seo_metadata.py`.

## Required spec references

- `specs/seo.md` (readability requirements: FK grade ≤ 12 for tech content)

## Scope

### In scope
- New file `workers/evaluate/checks/readability.py` with:
  - `check_readability(page_ir) -> list[Finding]`
  - `_flesch_kincaid_grade(text: str) -> float`
  - `_count_syllables(word: str) -> int`
  - `_extract_body(page_ir) -> str`
  - `_split_sentences(text: str) -> list[str]`
  - `_split_words(text: str) -> list[str]`
- Wire into `checks/__init__.py` and `evaluate/worker.py` `_run_deterministic_checks()`
- Add `_calculate_reading_time(word_count: int) -> int` to `seo_metadata.py`
  and call in `optimize_seo_metadata()` (AFTER TC-3836 SEO-18 Done)

### Out of scope
- Detailed per-sentence analysis — just overall FK grade
- Parallel LLM reviews — TC-3855 (Tier 5)

## Inputs

- `src/launcher/workers/evaluate/checks/__init__.py` (existing check registration)
- `src/launcher/workers/evaluate/worker.py` (existing `_run_deterministic_checks()`)
- `src/launcher/workers/generate/seo_metadata.py` (TC-3836 Done first)

## Outputs

- `readability.py` — new check file
- `checks/__init__.py` — updated to include readability check
- `evaluate/worker.py` — readability wired into deterministic checks
- `seo_metadata.py` — `reading_time` field added to frontmatter

## Allowed paths

- plans/taskcards/TC-3846_readability_scoring.md
- src/launcher/workers/evaluate/checks/readability.py
- src/launcher/workers/evaluate/checks/__init__.py
- src/launcher/workers/evaluate/worker.py
- src/launcher/workers/generate/seo_metadata.py
- tests/unit/workers/test_readability_check.py

### Allowed paths rationale

New readability.py; 3 existing files updated; new test file.

## Implementation steps

### Step 1: Create readability.py

```python
"""Readability scoring check — Flesch-Kincaid grade level computation."""
from __future__ import annotations

import re

_VOWELS = re.compile(r"[aeiouAEIOU]")
_SENTENCE_ENDINGS = re.compile(r"[.!?]+")
_WORD_SPLITTER = re.compile(r"\s+")
_CODE_FENCE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`]+`")


def _extract_body(page_ir: object) -> str:
    """Extract prose body text, stripping code blocks."""
    body = ""
    for section in (getattr(page_ir, "sections", []) or []):
        for block in (getattr(section, "blocks", []) or []):
            if getattr(block, "type", "") in ("paragraph", "text"):
                body += " " + (getattr(block, "content", "") or "")
    # Strip code fences and inline code
    body = _CODE_FENCE.sub(" ", body)
    body = _INLINE_CODE.sub(" ", body)
    return body.strip()


def _split_sentences(text: str) -> list[str]:
    parts = _SENTENCE_ENDINGS.split(text)
    return [p.strip() for p in parts if p.strip()]


def _split_words(text: str) -> list[str]:
    return [w for w in _WORD_SPLITTER.split(text) if w]


def _count_syllables(word: str) -> int:
    word = word.lower().rstrip("es").rstrip("ed").rstrip("e")
    count = len(_VOWELS.findall(word))
    return max(1, count)


def _flesch_kincaid_grade(text: str) -> float:
    """Compute Flesch-Kincaid Grade Level for *text*."""
    sentences = _split_sentences(text)
    words = _split_words(text)
    if not sentences or not words:
        return 0.0
    syllables = sum(_count_syllables(w) for w in words)
    asl = len(words) / len(sentences)  # avg sentence length
    asw = syllables / len(words)       # avg syllables per word
    return 0.39 * asl + 11.8 * asw - 15.59


def check_readability(page_ir: object) -> list[dict]:
    """Return findings for pages with FK grade above threshold."""
    findings = []
    body = _extract_body(page_ir)
    if not body or len(body.split()) < 100:
        return findings  # not enough content to assess

    fk_grade = _flesch_kincaid_grade(body)
    if fk_grade > 12.0:
        findings.append({
            "check": "readability",
            "message": (
                f"Flesch-Kincaid grade level is {fk_grade:.1f} "
                "(threshold: ≤12.0 for technical documentation). "
                "Consider shorter sentences and simpler vocabulary."
            ),
            "severity": "low",
            "location": "body",
        })
    return findings
```

### Step 2: Register in checks/__init__.py

Read `checks/__init__.py` and add `check_readability` to the list of
deterministic checks (wherever `check_structure`, `check_seo`, etc. are listed).

### Step 3: Wire into evaluate/worker.py _run_deterministic_checks()

Find `_run_deterministic_checks()` in `evaluate/worker.py` and add:
```python
from launcher.workers.evaluate.checks.readability import check_readability
# ... in the check loop:
findings.extend(check_readability(page_ir))
```

### Step 4: Add _calculate_reading_time() to seo_metadata.py

```python
def _calculate_reading_time(word_count: int, words_per_minute: int = 200) -> int:
    """Return estimated reading time in minutes (minimum 1)."""
    return max(1, round(word_count / words_per_minute))
```

Call in `optimize_seo_metadata()` after freshness dates injection (TC-3836):
```python
# Reading time
body_words = len((fm.get("description", "") + " " + content_body).split())
fm["reading_time"] = _calculate_reading_time(body_words)
```

### Step 5: Add tests

`tests/unit/workers/test_readability_check.py` — 17 test cases as per plan:
- FK grade calculation: known text → expected grade range
- FK grade 0.0 for empty text
- FK grade 0.0 for text with < 100 words → no finding
- FK grade > 12 → finding with severity "low"
- FK grade ≤ 12 → no finding
- Syllable count: "hello" → 2, "the" → 1, "education" → 3
- Code blocks excluded from body
- Reading time: 200 words → 1 min, 400 words → 2 min, 1 word → 1 min

## Failure modes

### Failure mode 1: page_ir has no 'sections' attribute

**Detection**: `AttributeError` when iterating sections
**Resolution**: Use `getattr(page_ir, "sections", []) or []` — safe fallback
**Gate**: Unit test with empty page_ir

### Failure mode 2: FK grade always returns high value (syllable overcounting)

**Detection**: Simple text like "The cat sat on the mat" returns grade > 8
**Resolution**: Test `_flesch_kincaid_grade("The cat sat on the mat.")` and verify
expected FK grade is ~2-3.
**Gate**: Unit test with known-grade text

### Failure mode 3: reading_time injection breaks existing seo_metadata tests

**Detection**: `TestFreshnessDates` tests fail after reading_time injection
**Resolution**: reading_time is an additional FM key — should not affect existing keys.
Check that `fm.get("reading_time")` returns int, not overwrite existing keys.
**Gate**: All 63 existing seo_metadata tests still pass

## Task-specific review checklist

1. [ ] `readability.py` created with all 6 functions
2. [ ] `check_readability()` returns [] for < 100 word pages
3. [ ] FK grade > 12 → `severity="low"` finding
4. [ ] Code block content excluded from body extraction
5. [ ] `_calculate_reading_time(200)` returns 1, `_calculate_reading_time(400)` returns 2
6. [ ] All 17 tests in `test_readability_check.py` pass

## Deliverables

1. `src/launcher/workers/evaluate/checks/readability.py` — new file with 6 functions
2. `src/launcher/workers/evaluate/checks/__init__.py` — updated exports
3. `src/launcher/workers/evaluate/worker.py` — readability wired into deterministic checks
4. `src/launcher/workers/generate/seo_metadata.py` — `reading_time` field
5. `tests/unit/workers/test_readability_check.py` — 17 test cases

## Acceptance checks

1. [ ] `pytest tests/unit/workers/test_readability_check.py -v` — 17/17 PASS
2. [ ] `check_readability(empty_page_ir) == []`
3. [ ] FK grade > 12 text → finding with check="readability", severity="low"
4. [ ] `pytest tests/ -x -q` — 0 failures

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: FK grade computed correctly; reading_time in frontmatter
- [ ] Evidence file: `reports/TC-3846/evidence.md`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_readability_check.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Expected results**:
- 17 readability tests pass
- Full suite: 0 failures

## Integration boundary proven

**Upstream**: PageIR from generate worker; seo_metadata.py (TC-3836 Done for freshness)
**Downstream**: Evaluate worker aggregates readability findings; Hugo frontmatter has reading_time
**Contract**: `check_readability(page_ir) -> list[dict]`; `reading_time` is int (minutes)
