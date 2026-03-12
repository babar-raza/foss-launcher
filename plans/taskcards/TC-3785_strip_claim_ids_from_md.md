---
id: TC-3785
title: "Strip claim ID citations from rendered markdown content"
status: Done
priority: Critical
owner: agent
updated: "2026-03-07"
tags: [content-quality, generate, P0]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3785_strip_claim_ids_from_md.md
  - src/launcher/workers/generate/section_validator.py
  - tests/unit/workers/test_generate.py
evidence_required:
  - reports/TC-3785/evidence.md
---

# Taskcard TC-3785 — Strip claim ID citations from rendered markdown content

## Objective

Remove claim ID citations (`[CLM-xxx]`, `[CLM-xxx, CLM-yyy]`) from prose content in BlockIR blocks. Claim IDs must only exist in the structured `claim_ids` array, never in the rendered `content` field. Currently 47 occurrences leak into 10+ `.md` output files.

## Required spec references

- `specs/system_overview.md` (Rule 0: publication-ready content)
- `specs/worker_generate.md` (BlockIR output format)

## Scope

### In scope
- Add `_strip_claim_citations()` to section_validator.py
- Apply stripping to paragraph, heading, table, callout, and list block content
- Unit tests for the new function
- Verify existing `_strip_claim_comments` still handles code blocks

### Out of scope
- Prompt changes to prevent LLM from emitting citations (future TC)
- ir_renderer.py changes (not needed — fix at validation time)
- Re-running pilots (separate step)

## Inputs

- Raw LLM response JSON blocks with content containing `[CLM-xxx]` citations
- Existing `_strip_claim_comments` for code blocks

## Outputs

- Clean BlockIR content fields with no claim ID citations
- Structured `claim_ids` arrays remain intact

## Allowed paths

- `plans/taskcards/TC-3785_strip_claim_ids_from_md.md` — this taskcard
- `src/launcher/workers/generate/section_validator.py` — add stripping function
- `tests/unit/workers/test_generate.py` — add tests

### Allowed paths rationale
- section_validator.py: Root cause — LLM output validation/normalization point
- test_generate.py: Existing test file for generate worker components

## Implementation steps

### Step 1: Add `_strip_claim_citations` function

Add after `_strip_claim_comments` (~line 101) in section_validator.py:
```python
def _strip_claim_citations(text: str) -> str:
    """Remove bracket-format claim citations like [CLM-xxx, CLM-yyy] from prose."""
    return re.sub(r"\s*\[CLM-[^\]]*\]", "", text)
```

### Step 2: Apply to non-code blocks in `_validate_block`

In `_validate_block`, add `_strip_claim_citations(content)` call for non-code blocks before `_normalize_product_name`.

### Step 3: Apply to list items

Strip citations from list block items as well.

### Step 4: Add unit tests

Add tests to `tests/unit/workers/test_generate.py`:
- Paragraph with trailing citation is cleaned
- Multiple citations in one line are cleaned
- No-op on clean text
- Code blocks are NOT affected (only `_strip_claim_comments` applies)
- List items are cleaned

## Failure modes

### Failure mode 1: Regex strips legitimate bracket content

**Detection**: Content like `[see documentation]` is incorrectly removed
**Resolution**: Pattern anchors on `CLM-` prefix — only `[CLM-...]` is matched
**Gate**: Unit test verifies non-CLM brackets are preserved

### Failure mode 2: Citation in middle of sentence leaves double space

**Detection**: "text [CLM-xxx] more text" becomes "text  more text"
**Resolution**: The `\s*` prefix handles leading whitespace; post-strip normalize double spaces if needed
**Gate**: Unit test covers mid-sentence case

### Failure mode 3: Existing tests break

**Detection**: `pytest` failures
**Resolution**: Review test expectations; the change only affects content with `[CLM-` patterns
**Gate**: Full test suite must pass

## Task-specific review checklist

1. [ ] `_strip_claim_citations` removes `[CLM-xxx]` from paragraph content
2. [ ] `_strip_claim_citations` removes `[CLM-xxx, CLM-yyy]` (multiple IDs)
3. [ ] `_strip_claim_citations` is no-op on clean text
4. [ ] Non-CLM brackets like `[see docs]` are preserved
5. [ ] List items are stripped
6. [ ] Code block content is NOT processed by `_strip_claim_citations`
7. [ ] `claim_ids` array in BlockIR is NOT affected
8. [ ] All existing tests pass

## Deliverables

1. Updated `src/launcher/workers/generate/section_validator.py`
2. Updated `tests/unit/workers/test_generate.py` with new tests
3. Evidence in `reports/TC-3785/evidence.md`

## Acceptance checks

1. [ ] New unit tests pass
2. [ ] All existing tests pass (PYTHONHASHSEED=0)
3. [ ] `grep -r "\[CLM-" *.md` on fresh run output returns 0 matches

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-3785/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_generate.py -v -k "claim_citation"
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Expected results**:
- All new tests pass
- All existing tests pass
- No `[CLM-` patterns in rendered markdown content

## Integration boundary proven

**Upstream**: LLM returns JSON blocks with claim IDs embedded in content
**Downstream**: ir_renderer.py renders `block.content` into `.md` files
**Contract**: After section_validator, `block.content` is free of claim ID citations; `block.claim_ids` retains structured claim references
