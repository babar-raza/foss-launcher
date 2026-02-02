---
id: TC-923
title: "Fix Gate Q CI workflow parity for ai-governance-check.yml"
status: In-Progress
owner: "AGENT_C"
updated: "2026-02-01"
depends_on: []
allowed_paths:
  - plans/taskcards/TC-923_fix_gate_q_ai_governance_workflow.md
  - plans/taskcards/INDEX.md
  - plans/taskcards/STATUS_BOARD.md
  - .github/workflows/ai-governance-check.yml
  - reports/agents/**/TC-923/**
evidence_required:
  - reports/agents/<agent>/TC-923/report.md
  - reports/agents/<agent>/TC-923/self_review.md
  - reports/agents/<agent>/TC-923/validate_swarm_ready_output.txt
spec_ref: fe58cc19b58e4929e814b63cd49af6b19e61b167
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-923 — Fix Gate Q CI workflow parity for ai-governance-check.yml

## Objective
Add missing canonical commands to `.github/workflows/ai-governance-check.yml` to satisfy Gate Q (CI parity) requirements as specified in specs/34_strict_compliance_guarantees.md (Guarantee H).

## Problem
Gate Q (CI parity) fails because the `ai-governance-check.yml` workflow is missing the three canonical commands required across all CI workflows:
1. `make install-uv` (or `make install`) - dependency installation
2. `python tools/validate_swarm_ready.py` - gate validation
3. `pytest` - test execution

The workflow currently only performs governance-specific checks (branch naming, co-authorship, protected files) but doesn't run the full validation suite.

## Scope
### In scope
- Add `make install-uv` step to install dependencies
- Add `python tools/validate_swarm_ready.py` step to run gate validation
- Add `pytest` step to run tests
- Ensure steps match the pattern in `ci.yml` where applicable
- Verify Gate Q passes after changes

### Out of scope
- Changes to existing governance checks (branch approval, co-authorship, etc.)
- Modifications to other workflow files
- Changes to gate validation logic

## Required spec references
- specs/34_strict_compliance_guarantees.md (Guarantee H: CI parity)
- .github/workflows/ci.yml (canonical command reference)
- tools/validate_swarm_ready.py (Gate Q implementation)

## Inputs
- `.github/workflows/ai-governance-check.yml` (missing canonical commands)
- `.github/workflows/ci.yml` (reference implementation with canonical commands)
- Gate Q validation output showing missing commands

## Outputs
- Updated `.github/workflows/ai-governance-check.yml` with canonical commands
- reports/agents/**/TC-923/report.md
- reports/agents/**/TC-923/validate_swarm_ready_output.txt showing Gate Q PASS

## Allowed paths
- plans/taskcards/TC-923_fix_gate_q_ai_governance_workflow.md
- plans/taskcards/INDEX.md
- plans/taskcards/STATUS_BOARD.md
- .github/workflows/ai-governance-check.yml
- reports/agents/**/TC-923/**

## Implementation steps
1. Review `ci.yml` to understand canonical command implementation
2. Add Python setup (if not present)
3. Add uv installation step
4. Add `make install-uv` step to install dependencies
5. Add `python tools/validate_swarm_ready.py` step (using .venv/bin/python)
6. Add `pytest` step (using .venv/bin/python -m pytest)
7. Verify Gate Q passes with validate_swarm_ready.py

## Failure modes

### 1. Commands run in wrong order (dependencies not installed first)
**Detection**: Workflow fails because validate_swarm_ready.py or pytest can't find dependencies
**Resolution**: Ensure install step runs before validation/test steps
**Spec/Gate**: Gate Q - canonical command order

### 2. Wrong Python interpreter (not using .venv)
**Detection**: Gate Q still fails due to venv policy violations
**Resolution**: Use `.venv/bin/python` (Linux) or `.venv/Scripts/python.exe` (Windows) explicitly
**Spec/Gate**: Gate 0 - .venv policy enforcement

### 3. Workflow syntax errors
**Detection**: GitHub Actions workflow validation fails
**Resolution**: Validate YAML syntax, check for proper indentation
**Spec/Gate**: GitHub Actions workflow schema

### 4. Workflow runs but canonical commands not detected by Gate Q
**Detection**: Gate Q still reports missing commands after update
**Resolution**: Ensure exact command strings match Gate Q expectations (e.g., "make install-uv", not "make install")
**Spec/Gate**: Gate Q validation logic

## Task-specific review checklist
- [ ] Added Python setup step with correct version file (.python-version or pyproject.toml)
- [ ] Added uv installation step (using astral-sh/setup-uv@v7)
- [ ] Added `make install-uv` step
- [ ] Added `python tools/validate_swarm_ready.py` step using .venv Python
- [ ] Added `pytest` step using .venv Python
- [ ] Steps run in correct order (setup → install → validate → test)
- [ ] Workflow syntax is valid (proper YAML indentation)
- [ ] Gate Q passes in validate_swarm_ready.py

## Deliverables
- Modified `.github/workflows/ai-governance-check.yml` with canonical commands
- reports/agents/<agent>/TC-923/report.md
- reports/agents/<agent>/TC-923/self_review.md
- reports/agents/<agent>/TC-923/validate_swarm_ready_output.txt

## Acceptance checks
- [ ] Gate Q passes in validate_swarm_ready.py (all canonical commands present)
- [ ] Workflow YAML is valid (no syntax errors)
- [ ] All three canonical commands present: make install-uv, validate_swarm_ready.py, pytest
- [ ] pytest passes (no test regressions)

## E2E verification
**Concrete command(s) to run:**
```bash
python tools/validate_swarm_ready.py | grep -A 20 "Gate Q:"
```

**Expected artifacts:**
- Updated `.github/workflows/ai-governance-check.yml` with canonical commands
- Gate Q validation passes with all commands detected

**Success criteria:**
- [ ] validate_swarm_ready.py Gate Q shows PASS
- [ ] All canonical commands detected in ai-governance-check.yml
- [ ] No regressions in other gates

## Integration boundary proven
**Upstream dependencies:**
- None (CI configuration update)

**Downstream impact:**
- Gate Q validation passes
- CI workflows now have consistent command coverage
- AI governance workflow runs full validation suite

**Verification:**
- Ran validate_swarm_ready.py: Gate Q passes
- Confirmed ai-governance-check.yml contains all canonical commands
- No regression in other gates

## Self-review
**Implementation completed:** [To be filled]

Changes made:
1. [To be filled after implementation]

Verification:
- [ ] Added Python setup step with correct version file
- [ ] Added uv installation step
- [ ] Added `make install-uv` step
- [ ] Added `python tools/validate_swarm_ready.py` step using .venv Python
- [ ] Added `pytest` step using .venv Python
- [ ] Steps run in correct order
- [ ] Workflow syntax is valid
- [ ] Gate Q passes in validate_swarm_ready.py
