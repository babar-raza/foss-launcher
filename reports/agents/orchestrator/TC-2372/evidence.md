# TC-2372 Evidence: Gate 19 Cross-Page Redundancy Check

## Implementation Summary

Created `src/launch/workers/w9_validator/gates/gate_19_redundancy.py` with
`run_gate_19(pages)` entry point. Wired into `worker.py` after Gate 18 reusing `pages_g16`.

## Logic

- Groups pages by `Path(page["path"]).parent` (section = parent directory)
- For sections with ≥2 pages: pairwise Jaccard similarity on significant word sets
- `_tokenize(text)`: `\b[a-z]{3,}\b` matches, minus ~32 stopwords
- Threshold: 0.6 (>60% shared words → G19-001 warn)
- Gate passes (warn-only)

## Test Fix During Implementation

Initial test used generated words like `alpha0`/`beta0` which include digits.
The tokenizer regex `\b[a-z]{3,}\b` does not match words with embedded digits
(no word boundary between `alpha` and `0` inside `alpha0`). Fixed tests to
use plain English words (authenticate, credential, database, query, etc.).

## Test Results

```
tests/unit/workers/test_gate_19_redundancy.py::test_high_overlap_same_section_warns PASSED
tests/unit/workers/test_gate_19_redundancy.py::test_low_overlap_passes PASSED
tests/unit/workers/test_gate_19_redundancy.py::test_different_sections_not_compared PASSED
tests/unit/workers/test_gate_19_redundancy.py::test_single_page_per_section_passes PASSED
```

4 new tests pass. Full suite: **4535 passed**, 9 skipped, 1 pre-existing NUL failure.

## Acceptance Criteria Verification

- [x] Two pages in same dir, >60% word overlap → G19-001 warn
- [x] Two pages in same dir, <60% overlap → no issue
- [x] Two pages in different dirs, >60% overlap → no issue
- [x] One page per dir → no issue
- [x] Gate always passes (warn-only)
- [x] 4 new tests pass
