# State, Events, and Checkpoints

Canonical schemas: `specs/schemas/event_schemas/*.schema.json`

## Overview

The pipeline uses an event-sourced model for observability and a checkpoint
system for resumability. Every significant action emits an event. Every worker
boundary writes a checkpoint. Together they enable Rule 2 (reviewable) and
Rule 3 (resume from any stage).

---

## Event Types

Events are appended to `events.ndjson` (newline-delimited JSON). Each event is
validated against its schema in `specs/schemas/event_schemas/`.

| Event type | Emitted when | Key fields |
|------------|-------------|------------|
| `run_created` | Pipeline run starts | `run_id`, `config` (family, platform, repo_url) |
| `worker_started` | Worker begins execution | `run_id`, `worker` |
| `worker_completed` | Worker finishes | `run_id`, `worker`, `duration_ms`, `verdict` |
| `checkpoint_written` | Checkpoint artifact saved | `run_id`, `worker`, `artifact_path`, `content_hash` |
| `llm_call_completed` | LLM call returns | `call_id`, `model`, `usage`, `duration_ms` |
| `gate_executed` | Quality gate runs | `gate_id`, `passed`, `issues`, `severity` |
| `re_run_triggered` | Evaluate triggers re-run | `source_worker`, `target_worker`, `reason` |

### Common Event Fields

All events share:
- **type** (string): Event type identifier (matches schema `const`).
- **run_id** (string): UUID of the pipeline run.
- **timestamp** (string, ISO-8601): When the event was emitted.

### Event File

- Path: `{run_dir}/{run_id}/events.ndjson`
- Format: One JSON object per line, append-only.
- Encoding: UTF-8.
- Events are never deleted or modified after writing.

---

## Checkpoint Format

Checkpoints are JSON files written after each worker completes. They contain the
worker's validated output artifact.

### Checkpoint Structure

```
{run_dir}/{run_id}/checkpoints/
  intake.json            # IntakeBundle
  understand.json        # UnderstandingBundle
  generate.json          # ContentManifest
  evaluate.json          # EvaluationReport
  publish.json           # PublishBundle
```

### Checkpoint Properties

- **Format**: JSON, validated against the worker's `output_schema`.
- **Content hash**: SHA-256 of the serialized JSON, recorded in the
  `checkpoint_written` event.
- **Atomic write**: Checkpoints are written to a temp file and renamed to
  prevent partial writes.
- **Schema version**: The pipeline version is embedded in the checkpoint for
  migration detection.

### Checkpoint Validation

- On write: The checkpoint is validated against the worker's output schema.
  Invalid output = hard stop (no silent corruption).
- On read (resume): The checkpoint is re-validated. If the schema version
  mismatches, the pipeline emits a warning and requires explicit `--force` to
  proceed.
- On read (manual edit): The content hash is compared. If it differs from the
  `checkpoint_written` event, the pipeline logs a `manual_edit_detected` event
  and proceeds with the edited content.

---

## Resume-From Workflow

The pipeline supports resuming from any checkpoint (Rule 3).

### Command

```
launch run --resume-from {worker} --run-id {run_id}
```

### Resume Behavior

1. **Load checkpoint**: Read `{worker}.json` from the checkpoints directory.
2. **Validate**: Re-validate against the worker's output schema.
3. **Detect edits**: Compare content hash with the last `checkpoint_written`
   event. Log if edited.
4. **Skip upstream**: All workers before `{worker}` are skipped.
5. **Execute downstream**: Workers after `{worker}` run normally, using the
   loaded checkpoint as input.

### Resume Targets

| Resume from | Skips | Runs |
|-------------|-------|------|
| `intake` | nothing | intake, understand, generate, evaluate, publish |
| `understand` | intake | understand, generate, evaluate, publish |
| `generate` | intake, understand | generate, evaluate, publish |
| `evaluate` | intake, understand, generate | evaluate, publish |
| `publish` | intake, understand, generate, evaluate | publish |

---

## Manual Override (Rule 3)

Humans can edit checkpoint files directly to fix issues without re-running
upstream workers.

### Override Workflow

1. Inspect the checkpoint (e.g., `understand.json`) and identify the issue.
2. Edit the JSON file directly (e.g., fix a claim, adjust a page title).
3. Resume: `launch run --resume-from generate --run-id {run_id}`.
4. The pipeline detects the hash mismatch, logs it, and proceeds.

### Constraints

- Edited checkpoints must still pass schema validation.
- The pipeline will not silently accept invalid JSON.
- Manual edits are logged as events for audit trail.

---

## Re-Run Flow

When the Evaluate worker produces a `NO_GO` verdict, it can trigger a re-run of
upstream workers (Rule 6).

### Re-Run Mechanics

1. Evaluate produces a `root_cause_diagnosis` identifying the responsible worker.
2. If the responsible worker is in `re_run_targets` (configured in
   `pipeline.yaml`), a `re_run_triggered` event is emitted.
3. The pipeline re-executes from the target worker with tighter constraints
   derived from the diagnosis.
4. `max_re_runs` (default 2) caps the re-run count to prevent infinite loops.
5. If max re-runs is exhausted and verdict is still `NO_GO`, the pipeline halts
   with `NEEDS_HUMAN_REVIEW`.

### Re-Run vs. Resume

| Aspect | Re-run | Resume |
|--------|--------|--------|
| Trigger | Automatic (Evaluate) | Manual (human) |
| Direction | Backward (to upstream worker) | Forward (from checkpoint) |
| Input | Diagnosis constraints | Checkpoint artifact |
| Capped | Yes (max_re_runs) | No |

---

## Extended Spec (v2 Detail Addendum)

### Pipeline State Schema (LangGraph TypedDict)

```python
from typing import TypedDict, Optional, Literal

class PipelineState(TypedDict):
    # Identity
    run_id: str
    # Worker I/O (set by producing worker, read by the next)
    run_config: RunConfig
    intake_bundle: Optional[IntakeBundle]
    understanding_bundle: Optional[UnderstandingBundle]
    content_bundle: Optional[ContentBundle]
    evaluation_report: Optional[EvaluationReport]
    publish_bundle: Optional[PublishBundle]
    # Re-run control (set by Evaluate on NO-GO)
    re_run_count: int          # starts at 0
    re_run_diagnosis: Optional[list[RootCauseDiagnosis]]
    re_run_target: Optional[Literal["understand", "generate"]]
    # Terminal state
    verdict: Optional[Literal["GO", "NO-GO", "NEEDS_HUMAN_REVIEW"]]
    error: Optional[str]
```

**Key invariants**:
- `re_run_count` is incremented before `re_run_target` is set.
- On re-run, `content_bundle` and `evaluation_report` are cleared to `None` before the re-run.
- `re_run_target` must be `None` when `verdict == "GO"`.

### Routing Functions

```python
def route_after_evaluate(state: PipelineState) -> str:
    if state["verdict"] == "GO":
        return "publish"
    if state["re_run_count"] >= 2:
        return "needs_human_review"
    target = state.get("re_run_target")
    if target not in ("understand", "generate"):
        return "needs_human_review"
    return target

def route_after_understand(state: PipelineState) -> str:
    return "generate"  # re-run Understand always feeds Generate next
```

### Checkpoint Protocol (Extended)

Every worker writes a checkpoint after successful self-review:

1. Serialize output to JSON (deterministic: `sort_keys=True`, `PYTHONHASHSEED=0`).
2. Validate against output schema (`io/schema_validation.py`).
3. Write atomically via `io/atomic.py`.
4. Emit `checkpoint_written` event to `events.ndjson`.
5. Update `snapshot.json` with new worker state.

**Manual override (Rule 3)**: A human can edit any checkpoint artifact and resume. On resume, the artifact is re-validated against its schema. If valid → continue. If invalid → hard stop with `SCHEMA_VALIDATION_FAILED`.

**Checksum detection**: `snapshot.json` records SHA-256 of each artifact. On resume, if SHA-256 has changed → the artifact was manually edited → log INFO "Manual override detected at {artifact_name}".

### Schema Version Policy

Every checkpoint artifact includes a top-level `schema_version` field:

```json
{"schema_version": "1.0.0", "generated_at": "2026-03-08T14:22:00Z", ...payload...}
```

**Version semantics** (`MAJOR.MINOR.PATCH`):
- **PATCH**: Additive optional fields only → proceed silently.
- **MINOR**: Non-breaking structural changes → emit WARNING log, proceed.
- **MAJOR**: Breaking changes → HALT with `SCHEMA_VERSION_MISMATCH`.

**Migration**: `launch migrate --artifact <name> --run-id <id>` (Phase 5). Auto-migration is prohibited. Initial version: `"1.0.0"` for all v2 artifacts.

### Event Log Extended Details

Append-only NDJSON file. Every event is schema-validated against `specs/schemas/event_schemas/{event_type}.schema.json`.

| Event Type | When Emitted |
|-----------|-------------|
| `run_created` | Before first worker starts |
| `worker_started` | At the start of each worker |
| `worker_completed` | After worker writes checkpoint |
| `checkpoint_written` | After atomic write + schema validation |
| `llm_call_completed` | After every LLM API call |
| `gate_executed` | After each gate check in Evaluate |
| `re_run_triggered` | When Evaluate routes back to Understand/Generate |

**Chain hash**: Each event includes a `prev_hash` field (SHA-256 of the previous event's JSON). Allows tamper detection. Chain starts with `prev_hash: "0" * 64`.

**Re-run correlation**: Re-run events include `"re_run_of": "<original_run_id>"` for cross-run log analysis.

### Resume Protocol (Extended)

`launch run --resume-from <worker> --run-id <id>`:

1. Load `snapshot.json` for the run.
2. Verify all checkpoint artifacts up to `resume_from` are schema-valid.
3. Replay events up to the resume point (read-only; no re-emit).
4. Re-initialize `PipelineState` from checkpoints.
5. Start pipeline from the `resume_from` worker.

`re_run_count` is NOT reset on manual resume (it tracks auto re-runs; manual resumes use a separate `manual_resume_count` field).
