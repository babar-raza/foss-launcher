# Agent B1 — Changes Summary

## File 1: src/launcher/workers/understand/extract/_llm.py

### TC-4262
- **Line 19**: `_MAX_SOURCE_CHARS = 32_000` → `_MAX_SOURCE_CHARS = 128_000`

## File 2: src/launcher/workers/scout/scout.py

### TC-4263 Sub-change 1
- **Line 267**: `_DEFAULT_BUDGET_BYTES = 1_000_000` → `_DEFAULT_BUDGET_BYTES = 5_000_000`

### TC-4263 Sub-change 2
- **After line 267**: Added new constants block:
  ```python
  _PER_FILE_MAX_CHARS: dict[str, int] = {
      "doc": 500_000,
      "source": 300_000,
  }
  _PER_FILE_MAX_CHARS_DEFAULT = 100_000
  ```

### TC-4263 Sub-change 3 — README call site (originally ~line 493)
- Changed `sanitize_input(raw, max_chars=100_000)` to
  `sanitize_input(raw, max_chars=_PER_FILE_MAX_CHARS.get("doc", _PER_FILE_MAX_CHARS_DEFAULT))`
  (README is always a doc, so hardcoded "doc" key is correct)

### TC-4263 Sub-change 3 — Main loop call site (originally ~line 629)
- Changed `sanitize_input(raw, max_chars=100_000)` to
  `sanitize_input(raw, max_chars=_PER_FILE_MAX_CHARS.get(category.value, _PER_FILE_MAX_CHARS_DEFAULT))`
  (`category` is a `FileCategory` enum; `.value` gives the string key)

### TC-4264 — No source change
- Inspection confirmed the root-level guard `"/" not in lower and` does NOT exist in the
  current `_doc_skip_reason` implementation. The function already applies keyword filtering
  at all path depths. No source code modification was required.

## File 3: tests/unit/workers/test_understand.py

### TC-4262
- Added class `TestLLMDocWindowConstant` with test `test_max_source_chars_128k` at end of file

## File 4: tests/unit/workers/test_scout.py

### TC-4263
- Added class `TestScoutBudgetConstants` with three tests:
  - `test_default_budget_bytes_5mb`
  - `test_per_file_cap_doc_500kb`
  - `test_per_file_cap_source_300kb`

### TC-4264
- Added class `TestMetaDocSubdirFiltering` with four tests:
  - `test_metadoc_subdir_filtered`
  - `test_metadoc_roadmap_subdir_filtered`
  - `test_quickstart_not_filtered`
  - `test_readme_subdir_not_filtered`
