---
id: TC-4230
title: "G-4: Cap claim injection per section (max 20)"
status: Done
priority: High
owner: "Agent-B"
updated: "2026-03-12"
tags: [generate, claims, token-budget, section-prompt]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4230_generate-cap-claims-per-section.md
  - src/launcher/workers/generate/worker.py
  - src/launcher/workers/generate/section_prompt.py
  - tests/unit/workers/generate/
evidence_required:
  - reports/TC-4230/evidence.md
---

# Taskcard TC-4230 — G-4: Cap claim injection per section (max 20)

## Objective

Cap the number of claims injected per section call at 20 to prevent token budget overflow (`finish_reason: length`). Sections receiving 50+ claims from an uncapped pipeline exceed the context window, causing truncated responses.

## Required spec references

- `specs/worker_generate.md` (Section: Section prompt construction, token budget)

## Scope

### In scope
- Add `MAX_CLAIMS_PER_SECTION = 20` constant in `section_prompt.py` or `worker.py`
- Apply cap before rendering claims into prompt
- Log at DEBUG level when claims are capped: `f"Capped claims from {original} to {MAX_CLAIMS_PER_SECTION} for section {section_id}"`
- Unit tests for cap behavior

### Out of scope
- Changes to claim relevance scoring (TC-4231 scope)
- Changes to page-level claim counts (TC-4231 scope)

## Inputs

- `src/launcher/workers/generate/section_prompt.py` — claim injection site
- `src/launcher/workers/generate/worker.py` — section generation orchestration

## Outputs

- Modified `section_prompt.py` — claim cap applied
- Updated tests in `tests/unit/workers/generate/`

## Allowed paths

- plans/taskcards/TC-4230_generate-cap-claims-per-section.md
- src/launcher/workers/generate/worker.py
- src/launcher/workers/generate/section_prompt.py
- tests/unit/workers/generate/

### Allowed paths rationale
Claim injection happens in section_prompt.py; cap logic belongs there. worker.py may need updating if it passes claims directly.

## Implementation steps

### Step 1: Read section_prompt.py to find claim injection

Locate where claims are rendered into the section prompt string.

### Step 2: Add cap

```python
MAX_CLAIMS_PER_SECTION = 20

def build_section_prompt(section, claims, ...):
    original_count = len(claims)
    if len(claims) > MAX_CLAIMS_PER_SECTION:
        claims = claims[:MAX_CLAIMS_PER_SECTION]
        logger.debug(f"Capped claims from {original_count} to {MAX_CLAIMS_PER_SECTION} for section {section.id}")
    # ... rest of prompt construction
```

### Step 3: Write unit tests

Add tests covering:
1. 25 claims provided — only 20 injected, log message emitted
2. 15 claims provided — all 15 injected, no cap log
3. 0 claims provided — no crash, empty claims section in prompt

### Step 4: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ -v -q
```

## Failure modes

### Failure mode 1: Cap removes highest-value claims

**Detection**: Capped sections have lower factual_accuracy scores because top claims were not the first 20.
**Resolution**: Before capping, sort claims by confidence DESC so the highest-confidence claims are kept. Apply `claims = sorted(claims, key=lambda c: c.confidence, reverse=True)[:MAX_CLAIMS_PER_SECTION]`.
**Gate**: Evaluate factual_accuracy findings

### Failure mode 2: Cap too low for complex reference pages

**Detection**: Reference pages with many API methods have incomplete documentation.
**Resolution**: Allow per-role override: `MAX_CLAIMS_PER_SECTION_REFERENCE = 30` for reference/api_reference roles.
**Gate**: Content review A+B rate for reference pages

### Failure mode 3: finish_reason: length persists after cap

**Detection**: Log still shows `finish_reason: length` after fix.
**Resolution**: The overflow may be from other prompt components (snippets, instructions). Reduce claim cap further to 15, or reduce snippet count.
**Gate**: LLM response finish_reason field

## Task-specific review checklist

1. [ ] `MAX_CLAIMS_PER_SECTION = 20` constant defined at module level
2. [ ] Claims sorted by confidence DESC before cap is applied
3. [ ] Debug log emitted when cap is triggered
4. [ ] Cap applied before prompt rendering, not after
5. [ ] Unit test: 25 claims → 20 injected, log emitted
6. [ ] Unit test: 15 claims → 15 injected, no cap log
7. [ ] Docstrings updated for `build_section_prompt`
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields not applicable (no schema change)
10. [ ] Checked `docs/README.md` ownership map — trigger event check done
11. [ ] No new docs/guides/ file added

## Deliverables

1. `src/launcher/workers/generate/section_prompt.py` — claim cap applied
2. `tests/unit/workers/generate/` — 3 new test cases
3. `reports/TC-4230/evidence.md` — log showing zero finish_reason:length events

## Acceptance checks

1. [ ] All tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ -v`
2. [ ] No section receives more than 20 claims — confirmed by debug log
3. [ ] Pilot run: zero `finish_reason: length` events in log

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: claim cap behavior PASS
- [ ] Evidence captured: reports/TC-4230/evidence.md
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --uncommitted` — clean / acknowledged

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ -v
```

**Expected results**:
- Claim cap tests pass
- No regressions in existing generate tests

## Integration boundary proven

**Upstream**: Planner — assigns claims to sections (may assign 50+)
**Downstream**: LLM section writer — receives capped claim list within token budget
**Contract**: Maximum 20 claims per section prompt (sorted by confidence DESC)
