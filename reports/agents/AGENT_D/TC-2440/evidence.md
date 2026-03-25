# Evidence: TC-2440 Worker Cache Core

## Files Created
- `src/launch/workers/_shared/worker_cache.py` — WorkerCache class + load_cache_config factory
- `tests/unit/workers/test_worker_cache.py` — 18 tests

## Test Results
```
tests/unit/workers/test_worker_cache.py  18 passed
```

## Contract
- Disabled by default (caching.enabled=false). Zero behavior change when disabled.
- compute_input_hash: SHA256 over sorted paths+content.
- Atomic persist via .json.tmp rename.
- Corrupt/missing cache loads as empty dict (no crash).
