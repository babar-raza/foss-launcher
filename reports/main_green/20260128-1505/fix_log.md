# Fix Log

## Fix Branch: fix/main-green-20260128-1505

### Step 1: Fix pytest asyncio marker configuration

**Commit:** 20a86e4

**Changes:**
- Added `pytest-asyncio>=0.23,<1` to dev dependencies in pyproject.toml
- Added `asyncio` marker to pytest.ini_options markers list

**Reason:** Test collection was failing for 3 MCP test files that use `@pytest.mark.asyncio` decorator but the marker wasn't registered in pytest configuration.

**Files Changed:**
- pyproject.toml

### Step 2: Fix Gate B - Taskcard path mismatches

**Commit:** 1bf8610

**Changes:** Aligned allowed_paths section in body to match frontmatter for 6 taskcards:

1. **TC-410_facts_builder_w2.md**
   - Changed body to use: worker.py (not __main__.py), unit test (not integration test)
   - Removed non-existent: _evidence/__init__.py, __main__.py, integration test
   - Aligned with actual implementation files

2. **TC-412_evidence_map_linking.md**
   - Changed: evidence_map.py → map_evidence.py
   - Changed: test_tc_412_evidence_map.py → test_tc_412_map_evidence.py

3. **TC-413_truth_lock_compile_minimal.md**
   - Changed: truth_lock.py → detect_contradictions.py
   - Changed: test_tc_413_truth_lock.py → test_tc_413_detect_contradictions.py

4. **TC-421_snippet_inventory_tagging.md**
   - Changed body to use: extract_doc_snippets.py (not inventory.py + snippet_tagger.py)
   - Changed: test_tc_421_snippet_inventory.py → test_tc_421_extract_doc_snippets.py

5. **TC-422_snippet_selection_rules.md**
   - Changed: selection.py → extract_code_snippets.py
   - Changed: test_tc_422_snippet_selection.py → test_tc_422_extract_code_snippets.py

6. **TC-550_hugo_config_awareness_ext.md**
   - Changed: resolvers/hugo_config.py → content/hugo_config.py
   - Changed: resolvers/test_tc_550_hugo_config.py → content/test_tc_550_hugo_config.py
   - Changed: reports/agents/**/TC-550/** → reports/agents/CONTENT_AGENT/TC-550/**
   - Removed: non-existent src/launch/schemas/hugo_facts.schema.json

**Reason:** Taskcard validator (Gate B) requires that the allowed_paths list in the body section matches the frontmatter allowed_paths exactly. The body sections had drifted from actual implementation.

**Files Changed:**
- plans/taskcards/TC-410_facts_builder_w2.md
- plans/taskcards/TC-412_evidence_map_linking.md
- plans/taskcards/TC-413_truth_lock_compile_minimal.md
- plans/taskcards/TC-421_snippet_inventory_tagging.md
- plans/taskcards/TC-422_snippet_selection_rules.md
- plans/taskcards/TC-550_hugo_config_awareness_ext.md

### Step 3: Fix Gate D - Broken markdown links

**Commit:** d17bc7c

**Changes:** Fixed 10 broken links in 2 historical report files:

1. **reports/agents/hardening-agent/PRE_W1_HARDENING/report.md** (2 links):
   - Line 168: Replaced broken link `../../../../src/launch/mcp/tools/__init__.py` with plain text `` `src/launch/mcp/tools/__init__.py` `` (historical reference)
   - Line 360: Same fix

2. **reports/post_impl/20260128_131602/final_gates.md** (8 links):
   - Line 124: Fixed `tests/unit/test_determinism.py` → `../../../tests/unit/test_determinism.py`
   - Line 147: Fixed `tests/unit/test_determinism.py` → `../../../tests/unit/test_determinism.py`
   - Line 188: Fixed `src/launch/workers/w7_validator/gates/gate_p1_page_size_limit.py` → `../../../src/launch/workers/w7_validator/gates/gate_p1_page_size_limit.py`
   - Line 189: Fixed gate_p2_image_optimization.py (same pattern)
   - Line 190: Fixed gate_p3_build_time_limit.py (same pattern)
   - Line 193: Fixed gate_s1_xss_prevention.py (same pattern)
   - Line 194: Fixed gate_s2_sensitive_data_leak.py (same pattern)
   - Line 195: Fixed gate_s3_external_link_safety.py (same pattern)

**Reason:** Link checker (Gate D) validates that all markdown links point to existing files with correct relative paths. The report file was using incorrect relative paths.

**Files Changed:**
- reports/agents/hardening-agent/PRE_W1_HARDENING/report.md
- reports/post_impl/20260128_131602/final_gates.md
