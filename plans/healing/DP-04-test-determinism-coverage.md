# DP-04 — Test Determinism + Coverage Expansion

## Status: Done

## Gap linkage
- **DP-G4 (MODERATE)**: `test_backfill_multiple_runs` has a non-deterministic assertion (`assert "New" in content or "Old" in content`) that passes regardless of which run's content wins. The test should verify the A-graded version deterministically wins.

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix
1. Fix `test_backfill_multiple_runs` to deterministically verify the A-graded content wins by asserting on manifest grade and content.
2. Add `test_promote_index_page`: test that `_index` content paths (e.g., `products.aspose.org/cells/_index`) resolve correctly and deploy as `_index.md`.
3. Add `test_promote_slug_fallback`: test that when `content_path` is empty, `slug` is used as fallback key.
4. Remove unused `import pytest` from `test_manifest.py`.
5. Add a CLI smoke test for `deploy status` and `deploy diff` commands using `typer.testing.CliRunner`.

### Allowed paths
- `tests/unit/deploy/test_promoter.py`
- `tests/unit/deploy/test_manifest.py`

### Forbidden
- Any other file/path

## Acceptance checks

### Tests
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/deploy/ -v
# All tests pass, including new ones
# test_backfill_multiple_runs makes deterministic assertions
```

### No mock data in production paths
- All tests use `tmp_path`.

## Deliverables

### File: `tests/unit/deploy/test_promoter.py`

**Fix `test_backfill_multiple_runs`** — replace weak assertion:
```python
def test_backfill_multiple_runs(self, tmp_path: Path):
    deploy_dir = tmp_path / "deploy"
    runs_root = tmp_path / "runs"

    _create_run(tmp_path, "run_old", [
        {"content_path": "docs.aspose.org/cells/python/page", "grade": "C", "content": "# Old"},
    ])
    _create_run(tmp_path, "run_new", [
        {"content_path": "docs.aspose.org/cells/python/page", "grade": "A", "content": "# New"},
    ])

    reports = backfill_runs(runs_root, "cells", "python", deploy_dir)
    assert len(reports) == 2

    # A-graded content must win regardless of processing order
    manifest = load_manifest(deploy_dir / "manifest.json")
    entry = manifest.pages["docs.aspose.org/cells/python/page"]
    assert entry.grade == Grade.A

    content = (deploy_dir / "docs.aspose.org/cells/python/page.md").read_text(encoding="utf-8")
    assert "New" in content
```

**Add `test_promote_index_page`**:
```python
def test_promote_index_page(self, tmp_path: Path):
    """_index content paths must resolve to _index.md files."""
    deploy_dir = tmp_path / "deploy"
    run_dir = _create_run(tmp_path, "run1", [
        {"content_path": "products.aspose.org/cells/_index", "grade": "B"},
    ])
    report = promote_run(run_dir, deploy_dir)
    assert report.promoted == 1
    assert (deploy_dir / "products.aspose.org/cells/_index.md").exists()
```

**Add `test_promote_slug_fallback`**:
```python
def test_promote_slug_fallback(self, tmp_path: Path):
    """When content_path is empty, slug is used as key."""
    deploy_dir = tmp_path / "deploy"
    run_dir = tmp_path / "runs" / "run1"
    run_dir.mkdir(parents=True)
    # Eval report with empty content_path
    eval_report = {
        "verdict": "NO_GO",
        "pages": [{"slug": "docs.aspose.org/cells/python/install", "content_path": "", "grade": "B", "findings": [], "check_results": {}}],
        "quality": {}, "gates": [], "root_cause_diagnosis": [], "go_criteria": [],
    }
    (run_dir / "evaluation_report.json").write_text(json.dumps(eval_report), encoding="utf-8")
    pages_dir = run_dir / "content_bundle" / "pages"
    md_file = pages_dir / "docs.aspose.org/cells/python/install.md"
    md_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.write_text("# Install", encoding="utf-8")
    report = promote_run(run_dir, deploy_dir)
    assert report.promoted == 1
```

**Add CLI smoke tests**:
```python
class TestCLISmoke:
    def test_status_no_manifest(self, tmp_path: Path):
        from typer.testing import CliRunner
        from launcher.cli.main import app
        runner = CliRunner()
        result = runner.invoke(app, ["deploy", "status", "--deploy-dir", str(tmp_path / "empty")])
        assert "No deploy manifest found" in result.output

    def test_diff_shows_promotable(self, tmp_path: Path):
        from typer.testing import CliRunner
        from launcher.cli.main import app
        runner = CliRunner()
        run_dir = _create_run(tmp_path, "run1", [
            {"content_path": "docs.aspose.org/cells/python/page", "grade": "B"},
        ])
        result = runner.invoke(app, ["deploy", "diff", str(run_dir), "--deploy-dir", str(tmp_path / "deploy")])
        assert "would be promoted" in result.output
```

### File: `tests/unit/deploy/test_manifest.py`
- Remove `import pytest` (unused).

## Hard rules
- No network in offline tests.
- Deterministic runs (PYTHONHASHSEED=0).
- No new deps (typer.testing is part of typer).
- Keep code/docs/tests in sync.

## Review dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 criteria |
|-----------|-------------|
| Testability | Every logical path (index pages, slug fallback, CLI commands) has a dedicated test |
| Correctness | Backfill test deterministically verifies A-grade wins |
| Thoroughness | CLI smoke tests cover `status` and `diff`; edge cases for `_index` and empty `content_path` tested |
| Minimality | Only test files change; no production code modifications |
| Production grading | No flaky/non-deterministic assertions remain |

## Now (runbook)

```bash
# 1. Edit test_promoter.py — fix backfill test, add 3 new tests + CLI smoke tests
# 2. Edit test_manifest.py — remove unused import
# 3. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/deploy/ -v
# 4. All tests pass with deterministic results
```
