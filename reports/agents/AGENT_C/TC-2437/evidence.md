# Evidence: TC-2437 — W1 Repo Profiler

## Files Created
- `src/launch/workers/w1_repo_scout/repo_profiler.py` — deterministic repo profiling
- `tests/unit/workers/test_w1_repo_profiler.py` — 31 tests

## Functions Implemented
- `compute_docs_depth(doc_paths, example_paths)` — total file count as depth signal
- `compute_api_surface(paths)` — count non-test source files in API languages
- `_infer_source_type(path)` — path-based source type inference
- `score_citation_quality(citations, source_weights)` — max citation weight [0,1]
- `build_repo_profile_artifact(repo_inventory)` — full deterministic artifact

## Test Results
- 31 tests written (all pass)
- Coverage: empty inputs, all quality tiers (rich/standard/minimal), determinism, sorting
