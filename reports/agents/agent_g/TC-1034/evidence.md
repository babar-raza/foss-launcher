# TC-1034: W1 Stub Enrichment — Evidence

## Files Created
- `src/launch/workers/w1_repo_scout/frontmatter_discovery.py` (395 lines)
- `src/launch/workers/w1_repo_scout/site_context_builder.py` (new builder module)
- `src/launch/workers/w1_repo_scout/hugo_facts_builder.py` (new builder module)

## Files Modified
- `src/launch/workers/w1_repo_scout/worker.py` — replaced TC-300 stubs with real builder calls

## Bug Fix Applied
- `frontmatter_discovery.py:278-285` — Fixed `doc_entrypoints` format mismatch
- Root cause: `doc_entrypoints` is a flat list of strings, not dicts with `"path"` keys
- Fix: Use `doc_entrypoint_details` (which has dicts) with fallback to `doc_entrypoints` (strings), handling both formats via `isinstance` check

## Commands Run
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ --tb=short
# Result: 2392 passed, 12 skipped, 0 failures
```

## Test Results
- All 2392 tests pass
- 12 skipped (pre-existing)
- 0 failures

## Deterministic Verification
- All output uses `json.dumps(data, indent=2, sort_keys=True)` for deterministic serialization
- YAML frontmatter parser uses sorted key iteration
- Section contracts use sorted required_keys and optional_keys lists
