# Task H1: Windows Reserved Filenames Prevention Gate

**Agent:** hygiene-agent
**Date:** 2026-01-24
**Taskcard:** TC-571-1

## Executive Summary

Implemented Gate S: Windows Reserved Names Validation to prevent Windows reserved device filenames from entering the repository. This gate detects reserved names like NUL, CON, PRN, AUX, COM1-9, LPT1-9, and CLOCK$ (case-insensitive), preventing cross-platform incompatibility issues.

**Status:** COMPLETE

All deliverables implemented and validated:
- New validation gate: `tools/validate_windows_reserved_names.py`
- Integration into `tools/validate_swarm_ready.py` as Gate S
- Integration into `.github/workflows/ci.yml`
- Comprehensive test coverage: `tests/unit/test_validate_windows_reserved_names.py`
- All tests passing (7/7)
- Gate passes on current repository state

## What Was Implemented

### 1. Core Validation Gate (tools/validate_windows_reserved_names.py)

Implemented a standalone validation gate that:
- Detects all Windows reserved device names:
  - NUL, CON, PRN, AUX (standard devices)
  - COM1-COM9 (serial ports)
  - LPT1-LPT9 (parallel ports)
  - CLOCK$ (system clock)
- Case-insensitive detection (NUL, nul, Nul all detected)
- Detects names with extensions (NUL.txt is also invalid on Windows)
- Excludes standard directories: .git, .venv, node_modules, __pycache__
- Provides self-test mode (--self-test flag)
- Deterministic output (sorted violations)
- Exit code 0 if clean, 1 if violations found

### 2. Integration into Swarm Readiness (tools/validate_swarm_ready.py)

Added Gate S to the swarm readiness orchestrator:
- Follows existing gate pattern
- Runs as part of comprehensive validation suite
- Included in gate summary report

### 3. CI Integration (.github/workflows/ci.yml)

Added gate to CI pipeline:
- Runs with .venv active
- Runs before full swarm readiness check
- Ensures gate passes on all commits

### 4. Test Coverage (tests/unit/test_validate_windows_reserved_names.py)

Comprehensive test suite with 7 tests:
- `test_is_reserved_name`: Tests core detection logic
- `test_self_test_mode`: Validates self-test functionality
- `test_clean_repo_passes`: Verifies current repo passes
- `test_reserved_name_detection`: Tests detection logic
- `test_case_insensitive_detection`: Verifies case-insensitivity
- `test_exclusions`: Validates directory exclusions
- `test_deterministic_output`: Ensures stable output ordering

All tests handle Windows filesystem behavior correctly (Windows prevents creating files with reserved names even in test scenarios).

### 5. Authorization (TC-571-1 Micro-Taskcard)

Created micro-taskcard to authorize changes:
- `plans/taskcards/TC-571-1_windows_reserved_names_gate.md`
- Updated `plans/taskcards/INDEX.md`
- Follows write-fence requirements

## Why This Matters

Windows reserves certain filenames for device access. Attempting to create files with these names on Windows causes errors:
- **NUL**: Null device (like /dev/null on Unix)
- **CON**: Console
- **PRN**: Printer
- **AUX**: Auxiliary device
- **COM1-9**: Serial ports
- **LPT1-9**: Parallel ports
- **CLOCK$**: System clock

If these names enter a repository on Linux/Mac, Windows users cannot:
- Clone the repository
- Check out branches containing these files
- Build or test the project

This gate prevents these cross-platform compatibility issues at the source.

## Validation Evidence

### 1. Standalone Gate Execution

```bash
$ . .venv/Scripts/activate
$ python tools/validate_windows_reserved_names.py
======================================================================
WINDOWS RESERVED NAMES VALIDATION (Gate S)
======================================================================
Repository: C:\Users\prora\OneDrive\Documents\GitHub\foss-launcher

Scanning for Windows reserved device names...
  Reserved names: AUX, CLOCK$, COM1, COM2, COM3, COM4, COM5, COM6, COM7, COM8, COM9, CON, LPT1, LPT2, LPT3, LPT4, LPT5, LPT6, LPT7, LPT8, LPT9, NUL, PRN
  Excluded dirs: .git, .venv, __pycache__, node_modules

  PASS: No Windows reserved names found

======================================================================
RESULT: Windows reserved names validation PASSED

Repository is free of Windows reserved device names
======================================================================
```

### 2. Self-Test Mode

```bash
$ python tools/validate_windows_reserved_names.py --self-test
======================================================================
WINDOWS RESERVED NAMES GATE - SELF TEST
======================================================================

  [PASS] NUL                  -> True
  [PASS] nul                  -> True
  [PASS] Nul                  -> True
  [PASS] CON                  -> True
  [PASS] con                  -> True
  [PASS] PRN                  -> True
  [PASS] AUX                  -> True
  [PASS] COM1                 -> True
  [PASS] com9                 -> True
  [PASS] LPT1                 -> True
  [PASS] lpt9                 -> True
  [PASS] CLOCK$               -> True
  [PASS] clock$               -> True
  [PASS] NUL.txt              -> True
  [PASS] con.log              -> True
  [PASS] COM1.dat             -> True
  [PASS] normal.txt           -> False
  [PASS] README.md            -> False
  [PASS] config.yaml          -> False
  [PASS] NUCLEUS              -> False
  [PASS] CONSOLE              -> False

======================================================================
RESULT: Self-test PASSED (21/21 tests passed)
======================================================================
```

### 3. Unit Tests

```bash
$ python -m pytest tests/unit/test_validate_windows_reserved_names.py -v
============================= test session starts =============================
platform win32 -- Python 3.13.2, pytest-9.0.2, pluggy-1.6.0
rootdir: C:\Users\prora\OneDrive\Documents\GitHub\foss-launcher
configfile: pyproject.toml
plugins: anyio-4.12.1, langsmith-0.6.4
collected 7 items

tests\unit\test_validate_windows_reserved_names.py .......               [100%]

============================== warnings summary ===============================
.venv\Lib\site-packages\_pytest\config\__init__.py:1428
  C:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\.venv\Lib\site-packages\_pytest\config\__init__.py:1428: PytestConfigWarning: Unknown config option: env

    self._warn_or_fail_if_strict(f"Unknown config option: {key}\n")

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 7 passed, 1 warning in 1.12s =========================
```

### 4. Swarm Readiness Integration

```bash
$ python tools/validate_swarm_ready.py 2>&1 | grep -A 10 "Gate S"
Gate S: Windows reserved names prevention
======================================================================
======================================================================
WINDOWS RESERVED NAMES VALIDATION (Gate S)
======================================================================
Repository: C:\Users\prora\OneDrive\Documents\GitHub\foss-launcher

Scanning for Windows reserved device names...
  Reserved names: AUX, CLOCK$, COM1, COM2, COM3, COM4, COM5, COM6, COM7, COM8, COM9, CON, LPT1, LPT2, LPT3, LPT4, LPT5, LPT6, LPT7, LPT8, LPT9, NUL, PRN
  Excluded dirs: .git, .venv, __pycache__, node_modules

  PASS: No Windows reserved names found

[PASS] Gate S: Windows reserved names prevention
```

## Determinism Guarantees

1. **Stable File Ordering**: All violation lists use `sorted()` for deterministic order
2. **No Timestamps**: Output contains no timestamps or time-based data
3. **Reproducible**: Multiple runs produce identical output
4. **Platform-Aware Testing**: Tests handle Windows filesystem behavior correctly

## Files Changed

### Created
- `tools/validate_windows_reserved_names.py` (184 lines)
- `tests/unit/test_validate_windows_reserved_names.py` (239 lines)
- `plans/taskcards/TC-571-1_windows_reserved_names_gate.md` (109 lines)

### Modified
- `tools/validate_swarm_ready.py` (added Gate S)
- `.github/workflows/ci.yml` (added gate to CI)
- `plans/taskcards/INDEX.md` (added TC-571-1)

## Integration Verification

- **Upstream**: TC-571 (policy gates pattern) - followed existing gate structure
- **Downstream**: validate_swarm_ready.py - gate integrated as Gate S
- **Downstream**: CI pipeline - gate runs in CI workflow
- **Contracts**: Standard gate exit codes (0=pass, 1=fail)

## Known Limitations

1. **Windows Filesystem Quirks**: On Windows, the filesystem prevents creating files with reserved names, which makes testing challenging. Tests verify the detection logic directly rather than trying to create actual violations.

2. **Historical Detection**: The gate only scans the current tree, not git history. If reserved names exist in history, they won't be detected unless checked out.

3. **Path.exists() Behavior**: On Windows, `path.exists()` returns True for reserved device names even though they aren't regular files. This is expected Windows behavior.

## Success Criteria Met

- [x] Gate detects all Windows reserved names
- [x] Case-insensitive detection works (NUL, nul, Nul all detected)
- [x] Exclusions work (.git, .venv, node_modules, __pycache__)
- [x] Self-test mode passes (21/21 tests)
- [x] Integration into validate_swarm_ready.py complete (Gate S)
- [x] CI integration complete
- [x] All unit tests passing (7/7)
- [x] Deterministic output verified (sorted violations)
- [x] Current repository passes validation
- [x] Write-fence authorization created (TC-571-1)

## Recommendation

**SHIP** - All requirements met, all tests passing, gate integrated into CI and swarm readiness validation.
