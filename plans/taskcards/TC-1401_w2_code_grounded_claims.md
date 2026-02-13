---
id: TC-1401
title: "W2 Code-Grounded Claim Generation"
status: Done
priority: Normal
owner: "agent_b"
updated: "2026-02-12"
tags: ["w2", "claims", "code-analysis", "llm", "facts-builder"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-1401_w2_code_grounded_claims.md
  - src/launch/workers/w2_facts_builder/extract_claims.py
  - src/launch/workers/w2_facts_builder/worker.py
  - tests/unit/workers/test_tc_411_extract_claims.py
  - reports/agents/agent_b/TC-1401/plan.md
  - reports/agents/agent_b/TC-1401/changes.md
  - reports/agents/agent_b/TC-1401/evidence.md
  - reports/agents/agent_b/TC-1401/self_review.md
evidence_required:
  - "reports/agents/agent_b/TC-1401/evidence.md"
  - "reports/agents/agent_b/TC-1401/self_review.md"
spec_ref: "0cd4ce327b97b36f870adf2909707cf560b7e50c"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1401 — W2 Code-Grounded Claim Generation

## Objective
Integrate code-grounded claim generation into W2 FactsBuilder to generate 10-30 user-facing claims from the REAL API surface (classes, functions, modules) extracted via AST parsing, providing ground truth for downstream content generation.

## Problem Statement
The existing `extract_claims_from_code_analysis()` function (lines 917-1056) is fully implemented with both LLM and offline fallback paths, but it is NOT integrated into the claims extraction pipeline. This means code analysis results (classes, methods, modules) are not being converted to claims that can drive W4 planning and W5 content generation.

Without code-grounded claims, the pipeline relies solely on documentation-based claims extraction, missing critical API surface information that could produce richer, more accurate technical documentation.

## Required spec references
- specs/03_product_facts_and_evidence.md (Claims extraction algorithm, code analysis integration)
- specs/21_worker_contracts.md:98-125 (W2 FactsBuilder contract)
- specs/07_code_analysis_intelligence.md (Code analysis and API surface extraction)
- plans/virtual-scribbling-sifakis.md:41-68 (TC-1401 implementation specification)

## Scope

### In scope
- Load code_analysis artifact in `extract_claims()` function
- Call `extract_claims_from_code_analysis()` with code_analysis data
- Pass llm_client to enable LLM path when available
- Merge code-grounded claims with documentation claims
- Add 3+ new unit tests (LLM mocked, offline fallback, claim structure)
- Verify existing tests pass unchanged
- Document integration in evidence.md

### Out of scope
- Modifying the `extract_claims_from_code_analysis()` implementation (already complete)
- Changing code_analyzer.py or analyze_repository_code() logic
- Modifying LLM prompts or response parsing (already implemented)
- Adding new claim_kind values or claim structure fields
- Changing pilot configurations or expected outputs (changes are expected, not prescribed)

## Inputs
- Existing `code_analysis` dict from `analyze_repository_code()` in worker.py
- `product_name` from repo_inventory
- `repo_dir` path
- Optional `llm_client` for LLM-based generation
- Existing `extract_claims_from_code_analysis()` implementation (lines 917-1056)

## Outputs
- Modified `extract_claims()` function in extract_claims.py that loads and uses code_analysis
- Code-grounded claims merged into extracted_claims.json artifact
- 3+ new unit tests in test_tc_411_extract_claims.py
- Increased claim counts in pilot runs (10-30 additional claims per pilot)
- Evidence bundle at reports/agents/agent_b/TC-1401/

## Allowed paths
- plans/taskcards/TC-1401_w2_code_grounded_claims.md
- src/launch/workers/w2_facts_builder/extract_claims.py
- src/launch/workers/w2_facts_builder/worker.py
- tests/unit/workers/test_tc_411_extract_claims.py
- reports/agents/agent_b/TC-1401/plan.md
- reports/agents/agent_b/TC-1401/changes.md
- reports/agents/agent_b/TC-1401/evidence.md
- reports/agents/agent_b/TC-1401/self_review.md

### Allowed paths rationale
TC-1401 integrates existing code-grounded claim generation into the W2 claims extraction pipeline. Modifications are limited to extract_claims.py (load code_analysis, call function, merge claims) and test_tc_411_extract_claims.py (new test cases). Worker.py is read-only reference for understanding code_analysis availability.

## Implementation steps

### Step 1: Load code_analysis artifact in extract_claims()
Location: `extract_claims()` function around line 1104 (after loading repo_inventory.json)

Add code to load code_analysis.json if it exists:
```python
# Load code_analysis.json (TC-1042)
code_analysis_path = run_layout.artifacts_dir / "code_analysis.json"
code_analysis = {}
if code_analysis_path.exists():
    with open(code_analysis_path, 'r', encoding='utf-8') as f:
        code_analysis = json.load(f)
```

### Step 2: Call extract_claims_from_code_analysis()
Location: After documentation claims extraction (around line 1197), before deduplication

Add code-grounded claims:
```python
# Add code-grounded claims from API surface (TC-1401)
if code_analysis:
    code_claims = extract_claims_from_code_analysis(
        code_analysis=code_analysis,
        product_name=product_name,
        repo_dir=repo_dir,
        llm_client=llm_client,
    )
    claims.extend(code_claims)
    logger.info(
        "code_grounded_claims_added",
        count=len(code_claims),
        product_name=product_name,
    )
```

### Step 3: Add unit tests
Location: `tests/unit/workers/test_tc_411_extract_claims.py`

Add new test class `TestCodeGroundedClaims` with 3 tests:
1. `test_extract_claims_with_code_analysis_llm` (mocked LLM)
2. `test_extract_claims_with_code_analysis_offline` (no LLM)
3. `test_code_grounded_claim_structure` (validate claim fields)

Each test creates:
- code_analysis.json with api_surface (classes, functions, modules)
- discovered_docs.json and repo_inventory.json
- Calls extract_claims() and verifies code-grounded claims are present

### Step 4: Run existing test suite
```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_411_extract_claims.py -x
```

Expected: All existing tests pass unchanged (no regressions)

### Step 5: Run full W2 test suite
```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w2_facts_builder.py -x
```

Expected: All tests pass (0 failures)

### Step 6: Document changes and evidence
Create reports/agents/agent_b/TC-1401/ with:
- plan.md (implementation strategy)
- changes.md (files modified, lines changed)
- evidence.md (test results, before/after claim counts)

## Failure modes

### Failure mode 1: code_analysis.json missing or malformed
**Detection:** FileNotFoundError or json.JSONDecodeError when loading code_analysis.json
**Resolution:** Add defensive check: `if code_analysis_path.exists()` and handle gracefully; log warning if missing but continue (code-grounded claims are optional enhancement)
**Spec/Gate:** specs/21_worker_contracts.md:98-125 (W2 must handle missing artifacts gracefully)

### Failure mode 2: Existing tests fail after integration
**Detection:** pytest exit code non-zero; test failure messages showing claim_id mismatches or count differences
**Resolution:** Review test fixtures; ensure code_analysis integration doesn't break documentation claim extraction; verify deduplication still works; check that offline/LLM paths both work
**Spec/Gate:** Acceptance criteria #1 (all existing tests pass)

### Failure mode 3: LLM path generates invalid JSON
**Detection:** ValueError from `_parse_code_grounded_llm_response()` or missing required fields
**Resolution:** LLM path already has try/except that falls back to offline path; verify fallback triggers correctly; check logger.warning for "code_grounded_claims_llm_failed"
**Spec/Gate:** specs/03_product_facts_and_evidence.md (offline fallback must always work)

### Failure mode 4: Code-grounded claims duplicate documentation claims
**Detection:** High duplicate rate in deduplicate_claims(); claim counts lower than expected
**Resolution:** Review claim_id computation for code-grounded claims; ensure claim_text differs from doc claims; check that compute_claim_id() produces stable, unique IDs
**Spec/Gate:** specs/04_claims_compiler_truth_lock.md:12-19 (claim_id must be deterministic and unique)

### Failure mode 5: Pilot claim counts decrease instead of increase
**Detection:** Pilots show fewer claims after integration
**Resolution:** Bug in integration logic; verify code_claims are extended not replaced; check that code_analysis has non-empty api_surface; review logs for "code_grounded_claims_added" event
**Spec/Gate:** Acceptance criteria #5 (pilot claim counts increase by 10-30)

### Failure mode 6: Taskcard validation fails (missing sections, wrong status)
**Detection:** tools/validate_taskcards.py shows errors for TC-1401
**Resolution:** Ensure all 14 mandatory sections present; status must be "Draft", "In-Progress", or "Done"; evidence_required is a list; allowed_paths match between frontmatter and body
**Spec/Gate:** Gate B (taskcard validation), plans/taskcards/00_TASKCARD_CONTRACT.md

## Task-specific review checklist
1. [ ] code_analysis.json loading is defensive (handles missing file gracefully)
2. [ ] extract_claims_from_code_analysis() called with all 4 parameters (code_analysis, product_name, repo_dir, llm_client)
3. [ ] Code-grounded claims are extended to claims list (not replaced)
4. [ ] Integration happens BEFORE deduplication and validation (so code claims go through same pipeline)
5. [ ] All 3 new tests pass (LLM mocked, offline, structure validation)
6. [ ] All existing tests pass unchanged (test_tc_411_extract_claims.py)
7. [ ] Logger emits "code_grounded_claims_added" event with count
8. [ ] Pilot runs show increased claim counts (verify with before/after comparison)
9. [ ] Frontmatter and body allowed_paths match exactly
10. [ ] spec_ref SHA is correct: 0cd4ce327b97b36f870adf2909707cf560b7e50c
11. [ ] All 14 mandatory taskcard sections present
12. [ ] Self-review 12D checklist complete with all dimensions ≥4/5

## Deliverables
- Modified src/launch/workers/w2_facts_builder/extract_claims.py with code_analysis integration
- 3+ new unit tests in tests/unit/workers/test_tc_411_extract_claims.py
- Test run showing all existing tests pass (pytest output)
- Evidence bundle at reports/agents/agent_b/TC-1401/evidence.md
- Self-review at reports/agents/agent_b/TC-1401/self_review.md with 12D assessment
- Changes manifest at reports/agents/agent_b/TC-1401/changes.md

## Acceptance checks
1. [ ] All existing tests in test_tc_411_extract_claims.py pass unchanged (0 failures)
2. [ ] 3+ new tests added for code-grounded claims (LLM mocked, offline, structure)
3. [ ] extract_claims() successfully loads and uses code_analysis.json
4. [ ] Code-grounded claims appear in extracted_claims.json artifact
5. [ ] Pilot claim counts increase by 10-30 claims (verify with before/after comparison)
6. [ ] Logger shows "code_grounded_claims_added" or "code_grounded_claims_offline" events
7. [ ] Self-review scores all 12 dimensions ≥4/5 with no Known Gaps

## Preconditions / dependencies
- Python virtual environment activated (.venv)
- All dependencies installed
- TC-1042 complete (code_analyzer.py generates code_analysis.json with api_surface)
- code_analysis.json artifact exists in artifacts/ directory
- extract_claims_from_code_analysis() function exists (lines 917-1056)

## Test plan
1. **Test case 1**: LLM path with mocked client
   - Setup: Create code_analysis.json with api_surface, mock LLM client
   - Execute: Call extract_claims() with llm_client
   - Expected: Code-grounded claims present, logger shows "code_grounded_claims_llm"

2. **Test case 2**: Offline path without LLM
   - Setup: Create code_analysis.json with api_surface, no llm_client
   - Execute: Call extract_claims() with llm_client=None
   - Expected: Template-based claims present, logger shows "code_grounded_claims_offline"

3. **Test case 3**: Claim structure validation
   - Setup: Generate code-grounded claims (either path)
   - Execute: Validate claim fields (claim_id, claim_text, claim_kind, truth_status, confidence, source_priority, citations)
   - Expected: All fields present and valid, truth_status="fact", confidence="high", source_priority=2

4. **Test case 4**: Integration with existing claims
   - Setup: Create both documentation and code_analysis artifacts
   - Execute: Call extract_claims() and count total claims
   - Expected: Total claims = doc_claims + code_claims (merged correctly)

5. **Test case 5**: Regression test
   - Setup: Run full test suite
   - Execute: pytest tests/unit/workers/test_tc_411_extract_claims.py
   - Expected: All existing tests pass (0 failures)

## Self-review

### 12D Checklist
1. **Determinism:** Integration uses deterministic compute_claim_id() for stable IDs; code_analysis loading order is deterministic (single file); no timestamps or randomness introduced

2. **Dependencies:** No new dependencies added; reuses existing code_analyzer.py output; llm_client dependency already exists

3. **Documentation:** Added TC-1401 comments at integration points; updated evidence.md with before/after claim counts; self-review documents all changes

4. **Data preservation:** Documentation claims unchanged; code-grounded claims are additive; deduplication preserves highest-priority claim per ID

5. **Deliberate design:** Integration point chosen BEFORE deduplication so code claims go through same validation pipeline as doc claims; defensive loading handles missing code_analysis.json gracefully

6. **Detection:** Logger emits "code_grounded_claims_added" event; existing validation catches malformed claims; tests verify structure

7. **Diagnostics:** Logger shows claim count and source (llm vs offline); existing test suite provides coverage; evidence.md captures before/after metrics

8. **Defensive coding:** Defensive check for code_analysis_path.exists(); graceful handling of missing/malformed code_analysis; LLM fallback to offline path already implemented

9. **Direct testing:** 3+ new unit tests cover LLM, offline, and structure validation paths; existing test suite verifies no regressions

10. **Deployment safety:** Change is purely additive (doesn't modify existing logic); can revert by removing code_analysis loading block; pilots expected to show increased claims (positive change)

11. **Delta tracking:** Modified 1 function (extract_claims), added ~15 lines; 3+ new tests; evidence.md documents all changes

12. **Downstream impact:** W4 IAPlanner and W5 SectionWriter will see more claims (positive); content quality expected to improve with API-grounded claims; no breaking changes to claim structure

### Verification results
- [ ] Tests: X/X PASS (tests/unit/workers/test_tc_411_extract_claims.py)
- [ ] Tests: X/X PASS (tests/unit/workers/test_w2_facts_builder.py)
- [ ] Evidence captured: reports/agents/agent_b/TC-1401/evidence.md

## E2E verification
```bash
# Run TC-411 test suite
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_411_extract_claims.py -x -v

# Run W2 test suite
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w2_facts_builder.py -x -v

# Run integration tests (optional, if env allows)
.venv/Scripts/python.exe -m pytest tests/integration/ -k w2 -x
```

**Expected artifacts:**
- **tests/unit/workers/test_tc_411_extract_claims.py** - Contains 3+ new tests for code-grounded claims
- **src/launch/workers/w2_facts_builder/extract_claims.py** - Modified extract_claims() function
- **reports/agents/agent_b/TC-1401/evidence.md** - Before/after claim counts, test results
- **reports/agents/agent_b/TC-1401/self_review.md** - 12D assessment with all dimensions ≥4/5

**Expected results:**
- All existing tests pass (0 failures, 0 regressions)
- 3+ new tests pass (code-grounded claims validated)
- Pilot claim counts increase by 10-30 per pilot
- Logger shows "code_grounded_claims_added" events

## Integration boundary proven
**Upstream:** code_analyzer.py generates code_analysis.json artifact with api_surface (classes, functions, modules) via analyze_repository_code(). This artifact is written to artifacts/ directory by W2 worker.

**Downstream:** extract_claims() loads code_analysis.json, calls extract_claims_from_code_analysis(), and merges code-grounded claims into extracted_claims.json. Downstream W4 IAPlanner and W5 SectionWriter consume claims from extracted_claims.json.

**Contract:**
- code_analysis.json format: `{"api_surface": {"classes": [], "functions": [], "modules": []}, "constants": {}, "code_structure": {}}`
- Code-grounded claims have: truth_status="fact", confidence="high", source_priority=2
- Claims use compute_claim_id() for stable IDs
- Integration happens BEFORE deduplication (so code claims can dedupe with doc claims)
- Missing code_analysis.json is handled gracefully (logs warning, continues without code claims)

## Evidence Location
`reports/agents/agent_b/TC-1401/evidence.md`
