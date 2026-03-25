# TC-3684 Report — G3 Import Wiring + Allowlist Extension

## Summary
Threaded `canonical_import` and `product_name` parameters through all 11
`_call_llm_for_content()` call sites in content_generators.py. Extended
`_build_allowlist()` in gate_api_import_allowlist.py to derive modules from
product_facts.json distribution and code_structure fields.

## Changes
- `content_generators.py`: Added `_get_canonical_import()` lazy-import helper;
  all 11 call sites now pass `canonical_import=` and `product_name=`
- `gate_api_import_allowlist.py`: `_build_allowlist()` extended with
  product_facts.json distribution identifier + code_structure.package_names

## Tests
- 17 new tests in `tests/unit/workers/test_import_wiring.py`
  - `TestGetCanonicalImport` (4): api_inventory, code_structure, product_name, empty
  - `TestCanonicalImportThreading` (9): verifies all generators pass params
  - `TestAllowlistExtension` (5): distribution, package_names, no-facts, malformed

## Verification
- Full suite: 8617 passed, 0 failed (PYTHONHASHSEED=0)
