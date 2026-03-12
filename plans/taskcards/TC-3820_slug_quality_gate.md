---
id: TC-3820
title: "Slug semantic quality gate — human-readable SEO-friendly slugs"
status: In-Progress
priority: High
owner: agent
updated: "2026-03-07"
tags: [slug, seo, quality]
depends_on: [TC-3780, TC-3781]
allowed_paths:
  - plans/taskcards/TC-3820_slug_quality_gate.md
  - src/launcher/shared/slug_engine.py
  - src/launcher/workers/planner/plan.py
  - tests/unit/shared/test_slug_engine.py
  - tests/unit/workers/planner/test_plan_slug_quality.py
evidence_required:
  - reports/TC-3820/evidence.md
---

# Taskcard TC-3820 — Slug semantic quality gate

## Objective

Add a semantic quality validation layer to the slug engine that rejects nonsensical, redundant, or sentence-fragment slugs and replaces them with structured, human-readable alternatives. Currently `validate_slug_safety()` only catches URL-technical issues (brackets, double hyphens) but lets garbled slugs like `microsoft-windows-windows-desktop-spreadsheets` through.

## Required spec references

- `specs/rulesets/ruleset.yaml` (Section: slug_strategy per page type)
- `specs/20_rulesets_and_templates_registry.md` (Section: slug conventions)

## Scope

### In scope
- New `validate_slug_quality()` function in slug_engine.py
- Noise-word filtering in `derive_semantic_slug()`
- New `_extract_slug_core()` structured fallback helper
- Quality gate wiring in plan.py (slug assignment + `_derive_optional_slug`)
- Unit tests for all new functions

### Out of scope
- Changes to `validate_slug_safety()` (URL-technical checks — keep as-is)
- Changes to `_HOWTO_SLUG_TEMPLATES` (already produce good slugs)
- Changes to static blog slugs (already good)
- Gemini/LLM refinement path (keep as-is)
- Regenerating existing deploy content (separate run)

## Inputs

- Raw claim text, workflow titles, page roles from planner pipeline
- `ProductEvidence` from Understand worker
- `FAMILY_KEYWORD_MAP` constants

## Outputs

- Updated `slug_engine.py` with quality validation + noise filtering + structured fallback
- Updated `plan.py` with quality gate wiring
- Unit tests proving quality checks work

## Allowed paths

- plans/taskcards/TC-3820_slug_quality_gate.md
- src/launcher/shared/slug_engine.py
- src/launcher/workers/planner/plan.py
- tests/unit/shared/test_slug_engine.py
- tests/unit/workers/planner/test_plan_slug_quality.py

### Allowed paths rationale
- slug_engine.py: core slug generation logic, adding quality validation
- plan.py: slug assignment pipeline, wiring quality checks
- test files: proving correctness

## Implementation steps

### Step 1: Add `validate_slug_quality()` to slug_engine.py

Add function that checks for:
- Redundant words (same word appears twice)
- Consecutive duplicate words ("windows-windows")
- High stop-word ratio (>50% stop words = sentence fragment)
- OS/platform noise words that aren't product-relevant
Returns list of quality issues (empty = good).

### Step 2: Add noise-word filtering to `derive_semantic_slug()`

Add `_NOISE_WORDS` set and filter them from text before extracting first 6 words. Preserves product family words.

### Step 3: Add `_extract_slug_core()` helper

Extract verb+noun core from text for structured fallback:
- Scan for high-intent verbs (convert, create, load, etc.)
- Extract the object noun following the verb
- Combine as `{verb}-{object}-{family_keyword}`

### Step 4: Wire quality gate into plan.py

Add `_quality_check_slugs()` step that runs `validate_slug_quality()` on each page's slug after assignment. For failures: reconstruct using `_extract_slug_core()` or structured fallback pattern.

### Step 5: Harden `_derive_optional_slug()` in plan.py

When `derive_semantic_slug(claim.text)` fails quality check, try next claim. If all fail, use `{kind}-{family_keyword}-{index}` fallback.

### Step 6: Add unit tests

Test all new functions with known-bad slug examples from deploy folder.

## Failure modes

### Failure mode 1: Quality gate too aggressive — rejects valid slugs

**Detection**: Existing tests fail; good slugs like "how-to-load-spreadsheets-python" get flagged
**Resolution**: Tune thresholds (stop-word ratio, minimum word count for duplicate check). Add explicit allowlist for known-good patterns (how-to-*, introducing-*).
**Gate**: Unit tests for positive cases

### Failure mode 2: Noise-word filter removes product-relevant words

**Detection**: Family keyword ("cells", "note") stripped as noise
**Resolution**: Cross-reference `_NOISE_WORDS` with `FAMILY_KEYWORD_MAP` values and product names to ensure no overlap.
**Gate**: Unit test with family-keyword-containing slugs

### Failure mode 3: _extract_slug_core() produces empty/generic fallback

**Detection**: Slug becomes "feature" or empty string for most inputs
**Resolution**: Widen verb detection to include family-specific verbs. Ensure fallback chain: core → semantic → pattern.
**Gate**: Unit test with diverse claim texts

## Task-specific review checklist

1. [ ] `validate_slug_quality()` catches all 5 known-bad deploy slugs
2. [ ] `validate_slug_quality()` passes all existing good slugs (how-to-*, introducing-*, key-features)
3. [ ] `_NOISE_WORDS` does not overlap with `FAMILY_KEYWORD_MAP` values
4. [ ] `derive_semantic_slug()` noise filtering preserves family keywords
5. [ ] `_extract_slug_core()` produces readable slugs for blog and KB contexts
6. [ ] Quality gate in plan.py logs all slug replacements at DEBUG level

## Deliverables

1. Updated `src/launcher/shared/slug_engine.py`
2. Updated `src/launcher/workers/planner/plan.py`
3. Test file(s) with quality validation coverage

## Acceptance checks

1. [ ] All existing slug_engine tests pass
2. [ ] All existing planner tests pass
3. [ ] New unit tests for `validate_slug_quality()` pass
4. [ ] Known-bad slugs from deploy are correctly rejected
5. [ ] Known-good slugs pass quality check

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: slug quality gate PASS
- [ ] Evidence captured: reports/TC-3820/

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_slug_engine.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
```

**Expected results**:
- All existing tests pass (no regressions)
- New quality validation tests pass
- Known-bad slugs rejected, known-good slugs accepted

## Integration boundary proven

**Upstream**: Planner pipeline (plan.py) calls slug_engine functions with claim text and workflow titles
**Downstream**: Generated slugs become frontmatter fields, filenames, and URLs in deploy output
**Contract**: `validate_slug_quality()` returns `list[str]` (empty = pass), same pattern as `validate_slug_safety()`
