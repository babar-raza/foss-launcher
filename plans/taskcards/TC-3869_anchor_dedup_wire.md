---
id: TC-3869
title: "Wire _deduplicate_anchors into generate_anchor_texts"
status: Done
priority: Normal
owner: "claude-agent"
updated: "2026-03-08"
tags: [seo, linker, anchor-text, SEO-19]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3869_anchor_dedup_wire.md
  - src/launcher/shared/linker.py
  - tests/test_linker.py
evidence_required:
  - reports/TC-3869/evidence.md
---

# Taskcard TC-3869 — Wire _deduplicate_anchors into generate_anchor_texts

## Objective

`_deduplicate_anchors` is defined in `linker.py` and tested in isolation, but is
never called in `generate_anchor_texts`. Per the SEO-19 plan spec
(`sparkling-discovering-walrus.md`, §TC-SEO-19, point 4), deduplication must run
"after individual validation, before returning from `generate_anchor_texts()`".
This gap means near-identical anchor texts across a page's See Also links are NOT
de-duplicated, hurting SEO quality and content diversity.

## Required spec references

- `C:\Users\prora\.claude\plans\sparkling-discovering-walrus.md` (§TC-SEO-19)

## Scope

### In scope
- Wire `_deduplicate_anchors(anchors, fallbacks)` at the end of the post-LLM
  validation loop in `generate_anchor_texts()` in `src/launcher/shared/linker.py`
- Add a regression test in `tests/test_linker.py` that verifies deduplication
  fires within `generate_anchor_texts` (not just in isolation)

### Out of scope
- No changes to `_deduplicate_anchors` logic (already correct with `max` denominator)
- No changes to `_check_anchor_diversity` (standalone utility, tested separately)
- No schema changes

## Inputs

- `src/launcher/shared/linker.py` — current `generate_anchor_texts` function

## Outputs

- `src/launcher/shared/linker.py` — `generate_anchor_texts` now calls
  `_deduplicate_anchors(anchors, fallback_titles)` before building final result
- `tests/test_linker.py` — new test class `TestGenerateAnchorTextsDedup`

## Allowed paths

- `src/launcher/shared/linker.py`
- `tests/test_linker.py`

## Implementation steps

1. In `generate_anchor_texts`, after the post-LLM validation loop builds `result`,
   extract the validated anchor texts and their fallback titles, call
   `_deduplicate_anchors(validated_anchors, fallback_titles)`, then rebuild the
   `ScoredLink` objects with the deduped anchors.
2. Add test `TestGenerateAnchorTextsDedup::test_duplicate_anchors_deduped` that
   mocks the LLM to return two identical anchors, verifies they differ in the output.
3. Add test `test_distinct_anchors_preserved` verifying distinct anchors unchanged.

## Failure modes

1. `_deduplicate_anchors` length mismatch (anchors != fallbacks) → function already
   handles this by returning `list(anchors)` unchanged — safe fallthrough
2. Empty scored_links → early return before dedup → no issue
3. LLM unavailable → title fallback applied before dedup → dedup still applied to
   title-fallback anchors (correct — titles can also be near-duplicate)

## Task-specific review checklist

- [ ] `generate_anchor_texts` calls `_deduplicate_anchors` before return
- [ ] Fallback titles are collected as `fallback_titles` list (same length as anchors)
- [ ] No change to the standalone `_check_anchor_diversity` function or its tests
- [ ] New tests verify end-to-end dedup inside `generate_anchor_texts`
- [ ] All existing `TestGenerateAnchorTexts` tests still pass
- [ ] Full suite: 2936+ tests, 0 failures

## Deliverables

- Modified `src/launcher/shared/linker.py`
- Modified `tests/test_linker.py` (new `TestGenerateAnchorTextsDedup` class)

## Acceptance checks

- [x] Taskcard created with status In-Progress
- [ ] `_deduplicate_anchors` is called in `generate_anchor_texts`
- [ ] New tests pass, existing tests unchanged
- [ ] Full suite passes (PYTHONHASHSEED=0)

## Self-review

_To be filled after implementation._

## E2E verification

Run: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_linker.py -v`
Expected: all tests pass including new dedup tests.

## Integration boundary proven

`generate_anchor_texts` is called from `link_pages`, which is called from the
Generate worker. The dedup runs in the same process, no boundary crossing required.
