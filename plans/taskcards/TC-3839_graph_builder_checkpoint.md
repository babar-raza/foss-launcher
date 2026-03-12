---
id: TC-3839
title: "Graph Builder Worker Checkpoint Integration (H2.1)"
status: Done
priority: High
owner: "agent"
updated: "2026-03-08"
tags: [heal, checkpoint, orchestrator, pipeline]
depends_on: [TC-3832]
allowed_paths:
  - plans/taskcards/TC-3839_graph_builder_checkpoint.md
  - src/launcher/orchestrator/graph_builder.py
  - tests/unit/orchestrator/test_graph_builder.py
evidence_required:
  - reports/TC-3839/evidence.md
---

# Taskcard TC-3839 — Graph Builder Worker Checkpoint Integration (H2.1)

## Objective

Integrate `write_worker_checkpoint()` (TC-3832) into `graph_builder.py`'s
`_make_worker_node()` post-success block so that every completed worker
produces a `WorkerCheckpoint` with SHA-256 artifact hash that the heal CLI
can reference for rollback.

## Required spec references

- `specs/heal.md` (heal session checkpoint contract)

## Scope

### In scope
- In `_make_worker_node()`, after `ctx.store.write_json(f"{worker_name}_checkpoint.json", ...)`,
  call `write_worker_checkpoint(run_dir, worker_name, run_id, artifact_path, content_hash)`
- Emit `artifact_path` and `content_hash` on the existing `checkpoint_written` event
- Import `write_worker_checkpoint` and `WorkerCheckpoint` from `launcher.resilience.checkpoint`

### Out of scope
- Heal loop itself — TC-3851
- run_loop.py resume path — TC-3840
- heal_metadata pass-through — TC-3841

## Inputs

- `src/launcher/orchestrator/graph_builder.py` (524 lines, existing checkpoint block at line 281)
- `src/launcher/resilience/checkpoint.py` (WorkerCheckpoint + write_worker_checkpoint from TC-3832)

## Outputs

- `graph_builder.py` with worker checkpoint write in post-success block
- `checkpoint_written` event enriched with `artifact_path` and `content_hash`

## Allowed paths

- plans/taskcards/TC-3839_graph_builder_checkpoint.md
- src/launcher/orchestrator/graph_builder.py
- tests/unit/orchestrator/test_graph_builder.py

### Allowed paths rationale

Only `graph_builder.py` needs modification. The test file captures the checkpoint event enrichment.

## Implementation steps

### Step 1: Add import

In `graph_builder.py`, add at the top (near other launcher imports):
```python
from launcher.resilience.checkpoint import write_worker_checkpoint
```

### Step 2: Augment post-success checkpoint block

Current block (lines ~282-291):
```python
if entry.checkpoint:
    ctx.store.write_json(
        f"{worker_name}_checkpoint.json",
        output_dict,
    )
    ctx.emit_event(
        "checkpoint_written",
        {"worker": worker_name},
        worker=worker_name,
    )
```

Replace with:
```python
if entry.checkpoint:
    artifact_file = f"{worker_name}_checkpoint.json"
    ctx.store.write_json(artifact_file, output_dict)
    artifact_path = run_dir / artifact_file
    try:
        wcp = write_worker_checkpoint(
            run_dir=run_dir,
            worker=worker_name,
            run_id=state["run_id"],
            artifact_path=artifact_path,
        )
        content_hash = wcp.content_hash
        checkpoint_id = wcp.checkpoint_id
    except Exception:
        content_hash = ""
        checkpoint_id = ""
        logger.warning("[%s] Worker checkpoint write failed for %s", state["run_id"], worker_name)
    ctx.emit_event(
        "checkpoint_written",
        {
            "worker": worker_name,
            "artifact_path": str(artifact_path),
            "content_hash": content_hash,
            "checkpoint_id": checkpoint_id,
        },
        worker=worker_name,
    )
```

### Step 3: Add/update tests

In `tests/unit/orchestrator/test_graph_builder.py`, find or add a test that verifies:
- `checkpoint_written` event contains `artifact_path`, `content_hash`, `checkpoint_id`
- A `worker_checkpoints/` subdirectory is created under the run directory

## Failure modes

### Failure mode 1: `write_worker_checkpoint` raises on missing artifact

**Detection**: `write_worker_checkpoint` tries to read the artifact for SHA-256 hashing;
if `write_json` failed previously, the file is absent.
**Resolution**: Wrapped in `try/except Exception` with `logger.warning`; checkpoint_written
event still emits but with empty hash/id. Pipeline continues.
**Gate**: Unit test for write failure path

### Failure mode 2: Circular import between graph_builder and resilience

**Detection**: `ImportError` at `from launcher.resilience.checkpoint import write_worker_checkpoint`
**Resolution**: No circular dependency exists — graph_builder depends on models, io, and now resilience.
Verify by running `python -c "from launcher.orchestrator.graph_builder import build_pipeline"`
**Gate**: Import smoke test

### Failure mode 3: Content hash mismatch on resume

**Detection**: Heal rollback uses hash from WorkerCheckpoint; if artifact was edited manually,
hash differs.
**Resolution**: This is correct behavior — heal CLI warns on mismatch. No code change needed here.
**Gate**: Integration test (TC-3852)

## Task-specific review checklist

1. [ ] `write_worker_checkpoint()` called after `ctx.store.write_json()` in post-success block
2. [ ] `checkpoint_written` event includes `artifact_path`, `content_hash`, `checkpoint_id`
3. [ ] Failure in `write_worker_checkpoint()` does NOT crash the pipeline node
4. [ ] Import added at module level, not inside the async closure
5. [ ] `worker_checkpoints/` dir created by `write_worker_checkpoint()` (from TC-3832 impl)
6. [ ] All existing graph_builder tests still pass

## Deliverables

1. `src/launcher/orchestrator/graph_builder.py` — enriched checkpoint block
2. `tests/unit/orchestrator/test_graph_builder.py` — checkpoint event enrichment test

## Acceptance checks

1. [ ] `pytest tests/unit/orchestrator/test_graph_builder.py -v` — 0 failures
2. [ ] `checkpoint_written` event dict has keys `artifact_path`, `content_hash`, `checkpoint_id`
3. [ ] `pytest tests/ -x -q` — 0 failures

## Self-review

### Verification results
- [x] Tests: 3/3 PASS (targeted) + 2395/2395 PASS (full suite)
- [x] Validation: checkpoint_written event verified to carry artifact_path, content_hash, checkpoint_id
- [x] Evidence file: `reports/TC-3839/evidence.md`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/test_graph_builder.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Expected results**:
- All graph_builder tests pass
- Full suite: 0 failures

## Integration boundary proven

**Upstream**: Worker run() completes successfully; output_dict serialized
**Downstream**: Heal CLI reads WorkerCheckpoint from `worker_checkpoints/` dir
**Contract**: `checkpoint_written` event carries `content_hash` (SHA-256 hex) and `checkpoint_id` for heal rollback
