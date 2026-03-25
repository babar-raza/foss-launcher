# Evidence: TC-3110 WS-C - W5 Symbol Grounding Guardrail Tests

## Artifact

**File**: `tests/unit/workers/test_w5_fence_audit.py`  
**Line count**: 234 lines

## Syntax Check

Command:
```
.venv/Scripts/python.exe -c "import ast; ast.parse(open('tests/unit/workers/test_w5_fence_audit.py').read()); print('syntax OK')"
```
Result: `syntax OK`

## Validator Import Check

Command:
```
.venv/Scripts/python.exe -c "from launch.workers._shared.code_fence_validator import build_compact_allowlist, audit_fence, FenceAuditResult, GENERIC_FENCE_RE, extract_identifiers_heuristic, CompactAllowlist; print('imports OK')"
```
Result: `imports OK`

## WS-B Import Status

`_audit_code_fences` and `_format_compact_repair_prompt` not yet available in `multi_pass.py` (WS-B pending).
The 10 tests in `TestAuditCodeFences` and `TestCompactRepairPrompt` are decorated with
`@pytest.mark.skipif(not MULTI_PASS_AVAILABLE, ...)` and skip gracefully.

## Partial Test Run (WS-A classes only)

Command:
```
pytest tests/unit/workers/test_w5_fence_audit.py::TestCompactAllowlist
      tests/unit/workers/test_w5_fence_audit.py::TestExtractIdentifiers
      tests/unit/workers/test_w5_fence_audit.py::TestAuditFence -v
```

Output:
```
platform win32 -- Python 3.13.2, pytest-8.4.2
collected 12 items

tests/unit/workers/test_w5_fence_audit.py ............            [100%]

======================== 12 passed, 1 warning in 0.81s ========================
```

## Full File Run (all 22 tests)

Command: `pytest tests/unit/workers/test_w5_fence_audit.py -v`

Output:
```
collected 22 items

tests/unit/workers/test_w5_fence_audit.py ............ssssssssss   [100%]

================== 12 passed, 10 skipped, 1 warning in 0.89s ==================
```

- 12 tests pass (TestCompactAllowlist: 3, TestExtractIdentifiers: 5, TestAuditFence: 4)
- 10 tests skipped (TestAuditCodeFences: 7, TestCompactRepairPrompt: 3) - pending WS-B

## Test Classes Summary

| Class | Tests | Status |
|-------|-------|--------|
| TestCompactAllowlist | 3 | PASS |
| TestExtractIdentifiers | 5 | PASS |
| TestAuditFence | 4 | PASS |
| TestAuditCodeFences | 7 | SKIP (WS-B pending) |
| TestCompactRepairPrompt | 3 | SKIP (WS-B pending) |
| **Total** | **22** | **12 pass, 10 skip** |
