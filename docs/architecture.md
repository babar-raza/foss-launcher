# Architecture Overview (Engineer Onboarding)

This document summarizes the system architecture described in `specs/`.
It is **non-binding**; the binding contract is the `specs/` folder.

## High-level goal
Given a public GitHub repository for a product, the system produces a validated patch bundle and opens a PR against the Hugo-based site repo (default: aspose.org), creating/updating content across the relevant sections (products/docs/reference/kb/blog).

## Core components

### Orchestrator
- Owns the end-to-end state machine.
- Spawns worker tasks according to `specs/state-graph.md` and `specs/21_worker_contracts.md`.
- Enforces determinism (`specs/10_determinism_and_caching.md`) and the write fence (`run_config.allowed_paths`).
- Emits events and snapshots (`specs/11_state_and_events.md`).
- Never commits directly in production; uses the Commit Service (`specs/17_github_commit_service.md`).

### Workers
Workers are deterministic, contract-driven steps. Common worker categories:
- **Repo ingestion + profiling**: clone/fetch, inventory, normalize structures.
- **Facts + evidence**: extract claims with anchors, build evidence map.
- **Snippet curation**: identify examples, reduce duplication, tag for retrieval.
- **Page planning**: decide which pages to create/update across site sections.
- **Patch engine**: generate patch bundle operations only (no direct repo writes outside allowed_paths).
- **Validation gates**: run schema checks, link checks, Hugo build, content lint, policy checks.

### Local Telemetry
All operations are logged via Local Telemetry (`specs/16_local_telemetry_api.md`).
If the telemetry service is temporarily unavailable, payloads must be buffered to `RUN_DIR/telemetry_outbox.jsonl` and retried.

### Commit Service
Central service that applies a patch bundle and opens PRs. It enforces allowed_paths and emits auditable metadata.

## Artifact model (RUN_DIR)
Each run writes a deterministic set of artifacts under `RUN_DIR` (`specs/29_project_repo_structure.md`):
- `artifacts/*.json` (schemas in `specs/schemas/`)
- `events.ndjson`, `snapshot.json`
- reports and diffs

A run is considered successful only when all required artifacts exist, validate, and all gates pass.

## Control flow
1. Load and validate `run_config.yaml`
2. Create RUN_DIR + initial events
3. Ingest + profile repo(s)
4. Extract facts and evidence
5. Curate examples/snippets
6. Plan pages and generate patch bundle
7. Run validation gates
8. If gates fail: deterministic fix-loop (single issue at a time)
9. On pass: Commit Service commit + open PR
10. Associate commit SHA with telemetry

## Determinism requirements
- Temperature defaults to 0.0
- Stable ordering for outputs
- Pin inputs (refs, ruleset versions)
- Fix loops are capped and single-issue

## Where the scaffold stops
The Python code under `src/launch/**` only provides a minimal foundation:
- schema validation
- RUN_DIR scaffolding
- a validator that marks the unimplemented gates as NOT_IMPLEMENTED (no false positives)

The full orchestrator and worker implementation is driven by the LLM taskcards in `plans/`.
