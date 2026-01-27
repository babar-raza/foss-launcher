# Trace Matrix: Specs → Schemas

**Pre-Implementation Verification Run**: 20260127-1518
**Source**: AGENT_C/TRACE.md
**Date**: 2026-01-27

---

## Summary

**Total Schemas**: 22
**Specs with Schemas**: 13/13 core specs (100%)
**Artifact Coverage**: 13/13 required artifacts (100%)

---

## Spec → Schema Mapping

| Spec Document | Schema File | Status | Evidence | Notes |
|---------------|-------------|--------|----------|-------|
| **specs/01_system_contract.md** | run_config.schema.json | ✅ | Lines 28-40 | Inputs, budgets, profiles |
| specs/01_system_contract.md | issue.schema.json | ✅ | Lines 86-140 | Error taxonomy |
| specs/01_system_contract.md | api_error.schema.json | ✅ | Lines 78-90 | Error handling |
| **specs/02_repo_ingestion.md** | repo_inventory.schema.json | ✅ | Lines 8-31 | Repo profiling |
| **specs/03_product_facts_and_evidence.md** | product_facts.schema.json | ✅ | Lines 12-37 | Required fields (20) |
| specs/03_product_facts_and_evidence.md | evidence_map.schema.json | ✅ | Lines 40-150 | Evidence priority |
| **specs/04_claims_compiler_truth_lock.md** | truth_lock_report.schema.json | ✅ | Referenced | Claim stability |
| **specs/05_example_curation.md** | snippet_catalog.schema.json | ✅ | Lines 6-21 | Snippet structure |
| **specs/06_page_planning.md** | page_plan.schema.json | ✅ | Lines 6-18 | Page spec fields |
| **specs/08_patch_engine.md** | patch_bundle.schema.json | ✅ | Lines 6-28 | Patch types |
| **specs/09_validation_gates.md** | validation_report.schema.json | ✅ | Lines 72-74, 162-167 | Profile-based gating |
| **specs/11_state_and_events.md** | event.schema.json | ✅ | Lines 63-73 | Event log fields |
| specs/11_state_and_events.md | snapshot.schema.json | ✅ | Lines 100-111 | Snapshot structure |
| **specs/12_pr_and_release.md** | pr.schema.json | ✅ | Lines 33-54 | Rollback contract (Guarantee L) |
| **specs/17_github_commit_service.md** | commit_request.schema.json | ✅ | Lines 32-36 | POST /v1/commit |
| specs/17_github_commit_service.md | commit_response.schema.json | ✅ | Lines 32-36 | Commit response |
| specs/17_github_commit_service.md | open_pr_request.schema.json | ✅ | Lines 37-40 | POST /v1/open_pr |
| specs/17_github_commit_service.md | open_pr_response.schema.json | ✅ | Lines 37-40 | PR response |
| specs/17_github_commit_service.md | api_error.schema.json | ✅ | Lines 42-43 | Error responses |
| **specs/18_site_repo_layout.md** | frontmatter_contract.schema.json | ✅ | — | Frontmatter discovery |
| **specs/20_rulesets_and_templates_registry.md** | ruleset.schema.json | ✅ | Lines 16-76 | Ruleset structure (4 required keys) |
| **specs/30_site_and_workflow_repos.md** | site_context.schema.json | ✅ | — | Site and workflow repo context |
| **specs/31_hugo_config_awareness.md** | hugo_facts.schema.json | ✅ | — | Hugo config facts extraction |

---

## Schema → Spec Reverse Mapping

| Schema File | Primary Spec | Status | Critical Fields Traced |
|-------------|--------------|--------|------------------------|
| **run_config.schema.json** | specs/01_system_contract.md:28-40 | ✅ | budgets (7 required), validation_profile, allow_manual_edits, platform layout |
| **validation_report.schema.json** | specs/09_validation_gates.md:72-74 | ✅ | profile, gates[], issues[], manual_edits tracking |
| **product_facts.schema.json** | specs/03_product_facts_and_evidence.md:12-37 | ✅ | 20 required fields, claim_groups (6 groups), supported_formats |
| **issue.schema.json** | specs/01_system_contract.md:86-140 | ✅ | error_code pattern, severity enum, conditional error_code (blocker/error) |
| **pr.schema.json** | specs/12_pr_and_release.md:33-54 | ✅ | Rollback metadata: base_ref (40-char SHA), rollback_steps, affected_paths |
| **ruleset.schema.json** | specs/20_rulesets_and_templates_registry.md:16-76 | ✅ | 4 required keys: style, truth, editing, sections (5 required) |

---

## Critical Field Traceability

### run_config.schema.json

| Spec Requirement | Schema Implementation | Evidence | Status |
|------------------|----------------------|----------|--------|
| Locale/locales mutual exclusivity | anyOf + allOf logic | run_config.schema.json:26-54 | ✅ |
| Budget constraints (7 required fields) | budgets object | run_config.schema.json:558-610 | ✅ |
| Platform-aware layout support | target_platform, layout_mode, path_patterns | run_config.schema.json:83-199 | ✅ |
| Validation profiles (local/ci/prod) | validation_profile enum | run_config.schema.json:457-468 | ✅ |
| Emergency manual edits mode | allow_manual_edits field | run_config.schema.json:452-456 | ✅ |

### validation_report.schema.json

| Spec Requirement | Schema Implementation | Evidence | Status |
|------------------|----------------------|----------|--------|
| Profile tracking | profile field (enum) | validation_report.schema.json:20-24 | ✅ |
| Manual edits tracking | manual_edits, manual_edited_files | validation_report.schema.json:53-89 | ✅ |
| Gates array structure | gates with name, ok, log_path | validation_report.schema.json:25-45 | ✅ |
| Issue references | issues array refs issue.schema.json | validation_report.schema.json:47-52 | ✅ |

### product_facts.schema.json

| Spec Requirement | Schema Implementation | Evidence | Status |
|------------------|----------------------|----------|--------|
| Required top-level fields (20) | All 20 in required array | product_facts.schema.json:6-20 | ✅ |
| Positioning (tagline, short_description) | positioning object with required fields | product_facts.schema.json:40-61 | ✅ |
| claim_groups (6 required groups) | All 6 sub-groups | product_facts.schema.json:75-123 | ✅ |
| Supported formats structure | status, claim_id, direction, support_level | product_facts.schema.json:125-169 | ✅ |

### issue.schema.json

| Spec Requirement | Schema Implementation | Evidence | Status |
|------------------|----------------------|----------|--------|
| Error taxonomy format | error_code pattern: ^[A-Z]+(_[A-Z]+)*$ | issue.schema.json:12-16 | ✅ |
| Severity levels | enum: info/warn/error/blocker | issue.schema.json:10 | ✅ |
| Status tracking | enum: OPEN/IN_PROGRESS/RESOLVED | issue.schema.json:27 | ✅ |
| Conditional error_code | Required for error/blocker | issue.schema.json:29-40 | ✅ |

### pr.schema.json

| Spec Requirement | Schema Implementation | Evidence | Status |
|------------------|----------------------|----------|--------|
| Rollback metadata (Guarantee L) | base_ref, rollback_steps, affected_paths | pr.schema.json:6 | ✅ |
| base_ref SHA format | 40-char hex pattern | pr.schema.json:16-22 | ✅ |
| Rollback steps array | Array with minItems:1 | pr.schema.json:23-30 | ✅ |
| Validation summary | validation_summary with profile | pr.schema.json:66-85 | ✅ |

### ruleset.schema.json

| Spec Requirement | Schema Implementation | Evidence | Status |
|------------------|----------------------|----------|--------|
| 4 required top-level keys | schema_version, style, truth, editing, sections | ruleset.schema.json:6 | ✅ |
| Style structure | tone, audience, forbid_marketing_superlatives | ruleset.schema.json:9-24 | ✅ |
| Truth structure | no_uncited_facts, forbid_inferred_formats | ruleset.schema.json:26-36 | ✅ |
| Editing structure | diff_only, forbid_full_rewrite_existing_files | ruleset.schema.json:37-46 | ✅ |
| Sections (5 required) | products, docs, reference, kb, blog | ruleset.schema.json:75-86 | ✅ |

---

## Artifact Coverage (from specs/01_system_contract.md:42-56)

| Required Artifact | Schema | Status |
|-------------------|--------|--------|
| repo_inventory.json | repo_inventory.schema.json | ✅ |
| frontmatter_contract.json | frontmatter_contract.schema.json | ✅ |
| site_context.json | site_context.schema.json | ✅ |
| product_facts.json | product_facts.schema.json | ✅ |
| evidence_map.json | evidence_map.schema.json | ✅ |
| truth_lock_report.json | truth_lock_report.schema.json | ✅ |
| snippet_catalog.json | snippet_catalog.schema.json | ✅ |
| page_plan.json | page_plan.schema.json | ✅ |
| patch_bundle.json | patch_bundle.schema.json | ✅ |
| validation_report.json | validation_report.schema.json | ✅ |
| events.ndjson | event.schema.json | ✅ |
| snapshot.json (resume) | snapshot.schema.json | ✅ |
| PR metadata | pr.schema.json | ✅ |

**Coverage**: 13/13 required artifacts have schemas (100%)

---

## Key Findings

### Strengths
1. **Complete coverage**: Every required artifact has a schema
2. **Clear traceability**: Every schema maps to at least one spec
3. **Strict validation**: All schemas use additionalProperties:false
4. **Constraint enforcement**: Patterns, enums, minLength enforced consistently
5. **Conditional logic**: Complex requirements (locale/locales, error_code, manual_edits) correctly implemented

### Minor Observations (Non-Blocking)
1. **Mixed $id conventions**: Some schemas use local IDs, others use full URLs
2. **Schema versioning inconsistency**: Some use `"const": "1.0"`, others allow free strings
3. **Description field usage**: Inconsistent across schemas

### No Gaps or Blockers
All schemas are production-ready.

---

**Evidence Source**: reports/pre_impl_verification/20260127-1518/agents/AGENT_C/TRACE.md, AGENT_C/REPORT.md
**Verification Method**: Spec cross-reference + schema file inspection
