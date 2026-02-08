# TC-955 Storage Model Spec Verification - Plan

## Verification Approach

### 1. Spec Completeness Review (30 min)
**Objective:** Verify specs/40_storage_model.md accurately documents the storage model.

**Method:**
- Read entire spec document (771 lines)
- Check each section answers key questions:
  - Where are repo facts stored?
  - Where are snippets stored?
  - Where are evidence mappings stored?
  - Is there a database?
  - What's required for production?
- Compare spec against actual implementation observations
- Verify all artifact types are documented
- Check retention policy is clearly defined

### 2. Artifact Location Verification (20 min)
**Objective:** Confirm artifacts exist in expected locations with documented structure.

**Method:**
- Search for product_facts.json, snippet_catalog.json, evidence_map.json across runs
- Select most recent successful run: r_20260203T095219Z_launch_pilot-aspose-3d-foss-python_3711472_8d8661a_5e9522c5
- Read and sample each artifact file:
  - product_facts.json: Extract claims structure
  - evidence_map.json: Extract evidence mapping structure
  - snippet_catalog.json: Extract snippet structure
  - repo_inventory.json: Extract file inventory structure
  - page_plan.json: Extract page planning structure
- Document file sizes, schemas, and key fields
- Verify artifacts validate against documented schemas

### 3. Traceability Test (40 min)
**Objective:** Trace one page through the complete pipeline (backward trace).

**Test Case:** docs.aspose.org/3d/en/python/docs/getting-started.md

**Trace Steps:**
1. Find page in page_plan.json by output_path
2. Extract required_claim_ids from page entry
3. Look up claim in evidence_map.json
4. Find source file citations
5. Locate source file in repo_inventory.json
6. Verify source file exists in work/repo/
7. Document complete chain with file paths and line numbers

### 4. Database Scope Verification (15 min)
**Objective:** Verify SQLite database is telemetry-only.

**Method:**
- Confirm telemetry.db exists at root
- Review spec section on database (lines 250-367)
- Verify spec clearly states: "Used ONLY for Local Telemetry API"
- Document non-use cases (operational state, deterministic replay)
- Check spec includes schema documentation

### 5. Retention Policy Feasibility (15 min)
**Objective:** Verify 90-day retention policy is feasible for pilots.

**Method:**
- Review retention policy section (lines 517-594)
- Verify three-tier retention model:
  - Minimal (90 days): run_config, events, artifacts, work/repo
  - Debugging (30 days): snapshot, reports, logs
  - Short-term (7 days): drafts, work/site, telemetry_outbox
- Check evidence packaging is documented
- Assess feasibility based on pilot run sizes

### 6. Gap Analysis (10 min)
**Objective:** Identify any gaps or inaccuracies in spec.

**Method:**
- Compare spec against actual file structure
- Check for missing artifact types
- Verify all schemas are referenced
- Note any discrepancies between spec and reality

## Success Criteria

- All 5 key questions answered correctly
- Artifact locations verified with file paths
- Complete traceability chain documented
- Database scope confirmed as telemetry-only
- Retention policy verified as feasible
- Any gaps documented

## Estimated Time
Total: 2 hours

## Dependencies
- specs/40_storage_model.md (exists, 771 lines)
- Recent successful run directories (exist)
- Artifact files (exist in multiple runs)

## Risk Mitigation
- If artifacts don't exist: Document expected locations based on spec
- If database unavailable: Reference spec schema documentation
- If traceability incomplete: Document partial chain with notes
