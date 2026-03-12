---
id: TC-3873
title: "Post-render deduplication of repeated code blocks within a page"
status: Done
priority: High
owner: "claude-agent"
updated: "2026-03-08"
tags: [generate, repetition, code-blocks, e2e-quality]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3873_code_block_dedup_postrender.md
  - src/launcher/shared/ir_renderer.py
  - tests/unit/shared/test_ir_renderer_dedup.py
evidence_required:
  - reports/TC-3873/evidence.md
---

# Taskcard TC-3873 — Post-render deduplication of repeated code blocks

## Objective

The generate worker builds sections concurrently via `asyncio.gather`. Each concurrent
section independently filters snippets from `page_snippets` by claim_id intersection.
Since multiple sections share claims (via round-robin distribution), the same snippet
can be injected into multiple section prompts. The LLM copies the snippet verbatim into
each section output, resulting in the same code block appearing 2–4 times per page.

The `check_repetition` check flags this as `high`-severity, causing 65 findings across
19 pages in the pilot run. All pages graded D as a result.

## Root Cause

Per-section concurrent snippet selection in `worker.py`:
  ```python
  sec_snippets = [s for s in page_snippets if set(s.claim_ids) & sec_claim_ids]
  ```
Multiple sections with overlapping claim assignments receive identical snippets.
Adding shared state to concurrent coroutines would require locking and is architecturally
complex. The canonical fix is post-render deduplication.

## Required spec references

- `src/launcher/shared/ir_renderer.py` (render_page function)
- `src/launcher/workers/generate/worker.py` (section generation loop)

## Scope

### In scope
- Add `_dedup_code_blocks(markdown: str) -> str` in `ir_renderer.py` that:
  - Extracts all fenced code blocks (```lang\n...\n```)
  - On the SECOND and subsequent occurrences of the same code block content,
    replaces the duplicate with an empty string (removes it entirely)
  - Normalizes whitespace for comparison (strip, collapse internal whitespace)
  - Minimum size threshold: only dedup blocks with ≥3 lines of code
- Call `_dedup_code_blocks` inside `render_page()` after assembling markdown
- Add unit tests in `tests/unit/shared/test_ir_renderer_dedup.py`

### Out of scope
- No changes to the concurrent section generation logic
- No changes to snippet selection in `section_prompt.py`
- No changes to the `check_repetition` check
- Do NOT deduplicate reference page roles (api_reference, reference_object_page)
  where the same example per overload is intentional

## Inputs

- `src/launcher/shared/ir_renderer.py` — current render_page function

## Outputs

- `src/launcher/shared/ir_renderer.py` — render_page calls _dedup_code_blocks
- `tests/unit/shared/test_ir_renderer_dedup.py` — dedup unit tests

## Allowed paths

- `src/launcher/shared/ir_renderer.py`
- `tests/unit/shared/test_ir_renderer_dedup.py`

## Implementation steps

1. Add `_DEDUP_MIN_LINES = 3` constant.
2. Add `_dedup_code_blocks(markdown: str) -> str`:
   - Use `re.finditer` to find all fenced code blocks.
   - For each block, compute a normalized key: `"\n".join(line.strip() for line in code.strip().split("\n"))`.
   - First occurrence: keep it; subsequent occurrences: replace with empty string.
   - Only dedup blocks with code that has at least `_DEDUP_MIN_LINES` lines.
3. In `render_page()`, call `_dedup_code_blocks(markdown)` before returning.
4. Add unit tests covering: exact duplicate blocks removed, distinct blocks kept,
   single-line blocks not deduped (below threshold), reference page role exemption.

## Failure modes

1. Two legitimately different but visually similar code blocks — normalized comparison
   may incorrectly merge them. Threshold of 3 lines reduces this risk; content authors
   can make small intentional differences to preserve both.
2. Code block with trailing whitespace differences — normalized key strips each line,
   so whitespace-only differences are treated as duplicates (correct behavior).
3. Very large pages — regex scan is O(n) in page length, negligible cost.

## Task-specific review checklist

- [ ] `_dedup_code_blocks` removes second/subsequent occurrences of same code block
- [ ] Blocks with fewer than 3 lines are NOT deduped (preserved as-is)
- [ ] Distinct code blocks are preserved unchanged
- [ ] `render_page` calls `_dedup_code_blocks` before returning
- [ ] No changes to reference page generation
- [ ] New unit tests pass
- [ ] Full suite: 2977+ tests, 0 failures

## Deliverables

- Modified `src/launcher/shared/ir_renderer.py`
- New `tests/unit/shared/test_ir_renderer_dedup.py`

## Acceptance checks

- [x] Taskcard created with status In-Progress
- [ ] Code block repetition reduced significantly in E2E pilot
- [ ] `check_repetition` findings drop from 65
- [ ] Full suite passes (PYTHONHASHSEED=0)

## Self-review

_To be filled after implementation._

## E2E verification

Run pilot. Check evaluation_summary.json for repetition finding count.
Expected: repetition findings significantly reduced from 65.

## Integration boundary proven

`_dedup_code_blocks` is called inside `render_page` only. No cross-boundary changes.
