# TC-923 Implementation Report

## Agent
AGENT_C (TC-922/TC-923 GATE D + GATE Q FIX)

## Implementation Date
2026-02-01

## Objective
Add missing canonical commands to `.github/workflows/ai-governance-check.yml` to satisfy Gate Q (CI parity) requirements as specified in specs/34_strict_compliance_guarantees.md (Guarantee H).

## Changes Made

### 1. Created TC-923 Taskcard
- File: `plans/taskcards/TC-923_fix_gate_q_ai_governance_workflow.md`
- Status: In-Progress
- Spec ref: fe58cc19b58e4929e814b63cd49af6b19e61b167

### 2. Updated .github/workflows/ai-governance-check.yml
Added the three required canonical commands:

#### Added Python Version Detection
```yaml
- name: Choose Python version file
  id: pyver
  shell: bash
  run: |
    if [ -f .python-version ]; then
      echo "file=.python-version" >> "$GITHUB_OUTPUT"
    else
      echo "file=pyproject.toml" >> "$GITHUB_OUTPUT"
    fi
```

#### Updated Python Setup
Changed from hardcoded Python 3.11 to use version file:
```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version-file: ${{ steps.pyver.outputs.file }}
```

#### Added uv Installation
```yaml
- name: Install uv
  uses: astral-sh/setup-uv@v7
  with:
    enable-cache: true
```

#### Added Dependency Installation (Canonical Command #1)
```yaml
- name: Install dependencies
  shell: bash
  run: make install-uv
```

#### Added Gate Validation (Canonical Command #2)
```yaml
- name: Run gates validation
  shell: bash
  run: |
    mkdir -p ci_artifacts
    ./.venv/bin/python tools/validate_swarm_ready.py | tee ci_artifacts/validate_swarm_ready.txt
```

#### Added Test Execution (Canonical Command #3)
```yaml
- name: Run tests
  shell: bash
  run: |
    ./.venv/bin/python -m pytest -q | tee ci_artifacts/pytest.txt
```

#### Added Artifact Upload
```yaml
- name: Upload CI logs
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: ai_governance_ci_artifacts
    path: ci_artifacts
```

### 3. Updated INDEX.md
Added TC-923 to the taskcards index under "Additional critical hardening" section.

### 4. Regenerated STATUS_BOARD.md
Ran `tools/generate_status_board.py` to include TC-923 in the status board.

## Verification Results

### Gate Q Status: PASS
```
Gate Q: CI parity (Guarantee H: canonical commands)
======================================================================
CI PARITY VALIDATION (Gate Q)
======================================================================
Repository: C:\Users\prora\OneDrive\Documents\GitHub\foss-launcher

Found 2 workflow(s) to validate

Checking: .github\workflows\ai-governance-check.yml
  PASS: All canonical commands present
Checking: .github\workflows\ci.yml
  PASS: All canonical commands present

======================================================================
RESULT: All CI workflows use canonical commands
======================================================================

[PASS] Gate Q: CI parity (Guarantee H: canonical commands)
```

All three canonical commands are now detected:
1. `make install-uv` - Dependency installation
2. `python tools/validate_swarm_ready.py` - Gate validation
3. `pytest` - Test execution

### Workflow Validation
- YAML syntax is valid
- Steps run in correct order: setup → install → validate → test
- Uses .venv Python interpreter for all Python commands
- Matches pattern from ci.yml workflow

### Test Results
- Pre-existing test failures in test_tc_400_repo_scout.py and test_tc_401_clone.py (10 failures)
- These failures are related to repo_url_validator and are NOT caused by TC-923 changes
- No new test failures introduced by workflow changes

## Success Criteria Met
- [x] Added Python setup step with version file detection
- [x] Added uv installation step
- [x] Added `make install-uv` step
- [x] Added `python tools/validate_swarm_ready.py` step using .venv Python
- [x] Added `pytest` step using .venv Python
- [x] Steps run in correct order
- [x] Workflow syntax is valid
- [x] Gate Q passes in validate_swarm_ready.py
- [x] TC-923 added to INDEX.md
- [x] STATUS_BOARD.md updated

## Impact
- Gate Q now passes (was failing with missing canonical commands)
- AI governance workflow now runs full validation suite
- CI workflows now have consistent command coverage
- Workflow will catch gate failures and test failures in PRs

## Evidence
- Modified file: .github/workflows/ai-governance-check.yml
- Taskcard: plans/taskcards/TC-923_fix_gate_q_ai_governance_workflow.md
- validate_swarm_ready.py output showing Gate Q PASS

## Notes
- The workflow now matches the canonical command pattern from ci.yml
- Uses .venv/bin/python (Linux) path - appropriate for GitHub Actions ubuntu-latest
- Maintains existing governance checks (branch approval, co-authorship, protected files)
- Adds CI artifacts upload for debugging
