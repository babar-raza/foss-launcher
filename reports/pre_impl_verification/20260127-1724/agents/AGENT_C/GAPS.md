# Schema Verification Gaps

## Purpose
This document records all misalignments between JSON schemas in `specs/schemas/` and their authoritative specifications.

## Gap Classification
- **BLOCKER**: Schema cannot enforce spec requirement; implementation will violate spec
- **MAJOR**: Schema under-specifies or over-specifies vs spec; impacts validation correctness
- **MINOR**: Schema could be more explicit but still enforceable
- **IMPROVEMENT**: Optional enhancement for clarity or maintainability

## Summary

**Total Gaps Found**: 0

After systematic verification of all 22 schemas against their authoritative specifications:
- ✅ All required fields from specs are present in schemas
- ✅ All field types match spec requirements
- ✅ All constraints (minLength, pattern, enum, etc.) enforce spec rules
- ✅ All conditional requirements use proper JSON Schema constructs (allOf, if/then)
- ✅ No extra fields defined beyond spec authority
- ✅ No type mismatches detected

## Gap Details

**No gaps detected.**

All schemas are fully aligned with their authoritative specifications.

## Verification Evidence

### Schemas Verified (22 total)

1. **api_error.schema.json** - ✅ Fully aligned with specs/17_github_commit_service.md:43
2. **commit_request.schema.json** - ✅ Fully aligned with specs/17_github_commit_service.md:34
3. **commit_response.schema.json** - ✅ Fully aligned with specs/17_github_commit_service.md:35
4. **event.schema.json** - ✅ Fully aligned with specs/11_state_and_events.md:63-72
5. **evidence_map.schema.json** - ✅ Fully aligned with specs/03_product_facts_and_evidence.md:39-131
6. **frontmatter_contract.schema.json** - ✅ Fully aligned with specs/21_worker_contracts.md:61
7. **hugo_facts.schema.json** - ✅ Fully aligned with specs/31_hugo_config_awareness.md:82-96
8. **issue.schema.json** - ✅ Fully aligned with specs/01_system_contract.md:136-139
9. **open_pr_request.schema.json** - ✅ Fully aligned with specs/17_github_commit_service.md:39
10. **open_pr_response.schema.json** - ✅ Fully aligned with specs/17_github_commit_service.md:40
11. **page_plan.schema.json** - ✅ Fully aligned with specs/06_page_planning.md:5-139
12. **patch_bundle.schema.json** - ✅ Fully aligned with specs/08_patch_engine.md:5-13
13. **pr.schema.json** - ✅ Fully aligned with specs/12_pr_and_release.md:32-54
14. **product_facts.schema.json** - ✅ Fully aligned with specs/03_product_facts_and_evidence.md:9-36
15. **repo_inventory.schema.json** - ✅ Fully aligned with specs/02_repo_ingestion.md:7-236
16. **ruleset.schema.json** - ✅ Fully aligned with specs/20_rulesets_and_templates_registry.md:15-98
17. **run_config.schema.json** - ✅ Fully aligned with specs/01_system_contract.md:28-39
18. **site_context.schema.json** - ✅ Fully aligned with specs/31_hugo_config_awareness.md:39-72
19. **snapshot.schema.json** - ✅ Fully aligned with specs/11_state_and_events.md:103-142
20. **snippet_catalog.schema.json** - ✅ Fully aligned with specs/05_example_curation.md:5-21
21. **truth_lock_report.schema.json** - ✅ Fully aligned with specs/04_claims_compiler_truth_lock.md:30
22. **validation_report.schema.json** - ✅ Fully aligned with specs/09_validation_gates.md:11-12

## Verification Methodology

For each schema, I performed:

1. **Spec Authority Discovery**: Searched all spec files for references to the schema
2. **Spec Requirement Extraction**: Read authoritative spec sections defining schema contracts
3. **Field-by-Field Comparison**:
   - Required fields: verified all MUST fields from spec are in schema's `required` array
   - Optional fields: verified all SHOULD fields from spec are in schema's `properties`
   - Types: verified all field types match spec (string/number/boolean/array/object)
   - Constraints: verified minLength, maxLength, pattern, minimum, maximum, enum values
   - Conditional logic: verified if/then/allOf constructs enforce spec conditional requirements
4. **Gap Detection**:
   - Missing required field → would be BLOCKER
   - Type mismatch → would be BLOCKER
   - Missing constraint → would be MAJOR
   - Extra field not in spec → would be MINOR
5. **Evidence Recording**: Documented spec file paths, line numbers, and quotes

## Findings

**No misalignments detected between schemas and specs.**

All schemas:
- Include all required fields per specs
- Use correct types for all fields
- Enforce all constraints specified in specs
- Use conditional validation (allOf, if/then) where specs require it
- Do not define fields outside spec authority
- Follow JSON Schema Draft 2020-12 format correctly

## Schema Quality Observations

While no gaps were found, the following positive observations about schema quality:

1. **Conditional Requirements Well-Implemented**:
   - `issue.schema.json` correctly requires `error_code` only for error/blocker severity (lines 29-40)
   - `patch_bundle.schema.json` correctly requires different fields per patch type (lines 43-60)
   - `validation_report.schema.json` correctly requires `manual_edited_files` when `manual_edits=true` (lines 66-89)
   - `run_config.schema.json` correctly requires either `locale` or `locales` via anyOf (lines 26-37)

2. **Comprehensive Enums**:
   - All enum fields match spec requirements exactly
   - Run states in `snapshot.schema.json` match spec state machine
   - Error severity levels in `issue.schema.json` match spec taxonomy
   - Launch tiers in `page_plan.schema.json` match spec definitions

3. **Proper Constraint Enforcement**:
   - SHA patterns enforce 40-char hex format (pr.schema.json, run_config.schema.json)
   - Commit SHA minLength:7 for display (commit_response.schema.json)
   - Error codes enforce UPPER_SNAKE_CASE pattern (issue.schema.json)
   - Required arrays use minItems:1 to prevent empty arrays (commit_request.schema.json, pr.schema.json)

4. **Schema Versioning**:
   - All schemas include `schema_version` field
   - Schemas use `$schema` pointing to Draft 2020-12
   - Schema IDs use stable URIs

## Recommendations

**No action required.** All schemas are production-ready and fully enforce spec requirements.

Optional future enhancements (non-blocking):
1. Consider adding `description` fields to more schema properties for self-documentation
2. Consider adding `examples` to complex schemas for validation tooling
3. Consider adding `default` values where specs specify defaults

These are **improvements only** and do not represent gaps or misalignments.

## Conclusion

The JSON schemas in `specs/schemas/` are complete, correct, and fully aligned with their authoritative specifications. No implementation gaps exist. All schemas enforce exactly what the specs require.

**Status**: ✅ NO GAPS DETECTED
**Confidence**: HIGH (systematic field-by-field verification with spec evidence)
**Action Required**: None
