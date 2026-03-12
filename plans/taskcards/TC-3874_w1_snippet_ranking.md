---
id: TC-3874
title: "Wave 1: Snippet Quality Ranking in section_prompt.py"
status: In-Progress
priority: Medium
owner: "Agent-B"
updated: "2026-03-09"
tags: [wave-1, section-prompt, snippets, quality]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3874_w1_snippet_ranking.md
  - src/launcher/workers/generate/section_prompt.py
  - tests/generate/test_section_prompt.py
  - reports/TC-3874/evidence.md
evidence_required:
  - reports/TC-3874/evidence.md
---

# Taskcard TC-3874 — Wave 1: Snippet Quality Ranking

## Objective

Replace the FIFO `:5` slice in snippet selection with a quality-ranked sort that
prioritizes real extracted code examples over synthetic stubs. Pure in-memory sort,
deterministic, zero LLM calls.

## Required spec references

- `specs/worker_generate.md` (Section: snippet selection, section_prompt)

## Scope

### In scope
- Replace `[:5]` FIFO slice with `_rank_snippets(snippets, section_claim_ids)` function
- Sort by: (source_type priority, -claim overlap count)
- Add tests for ranking behavior

### Out of scope
- Snippet extraction changes (TC-3870)
- Evidence injection into prompts (TC-3876)
- Any changes outside section_prompt.py

## Inputs

- `src/launcher/workers/generate/section_prompt.py` — snippet selection line
- `src/launcher/models/claims.py` or similar — `Snippet.source_type` field definition

## Outputs

- Updated `src/launcher/workers/generate/section_prompt.py`
- `reports/TC-3874/evidence.md`

## Allowed paths

- plans/taskcards/TC-3874_w1_snippet_ranking.md
- src/launcher/workers/generate/section_prompt.py
- tests/generate/test_section_prompt.py
- reports/TC-3874/evidence.md

## Implementation steps

### Step 1: Read section_prompt.py

Read section_prompt.py. Find the snippet selection line (likely `[:5]` slice).
Confirm `Snippet` model has `source_type` field. Note actual field names.

### Step 2: Add _rank_snippets function

Add before the snippet selection call:
```python
def _rank_snippets(
    snippets: list,  # list[Snippet]
    section_claim_ids: set[str],
    max_count: int = 5,
) -> list:
    """Rank snippets by quality: real extracted > generated > synthetic, then by claim overlap."""
    _SOURCE_PRIORITY = {"extracted": 0, "generated": 1, "synthetic": 2}
    relevant = [s for s in snippets if set(s.claim_ids) & section_claim_ids]
    return sorted(
        relevant,
        key=lambda s: (
            _SOURCE_PRIORITY.get(getattr(s, "source_type", "generated"), 1),
            -len(set(s.claim_ids) & section_claim_ids),
        ),
    )[:max_count]
```

Replace the FIFO filter+slice with:
```python
section_snippets = _rank_snippets(snippets, section_claim_ids)
```

### Step 3: Add/update tests

In `tests/generate/test_section_prompt.py`, add test:
- Create 3 snippets: one "extracted" with 2 claim overlaps, one "synthetic" with 3 overlaps, one "generated" with 1 overlap
- Assert `_rank_snippets` returns them ordered: extracted(2) first, then generated(1), then synthetic(3)
  (source_type priority beats overlap count: extracted always wins over synthetic regardless of overlap)

### Step 4: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/generate/test_section_prompt.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --tb=short
```

## Failure modes

### Failure mode 1: Snippet model has no source_type field
**Detection**: `AttributeError: 'Snippet' has no attribute 'source_type'`
**Resolution**: Use `getattr(s, "source_type", "generated")` as safe fallback
**Gate**: Test passes with safe fallback

### Failure mode 2: Sort is not deterministic across different PYTHONHASHSEED values
**Detection**: Test order differs between runs
**Resolution**: Add secondary sort key on `s.claim_ids[0]` or `s.snippet_id` (stable string)
to ensure full determinism
**Gate**: Run test 3x with different seeds → same order

### Failure mode 3: FIFO was producing better results in practice (counter-intuitive)
**Detection**: No test failure but A-grade rate doesn't improve after Wave 2 pilot
**Resolution**: Add logging: "Snippet source_types selected: {types}" for audit
**Gate**: Monitor in evidence.md post-pilot

## Task-specific review checklist

1. [ ] `_rank_snippets` function added to section_prompt.py
2. [ ] FIFO `[:5]` slice replaced with `_rank_snippets` call
3. [ ] Sort is fully deterministic (no hash-dependent ordering)
4. [ ] Test confirms extracted > synthetic regardless of overlap count
5. [ ] No performance regression (in-memory sort, negligible overhead)
6. [ ] Docstring added to `_rank_snippets`
7. [ ] Spec updated if snippet selection behavior documented
8. [ ] evidence.md: before/after code diff + test result

## Deliverables

1. Updated `src/launcher/workers/generate/section_prompt.py`
2. `reports/TC-3874/evidence.md`

## Acceptance checks

1. [ ] `_rank_snippets` unit test passes with correct ordering
2. [ ] All 2944+ tests pass

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-3874/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --tb=short
```

## Integration boundary proven

**Upstream**: `snippets` list from understand worker (Snippet objects with claim_ids + source_type)
**Downstream**: selected snippets injected into section_prompt as code examples for LLM
**Contract**: `_rank_snippets(snippets, section_claim_ids) -> list[Snippet][:5]`
