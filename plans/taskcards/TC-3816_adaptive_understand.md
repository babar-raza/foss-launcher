---
id: TC-3816
title: "Adaptive understand: clean API surface + rich briefs + docstring claims + synthetic snippets"
status: In-Progress
priority: Critical
owner: agent
updated: "2026-03-07"
tags: [understand, api-surface, content-quality, lean-repos]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3816_adaptive_understand.md
  - src/launcher/models/product.py
  - src/launcher/workers/understand/extract.py
  - specs/schemas/understanding_bundle.schema.json
  - tests/unit/workers/understand/test_extract.py
  - tests/unit/models/test_product.py
  - reports/TC-3816/evidence.md
evidence_required:
  - reports/TC-3816/evidence.md
---

# Taskcard TC-3816 — Adaptive Understand: Clean API Surface + Rich Briefs + Docstring Claims + Synthetic Snippets

## Objective

Fix the understand phase to produce clean, rich API surface data that prevents generator hallucination across all repo densities. Currently, Cells has 14/22 contaminated classes (Docling), Note has 71/142 internal implementation classes, and the generator only receives bare class names — causing 22 `factual_accuracy:high` findings that drive 97% D+F grades.

## Required spec references

- `specs/07_code_analysis_and_enrichment.md` (API surface extraction algorithm)
- `specs/03_product_facts_and_evidence.md` (Claims extraction)

## Scope

### In scope
- **Change 0**: API surface contamination filter (package-path + canonical-import prefix + internal-class heuristic)
- **Change A**: ClassBrief model + population from existing analyzer data
- **Change E**: Docstring-to-claim harvesting for lean repos
- **Change G**: Synthetic snippet generation from ClassBrief data

### Out of scope
- Generator prompt changes (TC-3817)
- Planner page pruning (TC-3817)
- Post-LLM method name validation (TC-3817)
- ENGINE_VERSION bump (TC-3817, after both TCs complete)

## Inputs

- Repository source code (via `_find_source_files()` and `analyze_file_safe()`)
- `ProductIdentity.canonical_import` (from intake config)
- Existing `_extract_api_surface()` output

## Outputs

- Clean `ApiSurface` with `class_briefs: list[ClassBrief]` field
- Additional docstring-sourced claims (kind="api", source_type="docstring")
- Synthetic snippets (source_type="synthetic") for lean repos
- Updated `understanding_bundle.schema.json`

## Allowed paths

- plans/taskcards/TC-3816_adaptive_understand.md
- src/launcher/models/product.py
- src/launcher/workers/understand/extract.py
- specs/schemas/understanding_bundle.schema.json
- tests/unit/workers/understand/test_extract.py
- tests/unit/models/test_product.py
- reports/TC-3816/evidence.md

### Allowed paths rationale
- `models/product.py`: Add ClassBrief model, extend ApiSurface
- `extract.py`: All 4 changes modify this file (contamination filter, class_briefs population, docstring claims, synthetic snippets)
- Schema: Must match new ApiSurface fields
- Tests: Verify all 4 changes
- Evidence: Required by AG-002

## Implementation steps

### Step 1: Add ClassBrief model to product.py

Add `ClassBrief(LauncherBaseModel)` with fields: name, docstring_snippet, methods, properties.
Add `class_briefs: list[ClassBrief]` field to `ApiSurface`.

### Step 2: Implement contamination filter in _extract_api_surface()

a) Restrict `_find_source_files()` to prioritize files under `package_root`
b) Filter classes by canonical-import prefix (compute import path per file)
c) Add internal-class heuristic filter (FND, Chunk, Reference, Binary markers)

### Step 3: Populate class_briefs from analyze_file_safe() data

In the existing loop over `analyze_file_safe()` results, capture methods, properties, and docstring per class into ClassBrief objects. Cap at 10 methods + 10 properties per class.

### Step 4: Add docstring-to-claim harvesting

After LLM/deterministic claim extraction in `run_extract()`, iterate over `class_briefs` and create claims from docstrings > 30 chars. Cap at 50 docstring claims.

### Step 5: Add synthetic snippet generation

After `_extract_snippets()`, if snippet count < page count × 2, generate template-based snippets from ClassBrief data. Cap at 20 synthetic snippets.

### Step 6: Update schema

Add `class_briefs` array to `understanding_bundle.schema.json` under ApiSurface.

### Step 7: Write tests

- Contamination filter test: mock repo with third-party classes → verify filtered out
- ClassBrief population test: mock analyzer output → verify methods/properties captured
- Docstring claims test: mock ClassBrief with docstrings → verify claims created
- Synthetic snippets test: mock ClassBrief with methods → verify snippets generated
- Internal-class filter test: verify FND/Chunk classes excluded

### Step 8: Run full test suite

`PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short`

## Failure modes

### Failure mode 1: Over-filtering removes legitimate public classes

**Detection**: After filtering, check that `len(public_classes) >= 5` for repos with known APIs.
**Resolution**: Loosen heuristic — only filter if class name matches 2+ internal markers, not just 1.
**Gate**: factual_accuracy check in evaluator.

### Failure mode 2: ClassBrief docstrings are empty for auto-generated bindings

**Detection**: `class_briefs` populated but all have `docstring_snippet=""`.
**Resolution**: Fall back to using class name + base class info as docstring substitute.
**Gate**: No gate — graceful degradation.

### Failure mode 3: Synthetic snippets have invalid syntax

**Detection**: `ast.parse()` fails on generated snippet.
**Resolution**: Validate each synthetic snippet with `ast.parse()` before adding; skip invalid ones.
**Gate**: code_correctness check in evaluator.

## Task-specific review checklist

1. [ ] Cells repo: no Docling classes in public_classes
2. [ ] Note repo: no FND/Chunk/Reference classes in public_classes
3. [ ] ClassBrief objects have methods + properties for top classes
4. [ ] Docstring claims have kind="api" and source_type="docstring" evidence
5. [ ] Synthetic snippets use canonical_import correctly
6. [ ] Synthetic snippets pass ast.parse() validation
7. [ ] ApiSurface schema matches new model
8. [ ] All existing tests still pass

## Deliverables

1. Updated `src/launcher/models/product.py` with ClassBrief model
2. Updated `src/launcher/workers/understand/extract.py` with all 4 changes
3. Updated `specs/schemas/understanding_bundle.schema.json`
4. New/updated tests in `tests/unit/workers/understand/test_extract.py`
5. Evidence at `reports/TC-3816/evidence.md`

## Acceptance checks

1. [ ] Cells public_classes contains 0 Docling classes
2. [ ] Note public_classes contains 0 FND/Chunk internal classes
3. [ ] class_briefs populated for all public classes
4. [ ] At least 20 docstring claims generated for Note repo
5. [ ] At least 10 synthetic snippets generated for Note repo
6. [ ] All synthetic snippets pass ast.parse()
7. [ ] Full test suite passes with PYTHONHASHSEED=0

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-3816/evidence.md

## E2E verification

```bash
# 1. Unit tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -v

# 2. Verify contamination filter on real checkpoint data
.venv/Scripts/python.exe -c "
from launcher.models.product import ClassBrief, ApiSurface
print('ClassBrief model OK')
print('ApiSurface has class_briefs:', hasattr(ApiSurface.model_fields, 'class_briefs'))
"

# 3. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short
```

**Expected results**:
- 0 contaminated classes in filtered output
- ClassBrief objects with methods/properties populated
- Full test suite green

## Integration boundary proven

**Upstream**: Intake provides `ProductIdentity.canonical_import` and repo clone
**Downstream**: Generator consumes `ApiSurface.class_briefs` via understand_checkpoint.json; Planner uses claims for page assignment
**Contract**: `ApiSurface` pydantic model (serialized to JSON checkpoint). New `class_briefs` field is optional (defaults to empty list) for backward compatibility.
