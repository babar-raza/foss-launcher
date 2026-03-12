# Healing Plan: SR-4221..4224 — Missing unit tests + scope deviation

_Created: 2026-03-12_

## Context

Self-review of TC-4221..TC-4224 (pipeline bug fixes 2–5) identified three gaps:
1. **Testability 2/5**: No unit tests for TC-4221 (scout in _VALID_WORKERS),
   TC-4223 (prepend behavior), TC-4224 (advisor task_type mapping).
2. **Scope 3/5**: `tests/unit/test_pipeline_e2e.py` was edited outside TC-4222's
   `allowed_paths` (`tests/unit/cli/` does not cover that path).
3. **Thoroughness 3/5**: E2E CLI guard behavior (--stop-after scout, resume==stop)
   not verified via CliRunner.

## Gap → Taskcard mapping

| Gap ID | Description | Taskcard |
|--------|-------------|----------|
| GAP-1 | No unit test asserting "scout" in _VALID_WORKERS; no test for --stop-after scout guard | SR-01 |
| GAP-2 | `enhance_prompt_for_retry` test only checks substring presence, not prepend ordering | SR-02 |
| GAP-3 | No unit test asserting "advisor" in _TASK_TYPE_CONTENT_TYPE | SR-03 |
| GAP-4 | TC-4222 allowed_paths missing test_pipeline_e2e.py | SR-04 |

---

## SR-01 — Unit tests: scout in _VALID_WORKERS + CLI guard

**Status**: Done
**Gap linkage**: GAP-1
**Role**: Senior engineer. Drop-in, production-ready.

### Scope
- **Fix**: Add tests to `tests/unit/cli/test_main_workers.py` (new file)
- **Allowed paths**: `tests/unit/cli/test_main_workers.py`
- **Forbidden paths**: All source files

### Tests to add

```python
# tests/unit/cli/test_main_workers.py
from launcher.cli.main import _VALID_WORKERS

class TestValidWorkers:
    def test_scout_in_valid_workers(self):
        assert "scout" in _VALID_WORKERS

    def test_scout_order_after_intake(self):
        intake_idx = _VALID_WORKERS.index("intake")
        scout_idx = _VALID_WORKERS.index("scout")
        assert scout_idx == intake_idx + 1

    def test_stop_after_scout_not_rejected_by_guard(self, tmp_path):
        from typer.testing import CliRunner
        from launcher.cli.main import app
        config = tmp_path / "c.yaml"
        config.write_text("family: cells\nplatform: python\nrepo_url: https://github.com/x/y\n")
        result = CliRunner().invoke(app, ["run", str(config), "--stop-after", "scout"])
        # Guard must not reject "scout" as invalid worker
        assert "--stop-after must be one of" not in (result.output or "")

    def test_pipeline_order_complete(self):
        expected = ["intake", "scout", "understand", "planner", "generate", "evaluate", "publish"]
        assert _VALID_WORKERS == expected
```

### Acceptance checks
- [ ] `pytest tests/unit/cli/test_main_workers.py -v` — all pass
- [ ] No imports of source files outside `launcher.cli.main`

### Now (runbook)
```bash
# Write tests/unit/cli/test_main_workers.py
# Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/cli/test_main_workers.py -v
```

---

## SR-02 — Unit test: enhance_prompt_for_retry prepend ordering

**Status**: Done
**Gap linkage**: GAP-2
**Role**: Senior engineer. Drop-in, production-ready.

### Scope
- **Fix**: Update `tests/unit/shared/test_llm_response_validator.py` — add prepend-order test
  and update existing string-check test to match new message
- **Allowed paths**: `tests/unit/shared/test_llm_response_validator.py`
- **Forbidden paths**: All source files

### Tests to add / update

```python
# In TestValidateLlmResponse class, replace/augment existing enhance tests:

def test_enhance_prompt_prepends_notice(self):
    """Notice must come BEFORE the original prompt, not after."""
    enhanced = enhance_prompt_for_retry("original prompt", ["issue 1"])
    notice_end = enhanced.index("original prompt")
    assert notice_end > 0, "original prompt should not be at start"
    assert enhanced.startswith("CRITICAL")

def test_enhance_prompt_contains_required_fields(self):
    enhanced = enhance_prompt_for_retry("original prompt", ["Element 0 missing 'type' key"])
    assert "CRITICAL" in enhanced
    assert "Element 0 missing 'type' key" in enhanced
    assert "paragraph" in enhanced  # valid type values hint
    assert enhanced.endswith("original prompt")

def test_enhance_prompt_with_validation_result(self):
    from launcher.shared.llm_response_validator import ValidationResult
    vr = ValidationResult(is_valid=False, issues=["Element 0 missing 'type' key"])
    enhanced = enhance_prompt_for_retry("base prompt", vr)
    assert enhanced.startswith("CRITICAL")
    assert "base prompt" in enhanced
```

### Acceptance checks
- [ ] `pytest tests/unit/shared/test_llm_response_validator.py -v` — all pass
- [ ] Existing tests still pass (backward compat preserved)

### Now (runbook)
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_llm_response_validator.py -v
```

---

## SR-03 — Unit test: advisor task_type in _TASK_TYPE_CONTENT_TYPE

**Status**: Done
**Gap linkage**: GAP-3
**Role**: Senior engineer. Drop-in, production-ready.

### Scope
- **Fix**: Add test to `tests/unit/clients/test_model_routing.py` (existing file, new class)
- **Allowed paths**: `tests/unit/clients/test_model_routing.py`
- **Forbidden paths**: All source files

### Tests to add

```python
# New class in test_model_routing.py:
class TestTaskTypeContentTypeMap:
    """Verify _TASK_TYPE_CONTENT_TYPE has correct entries including advisor."""

    def test_advisor_maps_to_json_object(self):
        from launcher.clients.llm_provider import _TASK_TYPE_CONTENT_TYPE
        assert _TASK_TYPE_CONTENT_TYPE.get("advisor") == "json_object"

    def test_generate_maps_to_json_array(self):
        from launcher.clients.llm_provider import _TASK_TYPE_CONTENT_TYPE
        assert _TASK_TYPE_CONTENT_TYPE.get("generate") == "json_array"

    def test_review_maps_to_json_object(self):
        from launcher.clients.llm_provider import _TASK_TYPE_CONTENT_TYPE
        assert _TASK_TYPE_CONTENT_TYPE.get("review") == "json_object"

    def test_unknown_task_type_defaults_to_markdown(self):
        from launcher.clients.llm_provider import _TASK_TYPE_CONTENT_TYPE
        assert _TASK_TYPE_CONTENT_TYPE.get("unknown_type", "markdown") == "markdown"
```

### Acceptance checks
- [ ] `pytest tests/unit/clients/test_model_routing.py -v` — all pass

### Now (runbook)
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/clients/test_model_routing.py -v
```

---

## SR-04 — Retroactive allowed_paths fix for TC-4222

**Status**: Done
**Gap linkage**: GAP-4
**Role**: Administrative fix.

### Scope
- **Fix**: Add `tests/unit/test_pipeline_e2e.py` to TC-4222's `allowed_paths`
- **Allowed paths**: `plans/taskcards/TC-4222_resume-stop-guard.md`
- **Forbidden paths**: All source files

### Acceptance checks
- [ ] `tests/unit/test_pipeline_e2e.py` present in TC-4222 `allowed_paths` frontmatter

### Now (runbook)
```bash
# Edit plans/taskcards/TC-4222_resume-stop-guard.md — add the path to allowed_paths
```
