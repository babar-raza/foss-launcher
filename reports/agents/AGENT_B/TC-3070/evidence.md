# Evidence Report — TC-3070 Wire Provenance Validation into Artifact Reuse

## Test Results

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/state_store/test_store.py tests/unit/cli/test_drive.py tests/unit/provenance/ -x -v
```

**Result**: 67 passed, 0 failed

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
```

**Result**: 7136 passed, 13 skipped, 0 failed (full regression clean)

## Files Modified

| File | Change |
|------|--------|
| `src/launch/state_store/store.py` | Added `write_provenance()`, `read_provenance()` functions; updated docstring layout |
| `src/launch/state_store/__init__.py` | Exported `write_provenance`, `read_provenance` |
| `src/launch/cli/main.py` | Wired provenance validation before hydration (Step 4), provenance writing after publish (Step 10), added `ruleset_version`/`templates_version`/`provenance_status` to execution_plan.json |
| `docs/architecture/autopilot.md` | Updated flow diagram (provenance gate before hydration), store layout (provenance.json), execution_plan.json field table, Provenance section, failure modes |
| `tests/unit/state_store/test_store.py` | Added 5 new tests in `TestWriteProvenance` class |
| `tests/unit/cli/test_drive.py` | Added 5 new tests in `TestDriveProvenance` class |
| `plans/taskcards/INDEX.md` | Added TC-3070 entry |

## Files Created

| File | Purpose |
|------|---------|
| `plans/taskcards/TC-3070_provenance_validation.md` | Taskcard for provenance wiring |
| `reports/agents/agent_b/TC-3070/evidence.md` | This file |
| `reports/agents/agent_b/TC-3070/self_review.md` | Self-review 12D |

## Key Changes

### 1. `write_provenance()` + `read_provenance()` in store.py

```python
def write_provenance(store_root, store_key, repo_sha, provenance_record) -> Path:
    """Write provenance.json alongside worker dirs in the artifact set."""
    prov_path = store_root / store_key / "artifacts" / repo_sha / "provenance.json"
    ...

def read_provenance(artifact_set_path) -> Optional[Dict[str, Any]]:
    """Read provenance.json from an artifact set. Returns None if absent."""
    ...
```

### 2. CLI Step 4: Provenance validation before hydration

```python
# Before hydrating from store, check provenance compatibility
prov = read_provenance(artifact_set)
if prov is None:
    # Backward compat: old stores without provenance → warn + hydrate
    provenance_ok = True
else:
    provenance_ok, prov_reasons = validate_provenance_compat(
        prov,
        required_repo_sha=target_repo_sha,
        required_ruleset_version=run_config.get("ruleset_version", ""),
        required_templates_version=run_config.get("templates_version", ""),
    )
# If provenance mismatch → skip hydration, start fresh
```

### 3. CLI Step 10: Provenance writing after publish

```python
if result.exit_code == 0:
    published = publish_run_artifacts(store_root, store_key, target_repo_sha, run_dir)
    if published > 0:
        prov_record = build_provenance(run_config, target_repo_sha)
        write_provenance(store_root, store_key, target_repo_sha, prov_record)
```

### 4. execution_plan.json new fields

```python
"ruleset_version": run_config.get("ruleset_version", ""),
"templates_version": run_config.get("templates_version", ""),
"provenance_status": hydrate_source,  # "none", path, "provenance_mismatch", "failed"
```

### 5. Store re-populated with provenance

```
.foss_state/3d/python/artifacts/37114723.../
  w1/  (7 files)
  w2/  (6 files)
  w3/  (3 files)
  w4/  (2 files)
  w5/  (2 files)
  w8/  (1 file)
  w9/  (1 file)
  provenance.json  ← NEW (TC-3070)
```

Provenance record contents:
- `schema_version`: "1.0"
- `repo_sha`: "37114723be16c9c9441c8fb93116b044ad1aa6b5"
- `ruleset_version`: "ruleset.v1_1"
- `templates_version`: "templates.v1"

## New Tests Added (10)

### Store tests (5):
1. `test_write_creates_file` — write_provenance creates provenance.json at correct path
2. `test_read_returns_dict` — read_provenance returns parsed dict on round-trip
3. `test_read_missing_returns_none` — absent file returns None (no exception)
4. `test_read_corrupt_returns_none` — corrupt JSON returns None (no exception)
5. `test_write_idempotent` — writing twice with same data succeeds cleanly

### Drive tests (5):
1. `test_publish_and_write_provenance` — publish + write → provenance.json exists with correct versions
2. `test_provenance_mismatch_blocks_hydration` — ruleset version mismatch detected
3. `test_missing_provenance_allows_hydration` — backward compat: no provenance → hydrate with warning
4. `test_templates_version_mismatch_detected` — templates version mismatch detected
5. `test_matching_provenance_allows_hydration` — matching provenance → hydrate proceeds normally

## Acceptance Verification

- [x] `write_provenance()` writes to correct path: `artifacts/<repo_sha>/provenance.json`
- [x] `read_provenance()` returns None for missing file (not exception)
- [x] CLI Step 10 calls `build_provenance()` + `write_provenance()` after successful publish
- [x] CLI Step 4 calls `read_provenance()` + `validate_provenance_compat()` before hydration
- [x] Missing provenance.json → warn + hydrate (backward compat)
- [x] Provenance mismatch → skip hydration + log reasons
- [x] `execution_plan.json` includes `ruleset_version` and `templates_version`
- [x] All 67 targeted tests pass
- [x] Full regression (7136) passes
- [x] Store re-populated with provenance.json
