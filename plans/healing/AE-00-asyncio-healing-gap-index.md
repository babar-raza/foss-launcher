# Asyncio Event-Loop Healing — Gap Index

**Source**: Self-review of asyncio event loop fix (2026-03-07)
**Context**: Converted 34 `asyncio.get_event_loop().run_until_complete()` calls to `async def` + `await` in test_evaluate.py (28) and test_publish.py (6). Added `asyncio_mode = "auto"` to pyproject.toml. All 1692 tests pass. This healing sprint addresses gaps and risks identified in the self-review.

## Gap Table

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|----------|----------|
| G-AE-01 | `asyncio_mode = "auto"` is a footgun — any `async def` in test files is auto-detected as a test coroutine, which can cause false positives for async helpers. Should use `"strict"` + explicit `@pytest.mark.asyncio` decorators, matching existing pattern in test_generate/test_intake/test_understand. | Medium | AE-01 |
| G-AE-02 | No regression guard prevents reintroduction of `asyncio.get_event_loop().run_until_complete()` in test files. | Low | AE-02 |
| G-AE-03 | No comment in pyproject.toml explaining the `asyncio_mode` setting; future maintainers won't know why it's there. | Low | AE-01 |
| G-AE-04 | Diff was not reviewed by user — transformation was done via script without showing before/after. Need explicit verification of all 34 converted sites. | Medium | AE-03 |
