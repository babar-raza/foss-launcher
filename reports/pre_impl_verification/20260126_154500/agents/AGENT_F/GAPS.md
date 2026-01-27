# AGENT_F: Feature & Testability Gaps

**Generated:** 2026-01-26
**Agent:** AGENT_F (Feature & Testability Validator)

---

## Gap Summary

- **Total gaps:** 27
- **BLOCKER:** 3
- **MAJOR:** 18
- **MINOR:** 6

---

## Gap Format

`GAP-ID | SEVERITY | Description | Evidence | Proposed Fix`

---

## BLOCKER Gaps (Stop-the-Line)

### F-GAP-009 | BLOCKER | Batch execution feature missing despite "hundreds of products" requirement
**Evidence:** specs/00_overview.md:13-17 requires "queue many runs" with "bounded concurrency" but no feature/taskcard implements this.

**Why Blocker:** Scale requirement (specs/00_overview.md:12 "non-negotiable") is unimplementable without batch orchestration. Single-run architecture cannot scale to hundreds of products.

**Proposed Fix:**
1. Create spec: `specs/35_batch_execution.md` defining:
   - Queue model (in-memory vs persistent)
   - Concurrency limits (default: max 5 parallel runs)
   - Run prioritization rules
   - Failure handling (retry, skip, halt queue)
2. Create taskcard: `TC-610_batch_orchestrator.md` implementing:
   - Queue manager
   - Worker pool
   - Run lifecycle management (queue → running → done/failed)
3. Add MCP tools:
   - `launch_submit_batch(run_configs[])` → `{batch_id, queued_runs[]}`
   - `launch_get_batch_status(batch_id)` → `{total, running, succeeded, failed}`
4. Add E2E test in TC-523 or new TC-625: submit 10 runs, verify max 5 concurrent

---

### F-GAP-013 | BLOCKER | No LLM nondeterminism fallback strategy
**Evidence:** specs/10_determinism_and_caching.md:5 sets `temperature=0.0` but doesn't address provider-specific nondeterminism (e.g., Ollama vs OpenAI may produce different outputs even at temp=0).

**Why Blocker:** Determinism guarantee (specs/00_overview.md:22 "same inputs -> same plan") may be violated by LLM provider drift. No acceptance criteria for "how much variance is acceptable?"

**Proposed Fix:**
1. Add to specs/10_determinism_and_caching.md:54-60:
   ```markdown
   ## LLM nondeterminism tolerance
   - Worker outputs (ProductFacts, PagePlan, drafts) MUST be semantically equivalent across providers.
   - Acceptable variance: wording changes that preserve meaning (synonym substitution).
   - Unacceptable variance: different claims, different page structure, different code snippets.
   - If semantic drift detected: emit WARNING but do not fail run (determinism test checks *structural* determinism, not exact wording).
   ```
2. Add determinism harness test mode: `--semantic-diff` that compares:
   - Claim IDs (must match)
   - Page output_paths (must match)
   - Snippet IDs (must match)
   - Markdown structure (heading hierarchy must match)
3. Update TC-560:72-84 E2E test to include `--semantic-diff` mode

---

### F-GAP-022 | BLOCKER | Batch execution completion criteria undefined
**Evidence:** specs/00_overview.md:16 mentions "batch execution" but no "done" definition. What is "bounded concurrency"? No max parallel runs specified. No acceptance test for "queue many runs".

**Why Blocker:** Feature requirement exists (non-negotiable per specs/00_overview.md:12) but unverifiable without acceptance criteria.

**Proposed Fix:**
1. Add acceptance criteria to specs/35_batch_execution.md (new spec, see F-GAP-009):
   ```markdown
   ## Acceptance criteria
   - [ ] Queue accepts N run_configs (N >= 100)
   - [ ] Max parallel runs enforced (default: 5, configurable via run_config.batch.max_concurrency)
   - [ ] Run ordering stable (FIFO by submission time)
   - [ ] Batch status API returns accurate counts
   - [ ] E2E test: submit 10 runs, verify completion within timeout (max run time * 10 / max_concurrency)
   ```
2. Add E2E test command to new TC-610:
   ```bash
   python -m launch.batch.manager --submit batch_configs/10_runs.yaml --max-concurrency 3
   # Expected: 10 runs complete, max 3 concurrent at any time, all validation_report.ok=true
   ```

---

## MAJOR Gaps (Require Resolution Before Production)

### F-GAP-001 | MAJOR | Content rollback execution feature missing
**Evidence:** specs/34_strict_compliance_guarantees.md (Guarantee L) requires rollback capability. TC-480:38-41, 54-55, 136 show pr.json includes rollback metadata (base_ref, run_id, rollback_steps, affected_paths) but no documented rollback *execution* feature.

**Proposed Fix:**
1. Add to specs/12_pr_and_release.md:
   ```markdown
   ## Rollback command
   When a launch PR causes site breakage, rollback MUST be automated:
   - Input: commit_sha (from pr.json)
   - Action: revert commit OR create inverse PR
   - Output: rollback confirmation + new PR URL (if inverse PR strategy)
   - Verification: rollback_report.json validates that affected_paths were restored to base_ref state
   ```
2. Add MCP tool: `launch_rollback(pr_commit_sha)` → `{rollback_pr_url, restored_paths[]}`
3. Add taskcard TC-490_rollback_manager.md with E2E test:
   ```bash
   python -m launch.rollback --commit abc123 --strategy inverse_pr
   # Expected: new PR created reverting changes from abc123, validation passes
   ```

---

### F-GAP-002 | MAJOR | Network allowlist validation (Gate N) implementation missing
**Evidence:** specs/09_validation_gates.md:204 and specs/34_strict_compliance_guarantees.md (Guarantee D) reference Gate N but specs/19_toolchain_and_ci.md stops at Gate 9 + TemplateTokenLint. No implementation defined.

**Proposed Fix:**
1. Add to specs/19_toolchain_and_ci.md:172-190:
   ```markdown
   ### Gate N: Network allowlist
   **Binding (Guarantee D):**
   - All network requests (git clone, LLM API, telemetry API, commit service) MUST be to allowlisted endpoints
   - Allowlist source: `config/network_allowlist.yaml` (version-controlled)
   - Enforcement: runtime hook intercepts requests; denies if not in allowlist
   - Gate output: list of attempted requests + allow/deny decisions
   - Failure: BLOCKER if any denied request

   **Command:**
   ```bash
   python -m launch.validators.network_allowlist --run-dir $RUN_DIR --allowlist config/network_allowlist.yaml
   ```
   ```
2. Create `config/network_allowlist.yaml`:
   ```yaml
   allowed_endpoints:
     - github.com
     - api.github.com
     - localhost:8765  # telemetry
     - localhost:8787  # MCP
     - # Ollama/OpenAI endpoints from run_config
   ```
3. Add to TC-570_validation_gates_ext.md as subtask TC-572

---

### F-GAP-003 | MAJOR | Budget enforcement (Gate O) implementation missing
**Evidence:** specs/09_validation_gates.md:205 references Gate O (budget enforcement per Guarantees F/G from specs/34_strict_compliance_guarantees.md) but no implementation defined.

**Proposed Fix:**
1. Add to specs/19_toolchain_and_ci.md:191-210:
   ```markdown
   ### Gate O: Budget enforcement
   **Binding (Guarantees F, G):**
   - run_config MUST define budgets: `max_tokens`, `max_cost_usd`, `max_llm_calls`
   - Telemetry MUST track actual usage vs budgets
   - Gate enforces: if any budget exceeded, BLOCKER
   - Special case: `max_cost_usd` requires provider pricing config (optional; if missing, skip cost check but enforce token/call limits)

   **Command:**
   ```bash
   python -m launch.validators.budget_check --run-dir $RUN_DIR --telemetry-api $TELEMETRY_API_URL
   ```
   ```
2. Add budget schema to specs/schemas/run_config.schema.json:
   ```json
   "budgets": {
     "type": "object",
     "properties": {
       "max_tokens": {"type": "integer", "minimum": 1000},
       "max_cost_usd": {"type": "number", "minimum": 0.01},
       "max_llm_calls": {"type": "integer", "minimum": 1}
     },
     "required": ["max_tokens", "max_llm_calls"]
   }
   ```
3. Add to TC-570 as subtask TC-573

---

### F-GAP-004 | MAJOR | CI parity gate (Gate Q) implementation missing
**Evidence:** specs/09_validation_gates.md:206 references Gate Q (CI parity per Guarantee H from specs/34_strict_compliance_guarantees.md) but no implementation defined.

**Proposed Fix:**
1. Add to specs/19_toolchain_and_ci.md:211-230:
   ```markdown
   ### Gate Q: CI parity
   **Binding (Guarantee H):**
   - CI commands MUST match canonical commands defined in specs/19_toolchain_and_ci.md
   - Gate compares: `.github/workflows/*.yml` commands vs canonical commands
   - Allowed drift: environment variables, paths (must normalize before comparison)
   - Failure: WARNING (not blocker) if drift detected; blocker if critical gates missing in CI

   **Command:**
   ```bash
   python -m launch.validators.ci_parity --ci-dir .github/workflows --canonical-spec specs/19_toolchain_and_ci.md
   ```
   ```
2. Add to TC-570 as subtask TC-574

---

### F-GAP-005 | MAJOR | Untrusted code non-execution gate (Gate R) implementation missing
**Evidence:** specs/09_validation_gates.md:207 references Gate R (untrusted code non-execution per Guarantee J from specs/34_strict_compliance_guarantees.md) but no implementation defined.

**Proposed Fix:**
1. Add to specs/19_toolchain_and_ci.md:231-250:
   ```markdown
   ### Gate R: Untrusted code non-execution
   **Binding (Guarantee J):**
   - Ingested repo code MUST NOT be executed (parse-only)
   - Allowed: syntax validation, AST parsing, static analysis
   - Forbidden: `eval()`, `exec()`, `import` of ingested code, subprocess execution of ingested scripts
   - Gate scans: RepoScout, FactsBuilder, SnippetCurator logs for execution attempts
   - Failure: BLOCKER if any execution detected

   **Command:**
   ```bash
   python -m launch.validators.untrusted_code_check --run-dir $RUN_DIR --logs $RUN_DIR/logs/
   ```
   ```
2. Add runtime hook to W1/W2/W3 workers: any code execution attempt raises `POLICY_UNTRUSTED_CODE_EXECUTION` blocker
3. Add to TC-570 as subtask TC-575

---

### F-GAP-006 | MAJOR | Performance/scalability justification missing
**Evidence:** specs/00_overview.md:13-17 requires "hundreds of products" but no documented performance model, resource budgets, or scalability analysis.

**Proposed Fix:**
1. Create spec: `specs/36_performance_and_scalability.md` defining:
   - Per-run resource estimates: memory (estimate: 2GB avg), CPU (estimate: 2 cores), disk (estimate: 5GB worktrees + artifacts)
   - Batch execution throughput targets: N runs/hour given M parallel workers (target: 20 runs/hour with 5 workers)
   - Telemetry API throughput: X runs/sec (target: 10 concurrent runs)
   - Bottleneck analysis: LLM API latency (critical path), Hugo build time (medium impact), git clone time (low impact)
2. Add performance tests to TC-520:
   - Load test: 50 runs queued, measure throughput
   - Resource monitoring: track memory/CPU/disk usage per run
   - Telemetry stress test: 100 concurrent child run POSTs

---

### F-GAP-007 | MAJOR | Caching strategy undefined
**Evidence:** specs/10_determinism_and_caching.md:30-38 defines cache_key but no cache storage location, invalidation rules, or cache hit telemetry.

**Proposed Fix:**
1. Add to specs/10_determinism_and_caching.md:39-50:
   ```markdown
   ## Cache storage
   - Location: `$CACHE_DIR/<model_id>/<cache_key[:8]>.json`
   - Invalidation: cache entry invalid if `inputs_hash` or `prompt_hash` or `ruleset_version` changes
   - TTL: 30 days (configurable via `run_config.cache_ttl_days`)
   - Hit telemetry: emit `CACHE_HIT` or `CACHE_MISS` event per worker invocation
   - Cache miss handling: recompute and write to cache atomically

   ## What to cache (binding)
   - ProductFacts (W2 output)
   - SnippetCatalog (W3 output)
   - PagePlan (W4 output) - ONLY if deterministic (no LLM calls in planner)
   ```
2. Add cache validator to TC-560: verify cache hit produces identical output as cache miss

---

### F-GAP-010 | MAJOR | Resume from snapshot E2E test scenario missing
**Evidence:** specs/11_state_and_events.md:112-115 requires "resume continues from last stable state" but no E2E test scenario or fixture defined.

**Proposed Fix:**
1. Add to TC-520_pilots_and_regression.md or TC-522_pilot_e2e_cli.md:
   ```markdown
   ## Resume test scenario
   1. Start run: `launch_start_run --config pilot.yaml`
   2. Kill process after FACTS_READY state (simulate crash)
   3. Resume: `launch_resume --run-id <run_id>`
   4. Verify: run completes from FACTS_READY without re-running W1/W2
   5. Assert: no duplicate work, snapshot.json reflects resume, telemetry shows resume event
   ```
2. Create fixture: `specs/pilots/pilot-resume-test/` with pre-populated snapshot.json at FACTS_READY state

---

### F-GAP-011 | MAJOR | Telemetry buffering retry E2E test scenario missing
**Evidence:** specs/16_local_telemetry_api.md:123-135 defines buffering strategy (write to telemetry_outbox.jsonl on failure, retry with exponential backoff) but no E2E test for API outage scenario.

**Proposed Fix:**
1. Add to TC-500_clients_services.md or new TC-505_telemetry_resilience.md:
   ```markdown
   ## Telemetry outage test
   1. Start run with telemetry API disabled (simulate outage)
   2. Run completes, verify telemetry_outbox.jsonl contains all events
   3. Enable telemetry API
   4. Trigger flush: `launch_flush_telemetry_outbox --run-id <run_id>`
   5. Verify: all outbox events POSTed to API, outbox emptied
   6. Assert: no events dropped, retry count logged
   ```
2. Add telemetry mock server to tests/ with configurable failure modes

---

### F-GAP-012 | MAJOR | Conflict detection & resolution E2E test scenario missing
**Evidence:** specs/08_patch_engine.md:31-36 defines conflict behavior ("record Issue with severity=blocker, move to FIXING") but no fixture for "patch cannot apply cleanly".

**Proposed Fix:**
1. Add to TC-450_linker_and_patcher_w6.md:
   ```markdown
   ## Conflict test scenario
   1. Create fixture: site worktree with modified file (manual edit simulating upstream change)
   2. Run patcher with draft targeting same file
   3. Verify: conflict detected, blocker issue `PatchConflict` opened
   4. Verify: run moves to FIXING state
   5. Fixer (W8) updates draft to resolve conflict
   6. Re-run patcher, verify success
   ```
2. Create fixture: `tests/fixtures/patch_conflict/` with pre-modified site file + conflicting draft

---

### F-GAP-014 | MAJOR | Timestamp policy for events undefined
**Evidence:** specs/11_state_and_events.md:52 allows variance in `ts`/`event_id` values but specs/11_state_and_events.md:66 requires ISO8601 with timezone. No enforcement gate defined.

**Proposed Fix:**
1. Add to specs/11_state_and_events.md:66-70:
   ```markdown
   **Timestamp format (binding):**
   - All `ts` fields MUST use ISO8601 with UTC timezone: `YYYY-MM-DDTHH:MM:SS.sssZ`
   - No local timezones allowed (always Z suffix)
   - Precision: milliseconds (3 decimal places)
   - Schema validation: regex pattern `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$`
   ```
2. Add to specs/schemas/event.schema.json:
   ```json
   "ts": {
     "type": "string",
     "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}\\.\\d{3}Z$"
   }
   ```
3. Add validation to Gate 1 (schema validation) in TC-460

---

### F-GAP-015 | MAJOR | Cache invalidation rules undefined
**Evidence:** specs/10_determinism_and_caching.md:31-32 defines cache_key but no versioning strategy for cached artifacts. When does cached output become stale?

**Proposed Fix:**
1. See F-GAP-007 proposed fix (includes invalidation rules)
2. Add cache validator gate to specs/09_validation_gates.md:
   ```markdown
   ### Gate: Cache integrity
   - If cache hit, verify cached artifact still validates against current schema version
   - If schema version mismatch: invalidate cache entry, recompute
   - Emit telemetry: `CACHE_INVALIDATED` with reason (schema_version_mismatch, ttl_expired, inputs_changed)
   ```

---

### F-GAP-020 | MAJOR | MCP server lifecycle undefined
**Evidence:** plans/taskcards/TC-510_mcp_server.md:78-81 shows server start command but no shutdown, restart, or health check beyond /health endpoint.

**Proposed Fix:**
1. Add to specs/14_mcp_endpoints.md:28-35:
   ```markdown
   ## MCP server lifecycle
   - Start: `python -m launch.mcp.server --port 8787`
   - Health: `GET /health` → `{status: "ok", version: "..."}`
   - Shutdown: SIGTERM signal → graceful shutdown (finish in-flight requests, max 30s timeout)
   - Restart: not supported (stateless server; clients reconnect on restart)
   - Readiness: `/ready` endpoint (returns 200 when server can accept requests)
   ```
2. Add tests to TC-510:
   - Test: send SIGTERM, verify graceful shutdown within 30s
   - Test: `/ready` returns 503 during startup, 200 when ready

---

### F-GAP-021 | MAJOR | MCP tool examples missing
**Evidence:** specs/24_mcp_tool_schemas.md defines schemas but no example request/response payloads. No curl examples or integration test fixtures.

**Proposed Fix:**
1. Add to specs/24_mcp_tool_schemas.md:388-450 (new section after acceptance):
   ```markdown
   ## Example payloads

   ### Example: launch_start_run
   **Request:**
   ```json
   {
     "run_config": {
       "product_slug": "3d",
       "family": "3d",
       "github_repo_url": "https://github.com/aspose-3d/Aspose.3D-for-Python-via-.NET",
       "github_ref": "abc123...",
       "locales": ["en"],
       "required_sections": ["products", "docs"]
     }
   }
   ```

   **Response (success):**
   ```json
   {
     "ok": true,
     "run_id": "r_2026-01-26T15-30-00Z_launch_3d_abc123_def456",
     "state": "CREATED"
   }
   ```
   [... examples for all 11 tools ...]
   ```
2. Add curl examples to each tool section
3. Create integration test fixtures in `tests/fixtures/mcp_examples/`

---

### F-GAP-023 | MAJOR | Caching feature completion criteria undefined
**Evidence:** specs/10_determinism_and_caching.md:30-38 defines cache keys but no "done" definition. What to cache? Cache hit rate target? Cache storage limits?

**Proposed Fix:**
1. See F-GAP-007 for implementation spec additions
2. Add acceptance criteria to specs/10_determinism_and_caching.md:51-60 (new section):
   ```markdown
   ## Caching acceptance criteria
   - [ ] Cache directory created at run start
   - [ ] Cache hit/miss telemetry emitted for every cacheable worker invocation
   - [ ] Cache hit produces identical output as cache miss (verified by determinism harness)
   - [ ] Cache invalidation works: changing inputs_hash invalidates cache
   - [ ] TTL enforcement: cache entries older than ttl_days are ignored
   - [ ] Cache size monitoring: telemetry tracks total cache disk usage
   - Target: 80%+ cache hit rate for repeated runs with same inputs
   ```

---

### F-GAP-024 | MAJOR | Emergency manual edits enumeration enforcement missing
**Evidence:** specs/01_system_contract.md:74 requires "enumerates the affected files" but no validation gate checks this. plans/taskcards/TC-201_emergency_mode_manual_edits.md exists but no E2E test.

**Proposed Fix:**
1. Add to specs/09_validation_gates.md:80-85 (after fix loop section):
   ```markdown
   ### Gate: Manual edits enumeration (when allow_manual_edits=true)
   - If `run_config.allow_manual_edits=true`:
     - validation_report MUST set `manual_edits=true`
     - validation_report MUST include `manual_edits_files[]` array with all manually-edited file paths
     - Gate compares: git diff (all changes) vs patch_bundle.json (planned changes)
     - Any file changed but not in patch_bundle MUST be in manual_edits_files[]
     - Failure: BLOCKER if unenumerated manual edits detected
   ```
2. Add E2E test to TC-201 or TC-571:
   ```bash
   # Scenario: manual edit without enumeration
   1. Set allow_manual_edits=true
   2. Manually edit site file outside patch engine
   3. Run validator
   4. Verify: BLOCKER if manual_edits_files[] missing or incomplete
   ```

---

### F-GAP-025 | MAJOR | Telemetry buffering completion criteria vague
**Evidence:** specs/16_local_telemetry_api.md:123-135 defines "flush outbox when connectivity returns" but how to detect connectivity? Retry count? Exponential backoff parameters?

**Proposed Fix:**
1. Add to specs/16_local_telemetry_api.md:126-135 (expand buffering section):
   ```markdown
   ## Buffering retry rules (binding)
   - Initial retry delay: 1 second
   - Max retry delay: 60 seconds
   - Backoff multiplier: 2x
   - Max retry attempts: 10 (after 10 failures, mark run `partial` and stop retrying)
   - Connectivity detection: HTTP HEAD request to `/health` endpoint (2s timeout)
   - Flush triggers:
     1. State transition (any RUN_STATE_CHANGED event)
     2. Before opening PR (W9 prerequisite)
     3. On finalize (run completion)
   ```
2. Add telemetry client tests in TC-500:
   - Test: API fails, verify exponential backoff (1s, 2s, 4s, ...)
   - Test: max retry attempts reached, verify `partial` status
   - Test: connectivity restored, verify flush succeeds

---

### F-GAP-026 | MAJOR | Fix loop convergence criteria undefined
**Evidence:** specs/09_validation_gates.md:78-79 references "max_fix_attempts" but no default value or convergence criteria defined. When to give up?

**Proposed Fix:**
1. Add to specs/09_validation_gates.md:78-85:
   ```markdown
   ## Fix loop convergence (binding)
   - Default: `max_fix_attempts = 5`
   - Override: `run_config.max_fix_attempts` (min: 1, max: 20)
   - Convergence success: validation_report.ok=true within max_fix_attempts
   - Convergence failure:
     - After max_fix_attempts, if validation_report.ok=false, mark run FAILED
     - Emit BLOCKER issue: `FIX_EXHAUSTED` with remaining issue count
   - Infinite loop detection: if same issue reappears after fix, mark unfixable and skip
   ```
2. Add to specs/schemas/run_config.schema.json:
   ```json
   "max_fix_attempts": {
     "type": "integer",
     "minimum": 1,
     "maximum": 20,
     "default": 5
   }
   ```

---

## MINOR Gaps (Should Be Addressed)

### F-GAP-008 | MINOR | Template selection tiebreaker justification missing
**Evidence:** specs/20_rulesets_and_templates_registry.md referenced by plans/taskcards/TC-430_ia_planner_w4.md:99-102 warns about "arbitrary tiebreakers" but no resolution strategy defined.

**Proposed Fix:**
1. Add to specs/20_rulesets_and_templates_registry.md (new section):
   ```markdown
   ## Template selection tiebreaker (binding)
   When multiple templates match with equal priority:
   1. Prefer template with more recent `templates_version` (from template file metadata)
   2. If versions equal, prefer template with lexicographically first template_id
   3. Log tiebreaker to telemetry: `TEMPLATE_SELECTION_TIEBREAKER` event with candidates
   ```
2. Add test to TC-430: create 2 templates with same priority, verify deterministic selection

---

### F-GAP-016 | MINOR | Floating-point determinism policy missing
**Evidence:** If metrics_json includes float values (latency_ms, token costs), are they rounded? No rounding spec in specs/16_local_telemetry_api.md:79-91.

**Proposed Fix:**
1. Add to specs/16_local_telemetry_api.md:82-85 (expand metrics_json section):
   ```markdown
   ## Floating-point values (binding)
   - All float values in metrics_json MUST be rounded to 3 decimal places
   - Rounding mode: round-half-to-even (Python default)
   - Examples: `latency_ms: 123.456`, `cost_usd: 0.001`
   ```
2. Add validation to schema: all float fields use `multipleOf: 0.001` constraint

---

### F-GAP-017 | MINOR | MCP tool "list artifacts" missing
**Evidence:** launch_get_artifact (specs/24_mcp_tool_schemas.md:255-263) requires artifact_name but no discovery tool. User must know artifact names from schema docs.

**Proposed Fix:**
1. Add MCP tool to specs/14_mcp_endpoints.md:19 (after launch_get_artifact):
   ```
   - launch_list_artifacts(run_id) -> { artifacts[] }
   ```
2. Add tool schema to specs/24_mcp_tool_schemas.md:264-275:
   ```markdown
   ### launch_list_artifacts
   Request:
   ```json
   { "run_id": "r_..." }
   ```

   Response:
   ```json
   {
     "ok": true,
     "artifacts": [
       {"name": "repo_inventory.json", "size_bytes": 12345, "sha256": "..."},
       {"name": "page_plan.json", "size_bytes": 67890, "sha256": "..."}
     ]
   }
   ```
   ```
3. Add to TC-510

---

### F-GAP-018 | MINOR | MCP tool "get event log" missing
**Evidence:** events.ndjson referenced in specs/11_state_and_events.md:55 but no MCP accessor.

**Proposed Fix:**
1. Add MCP tool to specs/14_mcp_endpoints.md:20:
   ```
   - launch_get_events(run_id, limit?, offset?) -> { events[] }
   ```
2. Add tool schema to specs/24_mcp_tool_schemas.md
3. Add to TC-510

---

### F-GAP-019 | MINOR | MCP tool "get snapshot" missing
**Evidence:** snapshot.json referenced in specs/11_state_and_events.md:101-111 but no MCP accessor.

**Proposed Fix:**
1. Add MCP tool to specs/14_mcp_endpoints.md:21:
   ```
   - launch_get_snapshot(run_id) -> { snapshot }
   ```
2. Add tool schema to specs/24_mcp_tool_schemas.md
3. Add to TC-510

---

### F-GAP-027 | MINOR | Template selection completion criteria vague
**Evidence:** FEAT-009 (PagePlan) requires "deterministic template selection" (specs/21_worker_contracts.md:145-146) but plans/taskcards/TC-430_ia_planner_w4.md:99-102 warns about "arbitrary tiebreakers" without resolution.

**Proposed Fix:**
1. See F-GAP-008 for tiebreaker rules
2. Add acceptance criteria to TC-430:156-163:
   ```markdown
   - [ ] Template selection determinism test: run planner twice, verify identical template_id selections for all pages
   ```

---

## Gap Prioritization

### Implement First (Blockers + Critical MAJOR)
1. **F-GAP-009, F-GAP-022** (batch execution) - enables scale requirement
2. **F-GAP-013** (LLM nondeterminism fallback) - determinism guarantee at risk
3. **F-GAP-002 to F-GAP-005** (compliance gates N/O/Q/R) - security/cost controls
4. **F-GAP-001** (rollback execution) - production safety
5. **F-GAP-007, F-GAP-015, F-GAP-023** (caching) - performance + determinism

### Implement Second (Testing + Observability MAJOR)
6. **F-GAP-010** (resume E2E test) - verifies resume correctness
7. **F-GAP-011** (telemetry buffering test) - verifies resilience
8. **F-GAP-012** (conflict resolution test) - verifies patch engine robustness
9. **F-GAP-020, F-GAP-021** (MCP lifecycle + examples) - MCP usability

### Implement Third (Policy Enforcement MAJOR)
10. **F-GAP-024** (manual edits enumeration) - policy compliance
11. **F-GAP-025** (telemetry buffering params) - operational clarity
12. **F-GAP-026** (fix loop convergence) - prevents infinite loops
13. **F-GAP-014** (timestamp policy) - data quality

### Implement Fourth (Design Documentation MAJOR)
14. **F-GAP-006** (performance/scalability justification) - architecture clarity

### Implement Last (MINOR)
15. **F-GAP-008, F-GAP-027** (template selection tiebreaker) - determinism edge case
16. **F-GAP-016** (floating-point policy) - data quality edge case
17. **F-GAP-017, F-GAP-018, F-GAP-019** (MCP discovery tools) - convenience

---

## Summary by Category

### Feature Sufficiency Gaps
- F-GAP-001 (rollback execution)
- F-GAP-002, F-GAP-003, F-GAP-004, F-GAP-005 (compliance gates N/O/Q/R)
- F-GAP-009 (batch execution)
- F-GAP-017, F-GAP-018, F-GAP-019 (MCP discovery tools)

### Design Rationale Gaps
- F-GAP-006 (performance/scalability justification)
- F-GAP-007 (caching strategy)
- F-GAP-008 (template selection tiebreaker)

### Testability Gaps
- F-GAP-010 (resume E2E test)
- F-GAP-011 (telemetry buffering test)
- F-GAP-012 (conflict resolution test)
- F-GAP-020 (MCP lifecycle)
- F-GAP-021 (MCP examples)

### Determinism & Reproducibility Gaps
- F-GAP-013 (LLM nondeterminism fallback)
- F-GAP-014 (timestamp policy)
- F-GAP-015 (cache invalidation)
- F-GAP-016 (floating-point policy)

### Feature Completeness Gaps
- F-GAP-022 (batch execution completion criteria)
- F-GAP-023 (caching completion criteria)
- F-GAP-024 (manual edits enumeration)
- F-GAP-025 (telemetry buffering criteria)
- F-GAP-026 (fix loop convergence)
- F-GAP-027 (template selection criteria)
