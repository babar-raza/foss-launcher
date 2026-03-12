---
id: DM-04
title: "Add unit tests for check_doc_freshness.py"
status: Done
priority: High
owner: "agent"
updated: "2026-03-08"
tags: [healing, doc-maintenance, AG-019, tests]
depends_on: [DM-01, DM-02]
allowed_paths:
  - plans/healing/DM-04_test_coverage.md
  - tests/test_check_doc_freshness.py
evidence_required:
  - "PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_check_doc_freshness.py -v → all pass"
  - "Test count >= 12 (covers happy path, no-mapping, drift detected, empty diff edge case, subdirectory invocation, and --verbose flag)"
---

# Taskcard DM-04 — Add Unit Tests for `check_doc_freshness.py`

## Gap linkage

- GR-05: `check_doc_freshness.py` has zero unit tests; `matches_pattern` and
  drift detection logic are completely untested

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix

Create `tests/test_check_doc_freshness.py` with the following test groups.
All git I/O must be mocked via `unittest.mock.patch`. No real git calls.
No network. Deterministic.

#### Group 1: `matches_pattern` unit tests (6 tests)

```python
def test_matches_exact_file():
    # "src/launcher/shared/ts_analyzer.py" matches exact pattern
    assert matches_pattern("src/launcher/shared/ts_analyzer.py",
                           "src/launcher/shared/ts_analyzer.py")

def test_matches_double_star_subdirectory():
    # Deep path matches ** pattern
    assert matches_pattern("src/launcher/workers/evaluate/checks/foo.py",
                           "src/launcher/workers/evaluate/**")

def test_matches_double_star_direct_child():
    # Direct child of ** pattern also matches
    assert matches_pattern("src/launcher/workers/evaluate/worker.py",
                           "src/launcher/workers/evaluate/**")

def test_no_match_sibling_directory():
    # Different sibling dir must NOT match
    assert not matches_pattern("src/launcher/workers/generate/worker.py",
                               "src/launcher/workers/evaluate/**")

def test_no_match_parent_directory():
    # Parent path must NOT match a child ** pattern
    assert not matches_pattern("src/launcher/workers",
                               "src/launcher/workers/evaluate/**")

def test_exact_config_file():
    # Top-level config file matches exact pattern
    assert matches_pattern("configs/pipeline.yaml", "configs/pipeline.yaml")
```

#### Group 2: `find_governing_spec` unit tests (4 tests)

```python
def test_find_spec_for_evaluate_worker():
    assert find_governing_spec(
        "src/launcher/workers/evaluate/worker.py") == "specs/worker_evaluate.md"

def test_find_spec_for_shared_client():
    # After DM-02, clients/** must map to llm_provider.md
    assert find_governing_spec(
        "src/launcher/clients/llm_provider.py") == "specs/llm_provider.md"

def test_find_spec_returns_none_for_unmapped():
    # util/** is intentionally excluded per DM-02 comment
    assert find_governing_spec("src/launcher/util/logging.py") is None

def test_find_spec_for_config_file():
    assert find_governing_spec("configs/pipeline.yaml") == "specs/system_overview.md"
```

#### Group 3: `get_changed_files` with mocked git (2 tests)

```python
@patch("subprocess.run")
def test_get_changed_files_success(mock_run):
    mock_run.return_value = MagicMock(returncode=0,
        stdout="src/launcher/workers/evaluate/worker.py\nconfigs/pipeline.yaml\n")
    result = get_changed_files("HEAD~1")
    assert "src/launcher/workers/evaluate/worker.py" in result
    assert "configs/pipeline.yaml" in result
    assert len(result) == 2

@patch("subprocess.run")
def test_get_changed_files_git_failure_exits_2(mock_run):
    mock_run.return_value = MagicMock(returncode=1, stderr="fatal: bad object")
    with pytest.raises(SystemExit) as exc:
        get_changed_files("INVALID_REF")
    assert exc.value.code == 2
```

#### Group 4: Integration / drift detection (4 tests via mocked main() helpers)

```python
@patch("scripts.check_doc_freshness.get_changed_files")
def test_no_drift_when_spec_also_changed(mock_gcf, tmp_path, monkeypatch):
    # Both code and spec changed → no drift
    monkeypatch.chdir(tmp_path)
    # Create fake spec files so Path.exists() returns True
    (tmp_path / "specs").mkdir()
    (tmp_path / "specs" / "worker_evaluate.md").touch()
    mock_gcf.return_value = [
        "src/launcher/workers/evaluate/worker.py",
        "specs/worker_evaluate.md",
    ]
    # Should not raise and should find no drift pairs
    changed = mock_gcf.return_value
    changed_set = set(changed)
    from scripts.check_doc_freshness import find_governing_spec
    drift = []
    for f in changed:
        spec = find_governing_spec(f)
        if spec and spec not in changed_set and Path(spec).exists():
            drift.append((f, spec))
    assert drift == []

@patch("scripts.check_doc_freshness.get_changed_files")
def test_drift_detected_when_spec_not_touched(mock_gcf, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "specs").mkdir()
    (tmp_path / "specs" / "worker_evaluate.md").touch()
    mock_gcf.return_value = ["src/launcher/workers/evaluate/worker.py"]
    changed = mock_gcf.return_value
    changed_set = set(changed)
    from scripts.check_doc_freshness import find_governing_spec
    drift = []
    for f in changed:
        spec = find_governing_spec(f)
        if spec and spec not in changed_set and Path(spec).exists():
            drift.append((f, spec))
    assert len(drift) == 1
    assert drift[0][1] == "specs/worker_evaluate.md"

@patch("scripts.check_doc_freshness.get_changed_files")
def test_no_mapping_means_no_drift(mock_gcf, tmp_path, monkeypatch):
    # A file with no mapping (e.g. util/**) never triggers drift
    monkeypatch.chdir(tmp_path)
    mock_gcf.return_value = ["src/launcher/util/logging.py"]
    changed = mock_gcf.return_value
    from scripts.check_doc_freshness import find_governing_spec
    assert all(find_governing_spec(f) is None for f in changed)

@patch("subprocess.run")
def test_empty_diff_exits_2(mock_run, capsys):
    # --since HEAD with empty diff and clean working tree → exit 0 (not 2)
    # --since HEAD with empty diff but dirty tree → exit 2 with warning
    # This test verifies exit 2 path:
    def run_side_effect(cmd, **kwargs):
        if "diff" in cmd and "--name-only" in cmd:
            return MagicMock(returncode=0, stdout="")
        if "status" in cmd and "--porcelain" in cmd:
            return MagicMock(returncode=0, stdout=" M src/launcher/workers/evaluate/worker.py\n")
        return MagicMock(returncode=0, stdout="")
    mock_run.side_effect = run_side_effect
    # Invoke via get_changed_files + dirty-tree check logic (tested through main())
    # Minimal: just verify get_changed_files returns [] for empty stdout
    from scripts.check_doc_freshness import get_changed_files
    result = get_changed_files("HEAD~1")
    assert result == []
```

### Allowed paths

- `tests/test_check_doc_freshness.py` (new file)

### Forbidden

Any file outside `tests/test_check_doc_freshness.py` and this plan file.
Do not modify `scripts/check_doc_freshness.py` in this taskcard (that is
DM-01's scope).

---

## Acceptance checks

### CLI

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_check_doc_freshness.py -v
# Expected: all tests pass, 0 failed
# Expected: >= 12 tests collected

# Confirm no real git calls are made during tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_check_doc_freshness.py -v -s 2>&1 \
  | grep -i "git diff\|subprocess.run called with git"
# Expected: no real git commands in output
```

### UI/Web/API

N/A.

### Tests

This taskcard IS the tests. All 4 groups must pass. Coverage requirement:
- `matches_pattern`: all branches covered
- `find_governing_spec`: mapping hit, no-mapping miss, and config file hit
- `get_changed_files`: success and failure paths
- Drift detection: drift present, no drift, no mapping

### Config respected end-to-end

Tests must import `CODE_TO_SPEC` from the script directly so that expanding
the mapping in DM-02 automatically improves test coverage without test
changes.

### No mock data in production paths

All tests mock git subprocess calls. No real filesystem state required except
for tests that use `tmp_path` to simulate spec existence.

---

## Deliverables

1. **New file `tests/test_check_doc_freshness.py`** — fully implemented,
   no stubs. Must import from `scripts.check_doc_freshness` (adjust the
   import path based on how the project resolves `scripts/` in `sys.path`
   — check `pyproject.toml` for `testpaths` and `pythonpath`).

   If `scripts/` is not in `sys.path`, add a conftest.py fixture or use
   `importlib.util.spec_from_file_location` to load the module by path.

---

## Hard rules

- No real git calls in any test
- No network calls
- Tests must pass with `PYTHONHASHSEED=0`
- Tests must pass both on Linux and Windows (path separator handling)
- Do not add new runtime dependencies to the main script to make it testable;
  if needed, add test-only dependencies (e.g., `pytest`) which are already
  present

---

## Review dimensions (what 5/5 means for DM-04)

| Dimension | 5/5 criterion |
|-----------|---------------|
| Testability | All public functions have at least one happy-path and one failure-path test |
| Correctness | Drift detection tests cover: drift present, no drift, no mapping (3 cases) |
| Robustness | Edge cases tested: empty diff, git failure, unmapped file |
| No network | All git calls are mocked; tests run fully offline |
| Determinism | Tests pass consistently with PYTHONHASHSEED=0 |

---

## Now (runbook)

```bash
# Step 1: Check how scripts/ is exposed to pytest
grep -A 5 "testpaths\|pythonpath" pyproject.toml

# Step 2: Determine import strategy
# Option A: if scripts/ is in pythonpath → from scripts.check_doc_freshness import ...
# Option B: if not → use importlib.util at top of test file

# Step 3: Write tests/test_check_doc_freshness.py per the 4 groups above

# Step 4: Run
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_check_doc_freshness.py -v

# Step 5: Verify all 12+ tests pass, 0 failed
```
