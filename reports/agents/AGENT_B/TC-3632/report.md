# TC-3632 Report: Snapshot ARTIFACT_WRITTEN Reducer Normalization

**Agent**: agent_b | **Date**: 2026-03-02 | **Status**: Done

## Summary

Hardened the `apply_event_reducer()` ARTIFACT_WRITTEN branch in `snapshot_manager.py` to normalize heterogeneous payload key names from workers W4, W5, W8, W9, and W11. Previously, only events using the canonical `"name"` key (W1, W2, W3) were indexed; events from other workers were silently dropped.

## Changes Made

### `src/launch/state/snapshot_manager.py`
- Added `import logging` and module-level `logger`
- Added `_resolve_artifact_name()` — resolves artifact name from 4 key variants
- Added `_resolve_artifact_path()` — resolves path from 2 key variants
- Added `_resolve_writer_worker()` — resolves writer_worker from 2 key variants
- Replaced ARTIFACT_WRITTEN reducer block to use helpers + warning on unresolvable names

### `tests/unit/state/test_snapshot_artifacts_index.py` (new)
28 tests across 8 classes:
- `TestPattern1SpecCompliant` (1 test)
- `TestPattern2ArtifactKey` (4 tests)
- `TestPattern3W9` (2 tests)
- `TestPattern4W11` (1 test)
- `TestEdgeCases` (5 tests)
- `TestResolveArtifactName` (7 tests)
- `TestResolveArtifactPath` (4 tests)
- `TestResolveWriterWorker` (4 tests)

## Test Commands and Output

```
$ .venv/Scripts/python.exe -m pytest tests/unit/state/test_snapshot_artifacts_index.py -v
28 passed in 1.21s

$ .venv/Scripts/python.exe -m pytest tests/ --tb=line --no-header
8072 passed, 13 skipped, 3 xfailed, 0 failed in 153.20s
```

## Proof Document

`reports/ops/gap_p2_snapshot_artifacts.md` — contains full evidence of the 4 payload patterns with file/line citations, design decision, and GO/NO-GO assessment.

## GO/NO-GO

**GO** — All 4 payload variants indexed correctly. 28 new tests pass. 0 regressions.
