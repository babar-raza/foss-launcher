# TC-2431 Evidence: Callable Validation at Load Time

## Files Modified

- `src/launch/validation_engine/registry_loader.py`
  - Added private function `_validate_callables(gates)` that iterates all gates,
    calls `resolve_callable(gate)`, collects ImportError / AttributeError / non-callable
    errors, and raises `ValueError` listing all failures.
  - Added `validate_callables: bool = False` parameter to `load_registry()`.
  - Activation: `validate_callables=True` OR env var `LAUNCH_VALIDATE_GATE_CALLABLES=1`.
  - Backward compat: no behavior change when both False/unset.

## Tests Added

File: `tests/unit/test_validation_engine.py` (class `TestCallableValidation`)

| Test | Description |
|------|-------------|
| `test_callable_validation_passes_all_28_gates` | Sets env var, loads registry, asserts no error |
| `test_callable_validation_via_param_passes` | Uses `validate_callables=True`, no env var |
| `test_callable_validation_catches_bad_module` | Injects gate with non-existent module |
| `test_callable_validation_catches_non_callable_attr` | Injects gate pointing to `_REGISTRY_PATH` (Path object, not callable) |
| `test_callable_validation_catches_missing_attr` | Injects gate with non-existent callable_name |
| `test_callable_validation_disabled_by_default` | No env var, bad gate — no error raised |
| `test_callable_validation_env_var_takes_precedence` | Env var=1 with `validate_callables=False` still raises |
| `test_callable_validation_collects_multiple_errors` | Two bad gates — both appear in single ValueError |

**Tests added: 8**

## pytest Result Summary

```
52 passed, 3 skipped in 17.54s (3 skipped = LAUNCH_TEST_PILOT_RUN_DIR not set)
```

All 35 tests in `tests/unit/test_validation_engine.py` pass.
