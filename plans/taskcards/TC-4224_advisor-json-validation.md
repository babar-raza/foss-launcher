---
id: TC-4224
title: "Fix advisor: add task_type=advisor, increase max_tokens, promote error logging"
status: Done
priority: Medium
owner: "orchestrator"
updated: "2026-03-12"
tags: [advisor, pipeline, llm, logging]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4224_advisor-json-validation.md
  - src/launcher/clients/llm_provider.py
  - src/launcher/orchestrator/pipeline_advisor.py
  - tests/unit/clients/
  - tests/unit/orchestrator/
evidence_required:
  - reports/agents/B/TC-4224/evidence.md
---

# Taskcard TC-4224 — Fix advisor: add task_type=advisor, increase max_tokens, promote error logging

## Objective

The pipeline advisor LLM call has three independent bugs that together make
advisor output unreliable and failures invisible:

**Bug A — wrong content-type validation**: The advisor call omits `task_type`,
so `llm_provider.py` defaults to markdown validation. Markdown validation
accepts any non-empty string, meaning garbage responses (partial JSON, empty
object, raw prose) pass L1 validation silently and propagate downstream as
structured advisor decisions.

**Bug B — max_tokens truncation**: `max_tokens=1024` is passed to the advisor
LLM call. An advisor response that includes a full pipeline health assessment,
per-worker recommendations, and a JSON envelope easily exceeds 1024 tokens.
Truncated JSON is unparseable; the advisor silently returns a degraded
(or empty) decision, causing the pipeline to proceed without valid guidance.

**Bug C — invisible failures**: When the advisor call raises an exception,
the catch block logs at `WARNING` level. WARNING is typically filtered out in
production log aggregation, meaning advisor failures go completely unnoticed.
Operators have no visibility into how often the advisor is failing or why.

Fix:
- Add `"advisor": "json_object"` to `_TASK_TYPE_CONTENT_TYPE` in
  `llm_provider.py` so advisor responses are validated as JSON objects.
- Pass `task_type="advisor"` and `max_tokens=2048` in the advisor LLM call
  in `pipeline_advisor.py`.
- Change `logger.warning(...)` to `logger.error(..., exc_info=True)` in the
  advisor exception handler.

## Required spec references

- `src/launcher/clients/llm_provider.py` — `_TASK_TYPE_CONTENT_TYPE` mapping
- `src/launcher/orchestrator/pipeline_advisor.py` — advisor LLM call site
- `specs/system_overview.md` — pipeline advisor role and contract

## Scope

### In scope

- Add `"advisor": "json_object"` entry to `_TASK_TYPE_CONTENT_TYPE` in
  `llm_provider.py`
- In `pipeline_advisor.py`: add `task_type="advisor"` to the LLM call kwargs
- In `pipeline_advisor.py`: change `max_tokens=1024` to `max_tokens=2048`
- In `pipeline_advisor.py`: change `logger.warning` to `logger.error` with
  `exc_info=True` in the advisor exception handler
- Add unit tests for all three changes

### Out of scope

- Changes to the advisor prompt text
- Changes to the advisor's downstream decision logic (how it uses the LLM
  response)
- Changes to other task_type entries in `_TASK_TYPE_CONTENT_TYPE`
- Changes to the global default `max_tokens` used by non-advisor calls

## Inputs

- `src/launcher/clients/llm_provider.py` (current, missing "advisor" entry)
- `src/launcher/orchestrator/pipeline_advisor.py` (current, wrong task_type,
  low max_tokens, wrong log level)
- Existing tests in `tests/unit/clients/` and `tests/unit/orchestrator/`

## Outputs

- `src/launcher/clients/llm_provider.py` with `"advisor": "json_object"`
  added to `_TASK_TYPE_CONTENT_TYPE`
- `src/launcher/orchestrator/pipeline_advisor.py` with `task_type="advisor"`,
  `max_tokens=2048`, and `logger.error(..., exc_info=True)` in exception handler
- Unit tests for all three changes

## Allowed paths

- plans/taskcards/TC-4224_advisor-json-validation.md
- src/launcher/clients/llm_provider.py
- src/launcher/orchestrator/pipeline_advisor.py
- tests/unit/clients/
- tests/unit/orchestrator/

### Allowed paths rationale

Bug A is in `llm_provider.py`; Bugs B and C are in `pipeline_advisor.py`.
Both source files are in separate packages, so both must be listed. Tests go in
the corresponding test directories. No schema, config, or other worker file
requires a change.

## Implementation steps

### Step 1: Add "advisor" to `_TASK_TYPE_CONTENT_TYPE`

Open `src/launcher/clients/llm_provider.py`. Locate `_TASK_TYPE_CONTENT_TYPE`
(a dict mapping task_type strings to content-type strings or validator
identifiers). Add:

```python
"advisor": "json_object",
```

Place it alphabetically or adjacent to other `"json_object"` entries for
readability. Confirm the key string `"advisor"` exactly matches what
`pipeline_advisor.py` will pass as `task_type` (see Step 2).

### Step 2: Fix the advisor LLM call in `pipeline_advisor.py`

Open `src/launcher/orchestrator/pipeline_advisor.py`. Locate the call to the
LLM client (likely `self._llm.complete(...)` or `await
client.chat_complete(...)`). Apply three changes:

**Change 1 — task_type**:
```python
# Before (no task_type, or task_type missing)
response = await client.complete(prompt=advisor_prompt, max_tokens=1024)

# After
response = await client.complete(
    prompt=advisor_prompt,
    task_type="advisor",
    max_tokens=2048,
)
```

**Change 2 — max_tokens**: Already shown above; change `1024` → `2048`.

**Change 3 — exception handler log level**:
```python
# Before
except Exception as exc:
    logger.warning("Advisor LLM call failed: %s", exc)
    return _default_advisor_decision()

# After
except Exception as exc:
    logger.error("Advisor LLM call failed", exc_info=True)
    return _default_advisor_decision()
```

The `exc_info=True` keyword causes Python's logging framework to attach the
full traceback to the error log record, enabling post-hoc diagnosis from log
files without needing to reproduce the failure.

### Step 3: Verify JSON parsing is not broken by the new content-type

Confirm that the code path that receives the advisor LLM response already
calls `json.loads()` or a pydantic model parse on the result. If it does,
the new `"json_object"` content-type validation now catches malformed responses
before they reach `json.loads`, producing a clear L1 failure instead of a
`json.JSONDecodeError` deep in the call stack.

If the advisor response is currently consumed as a raw string without JSON
parsing, add `json.loads(response.content)` before the downstream usage — but
only if this is already structurally implied by the advisor contract (do not
add new logic beyond the three fixes listed in Scope).

### Step 4: Add unit tests

In `tests/unit/clients/` (extend or create `test_llm_provider.py`):

```python
def test_advisor_task_type_maps_to_json_object():
    from launcher.clients.llm_provider import _TASK_TYPE_CONTENT_TYPE
    assert _TASK_TYPE_CONTENT_TYPE.get("advisor") == "json_object"
```

In `tests/unit/orchestrator/` (extend or create
`test_pipeline_advisor.py`):

```python
def test_advisor_call_uses_correct_task_type(mock_llm_client):
    """Verify task_type='advisor' and max_tokens=2048 are passed to the LLM."""
    # Patch the LLM client, invoke the advisor, inspect the captured call kwargs.
    assert mock_llm_client.last_call_kwargs["task_type"] == "advisor"
    assert mock_llm_client.last_call_kwargs["max_tokens"] == 2048

def test_advisor_exception_logs_at_error_level(caplog):
    """Verify that LLM exceptions are logged at ERROR, not WARNING."""
    with caplog.at_level(logging.ERROR):
        # Force the LLM client to raise; run the advisor.
        ...
    assert any(r.levelname == "ERROR" for r in caplog.records)
    assert any("Advisor LLM call failed" in r.message for r in caplog.records)
```

### Step 5: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/clients/ tests/unit/orchestrator/ -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x -q 2>&1 | tail -10
```

## Failure modes

### Failure mode 1: `task_type="advisor"` key does not match `_TASK_TYPE_CONTENT_TYPE` key exactly

**Symptom**: The advisor call still falls through to the default content-type
(markdown) because the key lookup misses due to a typo or case difference.
**Detection**: Unit test `test_advisor_task_type_maps_to_json_object` catches
this; also `test_advisor_call_uses_correct_task_type` catches the call-site
spelling.
**Resolution**: Grep both files for the string `"advisor"` and confirm they are
identical; consider defining a module-level constant `TASK_TYPE_ADVISOR =
"advisor"` shared between the two files.
**Gate**: Unit test on `_TASK_TYPE_CONTENT_TYPE` key lookup.

### Failure mode 2: `max_tokens=2048` is still not enough for some advisor responses

**Symptom**: Occasional truncated JSON persists at 2048 tokens; the advisor
produces invalid decisions.
**Detection**: Monitor advisor call logs for `finish_reason: length` in the LLM
response metadata.
**Resolution**: Increase further to `max_tokens=4096`, or restructure the
advisor prompt to request a more compact JSON format.
**Gate**: Log monitoring after deployment; not a blocker for this taskcard.

### Failure mode 3: `exc_info=True` exposes sensitive prompt content in logs

**Symptom**: Full stack traces including advisor prompt text (which may contain
confidential repo data) appear in shared log aggregation systems.
**Detection**: Log review; privacy audit.
**Resolution**: If log scrubbing is required, add a custom `LogRecord` filter
that redacts `prompt` fields from ERROR-level records. This is a follow-up
taskcard if needed.
**Gate**: Privacy review (out of scope for this taskcard).

### Failure mode 4: Changing `logger.warning` to `logger.error` triggers an
existing log-level assertion in tests

**Symptom**: A test that asserts `caplog` contains no ERROR-level records
starts failing because the advisor exception path now logs at ERROR.
**Detection**: Pre-existing test failure after the change.
**Resolution**: Update the test to either accept the new log level or mock the
advisor so it does not raise during that test.
**Gate**: Full test suite.

## Task-specific review checklist

1. [ ] `"advisor": "json_object"` added to `_TASK_TYPE_CONTENT_TYPE` in
       `llm_provider.py`
2. [ ] `task_type="advisor"` passed in the advisor LLM call in
       `pipeline_advisor.py`
3. [ ] `max_tokens` in the advisor LLM call changed from `1024` to `2048`
4. [ ] `logger.warning` in the advisor exception handler changed to
       `logger.error` with `exc_info=True`
5. [ ] Unit test confirms `_TASK_TYPE_CONTENT_TYPE["advisor"] == "json_object"`
6. [ ] Unit test confirms `task_type="advisor"` and `max_tokens=2048` are
       passed to the LLM client
7. [ ] Unit test confirms exception is logged at `ERROR` level with traceback
8. [ ] No pre-existing tests broken
9. [ ] Evidence file created at `reports/agents/B/TC-4224/evidence.md`

## Deliverables

1. Updated `src/launcher/clients/llm_provider.py` with `"advisor"` entry in
   `_TASK_TYPE_CONTENT_TYPE`
2. Updated `src/launcher/orchestrator/pipeline_advisor.py` with `task_type`,
   `max_tokens`, and `logger.error` fixes
3. New or updated unit tests in `tests/unit/clients/` and
   `tests/unit/orchestrator/`
4. Evidence at `reports/agents/B/TC-4224/evidence.md`

## Acceptance checks

- [ ] `pytest tests/unit/clients/ -v` — all pass
- [ ] `pytest tests/unit/orchestrator/ -v` — all pass
- [ ] `pytest -x -q` — 0 new failures
- [ ] Code inspection confirms all three changes present in source files
- [ ] Log output during a test-run exception scenario shows `ERROR` level with
      full traceback

## Self-review

### Verification results

- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/agents/B/TC-4224/evidence.md
- [ ] Bug A confirmed fixed: `_TASK_TYPE_CONTENT_TYPE["advisor"] == "json_object"`
- [ ] Bug B confirmed fixed: `max_tokens=2048` in advisor LLM call
- [ ] Bug C confirmed fixed: `logger.error(..., exc_info=True)` in exception
      handler

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/clients/ tests/unit/orchestrator/ -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x -q 2>&1 | tail -10
# Optional live run to confirm advisor produces valid JSON decisions:
.venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-cells-foss-python.yaml \
  --run-id 260311_190711_cells_python_6882 2>&1 | grep -i "advisor"
```

**Expected results**:
- All client and orchestrator unit tests pass
- Full suite: 0 new failures
- Live run (if executed): advisor log lines show valid JSON decisions; any
  exception logs appear at ERROR level with full traceback

## Integration boundary proven

**Upstream**: The pipeline orchestrator invokes `pipeline_advisor.py` after
each worker phase to obtain a structured JSON recommendation (continue /
skip / fail-fast).
**Downstream**: The LLM provider receives `task_type="advisor"` and applies
JSON-object content-type validation to the raw LLM response before returning
it; invalid responses are rejected at L1 rather than propagating as garbage
structured data.
**Contract**:
- `_TASK_TYPE_CONTENT_TYPE` is the single registry of content-type validators
  per task type; the advisor must have an entry there or it silently bypasses
  format validation.
- `max_tokens=2048` is the minimum budget required for a complete advisor JSON
  response; below this threshold responses are routinely truncated.
- `logger.error` with `exc_info=True` is the minimum logging standard for
  failures that affect pipeline correctness; `logger.warning` is reserved for
  recoverable, expected edge cases.
