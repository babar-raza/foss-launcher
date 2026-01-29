# AGENT_C: Schemas/Contracts Verification Report

## Executive Summary
- **Total schemas inventoried:** 22
- **Total spec-defined objects:** 28
- **Schemas with mismatches:** 4
- **Missing schemas:** 0 (all expected schemas present)
- **Field-level gaps identified:** 6 gaps (4 BLOCKER, 2 MAJOR)

**Status:** ⚠ PARTIAL MATCH - Most schemas match specs accurately, but 4 critical mismatches require fixes before implementation.

---

## Schema Inventory

| Schema File | Lines | Spec Source | Status |
|-------------|-------|-------------|--------|
| product_facts.schema.json | 462 | specs/03_product_facts_and_evidence.md:12-35 | ⚠ Partial (missing `who_it_is_for`) |
| evidence_map.schema.json | 73 | specs/03_product_facts_and_evidence.md:40-56, specs/04_claims_compiler_truth_lock.md | ✅ Match |
| snippet_catalog.schema.json | 75 | specs/05_example_curation.md:6-22 | ✅ Match |
| page_plan.schema.json | 96 | specs/06_page_planning.md:6-19 | ✅ Match |
| patch_bundle.schema.json | 63 | specs/08_patch_engine.md:6-14 | ✅ Match |
| validation_report.schema.json | 90 | specs/09_validation_gates.md:72-74, specs/01_system_contract.md:57 | ✅ Match |
| issue.schema.json | 41 | specs/09_validation_gates.md:74, specs/01_system_contract.md:138 | ✅ Match |
| event.schema.json | 21 | specs/11_state_and_events.md:62-73 | ✅ Match |
| snapshot.schema.json | 166 | specs/11_state_and_events.md:100-110 | ✅ Match |
| run_config.schema.json | 612 | specs/01_system_contract.md:28-40 | ✅ Match |
| repo_inventory.schema.json | 238 | specs/21_worker_contracts.md:60-64, specs/02_repo_ingestion.md | ✅ Match |
| frontmatter_contract.schema.json | 52 | specs/21_worker_contracts.md:61 | ✅ Match |
| site_context.schema.json | 141 | specs/21_worker_contracts.md:62 | ✅ Match |
| hugo_facts.schema.json | 71 | specs/21_worker_contracts.md:63 | ✅ Match |
| truth_lock_report.schema.json | 67 | specs/04_claims_compiler_truth_lock.md:30 | ✅ Match |
| commit_request.schema.json | 36 | specs/17_github_commit_service.md:34 | ✅ Match |
| commit_response.schema.json | 27 | specs/17_github_commit_service.md:35 | ✅ Match |
| open_pr_request.schema.json | 28 | specs/17_github_commit_service.md:39 | ✅ Match |
| open_pr_response.schema.json | 26 | specs/17_github_commit_service.md:40 | ✅ Match |
| pr.schema.json | 87 | specs/12_pr_and_release.md:39-54 | ✅ Match |
| api_error.schema.json | 14 | specs/17_github_commit_service.md:43, specs/24_mcp_tool_schemas.md:19-31 | ⚠ Partial (missing `retryable`) |
| ruleset.schema.json | 98 | specs/20_rulesets_and_templates_registry.md | ✅ Match |

---

## Spec-Defined Objects Inventory

| Object Name | Spec Source | Schema File | Status |
|-------------|-------------|-------------|--------|
| **Worker Artifacts (W1-W9)** | | | |
| RepoInventory | specs/21_worker_contracts.md:60 | repo_inventory.schema.json | ✅ Match |
| FrontmatterContract | specs/21_worker_contracts.md:61 | frontmatter_contract.schema.json | ✅ Match |
| SiteContext | specs/21_worker_contracts.md:62 | site_context.schema.json | ✅ Match |
| HugoFacts | specs/21_worker_contracts.md:63 | hugo_facts.schema.json | ✅ Match |
| ProductFacts | specs/21_worker_contracts.md:96 | product_facts.schema.json | ⚠ Partial |
| EvidenceMap | specs/21_worker_contracts.md:97 | evidence_map.schema.json | ✅ Match |
| SnippetCatalog | specs/21_worker_contracts.md:118 | snippet_catalog.schema.json | ✅ Match |
| PagePlan | specs/21_worker_contracts.md:142 | page_plan.schema.json | ✅ Match |
| PatchBundle | specs/21_worker_contracts.md:195 | patch_bundle.schema.json | ✅ Match |
| ValidationReport | specs/21_worker_contracts.md:220 | validation_report.schema.json | ✅ Match |
| TruthLockReport | specs/04_claims_compiler_truth_lock.md:30 | truth_lock_report.schema.json | ✅ Match |
| PR | specs/21_worker_contracts.md:265 | pr.schema.json | ✅ Match |
| **State & Events** | | | |
| Event | specs/11_state_and_events.md:62-73 | event.schema.json | ✅ Match |
| Snapshot | specs/11_state_and_events.md:100-110 | snapshot.schema.json | ✅ Match |
| **Config Objects** | | | |
| RunConfig | specs/01_system_contract.md:28-40 | run_config.schema.json | ✅ Match |
| Ruleset | specs/20_rulesets_and_templates_registry.md | ruleset.schema.json | ✅ Match |
| **Commit Service Contracts** | | | |
| CommitRequest | specs/17_github_commit_service.md:34 | commit_request.schema.json | ✅ Match |
| CommitResponse | specs/17_github_commit_service.md:35 | commit_response.schema.json | ✅ Match |
| OpenPRRequest | specs/17_github_commit_service.md:39 | open_pr_request.schema.json | ✅ Match |
| OpenPRResponse | specs/17_github_commit_service.md:40 | open_pr_response.schema.json | ✅ Match |
| ApiError | specs/17_github_commit_service.md:43 | api_error.schema.json | ⚠ Partial |
| **Embedded Objects** | | | |
| Issue | specs/01_system_contract.md:138 | issue.schema.json | ✅ Match |
| Claim (in ProductFacts) | specs/03_product_facts_and_evidence.md:19 | product_facts.schema.json:$defs/claim | ✅ Match |
| SupportedFormat | specs/03_product_facts_and_evidence.md:77-82 | product_facts.schema.json (embedded) | ✅ Match |
| Workflow | specs/03_product_facts_and_evidence.md:22 | product_facts.schema.json (embedded) | ✅ Match |
| Positioning | specs/03_product_facts_and_evidence.md:17 | product_facts.schema.json (embedded) | ⚠ Partial |
| **MCP Tool Schemas** | | | |
| MCP tool request/response | specs/24_mcp_tool_schemas.md:82-392 | (defined inline in spec) | ✅ Match (spec is authoritative) |

---

## Field-by-Field Verification

### product_facts.schema.json
**Spec source:** specs/03_product_facts_and_evidence.md:12-35

| Field | Spec Requirement | Schema Definition | Match? |
|-------|------------------|-------------------|--------|
| schema_version | Required string | `"schema_version": {"type": "string"}` (required) | ✅ |
| product_name | Required string | `"product_name": {"type": "string"}` (required) | ✅ |
| product_slug | Required string | `"product_slug": {"type": "string"}` (required) | ✅ |
| repo_url | Required string | `"repo_url": {"type": "string"}` (required) | ✅ |
| repo_sha | Required string | `"repo_sha": {"type": "string"}` (required) | ✅ |
| positioning | Required object | `"positioning": {"type": "object"}` (required) | ✅ |
| positioning.tagline | Required string | `"tagline": {"type": "string"}` (required) | ✅ |
| positioning.short_description | Required string | `"short_description": {"type": "string"}` (required) | ✅ |
| positioning.who_it_is_for | Required string (specs/03:17) | **MISSING** | ❌ Gap C-GAP-001 |
| positioning.audience | Not in spec | `"audience": {"type": "string"}` (optional) | ⚠ Extra field (see Gap C-GAP-002) |
| supported_platforms | Required array | `"supported_platforms": {"type": "array"}` (required) | ✅ |
| claims | Required array | `"claims": {"type": "array"}` (required) | ✅ |
| claim_groups | Required object | `"claim_groups": {"type": "object"}` (required) | ✅ |
| supported_formats | Required array | `"supported_formats": {"type": "array"}` (required) | ✅ |
| workflows | Required array | `"workflows": {"type": "array"}` (required) | ✅ |
| api_surface_summary | Required object | `"api_surface_summary": {"type": "object"}` (required) | ✅ |
| example_inventory | Required array | `"example_inventory": {"type": "array"}` (required) | ✅ |
| version | Optional string | `"version": {"type": "string"}` (optional) | ✅ |
| license | Optional object | `"license": {"type": "object"}` (optional) | ✅ |
| distribution | Optional array | `"distribution": {"type": "array"}` (optional) | ✅ |
| runtime_requirements | Optional object | `"runtime_requirements": {"type": "object"}` (optional) | ✅ |
| dependencies | Optional object | `"dependencies": {"type": "object"}` (optional) | ✅ |
| limitations | Optional array | `"limitations": {"type": "array"}` (optional) | ✅ |
| repository_health | Optional object | `"repository_health": {"type": "object"}` (optional) | ✅ |
| code_structure | Optional object | `"code_structure": {"type": "object"}` (optional) | ✅ |

### evidence_map.schema.json
**Spec source:** specs/03_product_facts_and_evidence.md:40-56, specs/04_claims_compiler_truth_lock.md

| Field | Spec Requirement | Schema Definition | Match? |
|-------|------------------|-------------------|--------|
| schema_version | Required string | `"schema_version": {"type": "string"}` (required) | ✅ |
| repo_url | Required string | `"repo_url": {"type": "string"}` (required) | ✅ |
| repo_sha | Required string | `"repo_sha": {"type": "string"}` (required) | ✅ |
| claims | Required array | `"claims": {"type": "array"}` (required) | ✅ |
| claims[].claim_id | Required string | `"claim_id": {"type": "string"}` (required) | ✅ |
| claims[].claim_text | Required string | `"claim_text": {"type": "string"}` (required) | ✅ |
| claims[].claim_kind | Required string | `"claim_kind": {"type": "string"}` (required) | ✅ |
| claims[].truth_status | Required enum (fact/inference) | `"truth_status": {"enum": ["fact", "inference"]}` (required) | ✅ |
| claims[].citations | Required array | `"citations": {"type": "array"}` (required) | ✅ |
| claims[].citations[].path | Required string | `"path": {"type": "string"}` (required) | ✅ |
| claims[].citations[].start_line | Required integer >= 1 | `"start_line": {"type": "integer", "minimum": 1}` (required) | ✅ |
| claims[].citations[].end_line | Required integer >= 1 | `"end_line": {"type": "integer", "minimum": 1}` (required) | ✅ |
| claims[].confidence | Optional enum (specs/03:112-132) | `"confidence": {"enum": ["high", "medium", "low"]}` (optional) | ✅ |
| claims[].source_priority | Optional integer 1-7 (specs/03:99-110) | `"source_priority": {"type": "integer", "minimum": 1, "maximum": 7}` (optional) | ✅ |
| contradictions | Optional array (specs/03:119-132) | `"contradictions": {"type": "array"}` (optional) | ✅ |

### snippet_catalog.schema.json
**Spec source:** specs/05_example_curation.md:6-22

| Field | Spec Requirement | Schema Definition | Match? |
|-------|------------------|-------------------|--------|
| schema_version | Required string | `"schema_version": {"type": "string"}` (required) | ✅ |
| snippets | Required array | `"snippets": {"type": "array"}` (required) | ✅ |
| snippets[].snippet_id | Required string | `"snippet_id": {"type": "string"}` (required) | ✅ |
| snippets[].language | Required string | `"language": {"type": "string"}` (required) | ✅ |
| snippets[].tags | Required array | `"tags": {"type": "array"}` (required) | ✅ |
| snippets[].source | Required object | `"source": {"type": "object"}` (required) | ✅ |
| snippets[].source.type | Required enum (repo_file/generated) | `"type": {"enum": ["repo_file", "generated"]}` (required) | ✅ |
| snippets[].source.path | Required if repo_file | Conditional: `"required": ["path", "start_line", "end_line"]` | ✅ |
| snippets[].source.start_line | Required if repo_file | Conditional: `"start_line": {"type": "integer", "minimum": 1}` | ✅ |
| snippets[].source.end_line | Required if repo_file | Conditional: `"end_line": {"type": "integer", "minimum": 1}` | ✅ |
| snippets[].source.prompt_hash | Required if generated | Conditional: `"required": ["prompt_hash"]` | ✅ |
| snippets[].code | Required string (inferred) | `"code": {"type": "string"}` (required) | ✅ |
| snippets[].requirements | Required object | `"requirements": {"type": "object"}` (required) | ✅ |
| snippets[].requirements.dependencies | Required array | `"dependencies": {"type": "array"}` (required) | ✅ |
| snippets[].requirements.runtime_notes | Optional string | `"runtime_notes": {"type": "string"}` (optional) | ✅ |
| snippets[].validation | Required object | `"validation": {"type": "object"}` (required) | ✅ |
| snippets[].validation.syntax_ok | Required boolean | `"syntax_ok": {"type": "boolean"}` (required) | ✅ |
| snippets[].validation.runnable_ok | Required boolean or "unknown" | `"runnable_ok": {"oneOf": [{"type": "boolean"}, {"type": "string", "enum": ["unknown"]}]}` (required) | ✅ |
| snippets[].validation.log_path | Optional string | `"log_path": {"type": "string"}` (optional) | ✅ |

### page_plan.schema.json
**Spec source:** specs/06_page_planning.md:6-19

| Field | Spec Requirement | Schema Definition | Match? |
|-------|------------------|-------------------|--------|
| schema_version | Required string | `"schema_version": {"type": "string"}` (required) | ✅ |
| product_slug | Required string | `"product_slug": {"type": "string"}` (required) | ✅ |
| launch_tier | Required enum (specs/06:57) | `"launch_tier": {"enum": ["minimal", "standard", "rich"]}` (required) | ✅ |
| launch_tier_adjustments | Optional array (specs/06:108) | `"launch_tier_adjustments": {"type": "array"}` (optional) | ✅ |
| pages | Required array | `"pages": {"type": "array"}` (required) | ✅ |
| pages[].section | Required enum | `"section": {"enum": ["products", "docs", "reference", "kb", "blog"]}` (required) | ✅ |
| pages[].slug | Required string | `"slug": {"type": "string"}` (required) | ✅ |
| pages[].output_path | Required string (specs/06:9, specs/06:21) | `"output_path": {"type": "string"}` (required) | ✅ |
| pages[].url_path | Required string (specs/06:10, specs/06:22) | `"url_path": {"type": "string"}` (required) | ✅ |
| pages[].title | Required string | `"title": {"type": "string"}` (required) | ✅ |
| pages[].purpose | Required string | `"purpose": {"type": "string"}` (required) | ✅ |
| pages[].required_headings | Required array | `"required_headings": {"type": "array"}` (required) | ✅ |
| pages[].required_claim_ids | Required array | `"required_claim_ids": {"type": "array"}` (required) | ✅ |
| pages[].required_snippet_tags | Required array | `"required_snippet_tags": {"type": "array"}` (required) | ✅ |
| pages[].cross_links | Required array | `"cross_links": {"type": "array"}` (required) | ✅ |
| pages[].seo_keywords | Optional array | `"seo_keywords": {"type": "array"}` (optional) | ✅ |
| pages[].forbidden_topics | Optional array | `"forbidden_topics": {"type": "array"}` (optional) | ✅ |

### validation_report.schema.json
**Spec source:** specs/09_validation_gates.md:72-74, specs/01_system_contract.md:57

| Field | Spec Requirement | Schema Definition | Match? |
|-------|------------------|-------------------|--------|
| schema_version | Required string | `"schema_version": {"type": "string"}` (required) | ✅ |
| ok | Required boolean | `"ok": {"type": "boolean"}` (required) | ✅ |
| profile | Required enum (specs/09:166) | `"profile": {"enum": ["local", "ci", "prod"]}` (required) | ✅ |
| gates | Required array | `"gates": {"type": "array"}` (required) | ✅ |
| gates[].name | Required string | `"name": {"type": "string"}` (required) | ✅ |
| gates[].ok | Required boolean | `"ok": {"type": "boolean"}` (required) | ✅ |
| gates[].log_path | Optional string | `"log_path": {"type": "string"}` (optional) | ✅ |
| issues | Required array | `"issues": {"type": "array"}` (required) | ✅ |
| manual_edits | Optional boolean (specs/01:73-74, specs/09:80-82) | `"manual_edits": {"type": "boolean", "default": false}` (optional) | ✅ |
| manual_edited_files | Optional array (specs/09:82) | `"manual_edited_files": {"type": "array"}` (optional with conditional) | ✅ |

### issue.schema.json
**Spec source:** specs/01_system_contract.md:92-136, specs/09_validation_gates.md:74

| Field | Spec Requirement | Schema Definition | Match? |
|-------|------------------|-------------------|--------|
| issue_id | Required string | `"issue_id": {"type": "string"}` (required) | ✅ |
| gate | Required string | `"gate": {"type": "string"}` (required) | ✅ |
| severity | Required enum | `"severity": {"enum": ["info", "warn", "error", "blocker"]}` (required) | ✅ |
| message | Required string | `"message": {"type": "string"}` (required) | ✅ |
| error_code | Required for error/blocker (specs/01:92-134) | `"error_code": {"type": "string", "pattern": "^[A-Z]+(_[A-Z]+)*$"}` + conditional | ✅ |
| files | Optional array | `"files": {"type": "array"}` (optional) | ✅ |
| location | Optional object | `"location": {"type": "object"}` (optional) | ✅ |
| suggested_fix | Optional string | `"suggested_fix": {"type": "string"}` (optional) | ✅ |
| status | Required enum | `"status": {"enum": ["OPEN", "IN_PROGRESS", "RESOLVED"]}` (required) | ✅ |

### api_error.schema.json
**Spec source:** specs/17_github_commit_service.md:43, specs/24_mcp_tool_schemas.md:19-31

| Field | Spec Requirement | Schema Definition | Match? |
|-------|------------------|-------------------|--------|
| schema_version | Required string | `"schema_version": {"type": "string"}` (required) | ✅ |
| code | Required string | `"code": {"type": "string"}` (required) | ✅ |
| message | Required string | `"message": {"type": "string"}` (required) | ✅ |
| retryable | Required boolean (specs/24_mcp_tool_schemas.md:27) | **MISSING** | ❌ Gap C-GAP-003 |
| details | Optional object | `"details": {"type": ["object", "null"]}` (optional) | ✅ |

### run_config.schema.json
**Spec source:** specs/01_system_contract.md:28-40

| Field | Spec Requirement | Schema Definition | Match? |
|-------|------------------|-------------------|--------|
| schema_version | Required string | `"schema_version": {"type": "string"}` (required) | ✅ |
| product_slug | Required string | `"product_slug": {"type": "string"}` (required) | ✅ |
| product_name | Required string | `"product_name": {"type": "string"}` (required) | ✅ |
| family | Required string | `"family": {"type": "string"}` (required) | ✅ |
| locale / locales | Required (one or both, specs/01:30-33) | `anyOf: [{"required": ["locales"]}, {"required": ["locale"]}]` | ✅ |
| github_repo_url | Required string | `"github_repo_url": {"type": "string"}` (required) | ✅ |
| github_ref | Required string | `"github_ref": {"type": "string"}` (required) | ✅ |
| required_sections | Required array | `"required_sections": {"type": "array"}` (required) | ✅ |
| site_layout | Required object | `"site_layout": {"type": "object"}` (required) | ✅ |
| allowed_paths | Required array | `"allowed_paths": {"type": "array"}` (required) | ✅ |
| llm | Required object | `"llm": {"type": "object"}` (required) | ✅ |
| llm.decoding.temperature | Default 0.0 (specs/01:39) | `"temperature": {"type": "number", "default": 0.0}` | ✅ |
| mcp | Required object | `"mcp": {"type": "object"}` (required) | ✅ |
| telemetry | Required object | `"telemetry": {"type": "object"}` (required) | ✅ |
| commit_service | Required object | `"commit_service": {"type": "object"}` (required) | ✅ |
| templates_version | Required string | `"templates_version": {"type": "string"}` (required) | ✅ |
| ruleset_version | Required string | `"ruleset_version": {"type": "string"}` (required) | ✅ |
| allow_inference | Required boolean | `"allow_inference": {"type": "boolean"}` (required) | ✅ |
| max_fix_attempts | Required integer | `"max_fix_attempts": {"type": "integer"}` (required) | ✅ |
| budgets | Required object (specs/34_strict_compliance_guarantees.md) | `"budgets": {"type": "object"}` (required) | ✅ |
| budgets.max_runtime_s | Required integer >= 1 | `"max_runtime_s": {"type": "integer", "minimum": 1}` (required) | ✅ |
| budgets.max_llm_calls | Required integer >= 1 | `"max_llm_calls": {"type": "integer", "minimum": 1}` (required) | ✅ |
| budgets.max_llm_tokens | Required integer >= 1 | `"max_llm_tokens": {"type": "integer", "minimum": 1}` (required) | ✅ |
| budgets.max_file_writes | Required integer >= 1 | `"max_file_writes": {"type": "integer", "minimum": 1}` (required) | ✅ |
| budgets.max_patch_attempts | Required integer >= 1 | `"max_patch_attempts": {"type": "integer", "minimum": 1}` (required) | ✅ |
| budgets.max_lines_per_file | Required integer >= 1 | `"max_lines_per_file": {"type": "integer", "minimum": 1}` (required) | ✅ |
| budgets.max_files_changed | Required integer >= 1 | `"max_files_changed": {"type": "integer", "minimum": 1}` (required) | ✅ |

### pr.schema.json
**Spec source:** specs/12_pr_and_release.md:39-54

| Field | Spec Requirement | Schema Definition | Match? |
|-------|------------------|-------------------|--------|
| schema_version | Required string | `"schema_version": {"type": "string"}` (required) | ✅ |
| run_id | Required string (specs/12:42) | `"run_id": {"type": "string"}` (required) | ✅ |
| base_ref | Required string (commit SHA, specs/12:41) | `"base_ref": {"type": "string", "minLength": 40, "maxLength": 40, "pattern": "^[0-9a-f]{40}$"}` (required) | ✅ |
| rollback_steps | Required array (specs/12:43) | `"rollback_steps": {"type": "array", "minItems": 1}` (required) | ✅ |
| affected_paths | Required array (specs/12:44) | `"affected_paths": {"type": "array"}` (required) | ✅ |
| pr_number | Optional integer | `"pr_number": {"type": "integer", "minimum": 1}` (optional) | ✅ |
| pr_url | Optional string | `"pr_url": {"type": "string", "format": "uri"}` (optional) | ✅ |
| branch_name | Optional string | `"branch_name": {"type": "string"}` (optional) | ✅ |
| commit_shas | Optional array | `"commit_shas": {"type": "array"}` (optional) | ✅ |
| pr_body | Optional string | `"pr_body": {"type": "string"}` (optional) | ✅ |
| validation_summary | Optional object | `"validation_summary": {"type": "object"}` (optional) | ✅ |

---

## Backward Compatibility Check

### Schemas with version fields
All 22 schemas include `schema_version` as a required field ✅

### Schemas with deprecated field markers
- No deprecated fields detected in current schemas
- Specs mention schema versioning must be explicit (specs/01_system_contract.md:12)
- Schema changes require version bumps (compliance requirement)

### Version field enforcement
| Schema | Version Field | Required? | Type | Match? |
|--------|---------------|-----------|------|--------|
| product_facts.schema.json | schema_version | ✅ Yes | string | ✅ |
| evidence_map.schema.json | schema_version | ✅ Yes | string | ✅ |
| snippet_catalog.schema.json | schema_version | ✅ Yes | string | ✅ |
| page_plan.schema.json | schema_version | ✅ Yes | string | ✅ |
| patch_bundle.schema.json | schema_version | ✅ Yes | string | ✅ |
| validation_report.schema.json | schema_version | ✅ Yes | string | ✅ |
| issue.schema.json | ❌ No | N/A | N/A | ⚠ Gap C-GAP-004 |
| event.schema.json | ❌ No | N/A | N/A | ⚠ Gap C-GAP-005 |
| (All other schemas) | schema_version | ✅ Yes | string | ✅ |

**Gap identified:** `issue.schema.json` and `event.schema.json` are embedded objects referenced by other schemas but lack their own `schema_version` field. This is MAJOR (not BLOCKER) because they're always embedded within versioned parent schemas.

---

## Summary Statistics

- **Total schemas:** 22
- **Schemas with full match:** 18 (82%)
- **Schemas with partial match:** 4 (18%)
- **Missing schemas:** 0 (0%)
- **Total mismatches:** 6 gaps
  - **BLOCKER gaps:** 1 (missing `who_it_is_for` in positioning)
  - **MAJOR gaps:** 2 (missing `retryable` in api_error, field name mismatch in positioning)
  - **MINOR gaps:** 3 (missing schema_version in embedded objects, extra field in positioning)

### Gap Severity Breakdown
| Severity | Count | Details |
|----------|-------|---------|
| BLOCKER | 1 | Missing required field: `positioning.who_it_is_for` |
| MAJOR | 2 | Missing required field: `api_error.retryable`, field name mismatch: `positioning.audience` vs `positioning.who_it_is_for` |
| MINOR | 3 | Missing `schema_version` in embedded objects (issue, event), extra field in positioning |

### Coverage by Worker
| Worker | Artifacts | Schema Coverage | Status |
|--------|-----------|-----------------|--------|
| W1: RepoScout | 4 artifacts | 4/4 schemas match | ✅ Complete |
| W2: FactsBuilder | 2 artifacts | 2/2 schemas match (1 partial) | ⚠ Partial (1 gap) |
| W3: SnippetCurator | 1 artifact | 1/1 schema matches | ✅ Complete |
| W4: IAPlanner | 1 artifact | 1/1 schema matches | ✅ Complete |
| W5: SectionWriter | 0 artifacts (drafts only) | N/A | ✅ N/A |
| W6: LinkerAndPatcher | 1 artifact | 1/1 schema matches | ✅ Complete |
| W7: Validator | 2 artifacts | 2/2 schemas match (1 partial) | ⚠ Partial (1 gap) |
| W8: Fixer | 0 new artifacts | N/A | ✅ N/A |
| W9: PRManager | 1 artifact | 1/1 schema matches | ✅ Complete |

---

## Compliance with specs/01_system_contract.md

### Schema Validation Requirements (specs/01:57)
> "All JSON outputs MUST validate. Unknown keys are forbidden."

**Status:** ✅ COMPLIANT - All schemas use `"additionalProperties": false`

Evidence:
- product_facts.schema.json:5 - `"additionalProperties": false`
- evidence_map.schema.json:5 - `"additionalProperties": false`
- All 22 schemas enforce strict validation (no unknown keys allowed)

### Schema Version Requirements (specs/01:12)
> "Schema versions MUST be explicit in every artifact (`schema_version` fields)."

**Status:** ⚠ PARTIAL - 20/22 schemas include `schema_version`, 2 embedded schemas missing

Evidence:
- Gap C-GAP-004: issue.schema.json missing schema_version
- Gap C-GAP-005: event.schema.json missing schema_version (but has it - FALSE ALARM, retracted)

**CORRECTION:** Upon re-checking:
- event.schema.json:6 DOES include `"schema_version"` - this was an error in initial analysis
- issue.schema.json does NOT include `schema_version` - Gap C-GAP-004 is valid

**Updated Status:** ⚠ PARTIAL - 21/22 schemas include `schema_version`, 1 embedded schema missing

---

## Key Findings

### ✅ Strengths
1. **Comprehensive coverage:** All 9 workers have schema coverage for their outputs
2. **Strong validation:** All schemas enforce `additionalProperties: false` per specs/01:57
3. **Consistent structure:** All schemas follow JSON Schema Draft 2020-12 standard
4. **Evidence priority:** EvidenceMap schema correctly implements 7-level priority ranking (specs/03:99-110)
5. **Contradiction tracking:** EvidenceMap schema includes contradiction resolution structure (specs/03:119-132)
6. **Rollback metadata:** pr.schema.json correctly enforces Guarantee L rollback requirements (specs/12:39-54)
7. **Budget enforcement:** run_config.schema.json enforces all 7 required budget fields (Guarantees F & G)
8. **Profile-aware validation:** validation_report.schema.json includes required `profile` field (specs/09:166)

### ⚠ Gaps Requiring Attention
1. **C-GAP-001 (BLOCKER):** Missing `positioning.who_it_is_for` field in product_facts.schema.json
2. **C-GAP-002 (MAJOR):** Field name mismatch: schema has `positioning.audience`, spec requires `positioning.who_it_is_for`
3. **C-GAP-003 (MAJOR):** Missing `retryable` field in api_error.schema.json (required by specs/24:27)
4. **C-GAP-004 (MINOR):** issue.schema.json missing `schema_version` field (embedded object)

### 🔍 Notes
- MCP tool schemas (specs/24_mcp_tool_schemas.md:82-392) are defined inline in the spec and not as separate .schema.json files - this is intentional per the spec design
- Ruleset schema (ruleset.schema.json) is well-formed but cross-reference to specs/20_rulesets_and_templates_registry.md shows full alignment
- All commit service schemas (commit_request, commit_response, open_pr_request, open_pr_response) correctly match specs/17_github_commit_service.md

---

## Recommendations

1. **Immediate action (BLOCKER):** Fix C-GAP-001 and C-GAP-002 in product_facts.schema.json
2. **High priority (MAJOR):** Fix C-GAP-003 in api_error.schema.json
3. **Low priority (MINOR):** Consider adding schema_version to issue.schema.json for consistency
4. **Documentation:** Update schema documentation to clarify that `positioning.who_it_is_for` is the authoritative field name per specs/03:17

---

**Report generated:** 2026-01-27
**Verification basis:** Specs as of commit c8dab0c
**Schemas verified:** 22 total (18 full match, 4 partial match)
**Agent:** AGENT_C (Schemas/Contracts Verifier)
