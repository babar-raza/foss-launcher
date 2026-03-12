# Healing Plan — Test Coverage (QSR-01, QSR-02, QSR-03)
# Source: Self-review gaps G-01, G-02, G-03
# Date: 2026-03-11

---

## Taskcard QSR-01 — Unit tests for TC-4040: format_matrix → ProductEvidence wiring

**Status**: Done
**Gap linkage**: G-01 — Zero unit tests for format_matrix wiring added in TC-4040
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: Add ≥8 unit tests covering the new `supported_formats`, `input_formats`,
`output_formats` population logic in `_entry.py` AND the `or`-fallback merge logic
in `worker.py`.

**Allowed paths**:
- `plans/healing/QSR-test-coverage.md` (this file)
- `tests/unit/workers/test_understand_product_evidence.py`
- `tests/unit/workers/understand/test_extract.py`

**Forbidden**: Any other path. No changes to `src/` files.

### Acceptance checks

**CLI**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_understand_product_evidence.py \
  tests/unit/workers/understand/test_extract.py \
  -v --tb=short
```
Expected: all existing tests pass + ≥8 new tests pass.

**UI/Web/API**: N/A

**Tests** (must all pass):
1. `test_product_evidence_supported_formats_from_format_matrix` — given `_format_matrix` with 3 records (can_import=True, can_export=True, can_import=False+can_export=True), verify `supported_formats` = [name0, name1, name2], `input_formats` = [name0, name1], `output_formats` = [name1, name2]
2. `test_product_evidence_empty_format_matrix_yields_empty_lists` — given `_format_matrix = []`, verify all three format lists are empty `[]`
3. `test_product_evidence_import_only_formats` — record with can_import=True, can_export=False appears only in `input_formats` and `supported_formats`, not in `output_formats`
4. `test_product_evidence_export_only_formats` — record with can_import=False, can_export=True appears only in `output_formats` and `supported_formats`, not in `input_formats`
5. `test_worker_merge_prefers_extract_formats_when_non_empty` — `extract_evidence.supported_formats = ["OBJ", "FBX"]`, `repo_evidence.supported_formats = ["DOCX"]` → merged result has ["OBJ", "FBX"]
6. `test_worker_merge_falls_back_to_repo_formats_when_extract_empty` — `extract_evidence.supported_formats = []`, `repo_evidence.supported_formats = ["DOCX"]` → merged result has ["DOCX"]
7. `test_worker_merge_format_fields_isolated` — changing `input_formats` fallback does not affect `output_formats` fallback independently
8. `test_worker_merge_preserves_existing_fields` — format merge does NOT overwrite `limitations`, `workflow_examples`, `install_recipe` from extract_evidence

**Config respected end-to-end**: N/A (unit tests only)
**No mock data in production paths**: All tests use real `ProductEvidence` and `FormatRecord` model instances.

### Deliverables

1. **Full test additions** to `tests/unit/workers/test_understand_product_evidence.py`:
   - Class `TestFormatMatrixWiring` with tests 1–4 above
   - Each test constructs `FormatRecord` instances directly (from `launcher.models.product`)
   - Each test constructs `ProductEvidence` with the format list args and asserts fields

2. **Full test additions** to `tests/unit/workers/understand/test_extract.py`:
   - Tests 5–8 as `TestWorkerMergeFormatFallback` class
   - Use `ProductEvidence.model_copy(update={...})` to simulate the merge step
   - Test 8 verifies `limitations`, `workflow_examples`, `install_recipe` are unchanged

3. No stubs, no TODOs, no mocks that bypass real model validation.

### Hard rules

- No network calls in tests
- All tests deterministic (no random data)
- No new dependencies (only `launcher.models.product`, `launcher.models.understanding`)
- `FormatRecord` and `ProductEvidence` imported directly — do not mock Pydantic models
- Keep existing 6 tests in `test_understand_product_evidence.py` passing unchanged

### Review dimensions (5/5 means)

| Dimension | 5/5 definition for this taskcard |
|-----------|----------------------------------|
| Thoroughness | All 4 format fields covered (supported, input, output + empty fallback) + merge fallback logic |
| Correctness | Assertions match exact model field names and list comprehension semantics |
| Testability | Tests use real model instances; no mocks |
| Robustness | Edge cases: empty matrix, import-only, export-only, empty-fallback |
| Minimality | No new test fixtures — use model constructors directly |

### Now (runbook)

```bash
# 1. Verify FormatRecord and ProductEvidence field names
grep -n "class FormatRecord\|can_import\|can_export\|supported_formats" \
  src/launcher/models/product.py src/launcher/models/understanding.py

# 2. Run existing tests to confirm baseline
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_understand_product_evidence.py -v

# 3. Add new test class TestFormatMatrixWiring to test_understand_product_evidence.py
# 4. Add new test class TestWorkerMergeFormatFallback to test_extract.py
# 5. Run new tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_understand_product_evidence.py \
  tests/unit/workers/understand/test_extract.py -v

# 6. Confirm full suite still passes
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q \
  --ignore=tests/unit/workers/test_publish.py
```

---

## Taskcard QSR-02 — Unit tests for TC-4041: injection blocks in section_prompt

**Status**: Done
**Gap linkage**: G-02 — Zero unit tests for workflow_examples + format_matrix injection added in TC-4041
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: Add ≥8 unit tests to `tests/unit/workers/generate/test_section_prompt.py`
covering: (a) workflow_examples block present/absent/capped, (b) format_matrix block
present/absent/role-gated, (c) interaction with existing limitations block.

**Allowed paths**:
- `plans/healing/QSR-test-coverage.md` (this file)
- `tests/unit/workers/generate/test_section_prompt.py`

**Forbidden**: Any other path. No changes to `src/` files.

### Acceptance checks

**CLI**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/generate/test_section_prompt.py -v --tb=short
```
Expected: all existing tests pass + ≥8 new tests pass.

**UI/Web/API**: N/A

**Tests** (must all pass):
1. `test_workflow_examples_block_present_when_non_empty` — given 2 WorkflowExample objects, assert "REAL USAGE PATTERNS" appears in the returned prompt string
2. `test_workflow_examples_block_absent_when_empty` — given `workflow_examples=[]`, assert "REAL USAGE PATTERNS" does NOT appear
3. `test_workflow_examples_block_absent_when_none` — given `workflow_examples=None`, assert "REAL USAGE PATTERNS" does NOT appear
4. `test_workflow_examples_capped_at_3` — given 5 WorkflowExample objects, assert the prompt contains ≤3 "```" fenced blocks from the workflow section (not 5)
5. `test_format_matrix_block_present_for_eligible_role` — given `supported_formats={"input":["OBJ"],"output":["FBX"]}` and `page.page_role="feature_overview"`, assert "SUPPORTED FORMATS" appears
6. `test_format_matrix_block_absent_for_ineligible_role` — same `supported_formats` but `page.page_role="class_reference"`, assert "SUPPORTED FORMATS" does NOT appear
7. `test_format_matrix_block_absent_when_formats_none` — `supported_formats=None`, assert "SUPPORTED FORMATS" does NOT appear
8. `test_format_matrix_input_and_output_labels` — given both input and output formats, assert "Input:" and "Output:" both appear in the prompt
9. `test_workflow_examples_code_capped_at_500_chars` — given WorkflowExample with `code="x"*1000`, assert the injected code block is ≤500 chars
10. `test_existing_limitations_block_unaffected` — given both limitations and workflow_examples, assert both "KNOWN LIMITATIONS" and "REAL USAGE PATTERNS" appear (no interference)

**Config respected end-to-end**: `_FORMAT_ELIGIBLE_ROLES` controls gating — tests cover at least one eligible and one ineligible role.
**No mock data in production paths**: All tests call `build_section_prompt()` with real model instances.

### Deliverables

1. **Full test additions** to `tests/unit/workers/generate/test_section_prompt.py`:
   - New class `TestWorkflowExamplesInjection` containing tests 1–4 + 9
   - New class `TestFormatMatrixInjection` containing tests 5–8
   - New class `TestInjectionInteraction` containing test 10
   - Each test creates minimal `SkeletonSection`, `PlannedPage`, `ProductIdentity` stubs (match existing test patterns in the file)
   - `WorkflowExample` constructed from `launcher.models.understanding`

2. No stubs, no TODOs, no mocks bypassing `build_section_prompt()`.

### Hard rules

- No network calls
- Deterministic: no random data
- No new test fixtures beyond what existing tests already define — reuse helpers
- All assertions on string content (use `assert "X" in prompt` pattern)
- Do NOT change `build_section_prompt()` signature — it must match current implementation

### Review dimensions (5/5 means)

| Dimension | 5/5 definition for this taskcard |
|-----------|----------------------------------|
| Thoroughness | All 4 injection states covered: present, absent (empty), absent (None), capped |
| Correctness | Role-gating logic tested with both eligible and ineligible roles |
| Robustness | Code cap test (500 chars), None vs empty list distinction |
| Testability | Tests call real function; no mocks; assertions on actual prompt string |
| Minimality | Reuse existing test helpers; no new fixtures |

### Now (runbook)

```bash
# 1. Inspect existing test structure to understand helper patterns
grep -n "def _make_page\|def _make_section\|def _make_product\|fixture" \
  tests/unit/workers/generate/test_section_prompt.py | head -20

# 2. Check WorkflowExample fields
grep -n "class WorkflowExample" -A 10 src/launcher/models/understanding.py

# 3. Run existing tests as baseline
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/generate/test_section_prompt.py -q

# 4. Add new test classes
# 5. Run new tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/generate/test_section_prompt.py -v

# 6. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q \
  --ignore=tests/unit/workers/test_publish.py
```

---

## Taskcard QSR-03 — Integration test for 5-hop evidence chain

**Status**: Not Started
**Gap linkage**: G-03 — No integration test verifying _format_matrix → ProductEvidence → worker merge → generate → build_section_prompt end-to-end
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: Add 1 integration-style test that constructs a minimal pipeline context, runs
the understand extract phase with a fake repo containing a format enum, then verifies
the resulting `section_prompt` output contains format-specific content. This test
crosses the understand/generate boundary.

**Allowed paths**:
- `plans/healing/QSR-test-coverage.md` (this file)
- `tests/integration/test_extract_embeddings.py` (extend if appropriate) OR new file:
- `tests/integration/test_evidence_chain.py` (new file)

**Forbidden**: Any other path. No changes to `src/` files.

### Acceptance checks

**CLI**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/integration/test_evidence_chain.py -v --tb=short
```
Expected: integration test(s) pass.

**UI/Web/API**: N/A

**Tests** (must all pass):
1. `test_format_matrix_flows_through_to_section_prompt` — given a fake `ProductEvidence` with `input_formats=["OBJ"]`, `output_formats=["FBX"]`, and a `PlannedPage` with `page_role="feature_overview"`, call `build_section_prompt()` and assert "OBJ" and "FBX" appear in the output
2. `test_workflow_examples_flow_through_to_section_prompt` — given `ProductEvidence.workflow_examples=[WorkflowExample(title="Load Scene", code="scene=Scene()")]`, call `build_section_prompt()` and assert "Load Scene" appears in output
3. `test_empty_evidence_produces_no_injection` — given `ProductEvidence` with empty workflow_examples and formats, assert neither "REAL USAGE PATTERNS" nor "SUPPORTED FORMATS" appear in output

**Config respected end-to-end**: Tests use the real `build_section_prompt()` function.
**No mock data in production paths**: No monkeypatching of core functions.

### Deliverables

1. **New file** `tests/integration/test_evidence_chain.py` with the 3 tests above.
2. All tests use real `ProductEvidence`, `WorkflowExample`, `PlannedPage`, `ProductIdentity`, `SkeletonSection` model instances.
3. Tests must pass in offline mode (no LLM calls, no network).

### Hard rules

- No network calls — `build_section_prompt()` is pure string construction; no LLM needed
- No new dependencies
- Tests must be deterministic (no randomness)

### Review dimensions (5/5 means)

| Dimension | 5/5 definition for this taskcard |
|-----------|----------------------------------|
| Thoroughness | All 3 injection states: both present, one present, both absent |
| Integration fit | Crosses understand→generate boundary using real model objects |
| Robustness | Empty-evidence case explicitly tested |
| Minimality | 3 tests in one file; no test infrastructure beyond model construction |

### Now (runbook)

```bash
# 1. Confirm build_section_prompt signature
grep -n "^def build_section_prompt" src/launcher/workers/generate/section_prompt.py

# 2. Check imports needed (PlannedPage, SkeletonSection, ProductIdentity)
grep -rn "class PlannedPage\|class SkeletonSection\|class ProductIdentity" \
  src/launcher/models/ | head -10

# 3. Create test file
# 4. Run
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/integration/test_evidence_chain.py -v

# 5. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q \
  --ignore=tests/unit/workers/test_publish.py
```
