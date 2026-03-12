---
id: TC-3887
title: "Fix missing code block language tags in generate worker post-processing"
status: In-Progress
priority: High
owner: "agent"
updated: "2026-03-09"
tags: [generate, code_correctness, language_tags, post_processing]
depends_on: [TC-3885]
allowed_paths:
  - plans/taskcards/TC-3887_fix_missing_code_block_language_tags.md
  - src/launcher/workers/generate/worker.py
  - tests/unit/workers/generate/
evidence_required:
  - reports/TC-3887/evidence.md
---

# Taskcard TC-3887 — Fix missing code block language tags

## Objective

The LLM reviewer generates `code_correctness HIGH` findings for code blocks that lack
language tags (e.g., bare ` ``` ` instead of ` ```python `). Six such findings appear
across `load-spreadsheets-python`, `save-spreadsheets-python`, `convert-spreadsheets-python`,
and `fix-spreadsheets-errors-python` pages.

Root cause: when the section writer LLM generates code blocks, it sometimes omits the
language identifier in the `language` field of the code block IR. The IR renderer then
produces bare ` ``` ` fences.

Fix: in `_generate_section` post-processing, after all passes (enforce_block_spec, fallback),
scan code blocks and set `language = "python"` on any code block where `language` is falsy.
Shell/installation blocks can be detected by content starting with `pip install` and should
use `language = "bash"` instead.

## Required spec references

- `specs/05_generate_worker.md` (section generation pipeline, IR format)

## Scope

### In scope
- Add code block language normalization in `_generate_section` after the final commercial URL strip (TC-3883)
- Default empty `language` to `"python"` unless content suggests shell (`pip`, `npm`, `apt`, `brew`, etc.)

### Out of scope
- Changing the LLM prompts for code generation
- Fixing hallucinated API method names (separate quality issue)
- Any other workers

## Inputs

- `src/launcher/workers/generate/worker.py` — `_generate_section`, block list processing

## Outputs

- Generate worker with language tag normalization post-processing

## Allowed paths

- plans/taskcards/TC-3887_fix_missing_code_block_language_tags.md
- src/launcher/workers/generate/worker.py
- tests/unit/workers/generate/

### Allowed paths rationale
- worker.py — post-processing step added after enforce_block_spec

## Implementation steps

### Step 1: Add language tag normalization function

In `worker.py`, add a function `_normalize_code_languages(blocks)` that:
1. Iterates code blocks (type=="code")
2. If `language` is falsy ("", None):
   - If content starts with `pip ` or `npm ` or `apt ` or `brew ` → `language = "bash"`
   - Otherwise → `language = "python"`
3. Returns updated blocks (model_copy where needed)

### Step 2: Apply after final commercial URL strip in `_generate_section`

After the TC-3883 commercial URL strip:
```python
# Final commercial URL strip — catches pass2 retry blocks and fallback paths (TC-3883)
final_blocks = _strip_commercial_urls(list(section_ir.blocks))
if final_blocks != list(section_ir.blocks):
    section_ir = section_ir.model_copy(update={"blocks": final_blocks})

# Normalize missing code block language tags (TC-3887)
normalized_blocks = _normalize_code_languages(list(section_ir.blocks))
if normalized_blocks != list(section_ir.blocks):
    section_ir = section_ir.model_copy(update={"blocks": normalized_blocks})
```

### Step 3: Add tests

In `tests/unit/workers/generate/`, add tests:
- Empty language → defaults to "python"
- `pip install` content → defaults to "bash"
- Already-set language → unchanged

## Failure modes

### Failure mode 1: Bash content incorrectly tagged as python

**Detection**: A bash snippet with `pip install` gets language=bash, but other bash
commands without pip/npm don't get detected
**Resolution**: Accept as good enough; the key false positives were pip install blocks
tagged as python
**Gate**: Pilot run code_correctness findings

### Failure mode 2: model_copy fails on block type

**Detection**: AttributeError in normalize step
**Resolution**: BlockIR is a pydantic model — model_copy works; verify in tests
**Gate**: Unit tests

### Failure mode 3: Empty content blocks incorrectly normalized

**Detection**: Empty code blocks get language=python
**Resolution**: Only normalize if `content.strip()` is non-empty
**Gate**: Unit tests

## Task-specific review checklist

1. [ ] `_normalize_code_languages` function implemented
2. [ ] Empty language defaults to "python"
3. [ ] pip/npm/apt/brew content defaults to "bash"
4. [ ] Already-set language not overwritten
5. [ ] Applied after TC-3883 strip in `_generate_section`
6. [ ] Unit tests cover all three cases
7. [ ] Tests pass

## Deliverables

1. `src/launcher/workers/generate/worker.py` — language normalization post-processing

## Acceptance checks

1. [ ] Pilot run shows 0 `code_correctness HIGH` findings for "missing language tag"
2. [ ] Shell install commands tagged as `bash` or `shell`
3. [ ] Python code blocks tagged as `python`
4. [ ] All unit tests pass

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-3887/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ -v
```

## Integration boundary proven

**Upstream**: section_writer LLM generates code blocks (may omit language)
**Downstream**: IR renderer produces markdown; LLM reviewer checks language tags
**Contract**: All code blocks have non-empty language field before render
