# TC-2444 Self-Review — Agent E: limitations_renderer.py

**Date**: 2026-02-23
**Agent**: Agent_E

---

## Checklist

### Correctness
- [x] `parse_limitations_json()` returns `None` on empty/None input (not exception)
- [x] Fence stripping handles both `json and plain ` ``` ` variants via regex
- [x] `find("[")` + `rfind("]")` approach finds outermost array even with leading prose
- [x] `JSONDecodeError` caught — returns `None`, caller uses freeform fallback
- [x] `title < 3 chars` or `description < 10 chars` → item filtered; all items filtered → `None`
- [x] Empty workaround string `""` → converted to `None` via `str(w).strip() or None`
- [x] `render_limitations_to_markdown([], name)` returns honest "No verified limitations" message
- [x] `render_limitations_to_markdown(items, name)` is pure (no I/O, no LLM) — deterministic

### Mode Isolation
- [x] `_STRUCTURED_MODE` set at module import time — existing pilots unaffected (env var absent)
- [x] `is_structured_mode()` strictly checks `== "json"` — typos default to freeform
- [x] Module imported by `content_generators.py` at load time (not lazily) — correct behavior

### Tests
- [x] 29 tests, 0 failures — covers all public functions + feature flag behavior
- [x] Determinism tested: `render_limitations_to_markdown` called twice → equal outputs
- [x] `TestFeatureFlagEnvVar`: monkeypatch + sanitizer integration tests

---

## Known Limitations

1. `_STRUCTURED_MODE` is read at module import time. Tests that need to change the mode
   must patch `m._STRUCTURED_MODE` directly (not env var), since `importlib.reload()` would
   re-execute other imports. This is documented in `TestFeatureFlagEnvVar`.

2. `parse_limitations_json` finds outermost `[` and `]` — if LLM wraps array in an outer
   object `{"limitations": [...]}`, the inner `[` is found correctly but only if the outer
   object doesn't itself have `[` before it. In practice this works for common LLM outputs.
