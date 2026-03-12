---
id: TC-3878
title: "Wave 2: Golden Corpus Mandatory Reference + Code Block Completeness"
status: In-Progress
priority: High
owner: "Agent-B"
updated: "2026-03-09"
tags: [wave-2, golden, code-blocks, reference-completeness]
depends_on: [TC-3876]
allowed_paths:
  - plans/taskcards/TC-3878_w2_golden_mandatory_code_blocks.md
  - src/launcher/workers/generate/worker.py
  - src/launcher/shared/golden_loader.py
  - src/launcher/workers/generate/section_prompt.py
  - tests/generate/test_worker.py
  - tests/shared/test_golden_loader.py
  - reports/TC-3878/evidence.md
evidence_required:
  - reports/TC-3878/evidence.md
---

# Taskcard TC-3878 — Wave 2: Golden Corpus Mandatory + Code Block Completeness

## Objective

Two generation quality improvements that eliminate reference_completeness HIGH findings:
1. W2-S6: Change golden corpus from optional to required — add `get_nearest_golden`
   fallback chain so every section always has a golden reference
2. W2-S7: Improve `_gap_fill_code_block` to use extracted snippets verbatim when available

## Required spec references

- `specs/worker_generate.md` (Section: golden reference, code block enforcement)
- `specs/claims_evidence.md` (Section: snippet source_type)

## Scope

### In scope
- W2-S6: Add `get_nearest_golden(page_role, variant, golden_dir)` to `golden_loader.py`
  with 3-level fallback: exact → role-only → generic
- W2-S6: In `build_section_prompt` or worker.py: call `get_nearest_golden` when no
  exact match found, ensuring every section has some golden reference
- W2-S7: In `worker.py` `_gap_fill_code_block`: prefer first extracted snippet's `code`
  verbatim over generated fallback; add ENFORCEMENT OVERRIDE to Pass 2 retry

### Out of scope
- Golden corpus file creation (TC-3880)
- Quality-annotated golden frontmatter (TC-3880)
- Per-section gate (TC-3877)

## Inputs

- `src/launcher/shared/golden_loader.py` — `GoldenIndex`, `_load_golden_for_role`
- `src/launcher/workers/generate/worker.py` — `_gap_fill_code_block`
- `src/launcher/workers/generate/section_prompt.py` — `build_section_prompt`, `golden_dir`

## Outputs

- Updated `src/launcher/shared/golden_loader.py`
- Updated `src/launcher/workers/generate/worker.py`
- `reports/TC-3878/evidence.md`

## Allowed paths

- plans/taskcards/TC-3878_w2_golden_mandatory_code_blocks.md
- src/launcher/workers/generate/worker.py
- src/launcher/shared/golden_loader.py
- src/launcher/workers/generate/section_prompt.py
- tests/generate/test_worker.py
- tests/shared/test_golden_loader.py
- reports/TC-3878/evidence.md

## Implementation steps

### Step 1: Read golden_loader.py and worker.py

Read `golden_loader.py` fully — understand `GoldenIndex.load`, `_load_golden_for_role`,
and how page_role + section_heading matching works.
Read worker.py — find `_gap_fill_code_block` and how `golden_dir` is passed to
`build_section_prompt`.

### Step 2: W2-S6 — Add get_nearest_golden to golden_loader.py

Add to `golden_loader.py`:
```python
def get_nearest_golden(
    page_role: str,
    section_heading: str,
    golden_dir: "Path | None",
    *,
    variant: str = "standard",
) -> str:
    """Return best available golden excerpt using 3-level fallback.

    Level 1: Exact match (page_role, section_heading, variant)
    Level 2: Same page_role, any section (nearest heading by prefix match)
    Level 3: Any golden file with a matching section type keyword

    Returns empty string if golden_dir is None or no golden files exist.
    """
    if golden_dir is None:
        return ""
    try:
        # Level 1: exact
        excerpt = _load_golden_for_role(page_role, golden_dir, section_heading, variant=variant)
        if excerpt:
            return excerpt
        # Level 2: same role, any section heading
        excerpt = _load_golden_for_role(page_role, golden_dir, "", variant=variant)
        if excerpt:
            return excerpt
        # Level 3: any golden file with overview/introduction section
        excerpt = _load_golden_for_role("", golden_dir, "overview", variant=variant)
        if excerpt:
            return excerpt
    except Exception:
        pass
    return ""
```

### Step 3: W2-S7 — Improve _gap_fill_code_block in worker.py

Find `_gap_fill_code_block` in worker.py. Modify to:
1. If `section_snippets` non-empty AND any have `source_type == "extracted"`: use first
   extracted snippet's `code` verbatim (already validated real code)
2. If `public_classes` non-empty: generate `import {canonical_import}` + `{class_name}()`
3. Add ENFORCEMENT OVERRIDE to Pass 2 retry prompt:
   "ENFORCEMENT OVERRIDE — MISSING CODE BLOCK: Include a complete {lang_tag} code
   block using {canonical_import}. No placeholder text. No comment-only blocks."

### Step 4: Tests

Add or update tests:
- `get_nearest_golden` returns empty string when golden_dir is None
- `get_nearest_golden` falls back to role-only match when no exact section match
- `_gap_fill_code_block` uses extracted snippet when available

### Step 5: Run full test suite

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --tb=short 2>&1 | tail -10
```
Baseline: 3118. Must not drop.

## Failure modes

### Failure mode 1: get_nearest_golden falls back to unrelated golden and confuses LLM
**Detection**: LLM generates wrong structure because golden is wrong page_role
**Resolution**: Level 3 fallback uses only "overview" section (most generic); add
note in prompt: "this is a structural reference only — adapt to your page_role"
**Gate**: Test confirms fallback returns content without crashing

### Failure mode 2: _gap_fill_code_block using extracted snippet adds duplicate code
**Detection**: Page has same code block twice (from section generation + gap fill)
**Resolution**: Only call `_gap_fill_code_block` when section has zero code blocks
(guard already exists — verify it's working)
**Gate**: Test confirms gap fill only triggers on zero-code sections

### Failure mode 3: golden_loader refactoring breaks existing GoldenIndex tests
**Detection**: Tests in tests/shared/test_golden_loader.py fail
**Resolution**: Add `get_nearest_golden` as a new standalone function; do NOT
modify existing `_load_golden_for_role` signature
**Gate**: All 3118+ tests pass

## Task-specific review checklist

1. [ ] `get_nearest_golden` added to golden_loader.py with 3-level fallback
2. [ ] Fallback never raises exception (try/except wraps all levels)
3. [ ] `_gap_fill_code_block` uses extracted snippet first (when available)
4. [ ] ENFORCEMENT OVERRIDE added to Pass 2 retry for missing code blocks
5. [ ] Tests added for `get_nearest_golden` fallback chain
6. [ ] Tests added for improved gap fill behavior
7. [ ] Docstrings updated

## Deliverables

1. Updated `src/launcher/shared/golden_loader.py`
2. Updated `src/launcher/workers/generate/worker.py`
3. `reports/TC-3878/evidence.md`

## Acceptance checks

1. [ ] `get_nearest_golden` returns content via fallback when no exact match
2. [ ] `_gap_fill_code_block` uses extracted snippet verbatim when available
3. [ ] All 3118+ tests pass

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --tb=short
```
