# TC-1042: Integrate Code Analysis into W2 Worker - Evidence

## Taskcard
- **ID**: TC-1042
- **Title**: Integrate code analysis into W2 FactsBuilder worker
- **Status**: Complete
- **Agent**: Agent-B

## Changes Made

### 1. `src/launch/workers/w2_facts_builder/worker.py`

**Change 1 - Code analysis invocation (after repo_inventory load):**
- Added import of `analyze_repository_code` from `.code_analyzer`
- Calls `analyze_repository_code(repo_dir, repo_inventory, product_name)` to get structured code analysis data
- Falls back to `run_layout.work_dir` if `repo` subdirectory does not exist

**Change 2 - API surface summary (replaced placeholder):**
- Now uses `code_analysis.get("api_surface", {})` as primary source for API classes and functions
- Falls back to claim-text-based extraction only when code analysis finds nothing

**Change 3 - Positioning (replaced placeholder):**
- Uses `code_analysis.get("positioning", {})` for tagline and short_description
- Falls back to placeholder strings only when code analysis returns empty values

**Change 4 - Code structure and version (new fields):**
- Adds `product_facts["code_structure"]` from code analysis when available
- Adds `product_facts["version"]` from manifest/constant extraction when available

### 2. `src/launch/workers/w2_facts_builder/extract_claims.py`

**New function `extract_claims_from_code_analysis()`:**
- Generates claims from extracted constants (version, supported formats)
- Uses correct 3-argument `compute_claim_id(claim_text, claim_kind, product_name)` signature
- Version claims have `claim_kind="metadata"`, truth_status="fact", confidence="high"
- Format claims from SUPPORTED_FORMATS constant have `claim_kind="format"`
- All claims include proper citations pointing to manifest/source files

## Test Results

```
tests/unit/workers/test_tc_411_extract_claims.py: 42 passed
tests/unit/workers/test_tc_412_map_evidence.py: 38 passed
tests/unit/workers/test_w2_code_analyzer.py: 29 passed
Total: 109 passed, 0 failed
```

## Verification

- All existing W2 tests pass without modification
- The `test_no_example_count_limit_in_assembly` test (which exercises `assemble_product_facts`) passes
- Code analysis gracefully handles missing repo directories by falling back
