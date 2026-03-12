# TC-3804 Healing Plan: Spec Leakage Claim Visibility Fix

## Context

TC-3804 synced the evaluator's `_INTERNAL_TERMS` (12 terms) into the claim
classifier's `_is_spec_fragment()`. Self-review found **1 production blocker**
and **4 gaps** that must be addressed before the fix is merge-ready.

**Critical finding:** The `any(term in text_lower ...)` substring check creates
false positives. "binary formatting options" is killed because "binary format"
is a substring of "binary formatting". This *removes legitimate public claims*
from the pipeline — the opposite of what we want.

## Gap Table

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|----------|----------|
| G-01 | Substring matching causes false positives ("binary formatting" killed) | BLOCKER | H-01 |
| G-02 | `_INTERNAL_CONTENT_TERMS` is a local var inside function body; re-allocated per call | LOW | H-01 |
| G-03 | Private-module regexes compiled inline per call | LOW | H-01 |
| G-04 | No boundary/false-positive tests in test suite | HIGH | H-02 |
| G-05 | `classify_claims.py` second filter path missing same 12 terms | MEDIUM | H-03 |
| G-06 | No cross-reference comment in `spec_leakage.py` pointing to classifier | LOW | H-04 |
| G-07 | L3 evaluator `check_spec_leakage()` has same substring matching issue | LOW | H-05 |

---

## Taskcard H-01: Word-Boundary Matching + Hoist Terms to Module Level

**Status:** Done
**Gap linkage:** G-01 (BLOCKER), G-02, G-03
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:**
1. Replace `any(term in text_lower for term in _INTERNAL_CONTENT_TERMS)` with
   word-boundary regex matching: `re.search(r'\b' + re.escape(term) + r'\b', text_lower)`
2. Move `_INTERNAL_CONTENT_TERMS` from local variable inside `_is_spec_fragment()`
   to a module-level tuple constant
3. Pre-compile `_PRIVATE_MODULE_RE` and `_PRIVATE_IMPL_RE` as module-level constants
   instead of inline `re.search()` calls

**Allowed paths:**
- `src/launcher/shared/extract_claims.py`

**Forbidden:** any other file/path

### Acceptance checks

- **CLI:** `classify_claim_visibility("Support for binary formatting options", "feature")` returns `"public"`
- **CLI:** `classify_claim_visibility("The library uses binary format for storage", "feature")` returns `"internal"`
- **CLI:** All 12 terms still classified as `internal` when used as exact phrases
- **Tests:** All existing tests in `test_claim_visibility_spec_leakage.py` still pass
- **Tests:** Full suite passes with `PYTHONHASHSEED=0`
- **Config respected end-to-end:** No config changes needed
- **No mock data in production paths:** N/A

### Deliverables

- Updated `src/launcher/shared/extract_claims.py`:
  - Module-level `_INTERNAL_CONTENT_TERMS` tuple (moved from function body)
  - Module-level `_PRIVATE_MODULE_RE` and `_PRIVATE_IMPL_RE` compiled patterns
  - Word-boundary loop replacing `any(term in text_lower ...)`

### Hard rules

- Keep `_is_spec_fragment()` signature unchanged (`text: str -> bool`)
- Keep `classify_claim_visibility()` signature unchanged
- No new dependencies
- Deterministic: same input always produces same output

### Review dimensions — what 5/5 means

| Dimension | 5/5 criterion |
|-----------|---------------|
| Thoroughness | All 12 terms use word-boundary matching; all three hoisting items done |
| Consistency | Pattern matches existing `re.search(r'\b...\b', ...)` style in same function |
| Production grading | Zero false positives on "binary formatting", "serialization formatters", etc. |
| Correctness | All 12 terms still caught; no regressions in existing test suite |
| Robustness | Word boundaries handle hyphenated compounds and plurals correctly |
| Performance | Module-level constants; no per-call allocation or compilation |
| Minimality | Only the 3 changes listed; no surrounding refactoring |

### Runbook

```bash
# 1. Edit extract_claims.py — move _INTERNAL_CONTENT_TERMS to module level as tuple
# 2. Replace substring check with word-boundary regex loop
# 3. Pre-compile _PRIVATE_MODULE_RE and _PRIVATE_IMPL_RE at module level
# 4. Verify false positive is fixed
.venv/Scripts/python.exe -c "
from launcher.shared.extract_claims import classify_claim_visibility
assert classify_claim_visibility('Support for binary formatting options', 'feature') == 'public'
assert classify_claim_visibility('The library uses binary format for storage', 'feature') == 'internal'
assert classify_claim_visibility('Supports converting XLSX to PDF format', 'feature') == 'public'
print('H-01 PASS')
"
# 5. Run existing spec leakage tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_claim_visibility_spec_leakage.py -v
# 6. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short
```

---

## Taskcard H-02: Add Boundary False-Positive Tests

**Status:** Done
**Gap linkage:** G-04 (HIGH)
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:** Add boundary/substring tests to `test_claim_visibility_spec_leakage.py`
that verify near-miss terms are NOT falsely classified as internal.

**Allowed paths:**
- `tests/unit/shared/test_claim_visibility_spec_leakage.py`

**Forbidden:** any other file/path

### Acceptance checks

- **Tests:** New boundary tests pass after H-01 is applied
- **Tests:** Tests *fail* against current code (proving they catch the bug)
- **Tests:** Full suite passes with `PYTHONHASHSEED=0`
- **No mock data in production paths:** N/A

### Deliverables

- Updated `tests/unit/shared/test_claim_visibility_spec_leakage.py`:
  - `TestBoundaryFalsePositives` class with at minimum these tests:
    - `test_binary_formatting_not_binary_format` — "binary formatting options" → public
    - `test_serialization_formatters_not_serialization_format` — "serialization formatters" → public
    - `test_implementation_details_plural` — "implementation details" → internal (still internal, plural of exact term)
    - `test_format_alone_not_matched` — "Export data in binary" → public (no "format" suffix)
    - `test_opcode_in_compound_word` — "opcodes" → internal (still internal, it's the same concept)
    - `test_case_insensitive_match` — "Binary Format" (mixed case) → internal

### Hard rules

- No changes to production code in this taskcard
- Tests must be deterministic (no randomness, no network)
- Keep existing test classes unchanged; add new class only

### Review dimensions — what 5/5 means

| Dimension | 5/5 criterion |
|-----------|---------------|
| Testability | Every boundary case has an explicit test; both true positive and false positive edges covered |
| Thoroughness | At least 6 boundary tests covering substring, plural, compound, case variations |
| Correctness | Tests accurately reflect expected behavior after H-01 |
| Minimality | Only new test class added; existing tests untouched |

### Runbook

```bash
# 1. Add TestBoundaryFalsePositives class to test file
# 2. Verify tests FAIL against current code (before H-01)
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_claim_visibility_spec_leakage.py::TestBoundaryFalsePositives -v
# Expected: 2+ failures (binary formatting, serialization formatters)
# 3. Apply H-01, then re-run
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_claim_visibility_spec_leakage.py -v
# Expected: all pass
```

---

## Taskcard H-03: Sync classify_claims.py Second Filter Path

**Status:** Done
**Gap linkage:** G-05 (MEDIUM)
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:** Add the 12 internal content terms to `_INTERNAL_PATTERNS` in
`classify_claims.py` so the second filtering path (`filter_claims()` called
from `extract.py:174`) also catches these terms. Use word-boundary regex
(not substring matching) from the start.

**Allowed paths:**
- `src/launcher/shared/classify_claims.py`
- `tests/unit/shared/test_classify_claims.py`

**Forbidden:** any other file/path

### Acceptance checks

- **CLI:** `classify_claim("The library uses implementation detail for processing")` returns `"internal_detail"`
- **CLI:** `classify_claim("Support for binary formatting options")` returns `"user_facing"` (word boundaries)
- **Tests:** New parametrized test class covering all 12 terms
- **Tests:** Existing `TestClassifyClaim` and `TestFilterClaims` tests unchanged and passing
- **Tests:** Full suite passes with `PYTHONHASHSEED=0`
- **No mock data in production paths:** N/A

### Deliverables

- Updated `src/launcher/shared/classify_claims.py`:
  - 12 new `re.compile()` patterns in `_INTERNAL_PATTERNS` using `\b` word boundaries
  - Private-module pattern: `re.compile(r"\._(?:internal|private)\b")`
- Updated `tests/unit/shared/test_classify_claims.py`:
  - `TestInternalContentTermSync` class with parametrized test over 12 terms
  - At least 1 false-positive boundary test

### Hard rules

- Keep `classify_claim()` and `filter_claims()` signatures unchanged
- Use `re.compile()` with `\b` boundaries (match existing pattern style in file)
- No new dependencies
- Deterministic

### Review dimensions — what 5/5 means

| Dimension | 5/5 criterion |
|-----------|---------------|
| Integration | Both filter paths (extract_claims + classify_claims) catch same terms |
| Consistency | Pattern style matches existing `_INTERNAL_PATTERNS` entries |
| Correctness | All 12 terms detected; zero false positives on boundary words |
| Testability | Parametrized test proves each term; boundary test proves no overreach |

### Runbook

```bash
# 1. Add 12+1 compiled patterns to _INTERNAL_PATTERNS in classify_claims.py
# 2. Add TestInternalContentTermSync to test_classify_claims.py
# 3. Verify
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_classify_claims.py -v
# 4. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short
```

---

## Taskcard H-04: Cross-Reference Comments Between Term Lists

**Status:** Done
**Gap linkage:** G-06 (LOW)
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:** Add cross-reference comments in `spec_leakage.py` and `classify_claims.py`
pointing back to `extract_claims.py` (and vice versa) so future maintainers know
all three lists must stay in sync.

**Allowed paths:**
- `src/launcher/workers/evaluate/checks/spec_leakage.py`
- `src/launcher/shared/extract_claims.py`
- `src/launcher/shared/classify_claims.py`

**Forbidden:** any other file/path

### Acceptance checks

- **Tests:** Full suite passes (comments only, no logic changes)
- **No mock data in production paths:** N/A

### Deliverables

- Comment block in `spec_leakage.py` above `_INTERNAL_TERMS`:
  ```
  # NOTE: These terms are also checked upstream in:
  #   - extract_claims.py: _INTERNAL_CONTENT_TERMS (L1 classifier)
  #   - classify_claims.py: _INTERNAL_PATTERNS (L1 filter)
  # Keep all three lists in sync when adding/removing terms.
  ```
- Comment block in `extract_claims.py` above `_INTERNAL_CONTENT_TERMS`:
  ```
  # Synced from spec_leakage.py _INTERNAL_TERMS (TC-3804).
  # Also mirrored in classify_claims.py _INTERNAL_PATTERNS.
  ```
- Comment block in `classify_claims.py` above the new internal content patterns (added by H-03):
  ```
  # Synced from spec_leakage.py _INTERNAL_TERMS (TC-3804).
  # Also in extract_claims.py _INTERNAL_CONTENT_TERMS.
  ```

### Hard rules

- Comments only — zero logic changes
- No signature changes

### Review dimensions — what 5/5 means

| Dimension | 5/5 criterion |
|-----------|---------------|
| Maintainability | Any engineer can find all three lists from any one of them |
| Minimality | Comments only, no code changes |

### Runbook

```bash
# 1. Add cross-reference comments to all 3 files
# 2. Verify no logic changes
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short
```

---

## Taskcard H-05: L3 Evaluator Word-Boundary Hardening

**Status:** Done
**Gap linkage:** G-07 (LOW)
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:** The evaluator's `check_spec_leakage()` in `spec_leakage.py` uses
`if term in lower_body` — the same substring matching that caused G-01. While
L3 false positives are less severe (they only add findings, don't remove content),
they produce noise in evaluation reports. Switch to word-boundary regex matching.

**Allowed paths:**
- `src/launcher/workers/evaluate/checks/spec_leakage.py`
- `tests/unit/workers/evaluate/test_spec_leakage.py` (if exists; create if needed)

**Forbidden:** any other file/path

### Acceptance checks

- **CLI:** `check_spec_leakage("Support for binary formatting options", "test-slug")` returns `[]` (no findings)
- **CLI:** `check_spec_leakage("The binary format is documented", "test-slug")` returns 1 finding
- **Tests:** Boundary test proving "binary formatting" does not trigger
- **Tests:** Full suite passes with `PYTHONHASHSEED=0`
- **No mock data in production paths:** N/A

### Deliverables

- Updated `src/launcher/workers/evaluate/checks/spec_leakage.py`:
  - Replace `if term in lower_body` with `re.search(r'\b' + re.escape(term) + r'\b', lower_body)`
- New or updated test file with boundary false-positive test

### Hard rules

- Keep `check_spec_leakage()` signature unchanged
- No new dependencies
- Deterministic

### Review dimensions — what 5/5 means

| Dimension | 5/5 criterion |
|-----------|---------------|
| Consistency | L1 and L3 now use identical matching strategy (word boundaries) |
| Robustness | No false positive findings on legitimate content |
| Minimality | Single-line logic change + test |

### Runbook

```bash
# 1. Edit spec_leakage.py — replace `in` with word-boundary regex
# 2. Add/update test
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/evaluate/ -v -k spec_leakage
# 3. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short
```

---

## Execution Order

| Order | Taskcard | Depends On | Priority |
|:-----:|----------|------------|----------|
| 1 | H-01 | — | BLOCKER |
| 2 | H-02 | H-01 | HIGH |
| 3 | H-03 | — | MEDIUM |
| 4 | H-04 | H-03 | LOW |
| 5 | H-05 | — | LOW |

H-01 and H-02 are blocking — they fix the false positive bug.
H-03 through H-05 are hardening — they close remaining gaps.
