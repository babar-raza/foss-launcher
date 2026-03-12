# LS-00 — LangGraph Streaming (TC-4064) Post-Implementation Gap Index

## Context

TC-4064 implemented LangGraph streaming always-on for the foss-launcher v2 pipeline.
The post-implementation self-review identified four categories of gaps ranging from a
critical silent-failure regression to minor observability improvements. This index maps
each gap to an executable healing taskcard.

## Gap Table

| Gap ID | Severity | Description | Taskcard |
|--------|----------|-------------|----------|
| LS-G1 | **Critical** | `consume()` returns `{}` silently when graph errors/never emits `LangGraph` chain_end — previously `ainvoke` would raise | LS-01 |
| LS-G2 | Significant | `_safe_stream_event` duplicated verbatim in `generate/worker.py` and `evaluate/worker.py` — third worker will copy again with no canonical home | LS-02 |
| LS-G3 | Significant | Change 4 from approved plan silently dropped: `state.py` `stream_events` field and `graph_builder.py` advisor enrichment never implemented | LS-03 |
| LS-G4 | Minor | `page_generated` event word count uses pre-render IR block estimate, diverging from `GeneratedPage.word_count`; `StreamEventHandler` not exported from `orchestrator/__init__.py`; no `(N/total)` progress counter | LS-04 |

## Priority order

1. LS-01 (critical — silent data-loss regression)
2. LS-02 (significant — maintainability debt that grows with each new worker)
3. LS-03 (significant — approved plan contract violation)
4. LS-04 (minor — observability polish, no correctness impact)

## Status summary

| Taskcard | Status |
|----------|--------|
| LS-01 | Done |
| LS-02 | Done |
| LS-03 | Done |
| LS-04 | Done |
