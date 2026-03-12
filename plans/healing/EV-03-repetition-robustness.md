# EV-03 — Repetition Check Robustness: Performance Cap + Sentence Splitting

**Status:** Done (pre-existing)
**Gap linkage:** G-EV-05, G-EV-06
**Role:** Senior engineer. Drop-in, production-ready.

## Context

**G-EV-05 (Performance):** `check_repetition` compares all sentence pairs with O(n²) complexity. A page with 200 sentences produces 19,900 comparisons. Real pilot pages can have 150+ sentences. No cap or early termination exists.

**G-EV-06 (Correctness):** Sentence splitting uses `re.split(r"\.\s", text)` which incorrectly splits on:
- Abbreviations: `"e.g. something"` → `["e.g", "something"]`
- Decimals: `"3.14 GB of data"` → `["3", "14 GB of data"]`
- URLs: `"docs.aspose.com is the site"` → `["docs.aspose", "com is the site"]`
- Filenames: `"Open test.xlsx to begin"` → `["Open test", "xlsx to begin"]`

## Scope

### Fix
1. Add sentence cap: After splitting, if `len(sentences) > 60`, truncate to first 60 sentences. This caps worst case to 1,770 pairs (acceptable).
2. Improve sentence splitting to handle common non-sentence-ending periods:
   - Skip splits inside known abbreviations (`e.g.`, `i.e.`, `etc.`, `vs.`, `Dr.`, `Mr.`, `Ms.`)
   - Skip splits where period is preceded by a single uppercase letter (initials)
   - Skip splits where period is between digits (`3.14`)
   - Skip splits where period is between lowercase letters with no space (filenames, URLs)
3. Add tests for edge cases.

### Allowed paths
- `src/launcher/workers/evaluate/checks/repetition.py`
- `tests/unit/workers/test_evaluate.py`

### Forbidden
- Any other file/path

## Acceptance checks

- **CLI:** `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py::TestCheckRepetition -v` — all pass
- **Tests:**
  - `test_sentence_cap_applied`: Content with 100+ sentences doesn't hang or slow down; completes in <1s
  - `test_abbreviations_not_split`: Content with `"e.g. something"` keeps `"e.g. something"` as one sentence
  - `test_urls_not_split`: Content with `"docs.aspose.com"` doesn't produce spurious sentence breaks
  - `test_decimals_not_split`: Content with `"3.14 GB"` is one sentence
- **Config respected end-to-end:** N/A
- **No mock data in production paths:** N/A

## Deliverables

- Modified `repetition.py` with improved `_split_sentences` and sentence cap
- New tests for abbreviation, URL, decimal, and performance edge cases
- Existing tests still pass (no behavior regression on normal content)

## Hard rules

- Keep `check_repetition` public signature unchanged
- Sentence cap is a constant (`_MAX_SENTENCES = 60`) — not configurable
- No new deps (no NLTK, no spaCy — pure regex)
- Deterministic: same input always produces same output
- The cap truncates (first N sentences) rather than sampling — deterministic and simple

## Review dimensions — what 5/5 means

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Performance | O(n²) capped at 1,770 pairs max; no page can cause >1s execution |
| Correctness | Abbreviations, URLs, decimals, filenames don't produce false sentence breaks |
| Robustness | Extremely long pages degrade gracefully (truncated, not crashed or timed out) |
| Testability | Each edge case has a dedicated test with clear assertion |
| Minimality | Only modify `_split_sentences` and add cap — no other changes |

## Now (runbook)

```bash
# 1. Read current repetition.py
cat src/launcher/workers/evaluate/checks/repetition.py

# 2. Add _MAX_SENTENCES = 60 constant

# 3. Rewrite _split_sentences:
#    - Pre-protect abbreviations: replace "e.g. " → "e∎g∎ " (sentinel)
#    - Pre-protect decimals: replace "(\d)\.(\d)" → "$1∎$2"
#    - Split on ". " or ".\n"
#    - Restore sentinels: replace "∎" → "."
#    - Filter sentences < 5 words

# 4. Add cap after split:
#    sentences = sentences[:_MAX_SENTENCES]

# 5. Write tests

# 6. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py::TestCheckRepetition -v

# 7. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=short -q
```
