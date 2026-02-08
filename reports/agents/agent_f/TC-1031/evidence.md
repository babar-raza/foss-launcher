# TC-1031 Evidence: Typed Artifact Models -- Worker Models (W3-W9)

## Files Created

### Model Files (src/launch/models/)
1. `src/launch/models/snippet_catalog.py` -- SnippetCatalog, Snippet, SnippetSource, SnippetValidation, SnippetRequirements
2. `src/launch/models/page_plan.py` -- PagePlan, PageEntry, ContentStrategy, ClaimQuota, LaunchTierAdjustment
3. `src/launch/models/patch_bundle.py` -- PatchBundle, Patch
4. `src/launch/models/validation_report.py` -- ValidationReport, GateResult, Issue, IssueLocation
5. `src/launch/models/pr_artifact.py` -- PRResult, ValidationSummary

### Updated Files
6. `src/launch/models/__init__.py` -- Added exports for all 18 new classes

### Test Files (tests/unit/models/)
7. `tests/unit/models/test_snippet_catalog.py` -- 20 tests
8. `tests/unit/models/test_page_plan.py` -- 23 tests
9. `tests/unit/models/test_patch_bundle.py` -- 17 tests
10. `tests/unit/models/test_validation_report.py` -- 20 tests
11. `tests/unit/models/test_pr_artifact.py` -- 15 tests

### Taskcard and Evidence
12. `plans/taskcards/TC-1031_typed_artifact_models_workers.md`
13. `reports/agents/agent_f/TC-1031/self_review.md`
14. `reports/agents/agent_f/TC-1031/evidence.md`

## Schema Alignment

Each model was created directly from the corresponding JSON schema:

| Model | Schema | Fields Covered |
|-------|--------|---------------|
| SnippetCatalog | snippet_catalog.schema.json | schema_version, snippets (with snippet sub-schema: snippet_id, language, tags, source, code, requirements, validation) |
| PagePlan | page_plan.schema.json | schema_version, product_slug, launch_tier, pages, launch_tier_adjustments, inferred_product_type, evidence_volume, effective_quotas |
| PatchBundle | patch_bundle.schema.json | schema_version, patches (with patch sub-schema: patch_id, type, path, content_hash, new_content, anchor, start/end_line, frontmatter_updates, expected_before_hash) |
| ValidationReport | validation_report.schema.json + issue.schema.json | schema_version, ok, profile, gates, issues, manual_edits, manual_edited_files |
| PRResult | pr.schema.json | schema_version, run_id, base_ref, rollback_steps, affected_paths, pr_number, pr_url, branch_name, commit_shas, pr_body, validation_summary |

## Test Results

### New model tests (95 tests):
```
tests/unit/models/test_snippet_catalog.py .................... [20 passed]
tests/unit/models/test_page_plan.py ....................... [23 passed]
tests/unit/models/test_patch_bundle.py ................. [17 passed]
tests/unit/models/test_validation_report.py .................... [20 passed]
tests/unit/models/test_pr_artifact.py ............... [15 passed]
```

### Full regression suite:
```
2182 passed, 12 skipped, 0 failed
```

## Design Decisions

1. **Followed TC-1030 pattern exactly**: All models extend Artifact, implement from_dict/to_dict/validate, handle optional fields with .get().

2. **Sub-models are plain classes (not Artifacts)**: SnippetSource, Issue, GateResult, etc. are regular classes with to_dict/from_dict -- they don't need schema_version.

3. **Deterministic output**: All list fields that represent sets (claim_ids, tags, paths, files) are sorted in to_dict(). Dictionary keys are inherently sorted by Artifact.to_json(sort_keys=True).

4. **Validation is lightweight**: validate() checks required fields, enum values, and types. It does NOT perform full JSON schema validation (that is handled by validate_schema_file() from the base class).

5. **No business logic**: Models are pure data containers. No worker-specific logic, no I/O, no side effects.

## Dependency Verification

- TC-1030 (foundation) is COMPLETE -- base.py Artifact class, existing W1/W2 models all present and working.
- No modification to any existing model files (only additive changes to __init__.py).
- No modification to any worker files.
