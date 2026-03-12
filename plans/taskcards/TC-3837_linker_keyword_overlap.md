---
id: TC-3837
title: "linker_keyword_overlap"
status: Done
priority: Normal
owner: "agent"
updated: "2026-03-08"
tags: [shared, linker, seo, keywords]
depends_on: [TC-3778]
allowed_paths:
  - src/launcher/shared/linker.py
  - tests/test_linker.py
  - plans/taskcards/TC-3837_linker_keyword_overlap.md
evidence_required:
  - reports/TC-3837/evidence.md
---

# Taskcard TC-3837 — linker_keyword_overlap

## Objective

Extend the cross-page linker with SEO keyword overlap scoring and contextual inline link injection so that pages sharing topic keywords produce stronger links and relevant titles in prose get wrapped as inline hyperlinks.

## Required spec references

- `specs/linker.md` (Section: scoring algorithm, contextual links)

## Scope

### In scope
- Add `seo_keywords: frozenset[str]` to `PageEntry` dataclass
- Populate from `PlannedPage.seo_keywords` in `build_page_index()`
- Add `_KEYWORD_OVERLAP_WEIGHT = 0.15` and `_jaccard_frozensets()` helper
- Wire keyword overlap into `score_links()` base score
- Add `inject_contextual_links()` function (Tier 1 implementation; wiring into `link_pages()` is Tier 2)
- 11 new tests in two new test classes

### Out of scope
- Wiring `inject_contextual_links()` into `link_pages()` (note: function exists and is tested; wiring deferred to Tier 2 to avoid disrupting existing e2e)
- Changes to other linker functions (`inject_links`, `absolutize_urls`)
- LLM-based keyword extraction

## Inputs

- `src/launcher/shared/linker.py` (cross-page linker)
- `src/launcher/models/plan.py` (PlannedPage with `seo_keywords` field already present)

## Outputs

- Modified `src/launcher/shared/linker.py` with keyword overlap scoring + contextual injection function
- 11 new tests in `tests/test_linker.py` (TestKeywordOverlap x5, TestContextualLinks x6)

## Allowed paths

- src/launcher/shared/linker.py
- tests/test_linker.py
- plans/taskcards/TC-3837_linker_keyword_overlap.md

### Allowed paths rationale
Source file contains the linker. Test file already exists. Taskcard documents the work.

## Implementation steps

### Step 1: Extend PageEntry dataclass

Add `seo_keywords: frozenset[str] = field(default_factory=frozenset)` to the `PageEntry` dataclass.

### Step 2: Populate in build_page_index()

Add `seo_keywords=frozenset(getattr(pp, "seo_keywords", []) or [])` when constructing PageEntry.

### Step 3: Add helpers before build_page_index()

Add `_KEYWORD_OVERLAP_WEIGHT = 0.15` constant and `_jaccard_frozensets(a, b)` helper.

### Step 4: Wire keyword overlap in score_links()

After the Jaccard claim scoring line, add:
```python
if src.seo_keywords or tgt.seo_keywords:
    kw_overlap = _jaccard_frozensets(src.seo_keywords, tgt.seo_keywords)
    base += kw_overlap * _KEYWORD_OVERLAP_WEIGHT
```

### Step 5: Add inject_contextual_links() function

Place after `link_pages()`. Uses `BlockType.paragraph` check to skip non-paragraph blocks. Uses `re.escape()` for title matching. Caps at `max_inline` per page. Returns `(new_page_ir, cross_links_list)`.

### Step 6: Add tests

Add `TestKeywordOverlap` and `TestContextualLinks` classes to `tests/test_linker.py`. Use `model_copy()` for frozen `PlannedPage` mutations.

### Step 7: Verify

Run `tests/test_linker.py` then full suite.

## Failure modes

### Failure mode 1: PlannedPage is frozen — cannot set seo_keywords directly

**Detection**: `ValidationError: Instance is frozen` when test does `plan.seo_keywords = [...]`
**Resolution**: Use `plan.model_copy(update={"seo_keywords": [...]})` in tests
**Gate**: Pydantic frozen model constraint

### Failure mode 2: Keyword bonus pushes score above 1.0

**Detection**: Score > 1.0 in score_links output
**Resolution**: Score is clamped to [0, 1] via `max(0.0, min(1.0, base))` after all bonuses
**Gate**: Clamp logic already in score_links

### Failure mode 3: inject_contextual_links regex matches inside existing links

**Detection**: `test_contextual_link_already_linked_skipped` fails
**Resolution**: Use negative lookbehind `(?<!\[)` to skip already-linked occurrences
**Gate**: regex correctness

## Task-specific review checklist

1. [x] `seo_keywords` field uses `frozenset` (not list) in PageEntry
2. [x] `_jaccard_frozensets` handles empty frozenset inputs without error
3. [x] Keyword overlap bonus applied BEFORE the clamp to [0, 1]
4. [x] `inject_contextual_links` skips non-paragraph blocks (code, list, heading, etc.)
5. [x] `inject_contextual_links` never self-links (target_id != source_id guard)
6. [x] All 47 linker tests pass; full suite 2392 passed

## Deliverables

1. `src/launcher/shared/linker.py` — keyword overlap scoring + `inject_contextual_links()`
2. 11 new tests in `tests/test_linker.py` (TestKeywordOverlap x5, TestContextualLinks x6)

## Acceptance checks

1. [x] 47/47 test_linker tests pass (11 new + 36 existing)
2. [x] Full suite: 2392 passed, 0 failed
3. [x] `inject_contextual_links()` is importable and functional

## Self-review

### Verification results
- [x] Tests: 120/120 PASS (full linker suite), 2392/2392 PASS (full suite, run 2026-03-08)
- [x] 11 new tests: TestKeywordOverlap (5) + TestContextualLinks (6)
- [x] self-link exclusion, code-block skip, already-linked skip all PASS
- [x] Evidence file: `reports/TC-3837/evidence.md`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_linker.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Actual results** (run 2026-03-08):
```
TestKeywordOverlap::test_keyword_overlap_boosts_score PASSED
TestKeywordOverlap::test_keyword_overlap_empty_keywords PASSED
TestKeywordOverlap::test_seo_keywords_in_page_entry PASSED
TestKeywordOverlap::test_jaccard_frozensets_basic PASSED
TestKeywordOverlap::test_jaccard_frozensets_empty PASSED
TestContextualLinks::test_contextual_link_injection_basic PASSED
TestContextualLinks::test_contextual_link_max_cap PASSED
TestContextualLinks::test_contextual_link_no_self_link PASSED
TestContextualLinks::test_contextual_link_skips_code_blocks PASSED
TestContextualLinks::test_contextual_link_no_match_no_change PASSED
TestContextualLinks::test_contextual_link_already_linked_skipped PASSED
120 passed in 0.48s

2392 passed in 53.28s
```

## Integration boundary proven

**Upstream**: `score_links()` consumes `PageEntry.seo_keywords` populated from `PlannedPage.seo_keywords`
**Downstream**: `inject_contextual_links()` consumes `ScoredLink` list and `PageEntry` index; returns modified `PageIR`
**Contract**: `inject_contextual_links` signature: `(page_ir, scored_links, page_index, source_id, max_inline=2) -> (PageIR, list[dict])`

### Note on Tier 2 wiring

`inject_contextual_links()` is implemented and tested but not yet wired into `link_pages()`. This is intentional — wiring requires updating the `link_pages()` orchestrator loop and the `CrossLink` manifest, which is a separate scope. See Tier 2 backlog.
