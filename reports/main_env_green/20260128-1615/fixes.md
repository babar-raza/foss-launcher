# Fixes Applied

**Branch**: main (applied directly)
**Base**: main (af8927f)
**Timestamp**: 2026-01-28 16:15 Asia/Karachi

## Baseline Issues

**Gates**: ✅ 21/21 passing (after removing .venv backup)
**Tests**: ❌ 9 failed, 1417 passed, 1 skipped

---

## Fix Log

### Fix 1: LLM Provider Client Tests (3 failures)

**Files Changed**:
- [src/launch/clients/llm_provider.py](../../../src/launch/clients/llm_provider.py)

**Problem**:
Tests were failing with:
```
AttributeError: <module 'launch.clients.llm_provider'> does not have the attribute 'http_post'
```

**Root Cause**:
The `http_post` function was imported inside the `_call_api` method (lazy import) instead of at module level. This prevented test mocking from working correctly.

**Solution**:
Moved the import statement from inside `_call_api()` to the module-level imports section:
```python
# Added at line 21
from .http import http_post
```

**Tests Fixed**:
- `TestLLMProviderClient::test_chat_completion_success`
- `TestLLMProviderClient::test_chat_completion_deterministic_temperature`
- `TestLLMProviderClient::test_evidence_capture_atomic_write`

---

### Fix 2: MCP Server Tests (3 failures)

**Files Changed**:
- [tests/unit/mcp/test_tc_510_server_setup.py](../../../tests/unit/mcp/test_tc_510_server_setup.py)

**Problem**:
Tests were failing with:
```
TypeError: Server.list_tools.<locals>.decorator() missing 1 required positional argument: 'func'
TypeError: mock_context() takes 0 positional arguments but 1 was given
```

**Root Cause**:
Tests were written for MCP library version <1.26, but we're using MCP 1.26.0 which changed the Server API:
1. Handler registration now uses `request_handlers` registry instead of direct decorator access
2. Context manager mocks need to accept `self` parameter

**Solution**:
1. Updated `test_list_tools_returns_empty_list` to use new MCP 1.26+ API:
   ```python
   from mcp import types
   handler = server.request_handlers.get(types.ListToolsRequest)
   result = await handler(types.ListToolsRequest())
   tools = result.root.tools
   ```

2. Updated `test_list_resources_returns_empty_list` similarly

3. Fixed `test_run_server_graceful_shutdown` mock context manager:
   ```python
   async def mock_context(self) -> tuple:  # Added 'self' parameter
       return (mock_read, mock_write)
   ```

**Tests Fixed**:
- `TestToolRegistry::test_list_tools_returns_empty_list`
- `TestResourceRegistry::test_list_resources_returns_empty_list`
- `TestServerLifecycle::test_run_server_graceful_shutdown`

---

### Fix 3: Graph Orchestration Test (1 failure)

**Files Changed**:
- [src/launch/orchestrator/graph.py:176](../../../src/launch/orchestrator/graph.py#L176)

**Problem**:
Test was expecting "FIXING" state in history but graph went directly from VALIDATING to PR_OPENED:
```
AssertionError: assert 'FIXING' in ['CLONED_INPUTS', 'INGESTED', 'FACTS_READY', ..., 'VALIDATING', 'PR_OPENED', 'DONE']
```

**Root Cause**:
The `validate_node()` stub was unconditionally clearing the issues list:
```python
state["issues"] = []  # No issues for now
```

This prevented the test from simulating validation failures that should trigger the fix loop.

**Solution**:
Changed `validate_node()` to preserve existing issues instead of clearing them:
```python
# Stub: preserve existing issues for testing
# In real implementation, this would run actual validation gates
if "issues" not in state:
    state["issues"] = []
```

**Tests Fixed**:
- `test_graph_execution_with_fix_loop`

---

### Fix 4: Telemetry API Tests (2 failures)

**Files Changed**:
- [tests/unit/telemetry_api/test_tc_522_batch_upload.py](../../../tests/unit/telemetry_api/test_tc_522_batch_upload.py)

**Problem**:
Tests were expecting HTTP 400 status code but getting 422:
```
assert 422 == 400
```

Then after fixing status code, tests failed with:
```
AttributeError: 'list' object has no attribute 'lower'
```

**Root Cause**:
1. FastAPI uses 422 (Unprocessable Entity) for Pydantic validation errors, not 400 (Bad Request)
2. FastAPI validation errors return detail as a list of error objects, not a string

**Solution**:
1. Updated expected status code from 400 to 422
2. Updated error message assertions to handle list format:
   ```python
   assert response.status_code == 422  # FastAPI validation error
   detail = response.json()["detail"]
   assert isinstance(detail, list)
   assert len(detail) > 0
   assert "at least 1" in detail[0]["msg"]
   ```

**Tests Fixed**:
- `TestBatchUpload::test_batch_upload_empty_batch`
- `TestBatchUploadTransactional::test_batch_transactional_empty_batch`

---

## Final Results

**After all fixes**:
- **Gates**: ✅ 21/21 passing
- **Tests**: ✅ 1426 passed, 1 skipped, 0 failed

**Verification**:
```bash
export PYTHONHASHSEED=0
.venv/Scripts/python.exe tools/validate_swarm_ready.py  # ✅ All 21 gates pass
.venv/Scripts/python.exe -m pytest -v --tb=no            # ✅ 1426 passed, 1 skipped
```

**Summary**:
All 9 test failures were fixed across 4 categories:
- 3 LLM provider client tests (import issue)
- 3 MCP server tests (API version mismatch)
- 1 graph orchestration test (stub clearing state)
- 2 telemetry API tests (expected error format)

No new test failures introduced. All gates remain passing.
