---
id: TC-421
title: "W3.1 Snippet inventory and tagging"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
depends_on:
  - TC-400
allowed_paths:
  - src/launch/workers/w3_snippet_curator/inventory.py
  - src/launch/adapters/snippet_tagger.py
  - tests/unit/workers/test_tc_421_snippet_inventory.py
  - reports/agents/**/TC-421/**
evidence_required:
  - reports/agents/<agent>/TC-421/report.md
  - reports/agents/<agent>/TC-421/self_review.md
---

# Taskcard TC-421 — W3.1 Snippet inventory and tagging

## Objective
Generate `snippet_catalog.json` by discovering snippets/examples deterministically and tagging them for later selection.

## Required spec references
- specs/05_example_curation.md
- specs/26_repo_adapters_and_variability.md
- specs/27_universal_repo_handling.md
- specs/10_determinism_and_caching.md
- specs/schemas/snippet_catalog.schema.json
- specs/schemas/issue.schema.json

## Scope
### In scope
- Deterministic discovery of snippet candidates (examples/, samples/, docs code blocks, etc.)
- Tagging rules:
  - language
  - feature area
  - requires_assets (yes/no)
  - runnable (yes/no)
- Stable ordering and stable IDs

### Out of scope
- Selecting snippets for specific pages (TC-422)
- Running snippets (validator optional gate)

## Inputs
- `RUN_DIR/work/repo` + repo profile/adapters
- Optional repo_hints.preferred_examples_roots

## Outputs
- `RUN_DIR/artifacts/snippet_catalog.json` (schema-valid)
- Issues for:
  - unreadable/unsupported files
  - ambiguous language detection

## Allowed paths
- src/launch/workers/w3_snippet_curator/inventory.py
- src/launch/adapters/snippet_tagger.py
- tests/unit/workers/test_tc_421_snippet_inventory.py
- reports/agents/**/TC-421/**
## Implementation steps
1) Enumerate candidate paths deterministically (sorted).
2) Extract code blocks/snippet files, normalize line endings, and classify language.
3) Generate stable snippet IDs (hash of normalized content + source locator).
4) Tag snippets using deterministic heuristics; record unknown tags explicitly.
5) Validate schema and write artifact atomically.
6) Tests:
   - stable ID generation test
   - deterministic ordering test

## Deliverables
- Code:
  - snippet inventory + tagging
- Tests:
  - determinism tests
- Reports (required):
  - reports/agents/<agent>/TC-421/report.md
  - reports/agents/<agent>/TC-421/self_review.md

## Acceptance checks
- [ ] snippet_catalog validates against schema
- [ ] snippet IDs stable across runs
- [ ] tagging is deterministic and documented
- [ ] Tests passing

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
