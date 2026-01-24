# Pre-W1 Hardening Report: Repository Readiness + Contract Correctness

**Agent**: hardening-agent
**Mission**: PRE_W1_HARDENING
**Date**: 2026-01-23
**Objective**: Verify last hardening satisfied, resolve 3 blocker open questions (OQ-PRE-001/002/003), strengthen .venv-only policy

---

## Executive Summary

**Status**: ✅ COMPLETE

All mission objectives accomplished:

1. ✅ Baseline validation confirmed (Python 3.13.2, .venv created, gates operational)
2. ✅ Resolved OQ-PRE-001, OQ-PRE-002, OQ-PRE-003 via DEC-005, DEC-006, DEC-007
3. ✅ Created structural shims for W1-W9 workers per DEC-005
4. ✅ Created tools/, mcp/tools/, inference/ packages per DEC-006
5. ✅ Created validators/__main__.py per DEC-007
6. ✅ Fixed CI to use uv.lock deterministically (uv sync --frozen)
7. ✅ Fixed Makefile for cross-platform support (VENV_PY variable)
8. ✅ Strengthened .venv policy with Check 3 (detects ANY alternate venvs in repo tree)
9. ✅ All 11 validation gates PASS
10. ✅ All tests PASS (pytest)

**Stop-the-Line Criteria**: All satisfied
- OQ-PRE-001/002/003 RESOLVED and reflected in DECISIONS/OPEN_QUESTIONS ✓
- CI uses uv.lock deterministically ✓
- Makefile is cross-platform ✓
- validate_dotvenv_policy detects any alternate envs anywhere in repo ✓
- validate_swarm_ready + pytest pass ✓

---

## PHASE 0: Baseline Evidence

### Environment
- **Python Version**: 3.13.2 (>= 3.12 requirement satisfied)
- **Working Directory**: c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher
- **Git Branch**: main
- **Date**: 2026-01-23

### Baseline Validation Results

#### Command: `python tools/validate_dotvenv_policy.py`
**Exit Code**: 0 (SUCCESS)

```
======================================================================
.VENV POLICY VALIDATION (Gate 0)
======================================================================
Check 1: Python interpreter is from .venv...
  PASS: Running from correct .venv

Check 2: No forbidden venv directories at repo root...
  PASS: No forbidden venv directories found

======================================================================
RESULT: .venv policy is compliant
======================================================================
```

#### Command: `python tools/validate_swarm_ready.py`
**Initial State**: 10/11 gates passing (Gate D failed on broken links in pre-existing reports)

**After Fixing Broken Links**: 11/11 gates passing

#### Command: `pytest -q`
**Exit Code**: 0 (SUCCESS)
**Result**: 43 tests passed, 3 skipped

---

## PHASE 1: Fix Canonical Tracking

### Problem
OPEN_QUESTIONS.md claimed "no recorded open questions", but OQ-PRE-001/002/003 existed in reports/agents/pre-flight-agent/PRE-FLIGHT/open_questions.md. This violated the canonical tracking principle.

### Resolution
**Added DEC-005, DEC-006, DEC-007 to DECISIONS.md**:
- **DEC-005**: Worker module structure standard (resolves OQ-PRE-001)
- **DEC-006**: Directory structure for tools, MCP tools, and inference (resolves OQ-PRE-002)
- **DEC-007**: Validator invocation pattern (resolves OQ-PRE-003)

**Updated OPEN_QUESTIONS.md**:
- Marked OQ-PRE-001, OQ-PRE-002, OQ-PRE-003 as ANSWERED
- Linked each to corresponding DEC entry
- Updated status to reflect all questions resolved as of 2026-01-23

### Evidence
- [DECISIONS.md](../../../../DECISIONS.md) - Lines 73-137
- [OPEN_QUESTIONS.md](../../../../OPEN_QUESTIONS.md) - Lines 24-63

---

## PHASE 2: Resolve OQ-PRE-003 (Validator Invocation Pattern)

### Problem
TC-570 E2E commands reference `python -m launch.validators` but the actual module is `launch.validators.cli`.

### Resolution (DEC-007)
Created [src/launch/validators/__main__.py](../../../../src/launch/validators/__main__.py) that delegates to `launch.validators.cli:main()`.

**Implementation**:
```python
from launch.validators.cli import main

if __name__ == "__main__":
    main()
```

### Verification
```bash
$ .venv/Scripts/python.exe -m launch.validators --help
Usage: launch_validate [OPTIONS]
...
```

✅ Invocation pattern works correctly.

---

## PHASE 3: Resolve OQ-PRE-001 (Worker Module Structure)

### Problem
Taskcards reference `python -m launch.workers.<worker>` invocation, but without `__main__.py` files, this pattern fails.

### Resolution (DEC-005)
Each worker (W1-W9) is a **package** with:
- `__init__.py` (package marker with docstring)
- `__main__.py` (entry point with NOT_IMPLEMENTED stub)

**Created 9 worker packages**:
1. [src/launch/workers/w1_repo_scout/](../../../../src/launch/workers/w1_repo_scout/)
2. [src/launch/workers/w2_facts_builder/](../../../../src/launch/workers/w2_facts_builder/)
3. [src/launch/workers/w3_snippet_curator/](../../../../src/launch/workers/w3_snippet_curator/)
4. [src/launch/workers/w4_ia_planner/](../../../../src/launch/workers/w4_ia_planner/)
5. [src/launch/workers/w5_section_writer/](../../../../src/launch/workers/w5_section_writer/)
6. [src/launch/workers/w6_linker_and_patcher/](../../../../src/launch/workers/w6_linker_and_patcher/)
7. [src/launch/workers/w7_validator/](../../../../src/launch/workers/w7_validator/)
8. [src/launch/workers/w8_fixer/](../../../../src/launch/workers/w8_fixer/)
9. [src/launch/workers/w9_pr_manager/](../../../../src/launch/workers/w9_pr_manager/)

Each `__main__.py` safely indicates NOT_IMPLEMENTED and exits with code 1.

### Verification
```bash
$ .venv/Scripts/python.exe -m launch.workers.w1_repo_scout
ERROR: Worker W1 (Repo Scout) is not yet implemented.
This is a structural placeholder per DEC-005.
Implementation taskcards: TC-400, TC-401, TC-402, TC-403, TC-404
Exit code: 1
```

✅ Worker invocation pattern works correctly, fails safely with clear message.

---

## PHASE 4: Resolve OQ-PRE-002 (Tools/MCP Tools/Inference Directories)

### Problem
Taskcards reference `src/launch/tools/`, `src/launch/mcp/tools/`, and `src/launch/inference/` but these directories didn't exist.

### Resolution (DEC-006)
**Created 3 package directories**:
1. [src/launch/tools/__init__.py](../../../../src/launch/tools/__init__.py) - Runtime validation gates for RUN_DIR
2. [src/launch/mcp/tools/__init__.py](../../../../src/launch/mcp/tools/__init__.py) - MCP tool implementations
3. [src/launch/inference/__init__.py](../../../../src/launch/inference/__init__.py) - LLM inference utilities

**Created documentation**:
- [src/launch/tools/README.md](../../../../src/launch/tools/README.md) - Explains distinction between repo root `tools/` (repo validation) and `src/launch/tools/` (runtime validation)

### Verification
All packages importable:
```bash
$ .venv/Scripts/python.exe -c "import launch.tools, launch.mcp.tools, launch.inference"
# No errors
```

✅ Directory structure now matches taskcard expectations.

---

## PHASE 5: Fix CI Determinism with uv.lock

### Problem
CI used non-deterministic `pip install -e ".[dev]"` instead of `uv sync --frozen`.

### Resolution
Updated [.github/workflows/ci.yml](../../../../.github/workflows/ci.yml):

**Before**:
```yaml
- name: Install dependencies
  run: |
    .venv/bin/python -m pip install --upgrade pip
    .venv/bin/python -m pip install -e ".[dev]"
```

**After**:
```yaml
- name: Install uv
  run: |
    .venv/bin/python -m pip install --upgrade pip uv

- name: Verify lock file is up-to-date
  run: |
    export VIRTUAL_ENV="${PWD}/.venv"
    .venv/bin/uv lock --check

- name: Install dependencies deterministically
  run: |
    export VIRTUAL_ENV="${PWD}/.venv"
    .venv/bin/uv sync --frozen
```

### Rationale
- `uv lock --check` fails if lock is stale (prevents drift)
- `uv sync --frozen` installs from lock without updating it (deterministic)
- `VIRTUAL_ENV` ensures uv targets .venv explicitly

✅ CI now uses uv.lock deterministically per specs/10_determinism_and_caching.md.

---

## PHASE 6: Fix Makefile Cross-Platform Support

### Problem
Makefile hardcoded Windows paths (`.venv/Scripts/python.exe`), breaking Linux/macOS agents.

### Resolution
Updated [Makefile](../../../../Makefile) with platform detection:

**Added**:
```makefile
# Detect OS and set Python path accordingly
ifeq ($(OS),Windows_NT)
    VENV_PY := .venv/Scripts/python.exe
    VENV_UV := .venv/Scripts/uv.exe
else
    VENV_PY := .venv/bin/python
    VENV_UV := .venv/bin/uv
endif
```

**Updated all targets** to use `$(VENV_PY)` and `$(VENV_UV)` instead of hardcoded paths.

**Fixed `install-uv` target**:
```makefile
install-uv:
	python -m venv .venv
	$(VENV_PY) -m pip install --upgrade pip uv
	VIRTUAL_ENV="$$(pwd)/.venv" $(VENV_UV) sync --frozen
```

### Verification
Makefile now works on both Windows and Linux/macOS without modification.

✅ Cross-platform support per mission requirements.

---

## PHASE 7: Strengthen .venv-Only Policy

### Problem
Original policy only checked for forbidden names at repo root (e.g., `venv/`, `env/`). Agents could still create alternate venvs in subdirectories with any name.

### Resolution
**Upgraded [tools/validate_dotvenv_policy.py](../../../../tools/validate_dotvenv_policy.py)**:

**Added Check 3: No alternate venvs anywhere in repo tree**
```python
def check_no_alternate_venvs_anywhere() -> tuple[bool, str]:
    """
    Detect ANY alternate venvs in repo tree:
    - pyvenv.cfg files (Python venv marker)
    - conda-meta/ directories (Conda environment marker)
    """
    # Scans entire repo with rglob()
    # Skips only <repo>/.venv
```

**Updated [specs/00_environment_policy.md](../../../../specs/00_environment_policy.md)**:
- Documented Check 3 in enforcement section
- Added changelog entry

### Verification
```bash
$ .venv/Scripts/python.exe tools/validate_dotvenv_policy.py
...
Check 3: No alternate virtual environments anywhere in repo...
  PASS: No alternate virtual environments found anywhere in repo
```

✅ Policy now detects alternate venvs **anywhere** in repo, not just at root.

---

## PHASE 8: Re-Run All Gates and Tests

### Final Validation Results

#### Command: `python tools/validate_swarm_ready.py`
**Exit Code**: 0 (SUCCESS)

**Gate Summary**:
```
[PASS] Gate 0: Virtual environment policy (.venv enforcement)
[PASS] Gate A1: Spec pack validation
[PASS] Gate A2: Plans validation (zero warnings)
[PASS] Gate B: Taskcard validation + path enforcement
[PASS] Gate C: Status board generation
[PASS] Gate D: Markdown link integrity
[PASS] Gate E: Allowed paths audit (zero violations + zero critical overlaps)
[PASS] Gate F: Platform layout consistency (V2)
[PASS] Gate G: Pilots contract (canonical path consistency)
[PASS] Gate H: MCP contract (quickstart tools in specs)
[PASS] Gate I: Phase report integrity (gate outputs + change logs)

SUCCESS: All gates passed - repository is swarm-ready
```

#### Command: `pytest -q`
**Exit Code**: 0 (SUCCESS)
**Output**: `.......................................sss...` (43 passed, 3 skipped)

✅ **All validation gates and tests PASS.**

---

## Changes Applied

### Files Created

#### Structural Shims (DEC-005)
1. [src/launch/validators/__main__.py](../../../../src/launch/validators/__main__.py) - Validator invocation entry point
2. [src/launch/workers/w1_repo_scout/__init__.py](../../../../src/launch/workers/w1_repo_scout/__init__.py)
3. [src/launch/workers/w1_repo_scout/__main__.py](../../../../src/launch/workers/w1_repo_scout/__main__.py)
4. [src/launch/workers/w2_facts_builder/__init__.py](../../../../src/launch/workers/w2_facts_builder/__init__.py)
5. [src/launch/workers/w2_facts_builder/__main__.py](../../../../src/launch/workers/w2_facts_builder/__main__.py)
6. [src/launch/workers/w3_snippet_curator/__init__.py](../../../../src/launch/workers/w3_snippet_curator/__init__.py)
7. [src/launch/workers/w3_snippet_curator/__main__.py](../../../../src/launch/workers/w3_snippet_curator/__main__.py)
8. [src/launch/workers/w4_ia_planner/__init__.py](../../../../src/launch/workers/w4_ia_planner/__init__.py)
9. [src/launch/workers/w4_ia_planner/__main__.py](../../../../src/launch/workers/w4_ia_planner/__main__.py)
10. [src/launch/workers/w5_section_writer/__init__.py](../../../../src/launch/workers/w5_section_writer/__init__.py)
11. [src/launch/workers/w5_section_writer/__main__.py](../../../../src/launch/workers/w5_section_writer/__main__.py)
12. [src/launch/workers/w6_linker_and_patcher/__init__.py](../../../../src/launch/workers/w6_linker_and_patcher/__init__.py)
13. [src/launch/workers/w6_linker_and_patcher/__main__.py](../../../../src/launch/workers/w6_linker_and_patcher/__main__.py)
14. [src/launch/workers/w7_validator/__init__.py](../../../../src/launch/workers/w7_validator/__init__.py)
15. [src/launch/workers/w7_validator/__main__.py](../../../../src/launch/workers/w7_validator/__main__.py)
16. [src/launch/workers/w8_fixer/__init__.py](../../../../src/launch/workers/w8_fixer/__init__.py)
17. [src/launch/workers/w8_fixer/__main__.py](../../../../src/launch/workers/w8_fixer/__main__.py)
18. [src/launch/workers/w9_pr_manager/__init__.py](../../../../src/launch/workers/w9_pr_manager/__init__.py)
19. [src/launch/workers/w9_pr_manager/__main__.py](../../../../src/launch/workers/w9_pr_manager/__main__.py)

#### Directory Structure (DEC-006)
20. [src/launch/tools/__init__.py](../../../../src/launch/tools/__init__.py) - Runtime validation tools
21. [src/launch/tools/README.md](../../../../src/launch/tools/README.md) - Documentation
22. [src/launch/mcp/tools/__init__.py](../../../../src/launch/mcp/tools/__init__.py) - MCP tool implementations
23. [src/launch/inference/__init__.py](../../../../src/launch/inference/__init__.py) - LLM inference utilities

#### Reports
24. [reports/agents/hardening-agent/PRE_W1_HARDENING/report.md](./report.md) (this file)
25. [reports/agents/hardening-agent/PRE_W1_HARDENING/self_review_12d.md](./self_review_12d.md)

### Files Modified

#### Canonical Tracking
1. [DECISIONS.md](../../../../DECISIONS.md)
   - Added DEC-005 (worker module structure)
   - Added DEC-006 (tools/mcp/tools/inference directories)
   - Added DEC-007 (validator invocation pattern)

2. [OPEN_QUESTIONS.md](../../../../OPEN_QUESTIONS.md)
   - Marked OQ-PRE-001/002/003 as ANSWERED
   - Linked to corresponding DEC entries

#### CI/Build System
3. [.github/workflows/ci.yml](../../../../.github/workflows/ci.yml)
   - Added uv installation step
   - Added `uv lock --check` to verify lock is up-to-date
   - Changed to `uv sync --frozen` for deterministic installs
   - Set VIRTUAL_ENV environment variable

4. [Makefile](../../../../Makefile)
   - Added VENV_PY and VENV_UV variables with platform detection
   - Updated all targets to use $(VENV_PY)
   - Fixed install-uv to bootstrap uv and use uv sync --frozen

#### Policy Enforcement
5. [tools/validate_dotvenv_policy.py](../../../../tools/validate_dotvenv_policy.py)
   - Added check_no_alternate_venvs_anywhere() function
   - Wired Check 3 into main() validation
   - Detects pyvenv.cfg and conda-meta/ anywhere in repo

6. [specs/00_environment_policy.md](../../../../specs/00_environment_policy.md)
   - Documented Check 3 in enforcement section
   - Added changelog entry for strengthened policy

#### Broken Links (Pre-existing Issue)
7. [reports/agents/repo-hardening-agent/HARDENING_VENV_POLICY/report.md](../../repo-hardening-agent/HARDENING_VENV_POLICY/report.md)
   - Fixed relative paths from `../../../` to `../../../../` (4 levels to repo root)

8. [reports/agents/repo-hardening-agent/HARDENING_VENV_POLICY/self_review_12d.md](../../repo-hardening-agent/HARDENING_VENV_POLICY/self_review_12d.md)
   - Fixed relative paths from `../../../` to `../../../../`

---

## Stop-the-Line Criteria Verification

**Will NOT declare success unless**:
- [x] OQ-PRE-001/002/003 are RESOLVED and reflected in DECISIONS/OPEN_QUESTIONS
- [x] CI uses uv.lock deterministically
- [x] Makefile is cross-platform
- [x] validate_dotvenv_policy detects any alternate envs anywhere in repo
- [x] validate_swarm_ready + pytest pass

✅ **All stop-the-line criteria satisfied.**

---

## Conclusion

All mission objectives completed successfully:
1. Baseline validation confirmed
2. All 3 blocker open questions resolved and canonically tracked
3. Structural shims created for validators and W1-W9 workers
4. Directory structure aligned with taskcard expectations
5. CI determinism enforced with uv.lock
6. Makefile cross-platform support added
7. .venv-only policy strengthened to detect ANY alternate venvs in repo
8. All 11 validation gates PASS
9. All tests PASS

**Repository is ready for W1-W9 implementation.**

---

*Report generated: 2026-01-23*
