---
id: TC-420
title: "W3 SnippetCurator (snippet_catalog.json)"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
depends_on:
  - TC-421
  - TC-422
allowed_paths:
  - src/launch/workers/w3_snippet_curator/__init__.py
  - src/launch/workers/_snippets/__init__.py
  - tests/integration/test_tc_420_w3_integration.py
  - reports/agents/**/TC-420/**
evidence_required:
  - reports/agents/<agent>/TC-420/report.md
  - reports/agents/<agent>/TC-420/self_review.md
---

# Taskcard TC-420 — W3 SnippetCurator (snippet_catalog.json)

## Objective
Implement **W3: SnippetCurator** to extract, normalize, and tag reusable code snippets with deterministic IDs and provenance.

## Required spec references
- specs/21_worker_contracts.md (W3)
- specs/05_example_curation.md
- specs/10_determinism_and_caching.md
- specs/11_state_and_events.md
- specs/20_rulesets_and_templates_registry.md
- specs/schemas/snippet_catalog.schema.json
- specs/schemas/issue.schema.json

## Scope
### In scope
- W3 implementation reading repo inventory + product facts
- Deterministic snippet discovery (sorted file paths; ruleset-based selection)
- Deterministic normalization: LF newlines, trim trailing whitespace, do not reformat semantics
- Deterministic snippet_id derived from {path, line_range, sha256(content)}
- Stable tagging derived from rulesets (no ad-hoc tags)

### Out of scope
- Planning/writing/patching

## Inputs
- `RUN_DIR/artifacts/repo_inventory.json`
- `RUN_DIR/artifacts/product_facts.json`
- repo worktree under `RUN_DIR/work/repo/`

## Outputs
- `RUN_DIR/artifacts/snippet_catalog.json`

## Allowed paths
- src/launch/workers/w3_snippet_curator/__init__.py
- src/launch/workers/_snippets/__init__.py
- tests/integration/test_tc_420_w3_integration.py
- reports/agents/**/TC-420/**
## Implementation steps
1) Load and validate inputs.
2) Determine snippet sources deterministically (examples/ samples/ docs) using repo_profile.
3) Extract snippet blocks (language-aware when possible) and record provenance.
4) Normalize snippet text (
, trim trailing whitespace) and compute sha256.
5) Compute stable `snippet_id` and assign ruleset-derived tags.
6) Validate and write `snippet_catalog.json`; emit events.

## E2E verification
**Concrete command(s) to run:**
```bash
python -m launch.workers.w3_snippet_curator --config specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml
```

**Expected artifacts:**
- artifacts/snippet_catalog.json (schema: snippet_catalog.schema.json)

**Success criteria:**
- [ ] Snippets inventoried
- [ ] Tags assigned deterministically

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-400 (repo_profile with file inventory)
- Downstream: TC-430 (IAPlanner selects snippets)
- Contracts: snippet_catalog.schema.json

## Deliverables
- Code: W3 worker + snippet extractors
- Tests:
  - unit tests for normalization + snippet_id stability
  - golden test for stable ordering (sorted by snippet_id)
  - regression tests for multi-language snippet extraction
- Reports:
  - reports/agents/<agent>/TC-420/report.md
  - reports/agents/<agent>/TC-420/self_review.md

## Acceptance checks
- [ ] `snippet_catalog.json` validates against schema
- [ ] snippet_id stability proven by tests
- [ ] every snippet has provenance fields required by schema
- [ ] tags are derived from rulesets (no freeform)

## Self-review
Use `reports/templates/self_review_12d.md`.
