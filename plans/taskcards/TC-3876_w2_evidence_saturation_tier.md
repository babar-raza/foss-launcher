---
id: TC-3876
title: "Wave 2: Evidence-Anchored Generation + Claim Saturation + Tier in Prompts"
status: In-Progress
priority: High
owner: "Agent-B"
updated: "2026-03-09"
tags: [wave-2, evidence, saturation, tier, section-prompt]
depends_on: [TC-3871, TC-3875]
allowed_paths:
  - plans/taskcards/TC-3876_w2_evidence_saturation_tier.md
  - src/launcher/workers/generate/section_prompt.py
  - src/launcher/workers/planner/plan.py
  - src/launcher/models/plan.py
  - tests/generate/test_section_prompt.py
  - tests/planner/test_plan.py
  - reports/TC-3876/evidence.md
evidence_required:
  - reports/TC-3876/evidence.md
---

# Taskcard TC-3876 — Wave 2: Evidence Anchoring + Claim Saturation + Tier in Prompts

## Objective

Three generation quality improvements that reduce LLM hallucination and thin-content failures:
1. W2-S2: Pass claim evidence snippets to generation LLM (source-anchored generation)
2. W2-S3: Compute + use `claim_saturation` to guide generation on thin pages
3. W2-S5: Pass richness tier to generation prompts for tier-appropriate word counts

## Required spec references

- `specs/worker_generate.md` (Section: section_prompt, claim context)
- `specs/claims_evidence.md` (Section: EvidenceAnchor, snippet field)

## Scope

### In scope
- W2-S2: In `_format_claims`, emit evidence snippet when non-empty
- W2-S3: Compute `claim_saturation` in planner; inject warning in section prompt
- W2-S5: Pass tier to `build_section_prompt`; use tier-aware word counts
- Tests for all three

### Out of scope
- Per-section quality gate (TC-3877)
- Golden corpus changes (TC-3878)
- Heal loop changes (TC-3879)

## Inputs

- `src/launcher/workers/generate/section_prompt.py` — `_format_claims`, `build_section_prompt`
- `src/launcher/workers/planner/plan.py` — `_assign_claims`, `PlannedPage`
- `src/launcher/models/plan.py` — `PlannedPage` model
- `src/launcher/models/claims.py` — `Claim.evidence`, `EvidenceAnchor` model

## Outputs

- Updated `section_prompt.py`
- Updated `plan.py`
- Updated `models/plan.py`
- `reports/TC-3876/evidence.md`

## Allowed paths

- plans/taskcards/TC-3876_w2_evidence_saturation_tier.md
- src/launcher/workers/generate/section_prompt.py
- src/launcher/workers/planner/plan.py
- src/launcher/models/plan.py
- tests/generate/test_section_prompt.py
- tests/planner/test_plan.py
- reports/TC-3876/evidence.md

## Implementation steps

### Step 1: Read all source files

Read in full:
1. `src/launcher/workers/generate/section_prompt.py` — `_format_claims` and `build_section_prompt`
2. `src/launcher/models/claims.py` — `Claim`, `EvidenceAnchor` model fields
3. `src/launcher/models/plan.py` — `PlannedPage` fields
4. `src/launcher/workers/planner/plan.py` — `_assign_claims` / `_distribute_claims`

### Step 2: W2-S2 — Evidence-anchored generation

In `_format_claims` (or wherever claims are formatted as prompt text), extend claim formatting:
```python
# Before: "- [CLM-id] (kind): claim text"
# After (when evidence available):
# "- [CLM-id] (kind): claim text"
# "  Source: path/to/file.py:42 → `exact source snippet`"

def _format_single_claim(claim) -> str:
    line = f"- [{claim.claim_id}] ({claim.kind}): {claim.text}"
    if claim.evidence and claim.evidence[0].snippet:
        snippet = claim.evidence[0].snippet.strip()[:150]
        src = f"{claim.evidence[0].source_file}:{claim.evidence[0].line_start}"
        if snippet and snippet != claim.text.strip():
            line += f"\n  Source: {src} → `{snippet}`"
    return line
```

IMPORTANT: Check the actual field names on `Claim` and `EvidenceAnchor`. Adapt to what exists.
Guard: only emit evidence when `snippet` is non-empty and distinct from claim text.

### Step 3: W2-S3 — Claim saturation

**models/plan.py**: Add field to `PlannedPage`:
```python
claim_saturation: float = 1.0  # assigned_claims / skeleton_sections; <0.5 = thin
```

**plan.py `_assign_claims`**: After computing assigned claims per page, add:
```python
saturation = len(assigned_claims) / max(1, len(skeleton_sections))
planned_page.claim_saturation = saturation
```

**section_prompt.py `build_section_prompt`**: Check `claim_saturation` from page context:
```python
if getattr(page_context, 'claim_saturation', 1.0) < 0.5:
    prompt_parts.append(
        f"SATURATION WARNING: This page has limited claims ({N} claims for {S} sections). "
        "Write concise factual sections. Do NOT invent capabilities not supported by the claims above."
    )
```

### Step 4: W2-S5 — Tier-aware word counts

**section_prompt.py `build_section_prompt`**: Accept `richness_tier: str = "A"` parameter.
Apply tier-based word count guidance:
```python
_TIER_WORD_COUNTS = {
    "A": (150, 500),  # min, max
    "B": (100, 350),
    "C": (60, 200),
}
min_words, max_words = _TIER_WORD_COUNTS.get(richness_tier, (150, 500))
# Replace existing min_words/max_words in prompt template
# For Tier C, also add preamble:
if richness_tier == "C":
    prompt_parts.insert(0, "EVIDENCE CONSTRAINT: This is a lean repository with limited documentation. Write concise factual sections. Quality over length.")
```

**generate/worker.py**: Pass tier from PlanBundle to `build_section_prompt`.
Find the call site: `build_section_prompt(...)` and add `richness_tier=plan_bundle.richness_tier`.

### Step 5: Tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --tb=short 2>&1 | tail -10
```
Baseline: 3118. Must not drop.

## Failure modes

### Failure mode 1: `claim_saturation` field not available when building section prompt
**Detection**: `AttributeError` at build_section_prompt call
**Resolution**: Use `getattr(page_context, 'claim_saturation', 1.0)` everywhere
**Gate**: Test with page_context missing the field → no error, uses default

### Failure mode 2: Evidence snippet causes prompt token budget overflow
**Detection**: LLM call fails with context length error
**Resolution**: Cap snippet at 150 chars; cap total evidence lines at 3 per claim group;
add `max_evidence_tokens` guard that skips evidence when token estimate > budget
**Gate**: Very large claim sets still generate without token errors

### Failure mode 3: `claim_saturation` model change breaks existing planner tests
**Detection**: `pytest tests/planner/` shows validation error (unexpected field)
**Resolution**: Add `claim_saturation: float = 1.0` as optional field with default
**Gate**: All 3118+ tests pass

## Task-specific review checklist

1. [ ] `_format_claims` emits evidence snippet when non-empty and distinct from claim text
2. [ ] Evidence snippet capped at 150 chars
3. [ ] `claim_saturation` field added to `PlannedPage` with default 1.0
4. [ ] `claim_saturation` computed in `_assign_claims`
5. [ ] Section prompt injects SATURATION WARNING when saturation < 0.5
6. [ ] `build_section_prompt` accepts `richness_tier` parameter
7. [ ] Tier C pages get lower word-count targets and EVIDENCE CONSTRAINT preamble
8. [ ] Docstrings updated
9. [ ] Models updated
10. [ ] evidence.md with test results

## Deliverables

1. Updated `src/launcher/workers/generate/section_prompt.py`
2. Updated `src/launcher/workers/planner/plan.py`
3. Updated `src/launcher/models/plan.py`
4. `reports/TC-3876/evidence.md`

## Acceptance checks

1. [ ] Evidence snippets appear in formatted claim output for claims that have them
2. [ ] `claim_saturation` stored in PlannedPage (confirmed via test)
3. [ ] Tier C page builds with lower word counts (confirmed via test)
4. [ ] All 3118+ tests pass
