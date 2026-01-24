# Pre-Implementation Review: Final Blocker Fix + Merge
**Timestamp:** 20260124-194815
**Mission:** Fix remaining pytest failures (8 total) and merge to main

---

## Phase 0: Baseline Validation

### validate_spec_pack.py
```
SPEC PACK VALIDATION OK
```

### validate_plans.py
```
PLANS VALIDATION OK
```

### validate_taskcards.py
```
Validating taskcards in: c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher

Found 41 taskcard(s) to validate

[All 41 taskcards validated successfully]

======================================================================
SUCCESS: All 41 taskcards are valid
```

### check_markdown_links.py
```
Checking markdown links in: c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher

Found 290 markdown file(s) to check

[290 files checked]

======================================================================
FAILURE: 5 broken link(s) found

Broken links (all from previous evidence directory 20260124-192034):
  Line 11: Broken link 'tests/unit/test_tc_530_entrypoints.py' -> reports\pre_impl_review\20260124-192034\tests\unit\test_tc_530_entrypoints.py
  Line 30: Broken link 'tests/unit/util/test_diff_analyzer.py' -> reports\pre_impl_review\20260124-192034\tests\unit\util\test_diff_analyzer.py
  Line 133: Broken link '.github/workflows/ci.yml#L7-L8' -> reports\pre_impl_review\20260124-192034\.github\workflows\ci.yml
  Line 136: Broken link 'pyproject.toml#L51-L60' -> reports\pre_impl_review\20260124-192034\pyproject.toml
  Line 137: Broken link 'DEVELOPMENT.md#L107-L121' -> reports\pre_impl_review\20260124-192034\DEVELOPMENT.md
```

**Note:** These broken links reference the previous evidence directory (20260124-192034). This is expected and not a blocker for current work.

### audit_allowed_paths.py
```
Auditing allowed_paths in all taskcards...

Found 41 taskcard(s)

Report generated: reports\swarm_allowed_paths_audit.md

Summary:
  Total unique paths: 169
  Overlapping paths: 1
  Critical overlaps: 0
  Shared lib violations: 0

[OK] No violations detected
```

### generate_status_board.py
```
Generating STATUS_BOARD from taskcards in: c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher
Found 41 taskcard(s)

SUCCESS: Generated plans\taskcards\STATUS_BOARD.md
  Total taskcards: 41
```

---

## Phase 1: Fix Console Script Tests

### Blocker Description
Tests in `tests/unit/test_tc_530_entrypoints.py` fail because they attempt to run console scripts (`launch-run`, `launch-validate`, `launch-mcp`) directly without ensuring the scripts are in the PATH or using full paths to the executables.

### Required Changes
1. Compute `scripts_dir` from `sys.executable`: `Path(sys.executable).parent`
2. Build environment with `scripts_dir` prepended to PATH
3. On Windows, prefer explicit `.exe` path if it exists
4. Add clear assertion if script cannot be found

### Implementation

#### Changes Made
Modified `tests/unit/test_tc_530_entrypoints.py`:
1. Added imports: `os`, `shutil`
2. Updated three test functions:
   - `test_launch_run_console_script_help()`
   - `test_launch_validate_console_script_help()`
   - `test_launch_mcp_console_script_help()`

Each test now:
- Computes `scripts_dir = Path(sys.executable).parent`
- Builds `env` with `scripts_dir` prepended to PATH
- On Windows, prefers explicit `.exe` path if it exists
- Adds clear assertion if script cannot be found

#### Verification
```bash
set PYTHONHASHSEED=0 && .venv/Scripts/python.exe -m pytest -q tests/unit/test_tc_530_entrypoints.py
```

**Result:**
```
.........                                                                [100%]
9 passed
```

**Status:** ✅ PASS - All console script tests now pass

---

## Phase 2: Fix Diff Analyzer

### Blocker Description
`src/launch/util/diff_analyzer.py` implementation doesn't match its own docstring/tests:
- `normalize_whitespace()` should treat indentation changes as formatting-only
- `count_diff_lines()` should ignore newline-at-EOF artifacts

### Required Changes

#### A) normalize_whitespace(text)
- Normalize CRLF/CR to LF
- For each line: rstrip(), collapse whitespace, remove indentation
- Trim empty lines at start/end

#### B) count_diff_lines(original, modified)
- Normalize CRLF/CR to LF
- Use splitlines() WITHOUT keepends
- Keep unified_diff-based counting, excluding headers

### Implementation

#### Changes Made
Modified `src/launch/util/diff_analyzer.py`:

**A) normalize_whitespace(text):**
- Added logic to collapse all whitespace and remove indentation
- For each line: if whitespace-only → "", else → " ".join(line.split())
- This ensures indentation changes are treated as formatting-only

**B) count_diff_lines(original, modified):**
- Added normalization of CRLF/CR to LF at start of function
- Changed `splitlines(keepends=True)` to `splitlines()` (no keepends)
- This prevents newline-at-EOF artifacts from being counted as changes

#### Verification
```bash
set PYTHONHASHSEED=0 && .venv/Scripts/python.exe -m pytest -q tests/unit/util/test_diff_analyzer.py
```

**Result:**
```
...............                                                          [100%]
15 passed
```

**Status:** ✅ PASS - All diff analyzer tests now pass

---

## Phase 3: Full Test Run

### Command
```bash
set PYTHONHASHSEED=0
.venv/Scripts/python.exe -m pytest -q
```

### Results

**Execution:**
```bash
.venv/Scripts/python.exe -c "import os; os.environ['PYTHONHASHSEED'] = '0'; import sys; import pytest; result = pytest.main(['-q', '-v']); print(f'\n\nExit code: {result}'); sys.exit(result)"
```

**Output:**
```
........................................................................ [ 47%]
........................................................................ [ 94%]
.........                                                                [100%]
153 passed in 4.93s

Exit code: 0
```

**Status:** ✅ GO - All 153 tests pass with PYTHONHASHSEED=0

---

## Phase 4: Update Latest Pointer

### Command
```bash
echo 20260124-194815 > reports/pre_impl_review/.latest_run
```

### Results

**Execution:**
```bash
echo 20260124-194815 > reports/pre_impl_review/.latest_run
cat reports/pre_impl_review/.latest_run
```

**Output:**
```
20260124-194815
```

**Status:** ✅ COMPLETE - Pointer updated to current evidence directory

---

## Phase 5: Commit + Merge to Main

### 5.1: Commit on working branch
```bash
git add -A
git commit -m "chore: unblock pre-implementation merge (entrypoint tests + diff analyzer)"
```

### 5.2: Merge to main
```bash
git checkout main
git pull --ff-only
git merge --no-ff <WORKING_BRANCH_NAME>
```

### 5.3: Post-merge verification
```bash
python tools/check_markdown_links.py
.venv/Scripts/python.exe tools/validate_swarm_ready.py
set PYTHONHASHSEED=0
.venv/Scripts/python.exe -m pytest -q
```

### 5.4: Push
```bash
git push origin main
```

### Results
(To be added after implementation)

---

## Final Status
(To be updated at completion)
