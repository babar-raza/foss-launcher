# Readability Check Correctness — Gap Index & Taskcards

## Context

Self-review of `sparkling-discovering-walrus.md` (SEO Phase 2, TC-SEO-20) found three
correctness gaps in `src/launcher/workers/evaluate/checks/readability.py`:

1. **Severity thresholds wrong** — the spec defines FK>16→medium, FK>20→high; the
   implementation uses FK>12→low, FK>20→medium. Pages with FK grade 12-16 produce
   false-positive findings. Pages with FK>20 are under-reported (medium vs. high).

2. **Long sentence flagging absent** — the spec requires a separate low-severity finding
   when >40% of sentences exceed 30 words. Not implemented.

3. **`_split_words` returns non-alphabetic tokens** — the function splits on whitespace,
   so numbers, punctuation-only tokens, and mixed strings are counted as "words". The
   spec requires alphabetic-only extraction (`[a-zA-Z]+`), which is also critical for
   correct syllable counting (the `_count_syllables` function already strips non-alpha
   chars internally, but the word count and sentence-length calculations are skewed
   by non-word tokens).

These are independent fixes but should land together to avoid a partial-state where
thresholds are correct but counts are wrong.

---

## Gap Table

| Gap ID | Description                                              | Taskcard | Priority |
|--------|----------------------------------------------------------|----------|----------|
| GAP-03 | Readability severity thresholds wrong (FK>12, FK>20)     | RD-01    | CRITICAL |
| GAP-06 | Long sentence flagging (>40% sentences >30 words) absent | RD-02    | HIGH     |
| GAP-07 | `_split_words` includes non-alphabetic tokens            | RD-02    | MEDIUM   |

---

## RD-01 — Fix Readability Severity Thresholds

**Status:** Not Started
**Gap linkage:** GAP-03

### Role
Senior engineer. Drop-in, production-ready. No stubs. No TODOs.

### Scope

**Fix:**
In `src/launcher/workers/evaluate/checks/readability.py`, the `_readability_findings_from_grade`
function uses wrong thresholds. Replace the function body:

```python
# BEFORE (wrong):
if fk_grade > 20.0:
    severity = "medium"   # should be "high"
if fk_grade > 12.0:
    severity = "low"      # wrong threshold — spec says >16

# AFTER (correct per TC-SEO-20 spec):
def _readability_findings_from_grade(fk_grade: float, word_count: int) -> list[dict]:
    """Return raw finding dicts for a given FK grade.

    Thresholds (TC-SEO-20 spec):
      FK > 20  → severity "high"   (severely complex)
      FK > 16  → severity "medium" (complex)
      FK < 6   → severity "low"    (too simple, only if >=100 words)
    """
    if fk_grade > 20.0:
        return [{
            "check": "readability",
            "message": (
                f"Prose is severely complex (Flesch-Kincaid grade {fk_grade:.1f}, "
                "threshold: \u226420.0). Simplify sentences and vocabulary."
            ),
            "severity": "high",
            "location": "body",
        }]
    if fk_grade > 16.0:
        return [{
            "check": "readability",
            "message": (
                f"Prose may be too complex (Flesch-Kincaid grade {fk_grade:.1f}, "
                "threshold: \u226416.0). Consider shorter sentences and simpler vocabulary."
            ),
            "severity": "medium",
            "location": "body",
        }]
    if fk_grade < 6.0 and word_count >= 100:
        return [{
            "check": "readability",
            "message": (
                f"Prose may be too simple for a technical audience "
                f"(Flesch-Kincaid grade {fk_grade:.1f}, threshold: \u22656.0)."
            ),
            "severity": "low",
            "location": "body",
        }]
    return []
```

Update the docstring of both `check_readability` and `check_readability_from_markdown`
to reflect the corrected thresholds.

**Allowed paths:**
- `src/launcher/workers/evaluate/checks/readability.py`
- `tests/unit/workers/test_readability_check.py` (update existing tests)

**Forbidden:** any other file or path.

### Acceptance checks

**Tests:**
- `test_fk_21_is_high_severity` — FK=21 → finding severity "high"
- `test_fk_17_is_medium_severity` — FK=17 → finding severity "medium"
- `test_fk_13_no_finding` — FK=13 → empty list (was incorrectly "low" before fix)
- `test_fk_11_no_finding` — FK=11 → empty list
- `test_fk_5_is_low_with_100_words` — FK=5, 100 words → "low"
- `test_fk_5_no_finding_under_100_words` — FK=5, 80 words → empty
- `test_fk_16_boundary_no_finding` — FK=16.0 exactly → empty (boundary is >16)
- `test_fk_16_1_is_medium` — FK=16.1 → "medium"
- `test_fk_20_boundary_no_finding` — FK=20.0 exactly → medium, not high (boundary is >20)
- `test_fk_20_1_is_high` — FK=20.1 → "high"

All existing `test_readability_check.py` tests that passed must still pass (update any that
were asserting the old wrong thresholds).

**CLI:**
```bash
# After fix: a page with FK≈18 (complex tech prose) should emit medium finding
python -m launcher.cli.main run --config configs/pilots/cells-python.yaml --dry-run 2>&1 | grep readability
```

**No mock data in production paths:** thresholds must be constants in the function, not injected.

### Deliverables
- Full replacement of `_readability_findings_from_grade` in `readability.py`
- Updated docstrings on both `check_readability` variants
- Updated + expanded test suite in `test_readability_check.py`

### Hard rules
- Boundary conditions tested at exact values (16.0, 16.1, 20.0, 20.1)
- Both `check_readability` (PageIR path) and `check_readability_from_markdown` (markdown path) use `_readability_findings_from_grade`, so both are fixed by one change
- No new dependencies

### Review dimensions (what 5/5 means here)
| Dimension | 5/5 |
|-----------|-----|
| Correctness | FK>20=high, FK>16=medium, FK<6=low — matches spec exactly |
| Testability | 10 tests covering all bands + exact boundaries |
| Minimality | Single function body changed; no other code touched |

### Now (runbook)
```bash
# 1. Edit _readability_findings_from_grade in readability.py (change >12→>16, "medium"→"high")
# 2. Update docstrings on check_readability and check_readability_from_markdown
# 3. Update tests: fix any tests asserting old thresholds; add 10 boundary tests
# 4. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_readability_check.py -v
# 5. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x -q
```

---

## RD-02 — Add Long Sentence Flagging + Fix `_split_words`

**Status:** Not Started
**Gap linkage:** GAP-06, GAP-07

### Role
Senior engineer. Drop-in, production-ready. No stubs. No TODOs.

### Scope

**Fix A — `_split_words` alphabetic-only (GAP-07):**

```python
# BEFORE:
_WORD_SPLITTER = re.compile(r"\s+")

def _split_words(text: str) -> list[str]:
    return [w for w in _WORD_SPLITTER.split(text.strip()) if w]

# AFTER:
_ALPHA_WORD = re.compile(r"[a-zA-Z]+")

def _split_words(text: str) -> list[str]:
    """Extract alphabetic-only words (no numbers, punctuation, mixed tokens).

    This matches the spec requirement (TC-SEO-20) and ensures:
    - Word counts exclude numeric tokens (version numbers, etc.)
    - Syllable counting receives clean inputs
    - Non-Latin content (URLs, identifiers) is excluded as documented
    """
    return _ALPHA_WORD.findall(text)
```

Remove the old `_WORD_SPLITTER` module-level pattern (or keep it only if used elsewhere in the file — check first).

**Fix B — Long sentence flagging (GAP-06):**

Add a new helper and integrate it into both check variants:

```python
def _long_sentence_finding(sentences: list[str], location: str = "body") -> list[dict]:
    """Return a low-severity finding if >40% of sentences exceed 30 words.

    Spec: TC-SEO-20 — 'Also flag: >40% sentences exceed 30 words → low'
    Only applied when there are ≥3 sentences (avoids false positives on short pages).
    """
    if len(sentences) < 3:
        return []
    long_count = sum(
        1 for s in sentences
        if len(_ALPHA_WORD.findall(s)) > 30
    )
    ratio = long_count / len(sentences)
    if ratio > 0.40:
        return [{
            "check": "readability",
            "message": (
                f"{long_count}/{len(sentences)} sentences exceed 30 words "
                f"({ratio:.0%}). Break long sentences for readability."
            ),
            "severity": "low",
            "location": location,
        }]
    return []
```

Wire into `check_readability` (PageIR path):
```python
def check_readability(page_ir: object) -> list[dict]:
    body = _extract_body(page_ir)
    if not body:
        return []
    words = _split_words(body)
    if len(words) < 100:
        return []
    sentences = _split_sentences(body)
    fk_grade = _flesch_kincaid_grade(body)
    findings = _readability_findings_from_grade(fk_grade, len(words))
    findings.extend(_long_sentence_finding(sentences))
    return findings
```

Wire into `check_readability_from_markdown` analogously.

Note: `_flesch_kincaid_grade` calls `_split_sentences` and `_split_words` internally.
After fixing `_split_words`, verify `_flesch_kincaid_grade` still calls it correctly
(it calls `_split_words(text)` and `_split_sentences(text)` — no changes needed there,
but the word count will change slightly because numbers are now excluded, which is correct).

**Allowed paths:**
- `src/launcher/workers/evaluate/checks/readability.py`
- `tests/unit/workers/test_readability_check.py`

**Forbidden:** any other file or path.

### Acceptance checks

**Tests — `_split_words` fix:**
- `test_split_words_excludes_numbers` — `_split_words("API 3.14 version")` → `["API", "version"]`
- `test_split_words_excludes_punctuation` — `_split_words("foo, bar.")` → `["foo", "bar"]`
- `test_split_words_alphabetic_only` — `_split_words("hello world")` → `["hello", "world"]`
- `test_split_words_empty` — `_split_words("")` → `[]`
- `test_split_words_only_numbers` — `_split_words("123 456")` → `[]`

**Tests — long sentence flagging:**
- `test_long_sentence_triggers_at_41_pct` — 3 sentences, 2 with >30 words (67%) → low finding
- `test_long_sentence_no_finding_at_40_pct` — 5 sentences, 2 long (40%) → no finding (boundary is >40%)
- `test_long_sentence_no_finding_at_41_pct_boundary` — 5 sentences, 3 long (60%) → low finding
- `test_long_sentence_skips_under_3_sentences` — 2 sentences (even if both long) → no finding
- `test_long_sentence_combined_with_fk_finding` — both FK>16 AND long sentences → two findings returned
- `test_long_sentence_not_triggered_short_page` — <100 words → skip (pre-check exits early)

**Config respected end-to-end:** long sentence check uses `_ALPHA_WORD.findall(sentence)` for word count — consistent with the fixed `_split_words`.

### Deliverables
- Full replacement of `readability.py` with:
  - `_ALPHA_WORD` replacing `_WORD_SPLITTER`
  - Updated `_split_words`
  - New `_long_sentence_finding` helper
  - Both `check_readability` variants wired to call `_long_sentence_finding`
- Updated test suite: 5 `_split_words` tests + 6 long sentence tests

### Hard rules
- `_long_sentence_finding` uses `_ALPHA_WORD.findall(s)` for consistent word counting
- The minimum 3-sentence guard prevents false positives on stub/thin pages
- Both `check_readability` and `check_readability_from_markdown` must include long-sentence findings
- `PYTHONHASHSEED=0` in all test runs
- No new dependencies

### Review dimensions (what 5/5 means here)
| Dimension | 5/5 |
|-----------|-----|
| Correctness | `_split_words` returns alphabetic tokens only; long sentence % triggers at correct boundary |
| Thoroughness | Both check variants updated; boundary tested at 40% and 41% |
| Robustness | Empty input, <3 sentences, <100 words all handled without findings |
| Testability | 11 focused tests covering all new paths |

### Now (runbook)
```bash
# 1. Replace _WORD_SPLITTER with _ALPHA_WORD (compile r"[a-zA-Z]+")
# 2. Rewrite _split_words to use _ALPHA_WORD.findall(text)
# 3. Add _long_sentence_finding helper (use _ALPHA_WORD.findall per sentence)
# 4. Wire _long_sentence_finding into check_readability and check_readability_from_markdown
# 5. Update tests (add 11 new tests, fix any broken existing tests)
# 6. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_readability_check.py -v
# 7. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x -q
```
