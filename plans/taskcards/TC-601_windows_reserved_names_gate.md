---
id: TC-601
title: "Windows Reserved Names Validation Gate"
status: Done
owner: "hygiene-agent"
updated: "2026-01-24"
depends_on:
  - TC-571
allowed_paths:
  - tools/validate_windows_reserved_names.py
  - tools/validate_swarm_ready.py
  - .github/workflows/ci.yml
  - tests/unit/test_validate_windows_reserved_names.py
  - reports/agents/hygiene-agent/**
evidence_required:
  - reports/agents/hygiene-agent/H1_WINDOWS_RESERVED_NAMES/report.md
  - reports/agents/hygiene-agent/H1_WINDOWS_RESERVED_NAMES/self_review.md
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-601 — Windows Reserved Names Validation Gate

## Objective
Implement a validation gate to prevent Windows reserved device filenames (NUL, CON, PRN, AUX, COM1-9, LPT1-9, CLOCK$) from entering the repository, preventing file system incompatibilities on Windows platforms.

## Required spec references
- specs/34_strict_compliance_guarantees.md (cross-platform compatibility)
- specs/09_validation_gates.md (validation gate patterns)
- plans/taskcards/00_TASKCARD_CONTRACT.md (write fence)

## Scope
### In scope
- Detect Windows reserved device names in repository tree
- Case-insensitive detection (NUL, nul, Nul all detected)
- Exclude standard directories (.git, .venv, node_modules)
- Integration into swarm readiness gate
- Integration into CI pipeline
- Self-test mode for validation
- Comprehensive test coverage

### Out of scope
- Detection in git history (only current tree)
- Auto-fixing of violations (gate only detects)
- Other Windows path issues (long paths, special characters)

## Non-negotiables (binding for this task)
- **No improvisation:** if anything is unclear, write a blocker issue and stop that path.
- **Write fence:** you MAY ONLY change files under **Allowed paths** below.
- **Determinism:** stable file ordering (use sorted()), no timestamps in validation output.
- **Evidence:** all validation outputs recorded in report.

## Preconditions / dependencies
- TC-571 must exist (policy gates foundation)
- Python 3.12+ environment
- .venv with pytest installed

## Inputs
- Repository file tree (excluding .git, .venv, node_modules)
- Command-line flag: --self-test (optional)

## Outputs
- Exit code 0 if clean, 1 if violations found
- Deterministic error messages listing violations
- Integration into validate_swarm_ready.py as Gate S
- Unit test suite

## Allowed paths
- tools/validate_windows_reserved_names.py
- tools/validate_swarm_ready.py
- .github/workflows/ci.yml
- tests/unit/test_validate_windows_reserved_names.py
- reports/agents/hygiene-agent/**

### Allowed paths rationale
This task implements a new validation gate to prevent Windows reserved filenames. It requires creating the gate tool, integrating it into the swarm readiness orchestrator and CI pipeline, adding comprehensive tests, and producing evidence reports.

## Implementation steps
1) Create tools/validate_windows_reserved_names.py:
   - Define Windows reserved names list
   - Implement repo tree scanner with exclusions
   - Add case-insensitive detection
   - Implement --self-test mode
   - Stable sorting for determinism
2) Update tools/validate_swarm_ready.py:
   - Add Gate S (next available letter after R)
   - Follow existing gate pattern
3) Update .github/workflows/ci.yml:
   - Add gate to validation steps with .venv
4) Create tests/unit/test_validate_windows_reserved_names.py:
   - Test clean repo passes
   - Test reserved names detected
   - Test case-insensitive detection
   - Test self-test mode
5) Create evidence reports

## Test plan
- Unit tests to add:
  - test_clean_repo_passes: Verify current repo state passes
  - test_self_test_passes: Verify --self-test mode works
  - test_reserved_name_detection: Mock filesystem with violations
  - test_case_insensitive: Test NUL, nul, Nul all detected
- Integration tests:
  - Verify gate runs in validate_swarm_ready.py
  - Verify CI integration works
- Determinism proof:
  - Violations reported in stable sorted order
  - Identical output across multiple runs

## E2E verification
**Concrete command(s) to run:**
```bash
# Activate .venv first
. .venv/Scripts/activate

# Test the new gate standalone
python tools/validate_windows_reserved_names.py

# Test self-test mode
python tools/validate_windows_reserved_names.py --self-test

# Run full swarm readiness
python tools/validate_swarm_ready.py

# Run unit tests
pytest tests/unit/test_validate_windows_reserved_names.py -v
```

**Expected artifacts:**
- tools/validate_windows_reserved_names.py (validates repo tree)
- tests/unit/test_validate_windows_reserved_names.py (all tests pass)
- Updated tools/validate_swarm_ready.py (Gate S integrated)
- Updated .github/workflows/ci.yml (gate in CI)

**Success criteria:**
- [ ] Gate detects Windows reserved names
- [ ] Case-insensitive detection works
- [ ] Self-test mode passes
- [ ] Integration into validate_swarm_ready.py works
- [ ] CI integration works
- [ ] All unit tests pass
- [ ] Deterministic output (sorted violations)

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-571 (policy gates pattern)
- Downstream: validate_swarm_ready.py (gate orchestrator)
- Downstream: CI pipeline (.github/workflows/ci.yml)
- Contracts: Gate exit codes (0=pass, 1=fail), deterministic output

## Failure modes

### Failure mode 1: Reserved name detection misses case variant
**Detection:** Manual testing with filenames like `CON.txt`, `nul`, `NUL.md` shows some variants pass incorrectly
**Resolution:** Verify case-insensitive regex includes all reserved names (NUL, CON, PRN, AUX, COM1-9, LPT1-9, CLOCK$); test with lowercase, uppercase, and mixed case variants; ensure normalized comparison before matching
**Spec/Gate:** specs/34_strict_compliance_guarantees.md (cross-platform compatibility), Gate S

### Failure mode 2: Excluded directories not properly skipped
**Detection:** Gate reports violations in .venv, node_modules, or .git directories
**Resolution:** Check exclusion list in tree scanner; ensure Path.relative_to() logic correctly identifies excluded directories; verify exclusions apply to all depth levels
**Spec/Gate:** specs/09_validation_gates.md (gate patterns), tools/validate_windows_reserved_names.py

### Failure mode 3: Gate integration fails in CI pipeline
**Detection:** CI workflow fails at validation step with "Gate S not found" or timeout
**Resolution:** Verify gate is registered in validate_swarm_ready.py gates list; check .github/workflows/ci.yml includes gate in validation steps with correct .venv activation; ensure exit code propagates correctly
**Spec/Gate:** specs/09_validation_gates.md (gate orchestration), .github/workflows/ci.yml

## Task-specific review checklist
Beyond the standard acceptance checks, verify:
- [ ] All outputs are written atomically per specs/10_determinism_and_caching.md
- [ ] No manual content edits made (compliance with no_manual_content_edits policy)
- [ ] Determinism verified by running task twice and comparing artifacts byte-for-byte
- [ ] All spec references listed in taskcard were consulted during implementation
- [ ] Evidence files (report.md, self_review.md) include all required sections and command outputs
- [ ] No placeholder values (PIN_ME, TODO, FIXME, etc.) remain in production code paths

## Deliverables
- Code:
  - tools/validate_windows_reserved_names.py
  - Updated tools/validate_swarm_ready.py
  - Updated .github/workflows/ci.yml
- Tests:
  - tests/unit/test_validate_windows_reserved_names.py
- Reports (required):
  - reports/agents/hygiene-agent/TC-571-1/report.md
  - reports/agents/hygiene-agent/TC-571-1/self_review.md

## Acceptance checks
- [ ] Gate detects all Windows reserved names
- [ ] Case-insensitive detection verified
- [ ] Exclusions work (.git, .venv, node_modules)
- [ ] Self-test mode works
- [ ] Integration into validate_swarm_ready.py complete
- [ ] CI integration complete
- [ ] All tests passing
- [ ] Deterministic output verified
- [ ] Reports written with command outputs

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
