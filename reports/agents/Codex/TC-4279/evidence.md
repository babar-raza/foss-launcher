# Evidence: TC-4279 Scout Review Remediation

**Date**: 2026-03-14  
**Verified by**: Codex

## Scope

This task fixed four Scout defects found during manual review:
- product docs filtered as meta-docs
- README summaries reordered by score
- `SharedFacts.has_tests` missing manifest-backed test paths
- README local path contradictions not surfaced to operators

No schema or artifact-shape changes were introduced.

## Files Changed

| File | Purpose |
|------|---------|
| `src/launcher/workers/scout/scout.py` | Evidence selection, README ordering, manifest-backed test detection, README path helpers |
| `src/launcher/workers/scout/worker.py` | Scout self-review warning for missing local README paths |
| `tests/unit/workers/test_scout.py` | Regression tests for product-doc preservation, ordered README extraction, README path warnings |
| `tests/unit/workers/test_scout_facts.py` | Regression test for manifest-backed pytest `testpaths` |
| `specs/worker_understand.md` | Scout contract text updated to match README-summary and `has_tests` behavior |

## Targeted Test Verification

Command:

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_scout.py tests/unit/workers/test_scout_facts.py -q
```

Result:

```text
84 passed in 6.68s
```

## Doc Freshness Verification

Command:

```bash
python scripts/check_doc_freshness.py --uncommitted
```

Result:
- EXIT 1
- Scout-related behavior drift was fixed in `specs/worker_understand.md`
- Remaining flagged items were unrelated pre-existing dirty-worktree changes outside TC-4279 scope:
  - `specs/schemas/content_manifest.schema.json` -> `docs/guides/schema-authorship.md`
  - `src/launcher/models/claims.py` -> `specs/content_model_pageir.md`
  - `src/launcher/orchestrator/graph_builder.py` -> `specs/state_events_checkpoints.md`
  - `src/launcher/shared/code_analyzer.py` -> `specs/system_overview.md`
  - `src/launcher/workers/evaluate/checks/api_verification.py` -> `specs/worker_evaluate.md`
  - `src/launcher/workers/generate/section_prompt.py` -> `specs/worker_generate.md`
  - `src/launcher/workers/intake/clone.py` -> `specs/github_intake.md`
  - `src/launcher/workers/planner/plan.py` -> `docs/guides/new-worker.md`
  - `src/launcher/workers/publish/worker.py` -> `specs/worker_publish.md`

`docs/README.md` ownership was checked. No guide add/remove occurred, so no `docs/README.md` update was required.

## Fresh Scout-Only Pilot Runs

| Pilot | Fresh run |
|------|-----------|
| `aspose-3d-foss-python.yaml` | `runs/260314_111016_3d_python_4557` |
| `aspose-3d-foss-typescript.yaml` | `runs/260314_111019_3d_typescript_c0b0` |
| `aspose-cells-foss-python.yaml` | `runs/260314_111021_cells_python_139a` |
| `aspose-note-foss-python.yaml` | `runs/260314_111023_note_python_4795` |
| `aspose-slides-foss-python.yaml` | `runs/260314_111026_slides_python_0acd` |

Each run produced `scout_checkpoint.json`, `scout_inventory.json`, `scout_bundle.json`, and `scout.json`.

Scout self-review sweep on the fresh checkpoints:
- `3d_python` -> `passed = true`, no findings
- `3d_typescript` -> `passed = true`, medium warning `scout_readme_missing_local_paths`
- `cells_python` -> `passed = true`, no findings
- `note_python` -> `passed = true`, medium warning `scout_readme_missing_local_paths`
- `slides_python` -> `passed = true`, no findings

## Manual Spot-Checks Against Cached Clones

### 1. 3D Python: product docs preserved

Clone evidence:
- `runs/.clone_cache/aspose_3d_python` contains:
  - `FBX_IMPLEMENTATION_SUMMARY.md`
  - `OBJ_IMPORTER_IMPLEMENTATION.md`
  - `STL_IMPORT_IMPLEMENTATION.md`
  - `PYPI_READINESS.md`
  - `IMPLEMENTATION_SUMMARY.md`
  - `AGENTS.md`

Fresh Scout result:
- `runs/260314_111016_3d_python_4557/scout_checkpoint.json`
- `repo_info.doc_paths` now includes:
  - `FBX_IMPLEMENTATION_SUMMARY.md`
  - `OBJ_IMPORTER_IMPLEMENTATION.md`
  - `PYPI_READINESS.md`
  - `README.md`
  - `STL_IMPORT_IMPLEMENTATION.md`

Fresh Scout inventory confirms the generic/meta docs remain filtered:
- `AGENTS.md` -> `doc_ineligible_meta`
- `IMPLEMENTATION_SUMMARY.md` -> `doc_ineligible_meta`

Conclusion: the leading-token meta-doc fix preserved product evidence while keeping generic meta-doc filtering.

### 2. 3D TypeScript: README contradiction warning is warning-only

Clone evidence:
- `runs/.clone_cache/aspose_3d_typescript/examples` does not exist
- `runs/.clone_cache/aspose_3d_typescript/LICENSE` does not exist
- `runs/.clone_cache/aspose_3d_typescript/README.md` exists

Fresh self-review check against:
- `runs/260314_111019_3d_typescript_c0b0/scout_checkpoint.json`

Result:
- `passed = true`
- finding category: `scout_readme_missing_local_paths`
- warning message references missing local paths: `LICENSE`, `examples`, `examples/`

Conclusion: the README contradiction is now surfaced as a medium warning and does not fail Scout.

### 3. Cells Python: manifest-backed tests detected

Clone evidence:
- `runs/.clone_cache/aspose_cells_python/pyproject.toml` declares pytest `testpaths = ['tests', 'examples']`
- `runs/.clone_cache/aspose_cells_python/examples` exists

Fresh Scout result:
- `runs/260314_111021_cells_python_139a/scout_checkpoint.json`
- `repo_info.shared_facts.has_tests = true`

Conclusion: manifest-backed test evidence now counts when the declared paths exist.

### 4. Note Python: README summary order fixed

Fresh Scout result:
- `runs/260314_111023_note_python_4795/scout_checkpoint.json`
- `repo_info.readme_summary` starts with:

```text
# \U0001f5d2\ufe0f Aspose.Note FOSS for Python ...
```

Fresh Scout result also keeps curated docs:
- `docs/ms-one/README.md`
- `docs/ms-onestore/README.md`
- many `docs/ms-onestore/*.md` files
- `docs/onenote-api.md`
- `README.md`

Clone evidence:
- `runs/.clone_cache/aspose_note_python/language-agnostic-plan` exists
- `runs/.clone_cache/aspose_note_python/docs/ms-one/README.md` exists

Fresh self-review also reports:
- `scout_readme_missing_local_paths` for `samples`

Conclusion: the README summary now preserves title/introduction order, curated docs remain selected, `language-agnostic-plan/**` stays excluded from product evidence, and stale README path claims are now surfaced as warnings.

### 5. Slides Python: no regression on sparse-doc repo

Fresh Scout result:
- `runs/260314_111026_slides_python_0acd/scout_checkpoint.json`
- `repo_info.doc_paths = ['README.md']`
- `repo_info.shared_facts.has_tests = true`
- `repo_info.readme_summary` begins with the README title and installation guidance

Conclusion: the new Scout changes did not regress sparse-doc repo behavior.

## Acceptance Summary

| Requirement | Status |
|------------|--------|
| No schema changes | PASS |
| Targeted Scout tests pass | PASS |
| Fresh Scout-only pilots complete | PASS |
| Product-doc filtering defect fixed | PASS |
| README ordering defect fixed | PASS |
| Manifest-backed `has_tests` defect fixed | PASS |
| README contradiction warning added, warning-only | PASS |
