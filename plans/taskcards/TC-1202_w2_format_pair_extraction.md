---
id: TC-1202
title: "Page Expansion — W2 Format-Pair Extraction & Evidence Enrichment"
status: Draft
priority: High
owner: "Agent B (Backend/Workers)"
updated: "2026-02-11"
tags: ["w2", "format-pairs", "page-expansion", "phase-2"]
depends_on: ["TC-1200"]
allowed_paths:
  - plans/taskcards/TC-1202_w2_format_pair_extraction.md
  - src/launch/workers/w2_facts_builder/code_analyzer.py
  - src/launch/workers/w2_facts_builder/worker.py
  - tests/unit/workers/test_w2_format_pairs.py
evidence_required:
  - reports/agents/AGENT_B/TC-1202/evidence.md
  - reports/agents/AGENT_B/TC-1202/self_review.md
spec_ref: "33242628c6242b03c2c83a5e978f73d5155f247a"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1202 — Page Expansion — W2 Format-Pair Extraction & Evidence Enrichment

## Objective
Extend W2's code_analyzer and facts builder to extract format capabilities (read/write) from the target repository, producing a `format_capabilities` field in `product_facts.json` that W4 uses to generate `per_format_pair` pages.

## Required spec references
- specs/08_content_distribution_strategy.md (updated by TC-1200 — `per_format_pair` source contract)
- src/launch/workers/w2_facts_builder/code_analyzer.py (current AST parser — will be extended)
- src/launch/workers/w2_facts_builder/worker.py (current W2 worker — will emit new field)
- specs/rulesets/ruleset.v1.yaml (family_overrides.known_formats — read-only, from TC-1201)

## Scope

### In scope
1. **Format discovery in code_analyzer.py** — New function `extract_format_capabilities()`:
   - Parse class/method names for format indicators (e.g., `FbxExporter`, `load_obj`, `save_as_gltf`)
   - Parse docstrings/comments for format mentions
   - Parse manifest/setup files for keywords (e.g., "fbx", "gltf", "obj" in description)
   - Cross-reference with `family_overrides.known_formats` from ruleset (if available)
   - Apply `page_expansion.format_pairs_override` from run_config (add/remove pairs)
2. **New product_facts field** — `format_capabilities`:
   ```json
   {
     "format_capabilities": {
       "read_formats": ["FBX", "OBJ", "STL", "3DS"],
       "write_formats": ["FBX", "GLTF", "GLB", "OBJ", "STL"],
       "confirmed_pairs": [["FBX", "GLTF"], ["OBJ", "STL"], ...],
       "discovery_method": "ast_analysis|manifest|known_formats|override"
     }
   }
   ```
3. **Pair confirmation heuristic** — A pair `(A, B)` is confirmed if:
   - A is in `read_formats` AND B is in `write_formats`, OR
   - A conversion function/class explicitly mentions both formats, OR
   - Pair is in `format_pairs_override.add`
4. **Override application** — After auto-discovery, apply run_config overrides:
   - Add pairs from `format_pairs_override.add`
   - Remove pairs from `format_pairs_override.remove`
5. **Unit tests** for format extraction logic

### Out of scope
- W4 page generation from format pairs (TC-1203)
- Templates for format conversion pages (TC-1205)
- Ruleset changes (TC-1201)

## Inputs
- Target repository source code (via W1 clone)
- product_facts.json (current state from W2)
- run_config (page_expansion.format_pairs_override)
- ruleset (family_overrides.known_formats)

## Outputs
- src/launch/workers/w2_facts_builder/code_analyzer.py (UPDATED — +150 lines: `extract_format_capabilities()`)
- src/launch/workers/w2_facts_builder/worker.py (UPDATED — +30 lines: emit `format_capabilities`)
- tests/unit/workers/test_w2_format_pairs.py (NEW — ~120 lines)
- product_facts.json gains `format_capabilities` field

## Allowed paths
- plans/taskcards/TC-1202_w2_format_pair_extraction.md
- src/launch/workers/w2_facts_builder/code_analyzer.py
- src/launch/workers/w2_facts_builder/worker.py
- tests/unit/workers/test_w2_format_pairs.py

### Allowed paths rationale
W2 worker and its code_analyzer module are the only files that need modification. Tests are co-located in the standard test directory.

## Implementation steps

### Step 1: Read current code_analyzer.py and worker.py
Understand the current structure. Locate where `api_surface_summary` is built and where product_facts is assembled.

**Resilience note**: The code_analyzer.py already has AST parsing infrastructure. Reuse existing `_visit_class_def()` and `_visit_function_def()` patterns. Do NOT duplicate parsing logic.

### Step 2: Implement `extract_format_capabilities()` in code_analyzer.py
Add a new top-level function (not inside a class) that:

1. **Scans class names** for format suffixes/prefixes:
   - Pattern: `(Fbx|Gltf|Obj|Stl|3ds|Ply|Dae|Usd|Xlsx|Csv|Pdf|Html|One)(Exporter|Importer|Reader|Writer|Loader|Saver|Converter)`
   - Extract format name and direction (Reader/Importer/Loader → read, Writer/Exporter/Saver → write, Converter → both)

2. **Scans function names** for format patterns:
   - `load_{format}`, `read_{format}`, `open_{format}`, `import_{format}` → read
   - `save_{format}`, `write_{format}`, `export_{format}`, `to_{format}` → write
   - `convert_{from}_to_{to}` → read(from) + write(to) + confirmed pair

3. **Scans manifest/setup** for format keywords in description strings

4. **Cross-references with known_formats** (if provided) to validate discovered formats

5. **Generates confirmed pairs**: Cross-product of `read_formats × write_formats`, filtered by heuristic confidence

**Function signature:**
```python
def extract_format_capabilities(
    source_files: List[Dict[str, Any]],  # AST-parsed source files
    known_formats: Optional[List[str]] = None,  # From ruleset family_overrides
    format_pairs_override: Optional[Dict[str, Any]] = None,  # From run_config
) -> Dict[str, Any]:
```

### Step 3: Integrate into W2 worker
In the W2 worker's main pipeline function, after `code_analyzer.analyze()` returns:
1. Call `extract_format_capabilities()` with the parsed sources
2. Pass `known_formats` from merged ruleset family_overrides (if available in context)
3. Pass `format_pairs_override` from run_config (if available in context)
4. Add result to `product_facts["format_capabilities"]`

**Resilience note**: If `known_formats` or `format_pairs_override` are not available (older configs), the function must work with defaults (auto-discovery only).

### Step 4: Write unit tests
Create `tests/unit/workers/test_w2_format_pairs.py`:

1. **test_extract_formats_from_class_names** — Mock AST with `FbxExporter`, `ObjImporter` → verify read/write lists
2. **test_extract_formats_from_function_names** — Mock with `load_fbx()`, `save_gltf()` → verify
3. **test_confirmed_pairs_cross_product** — Verify pairs are generated correctly
4. **test_override_add_pairs** — Verify `format_pairs_override.add` adds pairs
5. **test_override_remove_pairs** — Verify `format_pairs_override.remove` removes pairs
6. **test_known_formats_filter** — Verify only known formats are included when provided
7. **test_empty_repo** — Verify graceful handling when no format indicators found
8. **test_deterministic_output** — Run twice, verify identical output (sorted lists)

### Step 5: Run tests and validate
```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w2_format_pairs.py -v
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w2_code_analyzer.py -v  # regression
```

## Failure modes

### Failure mode 1: False positive format detection (e.g., class `Format` matched as format name)
**Detection:** Unit tests show unexpected formats in output. Pilot run generates nonsensical conversion pages.
**Resolution:** Use strict regex patterns with known format names. Require format to match `known_formats` if provided. Add a minimum confidence threshold (format must appear in 2+ indicators).
**Spec/Gate:** specs/08 per_format_pair candidate generation rules

### Failure mode 2: No formats discovered for a repo
**Detection:** `format_capabilities.read_formats` and `write_formats` are both empty. W4 generates 0 format pair pages.
**Resolution:** This is valid for repos that don't handle file formats. The function must return empty lists gracefully. W4 handles empty candidate lists by generating 0 optional pages.
**Spec/Gate:** specs/08 graceful degradation rule

### Failure mode 3: Override application order causes inconsistency
**Detection:** A pair in both `add` and `remove` produces unpredictable result.
**Resolution:** Apply removes AFTER adds. If a pair is in both, remove wins. Document this precedence in the function docstring.
**Spec/Gate:** specs/08 override resolution order

## Task-specific review checklist
1. [ ] `extract_format_capabilities()` handles class names, function names, and manifests
2. [ ] Read/write direction correctly inferred from name patterns
3. [ ] Confirmed pairs generated as cross-product with filtering
4. [ ] Override add/remove applied correctly (remove wins on conflict)
5. [ ] known_formats filter applied when provided
6. [ ] Empty repo handled gracefully (empty lists, no error)
7. [ ] Output is deterministic (sorted lists)
8. [ ] Integration into W2 worker is backward compatible (field is optional)
9. [ ] 8+ unit tests covering all code paths
10. [ ] No regressions in existing code_analyzer tests

## Deliverables
- src/launch/workers/w2_facts_builder/code_analyzer.py (UPDATED)
- src/launch/workers/w2_facts_builder/worker.py (UPDATED)
- tests/unit/workers/test_w2_format_pairs.py (NEW)
- reports/agents/AGENT_B/TC-1202/evidence.md
- reports/agents/AGENT_B/TC-1202/self_review.md

## Acceptance checks
1. [ ] `extract_format_capabilities()` returns correct format_capabilities dict
2. [ ] product_facts.json includes `format_capabilities` field after W2 run
3. [ ] Override mechanism works (add + remove)
4. [ ] All unit tests pass
5. [ ] Existing W2 tests pass (no regression)
6. [ ] Output is deterministic

## Preconditions / dependencies
- TC-1200 completed (spec defines the `format_capabilities` contract)
- Existing code_analyzer.py AST infrastructure is functional

## Self-review
[To be completed by Agent B after implementation]
