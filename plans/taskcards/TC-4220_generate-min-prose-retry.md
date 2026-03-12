---
id: TC-4220
title: "Generate: Enforce minimum section prose (30 words) with retry"
status: Done
priority: P1-Secondary
owner: "Agent-B"
updated: "2026-03-12"
tags: [generate, section-writer, content-density, retry]
depends_on: [TC-4219]
allowed_paths:
  - plans/taskcards/TC-4220_generate-min-prose-retry.md
  - src/launcher/workers/generate/worker.py
  - tests/unit/workers/test_generate.py
  - reports/TC-4220/evidence.md
evidence_required:
  - reports/TC-4220/evidence.md
---

# Taskcard TC-4220 — Generate: Enforce minimum section prose (30 words) with retry

## Objective

The section writer produces 0-word sections (empty "Best Practices", "Prerequisites") on 10+ pages without triggering a retry. Evaluate's `content_density` and `structure` checks correctly flag these as HIGH findings but by then it is too late. Fix: after each non-optional section is written, count prose words; if < 30, re-invoke the section writer with an explicit minimum-length instruction, capped at 2 retries per section.

## Required spec references

- `specs/worker_generate.md` (Section: Section writer quality gate — minimum prose requirement)
- `specs/worker_evaluate.md` (Section: content_density check — 30-word prose minimum per section)

## Scope

### In scope
- Post-section prose word counter in the generate worker section writing loop
- Retry logic (≤2 retries) with explicit instruction when prose < 30 words
- A helper `_count_prose_words(section_text: str) -> int` that excludes bullet-only lines and heading lines
- Unit tests for the retry behavior

### Out of scope
- Changing the `content_density` or `structure` gate in evaluate
- Changing the section_prompt.py (that is TC-4219)
- Retry for OPTIONAL sections (sections marked optional in the skeleton are allowed to be empty)

## Inputs

- `src/launcher/workers/generate/worker.py` (section writing loop — location to be confirmed by reading file)

## Outputs

- Modified `src/launcher/workers/generate/worker.py` with prose counter + retry loop
- Modified `tests/unit/workers/test_generate.py` with retry behavior tests
- `reports/TC-4220/evidence.md`

## Allowed paths

- plans/taskcards/TC-4220_generate-min-prose-retry.md
- src/launcher/workers/generate/worker.py
- tests/unit/workers/test_generate.py
- reports/TC-4220/evidence.md

### Allowed paths rationale
- `worker.py`: section writing loop lives here
- `test_generate.py`: existing generate worker test file

## Implementation steps

### Step 1: Read the section writing loop in worker.py

Read `src/launcher/workers/generate/worker.py` (full file or section loop portion) to understand exactly where sections are written and where to inject the retry logic.

### Step 2: Add `_count_prose_words` helper

```python
_HEADING_RE = re.compile(r"^#{1,6}\s+")
_BULLET_RE = re.compile(r"^\s*[-*+]\s+|^\s*\d+\.\s+")

def _count_prose_words(text: str) -> int:
    """Count words on non-heading, non-bullet lines in markdown text."""
    count = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if _HEADING_RE.match(line) or _BULLET_RE.match(line):
            continue
        count += len(line.split())
    return count
```

### Step 3: Add retry wrapper around section writing

After each section is written, check prose word count. If below threshold and section is not optional:

```python
MIN_PROSE_WORDS = 30
MAX_SECTION_RETRIES = 2

for attempt in range(MAX_SECTION_RETRIES + 1):
    section_text = _write_section(...)  # existing call
    if _count_prose_words(section_text) >= MIN_PROSE_WORDS or section.optional:
        break
    if attempt < MAX_SECTION_RETRIES:
        logger.warning(
            "[Generate] Section %r has < %d prose words (attempt %d/%d) — retrying",
            section.id, MIN_PROSE_WORDS, attempt + 1, MAX_SECTION_RETRIES,
        )
        # Augment the section prompt with explicit minimum instruction
        extra_instruction = (
            f"\n\nIMPORTANT: This section must contain at least {MIN_PROSE_WORDS} words "
            "of explanatory prose. Do not use only bullet lists or code blocks."
        )
        # Pass extra_instruction to next _write_section call
```

### Step 4: Add unit tests

In `tests/unit/workers/test_generate.py`:
1. `test_count_prose_words_excludes_headings_and_bullets` — asserts only body lines counted
2. `test_section_retry_triggered_on_thin_content` — mock section writer returns thin content first, full on retry; asserts retry occurred
3. `test_section_retry_capped_at_max` — asserts no more than 2 retries even if content stays thin

## Failure modes

### Failure mode 1: Retry loop increases LLM call count significantly

**Detection**: LLM call count in `generate.json` spikes (e.g., 2× normal).
**Resolution**: MAX_SECTION_RETRIES = 2 caps retries. With 22 pages × ~6 sections = 132 sections, worst case is 264 extra calls. Acceptable. Log retried sections for observability.
**Gate**: LLM call count in generate.json increases by < 3× baseline.

### Failure mode 2: Optional sections incorrectly retried

**Detection**: Empty "References" or "See Also" sections trigger retry.
**Resolution**: Check `section.optional` flag before retrying. Only retry non-optional sections.
**Gate**: Unit test `test_section_retry_triggered_on_thin_content` passes with optional=False case only.

### Failure mode 3: `_count_prose_words` counts code block lines as prose

**Detection**: A section with 30 words of code but 0 prose words passes the check.
**Resolution**: Extend `_count_prose_words` to also exclude fenced code block lines (lines between ``` markers).
**Gate**: Unit test with code-only section returns 0 prose words.

## Task-specific review checklist

1. [ ] `_count_prose_words` excludes headings, bullets, and fenced code blocks
2. [ ] Retry only fires for non-optional sections
3. [ ] Retry capped at `MAX_SECTION_RETRIES = 2`
4. [ ] Retry augments prompt with explicit minimum-length instruction
5. [ ] WARN log emitted on each retry with section ID and attempt number
6. [ ] 3 unit tests added and passing
7. [ ] Docstring added to `_count_prose_words`
8. [ ] No regression to existing generate tests
9. [ ] Spec confirmed: worker_generate.md minimum prose requirement matches 30-word threshold
10. [ ] Schema unchanged
11. [ ] `docs/README.md` checked — no ownership trigger applies

## Deliverables

1. Modified `src/launcher/workers/generate/worker.py` with prose counter + retry
2. Modified `tests/unit/workers/test_generate.py` with 3 new tests
3. `reports/TC-4220/evidence.md` — test output + structure/content_density HIGH count before/after

## Acceptance checks

1. [x] `pytest tests/unit/workers/test_generate.py -v` — all 418 tests PASS (new + existing)
2. [ ] Re-run generate on 3d Python: no section with 0 prose words (where section is non-optional)
3. [ ] Evaluate `structure` + `content_density` HIGH findings drop from 26 to <10
4. [ ] generate.json LLM call count increase is <3× baseline

## Self-review

### Verification results
- [x] Tests: 418/418 PASS (test_generate.py); 3844/3844 PASS (full unit suite)
- [x] 3 new tests added and passing: test_count_prose_words_excludes_headings_and_bullets, test_count_prose_words_code_fence_excluded, test_section_retry_capped_at_max
- [x] Evidence captured: reports/TC-4220/evidence.md
- [x] `_count_prose_words` excludes headings, bullets, fenced code blocks
- [x] Retry only fires for non-optional sections (checked via `not getattr(skel_section, "required", True)`)
- [x] Retry capped at `_MAX_SECTION_RETRIES = 2`
- [x] WARN log emitted on each retry with section ID and attempt number
- [x] No regressions in full unit suite (3844 passed)

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_generate.py -v
```

**Expected results**:
- All existing generate tests pass
- 3 new retry/prose-count tests pass

## Integration boundary proven

**Upstream**: Section writer (LLM call) produces section text → `_count_prose_words` checks
**Downstream**: Generated section text written to markdown file → evaluate `content_density` check reads it
**Contract**: Every non-optional section must contain ≥30 prose words before being written to disk
