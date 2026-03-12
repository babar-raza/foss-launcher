# Claim Quality Healing Sprint

## Context

Self-review of CQ-01..CQ-08 identified 11 gaps preventing production readiness.
Claim extraction improved from 0% to 83% usable, but latent bugs (`_repair_json`
URL corruption), false negatives (backtick commands, third-party product claims),
missing tests (code fences, LLM path), and observability gaps remain.

This plan converts every gap into an executable taskcard.

## Gap Table

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|----------|----------|
| G1 | `_repair_json` `//` removal corrupts URLs in JSON strings | Blocker | HQ-01 |
| G2 | Emoji detection `ord(text[0]) > 0x2600` catches legitimate Unicode | High | HQ-01 |
| G3 | Backtick-wrapped commands bypass `_is_junk_claim` | High | HQ-01 |
| G4 | No product-relevance filter (Scikit-learn/Django claims pass) | High | HQ-02 |
| G5 | No test for code fence tracking in deterministic extractor | Medium | HQ-03 |
| G6 | LLM JSON repair path untested with real malformed JSON | Medium | HQ-03 |
| G7 | No logging of filtered claim counts (observability) | Medium | HQ-04 |
| G8 | `_SECTION_KIND_MAP` duplicates `_KIND_PATTERNS` mechanism | Low | HQ-04 |
| G9 | STOPWORDS imported inside `_is_junk_claim` per-call | Low | HQ-04 |
| G10 | `_score_doc_path` recreates local frozensets per-call | Low | HQ-04 |
| G11 | Only one pilot config tested (cells, not note) | Medium | HQ-03 |

---

## HQ-01: Fix Latent Bugs in `_is_junk_claim` and `_repair_json`

**Status**: Done
**Gap linkage**: G1, G2, G3
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**:
1. `_repair_json`: Change `//` comment removal from `r"//[^\n]*"` to `r"(?m)^\s*//[^\n]*"` (only line-start comments). This prevents corrupting URLs like `https://example.com` inside JSON string values.
2. Emoji detection: Replace `ord(text[0]) > 0x2600` with `unicodedata.category(text[0]) == 'So'` (Symbol, Other). This correctly identifies emoji without catching accented characters, CJK, or other legitimate Unicode.
3. Backtick-wrapped commands: Add a check for `` `pip install ...` `` and `` `npm install ...` `` patterns (backtick prefix) in `_is_junk_claim`.

**Allowed paths**:
- `src/launcher/workers/understand/extract.py`
- `tests/unit/workers/test_understand.py`

**Forbidden**: any other file/path

### Acceptance Checks

- CLI: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -x -v` -- all pass
- Tests:
  - `_repair_json('{"url": "https://example.com/path"}')` preserves the URL
  - `_repair_json("[\n// comment\n{\"a\": 1}]")` removes the comment
  - `_is_junk_claim("` `` `pip install aspose-cells-python` `` `")` returns True
  - `_is_junk_claim("Aspose.Cells for Python via .NET")` returns False (no false positive from Unicode fix)
  - Emoji: `_is_junk_claim("2\ufe0f\u20e3 Run the server")` returns True; `_is_junk_claim("Konig-class battleship")` returns False (umlaut)
- Config respected end-to-end: N/A (no config changes)
- No mock data in production paths: N/A
- Full suite: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ --ignore=tests/unit/test_pipeline_e2e.py -q` -- 0 failures

### Deliverables

- Modified `extract.py`: 3 surgical fixes (regex, unicodedata, backtick pattern)
- New/updated tests: 6+ tests covering URL preservation, emoji edge cases, backtick commands
- No schema or contract changes

### Hard Rules

- Keep `_is_junk_claim` signature unchanged
- Keep `_repair_json` signature unchanged
- No new dependencies (`unicodedata` is stdlib)
- Deterministic: all tests pass with PYTHONHASHSEED=0
- No network in tests

### Review Dimensions (5/5 means)

| Dimension | 5/5 Definition |
|-----------|----------------|
| Correctness | All 3 bugs verified fixed with regression tests |
| Robustness | URL corruption impossible; emoji false positives eliminated |
| Testability | Each fix has dedicated positive + negative test cases |
| Minimality | 3 line-level changes + tests only |

### Runbook

```bash
# 1. Read current _repair_json and _is_junk_claim
# 2. Apply 3 fixes:
#    a) _repair_json: r"//[^\n]*" -> r"(?m)^\s*//[^\n]*"
#    b) _is_junk_claim emoji: ord(text[0]) > 0x2600 -> unicodedata.category(text[0]) == 'So'
#    c) _is_junk_claim backtick: add re.match(r"^`(?:pip|npm|yarn|cargo|go)\s+", text)
# 3. Add import unicodedata at top of extract.py
# 4. Add 6+ tests to test_understand.py
# 5. Run:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -x -v
# 6. Full suite:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ --ignore=tests/unit/test_pipeline_e2e.py -q
```

---

## HQ-02: Product-Relevance Filtering for Claims

**Status**: Done
**Gap linkage**: G4
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**:
Add a `_is_off_topic(text: str, product: ProductIdentity) -> bool` function that detects claims describing third-party products rather than the target product. Claims that are off-topic get `visibility="internal"` (not deleted -- downstream workers can decide).

Logic:
1. Build a set of product keywords from `product.family`, `product.display_name`, `product.canonical_import` (e.g., `{"cells", "aspose", "excel", "spreadsheet", "workbook"}`).
2. Build a set of third-party indicators from the claim text (known library names: "scikit-learn", "sklearn", "django", "flask", "tensorflow", "numpy", "scipy", "matplotlib", "pandas").
3. If claim contains a third-party indicator AND does NOT contain any product keyword, mark as off-topic.
4. Apply in `_validate_and_normalize_claims` after the existing `_is_junk_claim` check.

The third-party indicator list should be configurable (module-level constant `_THIRD_PARTY_INDICATORS`), not hardcoded per-product.

**Allowed paths**:
- `src/launcher/workers/understand/extract.py`
- `tests/unit/workers/test_understand.py`

**Forbidden**: any other file/path

### Acceptance Checks

- CLI: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -x -v` -- all pass
- Tests:
  - `_is_off_topic("Scikit-learn is a machine learning library", cells_product)` returns True
  - `_is_off_topic("Using Scikit-learn with Aspose.Cells for reports", cells_product)` returns False (mentions product)
  - `_is_off_topic("The library supports XLSX format", cells_product)` returns False (no third-party indicator)
  - Claims marked off-topic get `visibility="internal"`, not deleted
- Config respected end-to-end: Uses `ProductIdentity` fields -- works for any product family
- No mock data in production paths: N/A
- Full suite: 0 failures

### Deliverables

- New function `_is_off_topic(text, product)` in `extract.py`
- Integration into `_validate_and_normalize_claims` -- off-topic claims get `visibility="internal"`
- 5+ tests: off-topic detection, mixed mentions, product-only claims, no-indicator claims
- No schema changes (uses existing `visibility` field)

### Hard Rules

- Do NOT delete off-topic claims -- mark `visibility="internal"` only
- Keep `_validate_and_normalize_claims` signature unchanged
- Product keywords derived from `ProductIdentity` fields (not hardcoded)
- Third-party indicators at module level (`_THIRD_PARTY_INDICATORS`)
- No new dependencies
- Deterministic with PYTHONHASHSEED=0

### Review Dimensions (5/5 means)

| Dimension | 5/5 Definition |
|-----------|----------------|
| Correctness | Zero Scikit-learn/Django/Flask-only claims in public visibility |
| Robustness | Mixed-mention claims (product + third-party) correctly kept public |
| Integration | Uses existing `visibility` field -- no downstream contract change |
| Maintainability | `_THIRD_PARTY_INDICATORS` is a single constant to extend |

### Runbook

```bash
# 1. Read _validate_and_normalize_claims in extract.py
# 2. Add _THIRD_PARTY_INDICATORS constant
# 3. Add _is_off_topic(text, product) function
# 4. Integrate after _is_junk_claim check in _validate_and_normalize_claims
# 5. Add 5+ tests
# 6. Run:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -x -v
# 7. Verify with real repo:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -c "
import sys; sys.path.insert(0, 'src')
# ... (run deterministic extraction + normalize, count public vs internal claims)
"
# 8. Full suite:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ --ignore=tests/unit/test_pipeline_e2e.py -q
```

---

## HQ-03: Missing Test Coverage (Code Fences, LLM Path, Second Pilot)

**Status**: Done
**Gap linkage**: G5, G6, G11
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**:
Add missing tests that the CQ sprint should have included:

1. **Code fence tracking** (G5): Test that content inside ` ```python ... ``` ` blocks is NOT extracted as claims. Test nested/mismatched fences.

2. **LLM JSON repair path** (G6): Test `_parse_claims_json` with the actual error pattern from the pilot ("Expecting ',' delimiter" caused by trailing comma at line 673). Test with JSON containing `//` URLs (verifies HQ-01 fix). Test with JS-style comments.

3. **Second pilot smoke test** (G11): Add an integration-level test that runs `_build_doc_contexts` + `_extract_claims_deterministic` on a synthetic repo structure mimicking aspose-note (different file layout, no Plugin/ dir, fewer docs). Verify claims are produced and none are junk.

**Allowed paths**:
- `tests/unit/workers/test_understand.py`
- `tests/integration/test_claim_extraction.py` (NEW)

**Forbidden**: any other file/path

### Acceptance Checks

- CLI: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py tests/integration/test_claim_extraction.py -x -v` -- all pass
- Tests:
  - Code fence test: 0 claims from fenced code blocks; claims before/after fences preserved
  - JSON repair test: trailing comma JSON parses successfully; URL-containing JSON preserved
  - Synthetic pilot test: >0 claims produced; 0 claims fail `_is_junk_claim`
- No mock data in production paths: Tests use synthetic markdown, not production content
- Full suite: 0 failures

### Deliverables

- 4+ new tests in `test_understand.py` (code fences, nested fences)
- 4+ new tests in `test_understand.py` (JSON repair with real error patterns)
- New `tests/integration/test_claim_extraction.py` with synthetic pilot test
- Total: 10+ new tests

### Hard Rules

- No network in tests
- Deterministic with PYTHONHASHSEED=0
- Synthetic test data only (no real repo content in tests)
- No modifications to production code

### Review Dimensions (5/5 means)

| Dimension | 5/5 Definition |
|-----------|----------------|
| Test Quality | Every new test has clear setup, action, assertion; covers happy + failure paths |
| Coverage | Code fence, JSON repair, and multi-config paths all exercised |
| Robustness | Edge cases: nested fences, mismatched fences, empty JSON, double-repair |

### Runbook

```bash
# 1. Read existing tests in test_understand.py for patterns
# 2. Add TestCodeFenceTracking class:
#    - test_code_inside_fences_skipped
#    - test_content_outside_fences_kept
#    - test_nested_fences
#    - test_mismatched_fence_stays_in_fence_mode
# 3. Add TestParseClaimsJsonRealErrors class:
#    - test_trailing_comma_at_line_673 (actual pilot error)
#    - test_json_with_url_preserved
#    - test_js_comments_removed
#    - test_double_repair_idempotent
# 4. Create tests/integration/test_claim_extraction.py:
#    - test_synthetic_note_repo_produces_claims
# 5. Run:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py tests/integration/test_claim_extraction.py -x -v
# 6. Full suite:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ --ignore=tests/unit/test_pipeline_e2e.py -q
```

---

## HQ-04: Observability + Code Hygiene

**Status**: Done
**Gap linkage**: G7, G8, G9, G10
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**:

1. **Filtered claim logging** (G7): Add `logger.info` after deterministic extraction and after `_validate_and_normalize_claims` reporting how many claims were filtered by `_is_junk_claim`. Add `logger.info` in `_build_doc_contexts` reporting budget allocation (README chars used, total chars, files included).

2. **Merge `_SECTION_KIND_MAP` into `_classify_kind_from_text`** (G8): Instead of two parallel mechanisms, extend `_classify_kind_from_text` to check exact heading matches (via `_SECTION_KIND_MAP`) first, then fall back to keyword matching (via `_KIND_PATTERNS`). Remove the duplicate override code in `_extract_claims_deterministic`.

3. **STOPWORDS import at module level** (G9): Move `from launcher.shared.jaccard import STOPWORDS` to the top of `_is_junk_claim` or to a module-level lazy cache, instead of importing on every call inside the function body.

4. **`_score_doc_path` local sets to module level** (G10): Move `_DOC_DIR_NAMES` and `_EXAMPLE_NAMES` frozensets from inside `_score_doc_path` to module-level constants.

**Allowed paths**:
- `src/launcher/workers/understand/extract.py`
- `tests/unit/workers/test_understand.py`

**Forbidden**: any other file/path

### Acceptance Checks

- CLI: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -x -v` -- all pass
- Tests:
  - Existing `TestDeterministicExtractorSectionKind` still passes (merged mechanism produces same results)
  - New test: `_classify_kind_from_text("Supported Formats")` returns `"format"` (exact match via merged map)
  - New test: `_classify_kind_from_text("Some format stuff")` returns `"format"` (keyword fallback)
- Config respected end-to-end: N/A
- No mock data in production paths: N/A
- Logging verified: run extraction script, confirm log lines for budget allocation and filter counts appear
- Full suite: 0 failures

### Deliverables

- Modified `_classify_kind_from_text` with exact-match-first logic
- Removed duplicate `_SECTION_KIND_MAP` override in `_extract_claims_deterministic`
- Module-level `_DOC_DIR_NAMES`, `_EXAMPLE_NAMES` constants
- Module-level or lazy STOPWORDS import
- 3 `logger.info` calls (budget, deterministic filter count, normalize filter count)
- 2+ new tests for merged kind classification
- No schema or contract changes

### Hard Rules

- `_classify_kind_from_text` signature unchanged
- Merged behavior must be backward-compatible: same results for all existing test cases
- No new dependencies
- Deterministic with PYTHONHASHSEED=0
- Log messages use structured format: `"claim_filter_stats total=%d kept=%d filtered=%d"`

### Review Dimensions (5/5 means)

| Dimension | 5/5 Definition |
|-----------|----------------|
| Observability | Budget allocation and filter counts visible in INFO logs |
| Maintainability | Single kind-classification mechanism instead of two |
| Performance | No per-call object creation (frozensets, imports) |
| Minimality | Pure refactor + logging; no behavioral change |

### Runbook

```bash
# 1. Read _classify_kind_from_text and _SECTION_KIND_MAP in extract.py
# 2. Merge: add _SECTION_KIND_MAP entries as exact-match first pass in _classify_kind_from_text
# 3. Remove override code in _extract_claims_deterministic (lines ~895-897)
# 4. Move _DOC_DIR_NAMES, _EXAMPLE_NAMES to module level
# 5. Move STOPWORDS import to module level or add lazy cache
# 6. Add 3 logger.info calls:
#    a) _build_doc_contexts: "doc_context_budget readme_chars=%d other_chars=%d files=%d"
#    b) _extract_claims_deterministic: "deterministic_claims total=%d"
#    c) _validate_and_normalize_claims: "claim_normalize_stats input=%d kept=%d filtered_junk=%d filtered_short=%d"
# 7. Add 2+ tests for merged classification
# 8. Run:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -x -v
# 9. Full suite:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ --ignore=tests/unit/test_pipeline_e2e.py -q
```
