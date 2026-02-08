---
id: TC-1050-T2
title: "Add Dedicated Unit Tests for Workflow Enrichment"
status: In-Progress
priority: High
owner: "Agent-C"
updated: "2026-02-08"
tags: ["testing", "w2", "agent-c", "tc-1050"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-1050-T2_workflow_enrichment_tests.md
  - plans/taskcards/INDEX.md
  - tests/unit/workers/test_w2_workflow_enrichment.py
  - reports/agents/agent_c/TC-1050-T2/**
evidence_required:
  - reports/agents/agent_c/TC-1050-T2/evidence.md
  - reports/agents/agent_c/TC-1050-T2/self_review.md
spec_ref: "7840566"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1050-T2 — Add Dedicated Unit Tests for Workflow Enrichment

## Objective
Create comprehensive unit test file `test_w2_workflow_enrichment.py` with 15-20 tests for `enrich_workflow()` and `enrich_example()` functions, achieving 100% test coverage for workflow and example enrichment modules.

## Problem Statement
Currently `enrich_workflows.py` and `enrich_examples.py` are tested indirectly via integration tests only. This creates coverage gaps and makes debugging enrichment failures difficult. Need dedicated unit tests for full coverage and faster iteration.

## Required spec references
- specs/03_product_facts_and_evidence.md (Workflow enrichment section)
- specs/05_example_curation.md (Example enrichment section)
- plans/taskcards/00_TASKCARD_CONTRACT.md (Taskcard format requirements)

## Scope

### In scope
- Create new test file: tests/unit/workers/test_w2_workflow_enrichment.py
- Test `enrich_workflow()` with step ordering, complexity determination, and time estimation
- Test `enrich_example()` with description extraction, complexity analysis, and audience level inference
- Achieve 100% coverage for enrich_workflows.py and enrich_examples.py
- 15-20 total test cases covering all code paths and edge cases

### Out of scope
- Modifying existing enrichment implementation (TC-1043/TC-1044 work)
- Integration tests with full W2 pipeline
- Tests for other W2 modules (code_analyzer, enrich_claims, etc.)
- Performance testing or benchmarking

## Inputs
- Existing enrich_workflows.py and enrich_examples.py implementations
- Current test patterns from test_w2_code_analyzer.py and other W2 tests
- Acceptance criteria requirements for 100% coverage

## Outputs
- tests/unit/workers/test_w2_workflow_enrichment.py with 15-20 test cases
- Test execution results showing all tests passing
- Coverage report showing 100% coverage for target modules
- Evidence bundle with test results and coverage analysis

## Allowed paths
- plans/taskcards/TC-1050-T2_workflow_enrichment_tests.md
- plans/taskcards/INDEX.md
- tests/unit/workers/test_w2_workflow_enrichment.py
- reports/agents/agent_c/TC-1050-T2/**

### Allowed paths rationale
TC-1050-T2 creates comprehensive unit tests for workflow and example enrichment modules to achieve 100% test coverage. The test file is the primary deliverable, with taskcard and evidence documentation.

## Implementation steps

### Step 1: Create test file structure
Create `tests/unit/workers/test_w2_workflow_enrichment.py` with two test classes:
- `TestWorkflowEnrichment` for enrich_workflow tests
- `TestExampleEnrichment` for enrich_example tests

### Step 2: Implement workflow enrichment tests (8-10 tests)
Test cases:
- Step ordering (install → setup → config → basic → advanced)
- Complexity determination (simple: 1-2 steps, moderate: 3-5, complex: 6+)
- Time estimation (scales with step count and workflow type)
- Workflow ID generation
- Empty claims handling
- Missing snippet handling
- Multi-phase workflow ordering

### Step 3: Implement example enrichment tests (7-10 tests)
Test cases:
- Description extraction from triple-quoted docstrings
- Description extraction from single-line comments
- Fallback description for missing docstrings
- Complexity analysis (trivial, simple, moderate, complex LOC thresholds)
- Audience level inference (beginner, intermediate, advanced)
- Field preservation (example_id, title, tags)
- Missing file handling

### Step 4: Run tests and verify coverage
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_w2_workflow_enrichment.py -xvs
```

Expected: 15-20 tests pass, 0 failures

### Step 5: Run full test suite
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
```

Expected: 2531+ tests pass (new baseline includes new tests)

### Step 6: Generate coverage report (if available)
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_w2_workflow_enrichment.py --cov=src/launch/workers/w2_facts_builder/enrich_workflows --cov=src/launch/workers/w2_facts_builder/enrich_examples --cov-report=term-missing
```

Expected: 100% coverage for both modules

### Step 7: Capture evidence
- Test file contents
- Test execution output showing all tests pass
- Coverage analysis (if available)
- Full test suite results

## Failure modes

### Failure mode 1: Tests fail due to incorrect expectations
**Detection:** pytest shows assertion failures with mismatch between expected and actual values
**Resolution:** Review enrich_workflows.py and enrich_examples.py implementation; adjust test expectations to match actual behavior; verify spec references for correct requirements
**Spec/Gate:** specs/03_product_facts_and_evidence.md workflow enrichment logic

### Failure mode 2: Coverage below 100% for target modules
**Detection:** Coverage report shows uncovered lines in enrich_workflows.py or enrich_examples.py
**Resolution:** Identify uncovered code paths; add test cases for missing scenarios; verify all branches and edge cases covered
**Spec/Gate:** Acceptance criteria requiring 100% coverage

### Failure mode 3: New tests break existing test suite
**Detection:** Full test suite run shows failures in previously passing tests
**Resolution:** Check for conflicting fixtures, imports, or test isolation issues; ensure no side effects from new tests; verify PYTHONHASHSEED=0 for determinism
**Spec/Gate:** Determinism requirement from specs/30_ai_agent_governance.md

### Failure mode 4: Taskcard validation fails
**Detection:** validate_taskcards.py shows missing required sections or frontmatter mismatches
**Resolution:** Add missing sections per 00_TASKCARD_CONTRACT.md; ensure frontmatter allowed_paths matches body section; verify all 14 mandatory sections present
**Spec/Gate:** Gate B taskcard validation

### Failure mode 5: Tmp_path fixture issues on Windows
**Detection:** Tests using tmp_path fixture fail with WinError or path resolution errors
**Resolution:** Use forward slashes in path construction; verify tmp_path / "file.py" syntax; ensure file write operations complete before reads
**Spec/Gate:** Windows compatibility requirements

## Task-specific review checklist
1. [ ] Test file contains 15-20 test cases (verified by pytest --collect-only)
2. [ ] All workflow enrichment functions tested (enrich_workflow, _determine_complexity, _estimate_time, _order_workflow_steps)
3. [ ] All example enrichment functions tested (enrich_example, _extract_description_from_code, _analyze_code_complexity, _infer_audience_level)
4. [ ] Step ordering tests cover all phases: install, setup, config, basic, advanced
5. [ ] Complexity thresholds tested for all levels: trivial, simple, moderate, complex
6. [ ] Edge cases covered: empty claims, missing files, missing docstrings
7. [ ] Test execution time reasonable (<30 seconds for 20 tests)
8. [ ] No test dependencies on external files (use tmp_path fixtures)
9. [ ] All tests pass consistently (run 3 times for determinism)
10. [ ] Coverage report shows 100% for enrich_workflows.py and enrich_examples.py

## Deliverables
- tests/unit/workers/test_w2_workflow_enrichment.py with 15-20 test cases
- Test execution output showing all tests pass
- Coverage report (if tooling available)
- Evidence bundle at reports/agents/agent_c/TC-1050-T2/evidence.md
- 12D self-review at reports/agents/agent_c/TC-1050-T2/self_review.md
- Updated plans/taskcards/INDEX.md with TC-1050-T2 registration

## Acceptance checks
1. [ ] test_w2_workflow_enrichment.py created with 15-20 test cases
2. [ ] All workflow enrichment functions covered (enrich_workflow, _determine_complexity, _estimate_time, _order_workflow_steps)
3. [ ] All example enrichment functions covered (enrich_example, _extract_description_from_code, _analyze_code_complexity, _infer_audience_level)
4. [ ] pytest execution shows 15-20 new tests pass, 0 failures
5. [ ] Full test suite passes (2531+ total tests)
6. [ ] Coverage report shows 100% for enrich_workflows.py and enrich_examples.py (if tooling available)
7. [ ] Evidence bundle captured with test results and coverage analysis
8. [ ] 12D self-review completed with all dimensions >= 4/5

## Preconditions / dependencies
- Python virtual environment activated (.venv)
- pytest installed and working
- enrich_workflows.py and enrich_examples.py implementations complete (TC-1043, TC-1044)
- PYTHONHASHSEED=0 for deterministic test execution

## Test plan
1. Test case category 1: Workflow step ordering
   - Verify install steps come first
   - Verify advanced steps come last
   - Verify full sequence: install → setup → config → basic → advanced
   Expected: Steps reordered according to phase keywords

2. Test case category 2: Workflow complexity determination
   - Test simple (1-2 steps), moderate (3-5 steps), complex (6+ steps)
   Expected: Correct complexity label for each threshold

3. Test case category 3: Workflow time estimation
   - Test that time scales with step count
   - Test base time varies by workflow type (install vs config vs other)
   Expected: Time estimates increase proportionally

4. Test case category 4: Example description extraction
   - Test triple-quoted docstrings (""" and ''')
   - Test single-line comments (#)
   - Test fallback for missing descriptions
   Expected: Description extracted from first available source

5. Test case category 5: Example complexity and audience inference
   - Test LOC thresholds: <10, <50, <200, 200+
   - Test audience keywords: beginner, intermediate, advanced
   Expected: Correct complexity and audience level assigned

6. Test case category 6: Edge cases
   - Empty claims, missing files, malformed content
   Expected: Graceful handling with fallback values

## Self-review

### 12D Checklist

1. **Determinism:** All tests use deterministic fixtures and sorted outputs; no randomness or timestamps; tmp_path provides isolated file system per test

2. **Dependencies:** No new dependencies added; uses existing pytest, pathlib, and unittest.mock from test infrastructure

3. **Documentation:** Test docstrings explain each test case purpose and expected behavior; inline comments for complex assertions

4. **Data preservation:** Tests use tmp_path fixtures to avoid modifying repo files; no side effects on production code or data

5. **Deliberate design:** Two test classes (TestWorkflowEnrichment, TestExampleEnrichment) mirror module structure; test names follow test_<function>_<scenario> convention

6. **Detection:** pytest assertions provide clear failure messages; test names indicate which function and scenario failed

7. **Diagnostics:** Test output includes full diffs for failed assertions; pytest -xvs provides detailed execution trace

8. **Defensive coding:** Tests handle missing files, empty inputs, and malformed data; tmp_path ensures test isolation

9. **Direct testing:** Each test targets specific function with minimal setup; no complex fixtures or mocking required

10. **Deployment safety:** Tests are read-only; no changes to production code; can run in parallel with other tests

11. **Delta tracking:** New test file clearly separate from existing tests; evidence captures test count delta (2531 → 2531+20)

12. **Downstream impact:** Enables faster debugging of enrichment issues; provides regression safety for future enrichment changes; increases confidence in W2 intelligence modules

### Verification results
- [ ] Tests: 15-20/15-20 PASS (pytest output captured)
- [ ] Coverage: 100% for enrich_workflows.py and enrich_examples.py
- [ ] Evidence captured: reports/agents/agent_c/TC-1050-T2/evidence.md

## E2E verification
```bash
# Run new test file
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_w2_workflow_enrichment.py -xvs

# Count new tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_w2_workflow_enrichment.py --collect-only

# Run full test suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x

# Coverage report (if pytest-cov installed)
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_w2_workflow_enrichment.py --cov=src/launch/workers/w2_facts_builder/enrich_workflows --cov=src/launch/workers/w2_facts_builder/enrich_examples --cov-report=term-missing
```

**Expected artifacts:**
- **tests/unit/workers/test_w2_workflow_enrichment.py** - Contains 15-20 test cases
- **pytest output** - Shows all new tests pass
- **coverage report** - Shows 100% coverage (if pytest-cov available)
- **reports/agents/agent_c/TC-1050-T2/evidence.md** - Evidence bundle

**Expected results:**
- 15-20 new tests added to test suite
- All tests pass consistently (3 consecutive runs)
- Full test suite shows 2531+ tests pass
- Coverage report shows 100% for enrich_workflows.py and enrich_examples.py

## Integration boundary proven
**Upstream:** pytest test runner discovers and executes test_w2_workflow_enrichment.py; tmp_path fixture provides isolated file system; test imports enrich_workflow and enrich_example functions from w2_facts_builder modules

**Downstream:** Test results consumed by pytest for pass/fail reporting; coverage data consumed by pytest-cov plugin (if available); evidence captured for agent self-review

**Contract:**
- Test file must be in tests/unit/workers/ directory for pytest discovery
- Test functions must start with `test_` prefix
- Tests must pass with PYTHONHASHSEED=0 for determinism
- Tests must not modify repo files (use tmp_path fixtures only)
- Coverage measurement requires pytest-cov plugin (optional)

## Evidence Location
`reports/agents/agent_c/TC-1050-T2/`
- evidence.md (test results, coverage report, implementation details)
- self_review.md (12D checklist scores and verification)
