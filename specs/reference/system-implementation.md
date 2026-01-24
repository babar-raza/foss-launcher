# System Implementation Guide (recommendations)

**Generated**: 2026-01-23  
**Purpose**: Practical, system-level recommendations for implementing the FOSS Launcher described by the binding `specs/`.  
**Relationship to specs**: If anything here conflicts with a binding spec or JSON schema, treat the spec or schema as the source of truth.

## Guiding principles

1. **Contract first**: treat JSON schemas under `specs/schemas/` as executable contracts. Validate at boundaries and fail fast with a structured issue.
2. **Determinism by construction**: avoid hidden randomness, unordered iteration, locale-dependent formatting, and time-based behavior in planning and content generation.
3. **Pure core, imperative edges**: keep business logic (planning, diff generation, validation orchestration) as pure functions over explicit inputs; isolate IO in small adapters.
4. **One run, one sandbox**: every run stays inside `RUN_DIR` with strict write fences driven by `run_config.allowed_paths`.
5. **Evidence or it did not happen**: model "facts", "claims", and "evidence anchors" as first-class entities early so every downstream worker can stay grounded.

## Recommended implementation order (maps to taskcards)

This repo already contains an LLM-ready program of work in `plans/taskcards/`. A low-risk build sequence:

### Phase 0: Foundations (schemas, IO, guardrails)
- Implement the **artifact store**: atomic writes, schema validation, deterministic file ordering.
- Implement **RUN_DIR** helpers: path resolution, allowed path enforcement, hashing, and manifesting.
- Implement **issue model** and error surfaces early (align with `specs/schemas/issue.schema.json` and `specs/01_system_contract.md`).
- Add the virtual environment and lockfile strategy required by `specs/00_environment_policy.md` and `specs/29_project_repo_structure.md`.

Recommended taskcards to anchor this phase:
- `plans/taskcards/TC-100_bootstrap_repo.md`
- `plans/taskcards/TC-200_schemas_and_io.md`
- `plans/taskcards/TC-250_shared_libs_governance.md`

### Phase 1: Orchestrator skeleton (LangGraph, state, resume)
- Build the LangGraph graph to match `specs/state-graph.md` exactly.
- Implement event log + snapshot behavior from `specs/state-management.md`.
- Implement idempotent node execution: node checks for required upstream artifacts and reuses them when unchanged.
- Implement "fix loop" routing and cap with `run_config.max_fix_attempts`.

Recommended taskcards:
- `plans/taskcards/TC-300_orchestrator_langgraph.md`

### Phase 2: Workers W1 to W5 (inputs to drafts)
Implement workers in dependency order, verifying each output artifact by schema and a small unit test suite.

- **W1 RepoScout**: cloning, SHA resolution, repo inventory, site context, frontmatter contract, Hugo facts.
- **W2 FactsBuilder**: ProductFacts + EvidenceMap, with evidence priority rules.
- **W3 SnippetCurator**: snippet catalog, de-duplication, provenance retention.
- **W4 PagePlanner**: PagePlan + section requirements, platform aware layout decisions.
- **W5 DraftWriter**: write drafts to `RUN_DIR/drafts/...` mirroring final site paths.

Recommended taskcards (examples):
- W1: `TC-400_repo_scout_w1.md` and its subcards
- W2: `TC-410_facts_builder_w2.md` and its subcards
- W3: `TC-420_snippet_curator_w3.md` and its subcards
- W4: `TC-430_page_planner_w4.md` and its subcards
- W5: `TC-440_draft_writer_w5.md` and its subcards

### Phase 3: Linking, patching, validating (W6 to W9)
- **W6 LinkerAndPatcher**: convert drafts into patch bundle operations (do not write outside `allowed_paths`).
- **W7 GateRunner**: run profiles of stop-the-line gates; generate `validation_report.json`.
- **W8 Fixer**: single-issue-at-a-time patch strategy, re-run relevant gates, cap attempts.
- **W9 PRManager**: call commit service to open PR and attach evidence summaries.

Recommended taskcards (examples):
- `TC-450_linker_and_patcher_w6.md`
- `TC-460_gate_runner_w7.md`
- `TC-470_fixer_w8.md`
- `TC-480_pr_manager_w9.md`

### Phase 4: MCP surface and operations
- Implement the MCP tool handlers from `specs/14_mcp_endpoints.md` and schemas in `specs/24_mcp_tool_schemas.md`.
- Ensure MCP calls and CLI share the same internal services (no parallel implementations).
- Integrate Local Telemetry API with buffering/outbox behavior (`specs/16_local_telemetry_api.md`).

Recommended taskcards:
- `TC-510_mcp_server.md`, `TC-500_clients_services.md`, `TC-580_observability_and_evidence_bundle.md` (see taskcard index)

### Phase 5: Pilots and regression
- Implement pilot configs and golden outputs as your regression harness.
- Add an explicit "golden run compare" command in CI to catch drift early.

Recommended taskcards:
- `TC-520_pilots_and_regression.md`

## Architecture recommendations

### 1) Service layer boundaries (keep them small and testable)
A structure that tends to stay clean for this kind of system:

- `src/launch/domain/`  
  Pure models and logic: claim IDs, evidence anchors, patch operations, determinism helpers.
- `src/launch/storage/`  
  Artifact store, atomic writes, hashing, schema validation, run directory layout.
- `src/launch/clients/`  
  OpenAI-compatible LLM client wrapper, telemetry client, commit service client, Git client.
- `src/launch/workers/`  
  One package per worker (align with `DECISIONS.md`), each with a `run()` function and a narrow IO contract.
- `src/launch/orchestrator/`  
  LangGraph graph definition and node wiring, resume logic, fix loop routing.
- `src/launch/mcp/`  
  FastAPI app, tool handlers, request and response validation, auth if needed.

This matches the repo's existing direction and reduces "cross-cutting sprawl".

### 2) Determinism checklist (practical)
Implement these early, then add tests to prevent regressions:

- Canonical ordering for file lists, JSON keys, and page inventories.
- Stable ID generation (claim IDs, snippet IDs, patch IDs) based on content hashes, not timestamps.
- Temperature forced to 0.0 for LLM calls; avoid sampling features unless explicitly allowed.
- Normalize line endings, trailing whitespace, and UTF-8 encoding decisions.
- Include `ruleset_version` and `templates_version` in every cache key and output artifact header.
- Record resolved SHAs and file fingerprints in `site_context.json` and `repo_inventory.json`.

### 3) Schema-first validation strategy
- Wrap every "write artifact" with: model validation + JSON schema validation + sha256 recording.
- Keep a single "schema registry" so tools and runtime share the same schema loading and versioning.
- Represent validation failures as `issue.schema.json` objects, not ad-hoc exceptions.

### 4) Patch bundle safety
- Generate patch operations as data (JSON patch bundle), and apply them via a single controlled applier.
- Enforce `allowed_paths` twice: once when generating patches, and again when applying them.
- Make patching idempotent by design: same inputs produce same patch bundle and same final worktree.

### 5) Gates and fix loop engineering
- Gates should be runnable in isolation with deterministic inputs (ideally against `RUN_DIR/work/site/` plus artifacts).
- The Fixer should operate on one issue at a time and leave an explicit paper trail: issue -> patch -> re-validate.
- Cache gate results keyed by input fingerprints to avoid expensive reruns.

## Testing recommendations

### Unit tests
- Artifact store: atomic write and schema validation.
- Deterministic helpers: stable ordering and hashing.
- Each worker: given fixed inputs, output artifacts match golden snapshots.

### Integration tests
- Run a minimal "fake repo" fixture through W1 to W5 and confirm deterministic artifacts.
- Patch application: apply patch bundle to a fixture site repo and confirm diffs.

### E2E tests
- Pilot runs with pinned SHAs and golden artifact comparisons.
- Gate profiles: ensure the full set of required gates run and report in the expected order.

## Operational recommendations

- Emit telemetry for every significant action, including LLM calls, tool invocations, artifact writes, gate runs, and patch applications.
- Create a single "evidence bundle" per run (tar/zip) that includes artifacts, reports, and key logs for external review.
- Treat unresolved items in `OPEN_QUESTIONS.md` as stop-the-line blockers unless the orchestrator explicitly records an approved exception in the master review.

## Common failure modes to proactively prevent
- Silent drift: outputs change without version bumps or golden tests catching it.
- Unbounded fix loops: always cap attempts and always record the reason a loop is continuing.
- Path escapes: always verify patch and write targets are inside `allowed_paths`.
- Evidence gaps: never allow a page draft to introduce new facts without claim markers and EvidenceMap anchors.
