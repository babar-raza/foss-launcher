# AGENT_S Gaps Report

**Run ID**: 20260127-1518
**Agent**: AGENT_S (Specs Quality Auditor)
**Date**: 2026-01-27

---

## Gap Format

| Field | Description |
|-------|-------------|
| Gap ID | Unique identifier (S-GAP-NNN) |
| Severity | BLOCKER / MAJOR / MINOR |
| Category | Completeness / Precision / Operational / Documentation |
| Description | What is missing or unclear |
| Evidence | Spec location and context |
| Proposed Fix | Actionable resolution |

---

## S-GAP-001 | MINOR | Operational

**Description**: Binary asset handling edge case underspecified when binary files are referenced in documentation but not in repo.

**Evidence**:
- `specs/02_repo_ingestion.md:155-163` - "Binary assets discovery" section
- Lines 159-162: "Ingestion MUST NOT send binary payloads to LLMs. Snippet extraction MUST skip binary files."
- Gap: What happens when docs claim binary samples exist (e.g., `testfiles/sample.one`) but file is not in repo (phantom path)?

**Impact**:
- RepoScout might not record binary phantom paths if detection only scans text files
- Could lead to broken snippet references in generated content

**Proposed Fix**:
1. Update `specs/02_repo_ingestion.md` phantom path detection (lines 90-128) to include binary file references
2. Add detection pattern: `\.(pdf|one|png|jpg|zip|tar\.gz|bin|exe)`
3. Update schema `repo_inventory.schema.json` to ensure `phantom_paths[]` can record binary file types
4. Add test case: docs mention `testfiles/sample.one` but file doesn't exist → record as phantom_path with note "binary_asset_claimed"

**Acceptance**: Phantom path detection includes binary file patterns and records them with binary_asset flag.

---

## S-GAP-002 | MINOR | Operational

**Description**: Gate execution order not fully deterministic when gates can run in parallel.

**Evidence**:
- `specs/09_validation_gates.md:170` - "Gate execution order is: schema → lint → hugo_config → content_layout_platform → hugo_build → links → snippets → truthlock → consistency"
- Gap: Spec states order but doesn't forbid parallelization for independent gates (schema, lint, snippets could run in parallel)
- `specs/19_toolchain_and_ci.md:293-294` - "SHOULD parallelize independent validation gates"

**Impact**:
- If parallel execution is allowed, deterministic ordering might be violated
- Telemetry event order could vary between runs

**Proposed Fix**:
1. Update `specs/09_validation_gates.md` to clarify:
   - Sequential gates (hugo_config MUST run before hugo_build, links MUST run after hugo_build)
   - Parallelizable gates (schema, lint, snippets CAN run in parallel if results are deterministically merged)
2. Add deterministic merging rule: When parallel gates complete, validation_report.issues[] MUST be sorted by stable ordering (specs/10_determinism_and_caching.md:44-48)
3. Update validation_report.schema.json to include gate_execution_order[] array recording actual execution order

**Acceptance**: Gate execution order is either fully sequential OR parallelizable with deterministic result merging.

---

## S-GAP-003 | MINOR | Documentation

**Description**: MCP tool schemas are referenced but not included in specs/24_mcp_tool_schemas.md.

**Evidence**:
- `specs/14_mcp_endpoints.md:43` - "All tools defined in specs/24_mcp_tool_schemas.md MUST be exposed"
- `specs/14_mcp_endpoints.md:82-94` - "Tool List" section lists 10 required tools
- `specs/24_mcp_tool_schemas.md` - File is referenced but no content provided (schema definitions missing)

**Impact**:
- Implementers cannot validate MCP tool arguments against schemas
- Tool invocation contract is incomplete (argument validation cannot be enforced)

**Proposed Fix**:
1. Create or complete `specs/24_mcp_tool_schemas.md` with JSON Schema definitions for each of 10 required MCP tools:
   - launch_run (input: run_config, output: run_id)
   - get_run_status (input: run_id, output: state + artifacts)
   - list_runs (input: filter?, output: runs[])
   - get_artifact (input: run_id + artifact_name, output: content + sha256)
   - validate_run (input: run_id, output: validation_report)
   - resume_run (input: run_id, output: state)
   - cancel_run (input: run_id, output: cancelled)
   - get_telemetry (input: run_id, output: telemetry events)
   - list_taskcards (output: taskcards[])
   - validate_taskcard (input: taskcard_path, output: validation result)
2. Add schemas to specs/schemas/ directory or inline in 24_mcp_tool_schemas.md
3. Update MCP server implementation to validate against these schemas

**Acceptance**: All 10 MCP tools have complete JSON Schema definitions in specs/24_mcp_tool_schemas.md.

---

## S-GAP-004 | MINOR | Operational

**Description**: Tool version mismatch handling has minor ambiguity - unclear if non-production profiles allow version drift.

**Evidence**:
- `specs/19_toolchain_and_ci.md:86-98` - "Verification Algorithm (binding)" section
- Lines 92-97: "If version mismatch: Emit BLOCKER issue with error_code GATE_TOOL_VERSION_MISMATCH"
- Gap: Doesn't specify if this applies to all profiles (local/ci/prod) or only prod/ci
- `specs/09_validation_gates.md:122-159` - Profile definitions don't clarify tool version strictness per profile

**Impact**:
- Local development might unnecessarily fail if developer has slightly different tool version
- Could slow down development iteration

**Proposed Fix**:
1. Update `specs/19_toolchain_and_ci.md` verification algorithm to specify profile-specific behavior:
   - **prod profile**: Tool version mismatch is BLOCKER (fail immediately)
   - **ci profile**: Tool version mismatch is BLOCKER (fail immediately)
   - **local profile**: Tool version mismatch is WARNING (log warning, proceed with caution flag)
2. Add `validation_report.tool_version_warnings[]` array for local profile to record version mismatches
3. Update toolchain.lock.yaml schema to include `strict_version_matching: true/false` per tool

**Acceptance**: Tool version mismatch behavior is profile-specific and clearly documented.

---

## S-GAP-005 | MINOR | Precision

**Description**: "Best effort" language in test command discovery creates ambiguity about required vs optional behavior.

**Evidence**:
- `specs/02_repo_ingestion.md:149-153` - "Test command discovery" section
- Line 152: "If no test commands are discoverable, set recommended_test_commands to empty array"
- Gap: "best effort" implies optional, but spec doesn't clarify if failure to discover tests is acceptable or should emit telemetry warning

**Impact**:
- Unclear if empty recommended_test_commands should reduce launch tier
- Inconsistent handling of repos without discoverable tests

**Proposed Fix**:
1. Update `specs/02_repo_ingestion.md:149-153` to clarify:
   - Test command discovery is "best effort" (non-blocking if fails)
   - If zero test commands found: set `recommended_test_commands = []` AND emit telemetry `TEST_DISCOVERY_COMPLETED` with count=0
   - If zero test commands found AND zero test_roots: set `repository_health.tests_present = false`
   - Launch tier SHOULD be reduced by one level when `tests_present == false` (per specs/06_page_planning.md:126)
2. Add explicit binding rule: "Test command discovery failure MUST NOT fail the run (W1 RepoScout completes successfully)"

**Acceptance**: Test command discovery behavior is explicit (best-effort + telemetry + tier reduction).

---

## S-GAP-006 | MINOR | Documentation

**Description**: Platform-aware layout mode resolution order could be clearer when V1 and V2 templates both exist.

**Evidence**:
- `specs/32_platform_aware_content_layout.md` - Referenced in specs but file not analyzed (not in provided spec list)
- `specs/29_project_repo_structure.md:67-86` - Mentions V1 and V2 layout detection
- Gap: If both V1 and V2 templates exist for a section, which takes precedence? Resolution order unclear.

**Impact**:
- Template selection might be non-deterministic if both layouts present
- Different runs could select different layout modes

**Proposed Fix**:
1. Update template selection logic in relevant spec (likely specs/07_section_templates.md or specs/32_platform_aware_content_layout.md) to specify precedence:
   - **Option A**: Always prefer V2 (platform-aware) if available, fall back to V1
   - **Option B**: Detect from site repo Hugo config (if config uses platform-aware content roots, use V2)
   - **Option C**: Explicit override in run_config (layout_mode: v1 | v2)
2. Add deterministic rule: "If multiple layout modes available, resolution order is: run_config override > site config detection > V2 preference > V1 fallback"
3. Emit telemetry `LAYOUT_MODE_SELECTED` with rationale

**Acceptance**: Layout mode resolution is deterministic with explicit precedence rules.

---

## S-GAP-007 | MAJOR | Operational

**Description**: Handoff failure recovery strategy incomplete for schema migration - migration algorithm not specified.

**Evidence**:
- `specs/28_coordination_and_handoffs.md:162-176` - "Recovery Strategies" section
- Lines 170-175: "Schema migration: If artifact has old schema_version, attempt migration. Migration MUST be deterministic (no LLM calls). If migration succeeds, proceed. If migration fails, open BLOCKER and halt."
- Gap: No migration algorithm specified. What transformations are applied? How is determinism ensured?
- `specs/28_coordination_and_handoffs.md:184-191` - Schema version compatibility rules mention migration but don't provide implementation

**Impact**:
- Workers cannot implement deterministic schema migration
- Schema version mismatches will always fail (blocking progress)
- No path to handle legitimate schema evolution

**Proposed Fix**:
1. Add new spec or section: `specs/schemas/migration_guide.md` OR add to `specs/schemas/README.md`
2. Define migration algorithm requirements:
   - **Migration registry**: Map of (from_version, to_version) → migration function
   - **Deterministic transformations**: Field renaming, default value insertion, type coercion rules
   - **Forbidden transformations**: No LLM calls, no network requests, no user input
   - **Validation**: Migrated artifact MUST validate against target schema
3. Add migration examples for common cases:
   - Adding optional field: Insert default value (e.g., `new_field: null`)
   - Renaming field: Copy old_field to new_field, delete old_field
   - Type change: Apply deterministic coercion (e.g., string to int if parseable, else fail)
4. Update `specs/28_coordination_and_handoffs.md:170-175` to reference migration guide
5. Add test requirement: "All schema migrations MUST have unit tests proving determinism"

**Acceptance**: Schema migration algorithm is fully specified with deterministic transformation rules and test requirements.

---

## Gap Summary

| Gap ID | Severity | Category | Status |
|--------|----------|----------|--------|
| S-GAP-001 | MINOR | Operational | Open |
| S-GAP-002 | MINOR | Operational | Open |
| S-GAP-003 | MINOR | Documentation | Open |
| S-GAP-004 | MINOR | Operational | Open |
| S-GAP-005 | MINOR | Precision | Open |
| S-GAP-006 | MINOR | Documentation | Open |
| S-GAP-007 | MAJOR | Operational | Open |

**Total Gaps**: 7 (1 MAJOR, 6 MINOR)

---

## Prioritization

### Immediate Action Required (Before Production)
- **S-GAP-007**: Schema migration algorithm must be specified to handle schema evolution

### Recommended for Implementation Phase
- S-GAP-001: Binary phantom path detection
- S-GAP-002: Gate execution order clarification
- S-GAP-003: MCP tool schemas documentation
- S-GAP-004: Tool version mismatch profile handling
- S-GAP-005: Test command discovery precision
- S-GAP-006: Layout mode resolution order

---

## Notes

All gaps identified have:
- Clear evidence from spec files
- Proposed actionable fixes
- Acceptance criteria for resolution

These gaps do not block pre-implementation verification PASS status, but SHOULD be addressed during implementation to ensure operational robustness.

---

**Generated**: 2026-01-27
**Agent**: AGENT_S (Specs Quality Auditor)
**Run**: 20260127-1518
