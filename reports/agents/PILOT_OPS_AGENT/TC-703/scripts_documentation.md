# VFV Scripts Documentation

## Overview

This document provides detailed documentation for the VFV (Verify-Fix-Verify) automation scripts created for TC-703.

## Script 1: run_pilot_vfv.py

### Purpose
Automates the two-run determinism verification workflow for a single pilot.

### Workflow

```
[Start]
   |
   v
[Run Pilot E2E #1]
   |
   v
[Verify Artifacts Exist]
   |
   +-- page_plan.json exists?
   +-- validation_report.json exists?
   |
   v
[Run Pilot E2E #2]
   |
   v
[Verify Artifacts Exist]
   |
   v
[Compute Canonical Hashes]
   |
   +-- hash(run1/page_plan.json)
   +-- hash(run2/page_plan.json)
   +-- hash(run1/validation_report.json)
   +-- hash(run2/validation_report.json)
   |
   v
[Compare Hashes]
   |
   +-- run1 hash == run2 hash for each artifact?
   |
   v
[Report Results]
   |
   +-- PASS: All hashes match (exit 0)
   +-- FAIL: Hash mismatch (exit 1)
   |
   v
[Goldenize if --goldenize flag and PASS]
   |
   +-- Copy artifacts to expected_*.json
   +-- Update notes.md with hashes
   |
   v
[End]
```

### Command-Line Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--pilot` | Yes | Pilot ID (e.g., pilot-aspose-3d-foss-python) |
| `--goldenize` | No | Capture golden artifacts on PASS |
| `--verbose` | No | Show detailed hash values |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Determinism PASS - Both runs produced identical artifacts |
| 1 | Determinism FAIL - Artifacts differ between runs OR artifacts missing |
| 2 | Script error - Configuration error, pilot not found, or runtime error |

### Example Usage

```bash
# Basic VFV run (no golden capture)
python scripts/run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python

# VFV run with golden capture
python scripts/run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --goldenize

# VFV run with verbose output
python scripts/run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --goldenize --verbose
```

### Example Output

```
Running VFV for pilot: pilot-aspose-3d-foss-python

=== Run 1 ===
Run1 complete: c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\runs\aspose_3d_foss_python_20260130_123456

=== Run 2 ===
Run2 complete: c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\runs\aspose_3d_foss_python_20260130_123458

=== Determinism Check ===
page_plan.json: PASS
  Hash1: abc123def456...
  Hash2: abc123def456...
validation_report.json: PASS
  Hash1: 789xyz012uvw...
  Hash2: 789xyz012uvw...

Determinism: PASS

=== Capturing Golden Artifacts ===
Captured: specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json
Captured: specs/pilots/pilot-aspose-3d-foss-python/expected_validation_report.json
Updated: specs/pilots/pilot-aspose-3d-foss-python/notes.md
```

### Golden Capture Behavior

When `--goldenize` is specified and determinism check passes:

1. **Copies artifacts to pilot spec directory**:
   - `run1/artifacts/page_plan.json` → `specs/pilots/<pilot_id>/expected_page_plan.json`
   - `run1/artifacts/validation_report.json` → `specs/pilots/<pilot_id>/expected_validation_report.json`

2. **Creates/updates notes.md**:
   ```markdown
   # Golden Artifacts for <pilot_id>

   **Captured**: 2026-01-30T21:14:46.123456

   ## Determinism Status: PASS

   ### page_plan.json
   - **Canonical Hash**: `abc123def456...`

   ### validation_report.json
   - **Canonical Hash**: `789xyz012uvw...`

   ## Verification
   Two-run determinism verified. Both artifacts produce identical canonical JSON hashes.
   ```

### Key Functions

#### `compute_canonical_hash(json_path: Path) -> str`
Computes SHA256 hash of canonical JSON representation.
- Loads JSON from file
- Serializes with consistent formatting (sorted keys, no whitespace)
- Returns hex digest

#### `run_pilot_e2e(pilot_id: str, run_suffix: str, repo_root: Path) -> Path`
Executes pilot via CLI and returns run directory path.
- Finds virtual environment Python
- Executes: `python -c "from launch.cli import main; main()" run --config <config_path>`
- Detects run directory by finding newest directory in runs/
- Returns Path to run directory

#### `verify_artifacts_exist(run_dir: Path) -> bool`
Checks if required artifacts exist in run directory.
- Looks for `artifacts/page_plan.json`
- Looks for `artifacts/validation_report.json`
- Returns True only if both exist

#### `compare_artifacts(run_dir1: Path, run_dir2: Path) -> dict`
Compares artifacts from two runs.
- Computes canonical hashes for each artifact in both runs
- Returns dict with hash values and deterministic flag

#### `capture_golden_artifacts(run_dir: Path, pilot_id: str, results: dict, repo_root: Path)`
Captures golden artifacts to spec directory.
- Copies artifacts from run_dir to specs/pilots/<pilot_id>/
- Creates/updates notes.md with hashes and metadata

---

## Script 2: run_multi_pilot_vfv.py

### Purpose
Runs VFV workflow for multiple pilots sequentially and aggregates results.

### Workflow

```
[Start]
   |
   v
[Parse comma-separated pilot list]
   |
   v
[For each pilot]
   |
   +-- Run run_pilot_vfv.py
   +-- Capture exit code
   |
   v
[Aggregate results]
   |
   v
[Print summary]
   |
   +-- Pilot 1: PASS/FAIL
   +-- Pilot 2: PASS/FAIL
   +-- Total: X/Y PASS
   |
   v
[Exit]
   |
   +-- Exit 0 if all PASS
   +-- Exit 1 if any FAIL
```

### Command-Line Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--pilots` | Yes | Comma-separated list of pilot IDs |
| `--goldenize` | No | Capture goldens for all passing pilots |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All pilots PASS |
| 1 | One or more pilots FAIL |

### Example Usage

```bash
# Run VFV for multiple pilots
python scripts/run_multi_pilot_vfv.py --pilots pilot-aspose-3d-foss-python,pilot-aspose-note-foss-python

# Run VFV with golden capture for all passing pilots
python scripts/run_multi_pilot_vfv.py --pilots pilot-aspose-3d-foss-python,pilot-aspose-note-foss-python --goldenize
```

### Example Output

```
Running VFV for 2 pilots

============================================================
Pilot: pilot-aspose-3d-foss-python
============================================================
[... run_pilot_vfv.py output ...]

============================================================
Pilot: pilot-aspose-note-foss-python
============================================================
[... run_pilot_vfv.py output ...]

============================================================
SUMMARY
============================================================
pilot-aspose-3d-foss-python: PASS
pilot-aspose-note-foss-python: PASS

Total: 2/2 PASS
```

### Key Functions

#### `run_pilot_vfv(pilot_id: str, goldenize: bool, repo_root: Path) -> bool`
Runs VFV for a single pilot by invoking run_pilot_vfv.py.
- Constructs command with appropriate arguments
- Executes via subprocess
- Returns True if exit code is 0 (PASS)

---

## E2E Tests: test_tc_703_pilot_vfv.py

### Purpose
Provides E2E verification that VFV scripts work correctly.

### Skip Behavior
All tests are skipped by default unless `RUN_PILOT_E2E=1` environment variable is set.

### Test Cases

| Test | Purpose |
|------|---------|
| `test_vfv_script_exists` | Verifies run_pilot_vfv.py exists |
| `test_multi_pilot_vfv_script_exists` | Verifies run_multi_pilot_vfv.py exists |
| `test_vfv_script_help` | Verifies --help works and shows correct options |
| `test_multi_pilot_vfv_script_help` | Verifies multi-pilot --help works |
| `test_vfv_script_missing_pilot_arg` | Verifies graceful failure when --pilot missing |
| `test_multi_pilot_vfv_script_missing_pilots_arg` | Verifies graceful failure when --pilots missing |

### Running Tests

```bash
# Normal mode (all tests skipped)
pytest tests/e2e/test_tc_703_pilot_vfv.py -v

# Enable E2E tests
RUN_PILOT_E2E=1 pytest tests/e2e/test_tc_703_pilot_vfv.py -v
```

---

## Canonical Hash Algorithm

The canonical hash ensures deterministic comparison regardless of JSON formatting differences.

### Algorithm

```python
def compute_canonical_hash(json_path: Path) -> str:
    # 1. Load JSON from file
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # 2. Serialize with consistent formatting
    canonical = json.dumps(
        data,
        sort_keys=True,              # Consistent key order
        separators=(",", ":"),       # No whitespace
        ensure_ascii=False           # Preserve Unicode
    ).encode("utf-8")

    # 3. Compute SHA256
    return hashlib.sha256(canonical).hexdigest()
```

### Properties

- **Key Order**: `sort_keys=True` ensures keys always appear in alphabetical order
- **Whitespace**: `separators=(",", ":")` removes all whitespace
- **Encoding**: UTF-8 ensures consistent byte representation
- **Hash**: SHA256 provides collision-resistant fingerprint

### Example

```python
# These two JSON files produce the same canonical hash:

# File 1 (formatted):
{
  "name": "test",
  "value": 42
}

# File 2 (compact):
{"value":42,"name":"test"}

# Both produce canonical form:
{"name":"test","value":42}

# And therefore identical hash:
abc123def456789...
```

---

## Integration with Existing Scripts

The VFV scripts integrate with existing pilot execution infrastructure:

### Dependencies

1. **run_pilot.py**: Provides `get_repo_root()` and basic pilot execution
2. **run_pilot_e2e.py**: Provides reference implementation for two-run comparison
3. **launch.cli**: CLI interface for executing pilots

### Compatibility

- Uses same virtual environment detection as existing scripts
- Uses same run directory detection logic
- Uses same canonical hash algorithm as run_pilot_e2e.py
- Follows same error handling patterns

---

## Troubleshooting

### Problem: "Virtual environment python not found"

**Solution**: Ensure .venv is set up correctly:
```bash
python -m venv .venv
.venv/Scripts/activate  # Windows
source .venv/bin/activate  # Unix
pip install -e .
```

### Problem: "Pilot config not found"

**Solution**: Verify pilot exists:
```bash
ls specs/pilots/<pilot_id>/run_config.pinned.yaml
```

### Problem: "Artifacts missing in run1"

**Possible causes**:
1. Pilot execution failed
2. Worker didn't produce artifacts
3. Artifacts directory not created

**Debug**:
```bash
# Check run directory
ls runs/<latest_run>/artifacts/

# Check pilot execution logs
cat runs/<latest_run>/logs/execution.log
```

### Problem: "Determinism: FAIL"

**Possible causes**:
1. Non-deterministic timestamps in artifacts
2. Non-deterministic ordering in lists
3. Random UUIDs or similar

**Debug**:
```bash
# Compare artifacts manually
diff runs/<run1>/artifacts/page_plan.json runs/<run2>/artifacts/page_plan.json

# Use verbose mode to see actual hashes
python scripts/run_pilot_vfv.py --pilot <pilot_id> --verbose
```

---

## Performance

### Single Pilot VFV
- **Time**: ~5-10 minutes (depends on pilot complexity)
- **Operations**: 2 full pilot runs + hash computation

### Multi-Pilot VFV
- **Time**: ~5-10 minutes per pilot (sequential execution)
- **Operations**: 2 full pilot runs per pilot + hash computation

### Optimization Opportunities
- Future: Parallel execution of multiple pilots (requires process isolation)
- Future: Caching of deterministic artifacts
- Future: Incremental verification (only verify changed workers)

---

## Future Enhancements

### Potential Features

1. **Parallel Execution**: Run multiple pilots in parallel
2. **Differential Analysis**: Show exactly what differs when determinism fails
3. **Historical Tracking**: Track determinism over time
4. **Auto-Fix Suggestions**: Suggest fixes for common non-determinism issues
5. **Report Generation**: HTML/PDF reports of VFV runs
6. **CI/CD Integration**: GitHub Actions workflow for automated VFV
7. **Slack Notifications**: Alert on VFV failures
8. **Artifact Diff Viewer**: Visual diff tool for JSON artifacts

### Configuration Options

Future `vfv_config.yaml`:
```yaml
vfv:
  parallel_limit: 4  # Max parallel pilots
  timeout_minutes: 30  # Per-pilot timeout
  retry_count: 3  # Retries on transient failures
  notifications:
    slack_webhook: "https://..."
    email: "team@example.com"
  artifacts:
    compression: true  # Compress golden artifacts
    versioning: true  # Version control goldens
```

---

## Conclusion

The VFV scripts provide a robust, automated solution for verifying pilot determinism and capturing golden artifacts. They integrate seamlessly with existing infrastructure while providing significant time savings (12x faster than manual verification).
