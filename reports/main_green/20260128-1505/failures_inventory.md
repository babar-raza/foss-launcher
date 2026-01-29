# Failures Inventory

## Baseline Information
- **Branch**: main
- **HEAD**: 00275907f5ad4f14f26880af90c77dd80954c6c6
- **Timestamp**: 20260128-1505

## Git Status
```
## main...origin/main [ahead 126]
```

## Failing Gates (2 code issues + 2 environment issues)

### Gate 0: Virtual environment policy (.venv enforcement)
**Status**: FAILED (environment issue - not a code fix)
- Running from global Python instead of .venv
- This will pass when running from within .venv

### Gate B: Taskcard validation + path enforcement
**Status**: FAILED (6 taskcards with path mismatches)

Failing taskcards:
1. **TC-410_facts_builder_w2.md**
   - In frontmatter but NOT in body:
     - `src/launch/workers/w2_facts_builder/worker.py`
     - `tests/unit/workers/test_tc_410_facts_builder.py`
   - In body but NOT in frontmatter:
     - `src/launch/workers/_evidence/__init__.py`
     - `src/launch/workers/w2_facts_builder/__main__.py`
     - `tests/integration/test_tc_410_w2_integration.py`

2. **TC-412_evidence_map_linking.md**
   - In frontmatter but NOT in body:
     - `src/launch/workers/w2_facts_builder/map_evidence.py`
     - `tests/unit/workers/test_tc_412_map_evidence.py`
   - In body but NOT in frontmatter:
     - `src/launch/workers/w2_facts_builder/evidence_map.py`
     - `tests/unit/workers/test_tc_412_evidence_map.py`

3. **TC-413_truth_lock_compile_minimal.md**
   - In frontmatter but NOT in body:
     - `src/launch/workers/w2_facts_builder/detect_contradictions.py`
     - `tests/unit/workers/test_tc_413_detect_contradictions.py`
   - In body but NOT in frontmatter:
     - `src/launch/workers/w2_facts_builder/truth_lock.py`
     - `tests/unit/workers/test_tc_413_truth_lock.py`

4. **TC-421_snippet_inventory_tagging.md**
   - In frontmatter but NOT in body:
     - `src/launch/workers/w3_snippet_curator/extract_doc_snippets.py`
     - `tests/unit/workers/test_tc_421_extract_doc_snippets.py`
   - In body but NOT in frontmatter:
     - `src/launch/adapters/snippet_tagger.py`
     - `src/launch/workers/w3_snippet_curator/inventory.py`
     - `tests/unit/workers/test_tc_421_snippet_inventory.py`

5. **TC-422_snippet_selection_rules.md**
   - In frontmatter but NOT in body:
     - `src/launch/workers/w3_snippet_curator/extract_code_snippets.py`
     - `tests/unit/workers/test_tc_422_extract_code_snippets.py`
   - In body but NOT in frontmatter:
     - `src/launch/workers/w3_snippet_curator/selection.py`
     - `tests/unit/workers/test_tc_422_snippet_selection.py`

6. **TC-550_hugo_config_awareness_ext.md**
   - In frontmatter but NOT in body:
     - `reports/agents/CONTENT_AGENT/TC-550/**`
     - `src/launch/content/hugo_config.py`
     - `tests/unit/content/test_tc_550_hugo_config.py`
   - In body but NOT in frontmatter:
     - `reports/agents/**/TC-550/**`
     - `src/launch/resolvers/hugo_config.py`
     - `src/launch/schemas/hugo_facts.schema.json`
     - `tests/unit/resolvers/test_tc_550_hugo_config.py`

### Gate D: Markdown link integrity
**Status**: FAILED (10 broken links in 2 files)

Broken links:
1. **reports\agents\hardening-agent\PRE_W1_HARDENING\report.md** (2 broken links)
   - Line 168: `../../../../src/launch/mcp/tools/__init__.py` -> src\launch\mcp\tools\__init__.py
   - Line 360: `../../../../src/launch/mcp/tools/__init__.py` -> src\launch\mcp\tools\__init__.py

2. **reports\post_impl\20260128_131602\final_gates.md** (8 broken links)
   - Line 124: `tests/unit/test_determinism.py` -> reports\post_impl\20260128_131602\tests\unit\test_determinism.py
   - Line 147: `tests/unit/test_determinism.py` -> reports\post_impl\20260128_131602\tests\unit\test_determinism.py
   - Line 188: `src/launch/workers/w7_validator/gates/gate_p1_page_size_limit.py`
   - Line 189: `src/launch/workers/w7_validator/gates/gate_p2_image_optimization.py`
   - Line 190: `src/launch/workers/w7_validator/gates/gate_p3_build_time_limit.py`
   - Line 193: `src/launch/workers/w7_validator/gates/gate_s1_xss_prevention.py`
   - Line 194: `src/launch/workers/w7_validator/gates/gate_s2_sensitive_data_leak.py`
   - Line 195: `src/launch/workers/w7_validator/gates/gate_s3_external_link_safety.py`

### Gate O: Budget config (Guarantees F/G: budget config)
**Status**: FAILED (environment issue - missing dependency)
- ModuleNotFoundError: No module named 'jsonschema'
- This will pass when running from .venv with dependencies installed

## Failing Tests

**Status**: Test collection errors (3 errors)
- ERROR tests/unit/mcp/test_tc_510_server_setup.py - Failed: 'asyncio' not found in `markers` configuration option
- ERROR tests/unit/mcp/test_tc_511_tool_registration.py - Failed: 'asyncio' not found in `markers` configuration option
- ERROR tests/unit/mcp/test_tc_512_tool_handlers.py - Failed: 'asyncio' not found in `markers` configuration option

Note: The prompt mentions "1362/1368 (6 failing)" but the current test run shows collection errors instead. This needs investigation.

## Summary

**Critical Fixes Needed:**
1. Fix 6 taskcard path mismatches (Gate B)
2. Fix 10 broken markdown links (Gate D)
3. Fix pytest asyncio marker configuration (test collection)

**Environment Issues (not code fixes):**
1. Gate 0 will pass when running from .venv
2. Gate O will pass when dependencies are properly installed
