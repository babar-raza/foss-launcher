---
id: TC-3791
title: "TreeSitter integration — cross-cutting fixes for multi-platform parity"
status: In-Progress
priority: High
owner: "agent-B"
updated: "2026-03-07"
tags: [multi-platform, tree-sitter, understand]
depends_on: [TC-3790]
allowed_paths:
  - plans/taskcards/TC-3791_treesitter_integration.md
  - src/launcher/workers/understand/extract.py
  - src/launcher/workers/understand/worker.py
  - src/launcher/workers/understand/file_classifier.py
  - src/launcher/workers/generate/section_validator.py
evidence_required:
  - reports/agents/B/TC-3791/evidence.md
---

# Taskcard TC-3791 — TreeSitter Integration (Cross-Cutting)

## Objective

Integrate TreeSitterAnalyzer into the understand pipeline: fix hardcoded
language="python" defaults, extend snippet validation to all languages,
and enable multi-language standalone file extraction.

## Required spec references

- `specs/worker_understand.md` (Phase B: snippet validation)

## Scope

### In scope
- Fix hardcoded language="python" in extract.py standalone file extraction
- Extend fenced code block validation to all languages via TreeSitterAnalyzer
- Extend worker.py self-review snippet check to all languages
- Extend standalone file extraction beyond *.py

### Out of scope
- Changes to ts_analyzer.py itself (TC-3790)
- Manifest parsing expansion (TC-3794)

## Inputs
- TreeSitterAnalyzer from TC-3790
- Source files in any language

## Outputs
- Multi-language snippet validation in extract.py
- Multi-language self-review in worker.py
- Language-correct snippet tagging

## Allowed paths
- plans/taskcards/TC-3791_treesitter_integration.md
- src/launcher/workers/understand/extract.py
- src/launcher/workers/understand/worker.py
- src/launcher/workers/understand/file_classifier.py
- src/launcher/workers/generate/section_validator.py

## Implementation steps

### Step 1: Fix extract.py fenced code block validation
Add TreeSitterAnalyzer.validate_snippet() for non-Python languages.

### Step 2: Fix extract.py standalone file extraction
Extend beyond *.py to all source extensions. Use file_classifier for language detection.
Fix hardcoded language="python".

### Step 3: Fix worker.py self-review
Add TreeSitterAnalyzer.validate_snippet() for non-Python snippets.

## Failure modes

### Failure mode 1: TreeSitter not installed
**Detection**: ImportError
**Resolution**: Fall back to existing behavior (skip validation)
**Gate**: Graceful degradation

### Failure mode 2: Breaking existing Python validation
**Detection**: Test failures in test_understand.py
**Resolution**: Keep ast.parse() for Python, only add tree-sitter for others
**Gate**: Python path unchanged

### Failure mode 3: Language detection mismatch
**Detection**: Wrong language tag on snippets
**Resolution**: Use file_classifier.LANG_BY_EXT consistently
**Gate**: Unit tests verify correct language tags

## Task-specific review checklist

1. [ ] Non-Python fenced blocks validated via TreeSitterAnalyzer
2. [ ] Standalone files beyond *.py extracted with correct language
3. [ ] Self-review checks all languages
4. [ ] Python path unchanged (ast.parse still used)
5. [ ] Import normalization dispatches to ts_analyzer for non-Python
6. [ ] All existing tests pass

## Acceptance checks

1. [ ] PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x -- 0 failures
