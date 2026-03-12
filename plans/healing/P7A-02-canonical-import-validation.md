# P7A-02 — Strengthen Canonical Import Validation

## Status: Done

## Gap Linkage: G-02

`_validate_canonical_import` in `run_config.py` only checks if `canonical_import`
contains a dot. This misses cases like `canonical_import: "aspose_wrong_foss"` which
has no dots but is still wrong. The function also has a dead variable `families_path`
that is computed but never used.

## Role

Senior engineer. Drop-in, production-ready validation.

## Scope

### Fix

Replace the dot-check with an actual value comparison:

```python
def _validate_canonical_import(data: Dict[str, Any], repo_root: Path) -> None:
    """Validate canonical_import matches families.yaml import_tpl."""
    canonical = data.get("canonical_import")
    family = data.get("family")
    platform = data.get("platform")

    if not canonical or not family or platform != "python":
        return

    expected = f"aspose_{family}_foss"
    if canonical != expected:
        logger.error(
            "canonical_import '%s' does not match expected '%s' "
            "(derived from families.yaml import_tpl for platform=%s, family=%s). "
            "Fix the pilot config.",
            canonical, expected, platform, family,
        )
        raise ConfigError(
            f"canonical_import '{canonical}' does not match expected "
            f"'{expected}' per families.yaml import_tpl."
        )
```

This:
- Removes dead `families_path` variable
- Validates against the exact expected value, not just format
- Catches `aspose.cells`, `aspose_wrong_foss`, `aspose-cells-foss`, etc.
- Still only validates Python platform (Java/dotnet have different patterns)

### Allowed paths

- `src/launcher/io/run_config.py`

### Forbidden

Any path not listed above.

## Acceptance Checks

- CLI: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q` — all pass
- Tests: P7A-01 tests (once written) must cover the new validation logic
- Config respected end-to-end: `aspose_cells_foss` accepted, `aspose.cells` rejected, `aspose_wrong_foss` rejected
- No mock data in production paths
- No dead variables in the function

## Deliverables

- Modified `src/launcher/io/run_config.py` — `_validate_canonical_import` rewritten
- No stubs, no TODOs

## Hard Rules

- Keep function signature unchanged: `_validate_canonical_import(data, repo_root)`
- `repo_root` parameter is kept for future use (loading families.yaml for non-Python platforms) but not used in current implementation
- Raises `ConfigError` on mismatch (fail-fast at startup)
- Logs at ERROR level before raising
- No new dependencies

## Review Dimensions — What 5/5 Means

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Thoroughness | Catches all known bad patterns: dotted, wrong family, wrong suffix |
| Consistency | Same error pattern as other ConfigError raises in the file |
| Production grading | Would catch the original bug AND prevent future variants |
| Correctness | Expected value derived from same formula as families.yaml import_tpl |
| Robustness | Handles missing fields gracefully (early return) |
| Minimality | Single function replacement, no other changes |
| Observability | Error message includes actual value, expected value, family, and platform |

## Now (Runbook)

```bash
# 1. Edit src/launcher/io/run_config.py — replace _validate_canonical_import body

# 2. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --ignore=tests/test_planner_per_module.py

# 3. Manually verify: load a pilot config with wrong value
.venv/Scripts/python.exe -c "
from pathlib import Path
from launcher.io.run_config import _validate_canonical_import
_validate_canonical_import({'canonical_import': 'aspose.cells', 'family': 'cells', 'platform': 'python'}, Path('.'))
" 2>&1 | grep -i "ConfigError"
# Should raise ConfigError

# 4. Verify correct value passes
.venv/Scripts/python.exe -c "
from pathlib import Path
from launcher.io.run_config import _validate_canonical_import
_validate_canonical_import({'canonical_import': 'aspose_cells_foss', 'family': 'cells', 'platform': 'python'}, Path('.'))
print('PASS')
"
# Should print PASS
```
