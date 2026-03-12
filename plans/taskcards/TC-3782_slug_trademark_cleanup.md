---
id: TC-3782
title: "Slug Pipeline — HTML Entity & Trademark Symbol Cleanup"
status: Done
priority: Medium
owner: Agent-B
updated: "2026-03-07"
tags: [phase-3, slug, quality]
depends_on: [TC-3780, TC-3781]
allowed_paths:
  - plans/taskcards/TC-3782_slug_trademark_cleanup.md
  - src/launcher/shared/slug_engine.py
  - tests/unit/shared/test_slug_engine.py
  - tests/unit/workers/test_plan_slug_integration.py
  - reports/agents/B/TC-3782/
evidence_required:
  - reports/agents/B/TC-3782/evidence.md
---

# Taskcard TC-3782 — Slug Pipeline — HTML Entity & Trademark Symbol Cleanup

## Objective

Strip HTML entities (`&reg;`, `&trade;`, `&copy;`) from text before slug derivation, and add a validation gate to catch trademark artifacts (`excelreg`, `windowsreg`) that leak into slugs from claim text. Pilot verification of TC-3781 showed slugs like `print-microsoft-excelreg-files-to-spreadsheets` which are SEO-harmful and visually broken.

## Required spec references

- `specs/site_model_hugo.md` (Section: slug format constraints — lowercase alphanumeric + hyphens)
- `specs/rulesets/ruleset.yaml` (Section: slug_strategy fields added by TC-3781)

## Scope

### In scope

- Add `html.unescape()` + trademark symbol stripping in `derive_semantic_slug()`
- Add `html.unescape()` + trademark symbol stripping in `derive_evidence_aware_slug()`
- Add HTML entity artifact detection in `validate_slug_safety()`
- Add tests for all three changes

### Out of scope

- Fixing claim extraction to strip HTML entities at source (belongs to CQ workstream)
- Modifying `extract.py` or claim normalization pipeline
- Changes to any evaluate check other than `validate_slug_safety()`

## Inputs

- Claim text containing HTML entities (e.g., `"Print Microsoft Excel&reg; files"`)
- `src/launcher/shared/slug_engine.py` (current slug derivation functions)

## Outputs

- Modified `src/launcher/shared/slug_engine.py` with HTML entity handling
- New tests in `tests/unit/shared/test_slug_engine.py`
- New test in `tests/unit/workers/test_plan_slug_integration.py`
- Evidence at `reports/agents/B/TC-3782/evidence.md`

## Allowed paths

- `plans/taskcards/TC-3782_slug_trademark_cleanup.md`
- `src/launcher/shared/slug_engine.py`
- `tests/unit/shared/test_slug_engine.py`
- `tests/unit/workers/test_plan_slug_integration.py`
- `reports/agents/B/TC-3782/`

### Allowed paths rationale

- `slug_engine.py`: Contains `derive_semantic_slug`, `derive_evidence_aware_slug`, and `validate_slug_safety` — all three need changes
- `test_slug_engine.py`: Unit tests for the slug engine changes
- `test_plan_slug_integration.py`: Integration test proving trademark claims produce clean slugs end-to-end
- `reports/agents/B/TC-3782/`: Evidence capture

## Implementation steps

### Step 1: Add `import html` to slug_engine.py

Add `import html` to the stdlib imports section at the top of the file.

### Step 2: Strip HTML entities in `derive_semantic_slug()`

After the preamble stripping loop (line ~192) and before the word extraction (line ~200), add:

```python
# Strip HTML entities (e.g. &reg; → ®) then remove trademark symbols
text = html.unescape(text)
text = re.sub(r"[®™©]", "", text)
```

### Step 3: Strip HTML entities in `derive_evidence_aware_slug()`

At line ~288 where `title_lower = title.lower()`, prepend:

```python
title = html.unescape(title)
title = re.sub(r"[®™©]", "", title)
title_lower = title.lower()
```

### Step 4: Add trademark artifact check in `validate_slug_safety()`

After the doubled-URL-segment check, add:

```python
# Check for HTML entity remnants glued to words
_ENTITY_ARTIFACT_RE = re.compile(r"[a-z](?:reg|trade|copy)(?=-|$)")
if _ENTITY_ARTIFACT_RE.search(slug):
    issues.append("Possible HTML entity remnant (e.g. 'excelreg' from '&reg;')")
```

### Step 5: Add tests

In `test_slug_engine.py`:
- `test_semantic_slug_strips_html_reg` — input with `&reg;` produces clean slug
- `test_semantic_slug_strips_html_trade` — input with `&trade;` produces clean slug
- `test_semantic_slug_strips_unicode_symbols` — input with `®™©` produces clean slug
- `test_safety_catches_entity_artifact` — `validate_slug_safety("excelreg-files")` reports issue
- `test_safety_no_false_positive_registration` — `validate_slug_safety("registration-form")` is clean

In `test_plan_slug_integration.py`:
- `test_claim_with_html_entities_produces_clean_slug` — claim text with `&reg;` results in slug without `reg` artifact

## Failure modes

### Failure mode 1: False positive on legitimate words

**Detection**: `validate_slug_safety("registration-form")` reports an issue when it shouldn't
**Resolution**: The regex `[a-z](?:reg|trade|copy)(?=-|$)` requires a preceding letter, so standalone `reg-` won't match. Verify with tests. If `registration` matches, the regex catches `ration` which contains `reg`... actually no — it looks for `reg` preceded by a letter and followed by `-` or `$`. `registration` has `reg` at position 0-2 but `[a-z]` requires a char before `reg`, so `istration` wouldn't match. `registreg-` would match but that's not a real word.
**Gate**: Slug safety validation

### Failure mode 2: Unrecognized HTML entities leak through

**Detection**: Claim text contains exotic entities like `&mdash;`, `&hellip;` that produce different artifacts
**Resolution**: `html.unescape()` handles ALL standard HTML entities (it's stdlib). The trademark strip (`[®™©]`) only removes the three trademark symbols, but other symbols like `—` and `…` are already removed by the `[^a-z0-9\s-]` regex in slugification.
**Gate**: SEO slug format check (`^[a-z0-9_-]+$`)

### Failure mode 3: Existing tests break due to expected slug changes

**Detection**: Existing tests that use claim text with `&reg;` would produce different slugs
**Resolution**: Search existing test fixtures for HTML entities. If any exist, update expected values.
**Gate**: Full test suite pass

## Task-specific review checklist

1. [ ] `derive_semantic_slug("Print Microsoft Excel&reg; files")` → no `reg` in output
2. [ ] `derive_evidence_aware_slug` with `&reg;` in title → clean slug
3. [ ] `validate_slug_safety("excelreg-files")` returns non-empty issues list
4. [ ] `validate_slug_safety("registration-form")` returns empty list (no false positive)
5. [ ] `validate_slug_safety("convert-xlsx-to-csv")` returns empty list (no regression)
6. [ ] All existing slug engine tests still pass
7. [ ] All existing planner integration tests still pass
8. [ ] Full suite passes with zero regressions

## Deliverables

1. Modified `src/launcher/shared/slug_engine.py` — HTML entity stripping + validation gate
2. New tests in `tests/unit/shared/test_slug_engine.py`
3. New test in `tests/unit/workers/test_plan_slug_integration.py`
4. Evidence at `reports/agents/B/TC-3782/evidence.md`

## Acceptance checks

1. [ ] `derive_semantic_slug` strips `&reg;`, `&trade;`, `&copy;` from input text
2. [ ] `validate_slug_safety` catches glued entity artifacts like `excelreg`
3. [ ] No false positives on words like `registration`, `copyright`, `trademark`
4. [ ] Full test suite passes: `.venv/Scripts/python.exe -m pytest tests/ --tb=short -q`
5. [ ] Pilot dry-run produces zero trademark artifact slugs

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: slug safety gate PASS
- [ ] Evidence captured: reports/agents/B/TC-3782/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_slug_engine.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_plan_slug_integration.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ --tb=short -q
```

**Expected results**:
- All slug engine tests pass including new HTML entity tests
- All planner integration tests pass including new trademark claim test
- Full suite green (1408+ tests)
- No trademark artifacts in pilot slug output

## Integration boundary proven

**Upstream**: TC-3781 (planner slug integration) calls `derive_semantic_slug` and `derive_evidence_aware_slug` with claim text that may contain HTML entities from extract.py
**Downstream**: `validate_slug_safety()` is already called at all 3 enrichment sites (SR-02) and in the evaluate gate (`check_slug_safety`). Adding the new check auto-propagates to both.
**Contract**: Slug strings remain `[a-z0-9-]+`, max 80 chars, no HTML entity remnants
