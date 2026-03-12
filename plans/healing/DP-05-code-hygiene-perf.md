# DP-05 — Code Hygiene + Performance Short-Circuit

## Status: Done

## Gap linkage
- **DP-G6 (LOW)**: SHA256 is computed for every page before the grade check. For runs with many low-grade pages (common during early iterations), this is unnecessary I/O. The hash should be computed only after the grade qualifies.
- **DP-G7 (LOW)**: `action` field on `PagePromotionResult` uses magic strings; dead `_index.md` fallback in `_resolve_content_file`; `MIN_GRADE_NAMES` dict duplicates what `Grade(name)` could do.

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix
1. In `promote_run()`, reorder the per-page loop: move `_resolve_content_file` and `sha256_file` calls to AFTER the `min_grade` check. The file-exists check can stay early, but hashing should happen only when the grade qualifies.
2. Replace the dead `_index.md` fallback in `_resolve_content_file` with a comment explaining why `_index` is part of `content_path` directly (no second lookup needed).
3. Replace `action: str` on `PagePromotionResult` with a `PromotionAction` string enum.
4. Replace `MIN_GRADE_NAMES` dict with inline `Grade(name.upper())` in CLI, with proper error handling.

### Allowed paths
- `src/launcher/deploy/promoter.py`
- `src/launcher/cli/deploy.py`
- `tests/unit/deploy/test_promoter.py`

### Forbidden
- Any other file/path

## Acceptance checks

### Tests
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/deploy/ -v
# All tests pass — no behavior change
```

### CLI
```bash
.venv/Scripts/python.exe -m launcher.cli.main deploy promote runs/pilot_cells_20260307T082430 --dry-run
# Output unchanged
```

### No mock data in production paths
- Tests use `tmp_path`.

## Deliverables

### File: `src/launcher/deploy/promoter.py`

**Add `PromotionAction` enum** (replace magic strings):
```python
class PromotionAction(str, Enum):
    PROMOTED = "promoted"
    SKIPPED_GRADE_LOW = "skipped_grade_low"
    SKIPPED_NO_IMPROVEMENT = "skipped_no_improvement"
    SKIPPED_SAME_HASH = "skipped_same_hash"
    SKIPPED_MISSING_FILE = "skipped_missing_file"
```

**Update `PagePromotionResult`**:
```python
action: PromotionAction
```

**Reorder per-page loop** in `promote_run()`:
```python
# Current order:   resolve_file → grade_check → sha256 → manifest_check
# New order:        grade_check → resolve_file → sha256 → manifest_check
```
Move the `_grade_ge(grade, min_grade)` check to BEFORE `_resolve_content_file`. This avoids file I/O + SHA256 for pages that will be rejected on grade.

**Remove dead `_index.md` fallback** in `_resolve_content_file`:
```python
def _resolve_content_file(run_dir: Path, content_path: str) -> Path | None:
    """Find the markdown file for a content_path in the run's content bundle.

    Note: _index pages have _index as part of content_path (e.g.,
    "products.aspose.org/cells/_index") so the .md suffix appending
    resolves them directly.
    """
    pages_dir = run_dir / "content_bundle" / "pages"
    candidate = pages_dir / (content_path + ".md")
    if candidate.exists():
        return candidate
    return None
```

**Remove `MIN_GRADE_NAMES`** dict (no longer needed — CLI handles parsing).

### File: `src/launcher/cli/deploy.py`
Replace `MIN_GRADE_NAMES.get(min_grade.upper())` with:
```python
try:
    grade = Grade(min_grade.upper())
except ValueError:
    typer.echo(f"Error: invalid grade '{min_grade}'. Use A, B, C, D, or F.", err=True)
    raise typer.Exit(code=1)
```
Remove `MIN_GRADE_NAMES` imports.

### File: `tests/unit/deploy/test_promoter.py`
- Update all `action=` string references to use `PromotionAction` enum values.
- Add `test_grade_check_before_file_io`: mock `sha256_file` to raise if called — verify it's never called for a page below min_grade.

## Hard rules
- Keep public signatures of `promote_run`, `backfill_runs` unchanged.
- `PromotionAction` enum values must match existing string values for backward compat of report JSON output.
- No network in offline tests.
- Deterministic runs (PYTHONHASHSEED=0).
- No new deps.
- Keep code/docs/tests in sync.

## Review dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 criteria |
|-----------|-------------|
| Performance | SHA256 only computed for pages that pass the grade floor |
| Maintainability | Magic strings replaced with enum; dead code removed |
| Consistency | Uses `Grade(name)` pattern consistent with other enum usage in codebase |
| Minimality | No behavior change; only internal restructuring |
| Testability | Mock-based test verifies hash is not computed for rejected pages |

## Now (runbook)

```bash
# 1. Edit promoter.py — add PromotionAction enum, reorder loop, remove dead code + MIN_GRADE_NAMES
# 2. Edit cli/deploy.py — use Grade(name) instead of MIN_GRADE_NAMES
# 3. Update test_promoter.py — enum refs + new test
# 4. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/deploy/ -v
# 5. No behavior change in CLI
.venv/Scripts/python.exe -m launcher.cli.main deploy promote runs/pilot_cells_20260307T082430 --dry-run
```
