# TC-2450 Evidence — Agent D: W5 Page Hash Cache + regen_failed_only

**Date**: 2026-02-23
**Agent**: Agent_D

---

## Deliverables

### 1. `WorkerCache` API Extension (`src/launch/workers/_shared/worker_cache.py`)

Extended `is_page_hit()` and `record_page()` with backward-compatible `input_hash=""` param:

```python
def is_page_hit(self, page_key: str, input_hash: str = "") -> Optional[str]:
    # If both input_hash and stored_hash non-empty → validate match
    # If either empty → skip hash check (backward compat)

def record_page(self, page_key: str, draft_path: str, input_hash: str = "") -> None:
    # Stores {draft_path, input_hash} — old callers pass no hash, stored as ""
```

Existing tests (`TestPageCache`) pass unchanged. 5 new hash tests added.

---

### 2. Two New Private Functions in `worker.py`

**`_compute_page_input_hash(page, product_facts, snippet_catalog) -> str`**
- SHA256 of: spec fields + resolved claim text + resolved snippet code
- Sorted by claim_id / tag for determinism
- Only includes claims/snippets in `required_claim_ids` / `required_snippet_tags`
- Pure function — no I/O, no LLM

**`_find_failed_page_slugs(validation_report_path) -> frozenset[str]`**
- Parses `validation_report.json` issues
- Returns slugs with `severity: blocker` or `error`
- Returns `frozenset()` on missing/corrupt file (safe fallback)

---

### 3. W5 `execute_section_writer()` Changes

**Cache init block** (~after line 2218, after `previous_drafts` load):
```python
_worker_cache = _load_cache_config(run_dir, run_config)

if run_config.get("regen_failed_only", False):
    _val_path = run_layout.artifacts_dir / "validation_report.json"
    if _val_path.exists():
        _failed_slugs = _find_failed_page_slugs(_val_path)
        for _p in pages:
            _p["page_status"] = "new" if _p.get("slug") in _failed_slugs else "preserved"
    else:
        logger.warning("[W5] regen_failed_only=true but no validation_report.json found ...")
```

**Sequential loop** — before `_generate_single_page()`:
```python
_page_input_hash = ""
if _worker_cache.enabled:
    _page_input_hash = _compute_page_input_hash(page, product_facts, snippet_catalog)
    _cached_rel = _worker_cache.is_page_hit(page_id, _page_input_hash)
    if _cached_rel and (run_layout.run_dir / _cached_rel).exists():
        # Build manifest entry from cached content, continue (skip LLM)
```

After generation:
```python
if _worker_cache.enabled:
    _worker_cache.record_page(page_id, entry["draft_path"], _page_input_hash)
```

**Parallel loop (Phase 1)** — same cache check before appending to `to_generate`.

**Parallel loop (Phase 2)** — pre-compute hashes, record after future completes.

---

### 4. `run_cache.schema.json` Updated

`pages` entry gains optional `input_hash` field (backward compat — `required: ["draft_path"]` unchanged).

---

### 5. Tests

- `test_worker_cache.py` — 5 new hash tests in `TestPageCache`
- `test_w5_incremental.py` (NEW) — 6 test classes, ~35 tests:
  - `TestComputePageInputHash` (7) — determinism, claim/snippet sensitivity, edge cases
  - `TestFindFailedPageSlugs` (7) — blocker/error/warn/info, missing file, corrupt
  - `TestWorkerCacheHashIntegration` (3) — enabled hit/miss/disabled
  - `TestRegenFailedOnlyPageStatusOverride` (3) — integration scenarios
  - `TestComputePageInputHashEdgeCases` (4) — minimal fields, sorted headings, SHA256 length

---

## Backward Compatibility

| Scenario | Effect |
|----------|--------|
| `caching.enabled` absent/false | `_worker_cache.enabled=False` → all cache calls are no-ops |
| `regen_failed_only` absent/false | Block skipped entirely |
| `is_page_hit(key)` without hash | `input_hash=""` → hash validation skipped → backward compat |
| Pilot configs (no new flags) | **Zero behavior change** |
