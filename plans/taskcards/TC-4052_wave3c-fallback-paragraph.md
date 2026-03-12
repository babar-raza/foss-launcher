---
id: TC-4052
title: "Wave 3C: Fallback paragraph-from-claim instead of bare list"
status: Done
priority: High
owner: "orchestrator"
updated: "2026-03-11"
tags: [crispy-growing-pebble, wave-3c, retroactive]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4052_wave3c-fallback-paragraph.md
  - src/launcher/workers/generate/fallback.py
  - tests/unit/workers/test_generate.py
  - tests/unit/workers/generate/test_fallback_deterministic.py
evidence_required:
  - reports/TC-4052/evidence.md
---

# Taskcard TC-4052 — Wave 3C: Fallback Paragraph Improvement

## Objective

Retroactive taskcard (AG-002 compliance) for Wave 3C changes to `fallback.py`. When the
deterministic fallback renders sections with claims but no boilerplate template, previously
emitted a bare bullet list. Now emits a prose paragraph from the first 1-2 claims, with
remaining claims as a smaller list. Reduces bot-like output.

## Required spec references

- `crispy-growing-pebble.md` Wave 3C

## Scope

### In scope
- `render_section_deterministic()` non-tabular claim rendering path
- First 2 claims → `BlockIR(type=paragraph, content="...")`
- Claims 3+ → `BlockIR(type=list, items=[...])`
- Two test files updated to match new block shape

### Out of scope
- Tabular heading sections (unchanged)
- Boilerplate sections (TC-3912 — separate taskcard)

## What was implemented

In `render_section_deterministic()`, for non-tabular sections with claims:

```python
intro_parts = [claims[0].text.rstrip(".")]
intro_claim_ids = [claims[0].claim_id]
if len(claims) > 1:
    intro_parts.append(claims[1].text.rstrip("."))
    intro_claim_ids.append(claims[1].claim_id)
intro = f"{product.display_name} {intro_parts[0]}."
if len(intro_parts) > 1:
    intro += f" {intro_parts[1]}."
blocks.append(BlockIR(type=BlockType.paragraph, content=intro, claim_ids=intro_claim_ids))
if len(claims) > 2:
    blocks.append(BlockIR(type=BlockType.list, items=[c.text for c in claims[2:]], claim_ids=[c.claim_id for c in claims[2:]]))
```

Two tests updated:
- `test_render_section_deterministic_with_claims` → expects paragraph + optional list
- `test_prerequisites_with_claims_uses_claims_not_boilerplate` → expects paragraph block

**Known gap**: Grammar issue — if claim starts with capitalized verb ("Supports..."), produces
"Aspose.Cells FOSS Supports..." (capitalized mid-sentence). Tracked in CGB-07.

## Inputs

- `src/launcher/workers/generate/fallback.py` (before Wave 3C)

## Outputs

- Updated `src/launcher/workers/generate/fallback.py`
- Updated test assertions in 2 test files

## Allowed paths

- plans/taskcards/TC-4052_wave3c-fallback-paragraph.md
- src/launcher/workers/generate/fallback.py
- tests/unit/workers/test_generate.py
- tests/unit/workers/generate/test_fallback_deterministic.py

## Self-review

### Verification results

- [x] `render_section_deterministic()` emits paragraph for non-tabular sections
- [x] Two updated tests pass (PYTHONHASHSEED=0)
- [x] Grammar gap documented in CGB-07 healing plan

## Integration boundary proven

**Upstream**: Called from generate worker when LLM call fails or eval_fast_path is set
**Downstream**: `BlockIR` objects assembled into PageIR → rendered to markdown
**Contract**: Non-tabular sections with claims → paragraph + optional list (never bare list)
