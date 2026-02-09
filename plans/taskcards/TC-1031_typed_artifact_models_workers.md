---
id: TC-1031
title: "Typed Artifact Models -- Worker Models"
status: Done
owner: agent-f
updated: "2026-02-07"
tags: [infrastructure, models, phase-3]
depends_on: [TC-1030]
allowed_paths:
  - src/launch/models/snippet_catalog.py
  - src/launch/models/page_plan.py
  - src/launch/models/patch_bundle.py
  - src/launch/models/validation_report.py
  - src/launch/models/pr_artifact.py
  - src/launch/models/__init__.py
  - tests/unit/models/**
  - plans/taskcards/TC-1031_*
  - reports/agents/agent_f/TC-1031/**
evidence_required:
  - reports/agents/agent_f/TC-1031/evidence.md
  - reports/agents/agent_f/TC-1031/self_review.md
spec_ref: "46d7ac2"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# TC-1031: Typed Artifact Models -- Worker Models (W3-W9)

## Objective

Create typed Python models for W3-W9 output artifacts: SnippetCatalog, PagePlan,
PatchBundle, ValidationReport, and PRResult.

## Context

TC-1030 established the model pattern with base classes (BaseModel, Artifact) and
W1/W2 models (RepoInventory, SiteContext, FrontmatterContract, HugoFacts,
TruthLockReport, Ruleset). This taskcard extends coverage to the remaining
worker artifacts.

## Deliverables

1. `src/launch/models/snippet_catalog.py` -- SnippetCatalog model (W3 output)
2. `src/launch/models/page_plan.py` -- PagePlan model (W4 output)
3. `src/launch/models/patch_bundle.py` -- PatchBundle model (W6 output)
4. `src/launch/models/validation_report.py` -- ValidationReport model (W7 output)
5. `src/launch/models/pr_artifact.py` -- PRResult model (W9 output)
6. Updated `src/launch/models/__init__.py` with new exports
7. Unit tests in `tests/unit/models/` for all new models

## Design Principles

- Follow exact pattern from TC-1030: extend Artifact, from_dict/to_dict/validate
- Models are lightweight typed containers with no business logic
- from_dict() handles missing optional fields gracefully via .get(key, default)
- to_dict() produces deterministic output (sorted keys)
- Only create new files in src/launch/models/ (no modification to existing models)

## Schema References

- specs/schemas/snippet_catalog.schema.json
- specs/schemas/page_plan.schema.json
- specs/schemas/patch_bundle.schema.json
- specs/schemas/validation_report.schema.json
- specs/schemas/pr.schema.json
- specs/schemas/issue.schema.json

## Verification

- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x`
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/models/ -v`

## E2E verification

```bash
# TODO: Add concrete verification command
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_*.py -x
```

**Expected artifacts:**
- TODO: Specify expected output files/results

**Expected results:**
- TODO: Define success criteria

## Integration boundary proven

**Upstream:** TODO: Describe what provides input to this taskcard's work

**Downstream:** TODO: Describe what consumes output from this taskcard's work

**Boundary contract:** TODO: Specify input/output contract
