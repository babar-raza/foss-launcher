# ST — SEO Test Gaps + Governance

**Source**: Self-review of TC-3837 (SEO-16), TC-3836 (SEO-18), TC-3845 (SEO-19),
TC-3846 (SEO-20), and AG-002 compliance review.

Gaps range from missing test functions (SEO-16/18/20) to a confirmed signature mismatch
between plan spec and implementation (SEO-19 `_check_anchor_diversity`), to an unrecorded
AG-002 allowed_paths violation requiring governance remediation.

All ST taskcards are test-only changes unless stated otherwise.

**Codebase**: `v2` branch

---

## Gap → Taskcard Map

| Gap ID  | Description                                                                 | Taskcard | Priority |
|---------|-----------------------------------------------------------------------------|----------|----------|
| G-ST-01 | SEO-16: 5 of 12 contextual link tests absent                                | ST-01    | Medium   |
| G-ST-02 | SEO-18: 3 of 7 freshness date tests absent                                  | ST-02    | Low      |
| G-ST-03 | SEO-19: `_check_anchor_diversity` signature mismatch vs plan + missing tests | ST-03   | Medium   |
| G-ST-04 | SEO-20: FK threshold + table + long-sentence + abbreviation tests absent     | ST-04    | Medium   |
| G-GV-01 | AG-002: `evaluate/worker.py` modified under TC-3853's scope (wrong allowed_paths) | GV-01 | Low   |

---

## ST-01 — SEO-16: Missing Contextual Link Tests

**Status**: Done
**Evidence**: 5/5 new tests pass (TestContextualLinks); 2634 total suite green.
**Gap linkage**: G-ST-01
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: Add 5 missing test functions to `TestContextualLinks` class in `tests/test_linker.py`.
Current implementation has 6 of 12 specified tests. Missing:
- `test_contextual_link_no_duplicate` — same target cannot be linked twice in one page
- `test_contextual_link_preserves_existing_markdown_link` — text already inside `[...](...)` is not double-linked
- `test_contextual_link_regex_metachar_title` — page title with `()`, `.`, `+` in it does not crash regex
- `test_contextual_link_exception_safety` — malformed page_index entry does not crash `inject_contextual_links()`
- `test_contextual_link_deterministic` — same input → same output with `PYTHONHASHSEED=0`

**Allowed paths**:
- `tests/test_linker.py`

**Forbidden**: Any other file or path. Do not modify `linker.py` or any `src/` file.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_linker.py::TestContextualLinks -v` — all PASS
- **UI/Web/API**: N/A
- **Tests**: All 5 missing functions listed in Scope above
- **Config respected end-to-end**: `max_inline=2` cap verified by existing `test_contextual_link_max_cap`; new tests exercise distinct scenarios
- **No mock data in production paths**: `inject_contextual_links()` called directly; production function unchanged

### Deliverables

- `tests/test_linker.py` — full file replacement with 5 new `TestContextualLinks` test functions. All 47+ existing tests preserved.
- No stubs, no TODOs; each test is self-contained with its own fixture data

### Hard rules

- `test_contextual_link_deterministic`: run `inject_contextual_links()` twice with same input; assert outputs are identical
- `test_contextual_link_regex_metachar_title`: use a page title like `"Aspose.Cells (for Python)"` — must not raise `re.error`
- `test_contextual_link_exception_safety`: inject a `None` URL or malformed entry; call must return original PageIR without exception
- No new dependencies; `re` already imported in linker
- PYTHONHASHSEED=0 required for determinism test

### Review dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| D1 Specification Alignment | All 5 missing spec test cases implemented with correct names |
| D4 Determinism | `test_contextual_link_deterministic` passes with both PYTHONHASHSEED=0 and =1 |
| D6 Production Robustness | Exception safety test exercises the `try/except` path in `inject_contextual_links` |
| D7 Test Coverage | 5 new functions bringing TestContextualLinks to 11/12 specified test count |

### Now (runbook)

```bash
# 1. Read current TestContextualLinks class
grep -n "class TestContextualLinks\|def test_" tests/test_linker.py | grep -A 50 "TestContextualLinks"

# 2. Find inject_contextual_links signature
grep -n "def inject_contextual_links" src/launcher/shared/linker.py

# 3. Check if exception safety try/except exists in linker
grep -n "try:\|except\|Exception" src/launcher/shared/linker.py | grep -A 5 "inject"

# 4. Write 5 test functions; use existing fixture pattern

# 5. Run
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_linker.py::TestContextualLinks -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q
```

---

## ST-02 — SEO-18: Missing Freshness Date Tests

**Status**: Done
**Evidence**: 7/7 TestFreshnessDates tests pass; 2603 total suite green.
**Files changed**: `tests/unit/workers/test_seo_metadata.py` (+2 tests: `test_schema_org_mirrors`, `test_unusual_preexisting_date_preserved`; `test_empty_date_replaced` was already present)
**Gap linkage**: G-ST-02
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: Add 3 missing test functions to `TestFreshnessDates` class in
`tests/unit/workers/test_seo_metadata.py`. Current: 4 of 7 specified tests. Missing:
- `test_date_empty_string_treated_as_missing` — `fm["date"] = ""` → replaced with `now` (not preserved)
- `test_schema_org_mirrors` — `fm["datePublished"] == fm["date"]` and `fm["dateModified"] == fm["lastmod"]`
- `test_unusual_preexisting_date_preserved` — `fm["date"] = "March 2025"` (non-ISO) → preserved as-is, no crash

**Allowed paths**:
- `tests/unit/workers/test_seo_metadata.py`

**Forbidden**: Any other file or path. Do not modify `seo_metadata.py` or any `src/` file.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_seo_metadata.py::TestFreshnessDates -v` — all PASS
- **UI/Web/API**: N/A
- **Tests**: All 3 missing functions listed in Scope above
- **No mock data in production paths**: `_inject_freshness_dates()` called directly with dict fixture; production function unchanged

### Deliverables

- `tests/unit/workers/test_seo_metadata.py` — full file replacement with 3 new `TestFreshnessDates` test functions. All existing tests preserved.
- No stubs, no TODOs

### Hard rules

- `test_date_empty_string_treated_as_missing`: input `{"date": ""}` → after call, `fm["date"]` is a valid ISO timestamp (not `""`)
- `test_schema_org_mirrors`: call function, then assert `result["datePublished"] == result["date"]` and `result["dateModified"] == result["lastmod"]`
- `test_unusual_preexisting_date_preserved`: input `{"date": "March 2025"}` → `fm["date"]` still `"March 2025"` (not overwritten); no exception raised
- Use `unittest.mock.patch` on `datetime` to freeze time for deterministic timestamp assertions (same pattern as existing tests in file)
- No new dependencies

### Review dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| D1 Specification Alignment | All 3 missing spec test names match plan exactly |
| D6 Production Robustness | Empty string edge case and non-ISO date edge case both covered |
| D7 Test Coverage | 3 functions bringing TestFreshnessDates to 7/7 specified coverage |
| D4 Determinism | `datetime` mocked for deterministic ISO timestamp assertions |

### Now (runbook)

```bash
# 1. Read TestFreshnessDates class in test file
grep -n "class TestFreshnessDates\|def test_" tests/unit/workers/test_seo_metadata.py | grep -A 30 "TestFreshnessDates"

# 2. Read _inject_freshness_dates to understand empty-string branch
grep -n "def _inject_freshness_dates\|not fm\[.date.\]\|empty\|\"\"" src/launcher/workers/generate/seo_metadata.py | head -15

# 3. Check datetime mock pattern in existing test
grep -n "patch.*datetime\|mock.*datetime\|freeze" tests/unit/workers/test_seo_metadata.py | head -5

# 4. Write 3 test functions using existing datetime mock pattern

# 5. Run
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_seo_metadata.py::TestFreshnessDates -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q
```

---

## ST-03 — SEO-19: Anchor Diversity Signature Mismatch + Missing Tests

**Status**: Done
**Evidence**: 5/5 new tests pass (TestAnchorTextOptimization); 2634 total suite green.
**Gap linkage**: G-ST-03
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: The plan specifies `_check_anchor_diversity(anchors: list[str], fallbacks: list[str]) -> list[str]`
(returns corrected list). The implementation has `_check_anchor_diversity(anchors: list[str]) -> bool`
(returns a boolean). This is a signature mismatch against spec.

Part A — Assess impact:
- Read the current implementation and all call sites
- If the boolean version is already wired correctly and diversity replacement happens at the call site, document that the implementation is functionally equivalent (different API shape)
- If diversity replacement is NOT happening (just checking without replacing), implement the full replacement

Part B — Add missing tests regardless of Part A outcome:
- `test_rejects_click_here` — `_validate_anchor("click here", fallback)` returns fallback
- `test_rejects_generic_case_insensitive` — `"CLICK HERE"` also rejected
- `test_rejects_generic_with_whitespace` — `" learn more "` also rejected
- `test_diversity_rejects_duplicates` — near-identical second anchor replaced with fallback
- `test_diversity_allows_distinct` — different anchors both kept

**Allowed paths**:
- `src/launcher/shared/linker.py` (only if signature fix is needed — Part A determines)
- `tests/test_linker.py`

**Forbidden**: Any other file or path.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_linker.py::TestAnchorTextOptimization -v` — all PASS
- **UI/Web/API**: N/A
- **Tests**: All 5 missing functions listed in Scope above
- **Config respected end-to-end**: `_validate_anchor()` rejections propagate through `generate_anchor_texts()`
- **No mock data in production paths**: `_validate_anchor()` called directly in tests; production linker.py unchanged if signature already functionally correct

### Deliverables

- `tests/test_linker.py` — full file replacement with 5 new `TestAnchorTextOptimization` functions. All existing tests preserved.
- If Part A requires `linker.py` change: `src/launcher/shared/linker.py` — targeted fix to `_check_anchor_diversity` signature + all call sites updated. No other changes.
- If Part A confirms functional equivalence: only test file changes; document the divergence in a code comment.

### Hard rules

- If signature is changed: ALL call sites of `_check_anchor_diversity` must be updated; no broken callers
- `.lower().strip()` used for all generic anchor comparisons — case + whitespace insensitive
- `_GENERIC_ANCHORS` frozenset membership check (O(1)); no iteration
- No new dependencies

### Review dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| D1 Specification Alignment | Either spec signature implemented OR functional equivalence documented |
| D2 Contract Compliance | All `_check_anchor_diversity` call sites updated if signature changes |
| D6 Production Robustness | Case-insensitive and whitespace-trimmed anchor matching verified by tests |
| D7 Test Coverage | 5 functions bringing TestAnchorTextOptimization to ~9/10 specified |

### Now (runbook)

```bash
# 1. Read current _check_anchor_diversity implementation
grep -n "def _check_anchor_diversity\|_check_anchor" src/launcher/shared/linker.py | head -10
# Read the function body (a few lines around it)

# 2. Find all call sites
grep -n "_check_anchor_diversity" src/launcher/shared/linker.py

# 3. Determine: is diversity replacement happening? Does the call site apply fallbacks?
# Read the call site context

# 4. If only a bool returned and no replacement: implement full replacement spec
# If functionally equivalent: add comment + proceed to tests only

# 5. Read TestAnchorTextOptimization in test file
grep -n "class TestAnchorTextOptimization\|def test_" tests/test_linker.py | grep -A 30 "TestAnchor"

# 6. Write 5 missing test functions

# 7. Run
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_linker.py::TestAnchorTextOptimization -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q
```

---

## ST-04 — SEO-20: Missing Readability Threshold and Edge Case Tests

**Status**: Done
**Evidence**: 6/6 new tests pass (TestReadabilityThresholdsAndEdgeCases); 2634 total suite green.
**Gap linkage**: G-ST-04
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: Add 6 missing test functions to `tests/unit/workers/test_readability_check.py`.
Current implementation has ~22 tests but is missing these plan-specified cases:
- `test_too_simple` — text with FK grade < 6 → low severity finding
- `test_too_complex` — text with FK grade 16–20 → medium severity finding
- `test_severely_complex` — text with FK grade > 20 → high severity finding
- `test_ignores_tables` — markdown tables stripped before scoring; no skewed word count
- `test_long_sentence_flagging` — >40% sentences exceed 30 words → low severity finding
- `test_abbreviations_not_split` — "e.g." and "i.e." not treated as sentence boundaries

**Allowed paths**:
- `tests/unit/workers/test_readability_check.py`

**Forbidden**: Any other file or path. Do not modify `readability.py` or any `src/` file.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_readability_check.py -v` — all PASS
- **UI/Web/API**: N/A
- **Tests**: All 6 missing functions listed in Scope above
- **No mock data in production paths**: `check_readability_from_markdown()` called with real markdown strings; no mocking of the function itself

### Deliverables

- `tests/unit/workers/test_readability_check.py` — full file replacement with 6 new test functions. All ~22 existing tests preserved.
- No stubs, no TODOs; each test uses synthetic markdown calibrated to trigger the threshold under test

### Hard rules

- `test_too_simple`: craft a text where FK < 6 (short sentences, common words: "The cat sat. The dog ran. The sun is hot."); verify `Finding.severity == "low"` and `check == "readability"` (or equivalent check name)
- `test_too_complex`: craft long, multi-syllable sentences that score 16–20; verify `severity == "medium"`
- `test_severely_complex`: FK > 20; verify `severity == "high"`
- `test_ignores_tables`: content with `|col1|col2|\n|---|---|\n|a|b|` → word count should not include table cells
- `test_long_sentence_flagging`: construct content where >40% sentences have >30 words; verify low finding
- `test_abbreviations_not_split`: text containing "e.g. some content. i.e. more content." — only 2 sentences detected, not 4
- Calibrate test inputs carefully — FK formula is sensitive; verify with the actual implementation first
- PYTHONHASHSEED=0 determinism

### Review dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| D1 Specification Alignment | All 6 missing plan spec test cases implemented with correct threshold assertions |
| D6 Production Robustness | Table stripping and abbreviation handling verified as defensive, not crash-prone |
| D7 Test Coverage | 6 new functions; each exercises a distinct threshold or edge case |
| D4 Determinism | No time-dependent logic; PYTHONHASHSEED=0 stable |

### Now (runbook)

```bash
# 1. Read readability check implementation to understand thresholds and check name
grep -n "def check_readability\|severity\|<6\|>16\|>20\|40%\|30 words\|e\.g\.\|table\|\|" src/launcher/workers/evaluate/checks/readability.py | head -40

# 2. Find the FK formula and threshold constants
grep -n "_flesch_kincaid\|FK\|threshold\|severity" src/launcher/workers/evaluate/checks/readability.py | head -20

# 3. Verify table stripping regex
grep -n "table\|pipe\|\\\|" src/launcher/workers/evaluate/checks/readability.py | head -10

# 4. Read existing test file to understand pattern and slug param
grep -n "def test_\|check_readability_from_markdown" tests/unit/workers/test_readability_check.py | head -30

# 5. Calibrate FK inputs manually:
# FK = 0.39*(words/sentences) + 11.8*(syllables/words) - 15.59
# For FK < 6: short sentences (5-6 words), 1 syllable/word
# For FK > 20: long sentences (30+ words), 3+ syllable words

# 6. Write 6 test functions

# 7. Run
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_readability_check.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q
```

---

## GV-01 — AG-002 Governance: evaluate/worker.py Allowed-Paths Violation Remediation

**Status**: Not Started
**Gap linkage**: G-GV-01
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: `evaluate/worker.py` was modified under TC-3853 (H5.1/H5.2 Selective Page Regen)
to add `eval_fast_path` logic, but TC-3853's `allowed_paths` only lists
`orchestrator/worker_contract.py` and `workers/generate/worker.py`.
The actual logical change belongs to TC-3854, whose `allowed_paths` correctly includes
`workers/evaluate/worker.py`.

Remediation steps:
1. Update `plans/taskcards/TC-3854_heal_opt_eval_cache_budget.md` to record that
   `evaluate/worker.py` was modified as part of TC-3854's scope (even though the commit
   occurred while TC-3853 was active). Add an evidence note in the TC-3854 self-review.
2. Update `plans/taskcards/TC-3853_heal_opt_selective_regen.md` to add a governance note
   documenting the violation: the file was written without being in `allowed_paths`;
   the change was logically part of TC-3854 and has been documented there.
3. Create `reports/GV-01/evidence.md` documenting the violation, its discovery, and the
   retroactive attribution.

This is a governance paper trail fix — no production code changes.

**Allowed paths**:
- `plans/taskcards/TC-3853_heal_opt_selective_regen.md`
- `plans/taskcards/TC-3854_heal_opt_eval_cache_budget.md`
- `reports/GV-01/evidence.md`

**Forbidden**: Any other file or path. In particular do NOT modify `evaluate/worker.py`
or `worker_contract.py` — the actual code change is correct; only the paper trail is wrong.

### Acceptance checks

- **CLI**: N/A (governance documentation only)
- **UI/Web/API**: N/A
- **Tests**: No code tests required; verify by reading updated taskcards
- **Config respected end-to-end**: AG-002 governance rule satisfied by retroactive documentation
- **No mock data**: N/A

### Deliverables

- `plans/taskcards/TC-3853_heal_opt_selective_regen.md` — governance violation note added to Self-review section
- `plans/taskcards/TC-3854_heal_opt_eval_cache_budget.md` — `evaluate/worker.py` added to allowed_paths; self-review evidence updated to include the `eval_fast_path` change
- `reports/GV-01/evidence.md` — new file documenting: what was violated, when, what the correct attribution is, and that no code harm resulted

### Hard rules

- Do not remove the `eval_fast_path` code from `evaluate/worker.py` — the code is correct and passes tests
- The violation note must be honest and specific: which file, which TC, which date, which change
- TC-3854's `allowed_paths` YAML frontmatter must be updated to include `evaluate/worker.py`
- TC-3853 status remains `Done` — the governance note is retrospective, not a reopen

### Review dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| D9 Taskcard Governance | Both affected taskcards updated; violation documented with evidence; no orphan change |
| D8 Conflict Zone Compliance | `allowed_paths` in TC-3854 now correctly covers `evaluate/worker.py` |
| D1 Specification Alignment | Evidence file confirms code behavior matches intended TC-3854 scope |

### Now (runbook)

```bash
# 1. Read TC-3853 taskcard to find self-review section
# Read plans/taskcards/TC-3853_heal_opt_selective_regen.md

# 2. Read TC-3854 taskcard to find allowed_paths and self-review
# Read plans/taskcards/TC-3854_heal_opt_eval_cache_budget.md

# 3. Verify the actual change in evaluate/worker.py
grep -n "eval_fast_path" src/launcher/workers/evaluate/worker.py | head -5

# 4. Update TC-3853 self-review: add "AG-002 Governance Note" subsection
# 5. Update TC-3854 allowed_paths frontmatter: add evaluate/worker.py
# 6. Update TC-3854 self-review: record eval_fast_path change attribution
# 7. Create reports/GV-01/ directory and write evidence.md

# 8. Verify no tests were broken (no code change)
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q
```
