# System Contract

This document defines the error code registry, severity levels, and
compliance requirements for foss-launcher v2. Every component in the
system must conform to these contracts.

## Error Code Registry

Error codes follow the pattern `CATEGORY_DESCRIPTION`. Each code maps to
a Python exception class in `src/launcher/util/errors.py`.

### Configuration Errors

| Code               | Severity | Description                                  |
|--------------------|----------|----------------------------------------------|
| CONFIG_INVALID     | critical | RunConfig fails schema validation            |
| CONFIG_MISSING     | critical | Required config file not found                |
| CONFIG_FIELD_MISSING | critical | Required field absent from run config       |
| CONFIG_FAMILY_UNKNOWN | high  | Family key not found in `families.yaml`      |
| CONFIG_PLATFORM_UNKNOWN | high | Platform key not found in `families.yaml`  |

### Schema Errors

| Code               | Severity | Description                                  |
|--------------------|----------|----------------------------------------------|
| SCHEMA_MISMATCH    | critical | Worker output fails output_schema validation |
| SCHEMA_INPUT_INVALID | critical | Worker input fails input_schema validation |
| SCHEMA_NOT_FOUND   | critical | Referenced schema file missing from registry |
| SCHEMA_VERSION_MISMATCH | high | Artifact schema version differs from expected |

### LLM Errors

| Code               | Severity | Description                                  |
|--------------------|----------|----------------------------------------------|
| LLM_FAILURE        | high     | Primary + fallback both failed               |
| LLM_TIMEOUT        | high     | LLM call exceeded timeout threshold          |
| LLM_PARSE_ERROR    | medium   | LLM response failed structured output parse  |
| LLM_CIRCUIT_OPEN   | high     | Circuit breaker tripped, endpoint unavailable |
| LLM_FALLBACK_USED  | low      | Primary failed, fallback succeeded           |

### Gate Errors

| Code               | Severity | Description                                  |
|--------------------|----------|----------------------------------------------|
| GATE_CRITICAL      | critical | Safety-critical gate failed (XSS, data leak) |
| GATE_FAILED        | high     | Mandatory quality gate failed                |
| GATE_SKIPPED       | medium   | Gate skipped due to dependency failure       |
| GATE_ERROR         | high     | Gate implementation raised an exception      |

### Checkpoint Errors

| Code               | Severity | Description                                  |
|--------------------|----------|----------------------------------------------|
| CHECKPOINT_CORRUPT | critical | Checkpoint file fails schema validation on read |
| CHECKPOINT_MISSING | high     | Expected checkpoint not found for resume     |
| CHECKPOINT_STALE   | medium   | Checkpoint from different engine version     |

### Pipeline Errors

| Code               | Severity | Description                                  |
|--------------------|----------|----------------------------------------------|
| PIPELINE_TOPOLOGY_INVALID | critical | pipeline.yaml fails schema validation |
| WORKER_NOT_FOUND   | critical | Worker named in pipeline.yaml has no implementation |
| SELF_REVIEW_FAILED | high     | Worker self-review returned passed=false     |
| RERUN_LIMIT        | high     | Maximum re-run iterations exhausted          |
| VERDICT_NOGO       | high     | Evaluate returned NO-GO after all re-runs    |

## Severity Levels

| Level    | Behavior                                                    |
|----------|-------------------------------------------------------------|
| critical | Hard stop. Pipeline halts immediately. No downstream work.  |
| high     | Blocks current worker. May trigger re-run or fallback.      |
| medium   | Logged and reported. Does not block pipeline progress.      |
| low      | Informational. Recorded in event log for diagnostics.       |

Critical errors are never recoverable by the pipeline. They require human
intervention (config fix, schema fix, or infrastructure fix).

## Compliance Requirements

### Schema Validation at Every Boundary

Seven enforcement points, all mandatory:

1. **Worker-to-worker**: Output validated against `output_schema` before
   checkpoint write. Input validated against `input_schema` on read.
   Mismatch = hard stop (SCHEMA_MISMATCH).

2. **LLM calls**: Every call uses structured request/response envelopes
   validated against `llm_request.schema.json` and `llm_response.schema.json`.

3. **Gate results**: Every gate returns a `GateResult` validated against
   `gate_result.schema.json`.

4. **Events**: Every event validated against its type-specific schema in
   `specs/schemas/event_schemas/`.

5. **Self-review**: Every worker self-review produces a `SelfReviewResult`
   validated against `self_review_result.schema.json`.

6. **Checkpoints**: Validated on write AND on read (including after manual
   edits per Rule 3).

7. **Run config**: Validated against `run_config.schema.json` before
   pipeline starts. Invalid config = hard stop.

### Determinism

- `PYTHONHASHSEED=0` required for all runs and tests.
- LLM temperature fixed at 0.0.
- Deterministic slug generation and permalink resolution.
- Reproducible ordering of claims, pages, and gate execution.

### Provenance

- Every artifact includes a provenance header (run_id, worker, timestamp,
  engine_version, input_hash).
- Event log (`events.ndjson`) records every worker start/complete, LLM
  call, gate execution, checkpoint write, and re-run trigger.

### Idempotency

- Re-running a worker with identical inputs must produce identical outputs
  (given deterministic LLM responses).
- Checkpoint resume must not duplicate work already completed.

## Schema Registry

All schemas live in `specs/schemas/` and are versioned. The full registry:

```
specs/schemas/
  run_config.schema.json
  pipeline.schema.json
  intake_bundle.schema.json
  intake_config.schema.json
  understanding_bundle.schema.json
  content_manifest.schema.json
  evaluation_report.schema.json
  publish_bundle.schema.json
  page_ir.schema.json
  gate_result.schema.json
  self_review_result.schema.json
  llm_request.schema.json
  llm_response.schema.json
  ruleset.schema.json
  event_schemas/
    run_created.schema.json
    worker_started.schema.json
    worker_completed.schema.json
    checkpoint_written.schema.json
    llm_call_completed.schema.json
    gate_executed.schema.json
    re_run_triggered.schema.json
```
