# Investigation: MCP Entrypoint Test UnicodeDecodeError

## Executive Summary

**Test**: `test_launch_mcp_console_script_help` in `tests/unit/test_tc_530_entrypoints.py`
**Status**: Pre-existing failure
**Root Cause**: Windows encoding mismatch (cp1252 vs UTF-8)
**Impact**: Single test failure, no functional impact on MCP server

## Problem Description

### Error Trace
```
UnicodeDecodeError: 'charmap' codec can't decode byte 0x90 in position 1433: character maps to <undefined>
```

This occurs in:
- **Location**: `tests/unit/test_tc_530_entrypoints.py:162`
- **Context**: `output = result.stdout + result.stderr`
- **Secondary Error**: `TypeError: unsupported operand type(s) for +: 'NoneType' and 'str'`

### Root Cause Analysis

1. **UTF-8 Box-Drawing Characters**
   The MCP server's help output (via Rich/Typer) uses Unicode box-drawing characters:
   - `─` (U+2500): Horizontal line - UTF-8 bytes: `e2 94 80`
   - `└` (U+2514): Bottom-left corner - UTF-8 bytes: `e2 94 90`
   - `│` (U+2502): Vertical line - UTF-8 bytes: `e2 94 82`

2. **Windows Default Encoding**
   ```python
   Default encoding: utf-8
   stdout encoding: cp1252  # ← Problem here
   ```

   When `subprocess.run(text=True)` is called on Windows without explicit encoding:
   - Python uses `sys.stdout.encoding` (cp1252)
   - Byte `0x90` (part of UTF-8 sequence `e2 94 90`) is **undefined** in cp1252
   - Decoder crashes in subprocess reader thread

3. **Cascading Failure**
   - Reader thread crashes → `result.stdout` is set to `None`
   - Line 162 tries `result.stdout + result.stderr` → TypeError
   - Test reports TypeError instead of the actual UnicodeDecodeError

### Evidence

**Hex dump at position 1433:**
```
  94  80  e2  94  80  e2  94  80  e2  94  80  e2  94  90  0d  0a
 224 200 342 224 200 342 224 200 342 224 200 342 224 220  \r  \n
      ─           ─           ─           ─           └
```

**Verification:**
```bash
# Binary mode: Works (1762 bytes captured)
$ python -c "subprocess.run(['launch_mcp.exe', '--help'], capture_output=True)"

# UTF-8 with error handling: Works
$ python -c "subprocess.run(['launch_mcp.exe', '--help'], text=True, encoding='utf-8', errors='replace')"

# Default encoding (cp1252): Fails
$ python -c "subprocess.run(['launch_mcp.exe', '--help'], text=True)"  # ← UnicodeDecodeError
```

## Impact Assessment

### Affected Tests
- ✅ `test_launch_run_console_script_help` - **PASSES** (no box-drawing chars in output)
- ✅ `test_launch_validate_console_script_help` - **PASSES** (no box-drawing chars in output)
- ❌ `test_launch_mcp_console_script_help` - **FAILS** (has box-drawing chars from Rich formatting)

### Why Only MCP Test Fails
The MCP server uses Rich/Typer formatting that includes box-drawing characters in help text, while the other CLI tools (launch_run, launch_validate) have simpler help output without Unicode decorations.

## Solution

### Option 1: Explicit UTF-8 Encoding (Recommended)
```python
result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    encoding='utf-8',      # ← Add this
    errors='replace',       # ← Add this (graceful degradation)
    timeout=10,
    env=env,
)
```

**Pros:**
- Handles all Unicode correctly
- Consistent behavior across platforms
- Graceful degradation with `errors='replace'`

**Cons:**
- None

### Option 2: Binary Mode + Manual Decode
```python
result = subprocess.run(
    cmd,
    capture_output=True,
    text=False,             # ← Binary mode
    timeout=10,
    env=env,
)
output = result.stdout.decode('utf-8', errors='replace') + result.stderr.decode('utf-8', errors='replace')
```

**Pros:**
- Explicit control over decoding

**Cons:**
- More verbose
- Requires None checks

### Option 3: Suppress Box-Drawing (Not Recommended)
Disable Rich formatting in MCP server help output.

**Pros:**
- Avoids Unicode issues

**Cons:**
- Reduces UX quality
- Doesn't fix underlying encoding issue

## Recommended Fix

Apply **Option 1** to all three console script tests for consistency:

### File: `tests/unit/test_tc_530_entrypoints.py`

**Changes Required:**
1. Line 84-90 (`test_launch_run_console_script_help`)
2. Line 120-126 (`test_launch_validate_console_script_help`)
3. Line 154-160 (`test_launch_mcp_console_script_help`)

Add `encoding='utf-8'` and `errors='replace'` to each `subprocess.run()` call.

### Patch Preview

```python
result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    encoding='utf-8',      # NEW
    errors='replace',       # NEW
    timeout=10,
    env=env,
)
```

## Testing Strategy

### Pre-Fix Verification
```bash
# Should fail with UnicodeDecodeError
pytest tests/unit/test_tc_530_entrypoints.py::test_launch_mcp_console_script_help -v
```

### Post-Fix Verification
```bash
# Should pass (all 9 tests)
pytest tests/unit/test_tc_530_entrypoints.py -v

# Verify on Windows specifically
pytest tests/unit/test_tc_530_entrypoints.py -v --tb=short
```

### Regression Tests
```bash
# All entrypoint tests should still pass
pytest tests/unit/test_tc_530_entrypoints.py -v

# All unit tests should still pass
pytest tests/unit/ -x
```

## Related Issues

### Similar Patterns in Codebase
Searched for other `subprocess.run(text=True)` calls that might have the same issue:
- ✅ All other subprocess calls in test suite use explicit encoding or don't capture text

### Windows-Specific Encoding Issues
This is a known Windows Python issue when:
- Default terminal encoding is cp1252
- Application outputs UTF-8
- No explicit encoding specified in subprocess

### Best Practice
**Always specify encoding explicitly** when calling `subprocess.run()` with `text=True`:
```python
subprocess.run(..., text=True, encoding='utf-8', errors='replace')
```

## Timeline

- **2026-02-12**: Investigation completed
- **Status**: Ready for fix implementation
- **Estimated Fix Time**: 5 minutes (3-line change)
- **Risk Level**: Low (test-only change, no functional code affected)

## Conclusion

This is a **test infrastructure issue**, not a functional bug. The MCP server works correctly; the test just needs to handle UTF-8 encoding explicitly on Windows. The fix is straightforward and should be applied to all three console script tests for consistency and cross-platform compatibility.
