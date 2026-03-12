---
id: TC-4080
title: "Add per-file snippet extraction logging for Python README"
status: Done
priority: Normal
owner: agent
updated: "2026-03-11"
tags: [phase3, understand, python, snippets]
depends_on: [TC-4079]
allowed_paths:
  - plans/taskcards/TC-4080_snippet_extraction_logging.md
  - src/launcher/workers/understand/extract/_snippets.py
  - tests/unit/workers/understand/test_python_hardening.py
evidence_required:
  - reports/TC-4080/evidence.md
---

# Taskcard TC-4080 — Add per-file snippet extraction logging for Python README

## Objective

`_extract_snippets` currently only logs total extracted count. Adding per-file
logging (blocks found, validated, skipped) makes failures diagnosable from run
logs without reading code.

## Allowed paths

- plans/taskcards/TC-4080_snippet_extraction_logging.md
- src/launcher/workers/understand/extract/_snippets.py
- tests/unit/workers/understand/test_python_hardening.py

## Implementation steps

### Step 1: Add per-file log in `_extract_snippets`

After `blocks = _extract_fenced_code_blocks(content)`, log:
```python
logger.debug("[Snippets] %s: %d fenced blocks found", rel_path, len(blocks))
```

After each validation decision (skip invalid, skip heading, skip dedup), add debug logs.

After processing a file, log summary:
```python
logger.info("[Snippets] %s: %d blocks found, %d added", rel_path, len(blocks), added_for_file)
```

## Failure modes

### Failure mode 1: Zero blocks in README despite having code
**Detection**: Log shows 0 blocks for README.md
**Resolution**: Check regex — `_extract_fenced_code_blocks` regex may not match
**Gate**: Snippet extraction

### Failure mode 2: All blocks fail validation
**Detection**: Log shows blocks found but 0 added
**Resolution**: Check `_validate_python_syntax` — AST parse failures indicate wrong language tag
**Gate**: Snippet extraction

### Failure mode 3: All blocks are heading-only
**Detection**: Log shows "heading-only" for all
**Resolution**: Code blocks in docs contain only headings — expected for sparse repos
**Gate**: Snippet extraction (not blocking)

## Task-specific review checklist

1. [ ] Per-file log at INFO level for README.md
2. [ ] Per-file log at DEBUG level for other files
3. [ ] Reason for each skip is logged at DEBUG
4. [ ] Total summary unchanged (already exists)
5. [ ] No performance impact from logging
6. [ ] Docstrings updated
7. [ ] Spec confirmed — no drift
8. [ ] Schema descriptions present

## Acceptance checks

1. [ ] `test_readme_fenced_blocks_extracted` passes
2. [ ] `test_fenced_block_without_language_tag_extracted_for_python_repo` passes
3. [ ] Log output shows per-file counts

## E2E verification

```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_python_hardening.py -v
```
