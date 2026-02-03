# TC-955: Storage Model Spec Verification

## Metadata
- **Status**: Ready
- **Owner**: STORAGE_VERIFIER
- **Depends On**: TC-939
- **Created**: 2026-02-03
- **Updated**: 2026-02-03

## Problem Statement
**NOTE:** TC-939 already created [specs/40_storage_model.md](specs/40_storage_model.md) with comprehensive storage documentation. TC-955 is a verification taskcard to ensure the spec accurately reflects the current system and answers key questions about data storage and retrievability.

Users need clear answers to:
1. Where are repo facts/snippets/evidence stored? (Files vs DB)
2. What retention policy is required for production runs?
3. How to trace from generated pages back to source files?
4. What data is needed to reproduce a run deterministically?

## Acceptance Criteria
1. Review [specs/40_storage_model.md](specs/40_storage_model.md) for completeness
2. Verify the spec accurately documents:
   - All artifact locations (artifacts/*.json)
   - Event log and snapshot model
   - SQLite database scope (telemetry ONLY, not operational)
   - Retention policy (minimal 90 days, debugging 30 days, short-term 7 days)
   - Traceability procedures (forward and backward)
   - Debugging procedures for common scenarios
3. Test traceability procedures by following the documented chains:
   - Forward: source file → repo_inventory → evidence_map → page_plan → draft → site
   - Backward: generated page → page_plan → evidence_map → repo_inventory → source file
4. Verify retention requirements are feasible for pilots
5. Document any gaps or inaccuracies found

## Allowed Paths
- plans/taskcards/TC-955_storage_model_spec.md
- specs/40_storage_model.md (only if corrections needed)
- reports/agents/**/TC-955/**
- plans/taskcards/INDEX.md
- plans/taskcards/STATUS_BOARD.md

## Evidence Requirements
- reports/agents/<agent>/TC-955/report.md
- reports/agents/<agent>/TC-955/self_review.md
- reports/agents/<agent>/TC-955/spec_audit.txt (review findings)
- reports/agents/<agent>/TC-955/traceability_test.txt (manual trace of 1 page)

## Implementation Notes

### Current Storage Model (TC-939)
[specs/40_storage_model.md](specs/40_storage_model.md) already documents:

**File-Based Storage (Primary):**
- Run directory structure: `runs/<run_id>/`
- Event log: `events.ndjson` (source of truth)
- Snapshot: `snapshot.json` (materialized state)
- Artifacts: `artifacts/*.json` (schema-validated outputs)
- Drafts: `drafts/` (generated markdown)
- Reports: `reports/` (human-readable summaries)
- Logs: `logs/` (raw tool outputs)

**SQLite Database (Telemetry Only):**
- Location: `telemetry.db` (configurable)
- Purpose: Run history queries, metrics aggregation (NOT operational state)
- Tables: `runs`, `events`
- Critical: Workers MUST NOT depend on database for correctness

**Artifacts Registry:**
| Artifact | Producer | Purpose |
|----------|----------|---------|
| repo_inventory.json | W1 | Repo fingerprint, file inventory |
| product_facts.json | W2 | Extracted claims and facts |
| evidence_map.json | W2 | Claim → evidence mappings |
| snippet_catalog.json | W3 | Curated code snippets |
| page_plan.json | W4 | Page generation plan |
| patch_bundle.json | W6 | Content patches |
| validation_report.json | W7 | Validation gate results |
| pr.json | W9 | Pull request metadata (optional) |

**Retention Policy:**
- Minimal (90 days): run_config.yaml, events.ndjson, artifacts/*.json, work/repo/
- Debugging (30 days): snapshot.json, reports/, logs/
- Short-term (7 days): drafts/, work/site/, telemetry_outbox.jsonl

**Traceability:**
- Forward: source file → repo_inventory → evidence_map → page_plan → draft → site
- Backward: page → page_plan → evidence_map → repo_inventory → source

### Verification Checklist

**1. Spec Completeness:**
- [ ] All artifact files documented
- [ ] Database scope is clear (telemetry only)
- [ ] Retention policy is defined
- [ ] Traceability procedures are complete
- [ ] Debugging procedures cover common scenarios

**2. Accuracy Check:**
- [ ] Verify artifact paths match actual code
- [ ] Verify schemas exist for all documented artifacts
- [ ] Verify database schema matches implementation
- [ ] Spot-check one traceability example

**3. Pilot Readiness:**
- [ ] Retention requirements are feasible for pilots
- [ ] Evidence package approach is documented (evidence.zip)
- [ ] Deterministic reproduction is explained

### Traceability Test
Pick one generated page from a pilot run and manually trace:
1. Find page in content_preview (e.g., `getting-started.md`)
2. Look up in `page_plan.json` by output_path
3. Extract claim_ids from page context
4. Look up claims in `evidence_map.json`
5. Find source files in `repo_inventory.json`
6. Verify source files exist in `work/repo/`
7. Document each step with file paths and line numbers

### Questions to Answer
1. **Where are repo facts stored?**
   - Answer: `artifacts/product_facts.json` (W2 output)
   - Schema: `specs/schemas/product_facts.schema.json`

2. **Where are snippets stored?**
   - Answer: `artifacts/snippet_catalog.json` (W3 output)
   - Schema: `specs/schemas/snippet_catalog.schema.json`

3. **Where are evidence mappings stored?**
   - Answer: `artifacts/evidence_map.json` (W2 output)
   - Schema: `specs/schemas/evidence_map.schema.json`

4. **Is there a database?**
   - Answer: YES, SQLite at `telemetry.db`
   - Purpose: Telemetry and run history queries ONLY
   - NOT used for: Operational state, artifact storage, deterministic replay

5. **What's required for production runs?**
   - Retention: 90 days minimum (run_config, events, artifacts, work/repo)
   - Evidence package: ZIP archive for long-term storage
   - Traceability: Full chain from page → source must be intact

### If Gaps Found
If verification reveals missing information:
1. Document gaps in TC-955 report
2. Update specs/40_storage_model.md with corrections (within allowed paths)
3. Note any implementation mismatches for future taskcards

## Dependencies
- TC-939 (Storage Model Audit and Documentation - Done)

## Related Issues
- TC-952 (content preview export needed to test traceability)
- TC-935 (validation report determinism)

## Definition of Done
- [ ] specs/40_storage_model.md reviewed for completeness
- [ ] All key questions answered (facts, snippets, evidence, DB, retention)
- [ ] Traceability test completed for 1 page (forward and backward)
- [ ] Retention policy verified as feasible
- [ ] Spec audit findings documented
- [ ] Report and self-review written
