---
id: TC-4231
title: "P-1: Add page-level claim relevance filtering in Planner"
status: Done
priority: Medium
owner: "Agent-B"
updated: "2026-03-12"
tags: [planner, claims, relevance, filtering]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4231_planner-claim-relevance-filtering.md
  - src/launcher/workers/planner/
  - tests/unit/workers/
evidence_required:
  - reports/TC-4231/evidence.md
---

# Taskcard TC-4231 — P-1: Add page-level claim relevance filtering in Planner

## Objective

Score each claim against page purpose/role/slug and assign only the top-N most relevant claims per section (max 15) and per page (max 50). This prevents generic claims from being assigned to unrelated pages, which causes the LLM to generate off-topic or hallucinatory content.

## Required spec references

- `specs/worker_understand.md` (Section: Claim fields — topic, page_role hints)
- `specs/worker_generate.md` (Section: Claim injection per page)

## Scope

### In scope
- Implement relevance scoring function: score(claim, page) based on topic overlap with page slug/role
- Apply top-N filter per section (max 15) and per page (max 50)
- Unit tests for scoring function and filter

### Out of scope
- Embedding-based semantic scoring (too expensive — use keyword overlap)
- Changes to claim extraction or understand phase
- Changes to generate worker (TC-4230 handles section-level cap)

## Inputs

- `src/launcher/workers/planner/` — planner worker files
- Understand bundle — claims with topic/confidence fields
- Page plan — page slug, role, title

## Outputs

- Modified planner worker — relevance filter applied before claim assignment
- Updated tests in `tests/unit/workers/`

## Allowed paths

- plans/taskcards/TC-4231_planner-claim-relevance-filtering.md
- src/launcher/workers/planner/
- tests/unit/workers/

### Allowed paths rationale
Claim-to-page assignment happens in the planner. The test directory covers planner unit tests.

## Implementation steps

### Step 1: Read planner worker to find claim assignment logic

Locate where claims are assigned to pages/sections in `src/launcher/workers/planner/`.

### Step 2: Implement relevance scoring

```python
MAX_CLAIMS_PER_SECTION = 15
MAX_CLAIMS_PER_PAGE = 50

def score_claim_relevance(claim: Claim, page_slug: str, page_role: str) -> float:
    """Score claim relevance to a page using keyword overlap."""
    slug_tokens = set(page_slug.lower().replace("-", " ").split())
    claim_tokens = set((claim.topic or "").lower().split())
    overlap = len(slug_tokens & claim_tokens)
    role_match = 1.0 if claim.page_role_hint == page_role else 0.0
    confidence_weight = claim.confidence
    return overlap * 0.5 + role_match * 0.3 + confidence_weight * 0.2
```

### Step 3: Apply filter in planner

Before assigning claims to a page:
1. Score all claims against the page
2. Sort by score DESC
3. Take top MAX_CLAIMS_PER_PAGE
4. Within each section, take top MAX_CLAIMS_PER_SECTION

### Step 4: Write unit tests

Add tests covering:
1. Claims with matching slug tokens score higher than unrelated claims
2. Page-level cap: 60 claims in → 50 out
3. Section-level cap: 20 claims for section → 15 out
4. Claims with page_role_hint matching page_role score higher

### Step 5: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/ -v -q
```

## Failure modes

### Failure mode 1: Relevance scoring removes all claims for a page

**Detection**: Page has 0 claims assigned; generate produces empty/thin content.
**Resolution**: Add fallback: if after filtering page has < 5 claims, re-add top-5 by confidence regardless of relevance score.
**Gate**: Generate content density check

### Failure mode 2: Keyword overlap scoring too coarse

**Detection**: Generic claims ("supports file formats") score equally for all pages.
**Resolution**: Apply IDF-style weighting: terms that appear in many claims are less discriminative. Downweight common claim tokens.
**Gate**: Factual accuracy findings per page

### Failure mode 3: Planner file structure unfamiliar causing wrong location for filter

**Detection**: Filter code added in wrong function, not applied before assignment.
**Resolution**: Read all files in `src/launcher/workers/planner/` before implementing. Add an integration test that checks assigned claim count after planner runs.
**Gate**: Unit test on claim assignment count

## Task-specific review checklist

1. [ ] `score_claim_relevance` function implemented with slug + role + confidence components
2. [ ] MAX_CLAIMS_PER_PAGE = 50 applied at page level
3. [ ] MAX_CLAIMS_PER_SECTION = 15 applied at section level
4. [ ] Fallback: if < 5 claims after filter, top-5 by confidence added
5. [ ] Unit test: matching-slug claims score higher
6. [ ] Unit test: page-level cap applied correctly
7. [ ] Docstrings updated for new relevance scoring function
8. [ ] Spec file updated if planner behavior changed
9. [ ] Schema `"description"` fields not applicable (no schema change)
10. [ ] Checked `docs/README.md` ownership map — trigger event check done
11. [ ] No new docs/guides/ file added

## Deliverables

1. `src/launcher/workers/planner/` — relevance filter applied
2. `tests/unit/workers/` — 4 new test cases
3. `reports/TC-4231/evidence.md` — claim assignment counts before/after

## Acceptance checks

1. [ ] All tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/ -v`
2. [ ] No page receives > 50 claims, no section > 15 — confirmed by test
3. [ ] Pilot run: factual_accuracy HIGH findings reduced vs baseline

## Self-review

### Verification results
- [x] Tests: 12/12 PASS (new) + 84/84 PASS (planner regression)
- [x] Validation: claim assignment count cap PASS — no page exceeds _MAX_RELEVANCE_CLAIMS_PER_PAGE
- [x] Evidence captured: reports/TC-4231/evidence.md
- [x] Doc freshness: pre-existing test_scout.py failures confirmed independent of this change

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/ -v
```

**Expected results**:
- Relevance filter tests pass
- No regressions in existing planner tests

## Integration boundary proven

**Upstream**: Understand bundle — claims with topic, confidence, page_role_hint
**Downstream**: Generate worker — receives filtered, relevant claim list per section
**Contract**: Each page receives at most 50 claims; each section at most 15; all scored for relevance
