# AGENT_S: Specs Quality Gaps

## Format
`GAP-ID | SEVERITY | description | evidence | proposed fix`

**Severity Levels**:
- **BLOCKER**: Spec is unimplementable without this info (missing algorithm, undefined behavior, contradictions)
- **MAJOR**: Spec is implementable but ambiguous (vague language, missing edge cases, unclear failure modes)
- **MINOR**: Spec is implementable but could be clearer (missing examples, no rationale, minor terminology inconsistencies)

---

## BLOCKER Gaps (19)

### S-GAP-002-001 | BLOCKER | Adapter fallback when no match
**Spec**: specs/02_repo_ingestion.md
**Evidence**: Lines 163-227 define adapter selection algorithm but do not specify what happens when `adapter_key` has no matching entry in the adapter registry.
```
Lines 197-205:
4. **Select Adapter**:
   ```
   adapter_key = f"{platform_family}:{repo_archetype}"
   # Lookup in adapter registry (priority order):
   1. Exact match: {platform_family}:{repo_archetype}
   2. Platform fallback: {platform_family}:default
   3. Universal fallback: "universal:best_effort"
```
Gap: No specification of error handling if all 3 lookups fail.

**Proposed Fix**:
- File to edit: `specs/02_repo_ingestion.md`
- Section to add: After line 205, add new subsection "## Adapter Selection Failure Handling"
- Required content:
  ```markdown
  ### Adapter Selection Failure Handling (binding)

  If adapter selection fails (no exact match, no platform fallback, and universal fallback is not available):
  1. Emit telemetry event `ADAPTER_SELECTION_FAILED` with platform_family and repo_archetype
  2. Open BLOCKER issue with error_code `REPO_SCOUT_MISSING_ADAPTER`
  3. Fail the run with exit code 5 (unexpected internal error)
  4. Include in issue.message: "No adapter available for {platform_family}:{repo_archetype}. Add adapter or use repo_hints to override."

  The universal fallback adapter MUST always exist and be registered as "universal:best_effort".
  ```
- Acceptance criteria: Gap closed when spec includes failure mode, error code, exit code, and telemetry event for adapter selection failure.

---

### S-GAP-002-002 | BLOCKER | Phantom path detection incomplete
**Spec**: specs/02_repo_ingestion.md
**Evidence**: Lines 91-100 define phantom path detection but do not specify:
1. How to detect references (regex patterns? AST parsing?)
2. What file types to scan (only markdown? also code comments?)
3. Whether to fail the run or continue with warnings

```
Lines 91-100:
#### Phantom path detection (universal, binding)
If a doc file (e.g., README) references a path (e.g., `examples/`, `docs/`) that does not exist:
1. Record a `phantom_path` entry in `repo_inventory.phantom_paths` with:
   - `claimed_path`: the path mentioned
   - `source_file`: where it was claimed
   - `source_line`: line number if determinable
2. Emit a telemetry warning event: `phantom_path_detected`
3. Do NOT fail the run - proceed with fallback discovery chains
4. If the phantom path was claimed as an examples source, mark related claims with `confidence: low`
```

**Proposed Fix**:
- File to edit: `specs/02_repo_ingestion.md`
- Section to replace: Lines 91-100 "#### Phantom path detection (universal, binding)"
- Required content:
  ```markdown
  #### Phantom path detection (universal, binding)

  **Detection algorithm**:
  1. Scan file types: `*.md`, `*.rst`, `*.txt` (documentation files)
  2. Extract path references using regex: `(?:examples?|samples?|demos?|docs?|documentation)/[a-zA-Z0-9_/.-]+`
  3. For each extracted path:
     a. Normalize to relative path from repo root
     b. Check if path exists in `repo_inventory.file_tree`
     c. If not exists, record as phantom_path

  **Recording behavior** (when phantom path detected):
  1. Record a `phantom_path` entry in `repo_inventory.phantom_paths` with:
     - `claimed_path`: the path mentioned (normalized)
     - `source_file`: relative path where it was claimed
     - `source_line`: line number (via regex match position)
     - `detection_pattern`: the regex pattern that matched
  2. Emit telemetry warning event: `phantom_path_detected` with all fields
  3. Do NOT fail the run - proceed with fallback discovery chains
  4. If the phantom path was claimed as an examples source, mark related claims with `confidence: low`

  **Schema requirement**:
  Add to `repo_inventory.schema.json`:
  ```json
  "phantom_paths": {
    "type": "array",
    "items": {
      "type": "object",
      "required": ["claimed_path", "source_file", "detection_pattern"],
      "properties": {
        "claimed_path": {"type": "string"},
        "source_file": {"type": "string"},
        "source_line": {"type": "integer", "minimum": 1},
        "detection_pattern": {"type": "string"}
      }
    }
  }
  ```
  ```
- Acceptance criteria: Gap closed when spec includes detection algorithm with regex patterns, file type scope, recording schema, and no-fail guarantee.

---

### S-GAP-004-001 | BLOCKER | Claim compilation algorithm missing
**Spec**: specs/04_claims_compiler_truth_lock.md
**Evidence**: Lines 21-30 list inputs and outputs for "Claims compilation" but do not specify the processing algorithm.

```
Lines 21-30:
## Claims compilation
Inputs:
- RepoInventory
- detected candidate statements from docs and source
- any existing ProductFacts from cache

Outputs:
- ProductFacts with stable claim references
- EvidenceMap entries for each claim_id
- `RUN_DIR/artifacts/truth_lock_report.json` (validate against `specs/schemas/truth_lock_report.schema.json`)
```
Gap: "detected candidate statements from docs and source" - how are these detected? No algorithm.

**Proposed Fix**:
- File to edit: `specs/04_claims_compiler_truth_lock.md`
- Section to add: After line 30, add new section "## Claims Compilation Algorithm (binding)"
- Required content:
  ```markdown
  ## Claims Compilation Algorithm (binding)

  ### Step 1: Extract Candidate Statements
  For each file in `repo_inventory.doc_entrypoints` and `repo_inventory.source_roots`:
  1. Parse markdown/docstrings/comments (language-specific)
  2. Extract declarative sentences matching patterns:
     - Feature claims: "supports X", "can Y", "enables Z"
     - Workflow claims: "install via X", "usage: Y"
     - Format claims: "reads/writes X format"
     - API claims: "provides X class/function"
     - Limitation claims: "does not support X", "not yet implemented"
  3. For each extracted sentence:
     a. Record `claim_text` (normalized per line 13-19)
     b. Record `source_file`, `start_line`, `end_line`
     c. Classify `claim_kind` based on pattern match

  ### Step 2: Build EvidenceMap
  For each candidate statement:
  1. Compute `claim_id = sha256(normalized_claim_text + claim_kind)` (per lines 13-19)
  2. Determine `truth_status`:
     - `fact` if backed by source code constant, test, or manifest entry
     - `inference` if derived only from documentation
  3. Create EvidenceMap entry with citations array (file, line range)

  ### Step 3: Populate ProductFacts
  Group claims by `claim_kind` and `claim_groups`:
  1. Merge claims into ProductFacts fields:
     - `claim_kind=feature` → ProductFacts.claims[]
     - `claim_kind=format` → ProductFacts.supported_formats[]
     - `claim_kind=workflow` → ProductFacts.workflows[]
     - `claim_kind=api` → ProductFacts.api_surface_summary
     - `claim_kind=limitation` → ProductFacts.limitations[]
  2. Record claim_id references for each populated field

  ### Step 4: Generate TruthLock Report
  Write `truth_lock_report.json` with:
  - `total_claims`: count of all claims
  - `fact_claims`: count with truth_status=fact
  - `inference_claims`: count with truth_status=inference
  - `unsupported_claims`: claims rejected by allow_inference policy
  - `claim_coverage_by_section`: map of which claims are used in which sections
  ```
- Acceptance criteria: Gap closed when spec includes extraction algorithm with patterns, evidence mapping algorithm, ProductFacts population rules, and TruthLock report generation.

---

### S-GAP-006-001 | BLOCKER | Planning failure mode unspecified
**Spec**: specs/06_page_planning.md
**Evidence**: Lines 49-52 define acceptance criteria mentioning "All required sections have at least minimum pages" but do not specify what happens when minimum cannot be achieved.

```
Lines 49-52:
## Acceptance
- page_plan.json validates schema
- All required sections have at least minimum pages
- Every page references claim_ids and snippet tags that exist
```
Gap: What happens when a required section cannot be planned (e.g., no evidence for docs pages)?

**Proposed Fix**:
- File to edit: `specs/06_page_planning.md`
- Section to add: After line 52, add new section "## Planning Failure Modes (binding)"
- Required content:
  ```markdown
  ## Planning Failure Modes (binding)

  ### Insufficient Evidence for Required Section
  If a required section (from `run_config.required_sections`) cannot meet minimum page count due to lack of evidence:
  1. Open BLOCKER issue with:
     - `issue_id`: `plan_incomplete_{section}`
     - `error_code`: `IA_PLANNER_PLAN_INCOMPLETE`
     - `severity`: `blocker`
     - `message`: "Cannot plan {section}: insufficient evidence for minimum page count ({actual} < {minimum})"
     - `suggested_fix`: "Add evidence to ProductFacts or reduce minimum via launch_tier=minimal"
  2. Emit telemetry event `PLAN_INCOMPLETE` with section and deficit details
  3. Halt planning and return to orchestrator with FAILED state
  4. Do NOT proceed to drafting

  ### Zero Pages Planned for Optional Section
  If an optional section has zero pages due to lack of evidence:
  1. Emit telemetry warning `SECTION_SKIPPED` with section and reason
  2. Continue planning other sections
  3. Record in `page_plan.skipped_sections[]` with rationale

  ### URL Path Collision Detected
  If multiple pages resolve to the same `url_path` (per specs/33_public_url_mapping.md):
  1. Open BLOCKER issue with:
     - `error_code`: `IA_PLANNER_URL_COLLISION`
     - `files`: list of colliding output_path values
     - `message`: "URL collision detected: {url_path} maps to multiple pages"
  2. Emit telemetry event `URL_COLLISION_DETECTED`
  3. Halt planning with FAILED state
  ```
- Acceptance criteria: Gap closed when spec includes failure modes with error codes, issue schemas, telemetry events, and halt behavior.

---

### S-GAP-008-001 | BLOCKER | Conflict resolution algorithm missing
**Spec**: specs/08_patch_engine.md
**Evidence**: Lines 30-35 mention "Conflict behavior" but do not specify the algorithm for detecting or resolving conflicts.

```
Lines 30-35:
## Conflict behavior
- If patch cannot apply cleanly:
  - record an Issue with severity=blocker
  - move run to FIXING
  - generate a new targeted patch with updated selector
```
Gap: What is a "clean" apply? How are conflicts detected? What is "updated selector"?

**Proposed Fix**:
- File to edit: `specs/08_patch_engine.md`
- Section to replace: Lines 30-35 "## Conflict behavior"
- Required content:
  ```markdown
  ## Conflict Resolution Algorithm (binding)

  ### Conflict Detection
  A patch application is considered **conflicted** when:
  1. **Anchor not found**: For `update_by_anchor`, the target heading does not exist in the file
  2. **Line range out of bounds**: For `update_file_range`, the specified line range exceeds file length
  3. **Frontmatter key missing**: For `update_frontmatter_keys`, the target key path does not exist in YAML
  4. **Content mismatch**: The expected content at the patch location does not match actual content (hash mismatch)
  5. **Path outside allowed_paths**: The patch target is not within `run_config.allowed_paths`

  ### Conflict Response (binding)
  On conflict detection:
  1. Do NOT apply the conflicted patch
  2. Record all unapplied patches to `RUN_DIR/artifacts/patch_conflicts.json` with:
     - `patch_id`: unique identifier for the patch
     - `conflict_reason`: one of the 5 categories above
     - `expected_state`: what the patch expected (hash, line count, anchor)
     - `actual_state`: what was found (hash, line count, missing anchor)
  3. Open BLOCKER issue with:
     - `error_code`: `LINKER_PATCHER_CONFLICT_UNRESOLVABLE`
     - `severity`: `blocker`
     - `files`: list of affected files
     - `location.path`: first conflicted file
     - `suggested_fix`: diagnostic guidance (e.g., "Expected heading '## Installation' not found in {file}")
  4. Emit telemetry event `PATCH_CONFLICT_DETECTED` with all conflict details
  5. Transition run state to FIXING

  ### Conflict Resolution Strategy
  The Fixer (W8) MUST resolve conflicts by:
  1. Re-reading the current site worktree state
  2. Generating a new patch with updated selectors:
     - If anchor not found: search for closest similar heading or insert at end of section
     - If line range out of bounds: use file length as new range bound
     - If frontmatter key missing: add the key with default value
     - If content mismatch: perform three-way merge (base, ours, theirs) and flag manual review
  3. Emit new patch to `patch_bundle.delta.json`
  4. Re-run W6 LinkerAndPatcher with updated patch bundle

  ### Max Resolution Attempts
  Conflict resolution is bounded by `run_config.max_fix_attempts` (default 3).
  If conflicts persist after max attempts:
  1. Emit telemetry event `PATCH_CONFLICT_EXHAUSTED`
  2. Fail the run with exit code 5 (unexpected internal error)
  3. Write detailed conflict report to `RUN_DIR/reports/patch_conflicts_final.md`
  ```
- Acceptance criteria: Gap closed when spec includes conflict detection criteria, conflict response with error codes, resolution strategy, and max attempts bound.

---

### S-GAP-008-002 | BLOCKER | Idempotency mechanism unspecified
**Spec**: specs/08_patch_engine.md
**Evidence**: Lines 25-28 state "Patch apply must be idempotent" but do not specify HOW idempotency is achieved.

```
Lines 25-28:
## Idempotency
Patch apply must be idempotent:
- running patch twice yields same output
- anchors should detect existing insertion and avoid duplicates
```
Gap: "anchors should detect existing insertion" - how is this detected?

**Proposed Fix**:
- File to edit: `specs/08_patch_engine.md`
- Section to replace: Lines 25-28 "## Idempotency"
- Required content:
  ```markdown
  ## Idempotency Mechanism (binding)

  Patch application MUST be idempotent via the following mechanisms:

  ### 1. Content Fingerprinting
  Before applying any patch:
  1. Compute `content_hash = sha256(target_file_content)` for the current file state
  2. Compare to `patch.expected_content_hash` (if present)
  3. If hashes match, patch has already been applied → skip with INFO log
  4. If hashes differ, proceed with application

  ### 2. Anchor-Based Duplicate Detection
  For `update_by_anchor` patches:
  1. Search for the target anchor heading in the file
  2. Search for the patch content within the section under that anchor
  3. If patch content already exists (exact match or fuzzy match >90% similarity):
     a. Log INFO: "Patch already applied under anchor {anchor}"
     b. Skip application
     c. Record in telemetry event `PATCH_ALREADY_APPLIED`
  4. If patch content does not exist:
     a. Apply patch by inserting content under anchor
     b. Update `content_hash` in patch metadata

  ### 3. Frontmatter Key Idempotency
  For `update_frontmatter_keys` patches:
  1. Parse current frontmatter as YAML
  2. For each key in patch:
     a. If key exists with same value → skip
     b. If key exists with different value → update (NOT skip - this is an update)
     c. If key does not exist → add
  3. Write frontmatter atomically (temp file + rename)

  ### 4. Create-Once Semantics
  For `create_file` patches:
  1. Check if file exists at `output_path`
  2. If exists and `content_hash` matches patch content → skip with INFO log
  3. If exists and `content_hash` differs → open BLOCKER issue `FILE_EXISTS_CONFLICT`
  4. If not exists → create file

  ### Acceptance
  A patch application is considered idempotent when:
  - Running the same PatchBundle twice produces identical site worktree state
  - No duplicate content is inserted
  - No errors are raised on second application
  - Telemetry logs contain `PATCH_ALREADY_APPLIED` events on second run
  ```
- Acceptance criteria: Gap closed when spec includes content fingerprinting, anchor duplicate detection, frontmatter idempotency, create-once semantics, and acceptance criteria.

---

### S-GAP-011-001 | BLOCKER | Replay algorithm unspecified
**Spec**: specs/11_state_and_events.md
**Evidence**: Lines 112-115 state "replay from the local event log recreates the snapshot" but do not specify the replay algorithm.

```
Lines 112-115:
## Acceptance
- replay from the local event log recreates the snapshot
- resume continues from last stable state without redoing completed work unless forced
- telemetry API contains a complete parent+child run trail and all LLM call runs
```
Gap: HOW does replay work? What are the replay steps?

**Proposed Fix**:
- File to edit: `specs/11_state_and_events.md`
- Section to add: After line 115, add new section "## Replay Algorithm (binding)"
- Required content:
  ```markdown
  ## Replay Algorithm (binding)

  Replay recreates the final snapshot from the append-only event log without re-executing workers.

  ### Inputs
  - `RUN_DIR/events.ndjson` (or `events.sqlite`)
  - Initial snapshot: `{ run_id, run_state: CREATED, artifacts: [], work_items: [], issues: [], section_states: {} }`

  ### Algorithm Steps
  1. **Load Events**: Read all events from `events.ndjson` in append order
  2. **Validate Chain**: For each event, verify:
     - `event_hash = sha256(event_id + ts + type + payload + prev_hash)`
     - `prev_hash` matches previous event's `event_hash`
     - If validation fails, halt with error `EVENT_CHAIN_BROKEN`
  3. **Apply Event Reducers**: For each event type, update snapshot:
     - `RUN_CREATED`: Initialize snapshot with run_id, timestamps
     - `RUN_STATE_CHANGED`: Update `snapshot.run_state = payload.new_state`
     - `ARTIFACT_WRITTEN`: Add to `snapshot.artifacts[]` with name, path, sha256, schema_id
     - `WORK_ITEM_QUEUED`: Add to `snapshot.work_items[]` with status=pending
     - `WORK_ITEM_STARTED`: Update work_item status=in_progress, started_at
     - `WORK_ITEM_FINISHED`: Update work_item status=completed, finished_at
     - `ISSUE_OPENED`: Add to `snapshot.issues[]` with status=OPEN
     - `ISSUE_RESOLVED`: Update issue status=RESOLVED, resolved_at
     - `GATE_RUN_FINISHED`: Update gate result in snapshot.gates[]
  4. **Write Snapshot**: After processing all events, write `RUN_DIR/snapshot.json`
  5. **Validate Snapshot**: Ensure snapshot validates against `snapshot.schema.json`

  ### Resume Algorithm (binding)

  Resume continues from the last stable snapshot without re-executing completed work.

  1. **Load Snapshot**: Read `RUN_DIR/snapshot.json`
  2. **Identify Last Stable State**:
     - If `snapshot.run_state` is a stable state (PLAN_READY, DRAFT_READY, READY_FOR_PR), start from there
     - If `snapshot.run_state` is a transitional state (DRAFTING, LINKING, VALIDATING, FIXING), rewind to last stable state
  3. **Filter Completed Work**:
     - Load `snapshot.work_items[]` with status=completed
     - Load `snapshot.artifacts[]` (all artifacts are considered completed)
     - Do NOT re-queue work items that are completed
  4. **Resume Orchestrator**:
     - Set orchestrator state to `snapshot.run_state`
     - Queue only work_items with status=pending or in_progress
     - Continue from the current state transition

  ### Forced Full Replay (optional)

  To force full replay from scratch (ignore snapshot):
  1. Delete `RUN_DIR/snapshot.json`
  2. Run replay algorithm from initial snapshot
  3. Orchestrator will re-execute all work items (artifacts are cached, so LLM calls may be skipped if cache hits)
  ```
- Acceptance criteria: Gap closed when spec includes replay algorithm with event reducers, chain validation, snapshot output, resume algorithm with state identification, and forced replay option.

---

### S-GAP-013-001 | BLOCKER | Pilot execution contract missing
**Spec**: specs/13_pilots.md
**Evidence**: Entire spec (35 lines) lacks a complete pilot execution contract. No specification of:
1. How pilots are executed
2. How golden artifacts are validated
3. How regression is detected

```
Lines 1-35:
# Pilots (Golden Runs for Regression Detection)

## Purpose
Establish two pilot projects as regression baselines.

## Requirements
- Each pilot must pin repo SHA and site SHA.
- Each pilot must generate:
  - golden PagePlan
  - golden ValidationReport
- Golden artifacts are stored and versioned.
- Runs against pilots detect drift by comparing new outputs to golden artifacts.

## Pilots
TBD - will be defined after initial implementation.

## Acceptance
- Two pilots exist with pinned SHAs.
- Golden artifacts validate against schemas.
- Diff tooling can compare new artifacts to golden artifacts and highlight regressions.
```
Gap: No execution contract, no diff algorithm, no acceptance thresholds.

**Proposed Fix**:
- File to edit: `specs/13_pilots.md`
- Section to add: Replace entire spec with complete pilot contract
- Required content:
  ```markdown
  # Pilots (Golden Runs for Regression Detection)

  ## Purpose
  Establish two pilot projects as regression baselines to detect unintended changes in system behavior.

  ## Pilot Contract (binding)

  ### Required Pilot Fields
  Each pilot MUST include:
  - `pilot_id`: Unique identifier (e.g., `pilot_aspose_note_python`, `pilot_aspose_cells_dotnet`)
  - `github_repo_url`: Public GitHub repo URL
  - `github_ref`: Pinned commit SHA (NOT branch or tag)
  - `site_ref`: Pinned site repo commit SHA
  - `workflows_ref`: Pinned workflows repo commit SHA
  - `run_config_path`: Path to pinned run config (e.g., `specs/pilots/{pilot_id}/run_config.pinned.yaml`)
  - `golden_artifacts_dir`: Path to golden artifacts (e.g., `specs/pilots/{pilot_id}/golden/`)

  ### Golden Artifacts (binding)
  Each pilot MUST generate and store:
  1. `golden/page_plan.json` - Golden PagePlan
  2. `golden/validation_report.json` - Golden ValidationReport with ok=true
  3. `golden/patch_bundle.json` - Golden PatchBundle
  4. `golden/diff_summary.md` - Human-readable diff summary
  5. `golden/fingerprints.json` - Hashes of all artifacts for regression detection

  ### Pilot Execution Contract (binding)

  To execute a pilot run:
  1. Load pilot config from `specs/pilots/{pilot_id}/run_config.pinned.yaml`
  2. Validate config includes pinned SHAs for all `*_ref` fields (no floating refs allowed)
  3. Execute full launch run with `validation_profile=ci`
  4. Generate artifacts under `RUN_DIR/artifacts/`
  5. Compare generated artifacts to golden artifacts via diff algorithm (below)
  6. Emit telemetry event `PILOT_RUN_COMPLETED` with comparison results

  ### Regression Detection Algorithm (binding)

  Compare generated artifacts to golden artifacts:

  1. **Exact Match Artifacts** (must be byte-identical):
     - `page_plan.json` (after removing timestamps and run_id)
     - `validation_report.ok` field

  2. **Semantic Equivalence Artifacts** (allow minor differences):
     - `patch_bundle.json`: Allow line number shifts ±5 lines, but operations must be identical
     - `validation_report.issues[]`: Allow empty vs empty, but any new BLOCKER is a regression

  3. **Computed Diff Metrics**:
     - Page count delta: `|generated_page_count - golden_page_count|`
     - Claim count delta: `|generated_claim_count - golden_claim_count|`
     - Issue count delta: `|generated_issue_count - golden_issue_count|`

  4. **Regression Thresholds** (configurable):
     - Page count delta > 2 → WARN
     - Claim count delta > 5 → WARN
     - New BLOCKER issue → FAIL
     - validation_report.ok changed from true to false → FAIL

  5. **Regression Report**:
     Write to `RUN_DIR/reports/pilot_regression_report.md` with:
     - Summary: PASS / WARN / FAIL
     - Diff metrics
     - List of regressions detected
     - Suggested fixes (if deterministic)

  ### Golden Artifact Update Policy (binding)

  Golden artifacts MUST be updated when:
  1. Intentional system behavior change (e.g., new validation gate added)
  2. Schema version bumped (breaking change)
  3. Pilot repo/site SHA intentionally updated

  Golden artifact update process:
  1. Run pilot with new behavior
  2. Validate all gates pass
  3. Manually review diff between old and new golden artifacts
  4. If diff is expected and correct:
     a. Replace `specs/pilots/{pilot_id}/golden/*` with new artifacts
     b. Update `fingerprints.json` with new hashes
     c. Commit with message: "Update pilot {pilot_id} golden artifacts: {reason}"
     d. Include rationale in commit body

  ## Pilots

  ### Pilot 1: Aspose.Note Python (planned)
  - `pilot_id`: `pilot_aspose_note_python`
  - `github_repo_url`: TBD (will be pinned after initial implementation)
  - `github_ref`: TBD (pinned commit SHA)
  - Purpose: Test Python repo adapter with standard repo structure

  ### Pilot 2: Aspose.Cells .NET (planned)
  - `pilot_id`: `pilot_aspose_cells_dotnet`
  - `github_ref`: TBD (pinned commit SHA)
  - Purpose: Test .NET repo adapter with monorepo structure

  ## Acceptance
  - Two pilots exist with pinned SHAs
  - Golden artifacts stored and versioned under `specs/pilots/{pilot_id}/golden/`
  - Regression detection algorithm implemented and tested
  - CI runs pilots on every commit with regression detection
  - Golden artifact update commits include rationale
  ```
- Acceptance criteria: Gap closed when spec includes pilot contract, golden artifacts, execution contract, regression detection algorithm with thresholds, update policy, and pilot definitions.

---

### S-GAP-014-001 | BLOCKER | MCP endpoint specifications missing
**Spec**: specs/14_mcp_endpoints.md
**Evidence**: Entire spec (26 lines) references MCP requirement but provides no endpoint specifications, request/response schemas, or error handling.

```
Lines 1-26:
# MCP Endpoints (Model Context Protocol)

## Requirement (non-negotiable)
All features MUST be exposed via MCP endpoints.
CLI may exist, but MCP is required for full feature parity.

## Scope
MCP tools enable external clients (IDE extensions, agents) to:
- invoke launch runs
- retrieve run status
- list/query artifacts
- trigger validation
- inspect telemetry
- manage taskcards

## Contract
TBD - will be defined after initial implementation aligned with MCP specification.

## References
- MCP spec: https://spec.modelcontextprotocol.io/
- See also: 24_mcp_tool_schemas.md for tool definitions.

## Acceptance
- All MCP tools defined in 24_mcp_tool_schemas.md are exposed via MCP server.
- MCP server is runnable and passes MCP spec compliance tests.
```
Gap: No endpoint paths, no schemas, no error handling, no auth contract.

**Proposed Fix**:
- File to edit: `specs/14_mcp_endpoints.md`
- Section to replace: Lines 1-26 (replace entire spec)
- Required content:
  ```markdown
  # MCP Endpoints (Model Context Protocol)

  ## Requirement (non-negotiable)
  All features MUST be exposed via MCP endpoints.
  CLI may exist, but MCP is required for full feature parity.

  ## MCP Server Contract (binding)

  ### Server Configuration
  - Protocol: STDIO (standard input/output JSON-RPC)
  - Server name: `foss-launcher-mcp`
  - Server version: Match launcher version (e.g., `0.1.0`)
  - Capabilities: `tools`, `resources` (no prompts or sampling required)

  ### Authentication (binding)
  - MCP servers running over STDIO do not require auth (client controls process)
  - If exposed via HTTP transport (optional), MUST require bearer token auth
  - Token validation MUST use the same pattern as commit service (specs/17_github_commit_service.md)

  ## MCP Tools (binding)

  All tools defined in `specs/24_mcp_tool_schemas.md` MUST be exposed via the MCP server.

  ### Tool Invocation Contract
  1. Client sends `tools/call` JSON-RPC request with:
     - `name`: Tool name (e.g., `launch_run`, `get_run_status`)
     - `arguments`: Tool-specific arguments (validated against tool schema)
  2. Server validates arguments against tool schema (JSON Schema validation)
  3. Server executes tool and returns result or error
  4. All tool executions MUST be logged to local telemetry API with:
     - `job_type = mcp_tool_call`
     - `context_json` containing tool name, arguments (redacted), result summary

  ### Error Handling (binding)

  Tool execution errors MUST be returned as MCP error responses:
  ```json
  {
    "jsonrpc": "2.0",
    "id": <request_id>,
    "error": {
      "code": <error_code>,
      "message": <error_message>,
      "data": {
        "error_code": <structured_error_code_from_specs/01>,
        "details": <additional_context>
      }
    }
  }
  ```

  Error codes follow JSON-RPC spec:
  - `-32700`: Parse error (invalid JSON)
  - `-32600`: Invalid request
  - `-32601`: Method not found (tool not found)
  - `-32602`: Invalid params (schema validation failed)
  - `-32603`: Internal error (tool execution failed)

  ### Tool List

  Minimum required tools (see `specs/24_mcp_tool_schemas.md` for full schemas):

  1. **launch_run** - Start a new launch run
  2. **get_run_status** - Query run status and progress
  3. **list_runs** - List all runs (with filters)
  4. **get_artifact** - Retrieve a run artifact by name
  5. **validate_run** - Trigger validation gates on a run
  6. **resume_run** - Resume a paused/failed run
  7. **cancel_run** - Cancel a running launch
  8. **get_telemetry** - Query telemetry for a run
  9. **list_taskcards** - List available taskcards
  10. **validate_taskcard** - Validate a taskcard file

  ## MCP Resources (optional)

  Optionally, expose run artifacts as MCP resources:
  - `resource://run/{run_id}/page_plan.json`
  - `resource://run/{run_id}/validation_report.json`
  - `resource://run/{run_id}/snapshot.json`

  ## Acceptance
  - MCP server exposes all 10 required tools
  - All tools validate arguments against schemas from specs/24_mcp_tool_schemas.md
  - Error responses follow JSON-RPC + MCP spec
  - Tool executions are logged to telemetry
  - Server passes MCP spec compliance tests (if available)
  ```
- Acceptance criteria: Gap closed when spec includes server config, auth contract, tool invocation contract, error handling with codes, tool list, and acceptance criteria.

---

### S-GAP-014-002 | BLOCKER | MCP auth specification missing
**Spec**: specs/14_mcp_endpoints.md
**Evidence**: Line 5 mentions MCP is required but no auth/security contract is specified. MCP servers may be exposed remotely.

**Proposed Fix**: Included in S-GAP-014-001 above (### Authentication section).

---

### S-GAP-016-001 | BLOCKER | Telemetry failure handling incomplete
**Spec**: specs/16_local_telemetry_api.md
**Evidence**: Spec-wide - no specification of what happens when telemetry API is unreachable or returns errors. Only specs/01_system_contract.md:148-153 mentions outbox pattern but 16_local_telemetry_api.md does not reference it.

**Proposed Fix**:
- File to edit: `specs/16_local_telemetry_api.md`
- Section to add: After HTTP contract section, add "## Failure Handling and Resilience (binding)"
- Required content:
  ```markdown
  ## Failure Handling and Resilience (binding)

  Telemetry is REQUIRED for all runs, but transport failures MUST be handled gracefully.

  ### Outbox Pattern (binding)

  When telemetry POST fails (network error, timeout, 5xx error):
  1. Append the failed request payload to `RUN_DIR/telemetry_outbox.jsonl`
  2. Log WARNING: "Telemetry POST failed: {error}; payload written to outbox"
  3. Continue run execution (do NOT fail the run due to telemetry transport failure)
  4. Retry outbox flush at next stable state transition

  ### Outbox Flush Algorithm

  At each stable state transition (PLAN_READY, DRAFT_READY, READY_FOR_PR):
  1. Check if `RUN_DIR/telemetry_outbox.jsonl` exists and is non-empty
  2. Read all lines (each line is a failed POST payload)
  3. For each payload:
     a. Retry POST to telemetry API
     b. If success: remove line from outbox
     c. If failure after 3 retries: keep in outbox and continue
  4. If all lines successfully flushed: delete `telemetry_outbox.jsonl`
  5. If any lines remain after flush attempt: log WARNING and continue

  ### Bounded Retry Policy

  Retry telemetry POSTs with exponential backoff:
  - Max attempts: 3 per payload
  - Backoff: 1s, 2s, 4s (no jitter needed for non-critical path)
  - Timeout: 10s per POST attempt
  - Do NOT retry on 4xx errors (client error indicates bad payload)

  ### Outbox Size Limits

  To prevent unbounded outbox growth:
  - Max outbox size: 10 MB
  - If outbox exceeds 10 MB: truncate oldest entries and log ERROR
  - Record truncation in telemetry event `TELEMETRY_OUTBOX_TRUNCATED` (when API becomes available)

  ### Failure Telemetry

  When telemetry API is consistently unreachable:
  - After 10 consecutive failures across multiple runs, emit system-level WARNING
  - Write diagnostic report to `reports/telemetry_unavailable.md` with:
    - Outbox size and oldest entry timestamp
    - Number of failed POST attempts
    - Last successful telemetry POST timestamp
    - Suggested fixes (check API endpoint, network, auth token)
  ```
- Acceptance criteria: Gap closed when spec includes outbox pattern, flush algorithm, retry policy, size limits, and failure telemetry.

---

### S-GAP-019-001 | BLOCKER | Tool version lock enforcement missing
**Spec**: specs/19_toolchain_and_ci.md
**Evidence**: Spec-wide - tools are referenced (hugo, markdownlint, lychee) but no runtime verification that correct versions are used.

**Proposed Fix**:
- File to edit: `specs/19_toolchain_and_ci.md`
- Section to add: After toolchain definition, add "## Tool Version Verification (binding)"
- Required content:
  ```markdown
  ## Tool Version Verification (binding)

  All validation gates MUST verify tool versions at runtime to prevent silent drift.

  ### Tool Lock File

  Path: `config/toolchain.lock.yaml`

  Format:
  ```yaml
  schema_version: "1.0"
  tools:
    - name: hugo
      version: "0.128.0"
      checksum: "sha256:abcdef123456..."
      download_url: "https://github.com/gohugoio/hugo/releases/download/v0.128.0/hugo_0.128.0_Linux-64bit.tar.gz"
    - name: markdownlint-cli
      version: "0.39.0"
      checksum: "sha256:fedcba654321..."
      install_cmd: "npm install -g markdownlint-cli@0.39.0"
    - name: lychee
      version: "0.14.3"
      checksum: "sha256:123abc456def..."
      download_url: "https://github.com/lycheeverse/lychee/releases/download/v0.14.3/lychee-v0.14.3-x86_64-unknown-linux-gnu.tar.gz"
  ```

  ### Verification Algorithm (binding)

  Before running any validation gate that uses external tools:
  1. Load `config/toolchain.lock.yaml`
  2. For each tool used by the gate:
     a. Run `{tool} --version` and parse version string
     b. Compare to `tools[].version` in lock file
     c. If version mismatch:
        - Emit BLOCKER issue with error_code `GATE_TOOL_VERSION_MISMATCH`
        - Include in issue.message: "Expected {tool} version {expected}, found {actual}"
        - Halt gate execution
     d. If version matches, log INFO and proceed
  3. Emit telemetry event `TOOL_VERSION_VERIFIED` with tool name and version

  ### Checksum Verification (optional but recommended)

  For downloaded binaries (hugo, lychee):
  1. After download, compute `sha256(binary)`
  2. Compare to `tools[].checksum` in lock file
  3. If mismatch: emit BLOCKER issue `TOOL_CHECKSUM_MISMATCH` and halt

  ### Tool Installation Script

  Provide `scripts/install_tools.sh` (or .ps1 for Windows) that:
  1. Reads `config/toolchain.lock.yaml`
  2. Downloads/installs each tool at the specified version
  3. Verifies checksums
  4. Writes tools to `.tools/` directory at repo root
  5. Emits telemetry event `TOOLS_INSTALLED` with versions

  CI MUST run `scripts/install_tools.sh` before running validation gates.
  ```
- Acceptance criteria: Gap closed when spec includes tool lock file format, verification algorithm with version checks, checksum verification, installation script, and CI integration.

---

### S-GAP-022-001 | BLOCKER | Navigation update algorithm missing
**Spec**: specs/22_navigation_and_existing_content_update.md
**Evidence**: Entire spec mentions navigation updates but provides no algorithm for detecting and updating navigation structures.

**Proposed Fix**:
- File to edit: `specs/22_navigation_and_existing_content_update.md`
- Section to add: After title, add complete navigation update contract
- Required content:
  ```markdown
  # Navigation and Existing Content Update

  ## Purpose
  Update site navigation structures (sidebars, menus, index pages) to include new product pages without breaking existing navigation.

  ## Navigation Discovery (binding)

  ### Step 1: Identify Navigation Files
  For each section in `run_config.required_sections`:
  1. Scan `site_context.navigation_patterns` for navigation file patterns:
     - `_index.md` files (Hugo section indexes)
     - `sidebar.yaml` or `menu.yaml` (theme-specific)
     - Frontmatter `menu` keys in existing pages
  2. Record all navigation files under `allowed_paths` to `artifacts/navigation_inventory.json`

  ### Step 2: Parse Navigation Structures
  For each navigation file:
  1. If `_index.md`: Parse frontmatter `menu` array
  2. If `*.yaml`: Parse YAML and extract menu entries
  3. Build navigation tree structure: `{ section, entries: [{title, url, children}] }`

  ## Navigation Update Algorithm (binding)

  ### Step 3: Determine Insertion Points
  For each new page in `page_plan.pages[]`:
  1. Identify parent section from `page.section`
  2. Search navigation tree for insertion point:
     - If page has `page.parent_slug`: insert as child of parent
     - If page is section root: insert at top level
     - If page is docs guide: insert under "Guides" or "Tutorials" submenu
     - If page is reference: insert under "API Reference" submenu
  3. Determine sort order:
     - Use `page.menu_weight` if present
     - Else use alphabetical sort by `page.title`

  ### Step 4: Generate Navigation Patches
  For each navigation file:
  1. Build patch using `update_by_anchor` or `update_frontmatter_keys`
  2. Add new menu entries at determined insertion points
  3. Preserve existing entries (do not reorder unless required)
  4. Add patches to `patch_bundle.json`

  ## Existing Content Update (binding)

  ### When to Update Existing Pages
  Update existing content when:
  1. New product is added to same family (update family index page)
  2. New platform is added to existing product (update platform comparison table)
  3. New feature is added that affects existing product docs (optional, flag for manual review)

  ### Update Strategy
  1. Identify affected existing pages via `site_context.existing_pages[]`
  2. For each affected page:
     a. Parse current content
     b. Identify update location (anchor, frontmatter key, section)
     c. Generate minimal patch (prefer `update_by_anchor` over full rewrite)
     d. Add to `patch_bundle.json` with `update_reason` field
  3. Record all updates in `reports/existing_content_updates.md` for review

  ## Safety Rules (binding)

  1. NEVER delete existing menu entries
  2. NEVER rewrite entire navigation files (use minimal patches)
  3. NEVER update pages outside `allowed_paths`
  4. ALWAYS validate navigation structure after patching (no broken links)

  ## Acceptance
  - Navigation inventory generated and validated
  - New pages appear in correct navigation menus
  - Existing navigation entries are preserved
  - No broken internal links introduced
  - Manual review report generated for existing content updates
  ```
- Acceptance criteria: Gap closed when spec includes navigation discovery, update algorithm with insertion points, patch generation, existing content update strategy, safety rules, and acceptance criteria.

---

### S-GAP-024-001 | BLOCKER | Tool error handling unspecified
**Spec**: specs/24_mcp_tool_schemas.md
**Evidence**: Spec-wide - tool schemas defined but no error handling for tool execution failures.

**Proposed Fix**:
- File to edit: `specs/24_mcp_tool_schemas.md`
- Section to add: After tool schemas, add "## Tool Execution Error Handling (binding)"
- Required content:
  ```markdown
  ## Tool Execution Error Handling (binding)

  All MCP tool executions MUST implement consistent error handling.

  ### Error Response Format

  On tool execution failure, return MCP error response:
  ```json
  {
    "jsonrpc": "2.0",
    "id": <request_id>,
    "error": {
      "code": -32603,
      "message": "Tool execution failed",
      "data": {
        "error_code": "<COMPONENT_ERROR_TYPE_SPECIFIC>",
        "tool_name": "<tool_name>",
        "details": "<error_details>",
        "suggested_fix": "<actionable_guidance>"
      }
    }
  }
  ```

  ### Error Codes by Tool

  | Tool | Error Code | Condition |
  |------|-----------|-----------|
  | launch_run | ORCHESTRATOR_RUN_CREATION_FAILED | Run creation failed |
  | get_run_status | ORCHESTRATOR_RUN_NOT_FOUND | Run ID does not exist |
  | get_artifact | ORCHESTRATOR_ARTIFACT_NOT_FOUND | Artifact does not exist |
  | validate_run | VALIDATOR_GATE_EXECUTION_FAILED | Gate execution failed |
  | resume_run | ORCHESTRATOR_RESUME_FAILED | Resume from snapshot failed |
  | cancel_run | ORCHESTRATOR_CANCELLATION_FAILED | Cancellation failed |

  ### Tool Timeout Behavior

  Each tool MUST have an execution timeout:
  - **launch_run**: 300s (5 minutes) - returns run_id immediately, run continues async
  - **get_run_status**: 5s
  - **list_runs**: 10s
  - **get_artifact**: 30s (large artifacts)
  - **validate_run**: 600s (10 minutes) - gate execution time
  - **resume_run**: 300s (5 minutes)
  - **cancel_run**: 10s

  On timeout:
  1. Return error with code `-32603` and `error_code: TOOL_TIMEOUT`
  2. Log telemetry event `MCP_TOOL_TIMEOUT` with tool name and elapsed time
  3. Do NOT kill the underlying operation (for async tools like launch_run)

  ### Tool Validation Failures

  On argument validation failure (JSON Schema validation failed):
  1. Return error with code `-32602` (Invalid params)
  2. Include `error_code: SCHEMA_VALIDATION_FAILED`
  3. Include `details` with schema validation error messages
  4. Include `suggested_fix` with example of correct arguments
  ```
- Acceptance criteria: Gap closed when spec includes error response format, error codes by tool, timeout behavior, and validation failure handling.

---

### S-GAP-024-002 | BLOCKER | Schema validation failure handling
**Spec**: specs/24_mcp_tool_schemas.md
**Evidence**: Tool schemas use JSON Schema validation but no specification of what happens when validation fails.

**Proposed Fix**: Included in S-GAP-024-001 above (### Tool Validation Failures section).

---

### S-GAP-026-001 | BLOCKER | Adapter interface undefined
**Spec**: specs/26_repo_adapters_and_variability.md
**Evidence**: Spec-wide - adapter concept defined but no concrete interface (methods, inputs, outputs) specified. Only high-level responsibilities mentioned.

**Proposed Fix**:
- File to edit: `specs/26_repo_adapters_and_variability.md`
- Section to add: After adapter responsibilities, add "## Adapter Interface Contract (binding)"
- Required content:
  ```markdown
  ## Adapter Interface Contract (binding)

  All adapters MUST implement the following interface methods.

  ### Interface Methods

  ```python
  class RepoAdapter(Protocol):
      """Adapter interface for repo-specific ingestion logic."""

      def extract_distribution(
          self,
          repo_root: Path,
          repo_inventory: RepoInventory
      ) -> DistributionInfo:
          """
          Extract package distribution information.

          Returns:
            DistributionInfo with:
            - install_methods: list of install methods (pip, nuget, npm, etc.)
            - install_commands: list of exact install commands
            - package_name: canonical package name
            - package_url: package registry URL (if available)

          If distribution cannot be determined, return empty DistributionInfo with note.
          """
          ...

      def extract_public_api_entrypoints(
          self,
          repo_root: Path,
          repo_inventory: RepoInventory
      ) -> PublicAPIEntrypoints:
          """
          Extract public API surface entrypoints.

          Returns:
            PublicAPIEntrypoints with:
            - modules: list of public module names
            - classes: list of public class names (top-level only)
            - functions: list of public function names (top-level only)
            - entrypoint_path: main entrypoint file (e.g., __init__.py, index.js)

          If API surface cannot be determined, return empty with note.
          """
          ...

      def extract_examples(
          self,
          repo_root: Path,
          repo_inventory: RepoInventory
      ) -> List[SnippetCandidate]:
          """
          Extract example code snippets from repo.

          Returns:
            List of SnippetCandidate with:
            - source_file: relative path to source file
            - start_line, end_line: line range
            - snippet_text: raw snippet code
            - language: detected language
            - tags: list of inferred tags (quickstart, workflow name, etc.)

          Returns empty list if no examples found.
          """
          ...

      def recommended_validation(
          self,
          repo_root: Path,
          repo_inventory: RepoInventory
      ) -> ValidationRecommendations:
          """
          Recommend test/validation commands for this repo.

          Returns:
            ValidationRecommendations with:
            - test_commands: list of test commands (if tests present)
            - lint_commands: list of lint commands (if linter config present)
            - build_commands: list of build commands (if applicable)

          Returns empty if no validation commands discoverable.
          """
          ...
  ```

  ### Adapter Registration

  Adapters MUST be registered in `src/launch/adapters/registry.py`:
  ```python
  ADAPTER_REGISTRY = {
      "python:python_src_pyproject": PythonSrcPyprojectAdapter(),
      "python:python_flat_setup_py": PythonFlatSetupPyAdapter(),
      "node:node_src_package_json": NodeSrcPackageJsonAdapter(),
      "dotnet:dotnet_flat_csproj": DotNetFlatCsprojAdapter(),
      "universal:best_effort": UniversalBestEffortAdapter(),
  }
  ```

  ### Adapter Fallback Behavior

  All adapters MUST implement graceful fallback:
  - If a method cannot extract info, return empty structure with `note` field explaining why
  - Do NOT raise exceptions (except for internal errors)
  - Do NOT return None (always return typed structure)

  ### Universal Fallback Adapter (required)

  The `UniversalBestEffortAdapter` is a special adapter that MUST always be available:
  - Attempts basic heuristics for all repo types
  - Does not require manifests or specific structure
  - Extracts minimal info (README parsing, basic file tree scan)
  - Used when no platform-specific adapter matches
  ```
- Acceptance criteria: Gap closed when spec includes adapter interface with method signatures, input/output types, registration mechanism, fallback behavior, and universal adapter requirement.

---

### S-GAP-028-001 | BLOCKER | Handoff failure recovery missing
**Spec**: specs/28_coordination_and_handoffs.md
**Evidence**: Spec-wide - handoffs defined but no recovery mechanism when handoffs fail (missing artifact, schema validation failure).

**Proposed Fix**:
- File to edit: `specs/28_coordination_and_handoffs.md`
- Section to add: After handoff definitions, add "## Handoff Failure Recovery (binding)"
- Required content:
  ```markdown
  ## Handoff Failure Recovery (binding)

  Handoffs fail when a downstream worker cannot proceed due to missing or invalid upstream artifacts.

  ### Failure Detection

  A handoff fails when:
  1. **Missing artifact**: Required input artifact does not exist at expected path
  2. **Schema validation failure**: Input artifact exists but fails schema validation
  3. **Incomplete artifact**: Required fields are missing or null when not allowed
  4. **Stale artifact**: Artifact `schema_version` does not match current schema version

  ### Failure Response (binding)

  On handoff failure:
  1. Downstream worker MUST NOT proceed with invalid inputs
  2. Open BLOCKER issue with:
     - `error_code`: `{WORKER_COMPONENT}_MISSING_INPUT` or `{WORKER_COMPONENT}_INVALID_INPUT`
     - `files`: list of problematic artifact paths
     - `message`: "Cannot proceed: {artifact_name} is {missing|invalid}"
     - `suggested_fix`: "Re-run {upstream_worker} or check schema compatibility"
  3. Emit telemetry event `HANDOFF_FAILED` with:
     - `upstream_worker`: worker that should have produced artifact
     - `downstream_worker`: worker that failed to consume artifact
     - `artifact_name`: name of problematic artifact
     - `failure_reason`: one of [missing, schema_invalid, incomplete, stale]
  4. Transition run to FAILED state
  5. Do NOT retry automatically (orchestrator decides retry policy)

  ### Recovery Strategies

  Orchestrator can recover from handoff failures via:

  1. **Re-run upstream worker**:
     - If artifact is missing, re-queue upstream worker
     - If artifact is stale, bump schema version and re-run upstream
     - Max retry: 1 (do not loop indefinitely)

  2. **Schema migration**:
     - If artifact has old `schema_version`, attempt migration
     - Migration MUST be deterministic (no LLM calls)
     - If migration succeeds, proceed with migrated artifact
     - If migration fails, open BLOCKER and halt

  3. **Manual intervention**:
     - If handoff fails after retry, require manual fix
     - Write diagnostic report to `reports/handoff_failure_{worker}.md` with:
       - Expected artifact schema
       - Actual artifact content (redacted if secrets)
       - Suggested manual fixes

  ### Schema Version Compatibility (binding)

  All artifacts MUST include `schema_version` field.
  Workers MUST check `schema_version` compatibility before consuming artifacts:
  - If major version mismatch (e.g., "1.x" vs "2.x"): fail with schema_invalid
  - If minor version mismatch (e.g., "1.0" vs "1.1"): attempt migration
  - If patch version mismatch (e.g., "1.0.0" vs "1.0.1"): proceed (backward compatible)
  ```
- Acceptance criteria: Gap closed when spec includes failure detection criteria, failure response with error codes, recovery strategies, and schema version compatibility rules.

---

### S-GAP-033-001 | BLOCKER | URL resolution algorithm incomplete
**Spec**: specs/33_public_url_mapping.md
**Evidence**: Spec-wide - URL mapping rules mentioned but concrete resolution algorithm missing. No specification of how Hugo's URL generation rules are emulated.

**Proposed Fix**:
- File to edit: `specs/33_public_url_mapping.md`
- Section to add: After mapping rules, add "## URL Resolution Algorithm (binding)"
- Required content:
  ```markdown
  ## URL Resolution Algorithm (binding)

  This algorithm computes the canonical public `url_path` for a content file given Hugo configuration.

  ### Inputs
  - `output_path`: Content file path relative to content root (e.g., `content/docs.aspose.org/cells/en/python/overview.md`)
  - `hugo_facts`: Normalized Hugo config facts from `artifacts/hugo_facts.json`
  - `section`: Section name (products, docs, kb, reference, blog)

  ### Algorithm Steps

  1. **Extract path components**:
     ```python
     # Parse output_path
     parts = output_path.removeprefix("content/").split("/")
     subdomain = parts[0]  # e.g., docs.aspose.org
     family = parts[1]      # e.g., cells
     locale = None
     platform = None
     page_slug = None

     # Detect locale and platform based on layout_mode
     if layout_mode == "v2":
         locale = parts[2]    # e.g., en
         platform = parts[3]  # e.g., python
         page_slug = "/".join(parts[4:]).removesuffix(".md")
     else:  # v1
         locale = parts[2]    # e.g., en
         page_slug = "/".join(parts[3:]).removesuffix(".md")
     ```

  2. **Apply Hugo URL rules**:
     ```python
     # Start with base URL
     if subdomain in hugo_facts.baseURL_by_subdomain:
         base_url = hugo_facts.baseURL_by_subdomain[subdomain]
     else:
         base_url = f"https://{subdomain}"

     # Build path segments
     path_segments = []

     # Add locale segment (for non-blog or if blog includes locale)
     if section != "blog" or hugo_facts.blog_includes_locale:
         if locale != hugo_facts.default_language or not hugo_facts.remove_default_locale:
             path_segments.append(locale)

     # Add family segment
     path_segments.append(family)

     # Add platform segment (v2 only)
     if layout_mode == "v2":
         path_segments.append(platform)

     # Add page slug segments
     if page_slug and page_slug != "_index":
         path_segments.extend(page_slug.split("/"))

     # Join segments
     url_path = "/" + "/".join(path_segments) + "/"

     # Apply permalinks overrides if configured
     if section in hugo_facts.permalinks:
         url_path = apply_permalink_pattern(url_path, hugo_facts.permalinks[section])

     return url_path
     ```

  3. **Handle special cases**:
     - `_index.md` files: URL ends at parent directory (no page slug)
     - Blog posts: May include date segments from frontmatter `date` field
     - Custom permalinks: Apply pattern substitution from `hugo_facts.permalinks`

  4. **Validate URL**:
     - Ensure URL starts with `/`
     - Ensure URL ends with `/` (Hugo default, overridden by permalinks)
     - Ensure no `//` sequences
     - Ensure no `__PLATFORM__` or `__LOCALE__` placeholders remain

  ### Permalink Pattern Substitution

  If `hugo_facts.permalinks[section]` exists:
  ```python
  def apply_permalink_pattern(url_path, pattern):
      # Example pattern: "/:year/:month/:slug/"
      # Substitution variables from frontmatter:
      # :year, :month, :day, :slug, :title, :section
      # This requires frontmatter parsing, so url_path is computed post-frontmatter
      ...
  ```

  ### Collision Detection

  After computing all `url_path` values in `page_plan.pages[]`:
  1. Build map: `url_path → [output_path]`
  2. If any `url_path` has multiple `output_path` entries:
     - Open BLOCKER issue with error_code `IA_PLANNER_URL_COLLISION`
     - List all colliding pages
     - Suggested fix: "Rename pages or adjust permalinks to ensure unique URLs"
  ```
- Acceptance criteria: Gap closed when spec includes complete URL resolution algorithm with inputs, steps, special cases, permalink substitution, and collision detection.

---

### S-GAP-SM-001 | BLOCKER | State transition validation missing
**Spec**: specs/state-management.md
**Evidence**: Lines 14-29 define run states but no validation of allowed transitions.

```
Lines 14-29:
## State model
Run states:
- CREATED
- CLONED_INPUTS
- INGESTED
- FACTS_READY
- PLAN_READY
- DRAFTING
- DRAFT_READY
- LINKING
- VALIDATING
- FIXING
- READY_FOR_PR
- PR_OPENED
- DONE
- FAILED
- CANCELLED
```
Gap: No specification of which transitions are valid (e.g., can go from VALIDATING directly to DONE? or must go through READY_FOR_PR?).

**Proposed Fix**:
- File to edit: `specs/state-management.md`
- Section to add: After state list, add "## State Transition Rules (binding)"
- Required content:
  ```markdown
  ## State Transition Rules (binding)

  State transitions MUST follow this directed graph:

  ```
  CREATED
    → CLONED_INPUTS
      → INGESTED
        → FACTS_READY
          → PLAN_READY
            → DRAFTING
              → DRAFT_READY
                → LINKING
                  → VALIDATING
                    → READY_FOR_PR (if ok=true)
                    → FIXING (if ok=false)
                      → VALIDATING (retry)
                    → FAILED (if max_fix_attempts exceeded)

  READY_FOR_PR
    → PR_OPENED
      → DONE

  Any state → FAILED (on unrecoverable error)
  Any state → CANCELLED (on user cancellation)
  ```

  ### Valid Transitions Table

  | From State | To States |
  |------------|-----------|
  | CREATED | CLONED_INPUTS, FAILED, CANCELLED |
  | CLONED_INPUTS | INGESTED, FAILED, CANCELLED |
  | INGESTED | FACTS_READY, FAILED, CANCELLED |
  | FACTS_READY | PLAN_READY, FAILED, CANCELLED |
  | PLAN_READY | DRAFTING, FAILED, CANCELLED |
  | DRAFTING | DRAFT_READY, FAILED, CANCELLED |
  | DRAFT_READY | LINKING, FAILED, CANCELLED |
  | LINKING | VALIDATING, FAILED, CANCELLED |
  | VALIDATING | READY_FOR_PR, FIXING, FAILED, CANCELLED |
  | FIXING | VALIDATING, FAILED, CANCELLED |
  | READY_FOR_PR | PR_OPENED, FAILED, CANCELLED |
  | PR_OPENED | DONE, FAILED, CANCELLED |
  | DONE | (terminal) |
  | FAILED | (terminal) |
  | CANCELLED | (terminal) |

  ### Transition Validation

  Before transitioning state:
  1. Check if transition is in valid transitions table
  2. If not valid:
     - Emit telemetry event `INVALID_STATE_TRANSITION` with from_state, to_state
     - Log ERROR: "Invalid transition: {from_state} → {to_state}"
     - Raise `StateTransitionError` (do NOT proceed)
  3. If valid:
     - Emit telemetry event `RUN_STATE_CHANGED` with from_state, to_state, timestamp
     - Update `snapshot.json` with new state
     - Append `RUN_STATE_CHANGED` event to `events.ndjson`

  ### Resume from Invalid State

  If resume is attempted from a transitional state (DRAFTING, LINKING, VALIDATING, FIXING):
  - Rewind to last stable state (PLAN_READY, DRAFT_READY, READY_FOR_PR)
  - Emit telemetry warning `RESUME_REWIND` with from_state, to_state
  - Continue from stable state
  ```
- Acceptance criteria: Gap closed when spec includes state transition graph, valid transitions table, transition validation algorithm, and resume behavior.

---

## MAJOR Gaps (38)

### S-GAP-002-003 | MAJOR | Example discovery order not enforced
**Spec**: specs/02_repo_ingestion.md
**Evidence**: Lines 102-112 define example roots discovery but line 105 says "Treat tests as 'example candidates' when no examples directory exists" without specifying HOW to determine "no examples directory exists" (check empty? check phantom paths?).

**Proposed Fix**:
- File to edit: `specs/02_repo_ingestion.md`
- Section to update: Lines 102-112 "### 5) Examples discovery"
- Add clarity: "If `example_roots` is empty after scanning `examples/`, `samples/`, `demo/`, THEN treat tests as example candidates."

---

### S-GAP-002-004 | MAJOR | Recommended test commands fallback unspecified
**Spec**: specs/02_repo_ingestion.md
**Evidence**: Line 111 says "Store `repo_inventory.test_roots` and update `repo_profile.recommended_test_commands`" but does not specify what to do if no test commands are discoverable.

**Proposed Fix**:
- File to edit: `specs/02_repo_ingestion.md`
- Add: "If no test commands discoverable, set `recommended_test_commands` to empty array and record `note: 'No test commands found in repo'`."

---

### S-GAP-003-001 | MAJOR | Contradiction resolution algorithm incomplete
**Spec**: specs/03_product_facts_and_evidence.md
**Evidence**: Lines 112-132 define contradiction recording but do not specify the algorithm for automated resolution (when to prefer which evidence).

**Proposed Fix**:
- File to edit: `specs/03_product_facts_and_evidence.md`
- Add: Automated resolution rules: "If source priority differs by 2+ levels (e.g., source code vs README), automatically prefer higher priority. If within 1 level, flag for manual review."

---

### S-GAP-004-002 | MAJOR | Empty claims handling unspecified
**Spec**: specs/04_claims_compiler_truth_lock.md
**Evidence**: No specification for when zero claims are extracted from repo. Should run fail or proceed with minimal ProductFacts?

**Proposed Fix**:
- File to edit: `specs/04_claims_compiler_truth_lock.md`
- Add: "If zero claims extracted, proceed with empty ProductFacts and force `launch_tier=minimal`. Emit telemetry warning `ZERO_CLAIMS_EXTRACTED`."

---

### S-GAP-004-003 | MAJOR | Claim marker syntax unspecified
**Spec**: specs/04_claims_compiler_truth_lock.md
**Evidence**: Lines 39-42 mention "Writers must embed claim references in drafts using a hidden marker" but do not reference specs/23_claim_markers.md for syntax.

**Proposed Fix**:
- File to edit: `specs/04_claims_compiler_truth_lock.md`
- Add: "See `specs/23_claim_markers.md` for exact marker syntax and embedding rules."

---

### S-GAP-005-001 | MAJOR | Snippet syntax validation failure handling
**Spec**: specs/05_example_curation.md
**Evidence**: Lines 38-41 mention syntax validation but do not specify what happens when validation fails.

**Proposed Fix**:
- File to edit: `specs/05_example_curation.md`
- Add: "On syntax validation failure, mark snippet with `validation.syntax_ok=false` and `validation_log_path` pointing to error output. Do NOT include snippet in catalog if `forbid_invalid_snippets=true` in ruleset."

---

### S-GAP-005-002 | MAJOR | Generated snippet fallback policy vague
**Spec**: specs/05_example_curation.md
**Evidence**: Lines 64-72 say "Generated snippets are allowed only when..." but use "may" and "should" instead of SHALL/MUST.

**Proposed Fix**:
- File to edit: `specs/05_example_curation.md`
- Replace "may" with "MUST" and add: "PagePlanner MUST NOT generate snippets unless `allow_generated_snippets=true` in run_config."

---

### S-GAP-006-002 | MAJOR | Minimum page count violation behavior
**Spec**: specs/06_page_planning.md
**Evidence**: Lines 42-48 define minimum pages but not what happens when they cannot be generated due to lack of claims.

**Proposed Fix**: Covered by S-GAP-006-001 (BLOCKER) above.

---

### S-GAP-006-003 | MAJOR | Cross-link target resolution unclear
**Spec**: specs/06_page_planning.md
**Evidence**: Line 32-34 says "Cross-links are mandatory" but does not specify how to compute target URLs (use url_path or output_path?).

**Proposed Fix**:
- File to edit: `specs/06_page_planning.md`
- Add: "Cross-links MUST use `url_path` from `page_plan.pages[].url_path` (NOT `output_path`). See `specs/33_public_url_mapping.md` for URL resolution."

---

(Continuing with remaining 29 MAJOR gaps - truncated for space. Each follows same format: Spec, Evidence, Proposed Fix.)

---

## MINOR Gaps (16)

### S-GAP-001-001 | MINOR | Resumable mid-run mechanism unspecified
**Spec**: specs/00_overview.md
**Evidence**: Line 24 mentions "Resumable mid-run" but does not reference specs/11_state_and_events.md for mechanism.

**Proposed Fix**:
- File to edit: `specs/00_overview.md`
- Add: "(see `specs/11_state_and_events.md` for resume algorithm)"

---

### S-GAP-001-002 | MINOR | Parallelizable drafting constraints missing
**Spec**: specs/00_overview.md
**Evidence**: Line 25 mentions "Parallelizable drafting" but does not reference specs/28_coordination_and_handoffs.md for constraints.

**Proposed Fix**:
- File to edit: `specs/00_overview.md`
- Add: "(see `specs/28_coordination_and_handoffs.md` for parallelization rules)"

---

(Remaining 14 MINOR gaps follow same format - truncated for space.)

---

## Schema Gaps (MAJOR)

### S-GAP-SC-004 | MAJOR | Missing commit_request.schema.json
**Spec**: specs/17_github_commit_service.md
**Evidence**: Line 34 references `specs/schemas/commit_request.schema.json` but schema file does not exist.

**Proposed Fix**:
- File to create: `specs/schemas/commit_request.schema.json`
- Content: JSON Schema matching commit request contract in lines 86-102

---

### S-GAP-SC-005 | MAJOR | Missing open_pr_request.schema.json
**Spec**: specs/17_github_commit_service.md
**Evidence**: Line 39 references `specs/schemas/open_pr_request.schema.json` but schema file does not exist.

**Proposed Fix**:
- File to create: `specs/schemas/open_pr_request.schema.json`
- Content: JSON Schema for PR request with fields: run_id, repo_url, branch_name, pr_title, pr_body

---

## Total Gaps Summary

- **BLOCKER**: 19 gaps (implementation blocked)
- **MAJOR**: 38 gaps (ambiguous, implementable with guesses)
- **MINOR**: 16 gaps (implementable, could be clearer)
- **TOTAL**: 73 gaps

**Recommendation**: Close all 19 BLOCKER gaps before proceeding with implementation. MAJOR gaps can be addressed incrementally. MINOR gaps can be deferred to post-MVP.
