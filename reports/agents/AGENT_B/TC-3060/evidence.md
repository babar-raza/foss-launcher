# Evidence Report — TC-3060 State Store Full Pipeline Coverage

## Test Results

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/state_store/ tests/unit/cli/test_drive.py tests/integration/test_drive_e2e.py tests/unit/autopilot/ -x -v
```

**Result**: 77 passed, 0 failed

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
```

**Result**: 7035 passed, 13 skipped, 0 failed (full regression clean)

## Files Modified

| File | Change |
|------|--------|
| `src/launch/state_store/store.py` | Expanded `_PUBLISHABLE_WORKERS` from 4 to 7 workers, added 8 artifacts to `_ARTIFACT_WORKER_MAP`, updated docstrings |
| `docs/architecture/autopilot.md` | Updated store layout diagram, coverage text, publish description |
| `tests/unit/state_store/test_store.py` | Added 8 new tests, updated 2 existing tests |
| `plans/taskcards/INDEX.md` | Added TC-3060 entry |

## Files Created

| File | Purpose |
|------|---------|
| `plans/taskcards/TC-3060_store_full_coverage.md` | Taskcard for store expansion |
| `reports/agents/agent_b/TC-3060/evidence.md` | This file |
| `reports/agents/agent_b/TC-3060/self_review.md` | Self-review 12D |

## Key Changes

### 1. `_PUBLISHABLE_WORKERS` expanded

```python
# Before
_PUBLISHABLE_WORKERS = ("w1", "w2", "w3", "w4")

# After
_PUBLISHABLE_WORKERS = ("w1", "w2", "w3", "w4", "w5", "w8", "w9")
```

### 2. `_ARTIFACT_WORKER_MAP` — 8 new entries

| Artifact | Worker | Gap Type |
|----------|--------|----------|
| `code_analysis.json` | w2 | Was silently dropped |
| `code_understanding.json` | w2 | Was silently dropped |
| `code_snippets.json` | w3 | Was silently dropped |
| `doc_snippets.json` | w3 | Was silently dropped |
| `draft_manifest.json` | w5 | New coverage |
| `sanitizer_metrics.json` | w5 | New coverage |
| `patch_bundle.json` | w8 | New coverage |
| `validation_report.json` | w9 | New coverage |

### 3. Store re-populated: 14 -> 22 artifacts

```
w1/ (7 files): discovered_docs, discovered_examples, frontmatter_contract, hugo_facts, repo_inventory, resolved_refs, site_context
w2/ (6 files): api_inventory, code_analysis, code_understanding, evidence_map, extracted_claims, product_facts
w3/ (3 files): code_snippets, doc_snippets, snippet_catalog
w4/ (2 files): page_plan, shared_facts
w5/ (2 files): draft_manifest, sanitizer_metrics
w8/ (1 files): patch_bundle
w9/ (1 files): validation_report
```

### 4. Workers excluded (by design)

- **W6**: No JSON artifact in `artifacts/` (writes `seo_report.json` to `work/`)
- **W7**: No JSON artifact (in-place LLM review)
- **W10**: No artifact (in-place markdown fixes)
- **W11**: `pr.json` is external GitHub state — caching would create stale references

## New Tests Added (8)

1. `test_w5_publishable` — W5 draft_manifest publish works
2. `test_w8_publishable` — W8 patch_bundle publish works
3. `test_w9_publishable` — W9 validation_report publish works
4. `test_w6_w7_w10_w11_not_publishable` — excluded workers still rejected
5. `test_publish_w5_w8_artifacts` — publish_run_artifacts maps W5/W8 correctly
6. `test_publish_missing_w2_w3_artifacts` — 4 previously-missing artifacts now published
7. `test_found_with_w5_dir` — find_artifact_set recognizes W5 worker dirs
8. `test_hydrates_w5_w8_w9` — hydration copies W5/W8/W9 artifacts

## Tests Updated (2)

1. `test_skip_non_publishable_worker` — changed from w9 to w10 (w9 now publishable)
2. `test_publish_maps_to_workers` — updated count from 3 to 4 (validation_report now published), added w9 assertion

## Acceptance Verification

- [x] All 4 missing W2/W3 artifacts added to map
- [x] `_PUBLISHABLE_WORKERS` includes w5, w8, w9
- [x] W5/W8/W9 artifacts added to `_ARTIFACT_WORKER_MAP`
- [x] Store layout docstring updated
- [x] Architecture docs updated
- [x] All 77 targeted tests pass
- [x] Full regression (7035) passes
- [x] W6/W7/W10/W11 correctly excluded
- [x] Store re-populated with 22 artifacts (was 14)
