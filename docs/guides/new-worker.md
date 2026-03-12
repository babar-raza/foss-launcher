# New Worker Implementation Guide

Use this guide when implementing a new pipeline worker. It covers `WorkerContract`,
`WorkerContext`, required events, Pydantic model conventions, the 5-step registration
sequence, and the integration test pattern.

For the orchestrator and run_loop entry point, see `specs/state_events_checkpoints.md`
and `agents.md` Section 2. For schema authorship, see `docs/guides/schema-authorship.md`.

---

## 1. Design Principles Before Writing Code

### Stateless requirement

A worker is stateless: all state is read from `context.store` (the artifact store)
and written back to it. Workers must not hold mutable state in instance variables
across calls to `run()`. This makes them safely resumable.

### The sandwich model (Rule 5)

Every LLM call inside a worker follows:

```
Engineering pre-LLM  →  LLM call  →  Engineering post-LLM
(validate, prepare,      (single,      (validate response,
 build prompt)           focused)       handle rejection,
                                        fallback)
```

- **Pre-LLM**: validate inputs, build a focused prompt, check budget
- **LLM call**: exactly one concern per call; no multi-step reasoning in a single call
- **Post-LLM**: validate response against schema; if invalid → fallback or raise

Workers that call LLM N times have N sandwiches. Never chain LLM calls without
a validation layer between them.

### One job per LLM call

Decompose multi-step work into sequential single-concern calls. If a call
requires the LLM to "first extract, then classify, then plan", split it into
three calls with validation between each.

---

## 2. WorkerContract in Depth

`src/launcher/orchestrator/worker_contract.py`

```python
class WorkerContract(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def run(self, input_data: dict, context: WorkerContext) -> dict: ...

    @abstractmethod
    def self_review(self, output: dict, context: WorkerContext) -> SelfReviewResult: ...
```

### `name` property

Must exactly match the key in `configs/pipeline.yaml`. The orchestrator looks
up workers by name. A mismatch causes `WORKER_NOT_FOUND` at startup.

### `run()` contract

- **Input**: `input_data` is the previous worker's validated output (a plain dict,
  already schema-validated by the orchestrator before calling your worker).
- **Output**: must be a plain dict that is schema-valid against your worker's
  `output_schema` in `pipeline.yaml`.
- **No side effects outside `context.store`**: do not write to arbitrary paths.
  Use `context.store.write_json(name, data)` to write artifacts.
- **Exceptions**: raise `LauncherError` subtypes (from `src/launcher/util/errors.py`)
  for structured failures. Never swallow exceptions silently (AG-012).

### `self_review()` contract

Called by the orchestrator after `run()` succeeds. Returns a `SelfReviewResult`.

```python
from launcher.models.state import SelfReviewResult

def self_review(self, output: dict, context: WorkerContext) -> SelfReviewResult:
    issues = []
    if len(output.get("sections", [])) < 3:
        issues.append("fewer than 3 sections generated")
    return SelfReviewResult(
        passed=len(issues) == 0,
        issues=issues,
    )
```

When `passed=False`, the orchestrator routes to the evaluate worker's diagnosis
step, which may trigger a re-run. This is the mechanism that enforces
the sandwich model at the pipeline level.

### create_worker() convention

Every worker module exposes a top-level factory function (not a class import):

```python
# src/launcher/workers/myworker/worker.py

def create_worker() -> WorkerContract:
    return _MyWorker()
```

The orchestrator calls `create_worker()` on startup. This pattern allows
dependency injection in tests without importing the concrete class.

---

## 3. WorkerContext Property Guide

`WorkerContext` is injected by the orchestrator. Do not construct it yourself.

| Property | Type | Always present? | Notes |
|----------|------|----------------|-------|
| `run_id` | `str` | Yes | Stable for the entire run |
| `run_dir` | `Path` | Yes | Base path for all run artifacts |
| `config` | `RunConfig` | Yes | Full parsed run config |
| `llm_config` | `LLMConfig` | Yes | Endpoint, model, temperature, key |
| `store` | `ArtifactStore` | Yes | Read/write artifacts; emit events |
| `log` | `StructuredLogger` | Yes | Scoped to this worker + run_id |
| `repo_dir` | `Path` | Yes | Cloned repo root (set by intake) |
| `repo_content` | `dict[str, str]` | After understand | File path → content; set by understand worker |
| `heal_metadata` | `dict | None` | Only in heal passes | `tighter_constraints` from heal_decision |
| `telemetry` | `TelemetryClient` | Yes | Emit metrics (optional to use) |

### Using context.store

```python
# Write an artifact
context.store.write_json("my_artifact", {"key": "value"})

# Read an artifact written by a previous worker
prev = context.store.read_json("understanding_bundle")

# Emit an event
context.store.emit_event({
    "type": "my_worker_step_completed",
    "run_id": context.run_id,
    "worker": self.name,
    "step": "extract",
    "count": 42,
    "timestamp": "...",
})
```

### Using context.log

```python
context.log.info("Processing section", section="Installation", page_role="howto_article")
context.log.warning("LLM returned empty body", page="aspose-cells/install", attempt=1)
context.log.error("Schema validation failed", schema="content_manifest", error=str(e))
```

Always include structured key-value fields. Do not use f-strings in log messages —
put variables in fields so they are queryable in telemetry.

---

## 4. Required Events

The orchestrator emits `worker_started` and `worker_completed` automatically
**before** and **after** calling your worker's `run()`. You do not emit these.

Workers must emit their own domain events for significant steps:

```python
# In your run() method:
context.store.emit_event({
    "type": "my_worker_step_done",  # snake_case, unique name
    "run_id": context.run_id,
    "worker": self.name,
    "timestamp": datetime.utcnow().isoformat() + "Z",
    # domain-specific fields:
    "pages_processed": 12,
    "llm_calls_made": 48,
})
```

### When to emit events

Emit an event for each logically distinct phase within your worker's `run()`.
Events are the primary observability signal — ops-debug workflow depends on them.

For workers that call LLM, emit after each LLM call phase (this is required by
AG-010). The orchestrator emits `llm_call_completed` events from the LLM client
automatically; you do not need to emit these manually.

### Event schema

Create `specs/schemas/event_schemas/<your_event_type>.schema.json` for any new
event you emit. See `docs/guides/schema-authorship.md §6` for the required structure.

---

## 5. Input/Output Pydantic Model Conventions

For worker-internal data structures (not crossing worker boundaries), use Pydantic:

```python
from launcher.models.base import LauncherBaseModel
from pydantic import Field

class MySectionPlan(LauncherBaseModel):
    slug: str = Field(description="URL-safe slug for this section")
    role: str = Field(description="Page role from the ruleset")
    title: str = Field(description="H1 heading for this section")
    claims: list[str] = Field(default_factory=list,
                               description="Claim IDs to include")
```

Rules:
- Always inherit from `LauncherBaseModel` (not `BaseModel` directly)
- Every field must have `Field(description=...)`
- For the corresponding JSON schema in `specs/schemas/`, mirror these fields exactly
- Use `default_factory=list` (not `default=[]`) for mutable defaults

For dicts that cross worker boundaries, validate against the JSON schema
**before** returning from `run()`. The orchestrator also validates, but
self-validation is faster to debug.

---

## 6. The 5-Step Registration Sequence

All steps except step 1 touch protected paths and require an In-Progress taskcard.

### Step 1: worker.py (not protected)

Create `src/launcher/workers/<name>/worker.py` with:
- `class _<Name>Worker(WorkerContract)` (private class)
- `def create_worker() -> WorkerContract` (public factory)
- `__init__.py` in the directory

### Step 2: Register in run_loop.py (protected: `src/launcher/**`)

In `src/launcher/orchestrator/run_loop.py`, add your worker to `_discover_workers()`:

```python
from launcher.workers.myworker.worker import create_worker as create_myworker

def _discover_workers() -> dict[str, WorkerContract]:
    return {
        "understand": create_understand_worker(),
        "generate":   create_generate_worker(),
        "myworker":   create_myworker(),          # <-- add here
        ...
    }
```

### Step 3: Add to pipeline.yaml (protected: `configs/**`)

```yaml
workers:
  myworker:
    input_schema:  specs/schemas/myworker_input.schema.json
    output_schema: specs/schemas/myworker_output.schema.json
    position: 4    # 1-indexed position in the pipeline
```

Also update the `worker_order` list if your pipeline uses explicit ordering.

### Step 4: Create input/output schemas (protected: `specs/schemas/**`)

See `docs/guides/schema-authorship.md` for the full process.
Minimum required: `specs/schemas/<name>_input.schema.json` and
`specs/schemas/<name>_output.schema.json`.

### Step 5: Integration test

See Section 7 below. The integration test must pass before the taskcard is Done.

---

## 7. Integration Test Pattern

```python
# tests/integration/test_myworker_boundary.py

import json
import pytest
from pathlib import Path
from launcher.workers.myworker.worker import create_worker

SCHEMA_INPUT  = "specs/schemas/myworker_input.schema.json"
SCHEMA_OUTPUT = "specs/schemas/myworker_output.schema.json"


@pytest.fixture
def valid_input():
    return json.loads(Path("tests/fixtures/myworker_input.json").read_text())


def test_myworker_output_schema_valid(valid_input, worker_context, mock_llm_provider):
    """Worker output must be schema-valid against myworker_output.schema.json."""
    worker = create_worker()
    result = worker.run(valid_input, worker_context.with_llm(mock_llm_provider))
    validate_schema(result, SCHEMA_OUTPUT)  # from tests/conftest.py


def test_myworker_emits_required_events(valid_input, worker_context, mock_llm_provider):
    """Worker must emit at least one domain event."""
    worker = create_worker()
    worker.run(valid_input, worker_context.with_llm(mock_llm_provider))
    events = worker_context.store.emitted_events
    assert any(e["type"].startswith("myworker_") for e in events)


def test_myworker_checkpoint_written(valid_input, worker_context, mock_llm_provider):
    """Worker must write its checkpoint artifact."""
    worker = create_worker()
    worker.run(valid_input, worker_context.with_llm(mock_llm_provider))
    checkpoint = worker_context.store.read_json("myworker_checkpoint")
    assert checkpoint is not None
    validate_schema(checkpoint, SCHEMA_OUTPUT)


def test_myworker_self_review_passes_on_valid_output(valid_input, worker_context, mock_llm_provider):
    """self_review() must pass on nominal output."""
    worker = create_worker()
    output = worker.run(valid_input, worker_context.with_llm(mock_llm_provider))
    review = worker.self_review(output, worker_context)
    assert review.passed, f"self_review failed: {review.issues}"
```

### What the integration test must assert

- Output is schema-valid (not just "doesn't crash")
- Required domain events were emitted
- Checkpoint artifact exists and is schema-valid
- `self_review()` passes on nominal output
- Fallback is triggered (and valid) when LLM returns garbage

---

## 8. Pre-Done Checklist for New Worker Taskcards

```
[ ] create_worker() factory function present and exported
[ ] WorkerContract: name, run(), self_review() all implemented
[ ] All LLM calls wrapped in pre-LLM → LLM → post-LLM layers
[ ] Worker raises LauncherError subtypes (not bare Exception)
[ ] Domain events emitted for each significant phase
[ ] Event schemas created in specs/schemas/event_schemas/
[ ] Input/output Pydantic models use LauncherBaseModel + Field(description=...)
[ ] Input/output JSON schemas in specs/schemas/ — mandatory fields annotated
[ ] Registered in run_loop.py _discover_workers()
[ ] Registered in pipeline.yaml with input_schema + output_schema
[ ] Integration test: schema validity, events, checkpoint, self_review
[ ] PYTHONHASHSEED=0 tests pass: .venv/Scripts/python.exe -m pytest tests/ -x
[ ] docs/guides/new-worker.md updated if WorkerContract or WorkerContext changed
[ ] python scripts/check_doc_freshness.py --since HEAD~N exits 0
```
