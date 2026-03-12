---
id: TC-3779
title: "Enrich Understand Worker with ProductEvidence"
status: In-Progress
priority: High
owner: Agent-B
updated: "2026-03-07"
tags: [phase-1, understand, prerequisite]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3779_understand_product_evidence.md
  - src/launcher/models/understanding.py
  - src/launcher/workers/understand/worker.py
  - specs/schemas/understanding_bundle.schema.json
  - tests/unit/workers/test_understand_product_evidence.py
  - reports/agents/B/TC-3779/
evidence_required:
  - reports/agents/B/TC-3779/evidence.md
---

# Taskcard TC-3779 — Enrich Understand Worker with ProductEvidence

## Objective

Wire `build_repo_truth()` from `code_analyzer.py` into the Understand worker to produce `ProductEvidence` (supported_formats, conversion_pairs, workflows, input/output formats, capabilities) and expose it in the `UnderstandingBundle`. This is the prerequisite for evidence-aware slug generation in TC-3780.

## Required spec references

- `specs/07_code_analysis_and_enrichment.md` (Section: code analysis pipeline — defines `analyze_repository_code` and `build_repo_truth` contracts)
- `specs/03_product_facts_and_evidence.md` (Section: claims and evidence — defines the evidence types that feed into content generation)

## Scope

### In scope
- Add `ProductEvidence` model to `src/launcher/models/understanding.py`
- Add `product_evidence` field to `UnderstandingBundle`
- Wire `build_repo_truth()` + `analyze_repository_code()` into Understand worker Phase B.5
- Update JSON schema `specs/schemas/understanding_bundle.schema.json` (has `additionalProperties: false` — MUST update or orchestrator rejects output)
- Add tests verifying product_evidence population

### Out of scope
- Slug generation (belongs to TC-3780)
- Planner changes (belongs to TC-3781)
- Changes to `code_analyzer.py` itself (reused as-is; owned by shared lib)

## Inputs

- `repo_dir` (from Intake via scout — absolute path to cloned repository)
- `repo_info` (from scout: `file_tree`, `file_index`, `source_paths`, etc.)
- `api_surface` (from extract Phase B — list of discovered API symbols)
- `product` (ProductIdentity from intake — provides `display_name`)

## Outputs

- `ProductEvidence` model populated with formats, conversion pairs, workflows
- Updated `UnderstandingBundle` with `product_evidence` field
- Updated JSON schema `specs/schemas/understanding_bundle.schema.json`

## Allowed paths

- `plans/taskcards/TC-3779_understand_product_evidence.md`
- `src/launcher/models/understanding.py`
- `src/launcher/workers/understand/worker.py`
- `specs/schemas/understanding_bundle.schema.json`
- `tests/unit/workers/test_understand_product_evidence.py`
- `reports/agents/B/TC-3779/`

### Allowed paths rationale
- `models/understanding.py`: New `ProductEvidence` model and `UnderstandingBundle` field addition
- `workers/understand/worker.py`: Wire `build_repo_truth` + `analyze_repository_code` into Phase B.5
- `understanding_bundle.schema.json`: Schema must accept new `product_evidence` property (has `additionalProperties: false`)
- `test_understand_product_evidence.py`: Unit tests for new functionality
- `reports/agents/B/TC-3779/`: Evidence artifacts

## Implementation steps

### Step 1: Add ProductEvidence model

Add a new `ProductEvidence` pydantic model to `src/launcher/models/understanding.py` with the following fields:
- `supported_formats: list[str]` (default_factory=list)
- `conversion_pairs: list[dict[str, str]]` (default_factory=list)
- `workflows: list[str]` (default_factory=list)
- `input_formats: list[str]` (default_factory=list)
- `output_formats: list[str]` (default_factory=list)
- `capabilities: list[str]` (default_factory=list)

### Step 2: Add product_evidence field to UnderstandingBundle

Add `product_evidence: ProductEvidence = Field(default_factory=ProductEvidence)` to the `UnderstandingBundle` model. The default ensures backward compatibility — existing bundles without this field will deserialize cleanly.

### Step 3: Update JSON schema

Add a `product_evidence` property to `specs/schemas/understanding_bundle.schema.json` with the correct sub-schema matching the `ProductEvidence` model. This is critical because the schema has `additionalProperties: false` — omitting this step causes orchestrator rejection.

### Step 4: Wire Phase B.5 into Understand worker

In `src/launcher/workers/understand/worker.py`, after Phase B extract (~line 92), add Phase B.5:
1. Build `repo_inventory` from `repo_info.file_index` and `repo_info.source_paths`
2. Call `analyze_repository_code(repo_dir, repo_inventory, product.display_name)`
3. Call `build_repo_truth(repo_dir, manifest_data, code_analysis, source_roots)`
4. Populate `ProductEvidence` from the `repo_truth` dict using `.get()` with safe defaults
5. Wrap entire Phase B.5 in try/except — on failure, log warning and use empty `ProductEvidence`

### Step 5: Pass product_evidence into UnderstandingBundle

Update the `UnderstandingBundle` construction call to include the `product_evidence` field from Step 4.

### Step 6: Write tests

Create `tests/unit/workers/test_understand_product_evidence.py` with:
- Test that `ProductEvidence` model instantiates with defaults (all empty lists)
- Test that `ProductEvidence` model accepts populated fields
- Test that `UnderstandingBundle` includes `product_evidence` with default
- Test that worker Phase B.5 populates product_evidence for a non-empty repo (mock `analyze_repository_code` and `build_repo_truth`)
- Test that Phase B.5 failure produces empty `ProductEvidence` (no crash)

## Failure modes

### Failure mode 1: analyze_repository_code crashes on empty repo

**Detection**: Exception raised during Phase B.5; traceback in worker log with `analyze_repository_code` in stack
**Resolution**: Wrap entire Phase B.5 in try/except, return empty `ProductEvidence()`, log warning with exception details
**Gate**: No specific gate — this is defensive coding for robustness

### Failure mode 2: JSON schema validation rejects new field

**Detection**: Orchestrator raises `ValidationError` when validating UnderstandingBundle output against schema; error message references `additionalProperties`
**Resolution**: Verify that `understanding_bundle.schema.json` is updated BEFORE running the worker; the schema has `additionalProperties: false` so the `product_evidence` property must be explicitly declared in the schema's `properties` block

### Failure mode 3: build_repo_truth returns unexpected structure

**Detection**: `KeyError` or `TypeError` when accessing nested dicts in the repo_truth return value
**Resolution**: Use `.get()` with defaults throughout the ProductEvidence population code; all ProductEvidence fields have `default_factory=list` so missing keys produce empty lists rather than crashes

## Task-specific review checklist

1. [ ] `ProductEvidence` model has all 6 fields (`supported_formats`, `conversion_pairs`, `workflows`, `input_formats`, `output_formats`, `capabilities`) with correct types
2. [ ] `UnderstandingBundle.product_evidence` has default (`default_factory=ProductEvidence`) for backward compatibility
3. [ ] JSON schema `understanding_bundle.schema.json` updated with `product_evidence` property matching model
4. [ ] Worker Phase B.5 calls `analyze_repository_code` + `build_repo_truth` in correct order
5. [ ] Error handling: empty `ProductEvidence()` on any Phase B.5 failure (no crash propagation)
6. [ ] Existing understand tests still pass (`pytest tests/ -k understand`)
7. [ ] New test verifies `product_evidence` fields populated for non-empty repo input

## Deliverables

1. Modified `src/launcher/models/understanding.py` — `ProductEvidence` model + `UnderstandingBundle` field
2. Modified `src/launcher/workers/understand/worker.py` — Phase B.5 wiring
3. Modified `specs/schemas/understanding_bundle.schema.json` — `product_evidence` property
4. New `tests/unit/workers/test_understand_product_evidence.py` — unit tests

## Acceptance checks

1. [ ] `ProductEvidence` model importable: `from launcher.models.understanding import ProductEvidence`
2. [ ] Existing tests pass: `.venv/Scripts/python.exe -m pytest tests/ -k understand`
3. [ ] New test passes: `.venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand_product_evidence.py`
4. [ ] JSON schema valid: python validates understanding_bundle against schema

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: schema validation PASS
- [ ] Evidence captured: reports/agents/B/TC-3779/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -k understand -v
```

**Expected results**:
- All existing understand tests pass (no regressions)
- New `test_understand_product_evidence.py` tests all pass
- `ProductEvidence` model importable and serializable

## Integration boundary proven

**Upstream**: IntakeBundle provides `repo_dir` and `product` (ProductIdentity); scout provides `repo_info` with `file_index` and `source_paths`
**Downstream**: Planner consumes `UnderstandingBundle.product_evidence` for evidence-aware slug generation (TC-3781)
**Contract**: `ProductEvidence` fields are all optional lists with `default_factory=list` — backward compatible; existing consumers that do not read `product_evidence` are unaffected
