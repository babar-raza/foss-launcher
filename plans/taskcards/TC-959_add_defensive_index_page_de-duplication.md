---
id: TC-959
title: "Add Defensive Index Page De-duplication"
status: Draft
priority: Normal
owner: "Agent B"
updated: "2026-02-03"
tags: ["healing", "bug-fix", "w4-ia-planner", "template-collision"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-959_add_defensive_index_page_de-duplication.md
  - src/launch/workers/w4_ia_planner/worker.py
  - tests/unit/workers/test_w4_template_collision.py
evidence_required:
  - runs/[run_id]/evidence.zip
  - reports/agents/<agent>/TC-959/report.md
spec_ref: "fe582540d14bb6648235fe9937d2197e4ed5cbac"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-959 — Add Defensive Index Page De-duplication

## Objective
Add defensive de-duplication logic to `classify_templates()` function (lines 941-995) to prevent URL collisions from multiple `_index.md` template variants for the same section. This Phase 2 defensive measure ensures deterministic template selection (alphabetical by template_path) as future-proofing, since Phase 0 (TC-957) already eliminated root cause by filtering obsolete templates.

## Problem Statement
Multiple `_index.md` template variants for the same section could cause URL collisions, with both templates mapping to the same /{family}/{platform}/ URL. While Phase 0 (HEAL-BUG4/TC-957) filtered obsolete blog templates with __LOCALE__ structure to eliminate root cause, defensive de-duplication in `classify_templates()` adds future-proofing to ensure only one index page per section is selected deterministically.

## Required spec references
- specs/33_public_url_mapping.md - URL path requirements and collision avoidance
- specs/10_determinism_and_caching.md - Deterministic template selection requirements
- specs/07_section_templates.md - Template structure and variant handling

## Scope

### In scope
[Bulleted list of what WILL be done in this taskcard]

Example:
- Add SCAN_EXTENSIONS whitelist to validate_secrets_hygiene.py
- Update should_scan_file() to check extensions before glob matching
- Reduce file count from 1427 to ~340 files
- Ensure Gate L completes within 60-second timeout

### Out of scope
[Bulleted list of what will NOT be done, to avoid scope creep]

Example:
- Changing secrets detection patterns or entropy calculations
- Modifying other validation gates
- Scanning binary files or archives

## Inputs
[What does this taskcard consume/require?]

Example:
- Existing validate_secrets_hygiene.py with 60+ second execution time
- Gate L timeout threshold: 60 seconds
- Secrets patterns from existing implementation
- Repository structure with runs/ directory containing artifacts

## Outputs
[What artifacts/files/data does this taskcard produce?]

Example:
- Modified validate_secrets_hygiene.py with SCAN_EXTENSIONS whitelist
- Updated should_scan_file() function
- Gate L execution time reduced to ~47.7 seconds
- validate_swarm_ready output showing Gate L PASS

## Allowed paths
- plans/taskcards/TC-959_add_defensive_index_page_de-duplication.md
- src/launch/workers/w4_ia_planner/worker.py
- tests/unit/workers/test_w4_template_collision.py

### Allowed paths rationale
TC-959 modifies worker.py's `classify_templates()` function to add defensive de-duplication logic that prevents URL collisions from multiple _index.md template variants for the same section. The new test file provides comprehensive unit test coverage (8 tests) to verify de-duplication behavior.

## Implementation steps

### Step 1: [First step name]
[Detailed instructions with commands, code snippets, expected outputs]

Example format:
```bash
# Get current git SHA for spec_ref
git rev-parse HEAD
```

Expected output: `abc123def456...` (40-character SHA)

### Step 2: [Second step name]
[Continue with numbered steps - be specific and actionable]

Example:
Add SCAN_EXTENSIONS whitelist after EXCLUDE_PATTERNS:
```python
SCAN_EXTENSIONS = {
    ".txt",
    ".log",
    ".md",
    # ... other extensions
}
```

### Step 3: [Third step name]
[Include verification steps]

Example:
Run validation:
```powershell
.venv\Scripts\python.exe tools\validate_swarm_ready.py
```

Expected: Gate L completes in <60 seconds

## Failure modes

### Failure mode 1: [Name of failure scenario]
**Detection:** [How to detect this failure - command, log message, error code]
**Resolution:** [Step-by-step fix procedure]
**Spec/Gate:** [Which spec or gate this relates to]

Example:
### Failure mode 1: Gate L still times out
**Detection:** validate_swarm_ready shows Gate L execution time >60 seconds
**Resolution:** Further reduce file count or increase timeout threshold; review SCAN_EXTENSIONS for unnecessary types
**Spec/Gate:** specs/09_validation_gates.md Gate L timeout configuration

### Failure mode 2: [Name of failure scenario]
[Minimum 3 failure modes required]

Example:
### Failure mode 2: Validator rejects taskcard due to missing sections
**Detection:** validate_taskcards.py shows "Missing required section: X"
**Resolution:** Add missing section per 00_TASKCARD_CONTRACT.md; ensure frontmatter and body match
**Spec/Gate:** Gate B taskcard validation

### Failure mode 3: [Name of failure scenario]
[Include failure modes for: validation failures, missing dependencies, edge cases]

Example:
### Failure mode 3: Tests fail after implementation
**Detection:** pytest exit code non-zero; specific test failure messages
**Resolution:** Review test output; fix implementation logic; ensure determinism in test assertions
**Spec/Gate:** Acceptance criteria testing requirements

## Task-specific review checklist
[Minimum 6 task-specific items beyond standard acceptance checks]

Example:
1. [ ] SCAN_EXTENSIONS whitelist includes all text-based file types
2. [ ] File count reduced from baseline (measure before/after)
3. [ ] Execution time consistently <60 seconds (run 3 times)
4. [ ] No reduction in coverage of source files
5. [ ] Frontmatter and body allowed_paths match exactly
6. [ ] spec_ref SHA is correct (from git rev-parse HEAD)
7. [ ] All 14 mandatory sections present
8. [ ] Implementation steps match actual changes made

## Deliverables
[List of concrete outputs required for task completion]

Example:
- Modified file X at path Y with changes Z
- Test file at tests/unit/test_tc_xxx.py
- Validation report showing Gate X PASS
- Evidence bundle at runs/[run_id]/evidence.zip
- Agent report at reports/agents/<agent>/TC-959/report.md
- Self-review at reports/agents/<agent>/TC-959/self_review.md

## Acceptance checks
[Measurable criteria that must ALL be true for task to be considered done]

Example:
1. [ ] Gate L completes within 60 seconds consistently (3 consecutive runs)
2. [ ] File count reduced from 1427 to ~340
3. [ ] validate_swarm_ready shows Gate L PASS
4. [ ] No reduction in coverage of src/, specs/, tests/ files
5. [ ] All tests pass (pytest exit code 0)
6. [ ] Evidence bundle created with all artifacts

## Preconditions / dependencies
[Optional: What must be true before starting this taskcard]

Example:
- Python virtual environment activated (.venv)
- All dependencies installed (make install)
- validate_swarm_ready.py working correctly
- TC-YYY must be complete (if dependent on another taskcard)

## Test plan
[Optional: How to test this implementation]

Example:
1. Test case 1: Run validate_swarm_ready on repo with large runs/ directory
   Expected: Gate L completes in <60s and passes
2. Test case 2: Add test secret to .txt file in runs/
   Expected: Gate L detects secret and fails validation
3. Test case 3: Verify file count reduced from baseline
   Expected: Log shows ~340 files scanned (down from 1427)

## Self-review

### 12D Checklist
[Review across 12 dimensions - see reports/templates/self_review_12d.md]

1. **Determinism:** [How is determinism ensured?]
   Example: "File scanning order remains deterministic (sorted glob patterns); no timestamps or random IDs"

2. **Dependencies:** [What dependencies were added/changed?]
   Example: "No new dependencies; only logic changes in existing validate_secrets_hygiene.py"

3. **Documentation:** [What docs were updated?]
   Example: "Added TC-936 comments explaining whitelist approach and performance rationale"

4. **Data preservation:** [How is data integrity maintained?]
   Example: "All text-based files remain scanned; no data loss or corruption risk"

5. **Deliberate design:** [What design decisions were made and why?]
   Example: "Whitelist approach (SCAN_EXTENSIONS) chosen over blacklist for performance and clarity"

6. **Detection:** [How are errors/issues detected?]
   Example: "Gate L still detects secrets in scanned files; execution time logged"

7. **Diagnostics:** [What logging/observability added?]
   Example: "File count and timing logged in validate_swarm_ready output"

8. **Defensive coding:** [What validation/error handling added?]
   Example: "Extension check with fallback for extensionless files; exception handling maintained"

9. **Direct testing:** [What tests verify this works?]
   Example: "Manual verification with validate_swarm_ready showing <60s execution; 3 consecutive runs"

10. **Deployment safety:** [How is safe rollout ensured?]
    Example: "Change only affects performance, not detection logic; can revert by removing SCAN_EXTENSIONS"

11. **Delta tracking:** [What changed and how is it tracked?]
    Example: "Modified 3 sections: SCAN_EXTENSIONS definition, should_scan_file(), main()"

12. **Downstream impact:** [What systems/users are affected?]
    Example: "Enables reliable autonomous validation; unblocks CI/CD pipeline; no user-facing changes"

### Verification results
- [ ] Tests: X/X PASS (e.g., 5/5 PASS)
- [ ] Validation: Gate Y PASS (e.g., Gate L PASS)
- [ ] Evidence captured: [location] (e.g., runs/tc936_20260203/evidence.zip)

Example:
- ✓ Gate L execution time: 47.7 seconds (down from 59.7 seconds)
- ✓ File count: 340 files scanned (down from 1427)
- ✓ validate_swarm_ready: 21/21 gates PASS

## E2E verification
[Concrete command(s) to verify end-to-end functionality]

Example:
```bash
# Run complete validation workflow
.venv\Scripts\python.exe tools\validate_swarm_ready.py

# Run test suite
.venv\Scripts\python.exe -m pytest -q

# Measure Gate L timing (3 consecutive runs)
for i in 1 2 3; do
  echo "Run $i:"
  .venv\Scripts\python.exe tools\validate_swarm_ready.py | grep "Gate L"
done
```

**Expected artifacts:**
- **runs\[run_id]\validate_swarm_ready.txt** - Shows Gate L PASS with execution time <60s
- **runs\[run_id]\pytest_output.txt** - Shows all tests passing (exit code 0)
- **Modified tools\validate_secrets_hygiene.py** - Contains SCAN_EXTENSIONS whitelist

**Expected results:**
- Gate L completes in ~47.7 seconds (down from 59.7+ seconds)
- File count reduced from 1427 to ~340 files
- validate_swarm_ready shows 21/21 gates PASS (or expected count)
- All tests pass (pytest exit code 0)

## Integration boundary proven
**Upstream:** [What component/system provides input to this work?]

Example: "validate_swarm_ready.py Gate L calls validate_secrets_hygiene.main() with a 60-second timeout. It passes the repository root path as input."

**Downstream:** [What component/system consumes output from this work?]

Example: "validate_secrets_hygiene.py scans files and returns exit code 0 if no secrets found, non-zero if secrets detected. Output is consumed by Gate L for pass/fail decision."

**Contract:** [What interface/API/data format is guaranteed between them?]

Example:
- validate_secrets_hygiene must complete within 60 seconds
- Exit code 0 = no secrets found (PASS)
- Exit code non-zero = secrets detected (FAIL)
- Uses SCAN_EXTENSIONS whitelist to filter file types
- Maintains full coverage of text-based files

## Evidence Location
`runs/[run_id]/[evidence_files]`

Example: `runs/tc936_20260203_090328/evidence.zip`
