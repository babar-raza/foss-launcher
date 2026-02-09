---
id: TC-1050-T3
title: "Extract Stopwords to Shared Constant"
status: Done
priority: Normal
owner: "Agent-B"
updated: "2026-02-08"
tags: ["w2", "refactoring", "dry"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-1050-T3_extract_stopwords_shared.md
  - plans/taskcards/INDEX.md
  - src/launch/workers/w2_facts_builder/_shared.py
  - src/launch/workers/w2_facts_builder/embeddings.py
  - src/launch/workers/w2_facts_builder/map_evidence.py
  - tests/unit/workers/test_w2_*.py
  - reports/agents/agent_b/TC-1050-T3/**
evidence_required:
  - reports/agents/agent_b/TC-1050-T3/evidence.md
  - reports/agents/agent_b/TC-1050-T3/self_review.md
spec_ref: "7840566"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1050-T3 — Extract Stopwords to Shared Constant

## Objective
Extract STOPWORDS constant to shared module (`_shared.py`) to eliminate duplication and establish single source of truth for W2 FactsBuilder stopwords.

## Problem Statement
STOPWORDS constant is duplicated in two locations:
- `src/launch/workers/w2_facts_builder/embeddings.py` line 29-35: `STOPWORDS = frozenset({...})`
- `src/launch/workers/w2_facts_builder/map_evidence.py` line 38-44: `_STOPWORDS = frozenset({...})`

This violates DRY principle and creates maintenance burden. Any future stopword adjustments require changes in multiple locations.

## Required spec references
- specs/03_product_facts_and_evidence.md (Evidence mapping and claims)
- specs/07_code_analysis_and_enrichment.md (Code analysis and enrichment)
- specs/30_ai_agent_governance.md (Code quality and maintainability)
- plans/taskcards/00_TASKCARD_CONTRACT.md (Taskcard format requirements)

## Scope

### In scope
- Create new `src/launch/workers/w2_facts_builder/_shared.py` module with STOPWORDS constant
- Update `embeddings.py` to import STOPWORDS from `_shared.py`
- Update `map_evidence.py` to import STOPWORDS from `_shared.py` (replace `_STOPWORDS`)
- Verify all tests pass after refactoring

### Out of scope
- Changing stopword list contents
- Modifying stopword filtering logic in either module
- Adding new shared constants beyond STOPWORDS
- Performance optimization

## Inputs
- Existing `embeddings.py` with STOPWORDS definition (lines 29-35)
- Existing `map_evidence.py` with _STOPWORDS definition (lines 38-44)
- Existing test suite for W2 workers

## Outputs
- New `_shared.py` module with STOPWORDS constant
- Modified `embeddings.py` importing from `_shared`
- Modified `map_evidence.py` importing from `_shared` (renamed from `_STOPWORDS` to `STOPWORDS`)
- All tests passing (2531+ tests)
- Evidence bundle in `reports/agents/agent_b/TC-1050-T3/`

## Allowed paths
- plans/taskcards/TC-1050-T3_extract_stopwords_shared.md
- plans/taskcards/INDEX.md
- src/launch/workers/w2_facts_builder/_shared.py
- src/launch/workers/w2_facts_builder/embeddings.py
- src/launch/workers/w2_facts_builder/map_evidence.py
- tests/unit/workers/test_w2_*.py
- reports/agents/agent_b/TC-1050-T3/**

### Allowed paths rationale
TC-1050-T3 creates new `_shared.py` module and updates existing W2 modules to import from it. Tests verify correctness. Evidence bundle documents changes.

## Implementation steps

### Step 1: Create _shared.py module
Create new file `src/launch/workers/w2_facts_builder/_shared.py` with STOPWORDS constant:

```python
"""Shared constants for W2 FactsBuilder workers."""

STOPWORDS = frozenset({
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
    'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
    'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this',
    'that', 'these', 'those', 'it', 'its',
})
```

### Step 2: Update embeddings.py
Replace STOPWORDS definition (lines 29-35) with import:

**Before:**
```python
STOPWORDS: frozenset[str] = frozenset({
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
    'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
    'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this',
    'that', 'these', 'those', 'it', 'its',
})
```

**After:**
```python
from ._shared import STOPWORDS
```

### Step 3: Update map_evidence.py
Replace _STOPWORDS definition (lines 38-44) with import and update all references:

**Before:**
```python
_STOPWORDS: frozenset = frozenset({
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
    'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
    'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this',
    'that', 'these', 'those', 'it', 'its',
})
```

**After:**
```python
from ._shared import STOPWORDS
```

**References to update:**
- All uses of `_STOPWORDS` → `STOPWORDS` throughout the module

### Step 4: Verify imports work
Test Python imports to ensure module loading succeeds:

```powershell
.venv\Scripts\python.exe -c "from launch.workers.w2_facts_builder._shared import STOPWORDS; print(len(STOPWORDS))"
.venv\Scripts\python.exe -c "from launch.workers.w2_facts_builder.embeddings import STOPWORDS; print(len(STOPWORDS))"
.venv\Scripts\python.exe -c "from launch.workers.w2_facts_builder.map_evidence import STOPWORDS; print(len(STOPWORDS))"
```

Expected output: `36` (or actual stopword count) for all three imports

### Step 5: Run W2 tests
Run all W2-related tests to verify no regressions:

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_w2_*.py -x
```

Expected: All tests PASS, exit code 0

### Step 6: Register taskcard in INDEX.md
Add entry to `plans/taskcards/INDEX.md` under "W2 Intelligence — Deep Code Understanding" section:

```markdown
- TC-1050-T3 — Extract Stopwords to Shared Constant — Agent-B
```

### Step 7: Create evidence bundle
Create evidence directory and capture artifacts:
- `reports/agents/agent_b/TC-1050-T3/evidence.md` — Full evidence bundle
- `reports/agents/agent_b/TC-1050-T3/self_review.md` — 12D self-review

## Failure modes

### Failure mode 1: Import fails due to circular dependency
**Detection:** Python raises `ImportError` or `AttributeError` when importing from `_shared.py`
**Resolution:** Verify `_shared.py` has no imports from other W2 modules; ensure it contains only constants
**Spec/Gate:** Python module loading contract

### Failure mode 2: Tests fail due to STOPWORDS reference mismatch
**Detection:** pytest shows failures in test_w2_*.py modules; assertion errors on stopword filtering
**Resolution:** Search for remaining `_STOPWORDS` references in map_evidence.py; ensure all replaced with `STOPWORDS`
**Spec/Gate:** Test suite regression detection

### Failure mode 3: Module not found error in production code
**Detection:** Runtime `ModuleNotFoundError: No module named '_shared'`
**Resolution:** Verify `_shared.py` exists in correct location; ensure `__init__.py` not blocking imports
**Spec/Gate:** Python package structure contract

### Failure mode 4: Taskcard validation fails
**Detection:** `validate_taskcards.py` shows missing sections or malformed frontmatter
**Resolution:** Review against 00_TASKCARD_CONTRACT.md; ensure all 14 sections present; verify frontmatter matches body allowed_paths
**Spec/Gate:** Gate B taskcard validation

### Failure mode 5: Evidence bundle incomplete
**Detection:** Missing evidence.md or self_review.md files in reports/agents/agent_b/TC-1050-T3/
**Resolution:** Create evidence directory structure; populate with code diffs and test results
**Spec/Gate:** Taskcard contract evidence requirements

### Failure mode 6: INDEX.md registration missing or malformed
**Detection:** TC-1050-T3 not listed in INDEX.md; incorrect format or location
**Resolution:** Add entry in appropriate section; follow existing format pattern
**Spec/Gate:** Taskcard contract registration requirements

## Task-specific review checklist
1. [ ] _shared.py created with STOPWORDS frozenset (36 items)
2. [ ] embeddings.py imports STOPWORDS from _shared (no local definition)
3. [ ] map_evidence.py imports STOPWORDS from _shared (no local _STOPWORDS definition)
4. [ ] All _STOPWORDS references in map_evidence.py replaced with STOPWORDS
5. [ ] Python imports succeed for all three modules
6. [ ] All W2 tests pass (test_w2_*.py modules)
7. [ ] TC-1050-T3 registered in INDEX.md
8. [ ] Evidence bundle complete (evidence.md + self_review.md)
9. [ ] Frontmatter and body allowed_paths match exactly
10. [ ] 12D self-review shows all dimensions >= 4/5

## Deliverables
- New file: `src/launch/workers/w2_facts_builder/_shared.py`
- Modified file: `src/launch/workers/w2_facts_builder/embeddings.py`
- Modified file: `src/launch/workers/w2_facts_builder/map_evidence.py`
- Updated: `plans/taskcards/INDEX.md` with TC-1050-T3 entry
- Evidence: `reports/agents/agent_b/TC-1050-T3/evidence.md`
- Self-review: `reports/agents/agent_b/TC-1050-T3/self_review.md`
- Test results: All W2 tests passing

## Acceptance checks
1. [ ] _shared.py exists with correct STOPWORDS definition
2. [ ] embeddings.py imports from _shared (no duplicate definition)
3. [ ] map_evidence.py imports from _shared (no duplicate _STOPWORDS)
4. [ ] All W2 tests pass (pytest exit code 0)
5. [ ] Python imports succeed for all three modules
6. [ ] TC-1050-T3 registered in INDEX.md
7. [ ] Evidence bundle complete and accurate

## Preconditions / dependencies
- Python virtual environment activated (.venv)
- All dependencies installed
- Existing W2 modules (embeddings.py, map_evidence.py) functional
- Test suite passing baseline established

## Test plan
1. **Test case 1:** Import _shared.py directly
   - Command: `.venv\Scripts\python.exe -c "from launch.workers.w2_facts_builder._shared import STOPWORDS; print(len(STOPWORDS))"`
   - Expected: Prints stopword count (36), no errors

2. **Test case 2:** Import STOPWORDS from embeddings.py
   - Command: `.venv\Scripts\python.exe -c "from launch.workers.w2_facts_builder.embeddings import STOPWORDS; print(len(STOPWORDS))"`
   - Expected: Prints stopword count, no errors

3. **Test case 3:** Import STOPWORDS from map_evidence.py
   - Command: `.venv\Scripts\python.exe -c "from launch.workers.w2_facts_builder.map_evidence import STOPWORDS; print(len(STOPWORDS))"`
   - Expected: Prints stopword count, no errors

4. **Test case 4:** Run W2 test suite
   - Command: `PYTHONHASHSEED=0 .venv\Scripts\python.exe -m pytest tests/unit/workers/test_w2_*.py -x`
   - Expected: All tests PASS, exit code 0

## Self-review

### 12D Checklist

1. **Determinism:** STOPWORDS is a frozenset (immutable), ensures deterministic behavior across all uses. No random or time-dependent elements.

2. **Dependencies:** No new dependencies added. Only internal refactoring moving constant to shared module.

3. **Documentation:** Module docstring added to _shared.py explaining purpose. TC-1050-T3 taskcard documents rationale.

4. **Data preservation:** STOPWORDS content unchanged. Purely structural refactoring with no semantic changes.

5. **Deliberate design:** Shared module (_shared.py) chosen to establish single source of truth, follows Python best practices for shared constants.

6. **Detection:** Import errors would be immediately visible at module load time. Test suite detects behavioral regressions.

7. **Diagnostics:** No logging changes needed. Import failures provide clear stack traces.

8. **Defensive coding:** frozenset ensures immutability. No validation needed for constant definition.

9. **Direct testing:** Test suite exercises both modules extensively. Import verification confirms structural correctness.

10. **Deployment safety:** Pure refactoring with no logic changes. Can revert by restoring duplicate definitions if needed.

11. **Delta tracking:** Changes limited to: 1) _shared.py creation, 2) embeddings.py import change, 3) map_evidence.py import change and reference updates.

12. **Downstream impact:** Transparent to all consumers. Public API unchanged (STOPWORDS still accessible from both modules).

### Verification results
- [ ] Tests: W2 test suite PASS
- [ ] Imports: All three modules import successfully
- [ ] Evidence captured: reports/agents/agent_b/TC-1050-T3/

## E2E verification

```bash
# Verify imports work
.venv/Scripts/python.exe -c "from launch.workers.w2_facts_builder._shared import STOPWORDS; print('_shared:', len(STOPWORDS))"
.venv/Scripts/python.exe -c "from launch.workers.w2_facts_builder.embeddings import STOPWORDS; print('embeddings:', len(STOPWORDS))"
.venv/Scripts/python.exe -c "from launch.workers.w2_facts_builder.map_evidence import STOPWORDS; print('map_evidence:', len(STOPWORDS))"

# Run W2 test suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_w2_*.py -x -v
```

**Expected artifacts:**
- **src/launch/workers/w2_facts_builder/_shared.py** - Contains STOPWORDS frozenset
- **src/launch/workers/w2_facts_builder/embeddings.py** - Imports from _shared
- **src/launch/workers/w2_facts_builder/map_evidence.py** - Imports from _shared
- **reports/agents/agent_b/TC-1050-T3/evidence.md** - Full evidence bundle
- **reports/agents/agent_b/TC-1050-T3/self_review.md** - 12D self-review

**Expected results:**
- All three imports succeed with identical STOPWORDS count
- All W2 tests pass (pytest exit code 0)
- No behavioral changes in evidence mapping or embeddings

## Integration boundary proven
**Upstream:** Both embeddings.py and map_evidence.py consume STOPWORDS for text tokenization and filtering.

**Downstream:** Tokenization functions (tokenize() in embeddings.py, extract_keywords_from_claim() in map_evidence.py) use STOPWORDS to filter common words.

**Contract:**
- STOPWORDS must be a frozenset[str] (immutable collection of lowercase strings)
- Contains common English stopwords to exclude from semantic analysis
- Accessible via import from _shared, embeddings, or map_evidence modules
- Content must remain stable across module loads (deterministic)

## Evidence Location
`reports/agents/agent_b/TC-1050-T3/`
- `evidence.md` - Implementation details, code diffs, test results
- `self_review.md` - 12D self-review with scoring and verification
