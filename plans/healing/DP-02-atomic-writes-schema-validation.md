# DP-02 — Atomic Writes + Schema Validation

## Status: Done

## Gap linkage
- **DP-G2 (MODERATE)**: `shutil.copy2` for content file deployment is non-atomic. An interrupted copy leaves a partial `.md` file in `deploy/`. The project convention (see `atomic.py`) is to write a `.tmp` file then `os.replace`.
- **DP-G5 (LOW)**: `save_manifest()` does not pass `schema_path` to `atomic_write_json` despite `specs/schemas/deploy_manifest.schema.json` existing on disk.

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix
1. In `promoter.py` line 208, replace `shutil.copy2(source_file, dest_path)` with `atomic_write_text(dest_path, source_file.read_text(encoding="utf-8"), validate_boundary=deploy_dir)`.
2. Remove `import shutil` (now unused).
3. In `manifest.py` line 60, add `schema_path="specs/schemas/deploy_manifest.schema.json"` to `atomic_write_json` call.
4. Add a test that interrupting a promotion mid-write doesn't leave partial files (simulated via patching `atomic_write_text` to raise after partial work).
5. Add a test that a manifest with an invalid grade value fails schema validation on save.

### Allowed paths
- `src/launcher/deploy/promoter.py`
- `src/launcher/deploy/manifest.py`
- `tests/unit/deploy/test_promoter.py`
- `tests/unit/deploy/test_manifest.py`

### Forbidden
- Any other file/path

## Acceptance checks

### Tests
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/deploy/ -v
# All existing + new tests pass
```

### CLI
```bash
.venv/Scripts/python.exe -m launcher.cli.main deploy promote runs/pilot_cells_20260307T082430 --dry-run
# No regression — same output as before
```

### Config respected end-to-end
- Schema validation fires on every manifest save; invalid manifests rejected before write.

### No mock data in production paths
- Tests use `tmp_path`, never write to real `deploy/`.

## Deliverables

### File: `src/launcher/deploy/promoter.py`
- Replace line 208 `shutil.copy2(source_file, dest_path)` with:
  ```python
  from launcher.io.atomic import atomic_write_text
  atomic_write_text(dest_path, source_file.read_text(encoding="utf-8"), validate_boundary=deploy_dir)
  ```
- Remove `import shutil` from imports.

### File: `src/launcher/deploy/manifest.py`
- In `save_manifest()`, change:
  ```python
  atomic_write_json(path, data, validate_boundary=path.parent)
  ```
  to:
  ```python
  atomic_write_json(path, data, validate_boundary=path.parent, schema_path="specs/schemas/deploy_manifest.schema.json")
  ```

### File: `tests/unit/deploy/test_manifest.py`
- Add `test_save_validates_schema`: attempt to save a manifest with tampered data (e.g., grade="X") — must raise validation error.

### File: `tests/unit/deploy/test_promoter.py`
- Add `test_promotion_uses_atomic_write`: verify that a promoted file goes through atomic write by checking no `.tmp` files remain on success.

## Hard rules
- Keep public signatures; `promote_run` and `save_manifest` signatures unchanged.
- No network in offline tests.
- Deterministic runs (PYTHONHASHSEED=0).
- No new deps.
- Keep code/docs/tests in sync.

## Review dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 criteria |
|-----------|-------------|
| Consistency | All file writes in deploy module use `atomic_write_text`/`atomic_write_json` — matches project convention |
| Robustness | Interrupted writes never leave partial files; schema violations blocked before disk write |
| Production grading | Zero risk of partial content in deploy/ from crash; manifest schema enforced |
| Minimality | Two surgical changes (1 line in promoter, 1 kwarg in manifest), plus import cleanup |
| Testability | Schema validation failure path tested; atomic write behavior tested |

## Now (runbook)

```bash
# 1. Edit manifest.py — add schema_path kwarg
# 2. Edit promoter.py — replace shutil.copy2 with atomic_write_text, remove import shutil
# 3. Add new tests to test_manifest.py and test_promoter.py
# 4. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/deploy/ -v
# 5. Verify no .tmp files left after a real promote
.venv/Scripts/python.exe -m launcher.cli.main deploy promote runs/pilot_cells_20260307T082430 --dry-run
```
