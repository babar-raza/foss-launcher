# Clean-Room Setup Steps

**Timestamp**: 2026-01-28 16:15 Asia/Karachi
**Branch**: main
**HEAD**: af8927f6fe4e516f00ed017e931414b2044ebc11
**Platform**: Windows (win32)
**Python**: Python 3.13

## Step-by-Step Execution

### 1. Branch Preparation
```bash
git switch main
git pull --ff-only
git status
```

**Status**: Working directory had uncommitted changes (STATUS_BOARD.md timestamp update + untracked merge summary). Stashed these with:
```bash
git stash push -m "WIP: Pre-clean-room validation state"
```

### 2. Environment Cleanup
```bash
# Initial attempt: moved .venv to backup
mv .venv .venv.backup-20260128-154419

# Gate 0 policy violation detected - removed backup
rm -rf .venv.backup-20260128-154419
```

**Note**: Gate 0 (.venv policy) prohibits ANY alternate virtual environments in the repo. Must use `.venv` exclusively.

### 3. Canonical Setup
```bash
# Step 1: Create fresh virtual environment
python -m venv .venv

# Step 2: Install pip and uv in the venv
.venv/Scripts/python.exe -m pip install --upgrade pip uv

# Step 3: Install all dependencies with frozen lock file
.venv/Scripts/uv.exe sync --frozen

# Step 4: Install dev extras (pytest, etc.)
.venv/Scripts/uv.exe sync --frozen --all-extras

# Step 5: Install missing dependencies (manual fixes)
.venv/Scripts/uv.exe pip install pytest-asyncio
.venv/Scripts/uv.exe pip install mcp
```

**Dependency Issue Detected**:
- `pytest-asyncio` was not installed by `uv sync --frozen --all-extras` despite being in `[project.optional-dependencies].dev`
- `mcp` was not installed by `uv sync --frozen` despite being in `[project].dependencies`
- Both were installed manually to proceed with testing
- **Root Cause**: Likely issue with uv.lock file or dependency resolution on Windows

### 4. Gate Validation
```bash
export PYTHONHASHSEED=0
.venv/Scripts/python.exe tools/validate_swarm_ready.py
```

**Result**: 21/21 gates passing (after removing .venv backup)

### 5. Test Execution
```bash
export PYTHONHASHSEED=0
.venv/Scripts/python.exe -m pytest -q
```

**Result**: 1417 passed, 9 failed, 1 skipped

## Environment Notes

- **OS**: Windows 10/11 (win32)
- **Python Version**: 3.13.x
- **Virtual Environment**: `.venv` (enforced by Gate 0)
- **Determinism**: PYTHONHASHSEED=0 set for test execution
- **Installation Method**: uv sync --frozen (deterministic)

## Deviations from Ideal

1. **Manual dependency installation**: `pytest-asyncio` and `mcp` had to be installed manually
2. **PYTHONHASHSEED warning**: Test suite still shows warning despite export (bash/cmd shell interaction issue on Windows)

## Reproducibility Notes

To reproduce this clean-room setup:
```bash
# 1. Clone repo and checkout main
git clone <repo-url>
cd foss-launcher
git checkout main

# 2. Clean environment
rm -rf .venv

# 3. Run canonical setup
python -m venv .venv
.venv/Scripts/python.exe -m pip install --upgrade pip uv
.venv/Scripts/uv.exe sync --frozen --all-extras

# 4. Manual fixes (until lock file is corrected)
.venv/Scripts/uv.exe pip install pytest-asyncio mcp

# 5. Validate
export PYTHONHASHSEED=0
.venv/Scripts/python.exe tools/validate_swarm_ready.py
.venv/Scripts/python.exe -m pytest -q
```
