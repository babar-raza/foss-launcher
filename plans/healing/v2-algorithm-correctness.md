# v2 Self-Review Healing — Algorithm & Schema Correctness

> Source: Self-review of quirky-mapping-mccarthy (Heal), twinkly-beaming-wren (Golden),
>          sparkling-discovering-walrus (SEO-Phase-2)
> Severity: Critical / High
> Filed: 2026-03-08

Algorithmic bugs and schema gaps that produce wrong output in production even when all
tests pass — because the tests themselves inherit the same wrong assumptions.

---

## Gap Table

| Gap ID | Description | Taskcard | Status |
|--------|-------------|----------|--------|
| GAP-02-ALG | `_check_anchor_diversity` uses `min(len(a), len(b))` denominator — asymmetric lengths cause false duplicate flags | V2AC-01 | Done |
| GAP-05 | Jaccard heading threshold 0.5 rejects semantically equivalent section headings | V2AC-02 | Done |
| GAP-07 | `_inject_freshness_dates` sets `lastmod = now()` on every run — CI/CD re-runs produce spurious diffs | V2AC-03 | Done |
| GAP-03 | `reading_time`, `date`, `lastmod`, `datePublished`, `dateModified` are new frontmatter fields with no schema entry — schema validation fails at publish boundary | V2AC-04 | Done |

---

## V2AC-01 — Fix Anchor Diversity Denominator: `min` → `max`

**Status:** Done
**Gap linkage:** GAP-02-ALG

### Role
Senior engineer. Drop-in, production-ready.

### Context
`_check_anchor_diversity()` in `linker.py` computes word overlap between anchor texts as:
```python
overlap = len(words_i & words_j) / min(len(words_i), len(words_j))
```
Using `min` makes the denominator the length of the shorter anchor. For asymmetric-length
pairs this produces false positives:
- "Install" (1 word) vs "Installation Guide for Python" (4 words)
- Shared words: {"install"} (after .lower()) — but wait, they don't even share words exactly.
  More critically:
- "Install" (1 word) vs "Install Aspose Cells" (3 words)
- shared = {"install"}, `min(1, 3) = 1`, overlap = 1/1 = 1.0 > 0.6 → flagged as duplicate.
  But these are distinct anchors with different targets.

The correct measure is Jaccard (|A ∩ B| / |A ∪ B|) or overlap coefficient with `max`
denominator. Using `max` gives: 1/3 = 0.33 — not a duplicate. This matches intent.

### Scope
**Fix:**
Change `min` to `max` in `_check_anchor_diversity()`. Add a guard for empty sets. Update
existing tests that may rely on the incorrect `min` behavior.

**Allowed paths:**
```
src/launcher/shared/linker.py
tests/test_linker.py
```

**Forbidden:** Any other file.

### Acceptance Checks
- **CLI:**
  ```bash
  python -c "
  from launcher.shared.linker import _check_anchor_diversity
  # 'Install' vs 'Install Aspose Cells' should NOT be a duplicate
  result = _check_anchor_diversity(['Install', 'Install Aspose Cells'], ['Title A', 'Title B'])
  assert result[1] == 'Install Aspose Cells', f'False duplicate: {result}'
  print('ok')
  "
  ```
- **UI/Web/API:** N/A
- **Tests:**
  ```bash
  PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_linker.py -v -k diversity
  ```
  Must pass all existing tests plus 4 new tests.
- **Config respected end-to-end:** N/A — pure algorithmic change.
- **No mock data in production paths:** N/A.

### Deliverables
- **`src/launcher/shared/linker.py`** — full file. `_check_anchor_diversity` uses `max` denominator:
  ```python
  denom = max(len(words_i), len(words_j))
  overlap = len(words_i & words_j) / denom if denom > 0 else 0.0
  ```
- **`tests/test_linker.py`** — full file. New test class `TestAnchorDiversityDenominator` with 4 test cases:
  - `test_asymmetric_short_long_not_duplicate` — "Install" vs "Install Aspose Cells" → kept
  - `test_symmetric_same_word_is_duplicate` — "Install" vs "Install" → replaced (overlap = 1.0)
  - `test_empty_word_set_no_crash` — empty anchor after validation → `denom=0` handled
  - `test_boundary_exactly_60pct` — anchors sharing exactly 60% (max denom) → NOT flagged (threshold is `> 0.6`)

### Hard Rules
- Threshold remains `> 0.6` (not `>=`) — do not change the comparison operator.
- `denom = 0` must return `overlap = 0.0` (no division error).
- Existing `TestAnchorTextOptimization` tests must all still pass.
- No new dependencies.
- Determinism: `words_i` and `words_j` are `set` — intersection/union are set operations, stable with `PYTHONHASHSEED=0`.

### Review Dimensions (what 5/5 means here)
| Dimension | 5/5 criterion |
|-----------|---------------|
| Thoroughness | All 4 edge cases tested: asymmetric, symmetric, empty, boundary |
| Consistency | Aligned with Jaccard semantics used elsewhere in the codebase |
| Production grading | No false duplicate flags for natural anchor text variations |
| Systematic approach | Single formula change with guard; no structural changes |
| Correctness | "Install" vs "Install Aspose Cells" → 1/3 = 0.33 < 0.6 → not duplicate |
| Scope adherence | Only linker.py and its test file |
| Maintainability | `max` denominator is more self-explanatory than `min` |
| Testability | 4 targeted tests including boundary value |
| Robustness | `denom=0` guard prevents ZeroDivisionError on pathological input |
| Performance | No change — same O(1) set operations |
| Integration fit | `_check_anchor_diversity` is internal; no call-site changes |
| Observability | N/A — pure computation, no I/O |
| Minimality | 2-line change + 4 tests |

### Now (Runbook)
```
1. Open src/launcher/shared/linker.py
2. Find _check_anchor_diversity() — the overlap computation line.
3. Replace:
   overlap = len(words_i & words_j) / min(len(words_i), len(words_j))
   WITH:
   denom = max(len(words_i), len(words_j))
   overlap = len(words_i & words_j) / denom if denom > 0 else 0.0

4. In tests/test_linker.py, add class TestAnchorDiversityDenominator:
   - test_asymmetric_short_long_not_duplicate: ["Install", "Install Aspose Cells"] → result[1] == "Install Aspose Cells"
   - test_symmetric_same_word_is_duplicate: ["open", "open"] → result[1] uses fallback
   - test_empty_word_set_no_crash: pass anchor that becomes empty set after split → no crash
   - test_boundary_exactly_60pct_not_flagged: craft 5-word anchors sharing exactly 3 words → 3/5 = 0.60 → NOT duplicate

5. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_linker.py -v
6. Confirm all existing tests still pass.
```

---

## V2AC-02 — Lower Jaccard Heading Match Threshold from 0.5 to 0.3 + Add Normalized Substring

**Status:** Done
**Gap linkage:** GAP-05

### Role
Senior engineer. Drop-in, production-ready.

### Context
`GoldenIndex.get_section()` uses a 3-level match: exact → substring → Jaccard ≥ 0.5.
The 0.5 threshold is too strict for short technical headings:
- "Usage Examples" vs "Code Examples": shared={"examples"}, union={"usage","code","examples"} → Jaccard = 1/3 = 0.33 < 0.5 → no match.
- "Getting Started" vs "Get Started": Jaccard = 0 (lemma mismatch) → no match.

In practice, the golden index silently returns `None` for a majority of real headings, making
the enforcement cascade behave as if no golden reference exists. The plan's 95% code block
presence rate cannot be achieved if golden matches fail for 60%+ of sections.

### Scope
**Fix:**
1. Lower Jaccard threshold from 0.5 to 0.3.
2. Add a "normalized substring" level between exact and Jaccard: strip stop words (`a`, `an`, `the`, `of`, `for`, `in`, `and`, `or`, `with`, `to`), lowercase, check if normalized query is a substring of normalized candidate or vice versa.
3. Update tests to verify new threshold and normalization.

**Allowed paths:**
```
src/launcher/shared/golden_loader.py
tests/unit/shared/test_golden_loader.py
```

**Forbidden:** Any other file.

### Acceptance Checks
- **CLI:**
  ```bash
  python -c "
  from launcher.shared.golden_loader import GoldenIndex
  import tempfile, pathlib
  # Create minimal fixture
  with tempfile.TemporaryDirectory() as d:
      p = pathlib.Path(d) / 'test.md'
      p.write_text('# Test Page\n\n## Usage Examples\n\nSome content here.\n')
      idx = GoldenIndex.load(pathlib.Path(d))
      # Should match via Jaccard 0.33 >= 0.3
      section = idx.get_section('workflow_page', 'standard', 'Code Examples')
      assert section is not None, 'Jaccard 0.33 should match at threshold 0.3'
      print('ok')
  "
  ```
- **UI/Web/API:** N/A
- **Tests:**
  ```bash
  PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_golden_loader.py -v -k heading
  ```
  Must pass: all existing heading tests plus 5 new tests.
- **Config respected end-to-end:** Threshold is a module-level constant `_JACCARD_HEADING_THRESHOLD = 0.3`; not configurable at runtime (no need — it's a quality constant).
- **No mock data in production paths:** GoldenIndex loads real .md files.

### Deliverables
- **`src/launcher/shared/golden_loader.py`** — full file. `get_section()` updated:
  - Level 1: exact match (caseless, strip leading `#`)
  - Level 2: normalized substring match (strip stop words, lowercase, check containment both ways)
  - Level 3: Jaccard ≥ `_JACCARD_HEADING_THRESHOLD = 0.3` (was 0.5)
  - Module constant `_STOP_WORDS: frozenset[str]` for the 10 stop words above.
- **`tests/unit/shared/test_golden_loader.py`** — full file. 5 new test cases in class `TestHeadingMatch`:
  - `test_jaccard_033_matches_at_030_threshold` — "Usage Examples" vs "Code Examples"
  - `test_jaccard_below_030_no_match` — 0/3 shared words → no match
  - `test_normalized_substring_gets_started` — "Getting Started" vs "Get Started" — fails Jaccard but passes normalized substring (after stop word strip, "getting started" contains "get started" after stemming? Actually this won't work without stemming. Let me reconsider...)

  Actually "Getting Started" vs "Get Started" — stripping stop words gives same tokens "getting started" and "get started" — these don't have containment. Jaccard: shared = {}, union = {getting, get, started} — but wait, "started" is shared. So shared={"started"}, union={"getting", "get", "started"} = 3 words, Jaccard = 1/3 = 0.33 ≥ 0.3 → MATCHES via Jaccard. Good.

  Better test for normalized substring: "Introduction to the API" vs "API Introduction" — after stop word strip: "introduction api" vs "api introduction". These are anagram of same words → Jaccard = 2/2 = 1.0 → matches even at 0.5. Not a good test.

  Better: "Overview of Features" → strip "of" → "overview features". Query "Feature Overview" → strip stop → "feature overview". Substring? "overview features" does NOT contain "feature overview" (different order). Jaccard: shared={"overview","feature"}, union={"overview","features","feature"} — tricky with plurals. Let me use a cleaner example.

  Normalized substring is most useful for: "What is Aspose.Cells" vs "Aspose.Cells Overview" — after stop strip: "what aspose.cells" vs "aspose.cells overview". Not substring. So normalized substring mainly helps with articles: "The Installation Guide" vs "Installation Guide" — after strip "the": "installation guide" == "installation guide" → exact after normalization. This is valuable.

  Let me re-define the test cases:
  - `test_article_stripped_exact_match` — "The Installation Guide" vs "Installation Guide" → matches (normalized exact)
  - `test_of_stripped_substring_match` — "Overview of Features" vs "Overview Features" → matches (normalized exact after strip)
  - `test_jaccard_033_matches` — "Usage Examples" vs "Code Examples" → Jaccard 1/3 ≥ 0.3
  - `test_jaccard_029_no_match` — contrived 0.29 case → no match
  - `test_exact_caseless_still_works` — "Usage Examples" vs "usage examples" → exact match (no regression)

**Deliverables (continued):**
5 new test cases as above.

### Hard Rules
- `_JACCARD_HEADING_THRESHOLD = 0.3` is a named constant, not a magic number.
- Stop word stripping uses `frozenset` membership check — O(1) per word.
- Normalized substring check is case-insensitive, whitespace-normalized.
- Existing `GoldenIndex.get()`, `get_spec()`, `select_for_tier()` signatures unchanged.
- No new dependencies (all stdlib string operations).

### Review Dimensions (what 5/5 means here)
| Dimension | 5/5 criterion |
|-----------|---------------|
| Thoroughness | 3-level match fully implemented; stop word list explicit; threshold named constant |
| Consistency | Same Jaccard logic as jaccard.py helper (uses same frozenset-based formula) |
| Production grading | "Usage Examples" / "Code Examples" now match — real-world heading pairs work |
| Systematic approach | Three levels clearly separated; early return on first match |
| Correctness | Jaccard 1/3 = 0.33 ≥ 0.3 → match; 0/3 = 0.0 < 0.3 → no match |
| Scope adherence | Only golden_loader.py and its test file |
| Maintainability | `_STOP_WORDS` and `_JACCARD_HEADING_THRESHOLD` are module constants |
| Testability | 5 named tests covering all 3 levels plus boundary |
| Robustness | Empty heading string handled: `if not heading.strip(): return None` |
| Performance | Stop word strip and Jaccard are O(k) where k = word count — negligible |
| Integration fit | `get_section()` signature unchanged |
| Observability | N/A |
| Minimality | ~20 lines added to `get_section()`; one constant block added |

### Now (Runbook)
```
1. Open src/launcher/shared/golden_loader.py
2. Add module-level constants:
   _STOP_WORDS: frozenset[str] = frozenset({
       "a", "an", "the", "of", "for", "in", "and", "or", "with", "to",
   })
   _JACCARD_HEADING_THRESHOLD: float = 0.3

   def _normalize_heading(h: str) -> str:
       """Lowercase, strip leading '#', remove stop words."""
       words = h.lstrip("#").strip().lower().split()
       return " ".join(w for w in words if w not in _STOP_WORDS)

3. Update get_section() match logic:
   # Level 1: exact caseless
   if query.strip().lower() == candidate.strip().lower():
       return section
   # Level 2: normalized substring (stop-word stripped)
   q_norm = _normalize_heading(query)
   c_norm = _normalize_heading(candidate)
   if q_norm and c_norm and (q_norm in c_norm or c_norm in q_norm):
       return section
   # Level 3: Jaccard on original word sets
   q_words = frozenset(query.lower().split())
   c_words = frozenset(candidate.lower().split())
   if q_words and c_words:
       j = len(q_words & c_words) / len(q_words | c_words)
       if j >= _JACCARD_HEADING_THRESHOLD:
           return section

4. In tests/unit/shared/test_golden_loader.py, add class TestHeadingMatch with 5 test cases.
5. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_golden_loader.py -v -k heading
6. Confirm all prior tests still pass.
```

---

## V2AC-03 — Fix Freshness Dates: `lastmod` Must Not Update on Unchanged Content

**Status:** Done
**Gap linkage:** GAP-07

### Role
Senior engineer. Drop-in, production-ready.

### Context
`_inject_freshness_dates()` in `seo_metadata.py` sets `lastmod = datetime.now(timezone.utc)`
on every invocation. In a CI/CD pipeline that re-runs content generation for unchanged pages
(e.g., after a config change), every page gets a new `lastmod` even if its content is
identical. This causes:
- Spurious git diffs in every re-run (every file marked modified)
- CDN cache invalidation for all pages on every deploy
- Search engine confusion about page freshness (all pages "freshly modified")

Fix: Add an `update_lastmod: bool` parameter. Callers pass `True` when content actually
changed (new generation, heal re-run), `False` for idempotent re-runs.

### Scope
**Fix:**
- Add `update_lastmod: bool = True` to `_inject_freshness_dates(fm, update_lastmod=True)`.
- When `update_lastmod=False` and `"lastmod"` already in `fm` and is non-empty → preserve existing value.
- Add `update_lastmod` parameter to `optimize_seo_metadata()` and thread it through.
- The heal loop calls `optimize_seo_metadata(..., update_lastmod=True)` for pages it actually regenerated.
- A plain re-run (no changes) calls with `update_lastmod=False` (default behavior when wired from run config).

**Allowed paths:**
```
src/launcher/workers/generate/seo_metadata.py
tests/unit/workers/test_seo_metadata.py
```

**Forbidden:** Any other file (call-site threading is part of this taskcard's deliverable).

### Acceptance Checks
- **CLI:**
  ```bash
  python -c "
  from launcher.workers.generate.seo_metadata import _inject_freshness_dates
  fm = {'lastmod': '2026-01-01T00:00:00Z'}
  result = _inject_freshness_dates(dict(fm), update_lastmod=False)
  assert result['lastmod'] == '2026-01-01T00:00:00Z', 'Existing lastmod should be preserved'
  print('ok')
  "
  ```
- **UI/Web/API:** N/A
- **Tests:**
  ```bash
  PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_seo_metadata.py -v -k freshness
  ```
  Must pass all existing TestFreshnessDates tests plus 3 new tests.
- **Config respected end-to-end:** `update_lastmod=False` preserves existing `lastmod` when present.
- **No mock data in production paths:** Tests use `unittest.mock.patch` to freeze `datetime.now()`.

### Deliverables
- **`src/launcher/workers/generate/seo_metadata.py`** — full file. `_inject_freshness_dates(fm: dict, update_lastmod: bool = True) -> dict`. `optimize_seo_metadata(..., update_lastmod: bool = True)` threads the param.
- **`tests/unit/workers/test_seo_metadata.py`** — full file. Class `TestFreshnessDates` gains 3 new test cases:
  - `test_lastmod_preserved_when_update_false` — existing lastmod not overwritten when `update_lastmod=False`
  - `test_lastmod_updated_when_update_true` — existing lastmod IS overwritten when `update_lastmod=True`
  - `test_missing_lastmod_always_set_regardless_of_flag` — missing lastmod is always set (first generation)

### Hard Rules
- Default `update_lastmod=True` preserves current behavior for all existing call sites.
- `date` preservation logic (`if "date" not in fm or not fm["date"]`) is unchanged.
- `datePublished` and `dateModified` mirror `date` and `lastmod` respectively — no change to that logic.
- `update_lastmod=False` with missing `lastmod` → set it anyway (this is first generation).
- Use `datetime.now(timezone.utc)` — never `datetime.utcnow()`.
- No new dependencies.

### Review Dimensions (what 5/5 means here)
| Dimension | 5/5 criterion |
|-----------|---------------|
| Thoroughness | All 3 cases covered: update=True, update=False with existing, update=False without existing |
| Consistency | Default `update_lastmod=True` means zero behavior change for existing callers |
| Production grading | CI/CD re-runs produce identical output for unchanged pages |
| Systematic approach | Single param addition; no state machine or complex logic |
| Correctness | Missing lastmod is always set (even with update=False) — first generation is always "new" |
| Scope adherence | Only seo_metadata.py and its test file |
| Maintainability | Bool param is self-documenting; docstring explains "set True when content changed" |
| Testability | 3 cases; datetime mocked for determinism |
| Robustness | `update_lastmod=False` + missing lastmod → safe (still set) |
| Performance | No change — same operations |
| Integration fit | Heal loop can pass `update_lastmod=True`; pipeline can pass `False` for idempotent runs |
| Observability | N/A |
| Minimality | 2-line change in `_inject_freshness_dates` + 1-param addition to `optimize_seo_metadata` |

### Now (Runbook)
```
1. Open src/launcher/workers/generate/seo_metadata.py
2. Update _inject_freshness_dates signature:
   def _inject_freshness_dates(fm: dict, *, update_lastmod: bool = True) -> dict:
3. Inside, change lastmod logic:
   now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
   if "date" not in fm or not fm["date"]:
       fm["date"] = now
   # Only update lastmod when explicitly requested or when it's missing
   if update_lastmod or not fm.get("lastmod"):
       fm["lastmod"] = now
   fm["datePublished"] = fm["date"]
   fm["dateModified"] = fm["lastmod"]
   return fm
4. Add update_lastmod param to optimize_seo_metadata() and thread to _inject_freshness_dates call.
5. Add tests to TestFreshnessDates class.
6. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_seo_metadata.py -v -k freshness
```

---

## V2AC-04 — Add Missing Frontmatter Fields to JSON Schema

**Status:** Done
**Gap linkage:** GAP-03

### Role
Senior engineer. Drop-in, production-ready.

### Context
TC-SEO-18 adds `date`, `lastmod`, `datePublished`, `dateModified` to frontmatter.
TC-SEO-20 adds `reading_time`. Neither TC includes a schema update. At the publish
boundary, the pipeline validates page frontmatter against `specs/schemas/`. Any new field
not in the schema will either:
- Cause a validation *failure* if the schema uses `"additionalProperties": false`
- Be silently ignored if the schema is permissive (missing explicit opt-in for the field)
Either way, the new fields have no contract enforcement. This must be fixed before any
SEO-18 or SEO-20 code ships.

### Scope
**Fix:**
Add all 5 new fields as optional properties to the frontmatter JSON schema with correct
types, formats, and descriptions.

**Allowed paths:**
```
specs/schemas/frontmatter.schema.json
tests/unit/io/test_schema_validation.py
```

**Forbidden:** Any other file. Do not modify any other schema file.

### Acceptance Checks
- **CLI:**
  ```bash
  python -c "
  import json
  schema = json.loads(open('specs/schemas/frontmatter.schema.json').read())
  props = schema.get('properties', {})
  for field in ['date', 'lastmod', 'datePublished', 'dateModified', 'reading_time']:
      assert field in props, f'Missing field: {field}'
  print('All 5 fields present in schema')
  "
  ```
- **UI/Web/API:** N/A
- **Tests:**
  ```bash
  PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/io/test_schema_validation.py -v -k frontmatter
  ```
  Must pass: existing tests plus 5 new field-specific validation tests.
- **Config respected end-to-end:** Schema is loaded by `schema_validation.py` at the publish boundary; test confirms valid frontmatter with all 5 new fields passes validation.
- **No mock data in production paths:** Schema loaded from `specs/schemas/frontmatter.schema.json` on disk.

### Deliverables
- **`specs/schemas/frontmatter.schema.json`** — full file. 5 new properties added under `"properties"`:
  ```json
  "date":          {"type": "string", "format": "date-time", "description": "ISO 8601 UTC. Set on first generation, never overwritten."},
  "lastmod":       {"type": "string", "format": "date-time", "description": "ISO 8601 UTC. Updated when content changes."},
  "datePublished": {"type": "string", "format": "date-time", "description": "Schema.org datePublished. Mirrors 'date'."},
  "dateModified":  {"type": "string", "format": "date-time", "description": "Schema.org dateModified. Mirrors 'lastmod'."},
  "reading_time":  {"type": "integer", "minimum": 1, "description": "Estimated reading time in minutes (WPM=200)."}
  ```
  All 5 fields remain optional (not added to `"required"`).
- **`tests/unit/io/test_schema_validation.py`** — full file. 5 new test cases:
  - `test_date_field_valid_iso8601` — `"2026-03-08T12:00:00Z"` passes
  - `test_lastmod_field_valid_iso8601` — same
  - `test_reading_time_positive_integer` — `3` passes; `0` fails
  - `test_reading_time_string_fails` — `"3 min"` fails schema validation
  - `test_frontmatter_with_all_5_new_fields_passes` — complete FM with all 5 passes

### Hard Rules
- All 5 new fields are `optional` — never add to `"required"`.
- `"format": "date-time"` is advisory in JSON Schema draft-07 but many validators enforce it — include it.
- `"reading_time"` is `integer`, not `number` — fractional minutes are not valid.
- `"minimum": 1` for reading_time — zero-minute reads are not valid.
- No new dependencies.
- Schema file must remain valid JSON (run `python -m json.tool` to verify after edit).

### Review Dimensions (what 5/5 means here)
| Dimension | 5/5 criterion |
|-----------|---------------|
| Thoroughness | All 5 fields added; types, formats, minimums all specified |
| Consistency | `date-time` format matches what `_inject_freshness_dates` produces |
| Production grading | Publish boundary validation catches wrong types (e.g., `"3 min"` string) |
| Systematic approach | All 5 fields in one schema PR; no piecemeal additions |
| Correctness | `reading_time >= 1` matches `max(1, round(...))` in implementation |
| Scope adherence | Only frontmatter schema and one test file |
| Maintainability | Descriptions explain the business rule (e.g., "Set on first generation") |
| Testability | 5 named tests; valid/invalid pairs for each field type |
| Robustness | `reading_time: 0` fails validation — catches implementation regression |
| Performance | Schema is loaded once at startup; no runtime impact |
| Integration fit | Schema used by existing `schema_validation.py` — zero wiring needed |
| Observability | Validation failures logged with field name by schema_validation.py |
| Minimality | 5 property additions; JSON schema structure unchanged |

### Now (Runbook)
```
1. Open specs/schemas/frontmatter.schema.json
2. Locate the "properties" object.
3. Add the 5 properties listed in Deliverables section above.
4. Run: python -m json.tool specs/schemas/frontmatter.schema.json > /dev/null && echo "Valid JSON"
5. Open tests/unit/io/test_schema_validation.py
6. Add 5 test cases (see Deliverables).
7. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/io/test_schema_validation.py -v -k frontmatter
8. Confirm: all existing frontmatter validation tests still pass.
9. Quick sanity check: python -c "..." CLI check from Acceptance Checks above.
```
