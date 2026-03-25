# Evidence: SR-session7 Healing (SR-01, SR-02, SR-03)

## SR-01 — Direct unit test for seo.run_seo_research()

### Change
- `tests/unit/workers/understand/test_seo.py` created (10 tests)
- Tests call real `run_seo_research()` — no mocking of the function itself
- Covers: config.seo=None path, explicit offline_mode=True path, gemini_available=False

### Key correction during implementation
Initial assertion assumed offline=True → empty keyword bundle. Real behavior: offline
only skips network sources (Trends/Suggest/Gemini). Local sources (claim-derived +
search patterns — Sources 4 and 5) still run. Tests corrected to assert type (list) and
gemini_available=False, not emptiness.

### Test Evidence
Command: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_seo.py -v`
Result: 10 passed, 0 failed

---

## SR-02 — Verify Generate worker handles language="unknown" snippets

### Investigation (grep evidence)

Usage site 1 — `worker.py:1227`:
```python
_lang = _blk.language or "python"
```
`language="unknown"` is truthy → `_lang = "unknown"` → produces ````unknown\n...\n``` (valid markdown fence). NO CRASH.

Usage site 2 — `worker.py:1762`:
```python
language=block.language,
```
Simple copy of attribute value. NO PROCESSING. Safe for any string including "unknown".

Usage site 3 — `worker.py:1805`:
```python
if block.language and not (is_shell and block.language in ("python", "py")):
    result.append(block)
    continue
```
`"unknown"` is truthy (first condition passes). `"unknown" in ("python", "py")` is False → `not (is_shell and False)` = True → block passes through unchanged. NO CRASH.

Usage site 4 — `section_prompt.py:1540`:
```python
parts.append(f"```{s.language}\n# Claims: {claims_str}\n{clean_code}\n```")
```
`language="unknown"` produces ````unknown\n...\n``` (valid markdown). NO CRASH.

### Verdict: NO CODE CHANGE NEEDED. All 4 sites handle "unknown" gracefully.

### Tests Added
- `TestSyntaxValidFilter::test_unknown_language_snippet_is_included`: verifies filter passes language="unknown" with syntax_valid=None through
- `TestSyntaxValidFilter::test_unknown_language_formats_to_valid_fence`: calls real `_format_snippets()` and asserts ````unknown` fence is produced

Command: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_generate.py -v -k unknown_language`
Result: 2 passed, 0 failed

---

## SR-03 — Actual deterministic extraction artifact from TypeScript fixture

### Change
- `TestEndToEndDeterministicExtraction` class added to `tests/unit/workers/understand/test_typescript_integration.py` (6 tests)

### Architecture Note
`_extract_api_surface()` is Python-centric: it scans source files via `analyze_file_safe()`,
but `dist/` is in `_EXCLUDE_DIRS`, so `.d.ts` files are not reachable. TypeScript class
extraction in production goes through `TypeScriptAdapter._find_dts_root()` +
`_extract_classes_from_dts_files()`. The SR-03 test uses this production path directly.

### Artifact Evidence (captured by test assertions)

| Evidence Type | Function | Result |
|---|---|---|
| api_surface.public_classes | `_find_dts_root` + `_extract_classes_from_dts_files` | `["Workbook", "Worksheet", "FileFormat"]` |
| install_recipe.install_command | `extract_install_recipe` | `"npm install @aspose-ts/cells"` |
| limitations | `extract_limitations` | 1+ entries from `throw new Error(...)` in `src/index.ts` |

### Test Evidence
Command: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_typescript_integration.py -v -k EndToEnd`
Result: 6 passed, 0 failed

---

## Full Suite
Command: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q`
Result: 4333 passed, 65 skipped, 3 xfailed, 2 xpassed, 0 failed
Previous baseline: 4315 passed (Session 7 after TC-UND-100..105)
Delta: +18 tests
