---
id: TC-4087
title: "Doc-scan workflow examples for non-Python repos"
status: Done
priority: Normal
owner: agent
updated: "2026-03-11"
tags: [phase4, understand, multi_platform, workflow_examples]
depends_on: [TC-4084]
allowed_paths:
  - plans/taskcards/TC-4087_non_python_workflow_examples.md
  - src/launcher/workers/understand/extract/_deterministic.py
evidence_required:
  - reports/TC-4087/evidence.md
---

# Taskcard TC-4087 — Doc-scan workflow examples for non-Python repos

## Objective

`extract_workflow_examples()` currently only mines Python AST for workflow examples.
Non-Python repos get 0 examples. Add a doc-scan strategy for ordered lists and source
file examples (by line count, not AST) so non-Python repos get at least basic coverage.

## Allowed paths

- plans/taskcards/TC-4087_non_python_workflow_examples.md
- src/launcher/workers/understand/extract/_deterministic.py

## Implementation steps

### Step 1: Add doc-scan in `extract_workflow_examples`

When platform is non-Python (or Python fallback doesn't find anything), scan docs:
- README.md and docs/*.md for ordered lists ("1. ...", "2. ...", "3. ...")
  that look like workflow steps (≥ 3 steps with ≥ 30 chars each)
- Example source files by extension (.ts, .java, .cs, .go, .rs) if they exist
  and have ≥ 3 lines and ≤ 100 lines (line-count heuristic, not AST)

## Task-specific review checklist

1. [ ] Doc-scan fires for non-Python repos with ordered lists
2. [ ] Minimum 3 steps required for ordered list to count
3. [ ] Source file heuristic limits to ≤ 100 lines to avoid huge files
4. [ ] No performance regression for Python repos
5. [ ] Docstrings updated
6. [ ] Spec confirmed — no drift

## Acceptance checks

1. [ ] Non-Python fixture with ordered list doc produces ≥ 1 workflow example
2. [ ] Python extraction path unchanged
