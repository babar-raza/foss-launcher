---
id: TC-HO-09
title: "Embed api_surface + product_evidence in ContentManifest"
status: Done
priority: High
owner: "orchestrator-agent"
updated: "2026-03-11"
tags: [understand, evaluate, generate, schema, graph-state]
depends_on: [TC-HO-01, TC-HO-02, TC-HO-03]
allowed_paths:
  - plans/taskcards/TC-HO-09_contentmanifest-embedding.md
  - src/launcher/models/content.py
  - src/launcher/workers/generate/worker.py
  - src/launcher/workers/evaluate/worker.py
  - specs/schemas/content_manifest.schema.json
  - reports/agents/wave5/TC-HO-09/evidence.md
  - reports/agents/wave5/self_review.md
evidence_required:
  - reports/agents/wave5/TC-HO-09/evidence.md
---

# Taskcard TC-HO-09 — Embed api_surface + product_evidence in ContentManifest

## Objective

Embed `api_surface` (ApiSurface) and `product_evidence` (ProductEvidence) as optional fields
in `ContentManifest` so they flow through the schema-validated graph state from Generate →
Evaluate, eliminating the fragile disk side-loads in the Evaluate worker and making the
data contract explicit and verifiable at every boundary.

## Required spec references

- `specs/schemas/content_manifest.schema.json` (additionalProperties: false — must be updated)
- `specs/schemas/understanding_bundle.schema.json` (source definitions for api_surface and product_evidence sub-schemas)
- `specs/worker_understand.md` (UnderstandingBundle contract)
- `specs/worker_generate.md` (ContentManifest output contract)
- `specs/worker_evaluate.md` (Evaluate input contract)

## Scope

### In scope
- Add `api_surface: ApiSurface` and `product_evidence: ProductEvidence` optional fields to `ContentManifest` pydantic model
- Update `content_manifest.schema.json` to accept both new fields (without adding them to `required`)
- Populate both fields in `GenerateWorker.run()` from `understand.api_surface` and `understand.product_evidence`
- Update `EvaluateWorker.run()` to prefer manifest fields over disk side-loads when available
- Add unit tests for serialization/deserialization and evaluate-reads-from-manifest path

### Out of scope
- Removing the disk side-load helpers entirely (backward compat retained for old checkpoints)
- Changes to the UnderstandingBundle schema or model
- Changes to the Understand worker itself
- Changes to the Publish worker

## Inputs

- `src/launcher/models/understanding.py` — ApiSurface and ProductEvidence model definitions
- `src/launcher/models/product.py` — ApiSurface class (actual source of ApiSurface)
- `src/launcher/workers/understand/worker.py` — populated UnderstandingBundle
- `src/launcher/workers/generate/worker.py` — existing ContentManifest construction at line ~546

## Outputs

- Updated `src/launcher/models/content.py` — ContentManifest with two new optional fields
- Updated `specs/schemas/content_manifest.schema.json` — schema accepts new fields
- Updated `src/launcher/workers/generate/worker.py` — manifest construction passes both fields
- Updated `src/launcher/workers/evaluate/worker.py` — prefers manifest fields over disk loads
- `reports/agents/wave5/TC-HO-09/evidence.md` — test output and change summary

## Allowed paths

- plans/taskcards/TC-HO-09_contentmanifest-embedding.md
- src/launcher/models/content.py
- src/launcher/workers/generate/worker.py
- src/launcher/workers/evaluate/worker.py
- specs/schemas/content_manifest.schema.json
- reports/agents/wave5/TC-HO-09/evidence.md
- reports/agents/wave5/self_review.md

### Allowed paths rationale
- `content.py` — model definition change required
- `generate/worker.py` — must populate new manifest fields
- `evaluate/worker.py` — must read from manifest fields (prefer graph state over disk)
- `content_manifest.schema.json` — additionalProperties:false requires explicit declaration of new fields
- `reports/` — evidence and self-review artifacts (non-protected path)

## Implementation steps

### Step 1: Update src/launcher/models/content.py

Import `ApiSurface` from `launcher.models.product` and `ProductEvidence` from
`launcher.models.understanding`. Add both as optional fields with `default_factory`
to `ContentManifest`.

### Step 2: Update specs/schemas/content_manifest.schema.json

Add `api_surface` and `product_evidence` as optional properties in the root object,
copying the sub-schemas from `understanding_bundle.schema.json`. Do NOT add them to
`required` — they have defaults.

### Step 3: Update src/launcher/workers/generate/worker.py

At the `ContentManifest(...)` construction (~line 546), add:
```python
api_surface=understand.api_surface,
product_evidence=understand.product_evidence,
```

### Step 4: Update src/launcher/workers/evaluate/worker.py

In `_run_deterministic_checks` call sites, replace disk-loaded `api_surface` and
`product_evidence` with manifest fields when available (non-empty), with fallback to
disk loaders for backward compatibility with older checkpoint-only runs.

### Step 5: Add unit tests

Add tests in the existing evaluate test file asserting:
- ContentManifest serializes/deserializes with api_surface and product_evidence
- Evaluate worker reads from manifest fields when available

## Failure modes

### Failure mode 1: Circular import between content.py and understanding.py

**Detection**: `ImportError: cannot import name 'ProductEvidence' from 'launcher.models.understanding'` at test time.
**Resolution**: `ApiSurface` lives in `launcher.models.product`, not `understanding.py`. `ProductEvidence` lives in `launcher.models.understanding`. Both are imported in `content.py` from their respective modules. If a cycle occurs, use `TYPE_CHECKING` guard with `model_rebuild()`.
**Gate**: pytest import test at startup.

### Failure mode 2: Schema validation rejects new fields

**Detection**: `jsonschema.ValidationError: Additional properties are not allowed ('api_surface' was unexpected)` in integration tests or pipeline runs.
**Resolution**: Ensure `specs/schemas/content_manifest.schema.json` has `api_surface` and `product_evidence` in its `properties` section at the root level (NOT inside `generation_stats` or other sub-objects).
**Gate**: `specs/schemas/content_manifest.schema.json` additionalProperties:false constraint.

### Failure mode 3: Evaluate reads stale disk data when manifest has fresh data

**Detection**: Evaluate worker uses disk-loaded api_surface even when `manifest.api_surface.public_classes` is non-empty.
**Resolution**: Check preference logic — manifest fields should take priority when `manifest.api_surface.public_classes` is truthy or `manifest.api_surface.confidence != "low"`. Fall back to disk only when manifest api_surface is empty (default factory).
**Gate**: Unit test asserting manifest-preferred path.

### Failure mode 4: Existing tests break due to new required fields

**Detection**: Tests that construct `ContentManifest(pages=[], ...)` start failing with `ValidationError`.
**Resolution**: Both new fields use `default_factory` — they must NEVER be added to `required`. Verify `ContentManifest(pages=[], cross_links=[], generation_stats=GenerationStats())` still works without specifying api_surface or product_evidence.
**Gate**: All existing generate/evaluate tests pass unchanged.

## Task-specific review checklist

1. [ ] `ContentManifest` has `api_surface: ApiSurface = Field(default_factory=ApiSurface)` and `product_evidence: ProductEvidence = Field(default_factory=ProductEvidence)`
2. [ ] `content_manifest.schema.json` properties section includes `api_surface` and `product_evidence` (not in `required`)
3. [ ] `GenerateWorker.run()` sets both fields from `understand.api_surface` and `understand.product_evidence`
4. [ ] `EvaluateWorker` prefers manifest fields over disk side-load when `manifest.api_surface.public_classes` is non-empty
5. [ ] No circular import introduced — `content.py` imports from `product.py` (ApiSurface) and `understanding.py` (ProductEvidence) cleanly
6. [ ] `ContentManifest()` with no api_surface/product_evidence args still constructs without error (backward compat)
7. [ ] Docstrings updated for new fields in ContentManifest
8. [ ] Schema `"description"` fields present for both new properties
9. [ ] Spec file drift checked — no worker_generate.md or worker_evaluate.md spec update needed for this internal plumbing change
10. [ ] `docs/README.md` checked — no ownership map entry triggers for this change
11. [ ] All tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -x -q`

## Deliverables

1. Updated `src/launcher/models/content.py` — ContentManifest with api_surface + product_evidence
2. Updated `specs/schemas/content_manifest.schema.json` — schema accepts new fields
3. Updated `src/launcher/workers/generate/worker.py` — manifest construction passes both fields
4. Updated `src/launcher/workers/evaluate/worker.py` — reads from manifest when available
5. `reports/agents/wave5/TC-HO-09/evidence.md` — test output + before/after flow description

## Acceptance checks

1. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -x -q` passes — 3651 passed
2. [x] `ContentManifest(pages=[], cross_links=[], generation_stats=GenerationStats()).api_surface` returns an `ApiSurface` instance
3. [x] `content_manifest.schema.json` does not have `api_surface` or `product_evidence` in `required`
4. [x] `EvaluateWorker._run_deterministic_checks` call in `_evaluate_page_llm` reads from `manifest.api_surface` (not solely from disk) when manifest has data

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: schema validation PASS
- [ ] Evidence captured: reports/agents/wave5/TC-HO-09/evidence.md
- [ ] Doc freshness: confirmed no spec drift

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -x -q
```

**Expected results**:
- All existing tests pass
- New ContentManifest serialization tests pass
- New evaluate-reads-from-manifest tests pass

## Integration boundary proven

**Upstream**: Generate worker builds `ContentManifest` from `UnderstandingBundle.api_surface` and `UnderstandingBundle.product_evidence`
**Downstream**: Evaluate worker reads `ContentManifest.api_surface` and `ContentManifest.product_evidence` directly from graph state instead of disk
**Contract**: `content_manifest.schema.json` validates both fields at the graph boundary; Pydantic `default_factory` ensures backward compat with old manifests that lack these fields
