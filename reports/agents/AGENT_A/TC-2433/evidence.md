# TC-2433 Evidence: Legacy Engine DeprecationWarning

## Files Modified

- `src/launch/workers/w9_validator/worker.py`
  - Added `import warnings` to stdlib imports (line 32).
  - Added `warnings.warn(...)` call inside the `if _engine == "legacy":` branch,
    BEFORE the `_execute_validator_legacy(...)` call.
  - Warning message: `"LAUNCH_VALIDATION_ENGINE=legacy is deprecated. ..."`
  - Category: `DeprecationWarning`, `stacklevel=2`.

- `tests/unit/workers/w9/test_validator.py`
  - Added `test_legacy_engine_emits_deprecation_warning(monkeypatch, tmp_path)`
  - Sets `LAUNCH_VALIDATION_ENGINE=legacy`, calls `execute_validator()`,
    captures warnings with `warnings.catch_warnings`, asserts a matching
    `DeprecationWarning` was emitted.

## Tests Added

| Test | Description |
|------|-------------|
| `test_legacy_engine_emits_deprecation_warning` | Verifies DeprecationWarning with correct message is emitted |

**Tests added: 1**

## pytest Result Summary

```
1 passed in 1.14s
```

Full suite (52 passed, 3 skipped) also passes with this change included.
